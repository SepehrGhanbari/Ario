#!/usr/bin/env python3
"""W24 stdlib tests using published W22 signed notes and W20 consistency proof."""
import json
import multiprocessing
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from w24_atomic_witness_lab import observe, retained_head, worker

HERE = Path(__file__).resolve().parent
FIX = json.loads((HERE / 'W22_PUBLIC_SYNTHETIC_SIGNED_NOTES_2026-11-17.json').read_text('utf-8'))
W20 = json.loads((HERE / 'W20_SYNTHETIC_LOG_CHECKPOINTS_AND_PROOFS_2026-11-17.json').read_text('utf-8'))
KEY = FIX['public_vkey_for_synthetic_demo_only']
OLD = FIX['previous_checkpoint'].encode('utf-8')
NEW = FIX['current_checkpoint'].encode('utf-8')
FORK = FIX['same_signer_fork_checkpoint'].encode('utf-8')
PROOF = W20['consistency_proof']

class W24(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='w24_')
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name)/'state.sqlite3')

    def call(self, old_size, candidate_note, proof=None, crash_stage=None):
        return observe(self.db, old_size=old_size, candidate_note=candidate_note,
                       pinned_vkey=KEY, proof=proof, crash_stage=crash_stage)

    def first(self):
        return self.call(0,OLD)

    def test_01_genesis_fixture_only(self):
        r=self.first()
        self.assertEqual(r['status'],'COMMITTED_UNSIGNED_LAB_RECEIPT')
        self.assertFalse(r['cosignature_issued'])
        self.assertEqual(retained_head(self.db)['size'],3)

    def test_02_valid_growth_and_restart(self):
        self.first()
        r=self.call(3,NEW,PROOF)
        self.assertEqual(r['status'],'COMMITTED_UNSIGNED_LAB_RECEIPT')
        self.assertEqual(retained_head(self.db)['size'],8)

    def test_03_wrong_old_size_conflict(self):
        self.first()
        self.assertEqual(self.call(0,NEW)['status'],'CONFLICT')
        self.assertEqual(retained_head(self.db)['size'],3)

    def test_04_bad_consistency_does_not_persist(self):
        self.first()
        bad=PROOF.copy();bad[0]='0'*64
        self.assertEqual(self.call(3,NEW,bad)['status'],'DENY')
        self.assertEqual(retained_head(self.db)['size'],3)

    def test_05_no_fork_at_equal_size(self):
        self.first();self.call(3,NEW,PROOF)
        self.assertEqual(self.call(8,FORK,[])['status'],'DENY')
        self.assertEqual(retained_head(self.db)['size'],8)

    def test_06_same_note_retry_same_size_is_safe(self):
        self.first()
        a=self.call(3,NEW,PROOF)
        b=self.call(8,NEW,[])
        self.assertEqual(a['receipt'],b['receipt'])
        self.assertEqual(retained_head(self.db)['size'],8)

    def test_07_invalid_signature_no_state_change(self):
        self.first()
        corrupt=NEW.replace(b'\n8\n',b'\n9\n')
        self.assertEqual(self.call(3,corrupt,PROOF)['status'],'DENY')
        self.assertEqual(retained_head(self.db)['size'],3)

    def _crash(self,stage,old_size,note,proof):
        script=('import sys,json;from w24_atomic_witness_lab import observe;'
                'a=json.loads(sys.stdin.read());observe(a["db"],old_size=a["old"],'
                'candidate_note=a["note"].encode(),pinned_vkey=a["key"],'
                'proof=a["proof"],crash_stage=a["stage"])')
        return subprocess.run([sys.executable,'-B','-c',script], cwd=str(HERE),
            input=json.dumps({'db':self.db,'old':old_size,'note':note.decode(),
                              'key':KEY,'proof':proof,'stage':stage}),
            text=True,capture_output=True,timeout=12)

    def test_08_crash_before_commit_reverts(self):
        self.first()
        p=self._crash('before_commit',3,NEW,PROOF)
        self.assertEqual(p.returncode,73,p.stderr)
        self.assertEqual(retained_head(self.db)['size'],3)
        self.assertEqual(self.call(3,NEW,PROOF)['status'],'COMMITTED_UNSIGNED_LAB_RECEIPT')

    def test_09_crash_after_commit_keeps_head_no_receipt(self):
        self.first()
        p=self._crash('after_commit_before_receipt',3,NEW,PROOF)
        self.assertEqual(p.returncode,74,p.stderr)
        self.assertEqual(p.stdout,'')
        self.assertEqual(retained_head(self.db)['size'],8)
        self.assertEqual(self.call(8,NEW,[])['status'],'COMMITTED_UNSIGNED_LAB_RECEIPT')

    def test_10_initial_crash_before_commit_no_state(self):
        p=self._crash('before_commit',0,OLD,None)
        self.assertEqual(p.returncode,73,p.stderr)
        self.assertIsNone(retained_head(self.db))

    def test_11_two_forks_parallel_only_one_wins(self):
        self.first()
        tasks=[(self.db,dict(old_size=3,candidate_note=NEW,pinned_vkey=KEY,proof=PROOF)),
               (self.db,dict(old_size=3,candidate_note=FORK,pinned_vkey=KEY,proof=PROOF))]
        with multiprocessing.get_context('spawn').Pool(2) as pool:
            results=pool.map(worker,tasks)
        self.assertEqual([x['status'] for x in results].count('COMMITTED_UNSIGNED_LAB_RECEIPT'),1)
        self.assertEqual(retained_head(self.db)['size'],8)

    def test_12_parallel_duplicate_requests_one_commit_one_conflict(self):
        self.first()
        tasks=[(self.db,dict(old_size=3,candidate_note=NEW,pinned_vkey=KEY,proof=PROOF))]*2
        with multiprocessing.get_context('spawn').Pool(2) as pool:
            results=pool.map(worker,tasks)
        self.assertEqual(sorted(x['status'] for x in results),
          ['COMMITTED_UNSIGNED_LAB_RECEIPT','CONFLICT'])
        self.assertEqual(retained_head(self.db)['size'],8)

    def test_13_external_db_rollback_is_detected_only_with_independent_pin(self):
        self.first()
        backup=str(Path(self.tmp.name)/'old.sqlite3')
        shutil.copyfile(self.db,backup)
        self.call(3,NEW,PROOF)
        independently_retained_size=retained_head(self.db)['size']
        shutil.copyfile(backup,self.db) # same admin can replace DB
        self.assertEqual(retained_head(self.db)['size'],3)
        self.assertLess(retained_head(self.db)['size'],independently_retained_size)

    def test_14_audit_boundary_no_real_witness(self):
        r=self.first()
        self.assertTrue(r['receipt'].startswith('UNSIGNED_W24_LAB_RECEIPT:'))
        self.assertEqual(r['authority'],'NONE')
        self.assertEqual(r['custody'],'SAME_ADMIN_NOT_INDEPENDENT')
        self.assertEqual(r['world_freshness'],'UNKNOWN')
        self.assertEqual(r['external_actions'],0)
        self.assertFalse(r['cosignature_issued'])

if __name__=='__main__':
    unittest.main(verbosity=2)
