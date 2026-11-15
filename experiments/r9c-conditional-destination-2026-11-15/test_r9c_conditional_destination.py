"""Author-controlled POSIX research controls: results are NOT independent review."""
import copy
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

import r9c_conditional_destination as m

CODE = Path(m.__file__).resolve()

class R9CCases(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="r9c-")
        self.p=Path(self.tmp.name)
        self.dsock=self.p/'d.sock'; self.wsock=self.p/'w.sock'
        self.ddb=self.p/'destination.sqlite3'; self.wdb=self.p/'witness.sqlite3'
        self.dkey=self.p/'dk'; self.wkey=self.p/'wk'; self.seal=self.p/'receipt-key'
        for path in (self.dkey,self.wkey,self.seal):
            path.write_bytes(secrets.token_bytes(32)); path.chmod(0o600)
        self.procs=[]
        try:
            self.start('dest')
            self.start('witness')
        except BaseException:
            self.tearDown()  # unittest does not call tearDown if setUp fails.
            raise
        self.dest=m.WireClient(self.dsock,self.dkey.read_bytes())
        self.wit=m.WireClient(self.wsock,self.wkey.read_bytes())
        self.co=m.CoordinatedResearch(self.dest,self.wit)

    def tearDown(self):
        for proc in self.procs:
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=2)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=2)
            proc.stdout.close(); proc.stderr.close()
        self.tmp.cleanup()

    def start(self,role,env=None):
        sock,db,key=(self.dsock,self.ddb,self.dkey) if role=='dest' else (self.wsock,self.wdb,self.wkey)
        if sock.exists(): sock.unlink()
        e=os.environ.copy(); e.update(env or {})
        command=[sys.executable,'-B',str(CODE),role,'--db',str(db),'--socket',str(sock),
                 '--auth-key',str(key),'--receipt-key',str(self.seal)]
        proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=e)
        self.procs.append(proc)
        for _ in range(400):
            if sock.exists():
                try:
                    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
                        s.settimeout(.4);s.connect(str(sock))
                    return proc
                except OSError: pass
            if proc.poll() is not None:
                raise RuntimeError(f'{role} died early: {proc.stderr.read().decode()[:500]}')
            time.sleep(.025)
        raise RuntimeError(f'{role} socket unavailable')

    def kill(self,role):
        sock=self.dsock if role=='dest' else self.wsock
        proc=next(p for p in reversed(self.procs) if p.poll() is None and
                  (str(sock) in p.args))
        proc.kill();proc.wait(timeout=3)
        if sock.exists(): sock.unlink()

    def advance(self):
        answer=self.co.advance(m.sha('new','epoch',self.co.heads()['epoch']))
        self.assertEqual(answer['status'],'SIMULATED_EPOCH_CHECKPOINTED_NOT_INDEPENDENT')
        return self.dest.call('DEST_HEAD')

    def apply(self,op='OP-1',payload=None):
        return self.co.apply(op,payload or m.sha('payload',op))

    def event(self,idx):
        return self.dest.call('DEST_EVENT',idx=idx)['proof']

    def count(self):
        c=sqlite3.connect(self.ddb)
        try:
            return c.execute('SELECT COUNT(*) FROM effects').fetchone()[0]
        finally:
            c.close()

    def test_01_genesis_match_does_not_prove_independence(self):
        self.assertEqual(self.co.heads()['idx'],0)
        self.assertEqual(self.count(),0)

    def test_02_direct_epoch_commit_with_missing_checkpoint_holds(self):
        h=self.dest.call('DEST_HEAD')
        r=self.dest.call('DEST_ADVANCE',epoch=h['epoch'],epoch_hash=h['epoch_hash'],commitment=m.sha('direct'))
        self.assertEqual(r['status'],'ADVANCED_AT_DESTINATION_ONLY')
        with self.assertRaisesRegex(m.Hold,'HISTORY_DIVERGED'): self.co.heads()
        self.assertEqual(self.count(),0)

    def test_03_checkpointed_epoch_then_effect(self):
        self.advance(); self.assertEqual(self.apply()['status'],'SIMULATED_EFFECT_CHECKPOINTED_NOT_INDEPENDENT')
        self.assertEqual(self.count(),1); self.assertEqual(self.co.heads()['idx'],2)

    def test_04_duplicate_op_id_never_reapplies(self):
        self.advance(); self.apply()
        again=self.apply()
        self.assertEqual(again['destination_status'],'ALREADY_APPLIED_DESTINATION')
        self.assertEqual(self.count(),1);self.assertEqual(self.co.heads()['idx'],2)

    def test_05_conflicting_duplicate_identifier_holds(self):
        self.advance();self.apply()
        r=self.apply('OP-1',m.sha('different'))
        self.assertEqual(r['status'],'HOLD_UNCERTAIN_DESTINATION')
        self.assertEqual(self.count(),1)

    def test_06_out_of_band_epoch_CAS_before_APPLY_fails_at_destination(self):
        old=self.advance()
        r=self.dest.call('DEST_ADVANCE',epoch=old['epoch'],epoch_hash=old['epoch_hash'],commitment=m.sha('newer'))
        with self.assertRaisesRegex(m.Hold,'STALE_EPOCH_AT_DESTINATION'):
            self.dest.call('DEST_APPLY',op_id='OP-6',payload_hash=m.sha('v'),scope=m.SCOPE,epoch=old['epoch'],epoch_hash=old['epoch_hash'])
        self.assertEqual(self.count(),0)
        self.assertEqual(r['proof']['body']['idx'],2)

    def test_07_wrong_client_hmac_denied(self):
        other=m.WireClient(self.dsock,secrets.token_bytes(32))
        with self.assertRaisesRegex(m.Hold,'INVALID_RESPONSE_AUTH'): other.call('DEST_HEAD')
        self.assertEqual(self.co.heads()['idx'],0)

    def test_08_nonce_replay_denied(self):
        body={'format':m.PROTOCOL,'nonce':secrets.token_hex(16),'op':'DEST_HEAD'}
        signed={'body':body,'mac':m.sig(self.dkey.read_bytes(),body)}
        def send():
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
                s.settimeout(3);s.connect(str(self.dsock));s.sendall(m.canonical(signed)+b'\n');return m.read_packet(s)
        self.assertTrue(send()['body']['value']['ok'])
        self.assertEqual(send()['body']['value']['reason'],'REPLAYED_NONCE')

    def test_09_strict_boolean_rejected_for_epoch(self):
        with self.assertRaisesRegex(m.Hold,'BAD_ADVANCE_FIELDS'):
            self.dest.call('DEST_ADVANCE',epoch=True,epoch_hash=m.GENESIS,commitment=m.sha('x'))

    def test_10_unsupported_action_scope_rejected(self):
        self.advance();h=self.dest.call('DEST_HEAD')
        with self.assertRaisesRegex(m.Hold,'BAD_APPLY_FIELDS_OR_SCOPE'):
            self.dest.call('DEST_APPLY',op_id='evil',payload_hash=m.sha('x'),scope='REAL_TRANSFER',epoch=h['epoch'],epoch_hash=h['epoch_hash'])
        self.assertEqual(self.count(),0)

    def test_11_witness_rejects_forged_receipt(self):
        self.advance();raw=copy.deepcopy(self.event(1))
        raw['body']['payload_hash']=m.sha('tampered')
        with self.assertRaisesRegex(m.Hold,'UNTRUSTED_OR_MALFORMED_RECEIPT'):
            self.wit.call('WIT_RECORD',proof=raw)

    def test_12_witness_rejects_validly_signed_conflicting_digest(self):
        self.advance(); original=self.event(1)
        forged=copy.deepcopy(original); forged['body']['event_hash']=m.sha('foreign')
        forged['mac']=m.sig(self.seal.read_bytes(),forged['body'])
        with self.assertRaisesRegex(m.Hold,'PROOF_CONTENT_MISMATCH'):
            self.wit.call('WIT_RECORD',proof=forged)

    def test_13_witness_requires_no_gaps(self):
        self.advance();self.apply('OP-13')
        # At witness currently idx2. Advance destination to idx3 without checkpoint.
        head=self.dest.call('DEST_HEAD')
        self.dest.call('DEST_ADVANCE',epoch=head['epoch'],epoch_hash=head['epoch_hash'],commitment=m.sha('third'))
        # Next event4 signed by dest, but must not skip unrecorded event3.
        head=self.dest.call('DEST_HEAD')
        self.dest.call('DEST_ADVANCE',epoch=head['epoch'],epoch_hash=head['epoch_hash'],commitment=m.sha('fourth'))
        with self.assertRaisesRegex(m.Hold,'CHECKPOINT_GAP_OR_CONFLICT'):
            self.wit.call('WIT_RECORD',proof=self.event(4))
        self.assertEqual(self.wit.call('WIT_HEAD')['idx'],2)

    def test_14_duplicate_checkpoint_is_idempotent(self):
        self.advance()
        response=self.wit.call('WIT_RECORD',proof=self.event(1))
        self.assertEqual(response['status'],'ALREADY_RECORDED')

    def test_15_lost_client_ack_must_hold_even_after_commit(self):
        self.advance(); res=self.co.apply('LOST',m.sha('lost'),crash_in_ack=True)
        self.assertEqual(res['status'],'HOLD_UNCERTAIN_DESTINATION')
        self.assertEqual(self.count(),1)
        with self.assertRaisesRegex(m.Hold,'HISTORY_DIVERGED'):self.co.heads()
        self.assertEqual(self.co.reconcile('LOST')['status'],'SIMULATED_RECONCILED_NOT_INDEPENDENT')
        self.assertEqual(self.count(),1)

    def test_16_witness_unreachable_after_commit_is_uncertain(self):
        self.advance();self.kill('witness')
        # No orchestration HEAD possible; simulate dest-applied effect and lookup during downtime.
        h=self.dest.call('DEST_HEAD')
        dest=self.dest.call('DEST_APPLY',op_id='OP16',payload_hash=m.sha('x'),scope=m.SCOPE,epoch=h['epoch'],epoch_hash=h['epoch_hash'])
        self.assertEqual(dest['status'],'APPLIED_AT_SIMULATED_DESTINATION')
        with self.assertRaises(m.Hold):self.wit.call('WIT_RECORD',proof=dest['proof'])
        self.assertEqual(self.count(),1)
        self.start('witness')
        self.assertEqual(self.co.reconcile('OP16')['status'],'SIMULATED_RECONCILED_NOT_INDEPENDENT')

    def test_17_process_crash_after_destination_commit_before_ack(self):
        self.advance(); self.kill('dest')
        self.start('dest',{'R9C_KILL_AFTER_COMMIT_OP':'OP17'})
        result=self.apply('OP17')
        self.assertEqual(result['status'],'HOLD_UNCERTAIN_DESTINATION')
        self.assertEqual(self.count(),1)
        self.start('dest')
        self.assertEqual(self.co.reconcile('OP17')['status'],'SIMULATED_RECONCILED_NOT_INDEPENDENT')
        self.assertEqual(self.count(),1)

    def test_18_process_crash_after_witness_commit_before_ack(self):
        self.advance();self.kill('witness');self.start('witness',{'R9C_KILL_AFTER_WIT_RECORD_IDX':'2'})
        result=self.apply('OP18');self.assertEqual(result['status'],'HOLD_UNCERTAIN_CHECKPOINT')
        self.assertEqual(self.count(),1)
        self.start('witness')
        ans=self.co.reconcile('OP18')
        self.assertEqual(ans['status'],'SIMULATED_RECONCILED_NOT_INDEPENDENT')
        self.assertEqual(self.wit.call('WIT_HEAD')['idx'],2)

    def test_19_destination_only_rollback_detected_if_witness_kept(self):
        self.advance()
        copy=self.p/'old-d.sqlite3';shutil.copy2(self.ddb,copy)
        self.apply('OP19'); self.kill('dest')
        shutil.copy2(copy,self.ddb);self.start('dest')
        with self.assertRaisesRegex(m.Hold,'HISTORY_DIVERGED'):self.co.heads()

    def test_20_witness_only_rollback_detected_by_comparison(self):
        self.advance();copy=self.p/'old-w.sqlite3';shutil.copy2(self.wdb,copy)
        self.apply('OP20');self.kill('witness')
        shutil.copy2(copy,self.wdb);self.start('witness')
        with self.assertRaisesRegex(m.Hold,'HISTORY_DIVERGED'):self.co.heads()

    def test_21_shared_admin_rolls_back_both_negative_capability(self):
        self.advance()
        pre_dest=self.p/'baseline-d.sqlite3';pre_wit=self.p/'baseline-w.sqlite3'
        shutil.copy2(self.ddb,pre_dest);shutil.copy2(self.wdb,pre_wit)
        self.apply('OP21');self.kill('dest');self.kill('witness')
        shutil.copy2(pre_dest,self.ddb);shutil.copy2(pre_wit,self.wdb)
        self.start('dest');self.start('witness')
        self.assertEqual(self.co.heads()['idx'],1)
        second=self.apply('OP21')
        self.assertEqual(second['status'],'SIMULATED_EFFECT_CHECKPOINTED_NOT_INDEPENDENT')
        self.assertEqual(self.count(),1)
        # Previously recorded and forgotten effect existed before rollback.
        # Positive return after the rollback is an intentional NEGATIVE_CAPABILITY.

    def test_22_concurrent_clients_same_op_only_one_row(self):
        self.advance();h=self.dest.call('DEST_HEAD')
        args=dict(op_id='SAME',payload_hash=m.sha('same'),scope=m.SCOPE,epoch=h['epoch'],epoch_hash=h['epoch_hash'])
        # Eight real distinct OS processes, all independently transmitting to dest.
        code="""import os,sys,json
sys.path.insert(0,sys.argv[1])
import r9c_conditional_destination as m
from pathlib import Path
c=m.WireClient(Path(sys.argv[2]),Path(sys.argv[3]).read_bytes())
try: print(json.dumps(c.call('DEST_APPLY',**json.loads(sys.argv[4]))))
except m.Hold as e: print(json.dumps({'error':str(e)}))
"""
        tasks=[]
        with ThreadPoolExecutor(max_workers=8) as pool:
            fs=[pool.submit(subprocess.run,[sys.executable,'-B','-c',code,str(CODE.parent),str(self.dsock),str(self.dkey),json.dumps(args)],capture_output=True,text=True,timeout=14) for _ in range(8)]
            for f in fs: tasks.append(f.result())
        self.assertTrue(all(p.returncode==0 for p in tasks))
        vals=[json.loads(p.stdout) for p in tasks]
        self.assertTrue(all('error' not in x for x in vals), vals)
        self.assertEqual({x['proof']['body']['event_hash'] for x in vals}.__len__(),1)
        self.assertEqual(self.count(),1)
        self.assertEqual(self.dest.call('DEST_HEAD')['idx'],2)
        self.wit.call('WIT_RECORD',proof=self.event(2));self.assertEqual(self.co.heads()['idx'],2)

    def test_23_concurrent_CAS_vs_APPLY_no_stale_false_admission(self):
        self.advance();h=self.dest.call('DEST_HEAD')
        def apply():
            try:return ('applied',self.dest.call('DEST_APPLY',op_id='RACE',payload_hash=m.sha('race'),scope=m.SCOPE,epoch=h['epoch'],epoch_hash=h['epoch_hash']))
            except m.Hold as e:return ('hold',str(e))
        def cas():
            try:return ('advanced',self.dest.call('DEST_ADVANCE',epoch=h['epoch'],epoch_hash=h['epoch_hash'],commitment=m.sha('race-cas')))
            except m.Hold as e:return ('hold',str(e))
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(apply);b=pool.submit(cas);x,y=a.result(),b.result()
        # SQLite has a linearized order: either both occur in that order, or
        # the CAS wins first and the stale APPLY is refused.
        self.assertEqual(y[0],'advanced')
        if x[0]=='hold': self.assertEqual(self.count(),0)
        else: self.assertEqual(self.count(),1)
        self.assertEqual(self.dest.call('DEST_HEAD')['epoch'],h['epoch']+1)

    def test_24_missing_intermediate_checkpoint_holds_reconcile(self):
        self.advance();h=self.dest.call('DEST_HEAD')
        for i in ('ONE','TWO'):
            self.dest.call('DEST_APPLY',op_id=i,payload_hash=m.sha(i),scope=m.SCOPE,epoch=h['epoch'],epoch_hash=h['epoch_hash'])
        self.assertEqual(self.co.reconcile('TWO')['status'],'HOLD_MISSING_INTERMEDIATE_CHECKPOINTS')
        self.assertEqual(self.co.reconcile('ONE')['status'],'SIMULATED_RECONCILED_NOT_INDEPENDENT')
        self.assertEqual(self.co.reconcile('TWO')['status'],'SIMULATED_RECONCILED_NOT_INDEPENDENT')

    def test_25_unknown_result_is_not_evidence_of_nonapplication(self):
        self.advance()
        self.assertEqual(self.co.reconcile('NEVER')['status'],'HOLD_NO_AUTHENTICATED_DESTINATION_PROOF')
        self.assertEqual(self.count(),0)

if __name__=='__main__':
    unittest.main(verbosity=2)
