"""Local synthetic adversarial fixtures; no provider/network or security activation."""
import sys
import unittest
from pathlib import Path
from threading import Barrier, Thread

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ethics_dispatch_synthetic_v0_1 import SyntheticSession, termination_decision


class TerminationControlTests(unittest.TestCase):
    def test_structured_stop(self):
        self.assertEqual(termination_decision("STRUCTURED_REQUIRED", structured="STOP").state, "STOPPED_BY_AGENT_OUTPUT")

    def test_structured_continue(self):
        self.assertEqual(termination_decision("STRUCTURED_REQUIRED", structured="CONTINUE").state, "RUNNING")

    def test_conflict_structured_continue_final_stop(self):
        d = termination_decision("STRUCTURED_REQUIRED", structured="CONTINUE", final_direct="STOP")
        self.assertEqual((d.state, d.reason), ("PAUSED_FOR_REVIEW", "STRUCTURED_FINAL_CONFLICT"))

    def test_conflict_structured_stop_final_continue(self):
        d = termination_decision("STRUCTURED_REQUIRED", structured="STOP", final_direct="CONTINUE")
        self.assertEqual((d.state, d.reason), ("PAUSED_FOR_REVIEW", "STRUCTURED_FINAL_CONFLICT"))

    def test_malformed_structured_field_is_not_a_continue(self):
        self.assertEqual(termination_decision("STRUCTURED_REQUIRED", structured="bad", final_direct="CONTINUE").state, "PAUSED_FOR_REVIEW")

    def test_unhashable_direct_intents_fail_closed(self):
        for invalid in ([], {}, ["STOP"], {"intent": "CONTINUE"}):
            with self.subTest(invalid=invalid):
                result = termination_decision("STRUCTURED_REQUIRED", structured="CONTINUE", final_direct=invalid)
                self.assertEqual((result.state, result.reason),
                                 ("PAUSED_FOR_REVIEW", "INVALID_DIRECT_INTENT"))

    def test_quoted_stop_is_not_a_direct_stop(self):
        # A quote is deliberately excluded from final_direct, rather than keyword-matched.
        self.assertEqual(termination_decision("STRUCTURED_REQUIRED", structured="CONTINUE", final_direct=None).state, "RUNNING")

    def test_final_only_direct_stop(self):
        self.assertEqual(termination_decision("FINAL_ONLY", final_direct="STOP").state, "STOPPED_BY_AGENT_OUTPUT")

    def test_final_only_uncertain(self):
        self.assertEqual(termination_decision("FINAL_ONLY", final_direct="AMBIGUOUS").state, "PAUSED_FOR_REVIEW")


