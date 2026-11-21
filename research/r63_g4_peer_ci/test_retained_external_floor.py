"""R63 G4 research-only retained floor. A local mock is NOT external custody.
This detects rollback/fork only with a verified fresh (seq, head) from outside
the claimant's control. No signer, real key, or external publication here.
"""
from __future__ import annotations
import hashlib,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'r63_g3_witness_ci'))
import spend_chain_v2 as v2
PIN="c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd"
def journal(ids):
    b=b""
    for n,k in ids:
        b,s=v2.append(b,n,k)
        assert s=="NEW_NEEDS_DURABLE_APPEND"
    return b
def gate(raw,floor,*,verified_external_receipt,fresh,use_state="NO_SIGNER_USE_REPRESENTED"):
    if not verified_external_receipt or not fresh or floor is None:
        return "HOLD_EXTERNAL_FLOOR_NOT_VERIFIED"
    try:v2.review(raw,external_anchor=floor)
    except (v2.Hold,ValueError):return "HOLD_ROLLBACK_OR_FORK"
    if use_state!="NO_SIGNER_USE_REPRESENTED":
        return "HOLD_SIGNER_USE_STATUS_UNKNOWN"
    return "CHECKPOINT_CONSISTENT_RESEARCH_ONLY"
class RetainedFloor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if hashlib.sha256(Path(v2.__file__).read_bytes()).hexdigest()!=PIN:
            raise RuntimeError("PIN_MISMATCH")
        cls.p2=journal([("a"*64,"1"*64),("b"*64,"2"*64)])
        cls.p3=journal([("a"*64,"1"*64),("b"*64,"2"*64),("c"*64,"3"*64)])
        cls.s2=v2.review(cls.p2);cls.s3=v2.review(cls.p3)
    def test_positive_with_external_floor(self):
        self.assertEqual(gate(self.p3,(self.s3.seq,self.s3.head),verified_external_receipt=True,fresh=True),"CHECKPOINT_CONSISTENT_RESEARCH_ONLY")
    def test_old_chain_rejected_against_retained_head(self):
        self.assertEqual(gate(self.p2,(self.s3.seq,self.s3.head),verified_external_receipt=True,fresh=True),"HOLD_ROLLBACK_OR_FORK")
    def test_same_seq_hidden_fork_rejected(self):
        fork=journal([("a"*64,"1"*64),("b"*64,"2"*64),("d"*64,"4"*64)])
        self.assertEqual(gate(fork,(self.s3.seq,self.s3.head),verified_external_receipt=True,fresh=True),"HOLD_ROLLBACK_OR_FORK")
    def test_absent_external_floor_hold(self):
        self.assertEqual(gate(self.p3,None,verified_external_receipt=False,fresh=True),"HOLD_EXTERNAL_FLOOR_NOT_VERIFIED")
    def test_stale_external_floor_hold(self):
        self.assertEqual(gate(self.p3,(self.s2.seq,self.s2.head),verified_external_receipt=True,fresh=False),"HOLD_EXTERNAL_FLOOR_NOT_VERIFIED")
    def test_unverified_self_controlled_floor_hold(self):
        self.assertEqual(gate(self.p2,(self.s2.seq,self.s2.head),verified_external_receipt=False,fresh=True),"HOLD_EXTERNAL_FLOOR_NOT_VERIFIED")
    def test_coherent_rollback_with_self_rolled_floor_is_counterexample(self):
        # This is a KNOWN NEGATIVE: replacing both local history and claimed floor
        # can fool purely local verification; never treat as antirollback proof.
        self.assertEqual(v2.review(self.p2,external_anchor=(self.s2.seq,self.s2.head)).seq,2)
    def test_signature_use_uncertainty_still_hold(self):
        self.assertEqual(gate(self.p3,(self.s3.seq,self.s3.head),verified_external_receipt=True,fresh=True,use_state="SIGNER_USE_UNKNOWN"),"HOLD_SIGNER_USE_STATUS_UNKNOWN")
if __name__=="__main__":unittest.main(verbosity=2)
