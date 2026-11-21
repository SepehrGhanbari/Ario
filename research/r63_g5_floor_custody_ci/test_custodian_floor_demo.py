"""R63 G5 retained floor and same-admin fail-open negative regression tests."""
from __future__ import annotations
from pathlib import Path
import hashlib,sys,tempfile,unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
sys.path.insert(0,str(Path(__file__).resolve().parent))
import custodian_floor_demo as g5
import spend_chain_v2 as v2

def rows(count=3):
    raw=b'';events=[]
    for i in range(count):
        n=chr(ord('a')+i)*64;k=str(i+1)*64
        raw,s=v2.append(raw,n,k);assert s=='NEW_NEEDS_DURABLE_APPEND'
        events.append(v2.review(raw))
    return raw,events

class TestIndependentFloorSimulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert hashlib.sha256(Path(v2.__file__).read_bytes()).hexdigest()==g5.PIN
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.d=Path(tmp.name)
        self.key=Ed25519PrivateKey.generate()
        self.c=g5.SimulatedCustodian(self.d/'custodian.sqlite3',self.key)
        self.raw3,self.states=rows()
        self.r1=self.c.append('research_epoch_1',1,self.states[0].head,expected_prev=g5.genesis())
        prev=g5.sha(g5.canonical(self.r1.body)+self.r1.signature)
        self.r2=self.c.append('research_epoch_1',2,self.states[1].head,expected_prev=prev)
        prev=g5.sha(g5.canonical(self.r2.body)+self.r2.signature)
        self.r3=self.c.append('research_epoch_1',3,self.states[2].head,expected_prev=prev)
    def gate(self,raw,receipt,**kw):
        return g5.verify_latest(raw,receipt,kw.get('key',self.c.pub),kw.get('latest',self.c.latest()),kw.get('floor',3),'research_epoch_1')
    def test_positive_valid_latest(self):self.assertEqual(self.gate(self.raw3,self.r3),'EXTERNALLY_CONSISTENT_SIMULATION_ONLY_NO_SIGNING')
    def test_old_local_v2_rejected(self):self.assertEqual(self.gate(rows(2)[0],self.r3),'HOLD_ROLLBACK_OR_FORK')
    def test_old_signed_receipt_rejected(self):self.assertEqual(self.gate(rows(2)[0],self.r2),'HOLD_LOCAL_VERIFIER_FLOOR_REGRESSED')
    def test_old_receipt_even_when_local_min_old_rejected(self):self.assertEqual(self.gate(rows(2)[0],self.r2,floor=1),'HOLD_NOT_LAST_EXTERNAL_STATE')
    def test_offline_remote_floor_holds(self):self.assertEqual(self.gate(self.raw3,self.r3,latest=None),'HOLD_REMOTE_LATEST_UNAVAILABLE')
    def test_wrong_custodian_key_rejected(self):self.assertEqual(self.gate(self.raw3,self.r3,key=Ed25519PrivateKey.generate().public_key()),'HOLD_BAD_CUSTODIAN_SIGNATURE')
    def test_signed_bytes_tamper_rejected(self):
        bad=g5.Receipt({**self.r3.body,'head':'0'*64},self.r3.signature)
        self.assertEqual(self.gate(self.raw3,bad),'HOLD_BAD_CUSTODIAN_SIGNATURE')
    def test_same_seq_fork_rejected(self):
        f=v2.review(rows(2)[0]);h=v2.append(rows(2)[0],'d'*64,'4'*64)[0]
        self.assertEqual(self.gate(h,self.r3),'HOLD_ROLLBACK_OR_FORK')
    def test_gap_does_not_advance(self):
        prev=g5.sha(g5.canonical(self.r3.body)+self.r3.signature)
        with self.assertRaises(ValueError):self.c.append('research_epoch_1',5,'a'*64,expected_prev=prev)
    def test_stale_prev_does_not_advance(self):
        with self.assertRaises(ValueError):self.c.append('research_epoch_1',4,'a'*64,expected_prev=g5.genesis())
    def test_conflicting_seq_does_not_advance(self):
        prev=g5.sha(g5.canonical(self.r2.body)+self.r2.signature)
        with self.assertRaises(ValueError):self.c.append('research_epoch_1',3,'d'*64,expected_prev=prev)
    def test_custodian_restart_keeps_latest(self):
        c2=g5.SimulatedCustodian(self.d/'custodian.sqlite3',self.key)
        self.assertEqual(c2.latest(),self.c.latest())
    def test_negative_same_admin_replaces_custodian_and_public_key(self):
        # Counterexample: an attacker who owns BOTH local roots can roll back
        # the SQLite database, signing key and verifier pin. Not independently safe.
        with tempfile.TemporaryDirectory() as td:
            other=g5.SimulatedCustodian(Path(td)/'local_attacker_fake_custodian.sqlite3',Ed25519PrivateKey.generate())
            false_receipt=other.append('research_epoch_1',1,self.states[0].head,expected_prev=g5.genesis())
            self.assertEqual(g5.verify_latest(rows(1)[0],false_receipt,other.pub,other.latest(),0,'research_epoch_1'),'EXTERNALLY_CONSISTENT_SIMULATION_ONLY_NO_SIGNING')
    def test_rollback_remote_floor_if_verifier_pin_stays_rejected(self):
        old=self.c.latest()
        with tempfile.TemporaryDirectory() as td:
            other=g5.SimulatedCustodian(Path(td)/'fake.sqlite3',Ed25519PrivateKey.generate())
            r=other.append('research_epoch_1',1,self.states[0].head,expected_prev=g5.genesis())
            self.assertEqual(g5.verify_latest(rows(1)[0],r,self.c.pub,other.latest(),0,'research_epoch_1'),'HOLD_BAD_CUSTODIAN_SIGNATURE')
if __name__=='__main__':unittest.main(verbosity=2)