class DispatchControlTests(unittest.TestCase):
    def test_unbegun_reserved_result_is_quarantined(self):
        s = SyntheticSession()
        s.reserve("q")
        self.assertEqual(s.finish("q", "premature"), "QUARANTINED")
        self.assertEqual(s.requests["q"], "RESERVED")
        self.assertEqual(s.result_states["q"], "RESULT_QUARANTINED")
        self.assertFalse(any(x[0] == "RECORDED_RESULT" for x in s.events))

    def test_quarantined_reservation_recovers_unknown_dispatch(self):
        s = SyntheticSession()
        ticket = s.reserve("q")
        self.assertEqual(s.finish("q", "premature"), "QUARANTINED")
        self.assertFalse(s.begin(ticket))
        self.assertTrue(s.recover_ambiguous_send("q"))
        self.assertTrue(s.unknown_dispatch)
        self.assertEqual(s.requests["q"], "DISPATCH_UNKNOWN")
        self.assertEqual(s.result_states["q"], "RESULT_QUARANTINED")
        self.assertIsNone(s.reserve("r"))
        self.assertFalse(s.try_resume(explicit_authorization=True))

    def test_quarantined_early_result_never_replayed_after_reconciliation(self):
        s = SyntheticSession()
        s.reserve("q")
        self.assertEqual(s.finish("q", "premature"), "QUARANTINED")
        self.assertTrue(s.recover_ambiguous_send("q"))
        self.assertTrue(s.try_resume(explicit_authorization=True, reconciled=True))
        self.assertEqual(s.finish("q", "old result"), "DUPLICATE_RESULT")
        self.assertEqual(s.requests["q"], "DISPATCH_UNKNOWN")
        self.assertFalse(any(event[0] == "RECORDED_RESULT" for event in s.events))

    def test_quarantined_started_result_recovers_unknown_dispatch(self):
        s = SyntheticSession()
        ticket = s.reserve("q")
        self.assertTrue(s.begin(ticket))
        s.pause()
        self.assertEqual(s.finish("q", "late"), "QUARANTINED")
        self.assertEqual(s.requests["q"], "SEND_DECISION_ONLY")
        self.assertTrue(s.recover_ambiguous_send("q"))
        self.assertTrue(s.unknown_dispatch)
        self.assertEqual(s.requests["q"], "DISPATCH_UNKNOWN")
        self.assertIsNone(s.reserve("r"))

    def test_recorded_result_is_not_misclassified_as_unknown_dispatch(self):
        s = SyntheticSession()
        ticket = s.reserve("q")
        self.assertTrue(s.begin(ticket))
        self.assertEqual(s.finish("q", "good"), "RECORDED_RESULT")
        self.assertFalse(s.recover_ambiguous_send("q"))
        self.assertFalse(s.unknown_dispatch)

    def test_late_result_after_pause_then_resume_is_quarantined(self):
        s = SyntheticSession()
        ticket = s.reserve("q")
        self.assertTrue(s.begin(ticket))
        s.pause()
        self.assertTrue(s.try_resume(explicit_authorization=True))
        self.assertEqual(s.finish("q", "late"), "QUARANTINED")
        self.assertFalse(any(x[0] == "RECORDED_RESULT" for x in s.events))

    def test_duplicate_result_records_exactly_once(self):
        s = SyntheticSession()
        ticket = s.reserve("q")
        self.assertTrue(s.begin(ticket))
        self.assertEqual(s.finish("q", "first"), "RECORDED_RESULT")
        self.assertEqual(s.finish("q", "second"), "DUPLICATE_RESULT")
        self.assertEqual(s.requests["q"], "SEND_DECISION_ONLY")
        self.assertEqual(s.result_states["q"], "RESULT_RECORDED")
        self.assertEqual(len([x for x in s.events if x[0] == "RECORDED_RESULT"]), 1)

    def test_quarantined_result_cannot_be_recorded_on_retry(self):
        s = SyntheticSession()
        ticket = s.reserve("q")
        self.assertTrue(s.begin(ticket))
        s.pause()
        self.assertEqual(s.finish("q", "late"), "QUARANTINED")
        self.assertTrue(s.try_resume(explicit_authorization=True))
        self.assertEqual(s.finish("q", "retry"), "DUPLICATE_RESULT")
        self.assertFalse(any(x[0] == "RECORDED_RESULT" for x in s.events))

    def test_resume_while_running_is_noop(self):
        s = SyntheticSession()
        ticket = s.reserve("q")
        original_epoch = s.epoch
        self.assertFalse(s.try_resume(explicit_authorization=True))
        self.assertEqual(s.epoch, original_epoch)
        self.assertTrue(s.begin(ticket))
        self.assertFalse(any(x[0] == "EXPLICIT_RESUME" for x in s.events))

    def test_pause_wins_before_begin(self):
        s = SyntheticSession()
        t = s.reserve("q")
        self.assertEqual(s.pause(), "PAUSED_FOR_REVIEW")
        self.assertFalse(s.begin(t))

    def test_begin_wins_before_pause_and_reply_is_quarantined(self):
        s = SyntheticSession()
        t = s.reserve("q")
        self.assertTrue(s.begin(t))
        s.pause()
        self.assertEqual(s.finish("q", "synthetic reply"), "QUARANTINED")

    def test_stale_epoch_rejected_after_resume(self):
        s = SyntheticSession()
        t = s.reserve("q")
        s.pause()
        self.assertTrue(s.try_resume(explicit_authorization=True))
        self.assertFalse(s.begin(t))

    def test_no_automatic_resume(self):
        s = SyntheticSession()
        s.pause()
        self.assertFalse(s.try_resume())

    def test_uncertain_dispatch_blocks_new_request(self):
        s = SyntheticSession()
        t = s.reserve("q")
        self.assertTrue(s.recover_ambiguous_send("q"))
        self.assertEqual(s.requests["q"], "DISPATCH_UNKNOWN")
        self.assertFalse(s.begin(t))
        self.assertIsNone(s.reserve("r"))
        self.assertFalse(s.try_resume(explicit_authorization=True))

    def test_reconcile_must_be_attributed_before_resume(self):
        s = SyntheticSession()
        s.reserve("q")
        s.recover_ambiguous_send("q")
        self.assertFalse(s.try_resume(reconciled=True))
        self.assertTrue(s.try_resume(explicit_authorization=True, reconciled=True))
        self.assertIsNotNone(s.reserve("r"))

    def test_threaded_race_is_ordered(self):
        s = SyntheticSession()
        ticket = s.reserve("q")
        gate = Barrier(3)
        outcomes = []
        def start():
            gate.wait()
            outcomes.append(("started", s.begin(ticket)))
        def stop():
            gate.wait()
            outcomes.append(("paused", s.pause()))
        a = Thread(target=start)
        b = Thread(target=stop)
        a.start(); b.start(); gate.wait(); a.join(); b.join()
        self.assertEqual(s.status, "PAUSED_FOR_REVIEW")
        self.assertFalse(s.begin(ticket))
        self.assertEqual(sum(1 for e in s.events if e[0] == "SEND_DECISION_ONLY"), int(dict(outcomes)["started"]))

    def test_zero_actual_network_calls_by_construction(self):
        s = SyntheticSession()
        s.begin(s.reserve("q"))
        s.pause()
        self.assertTrue(all(x[0] != "NETWORK_SEND" for x in s.events))


if __name__ == "__main__":
    unittest.main()
