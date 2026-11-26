"""R13 adversarial source-ID and semantic evidence boundaries (synthetic)."""
import pytest

from core.source_monitoring import (
    SourceMonitoringGuard, SourceMonitoringError, SelfCitationError,
    SourceType, VeracityState
)

def test_collision_hypothesis_does_not_overwrite_first():
    g=SourceMonitoringGuard()
    old=g.create_hypothesis("claim A",attribution_id="COLLIDE")
    with pytest.raises(SourceMonitoringError, match="COLLISION"):
        g.create_hypothesis("claim B",attribution_id="COLLIDE")
    assert g.attributions["COLLIDE"]==old
    assert [x.assertion for x in g.attribution_history("COLLIDE")] == ["claim A"]

def test_same_attribution_exact_retry_is_idempotent():
    g=SourceMonitoringGuard()
    old=g.create_hypothesis("claim A",attribution_id="SAME")
    new=g.create_hypothesis("claim A",attribution_id="SAME")
    assert new==old
    assert len(g.attribution_history("SAME"))==1

def test_external_testimony_cannot_overwrite_hypothesis_with_same_id():
    g=SourceMonitoringGuard()
    old=g.create_hypothesis("the conjecture",attribution_id="OVERLAP")
    with pytest.raises(SourceMonitoringError,match="COLLISION"):
        g.create_external_testimony("the conjecture",attribution_id="OVERLAP")
    assert g.attributions["OVERLAP"]==old

def test_distinct_hypothesis_id_is_retained_independently():
    g=SourceMonitoringGuard()
    x=g.create_hypothesis("claim A",attribution_id="ONE")
    y=g.create_hypothesis("claim A",attribution_id="TWO")
    assert x.attribution_id!=y.attribution_id
    assert len(g.attributions)==2

def test_successful_tool_exit_does_not_prove_unrelated_external_witness_claim():
    g=SourceMonitoringGuard()
    x=g.record_empirical_observation(
        assertion="Ario has a real independent external checkpoint witness",
        tool="run_tests",target="toy",exit_code=0,stdout="unit tests passed",
        execution_lock="self-controlled input",attribution_id="UNCHECKED")
    assert x.veracity_state!=VeracityState.VERIFIED_EMPIRICAL
    assert g.filter_working_memory_candidates(["UNCHECKED"],require_verified=True)==[]

def test_even_exact_hashes_do_not_prove_semantically_unrelated_assertion():
    import hashlib
    g=SourceMonitoringGuard()
    out="synthetic tests passed";lock="same actor self-declared"
    x=g.record_empirical_observation(
        assertion="This proves the founder's private key is nonextractable",
        tool="run_tests",target="toy",exit_code=0,stdout=out,execution_lock=lock,
        expected_stdout_sha256=hashlib.sha256(out.encode()).hexdigest(),
        expected_execution_lock_sha256=hashlib.sha256(lock.encode()).hexdigest(),
        attribution_id="FALSE-WARRANT")
    assert x.veracity_state!=VeracityState.VERIFIED_EMPIRICAL

def test_narrow_tool_exit_report_is_allowed_not_arbitrary_witness_truth():
    g=SourceMonitoringGuard()
    x=g.record_empirical_observation(
        assertion="tool_exit:run_tests:synthetic-tests:0",
        tool="run_tests",target="synthetic-tests",exit_code=0,stdout="ok",
        execution_lock="synthetic runner",attribution_id="TOOL-SCOPE")
    assert x.veracity_state==VeracityState.VERIFIED_EMPIRICAL
    assert "TOOL-SCOPE" in [x.attribution_id for x in g.filter_working_memory_candidates(["TOOL-SCOPE"],require_verified=True)]

def test_unsupported_promotion_must_preserve_initial_registry_revision():
    g=SourceMonitoringGuard()
    g.create_hypothesis("claim A", attribution_id="C")
    g.create_hypothesis("claim B", attribution_id="B")
    with pytest.raises(SelfCitationError):
        g.evaluate_claim_promotion("C", ["B"])
    h=g.attribution_history("C")
    assert h[0].veracity_state==VeracityState.UNVERIFIED_HYPOTHESIS
    assert h[-1].veracity_state==VeracityState.UNSUPPORTED
    assert len(h)==2

def test_semantically_unrelated_tool_exit_cannot_promote_fact():
    g=SourceMonitoringGuard()
    g.create_hypothesis("the independent witness is active",attribution_id="CLAIM")
    g.record_empirical_observation(
        assertion="tool_exit:run_tests:tests:0",tool="run_tests",
        target="tests",exit_code=0,stdout="ok",execution_lock="runner",attribution_id="OBS")
    with pytest.raises(SelfCitationError,match="scope|claim|support|evidence|bound"):
        g.evaluate_claim_promotion("CLAIM",["OBS"])
    assert g.attributions["CLAIM"].veracity_state!=VeracityState.VERIFIED_EMPIRICAL

def test_public_registry_views_do_not_allow_nested_metadata_edits():
    g=SourceMonitoringGuard()
    g.record_empirical_observation(
        assertion="tool_exit:run_tests:x:0",tool="run_tests",target="x",
        exit_code=0,stdout="ok",execution_lock="lock",attribution_id="X")
    d=g.attributions
    attr=d["X"]
    attr.provenance.metadata["FORGED"]="yes"
    assert "FORGED" not in g.attributions["X"].provenance.metadata
