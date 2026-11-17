#!/usr/bin/env python3
"""Researcher-designed, non-blind negative and positive tests using published W22 notes."""
from pathlib import Path
import json
import unittest
from w23_checkpoint_gossip import compare, gossip, read_signed_note, verify_compact_consistency

HERE=Path(__file__).parent
W22=json.loads((HERE/'W22_PUBLIC_SYNTHETIC_SIGNED_NOTES_2026-11-17.json').read_text('utf8'))
W20=json.loads((HERE/'W20_SYNTHETIC_LOG_CHECKPOINTS_AND_PROOFS_2026-11-17.json').read_text('utf8'))
KEY=W22['public_vkey_for_synthetic_demo_only']
OLD=W22['previous_checkpoint'].encode()
NEW=W22['current_checkpoint'].encode()
FORK=W22['same_signer_fork_checkpoint'].encode()
PROOF=W20['consistency_proof']

class W23(unittest.TestCase):
    def test_01_real_w22_signatures_and_distinct_roots(self):
        old,new,fork=[read_signed_note(x,KEY) for x in (OLD,NEW,FORK)]
        self.assertEqual([x['size'] for x in (old,new,fork)],[3,8,8])
        self.assertNotEqual(new['root'],fork['root'])
    def test_02_same_size_split_view_proven(self):
        r=compare(NEW,FORK,KEY)
        self.assertEqual(r['finding'],'SIGNED_EQUIVOCATION_PROVEN')
        self.assertEqual(len(r['evidence_note_sha256']),2)
    def test_03_fork_is_symmetric(self):
        self.assertEqual(compare(FORK,NEW,KEY)['finding'],'SIGNED_EQUIVOCATION_PROVEN')
    def test_04_valid_growth_proof(self):
        self.assertTrue(verify_compact_consistency(3,8,read_signed_note(OLD,KEY)['root'],read_signed_note(NEW,KEY)['root'],PROOF))
        self.assertEqual(compare(OLD,NEW,KEY,PROOF)['finding'],'CONSISTENT_GROWTH_NOT_FRESHNESS')
    def test_05_no_proof_underdetermined(self):
        self.assertEqual(compare(OLD,NEW,KEY)['finding'],'HOLD_MISSING_CONSISTENCY_PROOF')
    def test_06_bad_proof_not_fork_proof(self):
        bad=list(PROOF); bad[0]='0'*64
        self.assertEqual(compare(OLD,NEW,KEY,bad)['finding'],'HOLD_INVALID_PROOF_NOT_FORK_EVIDENCE')
    def test_07_retained_new_catches_old_rollback(self):
        self.assertEqual(compare(NEW,OLD,KEY)['finding'],'DENY_ROLLBACK_RELATIVE_TO_RETAINED')
    def test_08_both_old_is_not_freshness(self):
        self.assertEqual(compare(OLD,OLD,KEY)['finding'],'MATCHING_SIGNED_HEADS_NOT_FRESHNESS')
        self.assertEqual(gossip({'observer1':OLD,'observer2':OLD},KEY)['finding'],'OBSERVED_AGREEMENT_NOT_WORLD_FRESHNESS')
    def test_09_no_trusted_key_fails_closed(self):
        self.assertEqual(compare(NEW,FORK)['finding'],'HOLD_INVALID_NOTE_OR_UNPINNED_KEY')
    def test_10_tampered_note_fails_closed(self):
        changed=NEW.replace(b'\n8\n',b'\n7\n')
        self.assertEqual(gossip({'a':changed,'b':FORK},KEY)['finding'],'HOLD_INVALID_NOTE_OR_UNPINNED_KEY')
    def test_11_three_way_gossip_finds_split_view(self):
        x=gossip({'A':OLD,'B':NEW,'C':FORK},KEY)
        self.assertEqual(x['finding'],'SIGNED_EQUIVOCATION_PROVEN')
        self.assertEqual(x['view_labels_untrusted'],['B','C'])
    def test_12_different_sizes_not_automatically_fork(self):
        self.assertEqual(gossip({'A':OLD,'B':NEW},KEY)['finding'],'HOLD_DIFFERENT_SIZES_NEED_PAIRWISE_CONSISTENCY')
    def test_13_label_and_set_tricks_fail_closed(self):
        self.assertEqual(gossip({'x/../../':NEW,'b':FORK},KEY)['finding'],'HOLD_BAD_VIEW_SET')
        self.assertEqual(gossip({'only':NEW},KEY)['finding'],'HOLD_BAD_VIEW_SET')
        self.assertEqual(gossip({'a':NEW,'b':b'not a signed note'},KEY)['finding'],'HOLD_INVALID_NOTE_OR_UNPINNED_KEY')
    def test_14_no_authority_even_with_valid_gossip(self):
        for x in (compare(NEW,FORK,KEY),compare(OLD,NEW,KEY,PROOF),gossip({'A':NEW,'B':NEW},KEY)):
            self.assertEqual(x['operational_authority'],'NONE')
            self.assertEqual(x['latest_world_state'],'UNKNOWN')
            self.assertEqual(x['independently_administered_custody'],'NOT_ESTABLISHED')
            self.assertEqual(x['out_of_band_pin'],'NOT_ESTABLISHED')
            self.assertEqual(x['external_actions'],0)
            self.assertFalse(x['memory_admitted'])
    def test_15_wrong_public_key_rejected(self):
        self.assertIsNone(read_signed_note(NEW,KEY[:-1]+'A'))
        self.assertIsNone(read_signed_note(NEW,KEY.replace('ario-w22','other-log',1)))
    def test_16_bad_proof_types_rejected(self):
        old,new=read_signed_note(OLD,KEY),read_signed_note(NEW,KEY)
        for proof in ([],['0'*64]*17,['A'*64],['0'*63],['z'*64],None):
            self.assertFalse(verify_compact_consistency(3,8,old['root'],new['root'],proof))

if __name__=='__main__':
    unittest.main(verbosity=2)
