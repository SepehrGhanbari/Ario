"""G5 cross-device MANUAL comparison test only; no OS custody claims."""
import unittest
from pathlib import Path
from g5_retained_floor import rows,canon,sha,snapshot,DOMAIN,VERSION,PINNED_HEAD
from g5_phone_manual_compare import compare
D=Path(__file__).parent
GOOD1=(D/'synthetic_seq3_v1.jsonl').read_bytes()
GOOD2=(D/'synthetic_seq3_v2.jsonl').read_bytes()
OLD1=(D/'synthetic_rollback_seq2_v1.jsonl').read_bytes()
OLD2=(D/'synthetic_rollback_seq2_v2.jsonl').read_bytes()

def fork():
    prev=rows(OLD2)[-1]['hash']
    pairs=[[e['nonce'],e['id']] for e in rows(OLD2)]
    n,k='d'*64,'4'*64
    body={'version':VERSION,'seq':3,'prev':prev,'nonce':n,'id':k,'before':snapshot(pairs),'after':snapshot(pairs+[[n,k]])}
    event={**body,'hash':sha(DOMAIN+canon(body))}
    return OLD1+canon([n,k])+b'\n',OLD2+canon(event)+b'\n'
class TestManualPhone(unittest.TestCase):
    def verdict(self,v1,v2,seq=3,head=PINNED_HEAD):return compare(v1,v2,reference_seq=seq,reference_head=head)
    def test_good_matching_local(self):self.assertEqual(self.verdict(GOOD1,GOOD2),'CONSISTENT_WITH_RETAINED_HISTORICAL_MINIMUM_NOT_LATEST')
    def test_old_chain_is_valid_locally(self):self.assertEqual(len(rows(OLD2)),2)
    def test_actual_seq2_rollback(self):self.assertEqual(self.verdict(OLD1,OLD2),'HOLD_ROLLBACK')
    def test_same_seq_fork(self):
        a,b=fork();self.assertEqual(self.verdict(a,b),'HOLD_FORK')
    def test_missing_phone_ref(self):self.assertEqual(compare(GOOD1,GOOD2,reference_seq=None,reference_head=None),'HOLD_NO_SEPARATE_REFERENCE')
    def test_bad_reference(self):self.assertEqual(self.verdict(GOOD1,GOOD2,seq=3,head='G'*64),'HOLD_INVALID_SEPARATE_REFERENCE')
    def test_bad_journal(self):self.assertEqual(self.verdict(GOOD1,GOOD2[:-1]),'HOLD_LOCAL_JOURNAL_INVALID')
    def test_extension_keeps_prefix(self):
        allpairs=[[r['nonce'],r['id']] for r in rows(GOOD2)]
        n,k='d'*64,'4'*64
        body={'version':VERSION,'seq':4,'prev':PINNED_HEAD,'nonce':n,'id':k,
            'before':snapshot(allpairs),'after':snapshot(allpairs+[[n,k]])}
        v2=GOOD2+canon({**body,'hash':sha(DOMAIN+canon(body))})+b'\n'
        v1=GOOD1+canon([n,k])+b'\n'
        self.assertEqual(self.verdict(v1,v2),'CONSISTENT_WITH_RETAINED_HISTORICAL_MINIMUM_NOT_LATEST')
if __name__=='__main__':unittest.main(verbosity=2)
