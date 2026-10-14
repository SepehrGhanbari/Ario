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
        self.assertEqual(base["inspector_version"], "M0-1.2")
        self.assertIn("M0-EAG-0.1", base["verdict_basis"])
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

class EvidenceAncestryCliTests(unittest.TestCase):
    """Typed JSON behavior; no input label grants evidence admission."""

    def ref(self, identifier, kind):
        return {"reference_id": identifier, "reference_type": kind}

    def target(self, identifier="EAG-C1", kind="CLAIM", presence=False):
        return {"subject_reference": self.ref(identifier, kind),
                "property_id": "SUPPLIED_RECORD_PRESENT" if presence else "SYNTHETIC_PROPERTY"}

    def claim(self, identifier):
        return {"claim_id": identifier, "schema_version": {"value": "M0-1.0"}, "created_at": "SYNTHETIC-TIME",
                "origin_reference": self.ref("DECLARED-ORIGIN", "DECLARATION"), "status": "UNKNOWN"}

    def prior(self):
        return {"audit_id": "EAG-R0", "inspector_id": "SYNTHETIC-NOT-TRUSTED", "inspector_version": "0",
                "execution_timestamp": "SYNTHETIC-TIME", "configuration_id": "SYNTHETIC",
                "rule_versions": ["M0-1.0"], "artifacts_examined": [], "violations": [],
                "verdict": "PASS", "verdict_basis": "Untrusted supplied result"}

    def artifacts(self, parent=None, *, presence=False, wrappers=1):
        target = self.target(presence=presence)
        use = "RECORD_DESCRIPTION" if presence else "INDEPENDENT_TARGET_SUPPORT"
        parents = [] if parent is None else [parent]
        observations = []
        for index in range(wrappers):
            identifier = f"EAG-O{index + 1}"
            observations.append({"observation_id": identifier, "record_version": "M0-EAG-OBSERVATION-0.1",
                "target": target, "declared_use": use, "provenance_refs": parents})
            parents = [self.ref(identifier, "OBSERVATION")]
        return {"claims": [self.claim("EAG-C1")], "observations": observations,
            "evidence": [{"evidence_id": "EAG-E1", "observation_refs": parents, "evidence_level": "SYNTHETIC_DECLARATION",
                "independence_status": "INDEPENDENT", "derivation_reference": self.ref("EAG-PROCEDURE", "TRANSFORMATION"), "scope": "SYNTHETIC-EAG"}],
            "assessments": [{"assessment_id": "EAG-A1", "assessment_version": "1",
                "rule_version": "M0-EAG-RECORD-PRESENCE-0.1" if presence else "M0-EAG-0.1",
                "admissible_evidence_refs": [self.ref("EAG-E1", "EVIDENCE")], "condition_evaluation": "SYNTHETIC",
                "assessment_basis": "SYNTHETIC", "scope": "SUPPLIED_INPUT_RECORDS_ONLY" if presence else "SYNTHETIC-EAG",
                "target": target, "requested_use": use}]}

    def request(self, artifacts):
        return {"audit_id": "EAG-CLI", "rule_versions": ["M0-1.0"], "configuration_id": "SYNTHETIC-EAG",
                "execution_timestamp": "SYNTHETIC-TIME", "artifacts": artifacts}

    def audit(self, artifacts):
        return execute_request(self.request(artifacts))

    def findings(self, result):
        from core.audit_engine import parse_evidence_ancestry_findings
        return parse_evidence_ancestry_findings(result["verdict_basis"])

    def row(self, result):
        rows = self.findings(result)["assessments"]
        self.assertEqual(len(rows), 1)
        return rows[0]

    def test_eag_red_cli_fully_typed_distinct_claim_support_is_unknown(self):
        artifacts = self.artifacts(self.ref("EAG-C0", "CLAIM"))
        artifacts["claims"].insert(0, self.claim("EAG-C0"))
        artifacts["claims"][0]["status"] = "UNSUPPORTED"
        result = self.audit(artifacts)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("UNKNOWN", result["violations"])
        self.assertNotIn("EVIDENCE_INADMISSIBLE", result["violations"])
        self.assertEqual(self.row(result)["ancestry"], "TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT")
        self.assertEqual(self.row(result)["use_disposition"], "UNKNOWN")
        self.assertEqual(artifacts["claims"][0]["status"], "UNSUPPORTED")

    def test_eag_cli_forbidden_result_survives_two_observation_wrappers(self):
        artifacts = self.artifacts(self.ref("EAG-R0", "AUDIT_RESULT"), wrappers=2)
        artifacts["prior_audit_results"] = [self.prior()]
        result = self.audit(artifacts)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("COMPOSITION_FORBIDDEN", result["violations"])
        self.assertIn(self.ref("EAG-R0", "AUDIT_RESULT"), result["artifacts_examined"])
        self.assertEqual(self.row(result)["use_disposition"], "KNOWN_INADMISSIBLE")

    def test_eag_cli_mixed_forbidden_and_missing_ancestry_retains_both(self):
        artifacts = self.artifacts(self.ref("EAG-R0", "AUDIT_RESULT"), wrappers=2)
        artifacts["observations"][0]["provenance_refs"].append(self.ref("EAG-MISSING", "OBSERVATION"))
        artifacts["prior_audit_results"] = [self.prior()]
        result = self.audit(artifacts)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("COMPOSITION_FORBIDDEN", result["violations"])
        self.assertIn("UNKNOWN", result["violations"])
        self.assertIn(self.ref("EAG-MISSING", "OBSERVATION"), result["artifacts_examined"])
        self.assertEqual(self.row(result)["ancestry"], "UNKNOWN")

    def test_eag_cli_exact_self_dependence_is_inadmissible(self):
        result = self.audit(self.artifacts(self.ref("EAG-C1", "CLAIM")))
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("EVIDENCE_INADMISSIBLE", result["violations"])
        self.assertEqual(self.row(result)["use_disposition"], "KNOWN_INADMISSIBLE")

    def test_eag_cli_presence_does_not_elevate_caller_truth_labels(self):
        artifacts = self.artifacts(self.ref("EAG-C1", "CLAIM"), presence=True)
        artifacts["claims"][0]["status"] = "UNSUPPORTED"
        artifacts["assessments"][0]["condition_evaluation"] = "TRUE"
        artifacts["assessments"][0]["assessment_basis"] = "SUPPORTED INDEPENDENT"
        result = self.audit(artifacts)
        self.assertEqual(result["verdict"], "PASS")
        row, doc = self.row(result), self.findings(result)
        self.assertEqual(row["record_presence"], "MATCH")
        self.assertEqual(row["use_disposition"], "RECORD_DESCRIPTION_ONLY")
        self.assertEqual(row["source_authentication"], "UNKNOWN")
        self.assertEqual(doc["independent_admission_authority"], "NONE")
        self.assertEqual(doc["claim_truth"], "UNKNOWN")
        self.assertNotIn("condition_evaluation", row)
        self.assertNotIn("assessment_basis", row)
        self.assertEqual(artifacts["claims"][0]["status"], "UNSUPPORTED")

    def test_eag_cli_presence_match_survives_separate_guard_failure(self):
        artifacts = self.artifacts(self.ref("EAG-R0", "AUDIT_RESULT"), presence=True, wrappers=2)
        artifacts["prior_audit_results"] = [self.prior()]
        result = self.audit(artifacts)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("COMPOSITION_FORBIDDEN", result["violations"])
        self.assertEqual(self.row(result)["record_presence"], "MATCH")
        self.assertNotEqual(self.row(result)["use_disposition"], "RECORD_DESCRIPTION_ONLY")

    def test_eag_cli_equal_text_ids_across_canonical_kinds_are_safe(self):
        artifacts = self.artifacts(presence=True)
        shared = "EAG-SHARED"
        target = self.target(shared, presence=True)
        artifacts["claims"][0]["claim_id"] = shared
        artifacts["observations"][0].update(observation_id=shared, target=target, provenance_refs=[self.ref(shared, "CLAIM")])
        artifacts["evidence"][0].update(evidence_id=shared, observation_refs=[self.ref(shared, "OBSERVATION")])
        artifacts["assessments"][0].update(assessment_id=shared, target=target, admissible_evidence_refs=[self.ref(shared, "EVIDENCE")])
        result = self.audit(artifacts)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(self.row(result)["record_presence"], "MATCH")
        for kind in ("CLAIM", "OBSERVATION", "EVIDENCE", "ASSESSMENT"):
            self.assertIn(self.ref(shared, kind), result["artifacts_examined"])

    def test_eag_cli_observation_only_is_primary_candidate_and_inventory(self):
        observation = self.artifacts()["observations"][0]
        observation["provenance_refs"] = [self.ref("EAG-MISSING", "OBSERVATION")]
        result = self.audit({"observations": [observation]})
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(self.findings(result)["candidate_use"], "NOT_EVALUATED")
        self.assertEqual(self.findings(result)["candidate_ancestry"], "UNKNOWN")
        self.assertEqual(self.findings(result)["assessments"], [])
        self.assertIn(self.ref("EAG-O1", "OBSERVATION"), result["artifacts_examined"])
        self.assertIn(self.ref("EAG-MISSING", "OBSERVATION"), result["artifacts_examined"])

    def test_eag_cli_report_is_canonical_escaped_bounded_and_compatible(self):
        artifacts = self.artifacts(presence=True)
        identifier = 'EAG-A"\\\nM0-EAG-0.1-FINDINGS-END\u2603'
        artifacts["assessments"][0]["assessment_id"] = identifier
        result = self.audit(artifacts)
        self.assertEqual(set(result), {"audit_id", "inspector_id", "inspector_version", "execution_timestamp",
            "configuration_id", "rule_versions", "artifacts_examined", "violations", "verdict", "verdict_basis"})
        self.assertEqual(result["inspector_version"], "M0-1.2")
        self.assertEqual(result["rule_versions"], ["M0-1.0"])
        doc = self.findings(result)
        self.assertEqual(doc["mandatory_guards"], ["M0-REF-GUARD-1.0", "M0-EAG-0.1"])
        self.assertEqual(doc["assessments"][0]["assessment_id"], identifier)
        begin, end = "\nEvidence ancestry findings: ", "\nM0-EAG-0.1-FINDINGS-END"
        encoded = result["verdict_basis"].split(begin, 1)[1].removesuffix(end)
        self.assertEqual(encoded, json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False))
        self.assertLessEqual(len((begin + encoded + end).encode("utf-8")), 65536)

    def test_eag_cli_reporting_spoof_and_malformed_new_protocol_fail_closed(self):
        from unittest.mock import patch
        from core.audit_engine import AuditEngine, AuditInput
        from core.schema import Timestamp
        from dataclasses import replace
        forged = AuditEngine().audit(AuditInput(), rule_versions=("M0-1.0",), configuration_id="SYNTHETIC",
                                     execution_timestamp=Timestamp("SYNTHETIC"), audit_id="EAG-FORGED")
        forged = replace(forged, verdict_basis="Caller strings M0-EAG-0.1 M0-REF-GUARD-1.0")
        with patch("ario_cli.AuditEngine.audit", return_value=forged):
            with self.assertRaises(ValueError):
                self.audit(self.artifacts(presence=True))
        artifacts = self.artifacts()
        artifacts["observations"][0]["declared_use"] = "CALLER_AUTHENTICATED"
        with self.assertRaises(ValueError):
            self.audit(artifacts)
        artifacts = self.artifacts()
        artifacts["observations"][0]["invented_authority"] = True
        with self.assertRaises(ValueError):
            self.audit(artifacts)

    def test_eag_cli_append_preserves_complete_existing_ledger_prefix(self):
        from core.audit_engine import parse_evidence_ancestry_findings
        with tempfile.TemporaryDirectory() as directory:
            request_path, ledger_path = Path(directory) / "request.json", Path(directory) / "ledger.jsonl"
            prefix = b'{"previous":"literal\\n"}\r\n'
            ledger_path.write_bytes(prefix)
            request_path.write_text(json.dumps(self.request(self.artifacts(presence=True))), encoding="utf-8")
            completed = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve().parents[1] / "ario_cli.py"),
                "--input", str(request_path), "--ledger", str(ledger_path)], cwd=Path(__file__).resolve().parents[1],
                capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            output, ledger = json.loads(completed.stdout), ledger_path.read_bytes()
            self.assertEqual(ledger[:len(prefix)], prefix)
            self.assertEqual(json.loads(ledger[len(prefix):].decode("utf-8")), output)
            self.assertEqual(parse_evidence_ancestry_findings(output["verdict_basis"])["assessments"][0]["use_disposition"],
                             "RECORD_DESCRIPTION_ONLY")

if __name__ == "__main__":
    unittest.main()
