"""R19 research-only probes against #295 head 7577b7c: allowed keys must not carry
untyped values. Positive baselines feed REAL reader output into the validator."""
import copy
import json

import pytest

from research.guard_v2_manual_report import main
from research import guard_v2_trusted_manual as reader
from test_guard_v2_trusted_manual import FakeRest, SOURCE_SHA
from test_guard_v2_review_graph import FakeGraphQL, HEAD, original

N = 295


def success():
    return reader.observe(N, HEAD, rest_reader=FakeRest(), graph_reader=FakeGraphQL(),
                          source_sha=SOURCE_SHA)


def error_hold():
    g = FakeGraphQL(); g.fail_on_call = 2
    return reader.observe(N, HEAD, rest_reader=FakeRest(), graph_reader=g, source_sha=SOURCE_SHA)


def reader_exit(result):
    # Same completion rule as research.guard_v2_trusted_manual.main.
    done = (result.get("review_graph_sample") == "SAMPLED_STABLE_UNATTESTED"
            and isinstance(result.get("live_identity"), dict)
            and result.get("first_digest") == result.get("second_digest")
            and isinstance(result.get("first_digest"), str))
    return 0 if done else 2


def rc(tmp_path, obj, exit_code):
    p = tmp_path / "report.json"
    p.write_text(json.dumps(obj, sort_keys=True, ensure_ascii=True) + "\n")
    return main([str(p), str(N), HEAD, SOURCE_SHA, str(exit_code)])


# ---- RED at 7577b7c: allowed key, untyped or unbound value ----
@pytest.mark.parametrize("patch", [
    {"review_graph_reason": {"merge_authorized": True}},
    {"review_graph_reason": "APPROVED_BY_FOUNDER"},
    {"error_type": ["MERGE_OK"]},
])
def test_success_values_of_allowed_keys_are_exact(tmp_path, patch):
    assert rc(tmp_path, {**success(), **patch}, 0) == 2


@pytest.mark.parametrize("patch", [
    {"review_graph_sample": {"trust_activated": True}},
    {"first_digest": 12345, "second_digest": []},
    {"source_commit_sha": "f" * 40},
    {"reason": "OK\u202e\u0000"},
])
def test_error_hold_optional_fields_are_typed(tmp_path, patch):
    assert rc(tmp_path, {**error_hold(), **patch}, 2) == 2


def test_error_hold_live_identity_must_still_bind_requested_pr(tmp_path):
    r = success()
    r["live_identity"] = {**r["live_identity"], "pr_number": 306, "head_sha": "e" * 40}
    assert rc(tmp_path, r, 2) == 2


# ---- positive baselines: unmodified real reader output ----
def test_real_reader_success_validates(tmp_path):
    r = success()
    assert reader_exit(r) == 0 and rc(tmp_path, r, 0) == 0


@pytest.mark.parametrize("mutate", ["graph_403", "graph_errors", "pr_changed", "head_mismatch",
                                    "wrong_repo", "base_not_main", "samples_differ"])
def test_real_reader_error_holds_validate_on_nonzero_exit(tmp_path, mutate):
    rest, graph, head = FakeRest(), FakeGraphQL(), HEAD
    if mutate == "graph_403":
        graph.fail_on_call = 2
    elif mutate == "graph_errors":
        graph.graph_errors = True
    elif mutate == "pr_changed":
        rest.after = copy.deepcopy(rest.pr); rest.after["body"] += "\nnew"
    elif mutate == "head_mismatch":
        head = "d" * 40
    elif mutate == "wrong_repo":
        rest.pr["base"]["repo"]["id"] += 1
    elif mutate == "base_not_main":
        rest.pr["base"]["ref"] = "development"
    elif mutate == "samples_differ":
        b = original(); b["comments"].clear(); graph = FakeGraphQL(original(), b)
    r = reader.observe(N, head, rest_reader=rest, graph_reader=graph, source_sha=SOURCE_SHA)
    assert reader_exit(r) == 2
    p = tmp_path / "report.json"; p.write_text(json.dumps(r, sort_keys=True, ensure_ascii=True))
    assert main([str(p), str(N), head, SOURCE_SHA, "2"]) == 0, r


def test_real_reader_init_failure_hold_validates(tmp_path):
    assert rc(tmp_path, reader._hold("TRUSTED_OBSERVER_INITIALIZATION_FAILED", error_type="OSError"), 2) == 0
