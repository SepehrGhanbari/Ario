"""R17 research-only probes against #295 head bfb2411 (manual report validator)."""
import json
import pytest
from research.guard_v2_manual_report import main
from research import guard_v2_trusted_manual as reader

HEAD, SRC, N = "a" * 40, "b" * 40, 295

def complete():
    r = reader._hold("PR_DRAFT_READ_ONLY_HOLD")
    r.update({"source_commit_sha": SRC, "review_graph_sample": "SAMPLED_STABLE_UNATTESTED",
              "review_graph_reason": "TWO_COMPLETE_GRAPH_SAMPLES_MATCH", "review_freshness": "TWO_SAMPLED_GRAPHS_MATCH_NON_ATOMIC",
              "first_digest": "c" * 64, "second_digest": "c" * 64,
              "live_identity": {"repository_id": 1, "pr_id": 2, "pr_number": N, "head_sha": HEAD, "base_sha": "d" * 40}})
    return r

def rc(tmp_path, obj=None, raw=None, number=str(N), exit_code="0"):
    p = tmp_path / "r.json"
    p.write_bytes(raw if raw is not None else (json.dumps(obj, sort_keys=True, ensure_ascii=True) + "\n").encode())
    return main([str(p), number, HEAD, SRC, exit_code])

@pytest.mark.parametrize("extra", [
    {"guard_decision": "PASS"}, {"merge_ready": True}, {"approved_by": "founder"},
    {"merge_auth\u043erized": True},          # Cyrillic o look-alike, emitted escaped
])
def test_unexpected_top_level_keys_rejected(tmp_path, extra):
    assert rc(tmp_path, {**complete(), **extra}) == 2

def test_raw_non_ascii_lookalike_key_rejected(tmp_path):
    raw = json.dumps({**complete(), "merge_authorіzed": True}, ensure_ascii=False).encode()
    assert rc(tmp_path, raw=raw) == 2

def test_nested_identity_extra_key_rejected(tmp_path):
    r = complete(); r["live_identity"]["merge_authorized"] = True
    assert rc(tmp_path, r) == 2

@pytest.mark.parametrize("number", ["2_95", " 295", "+295"])
def test_non_canonical_pr_number_rejected(tmp_path, number):
    assert rc(tmp_path, complete(), number=number) == 2

# ---- positive baselines: exactly what the real reader emits ----
def test_complete_reader_shaped_report_accepted(tmp_path):
    assert rc(tmp_path, complete()) == 0

def test_reader_error_hold_with_error_type_accepted_on_nonzero_exit(tmp_path):
    r = reader._hold("TRUSTED_OBSERVER_INITIALIZATION_FAILED", error_type="OSError")
    assert rc(tmp_path, r, exit_code="2") == 0

def test_reader_partial_hold_with_null_digests_accepted_on_nonzero_exit(tmp_path):
    r = reader._hold("GRAPH_UNKNOWN"); r.update({"source_commit_sha": SRC, "review_graph_sample": "UNKNOWN",
        "review_graph_reason": "UNKNOWN", "first_digest": None, "second_digest": None})
    assert rc(tmp_path, r, exit_code="2") == 0
