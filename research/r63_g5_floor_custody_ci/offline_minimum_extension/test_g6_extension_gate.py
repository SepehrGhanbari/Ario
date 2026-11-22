"""Independent negative controls for R63 G6 synthetic extension; NO signer."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import g6_extension_gate as m

ROOT=Path(__file__).resolve().parent
SRC=(ROOT/'spend_chain_v2.py' if (ROOT/'spend_chain_v2.py').exists() else ROOT.parent/'spend_chain_v2.py')
PIN={'epoch':m.PINNED_EPOCH,'seq':m.PINNED_SEQ,'head':m.PINNED_HEAD}

class TestG6PinnedSeq3Extension(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_v1=(ROOT/'g4_source_v1.jsonl').read_bytes()
        cls.original_v2=(ROOT/'g4_source_v2.jsonl').read_bytes()
        cls.next_v1,cls.next_v2=m.build_candidate(cls.original_v1,cls.original_v2,SRC)
        cls.mod=m.frozen_module(SRC)
    def decision(self,v1=None,v2=None,pin=None,confirmed=True):
        return m.assess(self.next_v1 if v1 is None else v1,
                        self.next_v2 if v2 is None else v2,
                        PIN if pin is None else pin,operator_reports_phone_is_separate=confirmed)
    def test_01_exact_frozen_v9_source(self):
        self.assertEqual(m.sha((SRC).read_bytes()),m.FROZEN_V9_SHA)
    def test_02_original_guest_raw_sha_pins(self):
        self.assertEqual(m.sha(self.original_v1),m.G4_RAW_V1_SHA)
        self.assertEqual(m.sha(self.original_v2),m.G4_RAW_V2_SHA)
    def test_03_original_guest_head_equals_phone(self):
        s=m.audited_journals(self.original_v1,self.original_v2)
        self.assertEqual((s['seq'],s['head']),(3,m.PINNED_HEAD))
    def test_04_only_one_bytewise_append(self):
        self.assertTrue(self.next_v1.startswith(self.original_v1))
        self.assertTrue(self.next_v2.startswith(self.original_v2))
        self.assertEqual(self.next_v1.count(b'\n')-self.original_v1.count(b'\n'),1)
        self.assertEqual(self.next_v2.count(b'\n')-self.original_v2.count(b'\n'),1)
    def test_05_canonical_seq4_chain_and_prefix(self):
        s=m.audited_journals(self.next_v1,self.next_v2)
        self.assertEqual((s['seq'],s['prefix_head']),(4,m.PINNED_HEAD))
    def test_06_exact_deterministic_new_head(self):
        self.assertEqual(m.audited_journals(self.next_v1,self.next_v2)['head'],
                         '52e1f33cf8bcf325a2cb817abe16473aa2e6a799fc76406b8cf831b912fd6d8c')
    def test_07_candidate_not_promoted(self):
        self.assertEqual(self.decision(),'CANDIDATE_EXTENDS_PINNED_SEQ3_ONLY_NOT_APPROVED_AS_LATEST')
    def test_08_no_phone_operator_claim_holds(self):
        self.assertEqual(self.decision(confirmed=False),'HOLD_PHONE_SEPARATION_NOT_ATTESTED')
    def test_09_missing_phone_reference_holds(self):
        self.assertEqual(m.assess(self.next_v1,self.next_v2,None,operator_reports_phone_is_separate=True),'HOLD_PHONE_REFERENCE_NOT_PROVIDED')
    def test_10_phone_floor_downgrade_claim_denied(self):
        self.assertEqual(self.decision(pin={**PIN,'seq':2,'head':m.audited_journals(self.original_v1[:272],self.original_v2[:990])['head']}),
                         'HOLD_PIN_REBOUND_OR_DOWNGRADED')
    def test_11_phone_floor_same_seq_rebind_denied(self):
        self.assertEqual(self.decision(pin={**PIN,'head':'f'*64}),'HOLD_PIN_REBOUND_OR_DOWNGRADED')
    def test_12_phone_floor_seq4_claim_denied_until_explicit_field_approval(self):
        self.assertEqual(self.decision(pin={**PIN,'seq':4}),'HOLD_PIN_REBOUND_OR_DOWNGRADED')
    def test_13_invalid_bool_seq_denied(self):
        self.assertEqual(self.decision(pin={**PIN,'seq':True}),'HOLD_PIN_REBOUND_OR_DOWNGRADED')
    def test_14_extra_untrusted_pin_field_denied(self):
        self.assertEqual(self.decision(pin={**PIN,'admin_override':1}),'HOLD_PIN_REBOUND_OR_DOWNGRADED')
    def test_15_replay_seq2_local_hold_rollback(self):
        self.assertEqual(self.decision(self.original_v1[:272],self.original_v2[:990]),'HOLD_ROLLBACK')
    def test_16_replay_seq3_no_new_event(self):
        self.assertEqual(self.decision(self.original_v1,self.original_v2),'PINNED_MINIMUM_PRESENT_NO_NEW_EVENT')
    def test_17_valid_coherent_branch_from_seq2_denied(self):
        # Recreate the entire third/fourth events canonically, with alternate
        # nonce and valid hashes. This is a *fully valid local fork*.
        v1=self.original_v1[:272];v2=self.original_v2[:990]
        for nonce,ident in [('e'*64,'5'*64),('d'*64,'4'*64)]:
            v2,status=self.mod.append(v2,nonce,ident)
            self.assertEqual(status,'NEW_NEEDS_DURABLE_APPEND')
            v1+=self.mod.canonical([nonce,ident])+b'\n'
        self.assertEqual(m.audited_journals(v1,v2)['seq'],4)
        self.assertEqual(self.decision(v1,v2),'HOLD_FORK')
    def test_18_corrupt_v2_hash_holds(self):
        self.assertEqual(self.decision(self.next_v1,self.next_v2.replace(b'"hash":"52e',b'"hash":"42e')),
                         'HOLD_LOCAL_JOURNAL_INVALID')
    def test_19_corrupt_v1_holds(self):
        self.assertEqual(self.decision(self.next_v1.replace(b'"dddddddd',b'"eeeeeeee'),self.next_v2),
                         'HOLD_LOCAL_JOURNAL_INVALID')
    def test_20_no_forged_orphan_v2(self):
        self.assertEqual(self.decision(self.original_v1,self.next_v2),'HOLD_LOCAL_JOURNAL_INVALID')
    def test_21_no_forged_orphan_v1(self):
        self.assertEqual(self.decision(self.next_v1,self.original_v2),'HOLD_LOCAL_JOURNAL_INVALID')
    def test_22_no_noncanonical_json(self):
        self.assertEqual(self.decision(self.next_v1.replace(b',',b', ',1),self.next_v2),'HOLD_LOCAL_JOURNAL_INVALID')
    def test_23_no_extra_unreviewed_seq5(self):
        raw,status=self.mod.append(self.next_v2,'e'*64,'5'*64)
        self.assertEqual(status,'NEW_NEEDS_DURABLE_APPEND')
        v1=self.next_v1+self.mod.canonical(['e'*64,'5'*64])+b'\n'
        self.assertEqual(self.decision(v1,raw),'HOLD_UNREVIEWED_MULTI_STEP_ADVANCE')
    def test_24_original_bytes_not_modified_after_build(self):
        self.assertEqual(m.sha((ROOT/'g4_source_v1.jsonl').read_bytes()),m.G4_RAW_V1_SHA)
        self.assertEqual(m.sha((ROOT/'g4_source_v2.jsonl').read_bytes()),m.G4_RAW_V2_SHA)
    def test_25_wrong_original_g4_refuses_builder(self):
        with self.assertRaisesRegex(ValueError,'HOLD_G4_ORIGINAL_BYTES_CHANGED'):
            m.build_candidate(self.next_v1,self.next_v2,SRC)
    def test_26_missing_newline_fails(self):
        self.assertEqual(self.decision(self.next_v1[:-1],self.next_v2),'HOLD_LOCAL_JOURNAL_INVALID')
    def test_27_same_authentic_seq4_replayed_does_not_promote_phone(self):
        self.assertEqual(m.PINNED_SEQ,3)
        self.assertEqual(self.decision(),'CANDIDATE_EXTENDS_PINNED_SEQ3_ONLY_NOT_APPROVED_AS_LATEST')
        self.assertEqual(self.decision(self.original_v1,self.original_v2),'PINNED_MINIMUM_PRESENT_NO_NEW_EVENT')
    def test_28_pinned_frozen_v9_source_mismatch_holds(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'sidecar.py';p.write_bytes(b'# altered V9 file\n')
            with self.assertRaisesRegex(ValueError,'HOLD_FROZEN_V9_SOURCE_CHANGED'):
                m.frozen_module(p)

if __name__=='__main__':unittest.main(verbosity=2)