"""Falsification-oriented tests for an isolated synthetic H3.2 laboratory.

These tests do NOT import, execute, or score the existing Ario M0 engine.
"""

from __future__ import annotations

import copy
import json
import io
import tempfile
from contextlib import redirect_stdout, redirect_stderr
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from h32_scope_lab_v01 import (  # noqa: E402
    CHECKS, LAB_VERSION, ResearchInputError, evaluate_case, main,
)


def base_case():
    """A complete, otherwise supported synthetic two-actor trace."""
    scope = {"facility": "X", "period": "Q1", "population": "PATIENT"}
    domain = {
        "facility": {"X": ["X"], "ALL_FACILITIES": ["X", "Y"]},
        "period": {"Q1": ["Q1"], "YEAR": ["Q1", "Q2", "Q3", "Q4"]},
        "population": {
            "ER": ["ER"], "NON_ER": ["NON_ER"],
            "PATIENT": ["ER", "NON_ER"],
            "ALL_CARE": ["ER", "NON_ER", "OTHER"],
        },
    }
    assertion = {
        "scope": copy.deepcopy(scope), "claim_kind": "capture",
        "strength": "CERTIFIED", "citations": ["G"], "citations_complete": True,
    }
    return {
        "case_id": "H32-E-BROAD", "domain": domain,
        "coverage_policy": "coverage/single-item-v1", "history_complete": True,
        "guarantees": [{
            "id": "G", "scope": copy.deepcopy(scope), "claim_kind": "capture",
            "strength": "CERTIFIED", "verification": "TEST_VERIFIED",
            "available_at": 5, "verified_at": 6, "published_at": 7,
        }],
        "events": [
            {"actor": "A", "at": 10, "display_facets": copy.deepcopy(scope),
             "scope_meta": copy.deepcopy(scope), "display_text": "All patient encounters at X during Q1 were captured.",
             "assertion": None},
            {"actor": "B", "at": 20, "display_facets": copy.deepcopy(scope),
             "scope_meta": copy.deepcopy(scope), "display_text": "All patient encounters at X during Q1 were captured.",
             "assertion": assertion},
        ],
        "obligations": [],
    }


def global_label(case, check="unsupported_scope_assertion"):
    return evaluate_case(case)["checks"][check]["earliest_global"]


