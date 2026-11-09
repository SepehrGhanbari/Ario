"""Falsification-oriented tests for an isolated synthetic H3.2 laboratory.

These tests do NOT import, execute, or score the existing Ario M0 engine.
"""

from __future__ import annotations

import copy
import json
import io
import os
import subprocess
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

    def test_typed_metadata_loss_requires_a_previously_present_key(self):
        """Null and empty maps cannot lose keys that were never supplied."""
        transitions = (
            (None, None, "NONE"),
            (None, {}, "NONE"),
            ({}, None, "NONE"),
            ({}, {}, "NONE"),
            ({}, {"population": "ER"}, "NONE"),
            ({"population": "PATIENT"}, None, "B"),
            ({"population": "PATIENT"}, {}, "B"),
            ({"population": "PATIENT"}, {"population": "ER"}, "NONE"),
        )
        for older, newer, expected in transitions:
            with self.subTest(older=older, newer=newer):
                case = base_case()
                case["events"][0]["scope_meta"] = older
                case["events"][1]["scope_meta"] = newer
                self.assertEqual(global_label(case, "typed_metadata_loss"), expected)

    def test_translating_all_known_times_preserves_verdicts(self):
        """Temporal decisions depend on relative times, not the baseline tick 20."""
        for late_field in (None, "available_at", "verified_at"):
            case = base_case()
            if late_field is not None:
                case["guarantees"][0][late_field] = 21
            case["obligations"] = [{
                "id": "P", "start_at": 10, "end_at": 20, "channel": "typed",
                "required_facets": {"population": "PATIENT"},
            }]
            baseline = evaluate_case(case)
            for offset in (1, 37, 1000):
                with self.subTest(late_field=late_field, offset=offset):
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
                    self.assertEqual(result["events"][1]["assertion_review"],
                                     baseline["events"][1]["assertion_review"])

    def test_eligibility_boundaries_follow_each_asserting_event_time(self):
        """Moving an assertion changes which evidence was eligible at that event."""
        for field in ("available_at", "verified_at"):
            for event_at in (30, 70, 101):
                for relative_tick, expected in ((-1, "NONE"), (0, "NONE"), (1, "B")):
                    with self.subTest(field=field, event_at=event_at,
                                      relative_tick=relative_tick):
                        case = base_case()
                        case["events"][1]["at"] = event_at
                        case["guarantees"][0][field] = event_at + relative_tick
                        self.assertEqual(global_label(case), expected)

    def test_scope_alias_and_atom_renaming_preserve_coverage(self):
        """Symbol spellings carry no scope semantics beyond the supplied domain."""
        for guarantee_population, expected in (("PATIENT", "NONE"), ("ER", "B")):
            with self.subTest(guarantee_population=guarantee_population):
                case = base_case()
                case["guarantees"][0]["scope"]["population"] = guarantee_population
                baseline = evaluate_case(case)
                renamed = copy.deepcopy(case)
                aliases = {}
                for dimension, expansions in case["domain"].items():
                    aliases[dimension] = {name: f"set_{dimension}_{i}"
                                          for i, name in enumerate(expansions)}
                    atoms = sorted({atom for members in expansions.values() for atom in members})
                    atom_names = {atom: f"atom_{dimension}_{i}" for i, atom in enumerate(atoms)}
                    renamed["domain"][dimension] = {
                        aliases[dimension][name]: [atom_names[atom] for atom in members]
                        for name, members in expansions.items()
                    }
                for guarantee in renamed["guarantees"]:
                    guarantee["scope"] = {dimension: aliases[dimension][term]
                                          for dimension, term in guarantee["scope"].items()}
                for event in renamed["events"]:
                    if event["assertion"] is not None:
                        event["assertion"]["scope"] = {
                            dimension: aliases[dimension][term]
                            for dimension, term in event["assertion"]["scope"].items()
                        }
                    for field in ("display_facets", "scope_meta"):
                        if event[field] is not None:
                            event[field] = {dimension: aliases[dimension][term]
                                            for dimension, term in event[field].items()}
                result = evaluate_case(renamed)
                self.assertEqual(result["checks"], baseline["checks"])
                self.assertEqual(result["checks"]["unsupported_scope_assertion"]
                                 ["earliest_global"], expected)
                self.assertEqual(result["events"][1]["assertion_review"],
                                 baseline["events"][1]["assertion_review"])

    def test_supplied_atom_expansions_override_familiar_alias_names(self):
        """Identical aliases can describe different finite sets in another fixture."""
        case = base_case()
        case["guarantees"][0]["scope"]["population"] = "ER"
        self.assertEqual(global_label(case), "B")
        case["domain"]["population"]["ER"] = ["ER", "NON_ER"]
        self.assertEqual(global_label(case), "NONE")
        case["domain"]["population"]["PATIENT"] = ["ER"]
        self.assertEqual(global_label(case), "NONE")
        case["domain"]["population"]["PATIENT"] = ["UNRELATED"]
        self.assertEqual(global_label(case), "B")

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

    def _assert_cli_rejected(self, raw: bytes) -> None:
        """Verify rejected bytes cannot leak success JSON to standard output."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "synthetic.json"
            path.write_bytes(raw)
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main([str(path)])
            self.assertEqual(code, 2)
            self.assertEqual(out.getvalue(), "")
            self.assertEqual(json.loads(err.getvalue())["status"], "REJECTED_INPUT")

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
        """Check the research contract: cli rejects deeply nested json and huge integer."""
        self._assert_cli_rejected(("[" * 1300 + "0" + "]" * 1300).encode("utf-8"))
        self._assert_cli_rejected(('{"case_id": ' + "7" * 5000 + '}').encode("utf-8"))

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

    def test_cli_json_output_round_trips_lone_surrogates_under_strict_utf8(self):
        """Accepted JSON strings remain serializable through a real UTF-8 pipe."""
        case = base_case()
        case["case_id"] = "case-\ud800-\u03b1"
        case["events"][1]["actor"] = "actor-\udfff"
        case["guarantees"][0]["id"] = "evidence-\udc00"
        case["events"][1]["assertion"]["citations"] = ["evidence-\udc00"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "escaped-strings.json"
            path.write_text(json.dumps(case, ensure_ascii=True), encoding="ascii")
            environment = os.environ.copy()
            environment["PYTHONIOENCODING"] = "utf-8:strict"
            process = subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parents[1] / "h32_scope_lab_v01.py"),
                 str(path)], capture_output=True, encoding="utf-8", errors="strict",
                env=environment, timeout=10, check=False,
            )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stderr, "")
        result = json.loads(process.stdout)
        self.assertEqual(result["case_id"], case["case_id"])
        self.assertEqual(result["events"][1]["actor"], case["events"][1]["actor"])
        self.assertEqual(result["events"][1]["assertion_review"]["citations"][0]["id"],
                         case["guarantees"][0]["id"])

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


if __name__ == "__main__":
    unittest.main()
