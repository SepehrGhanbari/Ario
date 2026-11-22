"""Research-only RF05 tests; Python stdlib; all journals under TemporaryDirectory."""
from __future__ import annotations
import copy
import hashlib
import sys
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
# Local artifact bundle mirrors the existing GitHub RF01 source; no newer memory engine.
for candidate in (ROOT.parent / 'recall_first_01', ROOT.parent / 'pinned_rf01',
                  ROOT.parent / 'research' / 'recall_first_01'):
    if (candidate / 'recall_first_lab.py').exists():
        sys.path.insert(0, str(candidate))
        break
from recall_first_lab import AnswerRecallLab
from equivalence_read_view import (EquivalenceReadView, ReviewHold, digest,
                                   review_event, semantic_contrast, propose_candidate)


class RF05(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='rf05-tests-')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'existing_answers.jsonl'
        self.lab = AnswerRecallLab(self.path)
        self.answer_id = self.lab.record_answer('Why did we preserve the archive?',
                         'We agreed to keep the previous history intact.',
                         scope='project/ario', source_ref='discussion:record-001')
        self.baseline = self.path.read_bytes()
        self.question = 'What was the reason we kept the archive?'

    def grant(self, *, question=None, original=None, answer_id=None, version=1,
              scope='project/ario', binding_id='eq-001', basis_ref='research-review-001'):
        return review_event('0'*64, 1, kind='GRANT', binding_id=binding_id,
                            basis_ref=basis_ref, reviewer_label='synthetic-reviewer',
                            rationale='Human-curated synthetic paraphrase pair for lab only',
                            scope=scope, question=question or self.question,
                            original_question=original or 'Why did we preserve the archive?',
                            answer_id=answer_id or self.answer_id,
                            answer_version=version,
                            journal_sha256=hashlib.sha256(self.path.read_bytes()).hexdigest())

    def view(self, events=(), *, floor='AUTO', pins='AUTO'):
        events = list(events)
        pinned_floor = (len(events), events[-1]['digest'] if events else '0'*64) if floor == 'AUTO' else floor
        pinned_reviews = {x['basis_ref']:x['digest'] for x in events} if pins == 'AUTO' else pins
        return EquivalenceReadView(self.path, events, pinned_floor=pinned_floor,
                                   pinned_review_digests=pinned_reviews)

    def test_exact_original_without_review(self):
        r = self.view().recall('Why did we preserve the archive?', scope='project/ario')
        self.assertEqual(r['disposition'], 'RECALLED_EXACT_ORIGINAL')
        self.assertEqual(r['source_ref'], 'discussion:record-001')
        self.assertEqual(r['effective_assessment'], 'NOT_EVALUATED')

    def test_trivial_normalization_original_question(self):
        r = self.view().recall('   why DID WE preserve the archive?! ', scope='project/ario')
        self.assertEqual(r['disposition'], 'RECALLED_EXACT_ORIGINAL')

    def test_paraphrase_requires_review(self):
        self.assertEqual(self.view().recall(self.question, scope='project/ario')['disposition'], 'UNKNOWN_MISSING')

    def test_candidate_proposer_never_promotes(self):
        r = propose_candidate('Why did we preserve the archive?', self.question)
        self.assertEqual(r, {'disposition':'CANDIDATE_NEEDS_REVIEW', 'equivalent':None})

    def test_reviewed_pair_bounded_recall(self):
        ev=self.grant(); view=self.view([ev]); r=view.recall(self.question,scope='project/ario')
        self.assertEqual(r['disposition'], 'RECALLED_LAB_REVIEWED_EQUIVALENCE')
        self.assertEqual(r['answer_id'], self.answer_id)
        self.assertEqual(r['equivalence']['review_event_digest'], ev['digest'])
        self.assertEqual(r['equivalence']['review_authenticity'], 'PIN_MATCH_IN_TEST_HARNESS_NOT_INDEPENDENTLY_ATTESTED')
        self.assertEqual(r['effective_assessment'], 'NOT_EVALUATED')

    def test_repeat_100_no_recompute_no_evidence_promotion(self):
        e=self.grant(); v=self.view([e]); expected=v.recall(self.question,scope='project/ario')
        for _ in range(100):
            r=v.recall(self.question,scope='project/ario')
            self.assertEqual(r['answer_id'],expected['answer_id'])
            self.assertEqual(r['evidence_promotions'],0)
            self.assertEqual(r['recompute_calls'],0)
        self.assertEqual(self.path.read_bytes(),self.baseline)
        self.assertEqual(v.lookups,101)

    def test_cross_language_curated_pair(self):
        e=self.grant(question='دلیل حفظ آرشیو چه بود؟')
        self.assertEqual(self.view([e]).recall('دلیل حفظ آرشیو چه بود؟',scope='project/ario')['disposition'],
                         'RECALLED_LAB_REVIEWED_EQUIVALENCE')

    def test_unreviewed_cross_language_hold(self):
        self.assertEqual(self.view().recall('دلیل حفظ آرشیو چه بود؟',scope='project/ario')['disposition'], 'UNKNOWN_MISSING')

    def test_wrong_topic_not_authorized_even_with_review(self):
        e=self.grant(question='Why is the pizza recipe preserved?')
        self.assertEqual(self.view([e]).recall('Why is the pizza recipe preserved?',scope='project/ario')['disposition'],
                         'HOLD_TOPIC_CONTRAST')

    def test_wrong_question_intent_not_authorized(self):
        e=self.grant(question='When did we preserve the archive?')
        self.assertEqual(self.view([e]).recall(e['question'],scope='project/ario')['disposition'],
                         'HOLD_INTENT_CONTRAST')

    def test_wrong_polarity_not_authorized(self):
        e=self.grant(question='Why did we not preserve the archive?')
        self.assertEqual(self.view([e]).recall(e['question'],scope='project/ario')['disposition'],
                         'HOLD_POLARITY_CONTRAST')

    def test_high_overlap_swapped_roles_still_refused_even_with_lab_review(self):
        # PAWS-style near-identical words need role checks, not bag-of-words.
        aid=self.lab.record_answer('Did Alice pay Bob?', 'Yes', scope='roles',source_ref='synthetic-case')
        e=self.grant(question='Did Bob pay Alice?', original='Did Alice pay Bob?',
                     answer_id=aid,scope='roles')
        self.assertEqual(self.view([e]).recall(e['question'],scope='roles')['disposition'],
                         'HOLD_ORDER_SENSITIVE_PARAPHRASE')

    def test_numeric_slot_mismatch_not_authorized(self):
        aid=self.lab.record_answer('What is 2 plus 2?', '4', scope='math',source_ref='session-x')
        e=self.grant(question='What is 2 plus 3?', original='What is 2 plus 2?',
                     answer_id=aid,scope='math')
        self.assertEqual(self.view([e]).recall(e['question'],scope='math')['disposition'],
                         'HOLD_NUMERIC_SLOT_CONTRAST')

    def test_a_different_question_not_connected_transitively(self):
        e=self.grant(); v=self.view([e]); self.assertEqual(
            v.recall('Please explain the archive policy?',scope='project/ario')['disposition'],'UNKNOWN_MISSING')

    def test_current_truth_request_stable_recheck(self):
        e=self.grant(); v=self.view([e]); r=v.recall(self.question,scope='project/ario',mode='CURRENT_FACT')
        self.assertEqual(r['disposition'],'RECHECK_REQUIRED')
        self.assertIsNone(r['answer'])

    def test_mislabeled_historical_with_now_rechecks(self):
        # Even a reviewed 'now' alias cannot bypass current-intent detector.
        e=self.grant(question='Is the archive policy still valid now?')
        r=self.view([e]).recall(e['question'],scope='project/ario',mode='HISTORICAL')
        self.assertEqual(r['disposition'],'RECHECK_REQUIRED')

    def test_persian_honuz_requires_recheck(self):
        e=self.grant(question='آیا این تصمیم هنوز معتبر است؟')
        r=self.view([e]).recall(e['question'],scope='project/ario')
        self.assertEqual(r['disposition'],'RECHECK_REQUIRED')

    def test_scope_mismatch(self):
        e=self.grant(); self.assertEqual(self.view([e]).recall(self.question,scope='private')['disposition'], 'UNKNOWN_MISSING')

    def test_missing_review_floor(self):
        e=self.grant(); self.assertEqual(self.view([e],floor=None).recall(self.question,scope='project/ario')['disposition'],
                         'HOLD_REVIEW_FLOOR_MISSING_OR_STALE')

    def test_wrong_review_floor(self):
        e=self.grant(); self.assertEqual(self.view([e],floor=(1,'0'*64)).recall(self.question,scope='project/ario')['disposition'],
                         'HOLD_REVIEW_FLOOR_MISSING_OR_STALE')

    def test_wrong_review_ticket_pin(self):
        e=self.grant(); self.assertEqual(self.view([e],pins={'research-review-001':'f'*64}).recall(self.question,scope='project/ario')['disposition'],
                         'HOLD_UNPINNED_REVIEW')

    def test_label_is_not_actor_authentication(self):
        e=self.grant(); r=self.view([e]).recall(self.question,scope='project/ario')
        self.assertNotIn(r['effective_assessment'], ('SUPPORTED','ACCEPTED'))
        self.assertIn('NOT_INDEPENDENTLY_ATTESTED',r['equivalence']['review_authenticity'])

    def revoked(self):
        e=self.grant(); revoke=review_event(e['digest'],2,kind='REVOKE',binding_id=e['binding_id'],
                                 basis_ref='research-revoke-002', reviewer_label='synthetic-reviewer',
                                 rationale='This paraphrase was challenged', revokes_digest=e['digest'])
        return [e,revoke]

    def test_revocation_blocks_old_link(self):
        events=self.revoked(); v=self.view(events)
        self.assertEqual(v.recall(self.question,scope='project/ario')['disposition'], 'HOLD_EQUIVALENCE_REVOKED')
        self.assertEqual([x['kind'] for x in v.events], ['GRANT','REVOKE'])

    def test_revocation_without_pin_abstains(self):
        events=self.revoked(); self.assertEqual(self.view(events,pins={events[0]['basis_ref']:events[0]['digest']}).recall(self.question,scope='project/ario')['disposition'],
                                                       'HOLD_UNPINNED_REVOCATION')

    def test_stale_floor_before_revocation_denied(self):
        events=self.revoked(); self.assertEqual(self.view(events,floor=(1,events[0]['digest'])).recall(self.question,scope='project/ario')['disposition'],
                                       'HOLD_REVIEW_FLOOR_MISSING_OR_STALE')

    def test_illegal_duplicate_revocation_rejected(self):
        events=self.revoked(); new=review_event(events[-1]['digest'],3,kind='REVOKE',binding_id=events[0]['binding_id'],
                    basis_ref='revoke3',reviewer_label='operator',rationale='duplicate',revokes_digest=events[0]['digest'])
        with self.assertRaisesRegex(ReviewHold,'HOLD_INVALID_REVOCATION'):
            self.view(events+[new])

    def test_regrant_after_revoke_with_new_id(self):
        events=self.revoked(); e=review_event(events[-1]['digest'],3,kind='GRANT',binding_id='eq-002',basis_ref='review-003',
                reviewer_label='synthetic-reviewer',rationale='Re-reviewed after challenge',scope='project/ario',
                question=self.question,original_question='Why did we preserve the archive?',
                answer_id=self.answer_id,answer_version=1,journal_sha256=hashlib.sha256(self.path.read_bytes()).hexdigest())
        result=self.view(events+[e]).recall(self.question,scope='project/ario')
        self.assertEqual(result['disposition'],'RECALLED_LAB_REVIEWED_EQUIVALENCE')
        self.assertEqual(result['equivalence']['binding_id'],'eq-002')

    def test_two_conflicting_active_grants_ambiguous(self):
        id2=self.lab.record_answer('Why archive policy differs?', 'Other',scope='project/ario',source_ref='session-002')
        e=self.grant(); e2=review_event(e['digest'],2,kind='GRANT',binding_id='eq-conflict',basis_ref='review-conflict',
                    reviewer_label='synthetic-reviewer',rationale='conflict fixture',scope='project/ario',
                    question=self.question, original_question='Why archive policy differs?',
                    answer_id=id2,answer_version=1,journal_sha256=hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(self.view([e,e2]).recall(self.question,scope='project/ario')['disposition'],'UNKNOWN_AMBIGUOUS')

    def test_duplicate_same_answer_reviews_ambiguous(self):
        e=self.grant(); e2=review_event(e['digest'],2,kind='GRANT',binding_id='eq-2',basis_ref='review2',
               reviewer_label='synthetic-reviewer',rationale='duplicate',scope='project/ario',
               question=self.question,original_question='Why did we preserve the archive?',
               answer_id=self.answer_id,answer_version=1,journal_sha256=hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(self.view([e,e2]).recall(self.question,scope='project/ario')['disposition'],'UNKNOWN_DUPLICATE_REVIEW')

    def test_revision_invalidates_reviewed_alias(self):
        e=self.grant(); self.lab.correct_answer(self.answer_id,'We changed the retention policy.',source_ref='discussion:record-002')
        # A reviewed old binding that was made against an old journal is invalid
        # to instantiate even if its pair remains similar.
        with self.assertRaisesRegex(ReviewHold,'HOLD_GRANT_JOURNAL_MISMATCH'):
            self.view([e])
        self.assertEqual(len(self.lab.history(self.answer_id)),2)

    def test_new_review_after_revision_can_recall_new_answer(self):
        self.lab.correct_answer(self.answer_id,'Now preserve history with redaction.',source_ref='discussion:record-002')
        e=self.grant(version=2)
        r=self.view([e]).recall(self.question,scope='project/ario')
        self.assertEqual(r['version'],2)
        self.assertEqual(len(self.view([e]).history(self.answer_id)),2)

    def test_forbid_duplicate_binding_ids(self):
        e=self.grant(); e2=review_event(e['digest'],2,kind='GRANT',binding_id='eq-001',basis_ref='review2',
                reviewer_label='synthetic-reviewer',rationale='duplicate',scope='project/ario',
                question=self.question,original_question='Why did we preserve the archive?',
                answer_id=self.answer_id,answer_version=1,journal_sha256=hashlib.sha256(self.path.read_bytes()).hexdigest())
        with self.assertRaisesRegex(ReviewHold,'HOLD_DUPLICATE_BINDING'):
            self.view([e,e2])

    def test_tampered_review_hash_fail(self):
        e=self.grant(); e['question']='wrong after hashing'
        with self.assertRaisesRegex(ReviewHold,'HOLD_REVIEW_DIGEST'):
            self.view([e])

    def test_reordered_sequence_fail(self):
        e=self.grant(); e['seq']=42
        with self.assertRaisesRegex(ReviewHold,'HOLD_REVIEW_SEQUENCE'):
            self.view([e])

    def test_wrong_grant_source_answer_fail(self):
        e=self.grant(original='How to cook lunch?')
        with self.assertRaisesRegex(ReviewHold,'HOLD_GRANT_CANONICAL_QUESTION'):
            self.view([e])

    def test_review_replay_omission_detected_by_floor(self):
        events=self.revoked(); floor=(2,events[-1]['digest'])
        old=[events[0]]
        self.assertEqual(self.view(old,floor=floor).recall(self.question,scope='project/ario')['disposition'],
                         'HOLD_REVIEW_FLOOR_MISSING_OR_STALE')

    def test_local_rollback_with_self_chosen_old_floor_is_not_detected(self):
        # Intentional *security limit*: a malicious caller can reuse both old review
        # snapshot AND old floor. This does not justify independent trust.
        events=self.revoked(); only_old=[events[0]]
        r=self.view(only_old).recall(self.question,scope='project/ario')
        self.assertEqual(r['disposition'],'RECALLED_LAB_REVIEWED_EQUIVALENCE')
        self.assertIn('NOT_INDEPENDENTLY_ATTESTED',r['equivalence']['review_authenticity'])

    def test_source_changes_after_view_yields_hold(self):
        e=self.grant(); v=self.view([e]); self.lab.correct_answer(self.answer_id,'Revision',source_ref='other')
        self.assertEqual(v.recall(self.question,scope='project/ario')['disposition'],'HOLD_SOURCE_CHANGED')

    def test_existing_source_untouched_by_read_view(self):
        e=self.grant(); v=self.view([e]); _=v.recall(self.question,scope='project/ario')
        self.assertEqual(self.path.read_bytes(),self.baseline)

    def test_reviewed_pair_not_transitive_and_not_truth(self):
        e=self.grant(); v=self.view([e]); r=v.recall(self.question,scope='project/ario')
        self.assertEqual(r['equivalence']['semantic_scope'],'ONE_EXACT_REVIEWED_PAIR_ONLY')
        self.assertEqual(r['record_state'],'RECORDED')
        self.assertEqual(r['effective_assessment'],'NOT_EVALUATED')

    def test_pair_false_negative_is_permitted(self):
        # Human can correctly understand oppositely phrased sentences, but cheap
        # polarity guard conservatively abstains; it is NOT general NLI.
        c=semantic_contrast('Why did we not delete the archive?', 'Why did we preserve the archive?')
        self.assertEqual(c,'HOLD_POLARITY_CONTRAST')

    def test_unknown_mode_fail_closed(self):
        e=self.grant(); self.assertEqual(self.view([e]).recall(self.question,scope='project/ario',mode='ALWAYS_TRUE')['disposition'],
                                     'HOLD_QUERY_MODE')


if __name__=='__main__':
    unittest.main()