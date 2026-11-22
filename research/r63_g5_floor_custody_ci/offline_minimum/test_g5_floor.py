"""Executable falsification tests, no keys and no network access."""
import base64,copy,hashlib,json,sys,unittest
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R))
import g5_retained_floor as g

def f(name):return (R/name).read_bytes()
CP=f('pinned_synthetic_seq3_checkpoint.json')
V1=f('synthetic_seq3_v1.jsonl'); V2=f('synthetic_seq3_v2.jsonl')
V1OLD=f('synthetic_rollback_seq2_v1.jsonl'); V2OLD=f('synthetic_rollback_seq2_v2.jsonl')

def fork():
 ev=g.rows(V2OLD);pairs=[[e['nonce'],e['id']] for e in ev]
 body={'version':g.VERSION,'seq':3,'prev':ev[-1]['hash'],'nonce':'d'*64,'id':'4'*64,
       'before':g.snapshot(pairs),'after':g.snapshot(pairs+[['d'*64,'4'*64]])}
 head=g.sha(g.DOMAIN+g.canon(body))
 return V1OLD+g.canon(['d'*64,'4'*64])+b'\n',V2OLD+g.canon({**body,'hash':head})+b'\n'

class Tests(unittest.TestCase):
 def test_pinned_sha_matches_public_checkpoint(self):self.assertTrue(g.pinned_checkpoint_ok(CP))
 def test_full_seq3_valid(self):self.assertEqual(g.verify_local(V1,V2)[:2],(3,g.PINNED_HEAD))
 def test_old_journals_are_fully_self_consistent(self):self.assertEqual(g.verify_local(V1OLD,V2OLD)[:2],(2,'cce8dfa45814ef13524b65f02d314a0841123fe310bdc3b745964d044d2b636a'))
 def test_seq2_rollback(self):self.assertEqual(g.verdict(V1OLD,V2OLD,CP,independent_pin_retained=True),'HOLD_ROLLBACK')
 def test_seq3_matching_prefix(self):self.assertEqual(g.verdict(V1,V2,CP,independent_pin_retained=True),'CONSISTENT_WITH_EXTERNAL_HISTORICAL_MINIMUM_ONLY_NOT_LATEST')
 def test_offline_pin_not_established(self):self.assertEqual(g.verdict(V1,V2,CP,independent_pin_retained=False),'HOLD_INDEPENDENT_PIN_NOT_ESTABLISHED')
 def test_seq3_fork_is_valid_locally_but_rejected(self):
  a,b=fork();self.assertEqual(g.verify_local(a,b)[0],3)
  self.assertEqual(g.verdict(a,b,CP,independent_pin_retained=True),'HOLD_FORK')
 def test_corrupted_checkpoint(self):self.assertEqual(g.verdict(V1,V2,CP+b' ',independent_pin_retained=True),'HOLD_BAD_PINNED_CHECKPOINT')
 def test_false_claimed_floor(self):
  r=json.loads(CP);r['seq']=2;bad=g.canon(r)
  self.assertEqual(g.verdict(V1OLD,V2OLD,bad,independent_pin_retained=True),'HOLD_BAD_PINNED_CHECKPOINT')
 def test_truncated_v2(self):self.assertEqual(g.verdict(V1,V2[:-1],CP,independent_pin_retained=True),'HOLD_LOCAL_JOURNAL_INVALID')
 def test_valid_v2_mismatched_v1(self):self.assertEqual(g.verdict(V1OLD,V2,CP,independent_pin_retained=True),'HOLD_LOCAL_JOURNAL_INVALID')
 def test_event_hash_tamper(self):
  b=V2.replace(b'"hash":"6e1d74',b'"hash":"0e1d74');self.assertEqual(g.verdict(V1,b,CP,independent_pin_retained=True),'HOLD_LOCAL_JOURNAL_INVALID')
 def test_seq4_extension_under_good_prefix(self):
  rows=g.rows(V2);oldpairs=[[e['nonce'],e['id']] for e in rows]
  body={'version':g.VERSION,'seq':4,'prev':g.PINNED_HEAD,'nonce':'d'*64,'id':'4'*64,
        'before':g.snapshot(oldpairs),'after':g.snapshot(oldpairs+[['d'*64,'4'*64]])}
  h=g.sha(g.DOMAIN+g.canon(body));v2=V2+g.canon({**body,'hash':h})+b'\n';v1=V1+g.canon(['d'*64,'4'*64])+b'\n'
  self.assertEqual(g.verdict(v1,v2,CP,independent_pin_retained=True),'CONSISTENT_WITH_EXTERNAL_HISTORICAL_MINIMUM_ONLY_NOT_LATEST')
 def test_two_heads_same_seq_not_equal(self):
  a,b=fork();self.assertNotEqual(g.verify_local(a,b)[1],g.PINNED_HEAD)
 def test_self_admin_pin_replacement_counterexample(self):
  # Counterexample, not passing gate: publisher can win by rewriting verifier constants.
  a,b=fork(); seq,head,prefix=g.verify_local(a,b)
  self.assertNotEqual(head,g.PINNED_HEAD)
  self.assertEqual(head,prefix) # A malicious unpinned verifier would accept its own new floor.
 def test_wrong_epoch_pin_rejected(self):
  bad=json.loads(CP);bad['epoch']='attacker_epoch';self.assertFalse(g.pinned_checkpoint_ok(g.canon(bad)))
if __name__=='__main__': unittest.main(verbosity=2)