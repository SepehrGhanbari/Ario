"""R63 defensive persisted-receipt mutation matrix in disposable Windows CI.

All cases mutate synthetic runner-temp files only, then restore them. A failing
verification must return nonzero, while original receipt must still verify.
The expected public key pin is a *separate but same-admin local file*;
this does not establish independent custody or prevent coordinated rollback.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

def h(b):return hashlib.sha256(b).hexdigest()

def run_verify(script,root,pin):
    cmd=["pwsh","-NoProfile","-NonInteractive","-File",str(script),
         "-Mode","Verify","-Root",str(root),"-ExpectedPublicPin",pin]
    return subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)

def main(root,script):
    if os.environ.get("RUNNER_OS")!="Windows" or os.environ.get("GITHUB_REPOSITORY")!="SepehrGhanbari/Ario":
        raise RuntimeError("REFUSE_NONWINDOWS_CI")
    root=root.resolve()
    runner=Path(os.environ["RUNNER_TEMP"]).resolve()
    if runner not in root.parents: raise RuntimeError("REFUSE_OUTSIDE_RUNNER_TEMP")
    receipt=root/"receipt-public.json"
    payload=root/"payload.bin"
    pin=(root/"expected-public-pin.sha256").read_text("ascii").strip()
    if len(pin)!=64: raise RuntimeError("bad separately supplied pin")
    raw_receipt=receipt.read_bytes()
    raw_payload=payload.read_bytes()
    if run_verify(script,root,pin).returncode!=0:
        raise RuntimeError("positive control rejected before mutation")
    if run_verify(script,root,"0"*64).returncode==0:
        raise RuntimeError("bad expected pin was accepted")
    tests=1
    original=json.loads(raw_receipt)
    def write_json(record):
        receipt.write_bytes(json.dumps(record,sort_keys=True,separators=(",",":")).encode()+b"\n")
    try:
        # If a field was altered on disk, the verifying process must reject.
        bad=dict(original)
        bad["public_pin_sha256"]="0"*64
        write_json(bad)
        if run_verify(script,root,pin).returncode==0: raise RuntimeError("bad embedded pin accepted")
        tests+=1
        receipt.write_bytes(raw_receipt)
        if run_verify(script,root,pin).returncode!=0:raise RuntimeError("restore failed after pin mutation")

        bad=dict(original)
        sig=bytearray(base64.b64decode(original["signature_p1363_b64"]))
        sig[0]^=1
        bad["signature_p1363_b64"]=base64.b64encode(sig).decode("ascii")
        write_json(bad)
        if run_verify(script,root,pin).returncode==0:raise RuntimeError("mutated persisted signature accepted")
        tests+=1
        receipt.write_bytes(raw_receipt)

        bad=dict(original)
        bad["version"]="R63_BAD_RECEIPT"
        write_json(bad)
        if run_verify(script,root,pin).returncode==0:raise RuntimeError("wrong receipt version accepted")
        tests+=1
        receipt.write_bytes(raw_receipt)

        receipt.write_bytes(raw_receipt[:-8])
        if run_verify(script,root,pin).returncode==0:raise RuntimeError("truncated receipt accepted")
        tests+=1
        receipt.write_bytes(raw_receipt)

        receipt.unlink()
        if run_verify(script,root,pin).returncode==0:raise RuntimeError("missing receipt accepted")
        tests+=1
        receipt.write_bytes(raw_receipt)

        changed=bytearray(raw_payload)
        changed[-1]^=1
        payload.write_bytes(bytes(changed))
        if run_verify(script,root,pin).returncode==0:raise RuntimeError("altered source payload accepted")
        tests+=1
        payload.write_bytes(raw_payload)
    finally:
        receipt.write_bytes(raw_receipt)
        payload.write_bytes(raw_payload)
    if run_verify(script,root,pin).returncode!=0:
        raise RuntimeError("positive control rejected after mutations")
    if receipt.read_bytes()!=raw_receipt or payload.read_bytes()!=raw_payload:
        raise RuntimeError("mutation matrix failed to restore original bytes")
    print("PERSISTED_MUTATIONS_FAIL_CLOSED="+str(tests)+"/"+str(tests))
    print("POSITIVE_REPLAY_BEFORE_AND_AFTER_MUTATION=PASS")
    print("RECEIPT_SHA256="+h(raw_receipt))
    print("PUBLIC_PIN_STORAGE=LOCAL_SAME_ADMIN_NOT_INDEPENDENT")
    print("SIGNER_USE_IN_MUTATION_TEST=ZERO_BY_SOURCE_ONLY")
    print("REAL_V9_BROKER=NOT_EXECUTED")

if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: script ROOT POWERSHELL_VERIFIER")
    main(Path(sys.argv[1]),Path(sys.argv[2]).resolve())
