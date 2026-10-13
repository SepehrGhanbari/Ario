import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ario_cli import execute_request


class RuntimeEntryPointTests(unittest.TestCase):
    def request(self, **overrides):
        payload = {
            "audit_id": "AUDIT-CLI-001",
            "rule_versions": ["M0-1.0"],
            "configuration_id": "CLI-TEST",
            "execution_timestamp": "TEST-TIMESTAMP-001",
            "artifacts": {},
        }
        payload.update(overrides)
        return payload

    def reference(self, reference_id, reference_type="TEST"):
        return {
            "reference_id": reference_id,
            "reference_type": reference_type,
        }

    def state(self, state_id, content_reference):
        return {
            "state_id": state_id,
            "claim_id": "CLAIM-CLI-LRT01",
            "state_version": state_id,
            "observed_at": f"TIME-{state_id}",
            "state_context": {"snapshot_id": f"SNAPSHOT-{state_id}"},
            "content_reference": content_reference,
            "provenance": {
                "source_reference": self.reference(f"SOURCE-{state_id}"),
                "relation": "TEST_DERIVATION",
            },
        }

    def authorization(
        self,
        authorization_id,
        source_type,
        target_type,
        decision="AUTHORIZED",
        *,
        rule_id="M0-LRT01-XTYPE",
        rule_version="1.0",
        relation_type="EXPLICIT_RELATION",
    ):
        return {
            "authorization_id": authorization_id,
            "rule_id": rule_id,
            "rule_version": rule_version,
            "source_reference_type": source_type,
            "target_reference_type": target_type,
            "relation_type": relation_type,
            "decision": decision,
            "provenance": {
                "source_reference": self.reference(f"SOURCE-{authorization_id}"),
                "relation": "TEST_AUTHORIZATION",
            },
        }

    def edge(
        self, lineage_id, from_reference, to_reference,
        compatibility_authorizations=(),
    ):
        return {
            "lineage_id": lineage_id,
            "from_reference": from_reference,
            "to_reference": to_reference,
            "relation_type": "EXPLICIT_RELATION",
            "derivation_reference": self.reference(f"DERIVATION-{lineage_id}"),
            "admissibility_status": "ADMISSIBLE",
            "compatibility_authorizations": list(compatibility_authorizations),
            "provenance": {
                "source_reference": self.reference(f"SOURCE-{lineage_id}"),
                "relation": "TEST_DERIVATION",
            },
        }

    def run_cli_audit(self, audit_id, artifacts, rule_versions=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path = root / "request.json"
            ledger_path = root / "audit.jsonl"
            request_path.write_text(
                json.dumps(self.request(
                    audit_id=audit_id,
                    artifacts=artifacts,
                    rule_versions=rule_versions or ["M0-1.0"],
                )),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve().parents[1] / "ario_cli.py"),
                    "--input", str(request_path),
                    "--ledger", str(ledger_path),
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            ledger_lines = ledger_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(ledger_lines), 1)
            self.assertEqual(json.loads(ledger_lines[0]), result)
            return result

    def test_empty_primary_input_stays_unknown(self):
        result = execute_request(self.request())
        self.assertEqual(result["verdict"], "UNKNOWN")
        self.assertEqual(result["audit_id"], "AUDIT-CLI-001")

    def test_unknown_top_level_field_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown field"):
            execute_request(self.request(unrestricted_shell=True))

    def test_unknown_artifact_field_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown field"):
            execute_request(self.request(artifacts={"arbitrary_python": "print(1)"}))

    def test_cli_appends_ledger_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path = root / "request.json"
            ledger_path = root / "audit.jsonl"
            request_path.write_text(json.dumps(self.request()), encoding="utf-8")
            ledger_path.write_text('{"previous":"entry"}\n', encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve().parents[1] / "ario_cli.py"),
                    "--input", str(request_path),
                    "--ledger", str(ledger_path),
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            lines = ledger_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[1])["verdict"], "UNKNOWN")
            self.assertEqual(json.loads(completed.stdout)["verdict"], "UNKNOWN")

    def test_malformed_input_returns_nonzero_and_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{not-json", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parents[1] / "ario_cli.py"),
                 "--input", str(path)],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(json.loads(completed.stderr)["verdict"], "UNKNOWN")

    def test_cli_lrt01_same_type_temporal_references_pass(self):
        reference_a = self.reference("CONTENT-CLI-A", "STATE_CONTENT")
        reference_b = self.reference("CONTENT-CLI-B", "STATE_CONTENT")
        result = self.run_cli_audit(
            "LRT01-CLI-SAME-TYPE",
            {
                "historical_states": (
                    self.state("STATE-A", reference_a),
                    self.state("STATE-B", reference_b),
                ),
                "lineage_edges": (
                    self.edge("EDGE-AB", reference_a, reference_b),
                ),
            },
        )

        self.assertEqual(result["verdict"], "PASS")
        self.assertNotIn("TEMPORALLY_UNRESOLVED", result["violations"])

    def test_cli_lrt01_mismatched_endpoint_type_is_unresolved(self):
        reference_a = self.reference("CONTENT-CLI-MISMATCH-A", "STATE_CONTENT")
        reference_b = self.reference("CONTENT-CLI-MISMATCH-B", "STATE_CONTENT")
        mismatched_reference = self.reference(
            reference_a["reference_id"], "OTHER_KIND"
        )
        result = self.run_cli_audit(
            "LRT01-CLI-TYPE-MISMATCH",
            {
                "historical_states": (
                    self.state("STATE-A", reference_a),
                    self.state("STATE-B", reference_b),
                ),
                "lineage_edges": (
                    self.edge("EDGE-AB", mismatched_reference, reference_b),
                ),
            },
        )

        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("TEMPORALLY_UNRESOLVED", result["violations"])
        self.assertIn(mismatched_reference, result["artifacts_examined"])

    def test_cli_lrt01_duplicate_typed_content_references_are_unknown(self):
        shared_reference = self.reference("CONTENT-CLI-SHARED", "STATE_CONTENT")
        result = self.run_cli_audit(
            "LRT01-CLI-DUPLICATE-TYPED-REFERENCE",
            {
                "historical_states": (
                    self.state("STATE-A", shared_reference),
                    self.state("STATE-B", shared_reference),
                ),
            },
        )

        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("UNKNOWN", result["violations"])

    def test_cli_lrt01_distinct_state_and_content_ids_preserve_chain(self):
        references = (
            self.reference("CONTENT-CLI-CHAIN-A", "STATE_CONTENT"),
            self.reference("CONTENT-CLI-CHAIN-B", "STATE_CONTENT"),
            self.reference("CONTENT-CLI-CHAIN-C", "STATE_CONTENT"),
        )
        states = tuple(
            self.state(state_id, reference)
            for state_id, reference in zip(
                ("STATE-INSTANCE-A", "STATE-INSTANCE-B", "STATE-INSTANCE-C"),
                references,
            )
        )
        result = self.run_cli_audit(
            "LRT01-CLI-DISTINCT-IDS",
            {
                "historical_states": states,
                "lineage_edges": (
                    self.edge("EDGE-CHAIN-AB", references[0], references[1]),
                    self.edge("EDGE-CHAIN-BC", references[1], references[2]),
                ),
            },
        )

        self.assertEqual(result["verdict"], "PASS")
        self.assertNotIn("TEMPORALLY_UNRESOLVED", result["violations"])

    def test_cli_lrt01_caller_authorized_cross_type_edge_is_unknown(self):
        source = self.reference("CONTENT-CLI-CROSS-SHARED", "STATE_CONTENT")
        target = self.reference("CONTENT-CLI-CROSS-SHARED", "EVENT_RECORD")
        authorization = self.authorization(
            "AUTH-CLI-CROSS-A-B", "STATE_CONTENT", "EVENT_RECORD"
        )
        result = self.run_cli_audit(
            "LRT01-CLI-AUTHORIZED-CROSS-TYPE",
            {
                "historical_states": (
                    self.state("STATE-A", source),
                    self.state("STATE-B", target),
                ),
                "lineage_edges": (
                    self.edge("EDGE-A-B", source, target, (authorization,)),
                ),
            },
            ["M0-1.0", "M0-LRT01-XTYPE-1.0"],
        )

        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("UNKNOWN", result["violations"])
        self.assertIn(
            self.reference("SOURCE-AUTH-CLI-CROSS-A-B"),
            result["artifacts_examined"],
        )

    def test_cli_lrt01_forged_authorization_outside_trusted_policy_is_unknown(self):
        source = self.reference("CONTENT-CLI-FORGED-SHARED", "STATE_CONTENT")
        target = self.reference("CONTENT-CLI-FORGED-SHARED", "AUDIT_RESULT")
        forged_authorization = self.authorization(
            "AUTH-CLI-FORGED-POLICY", "STATE_CONTENT", "AUDIT_RESULT"
        )
        result = self.run_cli_audit(
            "LRT01-CLI-FORGED-AUTHORIZATION",
            {
                "historical_states": (
                    self.state("STATE-A", source),
                    self.state("STATE-B", target),
                ),
                "lineage_edges": (
                    self.edge(
                        "EDGE-FORGED-A-B",
                        source,
                        target,
                        (forged_authorization,),
                    ),
                ),
            },
            ["M0-1.0", "M0-LRT01-XTYPE-1.0"],
        )

        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("UNKNOWN", result["violations"])

    def test_cli_lrt01_cross_type_without_authorization_is_unresolved(self):
        source = self.reference("CONTENT-CLI-NOAUTH-SHARED", "STATE_CONTENT")
        target = self.reference("CONTENT-CLI-NOAUTH-SHARED", "EVENT_RECORD")
        result = self.run_cli_audit(
            "LRT01-CLI-CROSS-TYPE-NO-AUTH",
            {
                "historical_states": (
                    self.state("STATE-A", source),
                    self.state("STATE-B", target),
                ),
                "lineage_edges": (self.edge("EDGE-A-B", source, target),),
            },
        )

        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("TEMPORALLY_UNRESOLVED", result["violations"])

    def test_cli_lrt01_reversed_cross_type_authorization_does_not_match(self):
        source = self.reference("CONTENT-CLI-DIR-A", "STATE_CONTENT")
        target = self.reference("CONTENT-CLI-DIR-B", "EVENT_RECORD")
        reversed_authorization = self.authorization(
            "AUTH-CLI-REVERSED", "EVENT_RECORD", "STATE_CONTENT"
        )
        result = self.run_cli_audit(
            "LRT01-CLI-REVERSED-AUTH",
            {
                "historical_states": (
                    self.state("STATE-A", source),
                    self.state("STATE-B", target),
                ),
                "lineage_edges": (
                    self.edge("EDGE-A-B", source, target, (reversed_authorization,)),
                ),
            },
            ["M0-1.0", "M0-LRT01-XTYPE-1.0"],
        )

        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("TEMPORALLY_UNRESOLVED", result["violations"])


    # Always-on M0 reference firewall; JSON CLI must reflect the core contract.
    def test_m0_guard_cli_typed_audit_observation_without_f15(self):
        evidence = {
            "evidence_id": "GUARD-CLI-E",
            "observation_refs": [self.reference("GUARD-CLI-AUDIT", "AUDIT_RESULT")],
            "evidence_level": "STRUCTURAL_ONLY",
            "independence_status": "UNKNOWN",
            "derivation_reference": self.reference("GUARD-CLI-DER", "DERIVATION"),
            "scope": "SYNTHETIC-CLI-GUARD",
        }
        result = self.run_cli_audit("GUARD-CLI-BLOCK", {"evidence": [evidence]})
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("COMPOSITION_FORBIDDEN", result["violations"])

    def test_m0_guard_cli_scope_annotation_and_rule_profile(self):
        evidence = {
            "evidence_id": "GUARD-CLI-NORMAL-E",
            "observation_refs": [self.reference("GUARD-CLI-NORMAL-O", "OBSERVATION")],
            "evidence_level": "STRUCTURAL_ONLY",
            "independence_status": "UNKNOWN",
            "derivation_reference": self.reference("GUARD-CLI-NORMAL-D", "DERIVATION"),
            "scope": "SYNTHETIC-CLI-GUARD",
        }
        base = self.run_cli_audit("GUARD-CLI-BASE", {"evidence": [evidence]})
        declared = self.run_cli_audit(
            "GUARD-CLI-DECLARED", {"evidence": [evidence]},
            ["M0-1.0", "M0-F15-1.0"],
        )
        self.assertEqual(base["verdict"], "PASS")
        self.assertEqual(declared["verdict"], "PASS")
        self.assertNotEqual(base["verdict_basis"], declared["verdict_basis"])
        self.assertIn("M0-REF-GUARD-1.0", base["verdict_basis"])
        self.assertEqual(base["inspector_version"], "M0-1.1")
        self.assertEqual(base["rule_versions"], ["M0-1.0"])

    def test_m0_guard_cli_no_bypass_by_declared_rule_list(self):
        evidence = {
            "evidence_id": "GUARD-CLI-BYPASS",
            "observation_refs": [self.reference("GUARD-CLI-ANOTHER-AUDIT", "AUDIT_RESULT")],
            "evidence_level": "STRUCTURAL_ONLY",
            "independence_status": "UNKNOWN",
            "derivation_reference": self.reference("GUARD-CLI-SAFE-DER", "DERIVATION"),
            "scope": "SYNTHETIC-CLI-GUARD",
        }
        for versions in (["M0-1.0"], ["M0-1.0", "M0-F11-1.0"], ["M0-1.0", "M0-F15-1.0"]):
            result = self.run_cli_audit(
                "GUARD-CLI-DECLARATION-" + str(len(versions)),
                {"evidence": [evidence]}, versions,
            )
            self.assertEqual(result["verdict"], "FAIL")
            self.assertIn("COMPOSITION_FORBIDDEN", result["violations"])


if __name__ == "__main__":
    unittest.main()
