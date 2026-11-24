"""R63 G9 external GCS retention pilot. RESEARCH_ONLY; never calls a signer.

Live mode is opt-in and writes ONLY one synthetic digest marker to an already
provisioned dedicated bucket. Never creates/locks/deletes a bucket, changes IAM,
or generates any keys. TLS/ADC provider readback is not signed custodian approval.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
import re
from urllib.parse import quote
import sys

EPOCH = "research_nov_2026_no_signer"
SEQ3 = "6e1d74f7860e0173b9b049487a6a89428439a987809cf363fa27503ae0b06ea1"
SEQ4 = "52e1f33cf8bcf325a2cb817abe16473aa2e6a799fc76406b8cf831b912fd6d8c"
API = "https://storage.googleapis.com"
REQUIRED = {"storage.buckets.get", "storage.objects.create", "storage.objects.get"}
FORBIDDEN = {"storage.buckets.update", "storage.buckets.delete",
             "storage.buckets.setIamPolicy", "storage.objects.delete",
             "storage.objects.update", "storage.objects.move",
             "storage.objects.setRetention", "storage.objects.overrideUnlockedRetention"}
HEX = re.compile(r"[0-9a-f]{64}\Z")
class Hold(ValueError): pass
def need(ok, reason):
    if not ok: raise Hold(reason)
def canon(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")
def sha(raw): return hashlib.sha256(raw).hexdigest()
def now(): return datetime.now(timezone.utc)
def timestamp(s):
    return datetime.fromisoformat(s.replace("Z","+00:00"))
def positive(s):
    return type(s) is str and re.fullmatch(r"[1-9][0-9]{0,29}",s) is not None
def pin_check(pin):
    need(type(pin) is dict and set(pin)=={"bucket","project_number","deployment","min_retention_seconds"}, "HOLD_BAD_OPERATOR_PIN")
    need(type(pin["bucket"]) is str and re.fullmatch(r"ario-r63-lab-[a-z0-9-]{8,48}",pin["bucket"]) is not None, "HOLD_NONLAB_BUCKET")
    need(positive(pin["project_number"]), "HOLD_PROJECT_PIN")
    need(type(pin["deployment"]) is str and re.fullmatch(r"[0-9a-f]{32}",pin["deployment"]) is not None, "HOLD_DEPLOYMENT_PIN")
    need(type(pin["min_retention_seconds"]) is int and 86400 <= pin["min_retention_seconds"] <= 2592000, "HOLD_PILOT_RETENTION_RANGE")
def checked_bucket(meta,pin):
    need(meta.get("name")==pin["bucket"] and meta.get("projectNumber")==pin["project_number"], "HOLD_BUCKET_IDENTITY_MISMATCH")
    r=meta.get("retentionPolicy",{})
    need(r.get("isLocked") is True and positive(r.get("retentionPeriod")) and int(r["retentionPeriod"])>=pin["min_retention_seconds"], "HOLD_BUCKET_RETENTION_NOT_LOCKED")
    access=meta.get("iamConfiguration",{})
    need(access.get("uniformBucketLevelAccess",{}).get("enabled") is True and access.get("publicAccessPrevention")=="enforced", "HOLD_BUCKET_ACCESS_CONFIGURATION")
def checked_permissions(data):
    granted=data.get("permissions",[])
    need(type(granted) is list and all(type(x) is str for x in granted), "HOLD_BAD_IAM_REPLY")
    s=set(granted)
    need(REQUIRED<=s and not (FORBIDDEN&s), "HOLD_CUSTODY_IAM_SCOPE")
def object_name(pin, nonce):
    need(type(nonce) is str and HEX.fullmatch(nonce), "HOLD_BAD_NONCE")
    # Global nonce within separately enrolled deployment+epoch. Do NOT key on
    # payload hash, signer pin or case, which would permit nonce scope splitting.
    return "research-only/"+pin["deployment"]+"/"+sha(EPOCH.encode())+"/spent/"+nonce
def marker(pin,nonce):
    return canon({"version":"ARIO_R63_G9_WORM_SYNTHETIC_V1","deployment":pin["deployment"],
                  "epoch":EPOCH,"nonce":nonce,"previous":{"seq":3,"head":SEQ3},
                  "candidate":{"seq":4,"head":SEQ4},"authority":"NONE","production":"NO_GO"})
class Pilot:
    def __init__(self, request,pin):
        pin_check(pin)
        self.request=request;self.pin=dict(pin)
        self.bucket=API+"/storage/v1/b/"+quote(pin["bucket"],safe="")
    def call(self,method,url,**kwargs):
        return self.request(method,url,timeout=15,allow_redirects=False,**kwargs)
    def preflight(self):
        r=self.call("GET",self.bucket)
        need(r.status_code==200,"HOLD_BUCKET_READ_UNAVAILABLE")
        checked_bucket(r.json(),self.pin)
        r=self.call("GET",self.bucket+"/iam/testPermissions",params=[("permissions",p) for p in sorted(REQUIRED|FORBIDDEN)])
        need(r.status_code==200,"HOLD_IAM_READ_UNAVAILABLE")
        checked_permissions(r.json())
    def run(self,nonce,write=False):
        result={"scope":"RESEARCH_ONLY","authority":"NONE","native_CNG":"NOT_CALLED",
                "independent_admin":"NOT_ESTABLISHED","independent_latest":"NOT_ESTABLISHED",
                "signed_custodian_ack":"NOT_IMPLEMENTED","production":"NO_GO"}
        try:
            self.preflight()
            if not write:
                return {**result,"verdict":"BUCKET_AND_CALLER_PREFLIGHT_ONLY"}
            name=object_name(self.pin,nonce); raw=marker(self.pin,nonce)
            upload=API+"/upload/storage/v1/b/"+quote(self.pin["bucket"],safe="")+"/o"
            r=self.call("POST",upload,params={"uploadType":"media","name":name,"ifGenerationMatch":"0"},
                        data=raw,headers={"Content-Type":"application/json"})
            if r.status_code==412:
                return {**result,"verdict":"HOLD_EXTERNAL_SPENT"}
            if r.status_code not in (200,201):
                return {**result,"verdict":"HOLD_WRITE_RESULT_UNCERTAIN"}
            meta=r.json(); gen=meta.get("generation")
            need(meta.get("bucket")==self.pin["bucket"] and meta.get("name")==name and positive(gen), "HOLD_WRITE_IDENTITY")
            path=self.bucket+"/o/"+quote(name,safe="")
            m=self.call("GET",path,params={"ifGenerationMatch":gen})
            need(m.status_code==200,"HOLD_METADATA_READBACK")
            md=m.json()
            need(md.get("generation")==gen and md.get("bucket")==self.pin["bucket"] and md.get("name")==name,"HOLD_READBACK_IDENTITY")
            expiration=timestamp(md["retentionExpirationTime"])
            need(expiration>=now()+timedelta(seconds=self.pin["min_retention_seconds"]-120),"HOLD_RETENTION_READBACK_TOO_SHORT")
            b=self.call("GET",path,params={"alt":"media","ifGenerationMatch":gen})
            need(b.status_code==200 and b.content==raw,"HOLD_EXACT_BYTES_READBACK")
            # Check policy again. This does not prove cloud project/admin independence.
            self.preflight()
            return {**result,"verdict":"SYNTHETIC_MARKER_CREATED_READBACK_ONLY",
                    "generation":gen,"marker_sha256":sha(raw),"retained_until":expiration.isoformat()}
        except Hold as e:
            return {**result,"verdict":str(e)}
        except Exception:
            # Do not log provider exceptions, secrets or authorization headers.
            return {**result,"verdict":"HOLD_PROVIDER_OR_ACK_UNCERTAIN"}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--operator-pin",required=True,help="operator-owned NON-secret JSON, not a publisher-provided pin")
    p.add_argument("--nonce",default="a"*64)
    p.add_argument("--execute-one-synthetic-write",action="store_true")
    args=p.parse_args()
    try:
        with open(args.operator_pin,encoding="utf-8") as f: pin=json.load(f)
        pin_check(pin)
        # Local ADC, never copy a token to the chat/repo. No credential generation here.
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        creds,_=google.auth.default(scopes=["https://www.googleapis.com/auth/devstorage.read_write"])
        with AuthorizedSession(creds,max_refresh_attempts=0) as session:
            answer=Pilot(session.request,pin).run(args.nonce,args.execute_one_synthetic_write)
    except Exception:
        answer={"verdict":"HOLD_CONFIGURATION_OR_ADC_UNAVAILABLE","authority":"NONE","production":"NO_GO"}
    print(json.dumps(answer,sort_keys=True))
    return 0 if answer["verdict"] in ("BUCKET_AND_CALLER_PREFLIGHT_ONLY","SYNTHETIC_MARKER_CREATED_READBACK_ONLY") else 2
if __name__=="__main__":sys.exit(main())
