"""Hard-coded PUBLIC reference controls; not blinded or confirmatory."""
import json
from pathlib import Path
from reference_oracle import adjudicate

directory = Path(__file__).resolve().parent
data = json.loads((directory / "public_controls.json").read_text(encoding="utf-8"))
cases = data["cases"]
expected = {
    "D01_clean": ("MATCH","LAB_CONDITIONALLY_SEPARATE","LAB_CONDITIONALLY_DISTINCT"),
    "D02_departure_mismatch": ("MISMATCH","UNKNOWN","LAB_CONDITIONALLY_DISTINCT"),
    "D03_departure_compromised_offpath": ("MISMATCH","UNKNOWN","LAB_CONDITIONALLY_DISTINCT"),
    "D04_valid_to_P3": ("MATCH","LAB_CONDITIONALLY_SEPARATE","LAB_CONDITIONALLY_DISTINCT"),
    "D05_to_P3_compromised": ("MATCH","COMPROMISED_BY_SCENARIO","LAB_CONDITIONALLY_DISTINCT"),
    "D06_forward_past_declared_P3": ("MISMATCH","UNKNOWN","LAB_CONDITIONALLY_DISTINCT"),
    "D07_forward_P4_compromised": ("MATCH","COMPROMISED_BY_SCENARIO","LAB_CONDITIONALLY_DISTINCT"),
    "D08_missing_required_transfer": ("MISMATCH","UNKNOWN","LAB_CONDITIONALLY_DISTINCT"),
    "D09_disconnected_second_transfer": ("UNKNOWN","UNKNOWN","LAB_CONDITIONALLY_DISTINCT"),
    "D10_ambiguous_same_time": ("UNKNOWN","UNKNOWN","LAB_CONDITIONALLY_DISTINCT"),
    "D11_self_declared_transfer": ("UNKNOWN","UNKNOWN","LAB_CONDITIONALLY_DISTINCT"),
    "D12_common_control": ("MATCH","COMMON_CONTROL_DETECTED","LAB_CONDITIONALLY_DISTINCT"),
    "D13_common_source": ("MATCH","LAB_CONDITIONALLY_SEPARATE","COMMON_SOURCE_DETECTED"),
    "D14_shared_storage": ("MATCH","COMMON_CONTROL_DETECTED","LAB_CONDITIONALLY_DISTINCT"),
    "D15_incomplete_control": ("MATCH","UNKNOWN","LAB_CONDITIONALLY_DISTINCT"),
    "D16_incomplete_transfer": ("UNKNOWN","UNKNOWN","LAB_CONDITIONALLY_DISTINCT"),
    "D17_after_snapshot": ("MATCH","LAB_CONDITIONALLY_SEPARATE","LAB_CONDITIONALLY_DISTINCT"),
    "D18_compromised_second_witness": ("MATCH","COMPROMISED_BY_SCENARIO","LAB_CONDITIONALLY_DISTINCT"),
}
assert len(cases) == len(expected) == 18
assert {x["case_id"] for x in cases} == set(expected)
assert data["kind"] == "PUBLIC_DEVELOPMENT_ONLY"
for item in cases:
    result = adjudicate(item)
    observed = (result["holder_status"], result["chain_independence"], result["source_independence"])
    assert observed == expected[item["case_id"]], (item["case_id"], observed, expected[item["case_id"]])
    assert not any(k in item for k in ("holder_status","chain_independence","source_independence","expected","label","correct"))
# Extra metamorphic controls (not hidden or confirmatory).
from copy import deepcopy
example = deepcopy(next(x for x in cases if x["case_id"] == "D16_incomplete_transfer"))
example["common_source"] = True
assert adjudicate(example)["source_independence"] == "COMMON_SOURCE_DETECTED"
example = deepcopy(next(x for x in cases if x["case_id"] == "D01_clean"))
example["other_witness_custodians"] = ["P1"]
try:
    adjudicate(example)
except ValueError as exc:
    assert "UNSUPPORTED_WITNESS_B_CONFIGURATION" in str(exc)
else:
    raise AssertionError("Reference oracle silently accepted different witness B facts")

print("PUBLIC_REFERENCE_CONTROLS_PASS",len(cases),"open non-blind cases")


# Adversarial OPEN development controls for PR #199's *input adapter*, not
# confirmatory benchmark results. Historical public 18 assertions remain above.
import copy
import tempfile
import unittest
from unittest import mock
from blind_runner import parse_unlabeled_dataset, validate_case, run as run_blind


def _runner_fixture():
    return copy.deepcopy(next(x for x in cases if x["case_id"] == "D01_clean"))


