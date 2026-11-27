"""Public synthetic development controls, NOT identity/authentication tests."""
import copy
import json
from pathlib import Path
import unittest
from reference import project

ROOT = Path(__file__).resolve().parent


class CorpusTests(unittest.TestCase):
    def test_nine_public_scenarios(self):
        cases = json.loads((ROOT / "synthetic_cases.json").read_text(encoding="utf-8"))
        self.assertEqual(len(cases), 9)
        self.assertEqual(len({c["case_id"] for c in cases}), 9)
        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                out = project(case["events"], subject_ref="SUBJECT-A", scope="PERSONALIZATION")
                self.assertEqual(out["status"], case["expected_status"])
                self.assertEqual(out["future_use"], case["expected_future_use"])
                self.assertEqual(out["identity_authentication"], "NOT_PERFORMED")
                self.assertEqual(out["memory_mutation"], "NONE")
                self.assertEqual(out["retention_decision"], "NOT_PERFORMED")

    def test_no_input_mutation_and_history_preserved(self):
        case = json.loads((ROOT / "synthetic_cases.json").read_text())[0]
        before = copy.deepcopy(case["events"])
        out = project(case["events"], subject_ref="SUBJECT-A", scope="PERSONALIZATION")
        self.assertEqual(case["events"], before)
        self.assertEqual(out["historical_statement_refs"], ["STMT-T1"])
        self.assertIn("INTERP-T1", out["system_interpretation_refs"])

    def test_late_model_summary_cannot_reinstate_superseded_preference(self):
        cases = json.loads((ROOT / "synthetic_cases.json").read_text())
        events = copy.deepcopy(cases[0]["events"])
        events.append(dict(events[1], event_id="I2", ref="STALE-NEW-SUMMARY"))
        out = project(events, subject_ref="SUBJECT-A", scope="PERSONALIZATION")
        self.assertEqual(out["current_interpretation_ref"], "CORR-T2")
        self.assertEqual(out["future_use"], "CURRENT_REF_ONLY")

    def test_unknown_authority_cannot_change_current(self):
        cases = json.loads((ROOT / "synthetic_cases.json").read_text())
        events = copy.deepcopy(cases[0]["events"])
        events[2]["authority"] = "UNKNOWN"
        out = project(events, subject_ref="SUBJECT-A", scope="PERSONALIZATION")
        self.assertEqual(out["status"], "UNKNOWN")
        self.assertEqual(out["current_interpretation_ref"], "INTERP-T1")

    def test_duplicate_event_id_does_not_override(self):
        cases = json.loads((ROOT / "synthetic_cases.json").read_text())
        events = copy.deepcopy(cases[0]["events"])
        events.append(dict(events[-1], ref="FAKE", target_ref="INTERP-T1"))
        out = project(events, subject_ref="SUBJECT-A", scope="PERSONALIZATION")
        self.assertIn("DUPLICATE_EVENT_ID", out["unresolved"])
        self.assertEqual(out["future_use"], "WITHHOLD")

    def test_historical_statement_from_other_actor_is_not_attributed_to_subject(self):
        cases = json.loads((ROOT / "synthetic_cases.json").read_text())
        events = copy.deepcopy(cases[0]["events"])
        events[0]["actor_ref"] = "OTHER-PERSON"
        observed = project(events, subject_ref="SUBJECT-A", scope="PERSONALIZATION")
        self.assertEqual(observed["historical_statement_refs"], [])
        self.assertIn("HISTORICAL_ATTRIBUTION_MISMATCH", observed["unresolved"])
        self.assertEqual(observed["future_use"], "WITHHOLD")

    def test_old_permission_cannot_transfer_to_corrected_interpretation(self):
        cases = json.loads((ROOT / "synthetic_cases.json").read_text())
        events = copy.deepcopy(cases[0]["events"])
        # Grant the old interpretation before the person corrects it.
        events[2], events[3] = events[3], events[2]
        events[2]["target_ref"] = "INTERP-T1"
        observed = project(events, subject_ref="SUBJECT-A", scope="PERSONALIZATION")
        self.assertEqual(observed["current_interpretation_ref"], "CORR-T2")
        self.assertEqual(observed["permission"], "UNKNOWN")
        self.assertEqual(observed["future_use"], "WITHHOLD")

    def test_old_permission_cannot_transfer_to_later_model_summary(self):
        cases = json.loads((ROOT / "synthetic_cases.json").read_text())
        events = copy.deepcopy(cases[0]["events"][:2])
        permission = copy.deepcopy(cases[0]["events"][3])
        permission["target_ref"] = "INTERP-T1"
        events.append(permission)
        late = copy.deepcopy(events[1])
        late["event_id"], late["ref"] = "I-LATE", "INTERP-LATE"
        events.append(late)
        observed = project(events, subject_ref="SUBJECT-A", scope="PERSONALIZATION")
        self.assertEqual(observed["current_interpretation_ref"], "INTERP-LATE")
        self.assertEqual(observed["permission"], "UNKNOWN")
        self.assertEqual(observed["future_use"], "WITHHOLD")

    def test_withdrawal_dominates_conflicting_untrusted_summary(self):
        cases = json.loads((ROOT / "synthetic_cases.json").read_text())
        events = copy.deepcopy(cases[3]["events"])
        events.append(dict(events[1], event_id="I-LATE", ref="FALSE-SUMMARY"))
        out = project(events, subject_ref="SUBJECT-A", scope="PERSONALIZATION")
        self.assertEqual(out["permission"], "WITHDRAWN")
        self.assertEqual(out["future_use"], "DENY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
