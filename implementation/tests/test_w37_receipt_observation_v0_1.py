#!/usr/bin/env python3
"""W37 deterministic stdlib tests against exact Git-blob copies of two Ario modules."""
from __future__ import annotations
import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "fixtures" / "w37_w35_public"
from research.w37_receipt_observation_v0_1 import observe_pair, FILES
from ledger_observation_adapter import observe_ledger
from ledger_audit_bridge import verify_observation_manifest

class W37Tests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.ledger = self.tmp/'events.jsonl'
        self.ledger.write_bytes((ROOT/'sample_events.jsonl').read_bytes())
        self.root = self.tmp/'W36'
        self.root.mkdir()
        for name,_ in FILES.values():
            shutil.copyfile(ROOT/name, self.root/name)

    def check_no_authority(self, r):
        self.assertFalse(r['may_use'])
        self.assertEqual(r['use_disposition'],'SUSPENDED')
        self.assertFalse(r['actual_ario_events_attested_by_w35'])
        self.assertEqual(r['cross_artifact_binding'],'NOT_ESTABLISHED')
        self.assertEqual(r['evidence_admission'],'NOT_EVALUATED')
        self.assertEqual(r['historical_event_truth'],'UNKNOWN')
        self.assertEqual(r['independent_event_inventory'],'NOT_ESTABLISHED')
        self.assertFalse(r['m0_evidence_created'])
        self.assertFalse(r['audit_engine_called'])
        self.assertEqual(r['signer_authority'],'NONE')
        self.assertEqual(r['trust_activation'],'NO_GO')
        self.assertEqual(r['genesis'],'NO_GO')
        self.assertEqual(r['production'],'NO_GO')

    def assert_refusal(self,r):
        self.assertEqual(r['result'],'UNKNOWN_OR_REJECTED_INPUT')
        self.check_no_authority(r)

    def test_01_legitimate_separate_observations(self):
        before = self.ledger.read_bytes()
        r=observe_pair(self.ledger,w36_inputs=self.root)
        self.assertEqual(r['result'],'SEPARATE_VALID_OBSERVATIONS')
        self.assertEqual(r['receipt_status'],'VERIFIED_SYNTHETIC_INCLUSION')
        self.assertEqual(r['ario_observation_status'],'OBSERVED')
        self.assertEqual(r['ario_bridge_status'],'OBSERVED')
        self.assertEqual(r['ario_observation_count'],2)
        self.assertNotEqual(r['w35_checkpoint_sha256'],r['ario_ledger_sha256'])
        self.assertFalse(r['artifact_byte_equality'])
        self.assertEqual(self.ledger.read_bytes(),before)
        self.check_no_authority(r)

    def test_02_claim_external_binding_ignored(self):
        for claim in ('CLEARED','ADMITTED','CONDITIONALLY_USABLE','proof attests Ario ledger','2202c78bf61138253e13d926733338fedd4b205520619bb6b5083ce9cacf8327'):
            r=observe_pair(self.ledger,w36_inputs=self.root,claimed_external_bind=claim)
            self.assertTrue(r['claimed_binding_ignored'])
            self.check_no_authority(r)

    def test_03_tamper_checkpoint(self):
        p=self.root/'checkpoint.PUBLIC_SYNTHETIC.json';p.write_bytes(p.read_bytes()+b'\n')
        r=observe_pair(self.ledger,w36_inputs=self.root)
        self.assertEqual(r['receipt_status'],'INVALID_OR_UNVERIFIED_RECEIPT')
        self.assertEqual(r['receipt_reason'],'CHECKPOINT_BYTES_MISMATCH')
        self.assert_refusal(r)

    def test_04_tamper_proof(self):
        p=self.root/'checkpoint.PUBLIC_SYNTHETIC.json.proof';b=p.read_bytes();p.write_bytes(b[:-1]+bytes([b[-1]^1]))
        r=observe_pair(self.ledger,w36_inputs=self.root)
        self.assertEqual(r['receipt_reason'],'PROOF_BYTES_MISMATCH')
        self.assert_refusal(r)

    def test_05_tamper_pubkey(self):
        p=self.root/'w35-lab-submitter.pub';p.write_bytes(p.read_bytes()+b' ')
        r=observe_pair(self.ledger,w36_inputs=self.root)
        self.assertEqual(r['receipt_reason'],'SUBMITTER_KEY_FILE_MISMATCH')
        self.assert_refusal(r)

    def test_06_tamper_policy(self):
        p=self.root/'sigsum-test1-2025.policy';p.write_bytes(p.read_bytes()+b'\n')
        r=observe_pair(self.ledger,w36_inputs=self.root)
        self.assertEqual(r['receipt_reason'],'UNPINNED_POLICY')
        self.assert_refusal(r)

    def test_07_missing_proof(self):
        (self.root/'checkpoint.PUBLIC_SYNTHETIC.json.proof').unlink()
        r=observe_pair(self.ledger,w36_inputs=self.root)
        self.assert_refusal(r)
        self.assertEqual(r['receipt_status'],'INVALID_OR_UNVERIFIED_RECEIPT')

    def test_08_symlink_proof(self):
        p=self.root/'checkpoint.PUBLIC_SYNTHETIC.json.proof';src=self.tmp/'real-proof'
        p.rename(src)
        try: p.symlink_to(src)
        except OSError: self.skipTest('symlink privileges unsupported')
        self.assert_refusal(observe_pair(self.ledger,w36_inputs=self.root))

    def test_09_oversize_proof(self):
        p=self.root/'checkpoint.PUBLIC_SYNTHETIC.json.proof';p.write_bytes(b'z'*(64*1024+1))
        self.assert_refusal(observe_pair(self.ledger,w36_inputs=self.root))

    def test_10_unknown_event_ledger(self):
        self.ledger.write_bytes(b'{"event":"NOT_IN_ARIO","timestamp":"t"}\n')
        r=observe_pair(self.ledger,w36_inputs=self.root)
        self.assertEqual(r['ario_observation_status'],'UNKNOWN')
        self.assert_refusal(r)

    def test_11_incomplete_ledger_line(self):
        self.ledger.write_bytes(b'{"event":"TASK_STARTED","timestamp":"t"}')
        self.assert_refusal(observe_pair(self.ledger,w36_inputs=self.root))

    def test_12_bad_ledger_json(self):
        self.ledger.write_bytes(b'not-json\n')
        self.assert_refusal(observe_pair(self.ledger,w36_inputs=self.root))

    def test_13_no_ledger(self):
        self.ledger.unlink()
        self.assert_refusal(observe_pair(self.ledger,w36_inputs=self.root))

    def test_14_empty_ledger(self):
        self.ledger.write_bytes(b'')
        self.assert_refusal(observe_pair(self.ledger,w36_inputs=self.root))

    def test_15_old_manifest_after_event_append(self):
        manifest=observe_ledger(self.ledger)
        with self.ledger.open('ab') as f:
            f.write(b'{"event":"TASK_STARTED","timestamp":"2026-11-21T00:01:00Z"}\n')
        r=observe_pair(self.ledger,w36_inputs=self.root,supplied_manifest=manifest)
        self.assertEqual(r['ario_bridge_status'],'REJECTED')
        self.assert_refusal(r)

    def test_16_old_manifest_after_same_size_tamper(self):
        manifest=observe_ledger(self.ledger)
        data=self.ledger.read_bytes()
        self.ledger.write_bytes(data.replace(b'COMPLETED',b'COMPLETEX'))
        r=observe_pair(self.ledger,w36_inputs=self.root,supplied_manifest=manifest)
        self.assertEqual(r['ario_bridge_status'],'REJECTED')
        self.assert_refusal(r)

    def test_17_manifest_status_forged(self):
        manifest=observe_ledger(self.ledger)
        manifest['observations'][1]['reported_status']='SIGNED_PRODUCTION_READY'
        r=observe_pair(self.ledger,w36_inputs=self.root,supplied_manifest=manifest)
        self.assertEqual(r['ario_bridge_status'],'REJECTED')
        self.assert_refusal(r)

    def test_18_manifest_extra_evidence_field(self):
        manifest=observe_ledger(self.ledger)
        manifest['Evidence']={'status':'ADMITTED'}
        r=observe_pair(self.ledger,w36_inputs=self.root,supplied_manifest=manifest)
        self.assertEqual(r['ario_bridge_status'],'REJECTED')
        self.assert_refusal(r)

    def test_19_manifest_duplicate_record(self):
        manifest=observe_ledger(self.ledger)
        manifest['observations'].append(copy.deepcopy(manifest['observations'][0]))
        r=observe_pair(self.ledger,w36_inputs=self.root,supplied_manifest=manifest)
        self.assertEqual(r['ario_bridge_status'],'REJECTED')
        self.assert_refusal(r)

    def test_20_manifest_float_line(self):
        manifest=observe_ledger(self.ledger)
        manifest['observations'][0]['line']=1.0
        r=observe_pair(self.ledger,w36_inputs=self.root,supplied_manifest=manifest)
        self.assertEqual(r['ario_bridge_status'],'REJECTED')
        self.assert_refusal(r)

    def test_21_manifest_bool_line(self):
        manifest=observe_ledger(self.ledger)
        manifest['observations'][0]['line']=True
        r=observe_pair(self.ledger,w36_inputs=self.root,supplied_manifest=manifest)
        self.assertEqual(r['ario_bridge_status'],'REJECTED')
        self.assert_refusal(r)

    def test_22_manifest_unknown(self):
        r=observe_pair(self.ledger,w36_inputs=self.root,supplied_manifest={'status':'UNKNOWN'})
        self.assertEqual(r['ario_bridge_status'],'UNKNOWN')
        self.assert_refusal(r)

    def test_23_ledger_path_is_symlink(self):
        src=self.tmp/'ledger-real';self.ledger.rename(src)
        try: self.ledger.symlink_to(src)
        except OSError: self.skipTest('symlink privileges unsupported')
        self.assert_refusal(observe_pair(self.ledger,w36_inputs=self.root))

    def test_24_invalid_receipt_does_not_contaminate_ledger(self):
        original=self.ledger.read_bytes()
        p=self.root/'checkpoint.PUBLIC_SYNTHETIC.json.proof';p.write_bytes(b'bad')
        r=observe_pair(self.ledger,w36_inputs=self.root)
        self.assertEqual(r['ario_bridge_status'],'OBSERVED')
        self.assert_refusal(r)
        self.assertEqual(self.ledger.read_bytes(),original)

    def test_25_untrusted_signed_presentation_is_not_upgraded(self):
        r=observe_pair(self.ledger,w36_inputs=self.root,claimed_external_bind='VERIFIED_SYNTHETIC_INCLUSION')
        self.check_no_authority(r)

    def test_26_positive_observations_do_not_mean_historical_completeness(self):
        r=observe_pair(self.ledger,w36_inputs=self.root)
        self.assertEqual(r['result'],'SEPARATE_VALID_OBSERVATIONS')
        self.assertEqual(r['independent_event_inventory'],'NOT_ESTABLISHED')
        self.assertEqual(r['snapshot_freshness'],'NOT_CHECKED')
        self.check_no_authority(r)

    def test_27_tampering_report_locators_cannot_promote(self):
        m=observe_ledger(self.ledger)
        m['observations'][0]['record_sha256']='f'*64
        self.assert_refusal(observe_pair(self.ledger,w36_inputs=self.root,supplied_manifest=m))

    def test_28_current_manifest_only_checks_current_read(self):
        m=observe_ledger(self.ledger)
        self.assertEqual(verify_observation_manifest(m,self.ledger)['status'],'OBSERVED')
        r=observe_pair(self.ledger,w36_inputs=self.root,supplied_manifest=m)
        self.assertEqual(r['result'],'SEPARATE_VALID_OBSERVATIONS')
        self.check_no_authority(r)

    def test_29_original_imports_resolve_to_installed_implementation(self):
        import ledger_observation_adapter, ledger_audit_bridge
        import research.w37_receipt_observation_v0_1 as w37
        import research.w36_pinned_sigsum_v0_1 as w36
        implementation = Path(__file__).resolve().parents[1]
        self.assertEqual(Path(ledger_observation_adapter.__file__).resolve(),
                         implementation / "ledger_observation_adapter.py")
        self.assertEqual(Path(ledger_audit_bridge.__file__).resolve(),
                         implementation / "ledger_audit_bridge.py")
        self.assertIs(w37.observe_ledger, ledger_observation_adapter.observe_ledger)
        self.assertIs(w37.verify_observation_manifest, ledger_audit_bridge.verify_observation_manifest)
        self.assertEqual(Path(w36.__file__).resolve(), implementation / "research" / "w36_pinned_sigsum_v0_1.py")

    def test_30_cli_success_is_not_authority(self):
        import subprocess, sys
        proc = subprocess.run([sys.executable,'-B','-m','research.w37_receipt_observation_v0_1',
                               str(self.ledger),'--receipt-dir',str(self.root)],
                              cwd=str(Path(__file__).resolve().parents[1]), capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        out=json.loads(proc.stdout)
        self.assertEqual(out['result'],'SEPARATE_VALID_OBSERVATIONS')
        self.check_no_authority(out)

    def test_31_cli_unknown_is_nonzero_and_non_authorizing(self):
        import subprocess, sys
        proc = subprocess.run([sys.executable,'-B','-m','research.w37_receipt_observation_v0_1',
                               str(self.tmp/'missing.jsonl'),'--receipt-dir',str(self.root)],
                              cwd=str(Path(__file__).resolve().parents[1]),capture_output=True,text=True)
        self.assertEqual(proc.returncode,2,proc.stderr)
        out=json.loads(proc.stdout)
        self.assert_refusal(out)

    def test_32_cli_invalid_receipt_is_nonzero(self):
        import subprocess, sys
        (self.root/'checkpoint.PUBLIC_SYNTHETIC.json.proof').write_bytes(b'INVALID')
        proc=subprocess.run([sys.executable,'-B','-m','research.w37_receipt_observation_v0_1',
                             str(self.ledger),'--receipt-dir',str(self.root)],
                            cwd=str(Path(__file__).resolve().parents[1]),capture_output=True,text=True)
        self.assertEqual(proc.returncode,2,proc.stderr)
        self.assert_refusal(json.loads(proc.stdout))


    def test_33_windows_crlf_checkout_restores_only_exact_pinned_bytes(self):
        for name,_ in FILES.values():
            p=self.root/name
            p.write_bytes(p.read_bytes().replace(b'\n',b'\r\n'))
        self.ledger.write_bytes(self.ledger.read_bytes().replace(b'\n',b'\r\n'))
        r=observe_pair(self.ledger,w36_inputs=self.root)
        self.assertEqual(r['result'],'SEPARATE_VALID_OBSERVATIONS')
        self.assertEqual(r['receipt_status'],'VERIFIED_SYNTHETIC_INCLUSION')
        self.assertEqual(set(r['w35_fixture_git_checkout_crlf_restored']),set(FILES))
        self.assertEqual(r['ario_bridge_status'],'OBSERVED')
        self.check_no_authority(r)

    def test_34_crlf_with_extra_byte_is_not_restored(self):
        for name,_ in FILES.values():
            p=self.root/name
            p.write_bytes(p.read_bytes().replace(b'\n',b'\r\n'))
        proof=self.root/'checkpoint.PUBLIC_SYNTHETIC.json.proof'
        proof.write_bytes(proof.read_bytes()+b'X')
        r=observe_pair(self.ledger,w36_inputs=self.root)
        self.assertEqual(r['receipt_reason'],'PROOF_BYTES_MISMATCH')
        self.assertNotIn('proof',r['w35_fixture_git_checkout_crlf_restored'])
        self.assert_refusal(r)

    def test_35_crlf_modified_policy_must_fail_closed(self):
        for name,_ in FILES.values():
            p=self.root/name
            p.write_bytes(p.read_bytes().replace(b'\n',b'\r\n'))
        policy=self.root/'sigsum-test1-2025.policy'
        policy.write_bytes(policy.read_bytes()+b'X')
        r=observe_pair(self.ledger,w36_inputs=self.root)
        self.assertEqual(r['receipt_reason'],'UNPINNED_POLICY')
        self.assertNotIn('policy',r['w35_fixture_git_checkout_crlf_restored'])
        self.assert_refusal(r)

if __name__ == '__main__':
    unittest.main(verbosity=2)
