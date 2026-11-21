"""One-time PUBLIC SYNTHETIC OpenTimestamps calendar test. NO real Ario data.
A calendar receipt is pending, NOT Bitcoin-confirmed, NOT a verified trust floor.
"""
from __future__ import annotations
import hashlib,json,os,secrets,sys,urllib.request,urllib.parse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'r63_g3_witness_ci'))
import spend_chain_v2 as v2
PIN="c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd"
URL="https://alice.btc.calendar.opentimestamps.org/digest"
def main():
    if not (os.environ.get("GITHUB_ACTIONS")=="true"
        and os.environ.get("GITHUB_REPOSITORY")=="SepehrGhanbari/Ario"
        and os.environ.get("R63_G4_ONE_TIME_PUBLIC_SYNTHETIC_ONLY")=="I_ACCEPT_PERMANENT_PUBLIC_RANDOM_DIGEST"):
        raise RuntimeError("REFUSE_UNAUTHORIZED_EXTERNAL_PUBLIC_SUBMISSION")
    if hashlib.sha256(Path(v2.__file__).read_bytes()).hexdigest()!=PIN:
        raise RuntimeError("FROZEN_SOURCE_MISMATCH")
    journal=b""
    for n,k in [("a"*64,"1"*64),("b"*64,"2"*64),("c"*64,"3"*64)]:
        journal,status=v2.append(journal,n,k)
        if status!="NEW_NEEDS_DURABLE_APPEND":raise RuntimeError("BAD_SYNTHETIC_CHAIN")
    state=v2.review(journal)
    fake={"domain":"ARIO_R63_G4_CALENDAR_PROBE_ONLY","synthetic":True,
          "seq":state.seq,"head":state.head,"random_salt":secrets.token_hex(32)}
    payload=json.dumps(fake,sort_keys=True,separators=(",",":")).encode("ascii")
    digest=hashlib.sha256(payload).digest()
    dest=Path("r63-g4-ots-response.bin")
    report=Path("r63-g4-ots-report.json")
    if dest.exists() or report.exists():raise RuntimeError("REFUSE_OVERWRITE")
    meta={"mode":"RESEARCH_ONLY_SYNTHETIC_PUBLIC_DIGEST","status":"HOLD",
          "calendar":URL,"checkpoint":fake,"submitted_digest_sha256":digest.hex(),
          "bitcoin_confirmed":False,"independent_latest_floor":False,
          "checkpoint_source_authentication":"NOT_ESTABLISHED",
          "real_keys_or_signer":"NOT_TOUCHED"}
    try:
        req=urllib.request.Request(URL,data=digest,method="POST",headers={
             "Accept":"application/vnd.opentimestamps.v1"})
        with urllib.request.urlopen(req,timeout=22) as response:
            url=response.geturl()
            if urllib.parse.urlsplit(url).hostname!="alice.btc.calendar.opentimestamps.org":
                raise RuntimeError("UNEXPECTED_CALENDAR_REDIRECT")
            body=response.read(65537)
            if response.status!=200 or not 8<=len(body)<=65536:
                raise RuntimeError("UNEXPECTED_CALENDAR_RESPONSE")
            dest.write_bytes(body)
            meta["receipt_sha256"]=hashlib.sha256(body).hexdigest()
            meta["receipt_size"]=len(body)
            meta["http_status"]=response.status
            meta["status"]="EXTERNAL_CALENDAR_RESPONSE_RECEIVED_PENDING_ONLY"
    except Exception as e:
        meta["error_type"]=type(e).__name__
        meta["status"]="HOLD_EXTERNAL_CALENDAR_UNAVAILABLE_OR_UNVERIFIED"
    report.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    print("G4_OTS_STATUS="+meta["status"])
    print("G4_CALENDAR_RECEIPT_FINAL_BITCOIN_ATTESTATION=NOT_ESTABLISHED")
    print("G4_EXTERNAL_VERIFIER_FLOOR=NOT_ESTABLISHED")
    if meta["status"]!="EXTERNAL_CALENDAR_RESPONSE_RECEIVED_PENDING_ONLY":raise SystemExit(1)
if __name__=="__main__":main()
