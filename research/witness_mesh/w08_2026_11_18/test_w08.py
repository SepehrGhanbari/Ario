"""Independent negative oracle over existing fixed W22 signed notes; NO SIGNING."""
import base64
import copy
import json
from pathlib import Path
import random
import unittest

from w08_signed_note_gate import verify_log_note, read_only_assess

FX = json.loads((Path(__file__).parent / 'fixture_w22_excerpt.json').read_text('utf-8'))
ORIGIN = FX['origin']
KEY = FX['public_vkey']
C = FX['current'].encode('utf-8')
P = FX['previous'].encode('utf-8')
F = FX['same_size_fork'].encode('utf-8')

class Witness08(unittest.TestCase):
    def verdict(self, candidate=C, old=P, claims=None):
        return read_only_assess(candidate,log_public_key=KEY,origin=ORIGIN,
                                local_retained=old,submitted_claims=claims)

    def test_01_original_previous_note_crypto(self):
        h=verify_log_note(P,KEY,ORIGIN); self.assertIsNotNone(h); self.assertEqual(h.size,3)
    def test_02_original_current_note_crypto(self):
        h=verify_log_note(C,KEY,ORIGIN); self.assertIsNotNone(h); self.assertEqual(h.size,8)
    def test_03_original_signed_fork_note_crypto(self):
        h=verify_log_note(F,KEY,ORIGIN); self.assertIsNotNone(h); self.assertEqual(h.size,8)
    def test_04_exact_origin_binding(self):
        self.assertIsNone(verify_log_note(C,KEY,ORIGIN+'/new'))
    def test_05_same_signature_wrong_syntactic_name(self):
        self.assertIsNone(verify_log_note(C,KEY.replace('synthetic-log','synthetic-log2'),ORIGIN))
    def test_06_keyid_mutation(self):
        bad=KEY.replace('+299a48f8+','+00000000+')
        self.assertIsNone(verify_log_note(C,bad,ORIGIN))
    def test_07_note_root_mutation(self):
        x=C.replace(b'/oVYTQgedPrcn6BQx88eKcG8AmOUB7/5vUt4s1vcs5I=',
                    b'/pVYTQgedPrcn6BQx88eKcG8AmOUB7/5vUt4s1vcs5I=')
        self.assertNotEqual(x,C)
        self.assertIsNone(verify_log_note(x,KEY,ORIGIN))
    def test_08_note_raw_mutation(self):
        x=C.replace(b'\n8\n',b'\n9\n'); self.assertIsNone(verify_log_note(x,KEY,ORIGIN))
    def test_09_duplicate_signature_line(self):
        x=C+C.split(b'\n\n')[1]; self.assertIsNone(verify_log_note(x,KEY,ORIGIN))
    def test_10_trailing_blank_line(self):
        self.assertIsNone(verify_log_note(C+b'\n',KEY,ORIGIN))
    def test_11_empty_or_bad_types(self):
        for x in (None,'',b'',{},[],False,23): self.assertIsNone(verify_log_note(x,KEY,ORIGIN))
    def test_12_old_note_relative_to_current_pin(self):
        self.assertEqual(self.verdict(P,C)['decision'],'HOLD_OLD_VIEW_RELATIVE_TO_LOCAL_REFERENCE')
    def test_13_self_same_view_is_not_fresh(self):
        self.assertEqual(self.verdict(C,C)['decision'],'HISTORICAL_MATCH_NOT_WORLD_FRESHNESS')
    def test_14_signed_same_size_fork_is_detected(self):
        a=self.verdict(F,C)
        self.assertEqual(a['decision'],'CONFLICT_SAME_SIGNER_SAME_SIZE_DIFFERENT_ROOT')
        self.assertEqual(a['log_note_crypto'],'VALID_FOR_CALLER_SUPPLIED_KEY_ONLY')
    def test_15_reverse_fork_is_detected(self):
        self.assertEqual(self.verdict(C,F)['decision'],'CONFLICT_SAME_SIGNER_SAME_SIZE_DIFFERENT_ROOT')
    def test_16_unsigned_growth_is_not_proved_consistent(self):
        self.assertEqual(self.verdict(C,P)['decision'],'HOLD_GROWTH_WITHOUT_CONSISTENCY_PROOF')
    def test_17_absent_retained_reference(self):
        self.assertEqual(self.verdict(C,None)['decision'],'HOLD_NO_PREVIOUSLY_RETAINED_REFERENCE')
    def test_18_untrusted_retained_reference(self):
        self.assertEqual(self.verdict(C,b'bad')['decision'],'HOLD_INVALID_RETAINED_REFERENCE')
    def test_19_fake_external_witness_assertions_never_trusted(self):
        a=self.verdict(claims={'cosignatures':['approved']*100,'verified':True})
        self.assertEqual(a['external_witness_cosignature'],'NOT_PRESENT_OR_VERIFIED')
        self.assertEqual(a['independent_operator_custody'],'NOT_ESTABLISHED')
    def test_20_fake_oob_pin_assertions_never_trusted(self):
        a=self.verdict(claims={'oob':{'verified':True,'root':'independent','operator':'separate'}})
        self.assertEqual(a['oob_key_pin'],'NOT_ESTABLISHED')
    def test_21_fake_rotation_is_not_accepted(self):
        a=self.verdict(claims={'old_key_revoked':True,'new_epoch':999,'key_provenance':'oob'})
        self.assertEqual(a['oob_key_pin'],'NOT_ESTABLISHED')
    def test_22_caller_clock_does_not_establish_freshness(self):
        a=self.verdict(P,P,claims={'claimed_current_unix':9999999999,'fresh':True})
        self.assertEqual(a['world_freshness'],'UNKNOWN')
    def test_23_false_guarantee_of_completeness_is_not_accepted(self):
        a=self.verdict(claims={'missing_event_17':False,'source_completeness':'PROVED'})
        self.assertEqual(a['source_completeness'],'UNKNOWN')
    def test_24_fake_100_admins_cannot_vote(self):
        a=self.verdict(claims={'witness_admins':[f'admin{i}' for i in range(100)],'quorum':100})
        self.assertEqual(a['independent_operator_custody'],'NOT_ESTABLISHED')
    def test_25_math_valid_never_authorization(self):
        self.assertEqual(self.verdict(C,C)['authority'],'NONE')
    def test_26_no_issued_signatures_or_external_calls(self):
        a=self.verdict();self.assertEqual(a['external_actions'],0);self.assertEqual(a['signatures_issued'],0)
    def test_27_fuzz_mutated_signatures_fail_or_hold(self):
        rng=random.Random(281126)
        for i in range(450):
            m=bytearray(C); pos=rng.randrange(len(m)); m[pos]^=rng.choice((1,2,8,32))
            q=verify_log_note(bytes(m),KEY,ORIGIN)
            self.assertIsNone(q, f'mutation {i} pos {pos} accepted')
    def test_28_fuzz_claims_never_promote(self):
        rng=random.Random(81118)
        for i in range(500):
            claims={'fresh':rng.choice([True, False, 'TRUE', 'YES']),
                    'pinned_verified':rng.choice([True,1,'verified']),
                    'independent_witnesses':rng.randrange(0,1000),
                    'revoked':rng.choice([True,'accepted'])}
            a=self.verdict(C,C,claims)
            self.assertEqual(a['authority'],'NONE');self.assertEqual(a['world_freshness'],'UNKNOWN')
    def test_29_invalid_current_note_not_promoted_by_claims(self):
        a=self.verdict(b'invalid',C,{'crypto_ok':True,'approved':True})
        self.assertEqual(a['log_note_crypto'],'NOT_VERIFIED')
    def test_31_explicit_hold_even_with_matching_valid_signed_head(self):
        a=self.verdict(C,C)
        self.assertEqual(a['status'],'HOLD_NO_EXTERNAL_TRUST')
        self.assertEqual(a['external_witness_cosignature'],'NOT_PRESENT_OR_VERIFIED')
    def test_32_explicit_hold_even_with_two_valid_conflicting_heads(self):
        a=self.verdict(F,C)
        self.assertEqual(a['status'],'HOLD_NO_EXTERNAL_TRUST')
        self.assertEqual(a['decision'],'CONFLICT_SAME_SIGNER_SAME_SIZE_DIFFERENT_ROOT')
    def test_30_verify_matches_known_root_bytes(self):
        self.assertEqual(verify_log_note(C,KEY,ORIGIN).root.hex(),base64.b64decode('/oVYTQgedPrcn6BQx88eKcG8AmOUB7/5vUt4s1vcs5I=').hex())

if __name__=='__main__': unittest.main(verbosity=2)
