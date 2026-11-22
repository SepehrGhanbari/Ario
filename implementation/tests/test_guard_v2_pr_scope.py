"""Guard V2 synthetic regressions based on real R1i shared-SHA PR 14/15/16 evidence."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from research import guard_v2_pr_scope as guard

HEAD = "508a6abfacf534fa01a4b97210c35b35ca965c86"
BASE = "be7c16d964872f88ddb9029f2677c49a7cd745ba"
PR14_ID = 5300854842
PR15_ID = 5431302927
PR16_ID = 5431303336
REPO = 999000
CHECK_ID = 132094820201


def page(*nodes):
    return {"totalCount": len(nodes), "nodes": list(nodes), "hasNextPage": False}


def evidence():
    return {
        "reviews": page({"id": 1, "state": "COMMENTED"}),
        "comments": page({"id": 2, "body": "Original reviewed note"}),
        "threads": page({"id": "T1", "isResolved": True}),
    }


def snapshot(num=14, pr_id=PR14_ID):
    return {"pr": {"repository_id": REPO, "id": pr_id, "number": num,
                   "head_sha": HEAD, "base_sha": BASE, "state": "open",
                   "draft": False}, "evidence": evidence()}


def pin(num=14, pr_id=PR14_ID):
    return {"repository_id": REPO, "pr_id": pr_id, "pr_number": num,
            "head_sha": HEAD, "base_sha": BASE,
            "review_digest": guard.digest(evidence())}


def checks(original_pr=14, original_id=PR14_ID):
    return {"total_count": 1, "hasNextPage": False, "check_runs": [{
        "id": CHECK_ID, "name": guard.CHECK_NAME, "app": {"id": guard.APP_ID},
        "head_sha": HEAD, "status": "completed", "conclusion": "success",
        "external_id": f"R1I-LAB-ONLY:PR{original_pr}:{HEAD}:RUN43484108692",
        "pull_requests": [{"number": original_pr, "id": original_id}],
    }]}


def do(num=14, pr_id=PR14_ID, **mutations):
    first = snapshot(num, pr_id)
    last = copy.deepcopy(first)
    obj = checks()
    pin_obj = pin(num, pr_id)
    for key, fn in mutations.items():
        fn({"first": first, "last": last, "checks": obj, "pin": pin_obj}[key])
    result = guard.assess(pin_obj, first, last, obj)
    assert result["merge_authorized"] is False
    assert result["check_publish_authorized"] is False
    assert result["trust_activated"] is False
    return result


def test_historical_pr14_self_consistent_is_still_reviewable_only():
    out = do()
    assert out["disposition"] == "REVIEWABLE_ONLY"
    assert out["independent_attestation"] == "NOT_ESTABLISHED"


@pytest.mark.parametrize("num,pr_id", [(15, PR15_ID), (16, PR16_ID)])
def test_real_shared_sha_cross_pr_reuse_is_rejected(num, pr_id):
    # GitHub native branch rules returned clean for both despite this PR14-only check.
    out = do(num, pr_id)
    assert out["disposition"] == "HOLD"
    assert out["reason"] == "CHECK_PR_ID_MISMATCH"


def test_pr14_text_in_external_id_is_not_enough_without_native_association():
    out = do(checks=lambda x: x["check_runs"][0]["pull_requests"][0].update(id=PR15_ID))
    assert out["reason"] == "CHECK_PR_ASSOCIATION_MISMATCH"


def test_pr_native_association_alone_is_not_enough_without_external_id():
    out = do(checks=lambda x: x["check_runs"][0].update(external_id=f"R1I-LAB-ONLY:PR15:{HEAD}:RUN43484108692"))
    assert out["reason"] == "CHECK_PR_ID_MISMATCH"


def test_after_check_critical_comment_is_not_accepted_as_old_snapshot():
    def changed(last):
        last["evidence"]["comments"]["nodes"][0]["body"] = "Severity: Critical after check"
    out = do(last=changed)
    assert out["reason"] == "SNAPSHOT_CHANGED_BETWEEN_READS"


def test_if_both_reads_share_new_comment_but_prior_review_pin_is_old_hold():
    def changed(data):
        data["evidence"]["comments"]["nodes"][0]["body"] = "Severity: Critical after check"
    out = do(first=changed, last=changed)
    assert out["reason"] == "STALE_OR_CHANGED_REVIEW_EVIDENCE"


@pytest.mark.parametrize("which", ["id", "number", "repository_id"])
def test_wrong_pr_identity_fails(which):
    out = do(last=lambda x: x["pr"].__setitem__(which, 999123))
    assert out["reason"] == "PR_IDENTITY_MISMATCH"


@pytest.mark.parametrize("field", ["head_sha", "base_sha"])
def test_stale_revision_fails(field):
    out = do(last=lambda x: x["pr"].__setitem__(field, "a" * 40))
    assert out["reason"] == "STALE_PR_REVISION"


def test_draft_cannot_be_reviewable():
    out = do(last=lambda x: x["pr"].update(draft=True))
    assert out["reason"] == "PR_NOT_READY"


def test_incomplete_review_collection_fails_closed():
    out = do(first=lambda x: x["evidence"]["comments"].update(hasNextPage=True))
    assert out["reason"] == "INCOMPLETE_COMMENTS"


def test_unresolved_thread_fails_closed():
    out = do(last=lambda x: x["evidence"]["threads"]["nodes"][0].update(isResolved=False))
    assert out["reason"] == "UNRESOLVED_THREAD"


def test_missing_app_check_fails():
    out = do(checks=lambda x: x["check_runs"][0]["app"].update(id=15368))
    assert out["reason"] == "MISSING_OR_AMBIGUOUS_APP_CHECK"


@pytest.mark.parametrize("malformed_id", [float(guard.APP_ID), True, str(guard.APP_ID)])
def test_app_id_requires_exact_json_integer(malformed_id):
    out = do(checks=lambda x: x["check_runs"][0]["app"].update(id=malformed_id))
    assert out["reason"] == "MISSING_OR_AMBIGUOUS_APP_CHECK"


@pytest.mark.parametrize("conclusion", ["skipped", "neutral", "failure", "cancelled", None])
def test_non_success_check_fails(conclusion):
    out = do(checks=lambda x: x["check_runs"][0].update(conclusion=conclusion))
    assert out["reason"] == "APP_CHECK_NOT_SUCCESS"


def test_missing_external_id_fails():
    out = do(checks=lambda x: x["check_runs"][0].pop("external_id"))
    assert out["reason"] == "CHECK_PR_ID_MISMATCH"


def test_check_pagination_fails():
    out = do(checks=lambda x: x.update(hasNextPage=True))
    assert out["reason"] == "INCOMPLETE_CHECK_CAPTURE"


def test_duplicated_native_check_id_fails():
    def dup(x):
        x["check_runs"].append(copy.deepcopy(x["check_runs"][0]))
        x["total_count"] = 2
    out = do(checks=dup)
    assert out["reason"] == "INVALID_CHECK_IDS"


def test_ambiguous_check_association_fails():
    out = do(checks=lambda x: x["check_runs"][0]["pull_requests"].append(
        {"number": 15, "id": PR15_ID}))
    assert out["reason"] == "CHECK_PR_ASSOCIATION_MISMATCH"


@pytest.mark.parametrize("bad", [b'{"a":1,"a":1}', b'{"a":NaN}', b'\xff'])
def test_strict_json_denies_bad_bytes(bad):
    with pytest.raises(guard.EvidenceError):
        guard.strict_json(bad)


def test_bool_ids_are_not_integers():
    out = do(last=lambda x: x["pr"].update(id=True))
    assert out["reason"] == "PR_IDENTITY_MISMATCH"


def test_self_audit_green_report_does_not_authorize_merge():
    r = guard.assess(pin(), snapshot(), snapshot(), checks(),
                     self_audit={"status": "UNKNOWN", "merge_authorized": False,
                                 "required_check_observation": "REPORTED_SUCCESS_BY_LINKED_PR_RUN"})
    assert r["disposition"] == "REVIEWABLE_ONLY" and r["merge_authorized"] is False


def test_self_audit_claiming_merge_authorization_is_denied():
    r = guard.assess(pin(), snapshot(), snapshot(), checks(),
                     self_audit={"status": "MATCH", "merge_authorized": True})
    assert r["disposition"] == "HOLD" and r["reason"] == "SELF_AUDIT_NOT_NONAUTHORITATIVE"


def test_cli_returns_nonzero_even_for_valid_research_positive(tmp_path):
    for name, obj in (("pin", pin()), ("first", snapshot()),
                      ("last", snapshot()), ("checks", checks())):
        (tmp_path / (name + ".json")).write_text(json.dumps(obj), encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / "research" / "guard_v2_pr_scope.py"
    cmd = [sys.executable, str(script), *(str(tmp_path / (name + ".json")) for name in
                                            ("pin", "first", "last", "checks"))]
    run = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert run.returncode == 1
    report = json.loads(run.stdout)
    assert report["disposition"] == "REVIEWABLE_ONLY"
    assert report["merge_authorized"] is False
