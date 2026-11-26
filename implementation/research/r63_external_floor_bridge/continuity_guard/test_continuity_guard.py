import os, secrets, shutil, tempfile, sqlite3, unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from continuity_guard import *

class Crash(Exception): pass

class Continuity(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root=Path(self.tmp.name)
        self.wkey=Ed25519PrivateKey.generate(); self.operators={n:Ed25519PrivateKey.generate() for n in ANCHORS}
        self.anchors=[Anchor(n,self.root/(n+'.db'),Ed25519PrivateKey.generate(),self.operators[n]) for n in ANCHORS]
        self.q=AnchorQuorum(self.anchors); self.identity='ario-r63-witness-01'; self.policy=sha(b'policy')
        self.genesis=sha(b'V11-genesis'); self.genesis_cp=make_checkpoint(self.identity,self.policy,pub(self.wkey),0,ZERO,self.genesis,secrets.token_hex(32))
        self.q.provision(self.genesis_cp,self.operators)
        self.w=Witness(self.identity,self.policy,self.root/'witness.db',self.wkey,self.q); self.w.provision_local(self.genesis_cp)
    def fresh(self):
        root=self.root/'fresh'; root.mkdir(); wk=Ed25519PrivateKey.generate(); ops={n:Ed25519PrivateKey.generate() for n in ANCHORS}
        aa=[Anchor(n,root/(n+'.db'),Ed25519PrivateKey.generate(),ops[n]) for n in ANCHORS]; q=AnchorQuorum(aa)
        ident='ario-r63-fresh'; pol=sha(b'fresh-policy'); gen=sha(b'fresh-genesis')
        cp=make_checkpoint(ident,pol,pub(wk),0,ZERO,gen,secrets.token_hex(32)); q.provision(cp,ops)
        return Witness(ident,pol,root/'witness.db',wk,q),aa,q,ops,cp
    def next_hash(self): return sha(b'R63-state-2')
    def advance(self): return self.w.transition(self.next_hash())
    def test_01_genesis_active(self): self.assertEqual(self.w.status(),ACTIVE)
    def test_02_transition_requires_three_durable_anchor_receipts(self): self.assertGreaterEqual(self.advance()['anchor_receipts'],3); self.assertEqual(self.w.status(),ACTIVE)
    def test_03_local_memory_loss_quarantines_same_identity(self):
        self.advance(); self.w.path.unlink(); same=Witness(self.identity,self.policy,self.w.path,self.wkey,self.q)
        self.assertEqual(same.status(),QUARANTINED)
        with self.assertRaises(ContinuityError): same.transition(sha(b'forbidden'))
        with self.assertRaises(ContinuityError): same.read_identity_proof(secrets.token_hex(32))
    def test_04_old_local_snapshot_quarantined(self):
        backup=self.root/'old.db'; shutil.copy2(self.w.path,backup); self.advance(); shutil.copy2(backup,self.w.path); self.assertEqual(self.w.status(),QUARANTINED)
    def test_05_one_anchor_lost_tolerated(self):
        self.advance(); self.anchors[0].path.unlink(); self.assertEqual(self.w.status(),ACTIVE)
    def test_06_two_anchor_stores_lost_hold(self):
        self.advance()
        for a in self.anchors[:2]: a.path.unlink()
        self.assertEqual(self.w.status(),HOLD)
    def test_07_two_anchor_rollback_hold(self):
        backs=[]
        for a in self.anchors[:2]:
            p=self.root/(a.name+'.old'); shutil.copy2(a.path,p); backs.append((a,p))
        self.advance()
        for a,p in backs: shutil.copy2(p,a.path)
        self.assertEqual(self.w.status(),HOLD)
    def test_08_three_old_one_new_never_falls_back(self):
        a=self.anchors[3]; cp=make_checkpoint(self.identity,self.policy,pub(self.wkey),1,self.genesis,sha(b'partial'),secrets.token_hex(32))
        a.commit(cp,sign(self.wkey,b'R63-WITNESS-CHECKPOINT',canon(cp))); self.assertEqual(self.w.status(),HOLD)
    def test_09_two_of_four_partial_write_holds_then_resumes(self):
        with self.assertRaises(ContinuityError): self.w.transition(self.next_hash(),write_available={'a1','a2'})
        self.assertEqual(self.w.status(),HOLD)
        self.w.resume_pending(); self.assertEqual(self.w.status(),ACTIVE)
    def test_10_crash_after_local_pending_recovers(self):
        def fp(x):
            if x=='after_local_pending': raise Crash()
        with self.assertRaises(Crash): self.w.transition(self.next_hash(),failpoint=fp)
        self.assertEqual(self.w.status(),'PENDING_ANCHOR_RECOVERY_REQUIRED'); self.w.resume_pending(); self.assertEqual(self.w.status(),ACTIVE)
    def test_11_crash_after_anchor_quorum_recovers(self):
        def fp(x):
            if x=='after_anchor_quorum': raise Crash()
        with self.assertRaises(Crash): self.w.transition(self.next_hash(),failpoint=fp)
        self.assertEqual(self.w.status(),ACTIVE)
    def test_12_crash_after_local_commit_is_idempotent(self):
        def fp(x):
            if x=='after_local_commit': raise Crash()
        with self.assertRaises(Crash): self.w.transition(self.next_hash(),failpoint=fp)
        self.assertEqual(self.w.status(),ACTIVE)
    def test_13_identity_proof_contains_three_or_four_signed_anchor_reads(self):
        nonce=secrets.token_hex(32); obj=decode(self.w.read_identity_proof(nonce)); b=obj['body']
        verify(self.w.witness_pub,b'R63-WITNESS-CONTINUITY',canon(b),obj['signature'])
        self.assertGreaterEqual(len(b['anchor_read_responses']),3)
        for raw in b['anchor_read_responses']:
            aobj=decode(raw.encode('ascii')); ab=aobj['body']; name=ab['anchor']
            self.assertEqual(ab['nonce'],nonce); verify(self.q.pinned[name],b'R63-ANCHOR-READ',canon(ab),aobj['signature'])
            self.assertEqual(ab['checkpoint'],b['checkpoint'])
    def test_14_one_bad_anchor_signature_tolerated(self):
        a=self.anchors[0]; a.key=Ed25519PrivateKey.generate(); a.public=pub(a.key); self.assertEqual(self.w.status(),ACTIVE)
    def test_15_two_bad_anchor_signatures_hold(self):
        for a in self.anchors[:2]: a.key=Ed25519PrivateKey.generate(); a.public=pub(a.key)
        self.assertEqual(self.w.status(),HOLD)
    def test_16_wrong_witness_key_quarantined(self):
        wrong=Witness(self.identity,self.policy,self.w.path,Ed25519PrivateKey.generate(),self.q); self.assertEqual(wrong.status(),QUARANTINED)
    def test_17_no_implicit_reenrollment_after_history_loss(self):
        self.advance(); self.w.path.unlink(); same=Witness(self.identity,self.policy,self.w.path,self.wkey,self.q)
        with self.assertRaises(ContinuityError): same.provision_local(self.genesis_cp)
    def test_18_local_loss_at_genesis_retires_identity(self):
        self.w.path.unlink(); same=Witness(self.identity,self.policy,self.w.path,self.wkey,self.q)
        self.assertEqual(same.status(),QUARANTINED)
        with self.assertRaises(ContinuityError): same.provision_local(self.genesis_cp)
    def test_19_crash_after_external_init_marker_retires_identity(self):
        w,aa,q,ops,cp=self.fresh(); q.mark_initialized(w.identity,cp)
        self.assertEqual(w.status(),QUARANTINED)
        with self.assertRaises(ContinuityError): w.provision_local(cp)
    def test_20_partial_init_marker_can_complete_before_service(self):
        w,aa,q,ops,cp=self.fresh()
        for a in aa[:2]: a.mark_initialized(w.identity,cp)
        self.assertEqual(w.status(),HOLD); w.provision_local(cp); self.assertEqual(w.status(),ACTIVE)
    def test_21_duplicate_genesis_enrollment_rejected(self):
        with self.assertRaises(ContinuityError): self.q.provision(self.genesis_cp,self.operators)
    def test_22_anchor_refuses_fork_after_commit(self):
        self.advance(); fork=make_checkpoint(self.identity,self.policy,pub(self.wkey),1,self.genesis,sha(b'fork'),secrets.token_hex(32))
        with self.assertRaises(ContinuityError): self.q.commit(fork,sign(self.wkey,b'R63-WITNESS-CHECKPOINT',canon(fork)))
    def test_23_corrupt_local_state_quarantined(self):
        c=sqlite3.connect(self.w.path); c.execute('UPDATE local SET cp=? WHERE id=1',(b'{}',)); c.commit(); c.close(); self.assertEqual(self.w.status(),QUARANTINED)
    def test_24_two_of_four_anchor_reads_hold(self): self.assertEqual(self.w.status(available={'a1','a2'}),HOLD)
    def test_25_new_identity_new_key_is_required_for_replacement(self):
        self.advance(); self.w.path.unlink(); self.assertEqual(self.w.status(),QUARANTINED)
        key=Ed25519PrivateKey.generate(); ident='ario-r63-witness-02'; pol=sha(b'new-policy'); gen=sha(b'new-genesis')
        cp=make_checkpoint(ident,pol,pub(key),0,ZERO,gen,secrets.token_hex(32)); self.q.provision(cp,self.operators)
        replacement=Witness(ident,pol,self.root/'replacement.db',key,self.q); replacement.provision_local(cp)
        self.assertEqual(replacement.status(),ACTIVE); self.assertEqual(self.w.status(),QUARANTINED)
    def test_26_joint_rollback_all_anchors_and_local_state_RED(self):
        local=self.root/'local.genesis'; shutil.copy2(self.w.path,local); backs=[]
        for a in self.anchors:
            p=self.root/(a.name+'.genesis'); shutil.copy2(a.path,p); backs.append((a,p))
        self.advance()
        for a,p in backs: shutil.copy2(p,a.path)
        shutil.copy2(local,self.w.path); self.assertEqual(self.w.status(),ACTIVE)
        print('RED: joint rollback of all four anchor stores and local state is undetectable',flush=True)
    def test_27_three_anchor_rollback_one_missing_plus_local_RED(self):
        local=self.root/'local.genesis'; shutil.copy2(self.w.path,local); backs=[]
        for a in self.anchors[:3]:
            p=self.root/(a.name+'.genesis'); shutil.copy2(a.path,p); backs.append((a,p))
        self.advance()
        for a,p in backs: shutil.copy2(p,a.path)
        self.anchors[3].path.unlink(); shutil.copy2(local,self.w.path)
        self.assertEqual(self.w.status(),ACTIVE)
        print('RED: 3/4 anchor rollback plus one missing anchor and local rollback is undetectable',flush=True)
    @unittest.skipUnless(hasattr(os,'fork'),'requires process isolation')
    def test_28_real_process_exit_after_pending(self):
        pid=os.fork()
        if pid==0:
            w=Witness(self.identity,self.policy,self.w.path,self.wkey,self.q)
            try: w.transition(self.next_hash(),failpoint=lambda x: os._exit(77) if x=='after_local_pending' else None)
            except BaseException: os._exit(98)
            os._exit(99)
        _,st=os.waitpid(pid,0); self.assertEqual(os.waitstatus_to_exitcode(st),77); self.w.resume_pending(); self.assertEqual(self.w.status(),ACTIVE)
    @unittest.skipUnless(hasattr(os,'fork'),'requires process isolation')
    def test_29_real_process_exit_after_anchor_quorum(self):
        pid=os.fork()
        if pid==0:
            w=Witness(self.identity,self.policy,self.w.path,self.wkey,self.q)
            try: w.transition(self.next_hash(),failpoint=lambda x: os._exit(77) if x=='after_anchor_quorum' else None)
            except BaseException: os._exit(98)
            os._exit(99)
        _,st=os.waitpid(pid,0); self.assertEqual(os.waitstatus_to_exitcode(st),77); self.assertEqual(self.w.status(),ACTIVE)
    @unittest.skipUnless(hasattr(os,'fork'),'requires process isolation')
    def test_30_real_process_exit_after_local_commit(self):
        pid=os.fork()
        if pid==0:
            w=Witness(self.identity,self.policy,self.w.path,self.wkey,self.q)
            try: w.transition(self.next_hash(),failpoint=lambda x: os._exit(77) if x=='after_local_commit' else None)
            except BaseException: os._exit(98)
            os._exit(99)
        _,st=os.waitpid(pid,0); self.assertEqual(os.waitstatus_to_exitcode(st),77); self.assertEqual(self.w.status(),ACTIVE)

    def test_31_duplicate_anchor_signing_key_rejected(self):
        duplicate=Anchor('a4',self.root/'a4-duplicate-key.db',self.anchors[0].key,self.operators['a4'])
        with self.assertRaises(ContinuityError):
            AnchorQuorum([self.anchors[0],self.anchors[1],self.anchors[2],duplicate])
    def test_32_duplicate_anchor_enrollment_key_rejected(self):
        duplicate=Anchor('a4',self.root/'a4-duplicate-operator.db',self.anchors[3].key,self.operators['a1'])
        with self.assertRaises(ContinuityError):
            AnchorQuorum([self.anchors[0],self.anchors[1],self.anchors[2],duplicate])
    def test_33_duplicate_anchor_store_path_rejected(self):
        duplicate=Anchor('a4',self.anchors[0].path,self.anchors[3].key,self.operators['a4'])
        with self.assertRaises(ContinuityError):
            AnchorQuorum([self.anchors[0],self.anchors[1],self.anchors[2],duplicate])
    def test_34_duplicate_anchor_identity_rejected(self):
        duplicate=Anchor('a3',self.root/'a3-duplicate-name.db',Ed25519PrivateKey.generate(),self.operators['a4'])
        with self.assertRaises(ContinuityError):
            AnchorQuorum([self.anchors[0],self.anchors[1],self.anchors[2],duplicate])
    def test_35_one_replayed_nonce_response_is_not_counted(self):
        old_nonce=secrets.token_hex(32); replay=self.anchors[0].read(self.identity,old_nonce)
        self.anchors[0].read=lambda identity,nonce,replay=replay: replay
        cp,reads,init_count=self.q.latest(self.identity,secrets.token_hex(32))
        self.assertEqual(cp,self.genesis_cp); self.assertEqual(len(reads),3); self.assertEqual(init_count,3)
    def test_36_two_replayed_nonce_responses_cannot_form_quorum(self):
        old_nonce=secrets.token_hex(32)
        first=self.anchors[0].read(self.identity,old_nonce); second=self.anchors[1].read(self.identity,old_nonce)
        self.anchors[0].read=lambda identity,nonce,replay=first: replay
        self.anchors[1].read=lambda identity,nonce,replay=second: replay
        with self.assertRaises(ContinuityError):
            self.q.latest(self.identity,secrets.token_hex(32))
    def test_37_one_rolled_back_anchor_is_outvoted_by_three_current(self):
        backup=self.root/'a1-genesis.db'; shutil.copy2(self.anchors[0].path,backup)
        self.advance(); shutil.copy2(backup,self.anchors[0].path)
        self.assertEqual(self.w.status(),ACTIVE)

if __name__=='__main__': unittest.main(verbosity=2)
