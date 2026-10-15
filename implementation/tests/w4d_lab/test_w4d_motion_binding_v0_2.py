"""W4-D synthetic typed motion/ballot binding regression, never live signatures."""
from dataclasses import replace
import pytest

import w4d_governance_lab as lab
from test_w4d_governance_lab import council, appeal, assert_non_authority

SUPPORT_STEPS = {
    "LAB_FREEZE_RECOMMENDATION",
    "LAB_RECOVERY_REVIEW_RECOMMENDATION",
    "LAB_PROCEDURAL_REVIEW_RECOMMENDATION",
}


def test_nominal_bound_motion_gets_only_mock_procedural_recommendation():
    fixture = council()
    assert fixture.motion.digest == lab.mock_motion_digest(fixture.motion)
    assert lab.evaluate_council(fixture).lab_step == "LAB_PROCEDURAL_REVIEW_RECOMMENDATION"
    assert_non_authority(lab.evaluate_council(fixture))


@pytest.mark.parametrize("field,value", [
    ("motion_id", "AnotherMotion"),
    ("action", "REVOKE_REVIEW_GRANT"),
    ("candidate_scope", "AnotherClaim"),
    ("epoch", 8),
    ("proposer_control_group", "AnotherProposer"),
    ("source_control_group", "AnotherSource"),
    ("audience", "AnotherAudience"),
    ("nonce", "AnotherNonce"),
    ("valid_from_tick", 6),
    ("valid_until_tick", 16),
])
def test_any_modified_typed_motion_field_mismatches_supplied_digest(field, value):
    original = council()
    changed = replace(original, motion=replace(original.motion, **{field: value}))
    result = lab.evaluate_council(changed)
    assert result.lab_step not in SUPPORT_STEPS
    assert result.rule in {"W4D_MOTION_DIGEST_NOT_BOUND", "W4D_STALE_OR_REPLAYED_EPOCH"}
    assert_non_authority(result)


@pytest.mark.parametrize("field,value", [
    ("motion_id", "AnotherMotion"),
    ("action", "REVOKE_REVIEW_GRANT"),
    ("candidate_scope", "AnotherClaim"),
    ("proposer_control_group", "AnotherProposer"),
    ("source_control_group", "AnotherSource"),
    ("audience", "AnotherAudience"),
    ("nonce", "AnotherNonce"),
    ("valid_from_tick", 6),
    ("valid_until_tick", 16),
])
def test_recomputed_motion_digest_still_rejects_old_ballots(field, value):
    original = council()
    mutated = replace(original.motion, **{field: value})
    forged_fixture = replace(original, motion=replace(mutated, digest=lab.mock_motion_digest(mutated)))
    result = lab.evaluate_council(forged_fixture)
    assert result.rule == "W4D_VOTE_SCOPE_OR_EPOCH_REPLAY"
    assert result.lab_step == "HOLD" or result.status == "REJECTED"
    assert_non_authority(result)


@pytest.mark.parametrize("field,value", [
    ("audience", "Ario/W4D"),
    ("nonce", ""),
    ("valid_from_tick", True),
    ("valid_until_tick", 2**200),
    ("valid_from_tick", 16),
    ("valid_until_tick", 4),
    ("nonce", []),
    ("audience", None),
    ("policy_version", "W4D-LAB-0.1"),
])
def test_malformed_or_legacy_motion_profile_fails_closed(field, value):
    c = council()
    result = lab.evaluate_council(replace(c, motion=replace(c.motion, **{field: value})))
    assert result.rule == "W4D_MOTION_SHAPE_OR_FORBIDDEN_ACTION"
    assert_non_authority(result)


@pytest.mark.parametrize("now", [4, 16])
def test_declared_validity_window_enforced_with_bounded_clock(now):
    c = council()
    result = lab.evaluate_council(replace(c, observed_tick=now))
    assert result.rule == "W4D_MOTION_OUTSIDE_DECLARED_VALIDITY"
    assert result.lab_step == "HOLD"
    assert_non_authority(result)


def test_validity_window_inclusive_boundaries_only_mock():
    c = council()
    for now in (5, 15):
        r = lab.evaluate_council(replace(c, observed_tick=now))
        assert r.rule == "W4D_LAB_QUORUM_ONLY"
        assert_non_authority(r)


def test_motion_digest_is_versioned_and_deterministic():
    c = council()
    digest = lab.mock_motion_digest(c.motion)
    # Fixed byte vector from documented array serialization and domain separator.
    assert digest == "bb466b9b9885d1f8d8bae95dc18fb5a9a77dd7fc86333af4b1a6fd2887acf014"
    assert len(digest) == 64


def test_an_applicant_can_fabricate_all_mock_bytes_but_cannot_mint_authority():
    original = council()
    changed = replace(original.motion, motion_id="AnotherMotion", nonce="AnotherNonce")
    changed = replace(changed, digest=lab.mock_motion_digest(changed))
    # Caller can fabricate every mock ballot too. This is why a "LAB_*" result
    # is not authorization or evidence; no external trust anchor or signature exists.
    votes = tuple(replace(b, motion_digest=changed.digest) for b in original.votes)
    forged = replace(original, motion=changed, votes=votes)
    out = lab.evaluate_council(forged)
    assert out.lab_step == "LAB_PROCEDURAL_REVIEW_RECOMMENDATION"
    assert_non_authority(out)


@pytest.mark.parametrize("groups", [(), ("Group1",), ("Group1", "Group1")])
def test_original_appeal_panel_missing_or_ambiguous_never_screenable(groups):
    r = lab.evaluate_appeal(replace(appeal(), original_panel_groups=groups))
    assert r.lab_step == "HOLD"
    assert r.rule == "W4D_APPEAL_ORIGINAL_PANEL_UNRESOLVED"
    assert_non_authority(r)


def test_explicit_unverified_panel_completeness_is_a_hold():
    r = lab.evaluate_appeal(replace(appeal(), original_panel_complete_claimed=False))
    assert r.rule == "W4D_APPEAL_ORIGINAL_PANEL_UNRESOLVED"
    assert_non_authority(r)


@pytest.mark.parametrize("input_value", [None, [], "VERIFIED_FOR_REVIEW_ONLY", "ADMITTED", "M0_PASS", "True"])
def test_lab_step_cannot_be_used_as_implicit_authority_channel(input_value):
    with pytest.raises(ValueError, match="LAB_CANNOT_GRANT_REAL_AUTHORITY_OR_TRUTH"):
        lab.Finding("UNKNOWN", "MOCK", lab_step=input_value)