class H32ScopeResearchTests(unittest.TestCase):
    def test_baseline_all_five_none_and_no_m0_claim(self):
        result = evaluate_case(base_case())
        self.assertEqual(tuple(result["checks"]), CHECKS)
        self.assertTrue(all(x["earliest_global"] == "NONE"
                            for x in result["checks"].values()))
        self.assertEqual(result["lab_version"], LAB_VERSION)
        self.assertEqual(result["execution_attribution"], "STANDALONE_RESEARCH_ONLY_NOT_M0")
        self.assertEqual(result["ario_m0_h32_runtime_score"], "NOT_EVALUATED")
        self.assertEqual(result["provenance_validation"], "NOT_PERFORMED_TEST_PREMISES_ONLY")

    def test_narrow_guarantee_broad_assertion_detected_at_b_in_both_checks(self):
        case = base_case()
        case["guarantees"][0]["scope"]["population"] = "ER"
        result = evaluate_case(case)
        self.assertEqual(result["checks"]["unsupported_scope_assertion"]["earliest_global"], "B")
        self.assertEqual(result["checks"]["unsupported_firm_certification"]["earliest_global"], "B")
        self.assertEqual(result["events"][1]["assertion_review"]["conditional_coverage"],
                         "NO_UNDER_SUPPLIED_CONTENT")

    def test_narrower_assertion_is_supported_not_inequality_failure(self):
        case = base_case()
        case["events"][1]["assertion"]["scope"]["population"] = "ER"
        self.assertEqual(global_label(case), "NONE")

    def test_strict_superset_guarantee_supports_narrower_assertion(self):
        case = base_case()
        case["guarantees"][0]["scope"]["population"] = "ALL_CARE"
        self.assertEqual(global_label(case), "NONE")

    def test_unverified_broad_is_unknown_not_verified(self):
        case = base_case()
        case["guarantees"][0]["verification"] = "UNVERIFIED"
        result = evaluate_case(case)
        self.assertEqual(global_label(case), "UNKNOWN")
        self.assertEqual(result["events"][1]["assertion_review"]["conditional_coverage"],
                         "YES_UNDER_SUPPLIED_CONTENT")
        self.assertEqual(result["events"][1]["assertion_review"]["citations"][0]["eligibility"],
                         "UNKNOWN")

    def test_known_narrow_scope_stays_unsupported_despite_unknown_provenance(self):
        case = base_case()
        case["guarantees"][0]["scope"]["population"] = "ER"
        case["guarantees"][0]["verification"] = "UNVERIFIED"
        result = evaluate_case(case)
        self.assertEqual(global_label(case), "B")
        self.assertEqual(result["events"][1]["assertion_review"]["citations"][0]["eligibility"],
                         "UNKNOWN")

    def test_invalid_verification_premise_cannot_be_admitted(self):
        case = base_case()
        case["guarantees"][0]["verification"] = "TEST_INVALID"
        self.assertEqual(global_label(case), "B")

    def test_late_availability_vs_late_verification_separate(self):
        for field in ("available_at", "verified_at"):
            with self.subTest(field=field):
                case = base_case()
                case["guarantees"][0][field] = 21
                self.assertEqual(global_label(case), "B")
                self.assertTrue(evaluate_case(case)["events"][1]["assertion_review"]
                                ["citations"][0]["eligibility"].startswith("REJECTED_"))

    def test_late_publication_does_not_backdate_access_but_is_not_required(self):
        case = base_case()
        case["guarantees"][0]["published_at"] = 999
        self.assertEqual(global_label(case), "NONE")

    def test_uncited_independent_broad_guarantee_does_not_rescue_narrow_citation(self):
        case = base_case()
        h = copy.deepcopy(case["guarantees"][0])
        h["id"] = "H"
        case["guarantees"][0]["scope"]["population"] = "ER"
        case["guarantees"].append(h)
        self.assertEqual(global_label(case), "B")

    def test_identical_display_and_assertion_distinct_evidence_changes_result(self):
        broad = base_case()
        narrow = copy.deepcopy(broad)
        narrow["guarantees"][0]["scope"]["population"] = "ER"
        self.assertEqual(broad["events"], narrow["events"])
        self.assertEqual(global_label(broad), "NONE")
        self.assertEqual(global_label(narrow), "B")

    def test_unknown_reference_causes_unknown_not_definite_failure(self):
        case = base_case()
        case["events"][1]["assertion"]["citations"] = ["MISSING"]
        self.assertEqual(global_label(case), "UNKNOWN")

    def test_incomplete_citation_set_can_still_be_supported_by_known_sufficient_item(self):
        case = base_case()
        case["events"][1]["assertion"]["citations_complete"] = False
        self.assertEqual(global_label(case), "NONE")

    def test_incomplete_citation_set_without_support_is_unknown(self):
        case = base_case()
        case["guarantees"][0]["scope"]["population"] = "ER"
        case["events"][1]["assertion"]["citations_complete"] = False
        self.assertEqual(global_label(case), "UNKNOWN")

    def test_two_cited_partitions_support_union_only_under_explicit_union_policy(self):
        case = base_case()
        case["guarantees"][0]["scope"]["population"] = "ER"
        second = copy.deepcopy(case["guarantees"][0])
        second["id"] = "H"
        second["scope"]["population"] = "NON_ER"
        case["guarantees"].append(second)
        case["events"][1]["assertion"]["citations"] = ["G", "H"]
        self.assertEqual(global_label(case), "B")
        case["coverage_policy"] = "coverage/union-v1"
        self.assertEqual(global_label(case), "NONE")

    def test_union_does_not_join_different_periods_or_facilities(self):
        case = base_case()
        case["coverage_policy"] = "coverage/union-v1"
        case["guarantees"][0]["scope"]["population"] = "ER"
        second = copy.deepcopy(case["guarantees"][0])
        second["id"] = "H"
        second["scope"].update({"population": "NON_ER", "facility": "ALL_FACILITIES",
                                "period": "YEAR"})
        case["guarantees"].append(second)
        case["events"][1]["assertion"]["citations"] = ["G", "H"]
        self.assertEqual(global_label(case), "NONE")
        second["scope"]["period"] = "Q1"
        # Still a covering superset; changing only period to Q1 does not affect coverage.
        self.assertEqual(global_label(case), "NONE")
        case["guarantees"][1]["claim_kind"] = "another_kind"
        self.assertEqual(global_label(case), "B")

    def test_unknown_reference_combined_with_known_good_is_still_supported(self):
        case = base_case()
        case["events"][1]["assertion"]["citations"] = ["G", "MISSING"]
        self.assertEqual(global_label(case), "NONE")

    def test_wrong_claim_kind_and_strength_each_preclude_support(self):
        for field, value in (("claim_kind", "not_capture"), ("strength", "TENTATIVE")):
            with self.subTest(field=field):
                case = base_case()
                case["guarantees"][0][field] = value
                self.assertEqual(global_label(case), "B")

    def test_tentative_unsupported_is_scope_finding_not_firm_certification(self):
        case = base_case()
        case["guarantees"][0]["scope"]["population"] = "ER"
        case["events"][1]["assertion"]["strength"] = "TENTATIVE"
        result = evaluate_case(case)
        self.assertEqual(result["checks"]["unsupported_scope_assertion"]["earliest_global"], "B")
        self.assertEqual(result["checks"]["unsupported_firm_certification"]["earliest_global"], "NONE")

    def test_all_five_checks_can_localize_b_without_collapsing_dimensions(self):
        case = base_case()
        case["events"][1]["display_facets"] = {"facility": "X"}
        case["events"][1]["scope_meta"] = None
        case["guarantees"][0]["scope"]["population"] = "ER"
        case["obligations"] = [{"id": "P", "start_at": 20, "end_at": 20,
                                "channel": "typed", "required_facets": {"population": "PATIENT"}}]
        result = evaluate_case(case)
        self.assertTrue(all(c["earliest_global"] == "B" for c in result["checks"].values()))

    def test_display_value_change_is_not_facet_omission(self):
        case = base_case()
        case["events"][1]["display_facets"]["population"] = "ER"
        self.assertEqual(global_label(case, "display_qualifier_omission"), "NONE")

    def test_typed_scope_changed_value_not_lost_key(self):
        case = base_case()
        case["events"][1]["scope_meta"]["population"] = "ER"
        self.assertEqual(global_label(case, "typed_metadata_loss"), "NONE")

    def test_explicit_preservation_breach_by_value_change_and_expiry(self):
        case = base_case()
        case["obligations"] = [{"id": "P", "start_at": 20, "end_at": 20,
                                "channel": "display", "required_facets": {"population": "PATIENT"}}]
        case["events"][1]["display_facets"]["population"] = "ER"
        self.assertEqual(global_label(case, "preservation_contract_breach"), "B")
        case["obligations"][0]["start_at"] = 10
        case["obligations"][0]["end_at"] = 19
        raise_case = copy.deepcopy(case)
        # An inactive obligation must not cause a preservation breach.
        self.assertEqual(global_label(raise_case, "preservation_contract_breach"), "NONE")

    def test_incomplete_prefix_preserves_observed_b_but_global_unknown(self):
        case = base_case()
        case["history_complete"] = False
        case["guarantees"][0]["scope"]["population"] = "ER"
        review = evaluate_case(case)["checks"]["unsupported_scope_assertion"]
        self.assertEqual(review, {"earliest_observed": "B", "earliest_global": "UNKNOWN"})

    def test_known_early_unknown_blocks_global_earliest_even_with_complete_history(self):
        case = base_case()
        case["events"][0]["assertion"] = copy.deepcopy(case["events"][1]["assertion"])
        case["events"][0]["assertion"]["citations"] = ["MISSING"]
        case["guarantees"][0]["scope"]["population"] = "ER"
        review = evaluate_case(case)["checks"]["unsupported_scope_assertion"]
        self.assertEqual(review, {"earliest_observed": "B", "earliest_global": "UNKNOWN"})

    def test_case_id_rename_and_json_key_reordering_do_not_change_labels(self):
        case = base_case()
        labels = evaluate_case(case)["checks"]
        case["case_id"] = "H32-RENAMED"
        case = json.loads(json.dumps(case, sort_keys=True))
        self.assertEqual(evaluate_case(case)["checks"], labels)

    def test_unexpected_field_rejected_closed(self):
        case = base_case()
        case["unexpected"] = "do-not-trust"
        with self.assertRaises(ResearchInputError):
            evaluate_case(case)

    def test_duplicate_guarantee_reference_rejected(self):
        case = base_case()
        case["guarantees"].append(copy.deepcopy(case["guarantees"][0]))
        with self.assertRaises(ResearchInputError):
            evaluate_case(case)

    def test_undeclared_scope_term_rejected(self):
        case = base_case()
        case["guarantees"][0]["scope"]["population"] = "BOGUS"
        with self.assertRaises(ResearchInputError):
            evaluate_case(case)

    def test_unknown_policy_rejected(self):
        case = base_case()
        case["coverage_policy"] = "heuristic/always-pass"
        with self.assertRaises(ResearchInputError):
            evaluate_case(case)

    def test_citation_duplicate_rejected(self):
        case = base_case()
        case["events"][1]["assertion"]["citations"] = ["G", "G"]
        with self.assertRaises(ResearchInputError):
            evaluate_case(case)

    def test_boolean_timestamp_rejected(self):
        case = base_case()
        case["guarantees"][0]["verified_at"] = True
        with self.assertRaises(ResearchInputError):
            evaluate_case(case)

    def test_out_of_order_events_rejected(self):
        case = base_case()
        case["events"][1]["at"] = 10
        with self.assertRaises(ResearchInputError):
            evaluate_case(case)

    def test_cli_reads_synthetic_fixture_and_emits_machine_readable_status(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "synthetic.json"
            path.write_text(json.dumps(base_case()), encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = main([str(path)])
            self.assertEqual(code, 0)
            parsed = json.loads(buffer.getvalue())
            self.assertEqual(parsed["checks"]["unsupported_scope_assertion"]["earliest_global"], "NONE")
            self.assertEqual(parsed["ario_m0_h32_runtime_score"], "NOT_EVALUATED")

    def test_cli_rejects_invalid_fixture_without_fake_pass(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "synthetic.json"
            path.write_text("{invalid}", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main([str(path)])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(stderr.getvalue())["status"], "REJECTED_INPUT")

    def test_missing_observation_is_not_fabricated(self):
        case = base_case()
        case["events"][1]["assertion"]["citations"] = []
        self.assertEqual(global_label(case), "B")  # explicit complete, no cited support
        case["events"][1]["assertion"]["citations_complete"] = False
        self.assertEqual(global_label(case), "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
