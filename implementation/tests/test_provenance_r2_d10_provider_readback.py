"""Offline bounded response tests. Fake reader is NOT a real GitHub connection."""
import copy
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import provenance_r2_d10_provider_readback as m

SHA = "277570d4f26afb4c69f58ec5426aff8b919d58e1"
TARGET = m.Target(270, 44392429462, SHA)

class FixtureReader:
    def __init__(self):
        pr = {"id": 128800, "number":270,"head":{"sha":SHA}}
        run = {"id": TARGET.run_id, "head_sha":SHA, "run_attempt":1,
               "workflow_id":379498305, "event":"pull_request", "status":"completed", "conclusion":"success"}
        def job(n, name):
            return {"id":n,"name":name,"run_id":TARGET.run_id,"run_attempt":1,
                    "head_sha":SHA,"status":"completed","conclusion":"success"}
        jobs={"total_count":2,"jobs":[job(135113339427,"m0-regression"),job(135113338821,"windows-differential-advisory")]}
        self.rows=[pr,run,jobs,copy.deepcopy(pr)]
        self.calls=[]
        self.error_index=None
        self.raw_override={}
    def get(self,path):
        self.calls.append(path)
        pos=len(self.calls)-1
        if pos==self.error_index:
            raise ValueError("synthetic 403")
        if pos in self.raw_override:
            return self.raw_override[pos]
        return json.dumps(self.rows[pos],sort_keys=True).encode()

