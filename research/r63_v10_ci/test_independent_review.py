"""Independent offline review of the frozen original and proposed checked tripwire.
No CNG, no Windows Sandbox, no signer, no host keys. Each test is isolated.
"""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import reference_oracle_from_previous_research as prior
import r63_v10_tripwire_checked as checked
import r63_v10_tripwire as original

class V2Adapter:
    @staticmethod
    def review(raw):
        seq, head, pairs = prior.review_v2(raw)
        return SimpleNamespace(seq=seq, head=head, pairs=tuple(tuple(p) for p in pairs))
    @staticmethod
    def snapshot(pairs):
        return prior.snap(pairs)

class IndependentAudit(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='ario-v10-ind-')
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        self.v1=root/'spend.jsonl'
        self.v2=root/'spend-v2.jsonl'
        self.pairs=[['e'*64,'1'*64],['1'*64,'2'*64]]
        self.write_pairs(self.pairs)

    def write_pairs(self, pairs):
        self.v1.write_bytes(prior.fmt_pairs(pairs))
        raw=b''
        for nonce,ident in pairs: raw=prior.append_v2(raw,nonce,ident)
        self.v2.write_bytes(raw)

    def run_gate(self,mod=checked,**kwargs):
        opts=dict(v1_path=self.v1,v2_path=self.v2,in_memory_pairs=self.pairs,
                  broker_before=prior.snap(self.pairs),canonical=prior.canon,
                  digest=lambda x: prior.h(prior.canon(x)),spendv2=V2Adapter)
        opts.update(kwargs)
        return mod.compare_tripwire(**opts)

    def test_01_clean_v1_v2_memory_and_sorted_digest(self):
        self.assertEqual(self.run_gate().seq,2)

    def test_02_noncanonical_v1_holds(self):
        self.v1.write_bytes(self.v1.read_bytes().replace(b',',b', ',1))
        with self.assertRaises(checked.TripwireHold):self.run_gate()

    def test_03_v2_forged_event_hash_holds(self):
        raw=self.v2.read_bytes()
        self.v2.write_bytes(raw.replace(b'"hash":"',b'"hash":"f',1))
        with self.assertRaises(checked.TripwireHold):self.run_gate()

    def test_04_memory_append_order_mismatch_holds(self):
        with self.assertRaises(checked.TripwireHold):
            self.run_gate(in_memory_pairs=list(reversed(self.pairs)))

    def test_05_r60_content_digest_wrong_holds(self):
        with self.assertRaises(checked.TripwireHold):
            self.run_gate(broker_before='0'*64)

    def test_06_v1_v2_digest_order_separation(self):
        self.assertEqual(prior.snap(self.pairs),prior.snap(list(reversed(self.pairs))))
        raw=b''
        for n,k in reversed(self.pairs):raw=prior.append_v2(raw,n,k)
        self.assertNotEqual(V2Adapter.review(raw).head,self.run_gate().head)

    def test_07_original_tripwire_can_miss_v1_change_during_review(self):
        actual=original._read_bounded
        did_change=[False]
        def controlled(path,limit):
            if path==self.v2 and not did_change[0]:
                self.v1.unlink()
                did_change[0]=True
            return actual(path,limit)
        with mock.patch.object(original,'_read_bounded',side_effect=controlled):
            self.assertEqual(self.run_gate(mod=original).seq,2)
        self.assertFalse(self.v1.exists())
        self.assertTrue(did_change[0])

    def test_08_checked_tripwire_holds_if_v1_changes_during_review(self):
        actual=checked._read_bounded
        did_change=[False]
        def controlled(path,limit):
            if path==self.v2 and not did_change[0]:
                self.v1.unlink()
                did_change[0]=True
            return actual(path,limit)
        with mock.patch.object(checked,'_read_bounded',side_effect=controlled):
            with self.assertRaisesRegex(checked.TripwireHold,'MISSING_OR_UNREADABLE'):
                self.run_gate()
        self.assertFalse(self.v1.exists())

    def test_09_checked_tripwire_holds_if_v2_changes_during_review(self):
        actual=checked._read_bounded
        calls=[0]
        def controlled(path,limit):
            calls[0]+=1
            if path==self.v1 and calls[0]==3:
                self.v2.unlink()
            return actual(path,limit)
        with mock.patch.object(checked,'_read_bounded',side_effect=controlled):
            with self.assertRaisesRegex(checked.TripwireHold,'MISSING_OR_UNREADABLE'):
                self.run_gate()
        self.assertFalse(self.v2.exists())

    def test_10_missing_v1_holds(self):
        self.v1.unlink()
        with self.assertRaises(checked.TripwireHold):self.run_gate()

    def test_11_partial_v2_holds(self):
        self.v2.write_bytes(self.v2.read_bytes()[:-1])
        with self.assertRaises(checked.TripwireHold):self.run_gate()

    def test_12_unchanged_journal_bytes_after_clean_check(self):
        a,b=self.v1.read_bytes(),self.v2.read_bytes()
        self.run_gate()
        self.assertEqual((a,b),(self.v1.read_bytes(),self.v2.read_bytes()))

    def test_13_coherent_local_rollback_remains_undetectable(self):
        old_a,old_b=self.v1.read_bytes(),self.v2.read_bytes()
        self.write_pairs(self.pairs+[['7'*64,'3'*64]])
        self.v1.write_bytes(old_a); self.v2.write_bytes(old_b)
        # This accepted old state is a NEGATIVE CONTROL, not a security pass.
        self.assertEqual(self.run_gate().seq,2)

    def test_14_empty_bootstrap_vs_restored_to_empty_cannot_distinguish(self):
        self.pairs=[]
        self.write_pairs([])
        self.assertEqual(self.run_gate().seq,0)
        # In absence of a retained external floor, empty may also mean erased history.

    def test_15_not_protected_after_final_check(self):
        self.assertEqual(self.run_gate().seq,2)
        self.v1.unlink()
        # Check and use is NOT atomic; this is another negative control.
        self.assertFalse(self.v1.exists())

    def test_16_cross_disk_mismatch_mandatory_hold(self):
        self.v1.write_bytes(prior.fmt_pairs(self.pairs[:1]))
        with self.assertRaises(checked.TripwireHold):self.run_gate()

if __name__=='__main__':unittest.main(verbosity=2)
