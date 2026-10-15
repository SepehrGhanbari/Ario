"""Independent negative probes: declared conflicted recovery voters cannot enable a lab quorum.

Only supplied controller labels are compared; no real identity, trust, or authorization exists.
"""
from dataclasses import replace

import pytest
import w4d_governance_lab as lab
from test_w4d_governance_lab import council, assert_non_authority


@pytest.mark.parametrize("action", ["ROTATE_ROOT", "UNFREEZE"])
@pytest.mark.parametrize("conflicting_group", ["Proposer", "Source"])
@pytest.mark.parametrize("steward_offset", [0, 3])
def test_w4d_review_conflicted_positive_recovery_ballot_blocks_mock_recommendation(
    action, conflicting_group, steward_offset
):
    flags = {"independent_recovery_attestation_claimed": True,
             "post_compromise_epoch_claimed": True,
             "currently_frozen": action == "UNFREEZE"}
    fixture = council(action, 4, **flags)
    roster = list(fixture.members)
    roster[steward_offset] = replace(roster[steward_offset],
                                     declared_control_group=conflicting_group)
    result = lab.evaluate_council(replace(fixture, members=tuple(roster)))
    assert result.rule == "W4D_RECOVERY_INTEREST_CONFLICT"
    assert result.lab_step == "HOLD"
    assert_non_authority(result)


def test_w4d_declared_interested_opposition_not_counted_as_support():
    fixture = council("ROTATE_ROOT", 3,
                      independent_recovery_attestation_claimed=True,
                      post_compromise_epoch_claimed=True)
    roster = list(fixture.members)
    roster[3] = replace(roster[3], declared_control_group="Proposer")
    votes = fixture.votes + (lab.Vote("Opposition", "Steward4", fixture.motion.digest,
                                      fixture.motion.epoch, "OPPOSE"),)
    result = lab.evaluate_council(replace(fixture, members=tuple(roster), votes=votes))
    assert result.rule == "W4D_CONDITIONAL_QUORUM_NOT_MET"
    assert result.lab_step == "HOLD"
    assert_non_authority(result)
