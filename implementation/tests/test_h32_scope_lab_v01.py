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
        """Check the research contract: baseline all five none and no m0 claim."""
        result = evaluate_case(base_case())
        self.assertEqual(tuple(result["checks"]), CHECKS)
        self.assertTrue(all(x["earliest_global"] == "NONE"
                            for x in result["checks"].values()))
        self.assertEqual(result["lab_version"], LAB_VERSION)
        self.assertEqual(result["execution_attribution"], "STANDALONE_RESEARCH_ONLY_NOT_M0")
        self.assertEqual(result["ario_m0_h32_runtime_score"], "NOT_EVALUATED")
        self.assertEqual(result["provenance_validation"], "NOT_PERFORMED_TEST_PREMISES_ONLY")

    def test_narrow_guarantee_broad_assertion_detected_at_b_in_both_checks(self):
        """Check the research contract: narrow guarantee broad assertion detected at b in both checks."""
        case = base_case()
        case["guarantees"][0]["scope"]["population"] = "ER"
        result = evaluate_case(case)
        self.assertEqual(result["checks"]["unsupported_scope_assertion"]["earliest_global"], "B")
        self.assertEqual(result["checks"]["unsupported_firm_certification"]["earliest_global"], "B")
        self.assertEqual(result["events"][1]["assertion_review"]["conditional_coverage"],
                         "NO_UNDER_SUPPLIED_CONTENT")

    def test_narrower_assertion_is_supported_not_inequality_failure(self):
        """Check the research contract: narrower assertion is supported not inequality failure."""
        case = base_case()
        case["events"][1]["assertion"]["scope"]["population"] = "ER"
        self.assertEqual(global_label(case), "NONE")

    def test_strict_superset_guarantee_supports_narrower_assertion(self):
        """Check the research contract: strict superset guarantee supports narrower assertion."""
        case = base_case()
        case["guarantees"][0]["scope"]["population"] = "ALL_CARE"
        self.assertEqual(global_label(case), "NONE")

    def test_unverified_broad_is_unknown_not_verified(self):
        """Check the research contract: unverified broad is unknown not verified."""
        case = base_case()
        case["guarantees"][0]["verification"] = "UNVERIFIED"
        result = evaluate_case(case)
        self.assertEqual(global_label(case), "UNKNOWN")
        self.assertEqual(result["events"][1]["assertion_review"]["conditional_coverage"],
                         "YES_UNDER_SUPPLIED_CONTENT")
        self.assertEqual(result["events"][1]["assertion_review"]["citations"][0]["eligibility"],
                         "UNKNOWN")

    def test_known_narrow_scope_stays_unsupported_despite_unknown_provenance(self):
        """Check the research contract: known narrow scope stays unsupported despite unknown provenance."""
        case = base_case()
        case["guarantees"][0]["scope"]["population"] = "ER"
        case["guarantees"][0]["verification"] = "UNVERIFIED"
        result = evaluate_case(case)
        self.assertEqual(global_label(case), "B")
        self.assertEqual(result["events"][1]["assertion_review"]["citations"][0]["eligibility"],
                         "UNKNOWN")

    def test_invalid_verification_premise_cannot_be_admitted(self):
        """Check the research contract: invalid verification premise cannot be admitted."""
        case = base_case()
        case["guarantees"][0]["verification"] = "TEST_INVALID"
        self.assertEqual(global_label(case), "B")

    def test_late_availability_vs_late_verification_separate(self):
        """Check the research contract: late availability vs late verification separate."""
        for field in ("available_at", "verified_at"):
            with self.subTest(field=field):
                case = base_case()
                case["guarantees"][0][field] = 21
                self.assertEqual(global_label(case), "B")
                self.assertTrue(evaluate_case(case)["events"][1]["assertion_review"]
                                ["citations"][0]["eligibility"].startswith("REJECTED_"))

    def test_tied_timestamps_are_eligible_under_synthetic_policy(self):
        """Check the research contract: tied timestamps are eligible under synthetic policy."""
        for field in ("available_at", "verified_at"):
            for timestamp, expected in ((19, "NONE"), (20, "NONE"), (21, "B")):
                with self.subTest(field=field, timestamp=timestamp):
                    case = base_case()
                    case["guarantees"][0][field] = timestamp
                    self.assertEqual(global_label(case), expected)

    def test_late_publication_does_not_backdate_access_but_is_not_required(self):
        """Check the research contract: late publication does not backdate access but is not required."""
        case = base_case()
        case["guarantees"][0]["published_at"] = 999
        self.assertEqual(global_label(case), "NONE")

    def test_uncited_independent_broad_guarantee_does_not_rescue_narrow_citation(self):
        """Check the research contract: uncited independent broad guarantee does not rescue narrow citation."""
        case = base_case()
        h = copy.deepcopy(case["guarantees"][0])
        h["id"] = "H"
        case["guarantees"][0]["scope"]["population"] = "ER"
        case["guarantees"].append(h)
        self.assertEqual(global_label(case), "B")

    def test_identical_display_and_assertion_distinct_evidence_changes_result(self):
        """Check the research contract: identical display and assertion distinct evidence changes result."""
        broad = base_case()
        narrow = copy.deepcopy(broad)
        narrow["guarantees"][0]["scope"]["population"] = "ER"
        self.assertEqual(broad["events"], narrow["events"])
        self.assertEqual(global_label(broad), "NONE")
        self.assertEqual(global_label(narrow), "B")

    def test_unknown_reference_causes_unknown_not_definite_failure(self):
        """Check the research contract: unknown reference causes unknown not definite failure."""
        case = base_case()
        case["events"][1]["assertion"]["citations"] = ["MISSING"]
        self.assertEqual(global_label(case), "UNKNOWN")

    def test_incomplete_citation_set_can_still_be_supported_by_known_sufficient_item(self):
        """Check the research contract: incomplete citation set can still be supported by known sufficient item."""
        case = base_case()
        case["events"][1]["assertion"]["citations_complete"] = False
        self.assertEqual(global_label(case), "NONE")

    def test_incomplete_citation_set_without_support_is_unknown(self):
        """Check the research contract: incomplete citation set without support is unknown."""
        case = base_case()
        case["guarantees"][0]["scope"]["population"] = "ER"
        case["events"][1]["assertion"]["citations_complete"] = False
        self.assertEqual(global_label(case), "UNKNOWN")

    def test_two_cited_partitions_support_union_only_under_explicit_union_policy(self):
        """Check the research contract: two cited partitions support union only under explicit union policy."""
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

    def test_union_known_superset_and_wrong_kind_cannot_be_mixed(self):
        """Check the research contract: union known superset and wrong kind cannot be mixed."""
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

    def test_union_does_not_cross_product_disjoint_evidence_cells(self):
        """Check the research contract: union does not cross product disjoint evidence cells."""
        case = base_case()
        case["coverage_policy"] = "coverage/union-v1"
        case["domain"]["facility"]["XY"] = ["X", "Y"]
        case["domain"]["facility"]["Y"] = ["Y"]
        case["domain"]["period"]["Q2"] = ["Q2"]
        case["domain"]["period"]["Q1_Q2"] = ["Q1", "Q2"]
        case["events"][1]["assertion"]["scope"].update({
            "facility": "XY", "period": "Q1_Q2"})
        second = copy.deepcopy(case["guarantees"][0])
        second["id"] = "H"
        second["scope"].update({"facility": "Y", "period": "Q2"})
        case["guarantees"].append(second)
        case["events"][1]["assertion"]["citations"] = ["G", "H"]
        # Projection-wise unions cover all dimensions, but actual cells (Y,Q1)
        # are absent from both cited guarantees; cellwise coverage must fail.
        self.assertEqual(global_label(case), "B")

    def test_unknown_reference_combined_with_known_good_is_still_supported(self):
        """Check the research contract: unknown reference combined with known good is still supported."""
        case = base_case()
        case["events"][1]["assertion"]["citations"] = ["G", "MISSING"]
        self.assertEqual(global_label(case), "NONE")

    def test_wrong_claim_kind_and_strength_each_preclude_support(self):
        """Check the research contract: wrong claim kind and strength each preclude support."""
        for field, value in (("claim_kind", "not_capture"), ("strength", "TENTATIVE")):
            with self.subTest(field=field):
                case = base_case()
                case["guarantees"][0][field] = value
                self.assertEqual(global_label(case), "B")

    def test_tentative_unsupported_is_scope_finding_not_firm_certification(self):
        """Check the research contract: tentative unsupported is scope finding not firm certification."""
        case = base_case()
        case["guarantees"][0]["scope"]["population"] = "ER"
        case["events"][1]["assertion"]["strength"] = "TENTATIVE"
        result = evaluate_case(case)
        self.assertEqual(result["checks"]["unsupported_scope_assertion"]["earliest_global"], "B")
        self.assertEqual(result["checks"]["unsupported_firm_certification"]["earliest_global"], "NONE")

    def test_all_five_checks_can_localize_b_without_collapsing_dimensions(self):
        """Check the research contract: all five checks can localize b without collapsing dimensions."""
        case = base_case()
        case["events"][1]["display_facets"] = {"facility": "X"}
        case["events"][1]["scope_meta"] = None
        case["guarantees"][0]["scope"]["population"] = "ER"
        case["obligations"] = [{"id": "P", "start_at": 20, "end_at": 20,
                                "channel": "typed", "required_facets": {"population": "PATIENT"}}]
        result = evaluate_case(case)
        self.assertTrue(all(c["earliest_global"] == "B" for c in result["checks"].values()))

    def test_display_value_change_is_not_facet_omission(self):
        """Check the research contract: display value change is not facet omission."""
        case = base_case()
        case["events"][1]["display_facets"]["population"] = "ER"
        self.assertEqual(global_label(case, "display_qualifier_omission"), "NONE")

    def test_typed_scope_changed_value_not_lost_key(self):
        """Check the research contract: typed scope changed value not lost key."""
        case = base_case()
        case["events"][1]["scope_meta"]["population"] = "ER"
        self.assertEqual(global_label(case, "typed_metadata_loss"), "NONE")

    def test_explicit_preservation_breach_by_value_change_and_expiry(self):
        """Check the research contract: explicit preservation breach by value change and expiry."""
        case = base_case()
        case["obligations"] = [{"id": "P", "start_at": 20, "end_at": 20,
                                "channel": "display", "required_facets": {"population": "PATIENT"}}]
        case["events"][1]["display_facets"]["population"] = "ER"
        self.assertEqual(global_label(case, "preservation_contract_breach"), "B")
        case["obligations"][0]["start_at"] = 10
        case["obligations"][0]["end_at"] = 19
        # The only changed facet is at B (tick 20), outside the active interval.
        self.assertEqual(global_label(case, "preservation_contract_breach"), "NONE")

    def test_obligation_window_both_boundaries_inclusive(self):
        """Check the research contract: obligation window both boundaries inclusive."""
        case = base_case()
        case["obligations"] = [{"id": "P", "start_at": 10, "end_at": 20,
                                "channel": "display", "required_facets": {"population": "PATIENT"}}]
        case["events"][0]["display_facets"]["population"] = "ER"
        self.assertEqual(global_label(case, "preservation_contract_breach"), "A")
        case["events"][0]["display_facets"]["population"] = "PATIENT"
        case["events"][1]["display_facets"]["population"] = "ER"
        self.assertEqual(global_label(case, "preservation_contract_breach"), "B")

    def test_incomplete_prefix_preserves_observed_b_but_global_unknown(self):
        """Check the research contract: incomplete prefix preserves observed b but global unknown."""
        case = base_case()
        case["history_complete"] = False
        case["guarantees"][0]["scope"]["population"] = "ER"
        review = evaluate_case(case)["checks"]["unsupported_scope_assertion"]
        self.assertEqual(review, {"earliest_observed": "B", "earliest_global": "UNKNOWN",
                                  "earliest_observed_event_index": 1,
                                  "earliest_global_event_index": None})

    def test_known_early_unknown_blocks_global_earliest_even_with_complete_history(self):
        """Check the research contract: known early unknown blocks global earliest even with complete history."""
        case = base_case()
        case["events"][0]["assertion"] = copy.deepcopy(case["events"][1]["assertion"])
        case["events"][0]["assertion"]["citations"] = ["MISSING"]
        case["guarantees"][0]["scope"]["population"] = "ER"
        review = evaluate_case(case)["checks"]["unsupported_scope_assertion"]
        self.assertEqual(review, {"earliest_observed": "B", "earliest_global": "UNKNOWN",
                                  "earliest_observed_event_index": 1,
                                  "earliest_global_event_index": None})

    def test_case_id_rename_and_json_key_reordering_do_not_change_labels(self):
        """Check the research contract: case id rename and json key reordering do not change labels."""
        case = base_case()
        labels = evaluate_case(case)["checks"]
        case["case_id"] = "H32-RENAMED"
        case = json.loads(json.dumps(case, sort_keys=True))
        self.assertEqual(evaluate_case(case)["checks"], labels)

    def test_unexpected_field_rejected_closed(self):
        """Check the research contract: unexpected field rejected closed."""
        case = base_case()
        case["unexpected"] = "do-not-trust"
        with self.assertRaises(ResearchInputError):
            evaluate_case(case)

    def test_reserved_actor_names_cannot_hide_errors(self):
        """Check the research contract: reserved actor names cannot hide errors."""
        for actor in ("NONE", "UNKNOWN"):
            with self.subTest(actor=actor):
                case = base_case()
                case["events"][1]["actor"] = actor
                case["guarantees"][0]["scope"]["population"] = "ER"
                with self.assertRaises(ResearchInputError):
                    evaluate_case(case)

    def test_repeated_actors_are_disambiguated_by_event_index(self):
        """Check the research contract: repeated actors are disambiguated by event index."""
        case = base_case()
        case["events"][1]["actor"] = "A"
        case["guarantees"][0]["scope"]["population"] = "ER"
        result = evaluate_case(case)["checks"]["unsupported_scope_assertion"]
        self.assertEqual(result["earliest_global"], "A")
        self.assertEqual(result["earliest_global_event_index"], 1)
        self.assertEqual(result["earliest_observed_event_index"], 1)

    def test_unhashable_citations_reject_instead_of_crashing(self):
        """Check the research contract: unhashable citations reject instead of crashing."""
        for ref in ({}, [], 12, None):
            with self.subTest(ref=ref):
                case = base_case()
                case["events"][1]["assertion"]["citations"] = [ref]
                with self.assertRaises(ResearchInputError):
                    evaluate_case(case)

    def test_uncited_oversize_guarantee_scope_is_rejected_eagerly(self):
        """Check the research contract: uncited oversize guarantee scope is rejected eagerly."""
        case = base_case()
        for dimension in ("facility", "period", "population"):
            case["domain"][dimension]["BIG"] = [f"{dimension}_{i}" for i in range(16)]
        extra = copy.deepcopy(case["guarantees"][0])
        extra["id"] = "H"
        extra["scope"] = {"facility": "BIG", "period": "BIG", "population": "BIG"}
        case["guarantees"].append(extra)  # Uncited H expands to 4096 cells.
        with self.assertRaises(ResearchInputError):
            evaluate_case(case)

    def test_duplicate_guarantee_reference_rejected(self):
        """Check the research contract: duplicate guarantee reference rejected."""
        case = base_case()
        case["guarantees"].append(copy.deepcopy(case["guarantees"][0]))
        with self.assertRaises(ResearchInputError):
            evaluate_case(case)

    def test_undeclared_scope_term_rejected(self):
        """Check the research contract: undeclared scope term rejected."""
        case = base_case()
        case["guarantees"][0]["scope"]["population"] = "BOGUS"
        with self.assertRaises(ResearchInputError):
            evaluate_case(case)

    def test_unknown_policy_rejected(self):
        """Check the research contract: unknown policy rejected."""
        case = base_case()
        case["coverage_policy"] = "heuristic/always-pass"
        with self.assertRaises(ResearchInputError):
            evaluate_case(case)

    def test_citation_duplicate_rejected(self):
        """Check the research contract: citation duplicate rejected."""
        case = base_case()
        case["events"][1]["assertion"]["citations"] = ["G", "G"]
        with self.assertRaises(ResearchInputError):
            evaluate_case(case)

    def test_boolean_timestamp_rejected(self):
        """Check the research contract: boolean timestamp rejected."""
        case = base_case()
        case["guarantees"][0]["verified_at"] = True
        with self.assertRaises(ResearchInputError):
            evaluate_case(case)

    def test_out_of_order_events_rejected(self):
        """Check the research contract: out of order events rejected."""
        case = base_case()
        case["events"][1]["at"] = 10
        with self.assertRaises(ResearchInputError):
            evaluate_case(case)

    def _assert_cli_rejected(self, raw: bytes, error_type: str | tuple[str, ...] | None = None) -> None:
        """Verify malformed fixtures fail closed with the expected error class."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "synthetic.json"
            path.write_bytes(raw)
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main([str(path)])
            self.assertEqual(code, 2)
            self.assertEqual(out.getvalue(), "")
            diagnostic = json.loads(err.getvalue())
            self.assertEqual(diagnostic["status"], "REJECTED_INPUT")
            if error_type is not None:
                self.assertIn(diagnostic["error_type"],
                                  (error_type,) if isinstance(error_type, str) else error_type)

    def test_cli_rejects_duplicate_json_keys_both_orders(self):
        """Check the research contract: cli rejects duplicate json keys both orders."""
        raw = json.dumps(base_case())
        marker = '"citations_complete": true'
        self.assertIn(marker, raw)
        for replacement in ('"citations_complete": false, ' + marker,
                            marker + ', "citations_complete": false'):
            with self.subTest(replacement=replacement):
                self._assert_cli_rejected(raw.replace(marker, replacement).encode("utf-8"))

    def test_cli_rejects_unhashable_citation_values(self):
        """Check the research contract: cli rejects unhashable citation values."""
        for bad in ({}, [], 13, None):
            with self.subTest(bad=bad):
                case = base_case()
                case["events"][1]["assertion"]["citations"] = [bad]
                self._assert_cli_rejected(json.dumps(case).encode("utf-8"))

    def test_cli_rejects_deeply_nested_json_and_huge_integer(self):
        """Distinguish the recursion guard from Python's huge-integer guard."""
        self._assert_cli_rejected(("[" * 1300 + "0" + "]" * 1300).encode("utf-8"),
                                  error_type=("RecursionError", "ResearchInputError"))
        self._assert_cli_rejected(('{"case_id": ' + "7" * 5000 + '}').encode("utf-8"),
                                  error_type="ValueError")

    def test_cli_validates_exact_file_size_boundary(self):
        """Check the research contract: cli validates exact file size boundary."""
        payload = json.dumps(base_case()).encode("utf-8")
        maximum = 262144
        self.assertLess(len(payload), maximum)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "limit.json"
            path.write_bytes(payload + b" " * (maximum - len(payload)))
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main([str(path)])
            self.assertEqual(code, 0, err.getvalue())
            self.assertEqual(json.loads(out.getvalue())["ario_m0_h32_runtime_score"], "NOT_EVALUATED")
            path.write_bytes(payload + b" " * (maximum + 1 - len(payload)))
            with redirect_stdout(out := io.StringIO()), redirect_stderr(err := io.StringIO()):
                code = main([str(path)])
            self.assertEqual(code, 2)
            self.assertEqual(out.getvalue(), "")
            self.assertEqual(json.loads(err.getvalue())["status"], "REJECTED_INPUT")

    def test_cli_invalid_utf8_and_missing_file_rejected(self):
        """Check the research contract: cli invalid utf8 and missing file rejected."""
        self._assert_cli_rejected(b"\xff")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "absent.json"
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main([str(path)])
            self.assertEqual(code, 2)
            self.assertEqual(out.getvalue(), "")
            self.assertEqual(json.loads(err.getvalue())["status"], "REJECTED_INPUT")

    def test_cli_rejects_symlink(self):
        """Check the research contract: cli rejects symlink."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "target.json"
            link = root / "link.json"
            target.write_text(json.dumps(base_case()), encoding="utf-8")
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unsupported: {exc}")
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main([str(link)])
            self.assertEqual(code, 2)
            self.assertEqual(out.getvalue(), "")
            self.assertEqual(json.loads(err.getvalue())["status"], "REJECTED_INPUT")

    def test_cli_accepts_crlf_json(self):
        """Check the research contract: cli accepts crlf json."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "synthetic.json"
            encoded = json.dumps(base_case(), indent=2).replace("\n", "\r\n")
            path.write_bytes(encoded.encode("utf-8"))
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main([str(path)])
            self.assertEqual(code, 0, err.getvalue())
            self.assertEqual(json.loads(out.getvalue())["checks"]["unsupported_scope_assertion"]
                             ["earliest_global"], "NONE")

    def test_cli_reads_synthetic_fixture_and_emits_machine_readable_status(self):
        """Check the research contract: cli reads synthetic fixture and emits machine readable status."""
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
        """Check the research contract: cli rejects invalid fixture without fake pass."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "synthetic.json"
            path.write_text("{invalid}", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main([str(path)])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(stderr.getvalue())["status"], "REJECTED_INPUT")

    def test_missing_observation_is_not_fabricated(self):
        """Check the research contract: missing observation is not fabricated."""
        case = base_case()
        case["events"][1]["assertion"]["citations"] = []
        self.assertEqual(global_label(case), "B")  # explicit complete, no cited support
        case["events"][1]["assertion"]["citations_complete"] = False
        self.assertEqual(global_label(case), "UNKNOWN")


    def test_empty_metadata_does_not_invent_a_lost_key(self):
        """Only keys previously supplied, not container presence, count as loss."""
        for older, newer, expected in (
            (None, None, "NONE"), (None, {}, "NONE"),
            ({}, {}, "NONE"), ({}, None, "NONE"),
            ({"population": "PATIENT"}, None, "B"),
            ({"population": "PATIENT"}, {}, "B"),
            ({"population": "PATIENT"}, {"population": "ER"}, "NONE"),
            ({"population": "PATIENT", "period": "Q1"},
             {"population": "PATIENT"}, "B"),
        ):
            with self.subTest(older=older, newer=newer):
                case = base_case()
                case["events"][0]["scope_meta"] = older
                case["events"][1]["scope_meta"] = newer
                finding = evaluate_case(case)["checks"]["typed_metadata_loss"]
                self.assertEqual(finding["earliest_global"], expected)
                self.assertEqual(finding["earliest_global_event_index"],
                                 1 if expected == "B" else None)

    def test_clean_but_incomplete_history_never_becomes_global_none(self):
        """An unobserved prefix blocks all five global no-fault conclusions."""
        case = base_case()
        case["history_complete"] = False
        result = evaluate_case(case)
        for check in CHECKS:
            with self.subTest(check=check):
                self.assertEqual(result["checks"][check]["earliest_observed"], "NONE")
                self.assertEqual(result["checks"][check]["earliest_global"], "UNKNOWN")
                self.assertIsNone(result["checks"][check]["earliest_global_event_index"])

    def test_unknown_firm_certification_cannot_silently_pass(self):
        """Unknown premise stays UNKNOWN for both modeled cited-justification checks."""
        case = base_case()
        case["guarantees"][0]["verification"] = "UNVERIFIED"
        result = evaluate_case(case)
        for check in ("unsupported_scope_assertion", "unsupported_firm_certification"):
            with self.subTest(check=check):
                self.assertEqual(result["checks"][check]["earliest_global"], "UNKNOWN")
                self.assertEqual(result["events"][1]["local_checks"][check], "UNKNOWN")

    def test_eligibility_rejection_reason_is_not_faked_by_strength_filter(self):
        """Diagnostic eligibility must track kind, strength, time, and invalid premise."""
        for field, value, reason in (
            ("claim_kind", "other", "REJECTED_KIND"),
            ("strength", "TENTATIVE", "REJECTED_STRENGTH"),
            ("verification", "TEST_INVALID", "REJECTED_INVALID_TEST_PREMISE"),
            ("available_at", 21, "REJECTED_NOT_AVAILABLE_TO_ACTOR"),
            ("verified_at", 21, "REJECTED_NOT_VERIFIED_AT_ACTOR_TIME"),
            ("verification", "UNVERIFIED", "UNKNOWN"),
        ):
            with self.subTest(field=field, value=value):
                case = base_case()
                case["guarantees"][0][field] = value
                review = evaluate_case(case)["events"][1]["assertion_review"]
                self.assertEqual(review["citations"][0]["eligibility"], reason)

    def test_claim_time_changes_eligibility_in_both_directions(self):
        """Kill the constant-at-20 eligibility mutant despite unchanged evidence."""
        for field in ("available_at", "verified_at"):
            case = base_case()
            case["guarantees"][0][field] = 21
            case["events"][1]["at"] = 20
            with self.subTest(field=field, event_at=20):
                self.assertEqual(global_label(case), "B")
            case["events"][1]["at"] = 30
            with self.subTest(field=field, event_at=30):
                self.assertEqual(global_label(case), "NONE")
            case["events"][1]["at"] = 21
            with self.subTest(field=field, event_at=21):
                self.assertEqual(global_label(case), "NONE")

    def test_declared_domain_membership_not_hardcoded_alias_semantics(self):
        """Changing only atom expansions must change containment decisions."""
        narrow = base_case()
        narrow["events"][1]["assertion"]["scope"]["population"] = "ER"
        self.assertEqual(global_label(narrow), "NONE")
        narrow["domain"]["population"]["ER"] = ["OTHER"]
        self.assertEqual(global_label(narrow), "B")
        flipped = base_case()
        flipped["events"][1]["assertion"]["scope"]["population"] = "ER"
        flipped["domain"]["population"]["PATIENT"] = ["ER"]
        flipped["domain"]["population"]["ER"] = ["ER", "NON_ER"]
        self.assertEqual(global_label(flipped), "B")
        flipped["domain"]["population"]["PATIENT"] = ["ER", "NON_ER"]
        self.assertEqual(global_label(flipped), "NONE")

    def test_fresh_alias_names_preserve_only_explicit_atom_coverage(self):
        """A case-ID or alias-name lookup cannot supply the scope semantics."""
        case = base_case()
        pop = case["domain"]["population"]
        pop["Z_GROUP"] = pop.pop("PATIENT")
        case["guarantees"][0]["scope"]["population"] = "Z_GROUP"
        case["events"][1]["assertion"]["scope"]["population"] = "Z_GROUP"
        self.assertEqual(global_label(case), "NONE")
        pop["Z_GROUP"] = ["OTHER"]
        self.assertEqual(global_label(case), "NONE")  # Both scope names stay equal.
        case["events"][1]["assertion"]["scope"]["population"] = "ER"
        self.assertEqual(global_label(case), "B")
        pop["Z_GROUP"] = ["ER", "OTHER"]
        self.assertEqual(global_label(case), "NONE")

    def test_small_seeded_domain_oracle_discriminates_both_coverage_policies(self):
        """Compare 120 synthetic populations against independently set-based coverage."""
        import random
        rng = random.Random(170)
        atoms = ["P0", "P1", "P2", "P3"]
        for policy in ("coverage/single-item-v1", "coverage/union-v1"):
            for trial in range(60):
                subsets = []
                for _ in range(3):
                    count = rng.randrange(1, 5)
                    subsets.append(set(rng.sample(atoms, count)))
                target, g_atoms, h_atoms = subsets
                with self.subTest(policy=policy, trial=trial):
                    case = base_case()
                    case["coverage_policy"] = policy
                    case["domain"]["population"].update({
                        "TARGET_CUSTOM": sorted(target),
                        "G_CUSTOM": sorted(g_atoms),
                        "H_CUSTOM": sorted(h_atoms),
                    })
                    case["events"][1]["assertion"]["scope"]["population"] = "TARGET_CUSTOM"
                    case["guarantees"][0]["scope"]["population"] = "G_CUSTOM"
                    second = copy.deepcopy(case["guarantees"][0])
                    second["id"] = "H"
                    second["scope"]["population"] = "H_CUSTOM"
                    case["guarantees"].append(second)
                    case["events"][1]["assertion"]["citations"] = ["G", "H"]
                    expected = (any(target <= s for s in (g_atoms, h_atoms))
                                if policy == "coverage/single-item-v1"
                                else target <= (g_atoms | h_atoms))
                    self.assertEqual(global_label(case), "NONE" if expected else "B")

    def test_surrogate_case_and_actor_ids_reject_cleanly_in_real_subprocess(self):
        """Strict UTF-8 process output must never crash on escaped lone surrogates."""
        import os
        import subprocess
        for slot in ("case_id", "actor"):
            with self.subTest(slot=slot), tempfile.TemporaryDirectory() as td:
                case = base_case()
                if slot == "case_id":
                    case["case_id"] = chr(0xD800)
                else:
                    case["events"][1]["actor"] = chr(0xD800)
                path = Path(td) / "surrogate.json"
                path.write_text(json.dumps(case), encoding="utf-8")
                env = dict(os.environ, PYTHONIOENCODING="utf-8:strict",
                           PYTHONDONTWRITEBYTECODE="1")
                result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1]
                                                       / "h32_scope_lab_v01.py"), str(path)],
                                        env=env, capture_output=True)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, b"")
                self.assertEqual(json.loads(result.stderr)["status"], "REJECTED_INPUT")

    def test_direct_api_rejects_mutating_dict_and_str_subclasses(self):
        """Reject non-JSON Python subclasses before repeated validation/read phases."""
        class StrangeDict(dict):
            def __getitem__(self, key):
                if key == "coverage_policy":
                    return "coverage/union-v1"
                return super().__getitem__(key)

        case = base_case()
        with self.assertRaises(ResearchInputError):
            evaluate_case(StrangeDict(case))
        case["events"][1]["assertion"]["citations"] = [type("Odd", (str,), {})("G")]
        with self.assertRaises(ResearchInputError):
            evaluate_case(case)

    def test_reviewed_label_semantics_remain_explicit_under_nonscope_rejections(self):
        """Pin current v0.1 label semantics, pending a separately versioned split."""
        for field, value in (("claim_kind", "other"), ("strength", "TENTATIVE"),
                             ("verification", "TEST_INVALID"), ("available_at", 21)):
            with self.subTest(field=field):
                case = base_case()
                case["guarantees"][0][field] = value
                result = evaluate_case(case)
                # This *is* the current cited-justification contract, not pure scope.
                self.assertEqual(result["checks"]["unsupported_scope_assertion"]
                                 ["earliest_global"], "B")
                self.assertEqual(result["checks"]["unsupported_firm_certification"]
                                 ["earliest_global"], "B")
                self.assertEqual(result["events"][1]["assertion_review"]
                                 ["effective_cited_justification"],
                                 "UNSUPPORTED_BY_CITED_EVIDENCE")



    def test_preservation_obligation_start_excludes_prior_event(self):
        """One tick before start_at must not be marked by the later obligation."""
        case = base_case()
        case["events"][0]["display_facets"]["population"] = "ER"
        case["obligations"] = [{"id":"P", "start_at":11, "end_at":20,
                                "channel":"display", "required_facets":{"population":"PATIENT"}}]
        self.assertEqual(global_label(case, "preservation_contract_breach"), "NONE")
        case["obligations"][0]["start_at"] = 10
        self.assertEqual(global_label(case, "preservation_contract_breach"), "A")

    def test_union_unknown_and_nonqualifying_strength_remain_distinct(self):
        """Missing premises cannot become firm eligible cover under union policy."""
        for change, expected, reason in (
            (("verification", "UNVERIFIED"), "UNKNOWN", "UNKNOWN"),
            (("strength", "TENTATIVE"), "B", "REJECTED_STRENGTH"),
        ):
            with self.subTest(change=change):
                case = base_case()
                case["coverage_policy"] = "coverage/union-v1"
                case["guarantees"][0]["scope"]["population"] = "ER"
                second = copy.deepcopy(case["guarantees"][0])
                second["id"] = "H"
                second["scope"]["population"] = "NON_ER"
                second[change[0]] = change[1]
                case["guarantees"].append(second)
                case["events"][1]["assertion"]["citations"] = ["G", "H"]
                self.assertEqual(global_label(case), expected)
                self.assertEqual(evaluate_case(case)["events"][1]["assertion_review"]
                                 ["citations"][1]["eligibility"], reason)

    def test_citation_diagnostics_echo_three_distinct_test_timestamps(self):
        """Diagnostic records disclose supplied time values without using publication as gate."""
        case = base_case()
        case["guarantees"][0].update({"available_at":5, "verified_at":6,
                                      "published_at":999})
        result = evaluate_case(case)
        cited = result["events"][1]["assertion_review"]["citations"][0]
        self.assertEqual({k:cited[k] for k in ("available_at", "verified_at", "published_at")},
                         {"available_at":5, "verified_at":6, "published_at":999})
        self.assertEqual(global_label(case), "NONE")
        case["guarantees"][0]["available_at"] = 21
        result = evaluate_case(case)
        self.assertEqual(result["events"][1]["assertion_review"]["citations"][0]
                         ["eligibility"], "REJECTED_NOT_AVAILABLE_TO_ACTOR")



    def test_overlapping_union_items_leave_holes_until_each_cell_is_covered(self):
        """Overlapping rectangles cannot fill their two opposite missing corners."""
        case = base_case()
        case["coverage_policy"] = "coverage/union-v1"
        case["domain"] = {
            "facility": {"left": ["a", "b"], "right": ["b", "c"],
                         "full": ["a", "b", "c"], "a": ["a"], "c": ["c"]},
            "period": {"early": ["q", "r"], "late": ["r", "s"],
                       "full": ["q", "r", "s"], "q": ["q"], "s": ["s"]},
            "population": {"group": ["p"]},
        }
        case["events"][1]["assertion"]["scope"] = {
            "facility": "full", "period": "full", "population": "group"}
        template = copy.deepcopy(case["guarantees"][0])
        case["guarantees"] = []
        scopes = (("left", "early"), ("right", "late"), ("a", "s"), ("c", "q"))
        for i, (facility, period) in enumerate(scopes):
            guarantee = copy.deepcopy(template)
            guarantee["id"] = f"item-{i}"
            guarantee["scope"] = {"facility": facility, "period": period,
                                  "population": "group"}
            case["guarantees"].append(guarantee)
            case["events"][1]["assertion"]["citations"] = [
                item["id"] for item in case["guarantees"]]
            with self.subTest(items=i + 1):
                self.assertEqual(global_label(case), "NONE" if i == 3 else "B")
        case["coverage_policy"] = "coverage/single-item-v1"
        self.assertEqual(global_label(case), "B")

    def test_translating_all_clocks_preserves_checks_and_translates_diagnostics(self):
        """Translate evidence, events, and active obligations as one clock system."""
        for changes, expected in (
            ({}, "NONE"),
            ({"available_at": 21}, "B"),
            ({"verified_at": 21}, "B"),
            ({"verified_at": None}, "UNKNOWN"),
            ({"available_at": 20, "verified_at": 20}, "NONE"),
        ):
            case = base_case()
            case["guarantees"][0].update(changes, published_at=999)
            case["events"][1]["scope_meta"] = None
            case["obligations"] = [{
                "id": "P", "start_at": 20, "end_at": 20, "channel": "typed",
                "required_facets": {"population": "PATIENT"},
            }]
            baseline = evaluate_case(case)
            self.assertEqual(baseline["checks"]["unsupported_scope_assertion"]
                             ["earliest_global"], expected)
            self.assertEqual(baseline["checks"]["preservation_contract_breach"]
                             ["earliest_global"], "B")
            for offset in (1, 37, 1000, 999_998_900):
                with self.subTest(changes=changes, offset=offset):
                    translated = copy.deepcopy(case)
                    for event in translated["events"]:
                        event["at"] += offset
                    for guarantee in translated["guarantees"]:
                        for field in ("available_at", "verified_at", "published_at"):
                            if guarantee[field] is not None:
                                guarantee[field] += offset
                    for obligation in translated["obligations"]:
                        obligation["start_at"] += offset
                        obligation["end_at"] += offset
                    result = evaluate_case(translated)
                    self.assertEqual(result["checks"], baseline["checks"])
                    self.assertEqual([event["local_checks"] for event in result["events"]],
                                     [event["local_checks"] for event in baseline["events"]])
                    self.assertEqual([event["at"] for event in result["events"]],
                                     [event["at"] + offset for event in baseline["events"]])
                    expected_review = copy.deepcopy(baseline["events"][1]["assertion_review"])
                    for citation in expected_review["citations"]:
                        for field in ("available_at", "verified_at", "published_at"):
                            if citation[field] is not None:
                                citation[field] += offset
                    self.assertEqual(result["events"][1]["assertion_review"], expected_review)


    def test_obligation_requires_event_inside_fixed_window(self):
        """Moving only the event clock must not carry a fixed obligation window."""
        case = base_case()
        case["events"][1]["scope_meta"] = None
        case["obligations"] = [{
            "id": "P", "start_at": 20, "end_at": 20, "channel": "typed",
            "required_facets": {"population": "PATIENT"},
        }]
        self.assertEqual(global_label(case, "preservation_contract_breach"), "B")
        for event_tick in (19, 21, 30):
            with self.subTest(event_tick=event_tick):
                shifted = copy.deepcopy(case)
                shifted["events"][1]["at"] = event_tick
                self.assertEqual(
                    global_label(shifted, "preservation_contract_breach"), "NONE"
                )

    def test_moving_only_assertion_time_changes_evidence_eligibility(self):
        """Evidence unavailable at B:20 must become eligible when B moves to 30."""
        case = base_case()
        case["guarantees"][0]["available_at"] = 21
        self.assertEqual(global_label(case), "B")
        case["events"][1]["at"] = 30
        self.assertEqual(global_label(case), "NONE")

    def test_tick_exact_maximum_is_valid_and_max_plus_one_rejected(self):
        """The synthetic one-billion tick limit is inclusive, not unbounded."""
        maximum = 1_000_000_000
        case = base_case()
        case["events"][1]["at"] = maximum
        case["guarantees"][0]["published_at"] = maximum
        self.assertEqual(global_label(case), "NONE")
        for field in ("event", "published_at"):
            with self.subTest(field=field):
                invalid = copy.deepcopy(case)
                if field == "event":
                    invalid["events"][1]["at"] = maximum + 1
                else:
                    invalid["guarantees"][0]["published_at"] = maximum + 1
                with self.assertRaisesRegex(
                    ResearchInputError, "expected nonnegative integer tick"
                ):
                    evaluate_case(invalid)


if __name__ == "__main__":
    unittest.main()
