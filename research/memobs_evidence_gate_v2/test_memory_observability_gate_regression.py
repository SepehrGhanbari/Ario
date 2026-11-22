"""Focused synthetic negative + legitimate positive for MEM-OBS-01 V2.
Run against a named fixture with --source to verify RED on original/GREEN on patched.
"""
import argparse
import importlib.util
import unittest
from pathlib import Path

PARSER=argparse.ArgumentParser()
PARSER.add_argument('--source',default=str(Path(__file__).with_name('test_memory_observability_evidence_gate_fixed.py')))
ARGS=PARSER.parse_args()
source=Path(ARGS.source).resolve()
spec=importlib.util.spec_from_file_location('target_memobs_demo',source)
demo=importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)

class EvidenceGateRegression(unittest.TestCase):
    def item(self, identity, kind, evidence='FAKE_BYTES', source_id='self_claimed'):
        return demo.MemoryRecord(identity, identity, f'claim {identity}', kind, source_id, raw_evidence=evidence)

    def test_forged_empirical_payload_is_not_supported(self):
        item=self.item('forged_probe',demo.ProvenanceType.LOCAL_EMPIRICAL,'{"result":"success"}')
        self.assertEqual(item.status, demo.EpistemicStatus.RECORDED)
        self.assertIsNotNone(item.sha256)

    def test_forged_witness_label_is_not_supported(self):
        item=self.item('forged_witness',demo.ProvenanceType.SIGNED_WITNESS,'signature: not a real signature')
        self.assertEqual(item.status,demo.EpistemicStatus.RECORDED)
        self.assertIn('not authenticated',item.epistemic_limit)

    def test_test_fixture_with_fake_evidence_is_not_supported(self):
        item=self.item('synthetic',demo.ProvenanceType.SYNTHETIC_TEST,'testing')
        self.assertEqual(item.status,demo.EpistemicStatus.RECORDED)

    def test_local_recorded_is_useful_positive_and_not_always_unknown(self):
        journal=demo.ObservableMemoryJournal()
        item=self.item('legitimate_local_receipt',demo.ProvenanceType.LOCAL_EMPIRICAL,'{"errno":0}')
        journal.ingest(item)
        self.assertEqual(item.status,demo.EpistemicStatus.RECORDED)
        self.assertEqual(len(journal.history),1)
        self.assertEqual(journal.history[0].sha256,item.sha256)

    def test_self_assigned_supported_before_ingest_rejected(self):
        journal=demo.ObservableMemoryJournal()
        item=self.item('self_support',demo.ProvenanceType.LOCAL_EMPIRICAL)
        with self.assertRaisesRegex(AttributeError,'status is read-only'):
            item.status=demo.EpistemicStatus.SUPPORTED
        self.assertEqual(item.status,demo.EpistemicStatus.RECORDED)
        journal.ingest(item)
        self.assertEqual(len(journal.history),1)

    def test_self_assigned_accepted_before_ingest_rejected(self):
        journal=demo.ObservableMemoryJournal()
        item=self.item('self_accept',demo.ProvenanceType.LOCAL_EMPIRICAL)
        with self.assertRaisesRegex(AttributeError,'status is read-only'):
            item.status=demo.EpistemicStatus.ACCEPTED
        self.assertEqual(item.status,demo.EpistemicStatus.RECORDED)
        journal.ingest(item)
        self.assertEqual(len(journal.history),1)

    def test_self_assigned_supported_after_ingest_rejected(self):
        journal=demo.ObservableMemoryJournal()
        item=self.item('post_ingest',demo.ProvenanceType.LOCAL_EMPIRICAL)
        journal.ingest(item)
        with self.assertRaisesRegex(AttributeError,'status is read-only'):
            item.status=demo.EpistemicStatus.SUPPORTED
        self.assertEqual(journal.history[0].status,demo.EpistemicStatus.RECORDED)

    def test_private_state_mutation_before_ingest_rejected(self):
        journal=demo.ObservableMemoryJournal()
        item=self.item('private_spoof',demo.ProvenanceType.LOCAL_EMPIRICAL)
        item._status=demo.EpistemicStatus.SUPPORTED
        with self.assertRaisesRegex(ValueError,'HOLD_UNAUTHORIZED_STATUS_AT_INGEST'):
            journal.ingest(item)
        self.assertEqual(len(journal.history),0)

    def test_demo_has_no_positive_supported_promotion_method(self):
        item=self.item('support_grant',demo.ProvenanceType.LOCAL_EMPIRICAL)
        with self.assertRaisesRegex(ValueError,'HOLD_UNAUTHORIZED_STATUS_TRANSITION'):
            item._diagnostic_transition(demo.EpistemicStatus.SUPPORTED, 'fake support')
        self.assertEqual(item.status,demo.EpistemicStatus.RECORDED)

    def test_missing_provenance_fails_closed(self):
        item=self.item('missing',demo.ProvenanceType.MISSING,'fake proof',source_id='')
        self.assertEqual(item.status,demo.EpistemicStatus.UNKNOWN)

    def test_ai_claim_quarantined_even_with_bytes(self):
        item=self.item('narrative',demo.ProvenanceType.AI_GENERATED,'fake proof')
        self.assertEqual(item.status,demo.EpistemicStatus.UNSUPPORTED)

    def test_conflicting_records_remain_contested_without_upgrade(self):
        journal=demo.ObservableMemoryJournal()
        a=demo.MemoryRecord('a','same-concept','claim A',demo.ProvenanceType.LOCAL_EMPIRICAL,'source-A','a')
        b=demo.MemoryRecord('b','same-concept','claim B',demo.ProvenanceType.LOCAL_EMPIRICAL,'source-B','b')
        journal.ingest(a);journal.ingest(b)
        self.assertEqual((a.status,b.status),(demo.EpistemicStatus.CONTESTED,demo.EpistemicStatus.CONTESTED))

    def test_revision_preserves_claim_but_does_not_upgrade(self):
        journal=demo.ObservableMemoryJournal()
        record=self.item('old',demo.ProvenanceType.LOCAL_EMPIRICAL,'port=8080')
        journal.ingest(record)
        newer=journal.revise('old','port=8443','port=8443','claimed-source')
        self.assertEqual(newer.status,demo.EpistemicStatus.RECORDED)
        self.assertEqual(record.assertion,'claim old')
        self.assertEqual(newer.parent_id,'old')

    def test_rollback_marker_is_not_verified_evidence(self):
        journal=demo.ObservableMemoryJournal()
        event=journal.rollback('prior','recovery-test')
        self.assertEqual(event.status,demo.EpistemicStatus.RECORDED)
        self.assertEqual(len(journal.history),1)

if __name__=='__main__': unittest.main(argv=[__file__], verbosity=2)
