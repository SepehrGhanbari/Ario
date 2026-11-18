"""Research-only negative control for proposed custody-correlation axis.

A LAB-labelled TRANSFERRED_TO edge whose source is not reachable from the
witness's initial capture custodian is not part of that witness's valid
per-witness custody chain, but the proposed axis over-approximates by collecting
ALL transfer endpoints tied to the artifact. Keep this test as xfail while
specification and implementation choices remain HOLD.
"""
from __future__ import annotations
import unittest
import w1_adversarial_input_sensitivity_v1 as w
import w1_custody_correlation_probe as c


class TestW1CustodyAxisExtraEdge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = w.load_pinned_engine()
        cls.sep = w.build_case(cls.p)

    def extra_edge_case(self):
        p = self.p
        disconnected = p.Edge(
            "unused-b", "origin-a", "holder-b", "TRANSFERRED_TO", p.LAB,
            "FROZEN:unused-b", subject_artifact_ref="artifact-b", sequence=9
        )
        return w.change_graph(self.sep, edges=self.sep.graph.edges + (disconnected,))

    def test_control_baseline_separate_declared_custody(self):
        self.assertEqual(c.custody_axis(self.sep, self.p),
                         ("NO_COMMON_CUSTODY_IN_DECLARED_GRAPH", ()))

    def test_unused_extra_edge_does_not_change_engine_custody(self):
        case = self.extra_edge_case()
        result = self.p.evaluate_provenance(case)
        self.assertEqual(tuple(x.status for x in result.per_witness_custody),
                         ("LAB_CHAIN_PRESENT", "LAB_CHAIN_PRESENT"))
        self.assertEqual(w.classify(self.p, case)["classification"], "CONDITIONAL")

    @unittest.expectedFailure
    def test_proposed_axis_should_ignore_unreachable_transfer_edge(self):
        # KNOWN GAP in experimental proposal, NOT in pinned TB-003 evaluator:
        # this asserted desired property currently fails; axis reports
        # COMMON_CUSTODY_DETECTED due to unrelated origin-a endpoint.
        self.assertEqual(c.custody_axis(self.extra_edge_case(), self.p),
                         ("NO_COMMON_CUSTODY_IN_DECLARED_GRAPH", ()))


if __name__ == "__main__":
    unittest.main()