class D10Tests(unittest.TestCase):
    def setUp(self):
        self.r = FixtureReader()
    def verify(self):
        return m.audit(TARGET,self.r)
    def assertUnknown(self,result):
        self.assertEqual(result['status'],'UNKNOWN')
        self.assertEqual(result['source_control_independence'],'NOT_ESTABLISHED')
        self.assertEqual(result['pytest_execution_attestation'],'NOT_ESTABLISHED')
        self.assertEqual(result['global_freshness'],'NOT_ESTABLISHED')
        self.assertEqual(result['evidence_admission'],'NOT_EVALUATED')
    def assertReject(self):
        result=self.verify(); self.assertUnknown(result)
        self.assertEqual(result['metadata_correspondence'],'UNKNOWN')
        return result
    def test_positive_is_only_correspondence(self):
        x=self.verify(); self.assertUnknown(x)
        self.assertEqual(x['metadata_correspondence'],'CONSISTENT_CALLER_SUPPLIED_READBACK')
        self.assertEqual(len(self.r.calls),4)
    def test_bound_to_fixed_paths(self):
        self.verify()
        self.assertEqual(self.r.calls,[f'/repos/{m.REPO}/pulls/270',f'/repos/{m.REPO}/actions/runs/{TARGET.run_id}',f'/repos/{m.REPO}/actions/runs/{TARGET.run_id}/jobs?per_page=100',f'/repos/{m.REPO}/pulls/270'])
    def test_invalid_target_number(self):
        self.assertUnknown(m.audit(m.Target(True,TARGET.run_id,SHA),self.r));self.assertEqual(self.r.calls,[])
    def test_invalid_target_head(self):
        self.assertUnknown(m.audit(m.Target(270,TARGET.run_id,'x'),self.r));self.assertEqual(self.r.calls,[])
    def test_invalid_reader(self):
        self.assertUnknown(m.audit(TARGET,None));self.assertEqual(self.r.calls,[])
    def test_pr_missing_id(self):
        del self.r.rows[0]['id'];self.assertReject()
    def test_pr_changes_head_between_reads(self):
        self.r.rows[3]['head']['sha']='a'*40
        self.assertEqual(self.assertReject()['reason'],'PR_HEAD_CHANGED_DURING_READBACK')
    def test_pr_changes_id_between_reads(self):
        self.r.rows[3]['id']+=1;self.assertReject()
    def test_pinned_target_stale(self):
        self.r.rows[0]['head']['sha']='b'*40; self.r.rows[3]['head']['sha']='b'*40
        self.assertReject()
    def test_run_wrong_head(self):
        self.r.rows[1]['head_sha']='f'*40;self.assertReject()
    def test_run_wrong_attempt(self):
        self.r.rows[1]['run_attempt']=0;self.assertReject()
    def test_run_not_success(self):
        self.r.rows[1]['conclusion']='failure';self.assertReject()
    def test_run_not_pull_request(self):
        self.r.rows[1]['event']='push';self.assertReject()
    def test_run_wrong_id(self):
        self.r.rows[1]['id']+=1;self.assertReject()
    def test_job_wrong_head(self):
        self.r.rows[2]['jobs'][0]['head_sha']='a'*40;self.assertReject()
    def test_job_wrong_attempt(self):
        self.r.rows[2]['jobs'][0]['run_attempt']=2;self.assertReject()
    def test_job_not_success(self):
        self.r.rows[2]['jobs'][0]['conclusion']='failure';self.assertReject()
    def test_duplicate_job_id(self):
        self.r.rows[2]['jobs'][1]['id']=self.r.rows[2]['jobs'][0]['id'];self.assertReject()
    def test_missing_required_job(self):
        self.r.rows[2]['jobs'][0]['name']='something else';self.assertReject()
    def test_empty_jobs(self):
        self.r.rows[2]={'total_count':0,'jobs':[]};self.assertReject()
    def test_partial_job_page(self):
        self.r.rows[2]['total_count']=3;self.assertReject()
    def test_more_than_one_page(self):
        self.r.rows[2]['total_count']=101;self.assertReject()
    def test_403_on_each_get(self):
        for n in range(4):
            r=FixtureReader();r.error_index=n; x=m.audit(TARGET,r)
            self.assertUnknown(x);self.assertEqual(x['reason'],'INCOMPLETE_OR_UNAVAILABLE_READBACK')
    def test_duplicate_json_key(self):
        self.r.raw_override[1]=b'{"id":44392429462,"id":44392429462}'
        self.assertReject()
    def test_json_not_object(self):
        self.r.raw_override[1]=b'[1,2,3]';self.assertReject()
    def test_nonfinite_json(self):
        self.r.raw_override[1]=b'{"id":NaN}';self.assertReject()
    def test_oversized_bytes(self):
        self.r.raw_override[1]=b'x'*(m.MAX_BYTES+1);self.assertReject()
    def test_raw_type_mismatch(self):
        self.r.raw_override[1]='notbytes';self.assertReject()
    def test_bare_non_json(self):
        self.r.raw_override[1]=b'not-json';self.assertReject()
    def test_network_missing_json(self):
        self.r.raw_override[2]=b'';self.assertReject()
    def test_later_pr_missing(self):
        self.r.raw_override[3]=b'{}';self.assertReject()
    def test_no_side_effects_on_import(self):
        import inspect
        s=inspect.getsource(m.audit)
        self.assertNotIn('urlopen',s)
        self.assertNotIn('subprocess',s)
    def test_reject_arbitrary_host_paths(self):
        # Block before any network is contacted.
        class FakeDirect(m.DirectGithubReader):
            pass
        rr=FakeDirect()
        for path in ('https://evil.example/x','/repos/SepehrGhanbari/Ario/secrets', '/repos/Other/X/pulls/270', '/repos/SepehrGhanbari/Ario/pulls/270/../../../secrets'):
            with self.assertRaises(ValueError): rr.get(path)
    def test_redirects_disabled(self):
        self.assertIsNone(m._NoRedirect().redirect_request(object(),None,302,'redirect',{},'https://example.org'))
    def test_aba_pr_head_can_escape_two_snapshots(self):
        # An unseen A->B->A transition is observationally equivalent to A->A.
        a = self.verify()
        self.assertEqual(a['metadata_correspondence'],'CONSISTENT_CALLER_SUPPLIED_READBACK')
        self.assertEqual(a['global_freshness'],'NOT_ESTABLISHED')

    def test_forged_reader_same_json_unobservable(self):
        # Fake response bytes and externally acquired bytes look identical here.
        x = self.verify()
        self.assertEqual(x['github_transport_authentication'],'NOT_ATTESTED_BY_THIS_ADAPTER')
        self.assertUnknown(x)

    def test_pr_head_wrong_type_rejected(self):
        self.r.rows[0]['head']['sha']=True
        self.assertReject()

    def test_static_cannot_claim_remote_custody(self):
        x=self.verify();self.assertEqual(x['externally_pinned_custodian'],'NOT_ESTABLISHED')
        self.assertEqual(x['github_transport_authentication'],'NOT_ATTESTED_BY_THIS_ADAPTER')

if __name__=='__main__': unittest.main()
