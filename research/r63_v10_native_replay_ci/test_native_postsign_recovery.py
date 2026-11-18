"""CI-only post-sign process-exit recovery test with disposable native CNG key.

Not native V9. A PowerShell worker exits 73 after key cleanup; no mid-NCrypt
crash, loss of power, separate administrative custody or V9 witness service.
"""
from __future__ import annotations
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
PREPARE=HERE/"prepare_public_payload.py"
BINDING=HERE/"verify_durable_snapshot.py"
SIGNER=HERE/"Invoke-DisposableCrashSigner.ps1"
VERIFIER=HERE/"Invoke-NativePublicReceipt.ps1"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def require(condition,message):
    if not condition:raise RuntimeError(message)

def run(args,timeout=120):
    return subprocess.run(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,timeout=timeout)

def replay(root,pin):
    receipt=root/"receipt-public.json"
    if not receipt.is_file():
        return b"HOLD_UNCERTAIN\n"
    cmd=["pwsh","-NoProfile","-NonInteractive","-File",str(VERIFIER),
         "-Mode","Verify","-Root",str(root),"-ExpectedPublicPin",pin]
    check=run(cmd,timeout=75)
    if check.returncode:
        return b"HOLD_UNCERTAIN\n"
    require(b"SEPARATE_PUBLIC_ONLY_VERIFIER_PASS" in check.stdout,
            "no positive signature validation marker")
    return receipt.read_bytes()

def scenario(base,name):
    root=base/name
    require(not root.exists(),"synthetic fixture root unexpectedly exists")
    p=run([sys.executable,"-B",str(PREPARE),str(root)])
    require(p.returncode==0,"fixture prep failed: "+repr(p.stderr[-1500:]))
    before={n:sha((root/n).read_bytes()) for n in
            ("v1.jsonl","v2.jsonl","payload.bin","metadata.json")}
    worker=run(["pwsh","-NoProfile","-NonInteractive","-File",str(SIGNER),
                "-Scenario",name,"-Root",str(root)])
    require(worker.returncode==73,
            "expected sign-worker exit 73, got "+str(worker.returncode)+
            " stderr "+repr(worker.stderr[-1200:]))
    for item in (b"CNG_ENTER=1",b"CNG_RETURN=1",
                 b"KEY_ABSENT_AFTER_DELETE=True",
                 b"FORCED_POSTSIGN_PROCESS_EXIT_AFTER_KEY_CLEANUP=73"):
        require(item in worker.stdout,"missing native use marker: "+repr(item)+
                " output "+repr(worker.stdout[-800:]))
    intent=(root/"use-entered.json").read_bytes()
    returned=(root/"use-returned.json").read_bytes()
    i=json.loads(intent);j=json.loads(returned)
    require(i["pid"]==j["pid"] and
            type(j["enter"]) is int and j["enter"]==j["returned"]==1,
            "sign-use enter/return marker mismatch")
    pin=(root/"expected-public-pin.sha256").read_text(encoding="ascii").strip()
    require(len(pin)==64,"self-administered expected public pin missing")
    receipt=root/"receipt-public.json"
    stored=receipt.read_bytes() if receipt.is_file() else None
    require((stored is not None)==(name=="AfterReceiptBeforeAck"),
            "receipt unexpectedly absent/present")
    check=run([sys.executable,"-B",str(BINDING),str(root)])
    require(check.returncode==0,
            "journal/payload binding failed: "+repr(check.stderr[-800:]))
    for count in (2,8,16):
        with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:
            responses=list(pool.map(lambda _: replay(root,pin), range(count)))
        expected=stored if stored is not None else b"HOLD_UNCERTAIN\n"
        require(all(x==expected for x in responses),
                "unexpected concurrent replay/HOLD response for "+name+
                " count "+str(count))
    require((root/"use-entered.json").read_bytes()==intent and
            (root/"use-returned.json").read_bytes()==returned,
            "replay changed sign-use markers")
    for n,digest in before.items():
        require(sha((root/n).read_bytes())==digest,
                "replay mutated journal/payload/metadata "+n)
    if stored is not None:
        require(receipt.read_bytes()==stored,"stored receipt bytes changed")
        mutated=bytearray(stored)
        mutated[-12]^=1
        receipt.write_bytes(bytes(mutated))
        try:
            require(replay(root,pin)==b"HOLD_UNCERTAIN\n",
                    "corrupt persisted receipt accepted")
        finally:
            receipt.write_bytes(stored)
        require(replay(root,pin)==stored,"valid receipt replay not restored")
    print("SCENARIO="+name+" PROCESS_EXIT=73 RETRIES=26 "+(
          "EXACT_PUBLIC_RECEIPT_REPLAY" if stored is not None else "HOLD_UNCERTAIN"))
    return {
      "window":name,"worker_exit":worker.returncode,
      "worker_pid":i["pid"],"ncrypt_enter_reported":1,"ncrypt_return_reported":1,
      "self_administered_pin_only":True,"synthetic_key_absent_after_cleanup":True,
      "v1_v2_unchanged":True,"retries":26,
      "receipt_present":stored is not None,
      "receipt_sha256":sha(stored) if stored is not None else None,
      "recovery":"EXACT_SAVED_PUBLIC_VERIFIED_RECEIPT" if stored is not None else "HOLD_UNCERTAIN",
      "native_v9_broker":"NOT_EXECUTED"
    }

def main():
    require(os.getenv("RUNNER_OS")=="Windows" and
            os.getenv("GITHUB_REPOSITORY")=="SepehrGhanbari/Ario",
            "refuse non-Windows or non-Ario CI execution")
    base=Path(os.environ["RUNNER_TEMP"]).resolve()/"r63-v11-ci-postsign-abort"
    require(not base.exists(),"refuse to overwrite previous evidence")
    base.mkdir()
    cases=[scenario(base,name) for name in
           ("AfterSignBeforeReceipt","AfterReceiptBeforeAck")]
    report={
      "status":"RESEARCH_ONLY_SYNTHETIC_NATIVE_CNG_CRASH_WINDOWS",
      "scenarios":cases,
      "total_retries":sum(c["retries"] for c in cases),
      "signer_crash_during_ncrypt":"NOT_TESTED",
      "native_v9_witness_rpc":"NOT_EXECUTED",
      "hardware_key_or_true_power_loss":"NOT_TESTED",
      "external_nonrollback_custody":"NOT_ESTABLISHED",
      "complete_native_sign_use_telemetry":"NOT_ESTABLISHED",
      "no_main_or_production_changes":True,
    }
    (base/"report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("R63_V11_EPHEMERAL_CNG_POSTSIGN_ABORT=PASS")
    print("TOTAL_RETRIES="+str(report["total_retries"]))

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("FAIL_CLOSED: "+type(exc).__name__+": "+str(exc),file=sys.stderr)
        raise SystemExit(1)
