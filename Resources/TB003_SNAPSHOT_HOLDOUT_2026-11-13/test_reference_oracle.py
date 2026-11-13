"""Hard-coded PUBLIC reference controls; not blinded or confirmatory."""
import json
from pathlib import Path
from reference_oracle import adjudicate

directory = Path(__file__).resolve().parent
data = json.loads((directory / "public_controls.json").read_text(encoding="utf-8"))
cases = data["cases"]
expected = {
    "D01_clean": ("MATCH","LAB_CONDITIONALLY_SEPARATE","LAB_CONDITIONALLY_DISTINCT"),
    "D02_departure_mismatch": ("MISMATCH","UNKNOWN","UNKNOWN"),
    "D03_departure_compromised_offpath": ("MISMATCH","UNKNOWN","UNKNOWN"),
    "D04_valid_to_P3": ("MATCH","LAB_CONDITIONALLY_SEPARATE","LAB_CONDITIONALLY_DISTINCT"),
    "D05_to_P3_compromised": ("MATCH","COMPROMISED_BY_SCENARIO","LAB_CONDITIONALLY_DISTINCT"),
    "D06_forward_past_declared_P3": ("MISMATCH","UNKNOWN","UNKNOWN"),
    "D07_forward_P4_compromised": ("MATCH","COMPROMISED_BY_SCENARIO","LAB_CONDITIONALLY_DISTINCT"),
    "D08_missing_required_transfer": ("MISMATCH","UNKNOWN","UNKNOWN"),
    "D09_disconnected_second_transfer": ("UNKNOWN","UNKNOWN","UNKNOWN"),
    "D10_ambiguous_same_time": ("UNKNOWN","UNKNOWN","UNKNOWN"),
    "D11_self_declared_transfer": ("UNKNOWN","UNKNOWN","UNKNOWN"),
    "D12_common_control": ("MATCH","COMMON_CONTROL_DETECTED","LAB_CONDITIONALLY_DISTINCT"),
    "D13_common_source": ("MATCH","LAB_CONDITIONALLY_SEPARATE","COMMON_SOURCE_DETECTED"),
    "D14_shared_storage": ("MATCH","COMMON_CONTROL_DETECTED","LAB_CONDITIONALLY_DISTINCT"),
    "D15_incomplete_control": ("MATCH","UNKNOWN","LAB_CONDITIONALLY_DISTINCT"),
    "D16_incomplete_transfer": ("UNKNOWN","UNKNOWN","UNKNOWN"),
    "D17_after_snapshot": ("MATCH","LAB_CONDITIONALLY_SEPARATE","LAB_CONDITIONALLY_DISTINCT"),
    "D18_compromised_second_witness": ("MATCH","COMPROMISED_BY_SCENARIO","LAB_CONDITIONALLY_DISTINCT"),
}
assert len(cases) == len(expected) == 18
assert data["kind"] == "PUBLIC_DEVELOPMENT_ONLY"
for item in cases:
    result = adjudicate(item)
    observed = (result["holder_status"], result["chain_independence"], result["source_independence"])
    assert observed == expected[item["case_id"]], (item["case_id"], observed, expected[item["case_id"]])
    assert not any(k in item for k in ("holder_status","chain_independence","source_independence","expected","label","correct"))
print("PUBLIC_REFERENCE_CONTROLS_PASS",len(cases),"open non-blind cases")
