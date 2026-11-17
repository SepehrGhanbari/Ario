"""W1 research-only tests for two uncovered TB-003 decision boundaries.

The known shared-custodian cross-witness gap is an expected failure,
not a passing assurance claim. No engine, history, keys or authority modified.
Original Trae patch is archived separately; these are independently reconstructed
controls from the source-pinned reviewer findings.
"""
from __future__ import annotations

import unittest

import w1_adversarial_input_sensitivity_v1 as w


class TestW1TraeBoundaryControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = w.load_pinned_engine()

    def test_gap1_ambiguous_custody_transfer_remains_unknown(self):
        p = self.p
        case = w.build_case(p)
        relay = p.Node("relay-a", "CUSTODIAN", case.scope, p.LAB, "FROZEN:relay-a")
        x1 = p.Edge("relay-in-a", "origin-a", "relay-a", "TRANSFERRED_TO", p.LAB,
                    "FROZEN:relay-in-a", subject_artifact_ref="artifact-a", sequence=3)
        x2 = p.Edge("relay-out-a", "relay-a", "holder-a", "TRANSFERRED_TO", p.LAB,
                    "FROZEN:relay-out-a", subject_artifact_ref="artifact-a", sequence=4)
        case = w.change_graph(case, nodes=case.graph.nodes+(relay,), edges=case.graph.edges+(x1,x2))
        report = p.evaluate_provenance(case)
        self.assertEqual(report.per_witness_custody[0].status, "UNKNOWN")
        self.assertEqual(report.per_witness_custody[0].reason, "MISSING_OR_AMBIGUOUS_CUSTODY_TRANSFER")
        self.assertEqual(report.per_witness_custody[1].status, "LAB_CHAIN_PRESENT")
        self.assertEqual(w.classify(p,case)["classification"], "UNKNOWN")

    def test_gap2_capture_after_mutation_remains_unknown(self):
        p = self.p
        case = w.build_case(p)
        # Keep custody sound and strictly sequenced; only the late capture fails.
        case = w.patch_node(case, "capture-a", capture_sequence=11)
        case = w.patch_edge(case, "xfer-a", sequence=12)
        report = p.evaluate_provenance(case)
        self.assertEqual(report.per_witness_custody[0].status, "LAB_CHAIN_PRESENT")
        self.assertEqual(report.per_witness_custody[1].status, "LAB_CHAIN_PRESENT")
        self.assertEqual(report.capture_order.status, "NOT_BEFORE_MUTATION")
        self.assertEqual(w.classify(p,case)["classification"], "UNKNOWN")

    def test_gap2_capture_equal_mutation_is_unknown(self):
        """M9 >= to > must be killed: equality is NOT strictly before."""
        p = self.p
        case = w.build_case(p)
        case = w.replace(case, mutation_sequence=2)  # capture-b=2, exactly on boundary
        report = p.evaluate_provenance(case)
        self.assertEqual(report.capture_order.status, "NOT_BEFORE_MUTATION")
        self.assertEqual(w.classify(p, case)["classification"], "UNKNOWN")

    def test_gap2_capture_just_before_mutation_is_conditional(self):
        """Positive neighbor: both original captures (1,2) precede mutation=3."""
        p = self.p
        case = w.replace(w.build_case(p), mutation_sequence=3)
        report = p.evaluate_provenance(case)
        self.assertEqual(report.capture_order.status, "LAB_BEFORE_MUTATION")
        self.assertEqual(w.classify(p, case)["classification"], "CONDITIONAL")

    @unittest.expectedFailure
    def test_known_gap3_shared_custodian_across_witnesses_not_separated(self):
        p = self.p
        case = w.build_case(p)
        case = w.patch_edge(case, "hold-b", target="holder-a")
        case = w.patch_edge(case, "xfer-b", target="holder-a")
        report = p.evaluate_provenance(case)
        self.assertEqual(tuple(f.status for f in report.per_witness_custody),
                         ("LAB_CHAIN_PRESENT","LAB_CHAIN_PRESENT"))
        # Stricter cross-witness custody separation is NOT implemented by TB-003.
        self.assertEqual(w.classify(p,case)["classification"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
