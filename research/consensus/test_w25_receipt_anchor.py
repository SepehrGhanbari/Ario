#!/usr/bin/env python3
"""W25 bounded, author-designed synthetic tests; no real signer or anchor identity."""
from __future__ import annotations
import base64
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from w25_receipt_anchor_lab import prepare,anchor_observe,finalize,read_heads,worker,_connect,_read

ORIGIN='ario-w22-research.invalid/synthetic-log'

def leaf(b):return hashlib.sha256(b'\x00'+b).digest()
def join(a,b):return hashlib.sha256(b'\x01'+a+b).digest()

class W25(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='w25_');self.addCleanup(self.tmp.cleanup)
        self.p=str(Path(self.tmp.name)/'publisher.sqlite3')
        self.a=str(Path(self.tmp.name)/'anchor.sqlite3')
        secret=Ed25519PrivateKey.generate()  # ephemeral test only, never written
        public=secret.public_key().public_bytes(encoding=serialization.Encoding.Raw,format=serialization.PublicFormat.Raw)
        keyid=hashlib.sha256(ORIGIN.encode()+b'\n\x01'+public).digest()[:4]
        self.key=ORIGIN+'+'+keyid.hex()+'+'+base64.b64encode(b'\x01'+public).decode()
        left=leaf(b'w25 public synthetic event 1')
        right=leaf(b'w25 public synthetic event 2')
        badright=leaf(b'w25 competing fork')
        def note(n,root):
            msg=(ORIGIN+'\n'+str(n)+'\n'+base64.b64encode(root).decode()+'\n').encode()
            sig=base64.b64encode(keyid+secret.sign(msg)).decode()
            return msg+b'\n'+('— '+ORIGIN+' '+sig+'\n').encode()
        self.old=note(1,left);self.new=note(2,join(left,right))
        self.fork=note(2,join(left,badright));self.proof=[right.hex()]

    def prep(self,rid='req1',old=0,note=None,proof=None,**kw):
        return prepare(self.p,request_id=rid,old_size=old,candidate_note=self.old if note is None else note,
                       pinned_vkey=self.key,proof=[] if proof is None else proof,**kw)
    def anchor(self,old=0,note=None,proof=None,**kw):
        return anchor_observe(self.a,old_size=old,candidate_note=self.old if note is None else note,
                              pinned_vkey=self.key,proof=[] if proof is None else proof,**kw)
    def finish(self,rid='req1',**kw):return finalize(self.p,self.a,request_id=rid,**kw)
    def first(self):
        self.assertEqual(self.prep()['status'],'PENDING_ANCHOR')
        self.assertEqual(self.anchor()['status'],'ANCHORED_LAB')
        self.assertEqual(self.finish()['status'],'FINAL_UNSIGNED_RECEIPT')
    def second(self):
        self.first()
        self.assertEqual(self.prep('req2',1,self.new,self.proof)['status'],'PENDING_ANCHOR')
        self.assertEqual(self.anchor(1,self.new,self.proof)['status'],'ANCHORED_LAB')
        return self.finish('req2')
    def _crash(self,kind,stage,rid='req1',old=0,note=None,proof=None):
        values={'p':self.p,'a':self.a,'key':self.key,'rid':rid,'old':old,'note':(self.old if note is None else note).decode(),
                'proof':[] if proof is None else proof,'stage':stage,'kind':kind}
        script=('import json,sys;from w25_receipt_anchor_lab import prepare,anchor_observe,finalize;'
                'a=json.loads(sys.stdin.read());'
                'k=a["kind"];'
                'prepare(a["p"],request_id=a["rid"],old_size=a["old"],candidate_note=a["note"].encode(),pinned_vkey=a["key"],proof=a["proof"],crash_stage=a["stage"]) if k=="prepare" else '
                'anchor_observe(a["a"],old_size=a["old"],candidate_note=a["note"].encode(),pinned_vkey=a["key"],proof=a["proof"],crash_stage=a["stage"]) if k=="anchor" else '
                'finalize(a["p"],a["a"],request_id=a["rid"],crash_stage=a["stage"])')
        return subprocess.run([sys.executable,'-B','-c',script],input=json.dumps(values),text=True,capture_output=True,
                              cwd=str(Path(__file__).parent),timeout=20)

    def test_01_prepare_no_receipt_and_no_head_advance(self):
        x=self.prep();self.assertEqual(x['status'],'PENDING_ANCHOR')
        self.assertNotIn('unsigned_lab_receipt',x)
        self.assertEqual(read_heads(self.p,self.a)['status'],'HOLD')
    def test_02_anchor_finalize_durable_receipt(self):
        self.first();r=self.finish();self.assertTrue(r['unsigned_lab_receipt'].startswith('UNSIGNED_W25_LAB_RECEIPT:'))
        self.assertEqual(read_heads(self.p,self.a)['status'],'MATCH')
    def test_03_lost_response_retry_same_receipt(self):
        self.first();self.assertEqual(self.finish()['unsigned_lab_receipt'],self.finish()['unsigned_lab_receipt'])
    def test_04_same_request_different_note_denied(self):
        self.prep();self.assertEqual(self.prep('req1',0,self.new)['reason'],'REQUEST_ID_REUSED_WITH_DIFFERENT_BYTES')
    def test_05_same_request_different_proof_denied(self):
        self.prep();self.assertEqual(self.prep('req1',0,self.old,['0'*64])['status'],'DENY')
    def test_06_same_pending_request_replayed(self):
        self.prep();self.assertEqual(self.prep()['status'],'EXISTING_INTENT')
    def test_07_wrong_expected_old_size(self):
        self.first();self.assertEqual(self.prep('req2',0,self.new)['status'],'CONFLICT')
    def test_08_invalid_signature_denied(self):
        self.assertEqual(self.prep('req1',0,self.old.replace(b'\n1\n',b'\n2\n'))['status'],'DENY')
    def test_09_bad_proof_and_competing_fork_denied(self):
        self.first()
        self.assertEqual(self.prep('req2',1,self.fork,self.proof)['status'],'DENY')
        self.assertEqual(self.anchor(1,self.fork,self.proof)['status'],'DENY')
    def test_10_anchor_crash_before_commit_rollback(self):
        self.prep();p=self._crash('anchor','before_anchor_commit')
        self.assertEqual(p.returncode,82,p.stderr)
        self.assertEqual(self.finish()['status'],'HOLD')
        self.anchor();self.assertEqual(self.finish()['status'],'FINAL_UNSIGNED_RECEIPT')
    def test_11_anchor_crash_after_commit_recovery(self):
        self.prep();p=self._crash('anchor','after_anchor_commit')
        self.assertEqual(p.returncode,83,p.stderr)
        self.assertEqual(self.finish()['status'],'FINAL_UNSIGNED_RECEIPT')
    def test_12_prepare_crash_after_commit_recovery(self):
        p=self._crash('prepare','after_prepare_commit')
        self.assertEqual(p.returncode,81,p.stderr)
        self.assertEqual(self.prep()['status'],'EXISTING_INTENT')
        self.anchor();self.assertEqual(self.finish()['status'],'FINAL_UNSIGNED_RECEIPT')
    def test_13_finalize_crash_before_commit_recovery(self):
        self.prep();self.anchor();p=self._crash('finalize','before_final_commit')
        self.assertEqual(p.returncode,84,p.stderr)
        self.assertEqual(self.finish()['status'],'FINAL_UNSIGNED_RECEIPT')
    def test_14_finalize_crash_after_commit_receipt_recovery(self):
        self.prep();self.anchor();p=self._crash('finalize','after_final_commit')
        self.assertEqual(p.returncode,85,p.stderr)
        self.assertEqual(p.stdout,'')
        a=self.finish();b=self.finish();self.assertEqual(a['unsigned_lab_receipt'],b['unsigned_lab_receipt'])
    def test_15_parallel_finalize_same_receipt(self):
        self.prep();self.anchor()
        jobs=[('finalize',self.p,self.a,{'request_id':'req1'})]*2
        with multiprocessing.get_context('spawn').Pool(2) as pool:outputs=pool.starmap(worker,jobs)
        self.assertTrue(all(x['status']=='FINAL_UNSIGNED_RECEIPT' for x in outputs))
        self.assertEqual(outputs[0]['unsigned_lab_receipt'],outputs[1]['unsigned_lab_receipt'])
    def test_16_pending_other_request_interlocked(self):
        self.prep()
        self.assertEqual(self.prep('req2',0,self.old)['reason'],'ANOTHER_REQUEST_PENDING')
    def test_17_local_rollback_detected_against_unchanged_anchor(self):
        self.first();backup=Path(self.tmp.name)/'old_p.sqlite3';shutil.copyfile(self.p,backup)
        self.prep('req2',1,self.new,self.proof);self.anchor(1,self.new,self.proof);self.finish('req2')
        shutil.copyfile(backup,self.p)
        self.assertEqual(read_heads(self.p,self.a)['reason'],'LOCAL_ROLLBACK_RELATIVE_TO_ANCHOR')
        self.assertEqual(self.finish()['status'],'DENY')
    def test_18_both_stores_rolled_back_not_detectable(self):
        self.first();p=Path(self.tmp.name)/'old_p.sqlite3';a=Path(self.tmp.name)/'old_a.sqlite3'
        shutil.copyfile(self.p,p);shutil.copyfile(self.a,a)
        self.prep('req2',1,self.new,self.proof);self.anchor(1,self.new,self.proof);self.finish('req2')
        shutil.copyfile(p,self.p);shutil.copyfile(a,self.a)
        self.assertEqual(read_heads(self.p,self.a)['status'],'MATCH')
        self.assertEqual(read_heads(self.p,self.a)['independent_operator_custody'],'NOT_ESTABLISHED')
    def test_19_mismatched_anchor_root_detected(self):
        self.first()
        c=_connect(self.a,'anchor')
        try:c.execute('UPDATE anchor SET root=? WHERE singleton=1',('0'*64,))
        finally:c.close()
        self.assertEqual(read_heads(self.p,self.a)['reason'],'SAME_SIZE_ROOT_CONFLICT')
        self.assertEqual(self.finish()['status'],'HOLD')
    def test_20_missing_anchor_holds(self):
        self.prep();self.assertEqual(self.finish()['reason'],'ANCHOR_UNAVAILABLE')
    def test_21_missing_publisher_head_fails(self):
        self.second();Path(self.p).unlink()
        self.assertEqual(read_heads(self.p,self.a)['status'],'DENY')
    def test_22_same_admin_can_fabricate_anchor_positive_negative_control(self):
        self.prep()
        from w23_checkpoint_gossip import read_signed_note
        h=read_signed_note(self.old,self.key)
        c=_connect(self.a,'anchor')
        try:
            c.execute('INSERT INTO anchor(singleton,size,root) VALUES(1,?,?)',(h['size'],h['root']))
            c.execute('INSERT INTO history(size,root) VALUES(?,?)',(h['size'],h['root']))
        finally:c.close()
        r=self.finish()
        self.assertEqual(r['status'],'FINAL_UNSIGNED_RECEIPT')
        self.assertEqual(r['anchor_authentication'],'NOT_ESTABLISHED')
    def test_24_w22_published_signed_notes_and_proof(self):
        """Real previous W22 synthetic published fixture; no new signer generated for this path."""
        base=Path(__file__).parent
        fixture_path=base/'W22_PUBLIC_SYNTHETIC_SIGNED_NOTES_2026-11-17.json'
        proof_path=base/'W20_SYNTHETIC_LOG_CHECKPOINTS_AND_PROOFS_2026-11-17.json'
        if not (fixture_path.exists() and proof_path.exists()):
            self.skipTest('W22 pinned fixtures available in Github checkout, absent from local scratch')
        fixture=json.loads(fixture_path.read_text('utf8'))
        proof=json.loads(proof_path.read_text('utf8'))['consistency_proof']
        key=fixture['public_vkey_for_synthetic_demo_only']
        old=fixture['previous_checkpoint'].encode()
        new=fixture['current_checkpoint'].encode()
        fork=fixture['same_signer_fork_checkpoint'].encode()
        def pr(rid,sz,n,prf):
            return prepare(self.p,request_id=rid,old_size=sz,candidate_note=n,pinned_vkey=key,proof=prf)
        def an(sz,n,prf):
            return anchor_observe(self.a,old_size=sz,candidate_note=n,pinned_vkey=key,proof=prf)
        self.assertEqual(pr('w22-size3',0,old,[])['status'],'PENDING_ANCHOR')
        self.assertEqual(an(0,old,[])['status'],'ANCHORED_LAB')
        self.assertEqual(self.finish('w22-size3')['status'],'FINAL_UNSIGNED_RECEIPT')
        self.assertEqual(pr('w22-size8',3,new,proof)['status'],'PENDING_ANCHOR')
        self.assertEqual(an(3,new,proof)['status'],'ANCHORED_LAB')
        self.assertEqual(self.finish('w22-size8')['status'],'FINAL_UNSIGNED_RECEIPT')
        self.assertEqual(read_heads(self.p,self.a)['status'],'MATCH')
        self.assertEqual(pr('fork',8,fork,[])['status'],'DENY')
        self.assertEqual(an(8,fork,[])['status'],'DENY')

    def test_25_corrupt_anchor_storage_fails_closed(self):
        self.prep()
        Path(self.a).write_bytes(b'Not a SQLite database')
        self.assertEqual(self.finish()['status'],'HOLD')
        self.assertEqual(self.anchor()['status'],'HOLD')

    def test_26_corrupt_publisher_storage_fails_closed(self):
        Path(self.p).write_bytes(b'Not a SQLite database')
        self.assertEqual(self.prep()['status'],'HOLD')
        self.assertEqual(self.finish()['status'],'HOLD')

    def test_27_receipt_rows_tampered_rejected_even_with_same_anchor(self):
        self.first()
        c=_connect(self.p,'publisher')
        try:c.execute("UPDATE requests SET receipt='UNSIGNED_W25_LAB_RECEIPT:forged' WHERE rid='req1'")
        finally:c.close()
        self.assertEqual(self.finish()['status'],'HOLD')

    def test_28_older_committed_receipt_survives_newer_checkpoint(self):
        self.first()
        original=self.finish('req1')['unsigned_lab_receipt']
        self.assertEqual(self.prep('req2',1,self.new,self.proof)['status'],'PENDING_ANCHOR')
        self.assertEqual(self.anchor(1,self.new,self.proof)['status'],'ANCHORED_LAB')
        self.assertEqual(self.finish('req2')['status'],'FINAL_UNSIGNED_RECEIPT')
        recovered=self.finish('req1')
        self.assertEqual(recovered['status'],'FINAL_UNSIGNED_RECEIPT',recovered)
        self.assertEqual(recovered['unsigned_lab_receipt'],original)

    def test_23_no_authority_or_real_witness(self):
        self.first();r=self.finish()
        for k,v in (('operational_authority','NONE'),('witness_cosignatures_issued',0),('publisher_actions',0),
                    ('source_truth','UNKNOWN'),('independent_operator_custody','NOT_ESTABLISHED'),
                    ('anchor_authentication','NOT_ESTABLISHED'),('memory_admitted',False)):
            self.assertEqual(r[k],v)

if __name__=='__main__':unittest.main(verbosity=2)
