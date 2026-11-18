"""Synthetic controls for ARG-01. Standard library only; no actual tools invoked."""
import unittest

from research.arg01_lineage_lab_v0_1 import (
    Node, TRUSTED, UNTRUSTED, UNKNOWN,
    derive_origin, evaluate_derived, evaluate_oracle_control,
)


def base_graph():
    return {
        "user": Node(root_fixture_origin=TRUSTED),
        "web": Node(root_fixture_origin=UNTRUSTED),
        "summary": Node(parents=("web",), self_declared_origin=TRUSTED),
        "derived_body": Node(parents=("summary",), self_declared_origin=TRUSTED),
        "recipient": Node(parents=("user",)),
        "evil_recipient": Node(parents=("summary",), self_declared_origin=TRUSTED),
    }


class SyntheticLineageTests(unittest.TestCase):
    def test_benign_user_recipient_external_body(self):
        self.assertEqual(evaluate_derived("SIMULATED_SEND_EMAIL", {
            "recipient": "recipient", "body": "derived_body"}, base_graph())["result"], "ALLOW")

    def test_untrusted_recipient_laundered_as_trusted_is_blocked(self):
        r = evaluate_derived("SIMULATED_SEND_EMAIL", {
            "recipient": "evil_recipient", "body": "derived_body"}, base_graph())
        self.assertEqual(r["result"], "BLOCK")
        self.assertEqual(r["origin_sets"]["recipient"], frozenset({UNTRUSTED}))

    def test_comment_cannot_authorize_merge_ref(self):
        r = evaluate_derived("SIMULATED_GITHUB_MERGE", {
            "target_ref": "evil_recipient", "description": "summary"}, base_graph())
        self.assertEqual(r["result"], "BLOCK")
        self.assertEqual(r["authority"], "NONE")

    def test_external_pdf_cannot_supply_deletion_path(self):
        self.assertEqual(evaluate_derived("SIMULATED_DELETE_FILE", {
            "path": "summary", "note": "summary"}, base_graph())["result"], "BLOCK")

    def test_missing_body_cannot_be_implicitly_permitted(self):
        self.assertEqual(evaluate_derived("SIMULATED_SEND_EMAIL", {
            "recipient": "recipient"}, base_graph())["result"], UNKNOWN)

    def test_missing_body_node_is_unknown(self):
        self.assertEqual(evaluate_derived("SIMULATED_SEND_EMAIL", {
            "recipient": "recipient", "body": "missing"}, base_graph())["result"], UNKNOWN)

    def test_body_cycle_is_unknown(self):
        g = base_graph()
        g["a"] = Node(parents=("b",))
        g["b"] = Node(parents=("a",))
        self.assertEqual(evaluate_derived("SIMULATED_SEND_EMAIL", {
            "recipient": "recipient", "body": "a"}, g)["result"], UNKNOWN)

    def test_missing_parent_cannot_be_trusted(self):
        g = base_graph()
        g["hidden"] = Node(parents=("unknown_parent",), self_declared_origin=TRUSTED)
        self.assertIsNone(derive_origin(g, "hidden"))

    def test_mixed_trusted_untrusted_target_is_blocked(self):
        g = base_graph()
        g["mixed"] = Node(parents=("user", "summary"))
        self.assertEqual(evaluate_derived("SIMULATED_SEND_EMAIL", {
            "recipient": "mixed", "body": "derived_body"}, g)["result"], "BLOCK")

    def test_replay_without_changed_provenance_remains_blocked(self):
        g = base_graph()
        args = {"recipient": "evil_recipient", "body": "derived_body"}
        self.assertEqual(evaluate_derived("SIMULATED_SEND_EMAIL", args, g)["result"], "BLOCK")
        g["retry"] = Node(parents=("evil_recipient",), self_declared_origin=TRUSTED)
        self.assertEqual(evaluate_derived("SIMULATED_SEND_EMAIL", {
            **args, "recipient": "retry"}, g)["result"], "BLOCK")

    def test_unknown_root_label_is_unknown(self):
        self.assertIsNone(derive_origin({"x": Node(root_fixture_origin=UNKNOWN)}, "x"))

    def test_attacker_derived_root_origin_is_unknown(self):
        g = base_graph()
        g["fake"] = Node(parents=("web",), root_fixture_origin=TRUSTED)
        self.assertIsNone(derive_origin(g, "fake"))

    def test_iterative_budget_unknown_not_recursion_crash(self):
        g = {"root": Node(root_fixture_origin=TRUSTED)}
        for i in range(1500):
            g[str(i)] = Node(parents=(str(i-1) if i else "root",))
        self.assertIsNone(derive_origin(g, "1499"))

    def test_unrecognized_tool_cannot_be_authorized(self):
        self.assertEqual(evaluate_derived("SEND_REAL_EMAIL", {
            "recipient": "recipient", "body": "summary"}, base_graph())["result"], UNKNOWN)

    def test_oracle_arm_separately_labeled(self):
        oracle = evaluate_oracle_control("SIMULATED_SEND_EMAIL", {
            "recipient": frozenset({TRUSTED}), "body": frozenset({UNTRUSTED})})
        derived = evaluate_derived("SIMULATED_SEND_EMAIL", {
            "recipient": "evil_recipient", "body": "derived_body"}, base_graph())
        self.assertEqual(oracle["arm"], "SUPPLIED_FIXTURE_LABELS")
        self.assertEqual(derived["arm"], "DERIVED_LINEAGE")
        self.assertEqual(oracle["result"], "ALLOW")
        self.assertEqual(derived["result"], "BLOCK")
        self.assertEqual(oracle["source_authentication"], UNKNOWN)

    def test_incomplete_origin_control_remains_unknown(self):
        r = evaluate_oracle_control("SIMULATED_SEND_EMAIL", {
            "recipient": frozenset({TRUSTED}), "body": None})
        self.assertEqual(r["result"], UNKNOWN)

    def test_no_surprise_origin_promotion(self):
        for origin in (TRUSTED, UNTRUSTED):
            with self.subTest(origin=origin):
                g = {"root": Node(root_fixture_origin=origin),
                     "derived": Node(parents=("root",), self_declared_origin=TRUSTED)}
                self.assertEqual(derive_origin(g, "derived"), frozenset({origin}))

    def test_duplicate_root_mentions_do_not_raise(self):
        g = base_graph()
        g["joined"] = Node(parents=("web", "web", "user"))
        self.assertEqual(derive_origin(g, "joined"), frozenset({UNTRUSTED, TRUSTED}))


if __name__ == "__main__":
    unittest.main()
