import os, secrets, tempfile, sqlite3, json, unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from cryptography.exceptions import InvalidSignature
from write_quorum import *

# Exact public envelope checksums discovered by #369, not raw snapshot hashes.
OLD='2125fe4baece1e50b46bd04c7810e079f25ce9307704cf428c9ced7309d89224'
NEW='910f24dfd153e31373a76011de7c3d84ac5fe3b7602a037bb323df3a1d00ef8c'
FORK='a'*64
FAIL=(ValueError,InvalidSignature,TypeError,KeyError,sqlite3.Error)

class Quorum(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.keys={n:Ed25519PrivateKey.generate() for n in NAMES}
        self.roster={n:pub(k) for n,k in self.keys.items()}; self.p=policy(self.roster,secrets.token_hex(32),OLD)
        self.ws=[Witness(self.root/(n+'.db'),self.p,n,self.keys[n]) for n in NAMES]
        self.fin=Finalizer(self.root/'final.db',self.p,NEW)
    def receipts(self,n=3): return [w.prepare(NEW) for w in self.ws[:n]]
    def blocked(self,rs):
        with self.assertRaises(FAIL): self.fin.finalize(rs)
        self.assertEqual(self.fin.status(),HOLD)
    def crash(self,fn,point):
        pid=os.fork()
        if pid==0:
            try: fn(lambda at: os._exit(77) if at==point else None)
            except BaseException: os._exit(99)
            os._exit(98)
        _,status=os.waitpid(pid,0); self.assertEqual(os.waitstatus_to_exitcode(status),77)
    def test_01_zero(self): self.blocked([])
    def test_02_one(self): self.blocked(self.receipts(1))
    def test_03_two(self): self.blocked(self.receipts(2))
    def test_04_three(self): self.fin.finalize(self.receipts()); self.assertEqual(self.fin.status(),FINAL)
    def test_05_four(self): self.fin.finalize(self.receipts(4)); self.assertEqual(self.fin.status(),FINAL)
    def test_06_duplicate(self):
        a,b=self.receipts(2); self.blocked([a,a,b])
    def test_07_wrong_target(self): self.blocked(self.receipts(2)+[self.ws[2].prepare(FORK)])
    def test_08_bad_sig(self):
        rs=self.receipts(); obj=decode(rs[2]); obj['signature']='0'*128; self.blocked(rs[:2]+[canon(obj)])
    def test_09_wrong_epoch(self):
        rs=self.receipts(2); p=policy(self.roster,secrets.token_hex(32),OLD); w=Witness(self.root/'other.db',p,'w3',self.keys['w3']); self.blocked(rs+[w.prepare(NEW)])
    def test_10_wrong_parent(self):
        rs=self.receipts(2); p=policy(self.roster,decode(self.p)['epoch'],FORK); w=Witness(self.root/'other.db',p,'w3',self.keys['w3']); self.blocked(rs+[w.prepare(NEW)])
    def test_11_same_key(self):
        r=dict(self.roster); r['w2']=r['w1'];
        with self.assertRaises(ValueError): policy(r,secrets.token_hex(32),OLD)
    def test_12_replay_exact(self):
        a=self.ws[0].prepare(NEW); self.assertEqual(a,self.ws[0].prepare(NEW)); self.blocked([a,a,a])
    def test_13_fork_lock(self):
        self.ws[0].prepare(NEW)
        with self.assertRaises(FAIL): self.ws[0].prepare(FORK)
    def test_14_concurrent_fork(self):
        def attempt(t):
            try: return self.ws[0].prepare(t)
            except FAIL: return None
        with ThreadPoolExecutor(2) as ex: results=list(ex.map(attempt,[NEW,FORK]))
        self.assertEqual(sum(x is not None for x in results),1)
    @unittest.skipUnless(hasattr(os,'fork'),'Linux process exit control')
    def test_15_witness_crash_before_commit(self):
        self.crash(lambda fp:self.ws[0].prepare(NEW,fp),'before_commit'); self.assertIsNone(stored(self.ws[0].path,self.ws[0].pin)); self.assertIsNotNone(self.ws[0].prepare(FORK))
    @unittest.skipUnless(hasattr(os,'fork'),'Linux process exit control')
    def test_16_witness_crash_after_commit(self):
        self.crash(lambda fp:self.ws[0].prepare(NEW,fp),'after_commit'); a=stored(self.ws[0].path,self.ws[0].pin); self.assertIsNotNone(a); self.assertEqual(a,self.ws[0].prepare(NEW));
        with self.assertRaises(FAIL): self.ws[0].prepare(FORK)
    @unittest.skipUnless(hasattr(os,'fork'),'Linux process exit control')
    def test_17_finalizer_crash_before_commit(self):
        rs=self.receipts(); self.crash(lambda fp:self.fin.finalize(rs,fp),'before_commit'); self.assertEqual(self.fin.status(),HOLD); n=secrets.token_hex(32); self.fin.recover(n,[w.read(n) for w in self.ws[:3]]); self.assertEqual(self.fin.status(),FINAL)
    @unittest.skipUnless(hasattr(os,'fork'),'Linux process exit control')
    def test_18_finalizer_crash_after_commit(self):
        rs=self.receipts(); self.crash(lambda fp:self.fin.finalize(rs,fp),'after_commit'); self.assertEqual(self.fin.status(),FINAL); self.assertEqual(self.fin.finalize(rs),stored(self.fin.path,self.fin.pin))
    def test_19_fresh_recovery_no_local_state(self):
        self.receipts(); n=secrets.token_hex(32); self.fin.recover(n,[w.read(n) for w in self.ws[:3]]); self.assertEqual(self.fin.status(),FINAL)
    def test_20_stale_nonce(self):
        self.receipts(); a,b=secrets.token_hex(32),secrets.token_hex(32);
        with self.assertRaises(FAIL): self.fin.recover(b,[w.read(a) for w in self.ws[:3]])
        self.assertEqual(self.fin.status(),HOLD)
    def test_21_three_reads_two_receipts(self):
        self.receipts(); n=secrets.token_hex(32)
        with self.assertRaises(FAIL): self.fin.recover(n,[self.ws[i].read(n) for i in (0,1,3)])
        self.assertEqual(self.fin.status(),HOLD)
    def test_22_duplicate_read(self):
        self.receipts(); n=secrets.token_hex(32); a,b=[w.read(n) for w in self.ws[:2]]
        with self.assertRaises(FAIL): self.fin.recover(n,[a,b,a])
    def test_23_read_conflict(self):
        self.receipts(); self.ws[3].prepare(FORK); n=secrets.token_hex(32)
        with self.assertRaises(FAIL): self.fin.recover(n,[w.read(n) for w in self.ws])
    def test_24_certificate_tamper(self):
        self.fin.finalize(self.receipts()); c=sqlite3.connect(self.fin.path); c.execute('UPDATE slot SET value=?',(b'{}',)); c.commit(); c.close()
        with self.assertRaises(FAIL): self.fin.status()
    def test_25_other_valid_subset_idempotent(self):
        rs=self.receipts(4); a=self.fin.finalize(rs[:3]); self.assertEqual(a,self.fin.finalize(rs[1:]))
    def test_26_db_policy_pin(self):
        self.ws[0].prepare(NEW); p=policy(self.roster,secrets.token_hex(32),OLD); w=Witness(self.ws[0].path,p,'w1',self.keys['w1'])
        with self.assertRaises(FAIL): w.prepare(NEW)
    def test_27_two_forks_no_final(self):
        a=[w.prepare(NEW) for w in self.ws[:2]]; b=[w.prepare(FORK) for w in self.ws[2:]]; self.blocked(a)
        with self.assertRaises(FAIL): certificate(self.p,proposal(self.p,FORK),b)
    def test_28_joint_reset_RED(self):
        self.fin.finalize(self.receipts()); old=stored(self.fin.path,self.fin.pin); self.assertEqual(self.fin.status(),FINAL)
        # Same administrator can erase all witness stores while keeping the keys.
        for w in self.ws[:3]: w.path.unlink()
        other=[w.prepare(FORK) for w in self.ws[:3]]; new=certificate(self.p,proposal(self.p,FORK),other)
        self.assertNotEqual(old,new); check_certificate(self.p,proposal(self.p,NEW),old); check_certificate(self.p,proposal(self.p,FORK),new)
        print('RED: joint witness reset permits two valid conflicting certificates',flush=True)
    def test_29_joint_reset_nonce_RED(self):
        self.receipts(); self.ws[0].path.unlink(); n=secrets.token_hex(32); raw=self.ws[0].read(n); self.assertIsNone(decode(raw)['body']['receipt']); self.assertEqual(decode(raw)['body']['nonce'],n)
        verify(self.roster['w1'],b'R63-READ',canon(decode(raw)['body']),decode(raw)['signature']); print('RED: reset witness signs fresh empty state',flush=True)

if __name__=='__main__': unittest.main(verbosity=2)
