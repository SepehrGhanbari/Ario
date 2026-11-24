import unittest
from datetime import timedelta
from copy import deepcopy
import gcs_pilot as p

PIN={"bucket":"ario-r63-lab-test-12345678","project_number":"12345","deployment":"c"*32,"min_retention_seconds":86400}
NONCE="a"*64
class Reply:
    def __init__(self,code,data=None,content=b""):
        self.status_code=code;self.data=data;self.content=content
    def json(self):return deepcopy(self.data)
class Fake:
    """Contract double, NOT the Google Cloud service or an IAM attestation."""
    def __init__(self):
        self.calls=[];self.obj=None;self.lose=False;self.fail_read=False
        self.meta={"name":PIN["bucket"],"projectNumber":PIN["project_number"],
                   "retentionPolicy":{"isLocked":True,"retentionPeriod":"86400"},
                   "iamConfiguration":{"uniformBucketLevelAccess":{"enabled":True},"publicAccessPrevention":"enforced"}}
        self.permissions=sorted(p.REQUIRED)
        self.bad_bytes=False;self.expiry=p.now()+timedelta(days=1)
    def request(self,method,url,**kw):
        self.calls.append((method,url,kw))
        if "/iam/testPermissions" in url:return Reply(200,{"permissions":self.permissions})
        if method=="POST":
            assert kw["params"]["ifGenerationMatch"]=="0"
            if self.obj is not None:return Reply(412,{})
            self.obj=(kw["params"]["name"],kw["data"])
            if self.lose:raise TimeoutError("simulated committed then lost reply")
            return Reply(200,{"bucket":PIN["bucket"],"name":self.obj[0],"generation":"456"})
        if "/o/" in url:
            if self.fail_read:return Reply(503,{})
            assert kw["params"]["ifGenerationMatch"]=="456"
            if kw["params"].get("alt")=="media":
                return Reply(200,content=b"changed" if self.bad_bytes else self.obj[1])
            return Reply(200,{"bucket":PIN["bucket"],"name":self.obj[0],"generation":"456",
                              "retentionExpirationTime":self.expiry.isoformat()})
        return Reply(200,self.meta)
    def pilot(self):return p.Pilot(self.request,PIN)
class Tests(unittest.TestCase):
    def setUp(self):self.f=Fake()
    def verdict(self,write=True):return self.f.pilot().run(NONCE,write)["verdict"]
    def test_read_only(self):
        self.assertEqual(self.verdict(False),"BUCKET_AND_CALLER_PREFLIGHT_ONLY")
        self.assertTrue(all(c[0]=="GET" for c in self.f.calls))
    def test_create_readback(self):
        self.assertEqual(self.verdict(),"SYNTHETIC_MARKER_CREATED_READBACK_ONLY")
        self.assertEqual(self.f.obj[1],p.marker(PIN,NONCE))
    def test_rollback_replay(self):
        self.assertEqual(self.verdict(),"SYNTHETIC_MARKER_CREATED_READBACK_ONLY")
        self.assertEqual(self.verdict(),"HOLD_EXTERNAL_SPENT")
    def test_lost_ack(self):
        self.f.lose=True
        self.assertEqual(self.verdict(),"HOLD_PROVIDER_OR_ACK_UNCERTAIN")
        self.f.lose=False
        self.assertEqual(self.verdict(),"HOLD_EXTERNAL_SPENT")
    def test_wrong_project(self):
        self.f.meta["projectNumber"]="99999"
        self.assertEqual(self.verdict(),"HOLD_BUCKET_IDENTITY_MISMATCH")
    def test_unlocked(self):
        self.f.meta["retentionPolicy"]["isLocked"]=False
        self.assertEqual(self.verdict(),"HOLD_BUCKET_RETENTION_NOT_LOCKED")
    def test_short_policy(self):
        self.f.meta["retentionPolicy"]["retentionPeriod"]="60"
        self.assertEqual(self.verdict(),"HOLD_BUCKET_RETENTION_NOT_LOCKED")
    def test_overprivileged(self):
        self.f.permissions+=["storage.objects.delete"]
        self.assertEqual(self.verdict(),"HOLD_CUSTODY_IAM_SCOPE")
    def test_missing_permission(self):
        self.f.permissions.remove("storage.objects.get")
        self.assertEqual(self.verdict(),"HOLD_CUSTODY_IAM_SCOPE")
    def test_public_bucket(self):
        self.f.meta["iamConfiguration"]["publicAccessPrevention"]="inherited"
        self.assertEqual(self.verdict(),"HOLD_BUCKET_ACCESS_CONFIGURATION")
    def test_expired_readback(self):
        self.f.expiry=p.now()-timedelta(seconds=1)
        self.assertEqual(self.verdict(),"HOLD_RETENTION_READBACK_TOO_SHORT")
    def test_readback_changed(self):
        self.f.bad_bytes=True
        self.assertEqual(self.verdict(),"HOLD_EXACT_BYTES_READBACK")
    def test_readback_unavailable(self):
        self.f.fail_read=True
        self.assertEqual(self.verdict(),"HOLD_METADATA_READBACK")
    def test_invalid_nonce(self):
        self.assertEqual(self.f.pilot().run("bad",True)["verdict"],"HOLD_BAD_NONCE")
    def test_nonlab_bucket(self):
        with self.assertRaises(p.Hold):p.Pilot(self.f.request,{**PIN,"bucket":"real-prod-data"})
    def test_global_nonce_key(self):
        self.assertEqual(p.object_name(PIN,NONCE),p.object_name(PIN,NONCE))
        self.assertNotEqual(p.object_name(PIN,NONCE),p.object_name(PIN,"b"*64))
    def test_never_authorizes(self):
        answer=self.f.pilot().run(NONCE,True)
        self.assertEqual(answer["authority"],"NONE")
        self.assertEqual(answer["native_CNG"],"NOT_CALLED")
        self.assertEqual(answer["independent_admin"],"NOT_ESTABLISHED")
        self.assertEqual(answer["production"],"NO_GO")
if __name__=="__main__":unittest.main(verbosity=2)
