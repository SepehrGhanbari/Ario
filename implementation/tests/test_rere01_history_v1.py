"""RERE v0.4: persistence, dependency invalidation and refusal tests."""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from research.rere01.revision_comparator_v0_2 import LabContractError, project
from research.rere01.assessment_history_v1 import encode_history, restore_history, append_history
from tests.test_rere01_v03_guard import _fixture


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pack(d):
    return json.dumps(d, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")


def test_every_assessment_depending_on_revoked_c_is_challenged():
    policy, rows, _ = _fixture()
    a,b,c,t3,cal,t4,again = rows
    second = replace(again, seq=5)
    result = project((a,b,c,t3,second,replace(cal,seq=6),replace(t4,seq=7)),policy)
    assert result.event_outcome == "UNKNOWN"
    assert dict(result.assessment_reliability)["LAB-T3"] == "CHALLENGED_BY_LATER_CALIBRATION"
    assert dict(result.assessment_reliability)["LAB-T3-AGAIN"] == "CHALLENGED_BY_LATER_CALIBRATION"


def test_relabeled_equivalent_observation_is_not_independent_basis():
    policy, rows, _ = _fixture()
    a,b,c,t3,cal,t4,again = rows
    other = replace(c, seq=5,record_id="LAB-C-OTHER")
    ref = replace(again.assessment.admissible_evidence_refs[0],reference_id=other.record_id)
    second = replace(again,seq=6,assessment=replace(again.assessment,admissible_evidence_refs=(ref,)))
    result = project((a,b,c,t3,other,second,replace(cal,seq=7),replace(t4,seq=8)),policy)
    assert result.event_outcome == "UNKNOWN"
    assert dict(result.assessment_reliability)["LAB-T3"] == "CHALLENGED_BY_LATER_CALIBRATION"
    assert dict(result.assessment_reliability)["LAB-T3-AGAIN"] == "CHALLENGED_BY_LATER_CALIBRATION"
    assert not result.evidence_authorized_for_real_memory


def test_t4_targets_exact_prior_assessment_and_preserves_history():
    policy,rows,_ = _fixture()
    prior = encode_history(rows[:4],policy)
    after = append_history(prior,expected_sha256=sha(prior),additions=rows[4:6])
    result = restore_history(after,expected_sha256=sha(after))
    assert result.projection.event_outcome == "UNKNOWN"
    assert result.as_of(4).event_outcome == "CONDITIONALLY_REFUTED_IN_LAB"
    assert result.records[:4] == rows[:4]
    assert json.loads(prior)["rows"] == json.loads(after)["rows"][:4]
    links = json.loads(after)["rows"][5]["links"]
    assert links[0]["role"] == "PRIOR_ASSESSMENT"
    assert links[0]["record_id"] == "LAB-T3"
    assert links[0]["record_sha256"] == sha(pack(json.loads(prior)["rows"][3]))
    assert not result.projection.evidence_authorized_for_real_memory


def test_recovery_in_fresh_process_keeps_t4_and_historical_t3(tmp_path):
    policy,rows,_ = _fixture()
    data = encode_history(rows,policy)
    p = tmp_path / "history.json"
    p.write_bytes(data)
    root = Path(__file__).resolve().parents[1]
    code = (
        "from pathlib import Path; import sys; "
        "from research.rere01.assessment_history_v1 import restore_history; "
        "r=restore_history(Path(sys.argv[1]).read_bytes(), expected_sha256=sys.argv[2]); "
        "assert r.projection.event_outcome=='UNKNOWN'; "
        "assert r.as_of(4).event_outcome=='CONDITIONALLY_REFUTED_IN_LAB'; "
        "assert not r.projection.evidence_authorized_for_real_memory"
    )
    subprocess.run([sys.executable,"-c",code,str(p),sha(data)],cwd=root,check=True)
    assert p.read_bytes() == data


@pytest.mark.parametrize("change",["drop_tail","alter_prior","replace_link","alter_policy","reorder","extra_field","duplicate_row","wrong_parent"])
def test_history_tamper_with_original_pin_rejected(change):
    policy,rows,_ = _fixture()
    raw = encode_history(rows[:6],policy)
    d = json.loads(raw)
    if change == "drop_tail": d["rows"].pop()
    elif change == "alter_prior": d["rows"][3]["record"]["payload"]["reason_code"]="changed"
    elif change == "replace_link": d["rows"][5]["links"][0]["record_sha256"]="f"*64
    elif change == "alter_policy": d["policy"]["event_time"]="different"
    elif change == "reorder": d["rows"][0],d["rows"][1]=d["rows"][1],d["rows"][0]
    elif change == "extra_field": d["truth"]=True
    elif change == "duplicate_row": d["rows"].append(d["rows"][0])
    else: d["rows"][3]["previous_sha256"]="f"*64
    with pytest.raises(LabContractError,match="digest mismatch"):
        restore_history(pack(d),expected_sha256=sha(raw))


@pytest.mark.parametrize("change",["replace_link","reorder","extra_field","duplicate_row","wrong_parent","wrong_kind"])
def test_self_rehashed_structural_corruption_is_still_refused(change):
    policy,rows,_ = _fixture()
    d=json.loads(encode_history(rows[:6],policy))
    if change=="replace_link": d["rows"][5]["links"][0]["record_sha256"]="f"*64
    elif change=="reorder": d["rows"][0],d["rows"][1]=d["rows"][1],d["rows"][0]
    elif change=="extra_field": d["truth"]=True
    elif change=="duplicate_row": d["rows"].append(d["rows"][0])
    elif change=="wrong_kind": d["rows"][5]["record"]["payload"]["assessment"]["target"]["subject_reference"]["reference_id"]="LAB-C"
    else: d["rows"][3]["previous_sha256"]="f"*64
    raw=pack(d)
    with pytest.raises(LabContractError):
        restore_history(raw,expected_sha256=sha(raw))


def test_exact_replay_and_permutation_are_idempotent():
    policy,rows,_ = _fixture()
    raw=encode_history(rows,policy)
    assert encode_history(tuple(reversed(rows)),policy)==raw
    assert append_history(raw,expected_sha256=sha(raw),additions=(rows[0],))==raw
    with pytest.raises(LabContractError):
        append_history(raw,expected_sha256=sha(raw),additions=(replace(rows[0],reported_value="CLOSED"),))


@pytest.mark.parametrize("count",[-1,True,8])
def test_invalid_as_of_cutoff(count):
    policy,rows,_ = _fixture()
    raw=encode_history(rows,policy)
    with pytest.raises(LabContractError):
        restore_history(raw,expected_sha256=sha(raw)).as_of(count)


def test_wrong_kind_and_missing_predecessor_cannot_be_serialized():
    policy,rows,_ = _fixture()
    a,b,c,t3,cal,t4,_ = rows
    bad_target=replace(t4.assessment.target,subject_reference=replace(t4.assessment.target.subject_reference,reference_id="LAB-C"))
    bad=replace(t4,assessment=replace(t4.assessment,target=bad_target))
    with pytest.raises(LabContractError):
        encode_history((a,b,c,t3,cal,bad),policy)
    with pytest.raises(LabContractError):
        encode_history((a,b,c,replace(cal,seq=4),replace(t4,seq=5)),policy)


def test_caller_supplied_old_pin_does_not_establish_freshness():
    policy,rows,_ = _fixture()
    old=encode_history(rows[:4],policy)
    latest=encode_history(rows[:6],policy)
    with pytest.raises(LabContractError):
        restore_history(old,expected_sha256=sha(latest))
    # Expected limitation, not a safety success: the caller controls the pin.
    assert restore_history(old,expected_sha256=sha(old)).projection.event_outcome=="CONDITIONALLY_REFUTED_IN_LAB"


@pytest.mark.parametrize("receipt",["", "f"*64, "new asserted signature"])
def test_alias_created_after_calibration_cannot_resurrect(receipt):
    policy,rows,_ = _fixture()
    a,b,c,t3,cal,t4,again = rows
    other = replace(c,seq=7,record_id="LAB-C-ALIAS",declared_receipt=receipt)
    ref = replace(again.assessment.admissible_evidence_refs[0],reference_id=other.record_id)
    second=replace(again,seq=8,assessment=replace(again.assessment,admissible_evidence_refs=(ref,)))
    initial=encode_history(rows[:6],policy)
    after=append_history(initial,expected_sha256=sha(initial),additions=(other,second))
    result=restore_history(after,expected_sha256=sha(after)).projection
    assert result.event_outcome=="UNKNOWN"
    assert dict(result.assessment_reliability)["LAB-T3-AGAIN"]=="NOT_WARRANTED"


def test_duplicate_json_key_with_self_pin_is_rejected():
    policy,rows,_ = _fixture()
    raw=encode_history(rows,policy)
    bad=raw.replace(b'"format":',b'"format":"forged","format":',1)
    with pytest.raises(LabContractError):
        restore_history(bad,expected_sha256=sha(bad))


@pytest.mark.parametrize("seq",[True,0,65,"1"])
def test_noncanonical_sequence_refused(seq):
    policy,rows,_ = _fixture()
    with pytest.raises(LabContractError):
        encode_history((replace(rows[0],seq=seq),),policy)


def test_full_distinct_record_budget_accepts_exact_replay_not_new_record():
    policy,rows,_ = _fixture()
    history=tuple(replace(rows[0],seq=i,record_id=f"UNVERIFIED-{i}") for i in range(1,65))
    raw=encode_history(history,policy)
    assert append_history(raw,expected_sha256=sha(raw),additions=(history[-1],))==raw
    with pytest.raises(LabContractError):
        append_history(raw,expected_sha256=sha(raw),additions=(replace(history[-1],record_id="new"),))
