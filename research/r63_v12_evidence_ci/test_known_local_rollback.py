"""R63 V12 local-rollback negative controls against the exact frozen V9 V2 source.

These passing tests demonstrate known limitations, NOT an antirollback defense.
No signer, CNG, ACL, services, credentials, or production data are touched.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
SIDECAR=HERE.parent/"r63_v10_source_gate"
sys.path.insert(0,str(SIDECAR))
import spend_chain_v2 as v2

PIN="c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd"
HOLD="HOLD_UNCERTAIN"
RESERVE="RESERVED_ONLY_NO_SIGN"
N=["a"*64,"b"*64,"c"*64]
I=["1"*64,"2"*64,"3"*64]

def pinned():
    if hashlib.sha256((SIDECAR/"spend_chain_v2.py").read_bytes()).hexdigest()!=PIN:
        raise RuntimeError("EXACT_FROZEN_SIDECAR_PIN_MISMATCH")

def write(root,rows):
    raw2=b""
    for nonce,ident in rows:
        raw2,status=v2.append(raw2,nonce,ident)
        if status!="NEW_NEEDS_DURABLE_APPEND":
            raise RuntimeError("unexpected fixture append")
    raw1=b"".join(v2.canonical(list(pair))+b"\n" for pair in rows)
    (root/"v1.jsonl").write_bytes(raw1)
    (root/"v2.jsonl").write_bytes(raw2)

def gate(root,nonce,ident):
    """Deliberately only a same-admin flag + coherent journals: MODEL ONLY."""
    try:
        if (root/"uncertain.flag").exists():
            return HOLD
        raw1=(root/"v1.jsonl").read_bytes()
        raw2=(root/"v2.jsonl").read_bytes()
        state=v2.review(raw2)
        expected=b"".join(v2.canonical(list(p))+b"\n" for p in state.pairs)
        if raw1!=expected:
            return HOLD
        rows=[list(p) for p in state.pairs]
        if [nonce,ident] in rows:
            return "ALREADY_RESERVED_NO_NEW_APPEND"
        if any(nonce==n or ident==ident0 for n,ident0 in rows):
            return HOLD
        new,status=v2.append(raw2,nonce,ident)
        if status!="NEW_NEEDS_DURABLE_APPEND":
            return HOLD
        # Simulates cooperating local writers, no OS mandatory lock.
        (root/"v2.jsonl").write_bytes(new)
        (root/"v1.jsonl").write_bytes(raw1+v2.canonical([nonce,ident])+b"\n")
        return RESERVE
    except (ValueError,TypeError,RuntimeError,OSError,RecursionError):
        return HOLD

class SameAdminNegativeControls(unittest.TestCase):
    def setUp(self):
        pinned()
        tmp=tempfile.TemporaryDirectory(prefix="r63_v12_known_counterexample_")
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        write(self.root,list(zip(N[:2],I[:2])))

    def test_positive_reservation_as_control(self):
        self.assertEqual(gate(self.root,N[2],I[2]),RESERVE)

    def test_uncertainty_marker_blocks(self):
        (self.root/"uncertain.flag").write_bytes(b"SYNTHETIC_CRASH_INTENT=pre_v2\n")
        self.assertEqual(gate(self.root,N[2],I[2]),HOLD)

    def test_flag_deletion_reopens_admission_expected_failure_of_security(self):
        marker=self.root/"uncertain.flag"
        marker.write_bytes(b"SYNTHETIC_CRASH_INTENT=pre_v2\n")
        self.assertEqual(gate(self.root,N[2],I[2]),HOLD)
        marker.unlink()  # attacker with same-admin local filesystem access
        self.assertEqual(gate(self.root,N[2],I[2]),RESERVE)

    def test_coherent_rollback_reissues_same_nonce_expected_failure_of_security(self):
        prior1=(self.root/"v1.jsonl").read_bytes()
        prior2=(self.root/"v2.jsonl").read_bytes()
        self.assertEqual(gate(self.root,N[2],I[2]),RESERVE)
        later=v2.review((self.root/"v2.jsonl").read_bytes())
        self.assertEqual(later.seq,3)
        (self.root/"v1.jsonl").write_bytes(prior1)
        (self.root/"v2.jsonl").write_bytes(prior2)
        old=v2.review((self.root/"v2.jsonl").read_bytes())
        self.assertEqual(old.seq,2)
        self.assertNotEqual(old.head,later.head)
        # ONLY an outside intact copy of the later head could spot regression.
        self.assertEqual(gate(self.root,N[2],I[2]),RESERVE)
        self.assertEqual(v2.review((self.root/"v2.jsonl").read_bytes()).seq,3)

    def test_split_journals_remain_hold_without_flag(self):
        raw2=(self.root/"v2.jsonl").read_bytes()
        new,status=v2.append(raw2,N[2],I[2])
        self.assertEqual(status,"NEW_NEEDS_DURABLE_APPEND")
        (self.root/"v2.jsonl").write_bytes(new)
        self.assertEqual(gate(self.root,N[2],I[2]),HOLD)

    def test_truncated_v2_remains_hold(self):
        p=self.root/"v2.jsonl"
        p.write_bytes(p.read_bytes()[:-1])
        self.assertEqual(gate(self.root,N[2],I[2]),HOLD)

    def test_missing_v1_remains_hold(self):
        (self.root/"v1.jsonl").unlink()
        self.assertEqual(gate(self.root,N[2],I[2]),HOLD)

if __name__=="__main__":
    unittest.main(verbosity=2)
