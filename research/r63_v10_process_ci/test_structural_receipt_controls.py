"""R63 research-only structural receipt replay: positive and negative controls.

Uses public SHA256 commitments, NOT a digital signature, witness authority,
nonrollback proof, key management, CNG, or live Ario receipt verification.
Designed to detect an always-HOLD implementation in earlier negative-only tests.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SRC = Path(__file__).resolve()
sys.path.insert(0, str(SRC.parent.parent / "r63_v10_source_gate"))
import spend_chain_v2 as v2

PIN = "c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd"
DOMAIN = b"R63-SYNTHETIC-STRUCTURAL-RECEIPT-V1\x00"
N0, I0 = "a"*64, "1"*64
N1, I1 = "b"*64, "2"*64
N2, I2 = "c"*64, "3"*64
HOLD = b"HOLD_UNCERTAIN\n"

def sha(b):
    return hashlib.sha256(b).hexdigest()

def source_guard():
    if sha(Path(v2.__file__).read_bytes()) != PIN:
        raise RuntimeError("V9 exact source mismatch")

def prepare(root, rows):
    root.mkdir(parents=True, exist_ok=True)
    raw1 = b"".join(v2.canonical(p)+b"\n" for p in rows)
    raw2 = b""
    for n,k in rows:
        raw2,how=v2.append(raw2,n,k)
        if how!="NEW_NEEDS_DURABLE_APPEND":
            raise RuntimeError("duplicate fixture row")
    (root/"v1.jsonl").write_bytes(raw1)
    (root/"v2.jsonl").write_bytes(raw2)
    return raw1,raw2

def create_receipt(root, target):
    raw1=(root/"v1.jsonl").read_bytes()
    raw2=(root/"v2.jsonl").read_bytes()
    state=v2.review(raw2)
    if not any(n==target for n,k in state.pairs):
        raise RuntimeError("target not reserved")
    fields={
        "version": "R63_SYNTHETIC_STRUCTURAL_RECEIPT_1",
        "nonce": target, "result": "EXISTING",
        "v1_sha256": sha(raw1), "v2_sha256": sha(raw2),
        "v2_head": state.head,
    }
    rec={**fields,"content_sha256":sha(DOMAIN+v2.canonical(fields))}
    receipt=v2.canonical(rec)+b"\n"
    (root/"receipt.json").write_bytes(receipt)
    return receipt

def verify(root, target):
    try:
        source_guard()
        receipt=(root/"receipt.json").read_bytes()
        if not receipt.endswith(b"\n") or len(receipt)>4096:
            return HOLD
        obj=json.loads(receipt)
        if not isinstance(obj,dict) or v2.canonical(obj)+b"\n"!=receipt:
            return HOLD
        if set(obj)!={"version","nonce","result","v1_sha256",
                     "v2_sha256","v2_head","content_sha256"}:
            return HOLD
        content={k:v for k,v in obj.items() if k!="content_sha256"}
        if obj["content_sha256"]!=sha(DOMAIN+v2.canonical(content)):
            return HOLD
        if obj["version"]!="R63_SYNTHETIC_STRUCTURAL_RECEIPT_1":
            return HOLD
        if obj["nonce"]!=target or obj["result"]!="EXISTING":
            return HOLD
        raw1=(root/"v1.jsonl").read_bytes()
        raw2=(root/"v2.jsonl").read_bytes()
        state=v2.review(raw2)
        canonical_v1=b"".join(v2.canonical(p)+b"\n" for p in state.pairs)
        if raw1!=canonical_v1:
            return HOLD
        if not any(n==target for n,k in state.pairs):
            return HOLD
        if (sha(raw1)!=obj["v1_sha256"] or sha(raw2)!=obj["v2_sha256"]
            or state.head!=obj["v2_head"]):
            return HOLD
        # Same persisted canonical bytes, not a new receipt or a new signature.
        return receipt
    except (OSError,ValueError,TypeError,RecursionError,RuntimeError):
        return HOLD

def verify_subproc(root, target):
    proc=subprocess.run([sys.executable,"-I","-B",str(SRC),
                         "--verify",str(root),target],
                        capture_output=True,timeout=10)
    if proc.returncode!=0:
        raise RuntimeError("verification process failed: "+repr(proc.stderr[-400:]))
    return proc.stdout

class ReceiptTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="r63_receipt_control_")
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.rows=[[N0,I0],[N1,I1],[N2,I2]]
        prepare(self.root,self.rows)
        self.receipt=create_receipt(self.root,N2)

    def test_positive_replay_identical_16_distinct_verifier_processes(self):
        for _ in range(16):
            self.assertEqual(verify_subproc(self.root,N2),self.receipt)

    def test_wrong_nonce_fails(self):
        self.assertEqual(verify_subproc(self.root,N1),HOLD)

    def test_missing_receipt_fails(self):
        (self.root/"receipt.json").unlink()
        self.assertEqual(verify_subproc(self.root,N2),HOLD)

    def test_receipt_one_byte_change_fails(self):
        raw=self.receipt
        (self.root/"receipt.json").write_bytes(raw.replace(b"EXISTING",b"EXISTINX"))
        self.assertEqual(verify_subproc(self.root,N2),HOLD)

    def test_partial_receipt_fails(self):
        (self.root/"receipt.json").write_bytes(self.receipt[:-1])
        self.assertEqual(verify_subproc(self.root,N2),HOLD)

    def test_corrupt_v1_fails(self):
        raw=(self.root/"v1.jsonl").read_bytes()
        (self.root/"v1.jsonl").write_bytes(raw[:-1])
        self.assertEqual(verify_subproc(self.root,N2),HOLD)

    def test_deleted_v1_fails(self):
        (self.root/"v1.jsonl").unlink()
        self.assertEqual(verify_subproc(self.root,N2),HOLD)

    def test_v2_corruption_fails(self):
        raw=(self.root/"v2.jsonl").read_bytes()
        (self.root/"v2.jsonl").write_bytes(raw[:-1])
        self.assertEqual(verify_subproc(self.root,N2),HOLD)

    def test_append_new_reservation_invalidates_stale_receipt(self):
        prepare(self.root,self.rows+[[("d"*64),("4"*64)]])
        self.assertEqual(verify_subproc(self.root,N2),HOLD)

    def test_v1_reordered_content_fails(self):
        (self.root/"v1.jsonl").write_bytes(
            b"".join(v2.canonical(p)+b"\n" for p in reversed(self.rows)))
        self.assertEqual(verify_subproc(self.root,N2),HOLD)

    def test_expected_coherent_rollback_remains_accepted(self):
        # All three local files roll back together; this is a known FAIL of
        # antirollback, even though the test passes as a negative control.
        old_receipt=self.receipt
        old_v1=(self.root/"v1.jsonl").read_bytes()
        old_v2=(self.root/"v2.jsonl").read_bytes()
        prepare(self.root,self.rows+[[("d"*64),("4"*64)]])
        create_receipt(self.root,"d"*64)
        (self.root/"v1.jsonl").write_bytes(old_v1)
        (self.root/"v2.jsonl").write_bytes(old_v2)
        (self.root/"receipt.json").write_bytes(old_receipt)
        self.assertEqual(verify_subproc(self.root,N2),old_receipt)

if __name__=="__main__":
    if len(sys.argv)==4 and sys.argv[1]=="--verify":
        sys.stdout.buffer.write(verify(Path(sys.argv[2]),sys.argv[3]))
    elif len(sys.argv)==1:
        source_guard()
        unittest.main(verbosity=2)
    else:
        sys.exit(2)