class BlindRunnerValueSchemaTests(unittest.TestCase):
    def test_valid_clean_and_transfer(self):
        clean = _runner_fixture()
        validate_case(clean)
        transferred = copy.deepcopy(clean)
        transferred["case_id"] = "DEV_TRANSFER"
        transferred["declared_holder"] = "P3"
        transferred["transfers"] = [
            {"from": "P1", "to": "P3", "origin": "LAB", "sequence": 2}
        ]
        validate_case(transferred)
        encoded = json.dumps({
            "schema": "ARIO-TB003-SNAPSHOT-CHALLENGE-0.1",
            "kind": "PUBLIC_DEVELOPMENT_ONLY",
            "cases": [clean, transferred]
        }).encode("utf-8")
        self.assertEqual(len(parse_unlabeled_dataset(encoded)["cases"]), 2)

    def test_reject_malformed_values_before_evaluator(self):
        mutations = [
            ("nested_gold", {"common_control": {"gold": False}}),
            ("false_string", {"common_control": "false"}),
            ("zero_integer_not_bool", {"common_control": 0}),
            ("null_not_bool", {"common_control": None}),
            ("source_string", {"common_source": "false"}),
            ("shared_storage_dict", {"shared_storage": {"expected": False}}),
            ("complete_flag_string", {"complete_transfer_surface": "true"}),
            ("snapshot_bool", {"snapshot_sequence": True}),
            ("negative_snapshot", {"snapshot_sequence": -2}),
            ("overflow_snapshot", {"snapshot_sequence": 1000001}),
            ("float_snapshot", {"snapshot_sequence": 1.0}),
            ("capture_bool_sequence", {"capture": {"sequence": False, "custodian": "P1"}}),
            ("capture_reserved_actor", {"capture": {"sequence": 0, "custodian": "B"}}),
            ("artifact_collision", {"declared_holder": "A"}),
            ("capture_collision", {"declared_holder": "CAPA"}),
            ("reserved_transfer_actor", {"transfers": [
                {"from": "SA", "to": "P3", "origin": "LAB", "sequence": 2}
            ]}),
            ("origin_not_enum", {"transfers": [
                {"from": "P1", "to": "P3", "origin": "GOLD", "sequence": 2}
            ]}),
            ("transfer_gold_key", {"transfers": [
                {"from": "P1", "to": "P3", "origin": "LAB", "sequence": 2, "gold": True}
            ]}),
            ("nonfixed_B", {"other_witness_custodians": ["P3"]}),
            ("nested_B_label", {"other_witness_custodians": [{"gold": False}]}),
            ("duplicate_compromised", {"compromised_custodians": ["P4", "P4"]}),
            ("invalid_identifier", {"declared_holder": "P3\nLEAK"}),
        ]
        for name, updates in mutations:
            with self.subTest(case=name):
                row = _runner_fixture()
                row["case_id"] = "TEST_" + name
                row.update(copy.deepcopy(updates))
                with self.assertRaises(ValueError):
                    validate_case(row)

    def test_accept_240_reject_241_and_duplicate_case_ids(self):
        cases240 = [dict(_runner_fixture(), case_id=f"LIMIT_{i:03}") for i in range(240)]
        data = {"schema": "ARIO-TB003-SNAPSHOT-CHALLENGE-0.1", "cases": cases240}
        self.assertEqual(len(parse_unlabeled_dataset(json.dumps(data).encode())["cases"]), 240)
        cases240.append(dict(_runner_fixture(), case_id="LIMIT_240"))
        with self.assertRaisesRegex(ValueError, "INVALID_CASE_IDS_OR_COUNT"):
            parse_unlabeled_dataset(json.dumps(data).encode())
        data["cases"] = [dict(_runner_fixture(), case_id="DUP")] * 2
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CASE_ID"):
            parse_unlabeled_dataset(json.dumps(data).encode())

    def test_reject_duplicate_json_keys_and_embedded_gold(self):
        raw = b'{"schema":"ARIO-TB003-SNAPSHOT-CHALLENGE-0.1","cases":[],"cases":[]}'
        with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_KEY"):
            parse_unlabeled_dataset(raw)
        row = _runner_fixture()
        row["gold"] = "do not disclose"
        with self.assertRaises(ValueError):
            parse_unlabeled_dataset(json.dumps({
                "schema": "ARIO-TB003-SNAPSHOT-CHALLENGE-0.1", "cases": [row]
            }).encode("utf-8"))
        root = {"schema": "ARIO-TB003-SNAPSHOT-CHALLENGE-0.1",
                "cases": [_runner_fixture()], "gold": False}
        with self.assertRaisesRegex(ValueError, "DATASET_UNEXPECTED_OR_GOLD_FIELDS"):
            parse_unlabeled_dataset(json.dumps(root).encode("utf-8"))

    def test_runner_rejects_before_loading_pinned_evaluator(self):
        row = _runner_fixture()
        row["common_control"] = {"gold": False}
        dataset = {"schema": "ARIO-TB003-SNAPSHOT-CHALLENGE-0.1", "cases": [row]}
        with tempfile.TemporaryDirectory(prefix="ario-pr199-value-check-") as directory:
            target = Path(directory) / "malformed.json"
            target.write_text(json.dumps(dataset), encoding="utf-8")
            with mock.patch("blind_runner.load_pinned", side_effect=AssertionError("unsafe_eval_called")):
                with self.assertRaisesRegex(ValueError, "FLAG_NOT_BOOLEAN"):
                    run_blind(target)


if __name__ == "__main__":
    unittest.main(verbosity=2)
