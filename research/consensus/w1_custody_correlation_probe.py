"""W1 research-only specification-candidate for the shared-custodian gap (F3).

The frozen TB-003 evaluator (Git blob 4faf010d73219af63c254097e9c135da68d60078)
has no cross-witness custody-identity axis: two witnesses whose LAB custody chains
pass through the same custodian still report CONDITIONAL. This module does NOT
modify, monkey-patch or re-pin the evaluator. It proposes a *separate*,
additive correlation axis and documents the current gap as an expected failure.

Semantics proposed (for review, NOT adopted in the engine):
  * collect the set of CUSTODIAN node ids on each witness's LAB custody chain
    (initial capture custodian, HELD_BY target, and TRANSFERRED_TO endpoints
    whose subject_artifact_ref is the witness artifact);
  * if the two sets intersect, a common custody actor exists in the declared
    graph -> report COMMON_CUSTODY_DETECTED (analogous to COMMON_CONTROL_DETECTED);
  * otherwise NO_COMMON_CUSTODY_IN_DECLARED_GRAPH.
This is a conservative over-approximation (it does not re-derive sequence
validity); over-detection can only add a dependency, never remove one.
It is deliberately a PROPOSAL: whether this should map to DEPENDENT, UNKNOWN, or
a new axis is a specification decision left to reviewers.
"""
from __future__ import annotations

import unittest

import w1_adversarial_input_sensitivity_v1 as w


def _custodian_ids(case, engine):
    ns = {n.node_id: n for n in case.graph.nodes}
    chains = []
    for art in case.witness_artifact_refs:
        chain = set()
        for e in case.graph.edges:
            if e.origin != engine.LAB:
                continue
            if e.kind == "CAPTURED_FROM" and e.source == art and e.target in ns:
                cust = ns[e.target].capture_custodian
                if cust is not None:
                    chain.add(cust)
            elif e.kind == "HELD_BY" and e.source == art:
                chain.add(e.target)
            elif e.kind == "TRANSFERRED_TO" and e.subject_artifact_ref == art:
                chain.update((e.source, e.target))
        chains.append(frozenset(chain))
    return chains


def custody_axis(case, engine):
    a, b = _custodian_ids(case, engine)
    shared = tuple(sorted(a & b))
    if shared:
        return "COMMON_CUSTODY_DETECTED", shared
    return "NO_COMMON_CUSTODY_IN_DECLARED_GRAPH", ()


def _relay(engine, case, seq_in, seq_out, witness):
    """Build a shared MIDDLE custodian (relay) feeding one witness chain."""
    art = "artifact-a" if witness == "a" else "artifact-b"
    holder = "holder-a" if witness == "a" else "holder-b"
    origin = "origin-a" if witness == "a" else "origin-b"
    node = engine.Node("relay-m", "CUSTODIAN", case.scope, engine.LAB, "FROZEN:relay-m")
    e_in = engine.Edge("r-in-" + witness, origin, "relay-m", "TRANSFERRED_TO", engine.LAB,
                       "FROZEN:r-in-" + witness, subject_artifact_ref=art, sequence=seq_in)
    e_out = engine.Edge("r-out-" + witness, "relay-m", holder, "TRANSFERRED_TO", engine.LAB,
                        "FROZEN:r-out-" + witness, subject_artifact_ref=art, sequence=seq_out)
    return node, e_in, e_out


def _shared_middle_case(engine, sep):
    drop = {"xfer-a", "xfer-b"}
    na, ia, oa = _relay(engine, sep, 3, 4, "a")
    nb, ib, ob = _relay(engine, sep, 5, 6, "b")
    edges = tuple(e for e in sep.graph.edges if e.edge_id not in drop) + (ia, oa, ib, ob)
    return w.change_graph(sep, nodes=sep.graph.nodes + (na,), edges=edges)


class TestCrossWitnessCustodyCorrelation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = w.load_pinned_engine()
        cls.sep = w.build_case(cls.e)

    def test_baseline_has_no_common_custody(self):
        status, shared = custody_axis(self.sep, self.e)
        self.assertEqual(status, "NO_COMMON_CUSTODY_IN_DECLARED_GRAPH")
        self.assertEqual(shared, ())

    def test_shared_final_custodian_detected(self):
        case = w.patch_edge(w.patch_edge(self.sep, "hold-b", target="holder-a"),
                            "xfer-b", target="holder-a")
        self.assertEqual(custody_axis(case, self.e), ("COMMON_CUSTODY_DETECTED", ("holder-a",)))

    def test_shared_initial_custodian_detected(self):
        case = w.patch_edge(w.patch_node(self.sep, "capture-b", capture_custodian="origin-a"),
                            "xfer-b", source="origin-a")
        self.assertEqual(custody_axis(case, self.e), ("COMMON_CUSTODY_DETECTED", ("origin-a",)))

    def test_shared_middle_custodian_detected(self):
        case = _shared_middle_case(self.e, self.sep)
        self.assertEqual(custody_axis(case, self.e), ("COMMON_CUSTODY_DETECTED", ("relay-m",)))

    @unittest.expectedFailure
    def test_frozen_engine_still_reports_conditional_for_shared_final(self):
        """Documents the gap: the frozen engine does not expose the new axis.

        This expected failure stays until a reviewed specification decides whether
        shared custody maps to DEPENDENT, UNKNOWN, or a separate axis. It must not
        be 'fixed' by editing the frozen evaluator.
        """
        case = w.patch_edge(w.patch_edge(self.sep, "hold-b", target="holder-a"),
                            "xfer-b", target="holder-a")
        self.assertEqual(w.classify(self.e, case)["classification"], "DEPENDENT")

    def test_frozen_engine_compromise_path_is_unchanged(self):
        """Regression guard: the engine's existing compromise handling still flags UNKNOWN."""
        case = w.patch_edge(w.patch_edge(self.sep, "hold-b", target="holder-a"),
                            "xfer-b", target="holder-a")
        case = w.replace(case, compromised_node_ids=("holder-a",))
        self.assertEqual(w.classify(self.e, case)["classification"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
