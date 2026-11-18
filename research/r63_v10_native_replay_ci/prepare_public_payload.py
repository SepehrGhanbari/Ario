"""Public-only synthetic receipt payload prepared from frozen V9 V2 event chain.

No signer, no secret, no user account, no service, no production policy.
All files are created in CI's disposable runner temp dir.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/"r63_v10_source_gate"))
import spend_chain_v2 as v2

V2_PIN="c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd"
DOMAIN=b"ARIO-R63-CI-PUBLIC-ONLY-SYNTHETIC-RECEIPT-2026\0"

def prepare(path:Path):
    actual=hashlib.sha256(Path(v2.__file__).read_bytes()).hexdigest()
    if actual!=V2_PIN:
        raise ValueError("frozen V9 sidecar differs from pinned bytes")
    if path.exists() and list(path.iterdir()):
        raise ValueError("refuse to overwrite prior CI output")
    path.mkdir(parents=True, exist_ok=True)
    journal=b""
    for nonce, ident in [("a"*64,"1"*64),("b"*64,"2"*64)]:
        journal,status=v2.append(journal,nonce,ident)
        if status!="NEW_NEEDS_DURABLE_APPEND":
            raise ValueError("unexpected synthetic reservation")
    state=v2.review(journal)
    legacy=b"".join(v2.canonical(list(pair))+b"\n" for pair in state.pairs)
    data={"version":"R63_CI_P256_PUBLIC_RECEIPT_1",
          "nonce":"b"*64, "identifier":"2"*64,
          "v1_sha256":hashlib.sha256(legacy).hexdigest(),
          "v2_sha256":hashlib.sha256(journal).hexdigest(),
          "v2_head":state.head,"v2_event_count":state.seq,
          "disposition":"SYNTHETIC_COMMITTED_FIXTURE"}
    body=DOMAIN+v2.canonical(data)
    (path/"payload.bin").write_bytes(body)
    (path/"v1.jsonl").write_bytes(legacy)
    (path/"v2.jsonl").write_bytes(journal)
    (path/"metadata.json").write_text(json.dumps(data,sort_keys=True,indent=2)+"\n",encoding="utf-8",newline="\n")
    print("SYNTHETIC_V9_V2_SOURCE_PIN=PASS")
    print("SYNTHETIC_V2_EVENTS="+str(state.seq))
    print("PUBLIC_RECEIPT_PAYLOAD_SHA256="+hashlib.sha256(body).hexdigest())
    print("REAL_V9_BROKER=NOT_EXECUTED")
    print("INDEPENDENT_CUSTODY=NOT_ESTABLISHED")

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: prepare_public_payload.py NEW_EMPTY_RUNNER_TMP")
    prepare(Path(sys.argv[1]))
