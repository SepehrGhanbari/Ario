"""TB-004 v0.2: inherited 32 scenarios + binding/chain regression gates.

No storage/network/cryptography/runtime access. The lab labels are not identities.
"""

from dataclasses import replace
from hashlib import sha256
import inspect

import pytest

import witness_compromise_recovery_experiment_v0_2 as m

D = sha256(b"synthetic-row-four-checkpoint").hexdigest()
D_ALT = sha256(b"synthetic-recomputed-checkpoint").hexdigest()
SCOPE = "LAB-LEDGER-001/EPOCH-A/BRANCH-A"


def base(**kw):
    epoch = m.WitnessEpoch("EP-A", "WITNESS-A", SCOPE, "ROOT-A", 0)
    art = m.HistoricalArtifact("ART-A", "WITNESS-A", "EP-A", SCOPE, 10, D)
    ref = m.FrozenReference("REF-EXTERNAL", "ART-A", D, 12, "ROOT-EXT",
                            "LAB_CONDITIONALLY_SEPARATE", True, m.LAB, "LAB-REFERENCE-BINDING")
    c = m.RecoveryCase(SCOPE, (epoch,), (art,), (ref,), (), (), (), (),
                       "ART-A", 70, True, m.LAB)
    return replace(c, **kw)


def obs(kind="CONFIRMED_WINDOW", earliest=18, confirmed=25, *, identity="O-COMP", target="EP-A",
        target_kind="EPOCH", discovery=40, origin=m.LAB, refutes=None):
    return m.CompromiseObservation(identity,target_kind,target,kind,discovery,
                                   earliest,confirmed,origin,"LAB-OBSERVATION",refutes)


def suspicion(identity="O-SUS", *, origin=m.LAB, discovery=30):
    return obs("SUSPECTED",None,None,identity=identity,origin=origin,discovery=discovery)


def refute(identity="O-REFUTE", *, target="O-SUS", discovery=50, origin=m.LAB):
    return obs("REFUTATION",None,None,identity=identity,discovery=discovery,
               origin=origin,refutes=target)


def recover(*, same_root=False, separation="LAB_CONDITIONALLY_SEPARATE", complete=True,
            origin=m.LAB,enrollment=m.LAB,second_proposal=False):
    epoch2 = m.WitnessEpoch("EP-B", "WITNESS-A", SCOPE, "ROOT-A" if same_root else "ROOT-B", 45, "EP-A")
    art2 = m.HistoricalArtifact("ART-B", "WITNESS-A", "EP-B", SCOPE, 50, D_ALT)
    ref2 = m.FrozenReference("REF-B", "ART-B", D_ALT, 52, "ROOT-EXT-B",
                             "LAB_CONDITIONALLY_SEPARATE", True, m.LAB, "LAB-REF-B")
    proposal = m.RecoveryProposal("REC-A","EP-A","EP-B",45,origin,separation,complete,
                                  enrollment,"LAB-ENROLLMENT-ONLY","LAB-RECOVERY")
    first=base()
    proposals=(proposal,)
    if second_proposal:
        proposals += (replace(proposal,proposal_id="REC-B"),)
    return replace(first,epochs=first.epochs+(epoch2,),artifacts=first.artifacts+(art2,),
                   observations=(obs(earliest=18,confirmed=25,discovery=40),),
                   frozen_references=first.frozen_references+(ref2,),
                   recovery_proposals=proposals,target_artifact_id="ART-B",evaluation_sequence=80)


def result(c):
    out=m.evaluate_recovery(c)
    assert out.production_custody_authenticity == "NOT_ESTABLISHED"
    assert out.cryptographic_authentication == "NOT_CHECKED"
    assert out.trusted_physical_time == "NOT_CHECKED"
    assert out.actual_revocation == "NOT_PERFORMED"
    assert out.human_authorization == "NOT_EVALUATED"
    assert out.evidence_admission == "NOT_EVALUATED"
    assert out.historical_event_truth == "UNKNOWN"
    assert out.entity_continuity == "UNKNOWN"
    assert out.ontological_continuity == "UNKNOWN"
    assert out.production_historical_continuity == "INCONCLUSIVE"
    assert out.original_artifacts == c.artifacts
    assert out.original_evaluations == c.prior_evaluations
    return out


def frozen_prior(case, *, origin=None):
    """Explicit laboratory declaration of a previously derived v0.2 record.

    This fixture IS NOT cryptographic proof of provenance. The report is
    converted into a LAB-declared prior to test internal chain consistency.
    """
    prior = result(case).new_evaluation
    assert prior is not None
    return m.PriorEvaluation(prior.evaluation_id, prior.artifact_id,
                             prior.epoch_id, prior.sequence, prior.policy,
                             prior.usability, prior.supersedes_evaluation_id,
                             m.LAB if origin is None else origin,
                             "LAB-FROZEN-PRIOR-DECLARATION",
                             prior.evidence_digest, prior.reason_codes)


# All 32 contract IDs remain stable and individually executable.
def test_TC_01_no_compromise_reported_but_independent_support_absent():
    r=result(base(frozen_references=()))
    assert r.evidentiary_usability.status == "INSUFFICIENT_SUPPORT"
    assert r.compromise_knowledge.status == "NOT_ESTABLISHED"


def test_TC_02_pin_with_explicit_lab_coverage_conditional_only():
    r=result(base())
    assert r.evidentiary_usability.status == "CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON"
    assert r.frozen_preservation.status == "LAB_CONDITIONAL_REFERENCE_PRESENT"


def test_TC_03_discovered_later_onset_unknown():
    r=result(base(observations=(obs(earliest=None),)))
    assert r.compromise_knowledge.status == "CONFIRMED_BY_LAB_CONTROL"
    assert r.capture_window_relation.status == "WITHIN_OR_UNBOUNDED_WINDOW"
    assert r.evidentiary_usability.status == "SUSPENDED"


def test_TC_04_capture_within_possible_compromise_window():
    r=result(base(observations=(obs(earliest=9,confirmed=25),)))
    assert r.capture_window_relation.status == "WITHIN_OR_UNBOUNDED_WINDOW"
    assert r.evidentiary_usability.status == "SUSPENDED"


def test_TC_05_capture_after_all_possible_compromise_onsets():
    r=result(base(observations=(obs(earliest=2,confirmed=8),)))
    assert r.capture_window_relation.status == "AFTER_CONFIRMED_ONSET"
    assert r.evidentiary_usability.status == "SUSPENDED"


def test_TC_06_local_hash_well_formed_not_trust():
    r=result(base(observations=(obs(earliest=None),)))
    assert len(base().artifacts[0].checkpoint_sha256)==64
    assert r.evidentiary_usability.status == "SUSPENDED"


def test_TC_07_attacker_reseals_later_checkpoint():
    c=base(artifacts=(replace(base().artifacts[0],checkpoint_sha256=D_ALT),),
           observations=(obs(earliest=2,confirmed=8),))
    r=result(c)
    assert r.evidentiary_usability.status == "REJECTED_FOR_NAMED_USE"
    assert r.frozen_preservation.status == "MISMATCH"


def test_TC_08_pinned_before_possible_compromise_keeps_limited_utility():
    r=result(base(observations=(obs(earliest=18,confirmed=25),)))
    assert r.capture_window_relation.status == "BEFORE_POSSIBLE_ONSET"
    assert r.evidentiary_usability.status == "CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON"


def test_TC_09_old_reference_only_in_compromised_custody():
    r0=base().frozen_references[0]
    r=result(base(frozen_references=(replace(r0,custody_control_root="ROOT-A"),),
                  observations=(obs(earliest=18,confirmed=25),)))
    assert r.frozen_preservation.status == "UNKNOWN"
    assert r.evidentiary_usability.status == "SUSPENDED"


def test_TC_10_witness_self_reported_compromise_onset_not_authoritative():
    r=result(base(observations=(obs(origin=m.SELF,earliest=19),),complete_compromise_inventory=False))
    assert r.compromise_knowledge.status == "UNKNOWN"
    assert r.evidentiary_usability.status == "INSUFFICIENT_SUPPORT"
    assert "O-COMP" in r.unsupported_observations


def test_TC_11_conflicting_confirmed_onset_windows():
    r=result(base(observations=(obs(earliest=15,confirmed=20),
                                obs(identity="O-2",earliest=30,confirmed=35,discovery=45))))
    assert r.compromise_knowledge.status == "CONTRADICTORY_EVIDENCE"
    assert r.evidentiary_usability.status == "SUSPENDED"
    assert "INCOMPATIBLE_CONFIRMED_ONSET_WINDOWS" in r.conflicts


def test_TC_12_unverified_clock_cannot_resolve_onset():
    r=result(base(observations=(obs(earliest=None),)))
    assert r.trusted_physical_time == "NOT_CHECKED"
    assert r.capture_window_relation.status != "BEFORE_POSSIBLE_ONSET"


def test_TC_13_compromised_predecessor_self_enrollment_denied():
    r=result(recover(origin=m.SELF,enrollment=m.SELF))
    assert r.recovery_assessment.status != "LAB_CONDITIONALLY_RECOVERED"
    assert r.evidentiary_usability.status == "INSUFFICIENT_SUPPORT"


def test_TC_14_same_control_root_not_new_trust():
    r=result(recover(same_root=True))
    assert r.recovery_assessment.status == "UNKNOWN"
    assert r.evidentiary_usability.status != "CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON"


def test_TC_15_new_storage_but_shared_control_backup():
    r=result(recover(separation="COMMON_CONTROL_DETECTED"))
    assert r.recovery_assessment.status == "UNKNOWN"
    assert r.evidentiary_usability.status == "INSUFFICIENT_SUPPORT"


def test_TC_16_complete_lab_separation_new_epoch_conditional_only():
    r=result(recover())
    assert r.recovery_assessment.status == "LAB_CONDITIONALLY_RECOVERED"
    assert r.epoch_lifecycle.status == "EPOCH_ACTIVE_IN_LAB_MODEL"
    assert r.evidentiary_usability.status == "CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON"


def test_TC_17_matching_old_digest_does_not_retroactively_prove_old_history():
    c=recover()
    a=c.artifacts[1]
    ref2=c.frozen_references[1]
    c=replace(c,artifacts=(c.artifacts[0],replace(a,checkpoint_sha256=D)),
              frozen_references=(c.frozen_references[0],replace(ref2,checkpoint_sha256=D)))
    r=result(c)
    assert r.evidentiary_usability.status == "CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON"
    assert r.historical_event_truth=="UNKNOWN"


def test_TC_18_incomplete_admin_inventory_prevents_recovery():
    r=result(recover(complete=False))
    assert r.recovery_assessment.status == "UNKNOWN"


def test_TC_19_original_evaluations_preserved_after_new_conflicting_information():
    old=frozen_prior(base(evaluation_sequence=20))
    c=base(prior_evaluations=(old,),observations=(obs(earliest=None),),
           expected_previous_evaluation_id=old.evaluation_id)
    r=result(c)
    assert r.original_evaluations==(old,)
    assert r.new_evaluation.supersedes_evaluation_id == old.evaluation_id
    assert r.evidentiary_usability.status == "SUSPENDED"


def test_TC_20_attempt_to_hide_expected_historical_evaluation():
    c=base(expected_previous_evaluation_id="EVAL-OLD")
    r=result(c)
    assert r.evidentiary_usability.status == "INVALID_INPUT"
    assert "EXPECTED_HISTORICAL_EVALUATION_MISSING" in r.reason_codes


def test_TC_21_replay_recovery_with_wrong_predecessor_or_scope():
    c=recover()
    bad_epoch=replace(c.epochs[1],scope="OTHER-LEDGER")
    r=result(replace(c,epochs=(c.epochs[0],bad_epoch)))
    assert r.evidentiary_usability.status == "INVALID_INPUT"


def test_TC_22_witnesses_share_compromised_root_no_majority():
    second=m.WitnessEpoch("EP-C","WITNESS-B",SCOPE,"ROOT-A",0)
    c=base()
    c=replace(c,epochs=c.epochs+(second,),
              observations=(obs(target_kind="CONTROL_ROOT",target="ROOT-A",earliest=None),))
    r=result(c)
    assert r.evidentiary_usability.status == "SUSPENDED"
    assert r.historical_event_truth == "UNKNOWN"


def test_TC_23_earlier_assessment_not_fresh_enrollment_evidence():
    r=result(recover(enrollment=m.DERIVED))
    assert r.recovery_assessment.status == "UNKNOWN"


def test_TC_24_conflicting_recovery_proposals_not_auto_selected():
    r=result(recover(second_proposal=True))
    assert "CONFLICTING_RECOVERY_PROPOSALS" in r.conflicts
    assert r.evidentiary_usability.status == "SUSPENDED"


def test_TC_25_full_compromise_of_lab_controller():
    c=replace(recover(),controller_compromised=True)
    r=result(c)
    assert r.evidentiary_usability.status == "INSUFFICIENT_SUPPORT"
    assert r.epoch_lifecycle.status == "UNKNOWN"


def test_TC_26_cycle_or_inconsistent_successor_order():
    c=recover()
    cycle=replace(c.epochs[0],predecessor_epoch_id="EP-B")
    r=result(replace(c,epochs=(cycle,c.epochs[1])))
    assert r.evidentiary_usability.status == "INVALID_INPUT"


def test_TC_27_order_permutation_deterministic_report():
    c=base(observations=(suspicion("O-SUS-1"),suspicion("O-SUS-2")))
    r1=result(c)
    r2=result(replace(c,observations=tuple(reversed(c.observations))))
    assert r1==r2


def test_TC_28_duplicate_ids_and_unsupported_types_fail_bounded():
    c=base()
    assert result(replace(c,epochs=c.epochs+c.epochs)).evidentiary_usability.status=="INVALID_INPUT"
    assert result(replace(c,profile="UNSUPPORTED")).evidentiary_usability.status=="INVALID_INPUT"
    assert result(replace(c,observations=(suspicion(),)*33)).evidentiary_usability.status=="INVALID_INPUT"


def test_TC_29_report_has_no_m0_authority():
    r=result(base())
    assert r.kind=="EXPERIMENTAL_COMPROMISE_RECOVERY_V0_2"
    assert r.human_authorization=="NOT_EVALUATED"
    assert r.evidence_admission=="NOT_EVALUATED"
    assert "ADMIT" not in inspect.getsource(m.evaluate_recovery)


def test_TC_30_independently_supported_refutation_append_new_verdict():
    c=base(observations=(suspicion(),refute()),evaluation_sequence=65)
    r=result(c)
    assert r.compromise_knowledge.status=="NOT_ESTABLISHED"
    assert r.evidentiary_usability.status=="CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON"
    assert any(o.kind == "SUSPECTED" for o in c.observations)  # never deleted


def test_TC_31_late_refutation_not_backdated_to_prior_evaluation():
    c=base(observations=(suspicion(),refute(discovery=65)),evaluation_sequence=55)
    r=result(c)
    assert r.compromise_knowledge.status=="SUSPECTED"
    assert r.evidentiary_usability.status=="SUSPENDED"
    after=result(replace(c,evaluation_sequence=70))
    assert after.compromise_knowledge.status=="NOT_ESTABLISHED"


def test_TC_32_independent_frozen_reference_conflicts_with_claimed_digest():
    c=base(frozen_references=(replace(base().frozen_references[0],checkpoint_sha256=D_ALT),))
    r=result(c)
    assert r.frozen_preservation.status=="MISMATCH"
    assert r.evidentiary_usability.status=="REJECTED_FOR_NAMED_USE"
    assert "PRESERVED_CHECKPOINT_DIGEST_CONFLICT" in r.conflicts


# Additional regression controls: safety requirements that should survive refactors.
def test_reference_retained_after_earliest_onset_not_early_credible_pin():
    c=base(observations=(obs(earliest=18,confirmed=25),),
           frozen_references=(replace(base().frozen_references[0],retention_sequence=19),))
    assert result(c).evidentiary_usability.status=="SUSPENDED"


def test_reference_custody_root_compromised():
    o=obs(target_kind="CONTROL_ROOT",target="ROOT-EXT",earliest=1,confirmed=8)
    assert result(base(observations=(o,))).frozen_preservation.status=="UNKNOWN"


def test_self_refutation_cannot_clear_suspicion():
    r=result(base(observations=(suspicion(),refute(origin=m.SELF))))
    assert r.compromise_knowledge.status=="SUSPECTED"


def test_refutation_of_confirmed_compromise_creates_conflict():
    r=result(base(observations=(obs(earliest=18),refute(target="O-COMP"))))
    assert r.compromise_knowledge.status=="CONTRADICTORY_EVIDENCE"
    assert r.evidentiary_usability.status=="SUSPENDED"


def test_no_upgrade_from_missing_completeness():
    r=result(base(complete_compromise_inventory=False))
    assert r.evidentiary_usability.status=="INSUFFICIENT_SUPPORT"


def test_untrusted_reference_does_not_pin_even_with_matching_digest():
    r0=base().frozen_references[0]
    r=result(base(frozen_references=(replace(r0,origin=m.CANDIDATE),)))
    assert r.evidentiary_usability.status=="INSUFFICIENT_SUPPORT"


def test_no_retrocausal_evaluation():
    assert result(base(evaluation_sequence=5)).evidentiary_usability.status=="INVALID_INPUT"


def test_suspension_not_silently_reinstated():
    s=m.SuspensionEvent("S1","EP-A",30,m.LAB,"LAB-SUSP")
    r=result(base(suspensions=(s,)))
    assert r.evidentiary_usability.status=="SUSPENDED"


def test_incomplete_predecessor_history_cannot_be_fabricated():
    c=base(expected_previous_evaluation_id="NONEXISTENT")
    assert result(c).evidentiary_usability.status=="INVALID_INPUT"


def test_multiple_prior_evaluation_heads_ambiguous():
    a=frozen_prior(base(evaluation_sequence=20))
    b=frozen_prior(base(evaluation_sequence=25))
    r=result(base(prior_evaluations=(a,b)))
    assert r.evidentiary_usability.status=="INVALID_INPUT"


def test_prefix_report_or_signer_never_loaded():
    source=inspect.getsource(m)
    for forbidden in ("import checkpoint_prefix_experiment", "import independent_witness_experiment",
                      "import witness_provenance_experiment", "subprocess", "socket", "open(", "os.system"):
        assert forbidden not in source


def test_frozen_input_unchanged_and_repeatable():
    c=base(observations=(obs(earliest=18),))
    before=repr(c)
    assert result(c)==result(c)
    assert repr(c)==before


def test_raw_digest_not_proof_of_historical_truth():
    c=base()
    r=result(c)
    assert r.evidentiary_usability.status == "CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON"
    assert r.historical_event_truth == "UNKNOWN"


def test_no_recovery_without_predecessor_freeze():
    c=recover()
    c=replace(c,observations=())
    r=result(c)
    assert r.recovery_assessment.status=="UNKNOWN"
    assert r.evidentiary_usability.status=="INSUFFICIENT_SUPPORT"


def test_predecessor_epoch_remains_superseded_not_revalidated():
    c=recover()
    c=replace(c,target_artifact_id="ART-A")
    r=result(c)
    assert r.epoch_lifecycle.status=="EPOCH_SUPERSEDED_IN_LAB_MODEL"
    assert r.historical_event_truth=="UNKNOWN"


def test_expected_previous_evaluation_must_bind_to_target_artifact():
    c=recover()
    previous=frozen_prior(replace(c,evaluation_sequence=65))
    c=replace(c,target_artifact_id="ART-A",prior_evaluations=(previous,),
              expected_previous_evaluation_id=previous.evaluation_id)
    r=result(c)
    assert r.evidentiary_usability.status=="INVALID_INPUT"
    assert "EXPECTED_HISTORICAL_EVALUATION_WRONG_SCOPE_OR_TIME" in r.reason_codes


def test_compromised_external_reference_does_not_supply_definite_mismatch():
    base_case=base()
    forged=replace(base_case.frozen_references[0],checkpoint_sha256=D_ALT)
    compromised=obs(target_kind="CONTROL_ROOT",target="ROOT-EXT",earliest=1,confirmed=8)
    r=result(replace(base_case,frozen_references=(forged,),observations=(compromised,)))
    assert "PRESERVED_CHECKPOINT_DIGEST_CONFLICT" not in r.conflicts
    assert r.evidentiary_usability.status!="REJECTED_FOR_NAMED_USE"


def test_one_matching_and_one_conflicting_lab_pin_no_majority():
    c=base()
    bad=replace(c.frozen_references[0],reference_id="REF-CONFLICT",checkpoint_sha256=D_ALT)
    r=result(replace(c,frozen_references=c.frozen_references+(bad,)))
    assert r.frozen_preservation.status=="MISMATCH"
    assert r.evidentiary_usability.status=="REJECTED_FOR_NAMED_USE"


def test_unhashable_malformed_origin_yields_invalid_not_exception():
    c=base(completeness_origin=[])  # type: ignore[arg-type]
    assert result(c).evidentiary_usability.status=="INVALID_INPUT"
    o=replace(suspicion(),origin=[])  # type: ignore[arg-type]
    assert result(base(observations=(o,))).evidentiary_usability.status=="INVALID_INPUT"


def test_unsupported_requested_property_cannot_be_autogranted():
    c=base(requested_property="HISTORICAL_EVENT_TRUTH")
    assert result(c).evidentiary_usability.status=="INVALID_INPUT"


def test_recovery_proposal_after_evaluation_not_applied_backwards():
    c=recover()
    # An artifact in the proposed successor epoch cannot be approved before
    # its recovery proposal sequence/capture, even if a future record is supplied.
    c=replace(c,evaluation_sequence=49)
    assert result(c).evidentiary_usability.status=="INVALID_INPUT"


# V0.2 security behavior: each case previously named by reason-only status
# must be evidence-bound, without granting authenticity or authority.

@pytest.mark.parametrize("change", (
    "observation_id", "observation_support_ref", "observation_window",
    "reference_id", "reference_digest", "reference_support_ref",
    "controller_flag", "completeness_flag", "artifact_digest", "scope_label",
    "epoch_control_root", "requested_sequence", "previous_pin",
))
def test_v02_full_case_evidence_binding_distinguishes_declared_changes(change):
    c=base(observations=(obs(earliest=18,confirmed=25),))
    if change == "observation_id":
        c=replace(c,observations=(replace(c.observations[0],observation_id="O-REPLACED"),))
    elif change == "observation_support_ref":
        c=replace(c,observations=(replace(c.observations[0],support_ref="LAB-ALT"),))
    elif change == "observation_window":
        c=replace(c,observations=(replace(c.observations[0],earliest_onset_sequence=19),))
    elif change == "reference_id":
        c=replace(c,frozen_references=(replace(c.frozen_references[0],reference_id="REF-NEW"),))
    elif change == "reference_digest":
        c=replace(c,frozen_references=(replace(c.frozen_references[0],checkpoint_sha256=D_ALT),))
    elif change == "reference_support_ref":
        c=replace(c,frozen_references=(replace(c.frozen_references[0],support_ref="LAB-ALT"),))
    elif change == "controller_flag":
        c=replace(c,controller_compromised=True)
    elif change == "completeness_flag":
        c=replace(c,complete_compromise_inventory=False)
    elif change == "artifact_digest":
        c=replace(c,artifacts=(replace(c.artifacts[0],checkpoint_sha256=D_ALT),))
    elif change == "scope_label":
        new_scope="LAB-LEDGER-001/EPOCH-B/BRANCH-A"
        c=replace(c,scope=new_scope,epochs=tuple(replace(e,scope=new_scope) for e in c.epochs),
                  artifacts=tuple(replace(a,scope=new_scope) for a in c.artifacts))
    elif change == "epoch_control_root":
        c=replace(c,epochs=(replace(c.epochs[0],control_root="ROOT-NEW"),))
    elif change == "requested_sequence":
        c=replace(c,evaluation_sequence=71)
    elif change == "previous_pin":
        # A valid prior history exists in this branch so the head check is meaningful.
        a=frozen_prior(base(evaluation_sequence=20))
        parent=replace(base(observations=(obs(earliest=18,confirmed=25),)),
                       prior_evaluations=(a,), expected_previous_evaluation_id=a.evaluation_id)
        changed=replace(parent,prior_evaluations=(replace(a,support_ref="LAB-NEW"),))
        assert result(parent).new_evaluation.evaluation_id != result(changed).new_evaluation.evaluation_id
        return
    first=result(base(observations=(obs(earliest=18,confirmed=25),)))
    second=result(c)
    assert first.new_evaluation is not None and second.new_evaluation is not None
    assert first.new_evaluation.evaluation_id != second.new_evaluation.evaluation_id
    assert first.new_evaluation.evidence_digest != second.new_evaluation.evidence_digest


def test_v02_proposal_identity_changes_even_if_same_status():
    c=recover()
    second=replace(c,recovery_proposals=(replace(c.recovery_proposals[0],proposal_id="REC-DIFFERENT"),))
    assert result(c).new_evaluation.evaluation_id != result(second).new_evaluation.evaluation_id


def test_v02_same_case_reordered_collections_same_identity():
    c=base(observations=(suspicion("O-SUS-1"),suspicion("O-SUS-2")),
           frozen_references=(base().frozen_references[0],replace(base().frozen_references[0],reference_id="REF-TWO")))
    changed=replace(c,observations=tuple(reversed(c.observations)),
                    frozen_references=tuple(reversed(c.frozen_references)))
    assert result(c).new_evaluation.evaluation_id == result(changed).new_evaluation.evaluation_id
    assert result(c)==result(changed) or (result(c).new_evaluation==result(changed).new_evaluation)


def test_v02_identifier_uses_new_namespace_and_full_digest():
    r=result(base())
    assert r.new_evaluation.evaluation_id.startswith("TB4-V02-EVAL-")
    assert len(r.new_evaluation.evaluation_id) == len("TB4-V02-EVAL-") + 64
    assert m.PROFILE.endswith("0.2") and m.POLICY.endswith("0.2")
    assert r.kind == "EXPERIMENTAL_COMPROMISE_RECOVERY_V0_2"
    assert r.historical_event_truth == "UNKNOWN"


def test_v02_prior_without_declared_head_is_rejected():
    a=frozen_prior(base(evaluation_sequence=20))
    r=result(base(prior_evaluations=(a,)))
    assert r.new_evaluation is None
    assert r.reason_codes == ("MISSING_CONTROLLER_DECLARED_PRIOR_HEAD",)
    assert r.original_evaluations == (a,)


@pytest.mark.parametrize("untrusted_origin",(m.CANDIDATE,m.SELF,m.DERIVED,m.UNKNOWN_ORIGIN))
def test_v02_nonlab_prior_cannot_be_a_chain_head(untrusted_origin):
    a=frozen_prior(base(evaluation_sequence=20), origin=untrusted_origin)
    r=result(base(prior_evaluations=(a,),expected_previous_evaluation_id=a.evaluation_id))
    assert r.new_evaluation is None
    assert r.reason_codes == ("NON_LAB_PRIOR_CANNOT_SUPPLY_HEAD",)
    assert r.original_evaluations == (a,)


def test_v02_fake_prior_id_rejected_even_when_lab_labeled():
    a=frozen_prior(base(evaluation_sequence=20))
    fake=replace(a,evaluation_id="FAKE-EVAL-ID-NOT-A-HASH")
    r=result(base(prior_evaluations=(fake,),expected_previous_evaluation_id=fake.evaluation_id))
    assert r.new_evaluation is None
    assert r.reason_codes == ("PRIOR_EVALUATION_CONTENT_BINDING_MISMATCH",)


@pytest.mark.parametrize("field,wrong", (
    ("usability","SUSPENDED"), ("sequence",19),
    ("evidence_digest", "f"*64), ("reason_codes", ("ALTERNATE_REASONS",)),
    ("supersedes_evaluation_id", "FAKE-PARENT"),
))
def test_v02_prior_metadata_tampering_cannot_keep_same_id(field,wrong):
    a=frozen_prior(base(evaluation_sequence=20))
    damaged=replace(a,**{field:wrong})
    r=result(base(prior_evaluations=(damaged,),expected_previous_evaluation_id=damaged.evaluation_id))
    assert r.new_evaluation is None
    assert r.reason_codes == ("PRIOR_EVALUATION_CONTENT_BINDING_MISMATCH",)


def test_v02_wrong_declared_head_cannot_pick_older_liked_record():
    a=frozen_prior(base(evaluation_sequence=20))
    b=frozen_prior(base(evaluation_sequence=25,prior_evaluations=(a,),
                        expected_previous_evaluation_id=a.evaluation_id))
    # b itself is the single current head, but the caller pins an older ancestor.
    r=result(base(prior_evaluations=(a,b),expected_previous_evaluation_id=a.evaluation_id))
    assert r.new_evaluation is None
    assert r.reason_codes == ("CONTROLLER_DECLARED_HEAD_MISMATCH",)


def test_v02_pinned_consistent_chain_supersedes_only_head():
    a=frozen_prior(base(evaluation_sequence=20))
    mid=base(evaluation_sequence=25,prior_evaluations=(a,),expected_previous_evaluation_id=a.evaluation_id)
    b=frozen_prior(mid)
    case=base(prior_evaluations=(a,b),expected_previous_evaluation_id=b.evaluation_id)
    r=result(case)
    assert r.new_evaluation is not None
    assert r.new_evaluation.supersedes_evaluation_id == b.evaluation_id
    assert r.original_evaluations==(a,b)


def test_v02_hiding_known_head_is_rejected_when_controller_declares_pin():
    a=frozen_prior(base(evaluation_sequence=20))
    r=result(base(expected_previous_evaluation_id=a.evaluation_id))
    assert r.new_evaluation is None
    assert r.reason_codes == ("EXPECTED_HISTORICAL_EVALUATION_MISSING",)


def test_v02_preexisting_v01_policy_priors_not_silently_migrated():
    a=frozen_prior(base(evaluation_sequence=20))
    old=replace(a,policy="ARIO-TB4-LAB-POLICY-0.1")
    r=result(base(prior_evaluations=(old,), expected_previous_evaluation_id=old.evaluation_id))
    assert r.new_evaluation is None
    assert r.reason_codes == ("INVALID_PRIOR_EVALUATION",)


def test_v02_long_but_valid_unsupported_observation_reason_can_be_a_prior():
    long_identity="O"*128
    c=base(evaluation_sequence=50,complete_compromise_inventory=False,
           observations=(suspicion(identity=long_identity,origin=m.CANDIDATE),))
    a=frozen_prior(c)
    assert any(len(reason)>128 for reason in a.reason_codes)
    future=base(prior_evaluations=(a,),expected_previous_evaluation_id=a.evaluation_id)
    r=result(future)
    assert r.new_evaluation is not None
    assert r.new_evaluation.supersedes_evaluation_id==a.evaluation_id


def test_v02_compromised_lab_can_forge_consistent_inputs_no_trust_claim():
    a=frozen_prior(base(evaluation_sequence=20))
    # An attacker controlling all declarations can recalculate the hash chain.
    forged_digest="a"*64
    rewritten=replace(a,evidence_digest=forged_digest)
    rewritten=replace(rewritten,evaluation_id=m._evaluation_id(
        rewritten.artifact_id,rewritten.epoch_id,rewritten.sequence,
        rewritten.policy,rewritten.usability,rewritten.supersedes_evaluation_id,
        rewritten.reason_codes,rewritten.evidence_digest))
    c=base(prior_evaluations=(rewritten,),expected_previous_evaluation_id=rewritten.evaluation_id)
    r=result(c)
    assert r.new_evaluation is not None
    assert r.historical_event_truth=="UNKNOWN"
    assert r.production_custody_authenticity=="NOT_ESTABLISHED"
    assert r.cryptographic_authentication=="NOT_CHECKED"


def test_v02_no_mutation_of_inputs_or_prior_history():
    a=frozen_prior(base(evaluation_sequence=20))
    c=base(prior_evaluations=(a,),expected_previous_evaluation_id=a.evaluation_id)
    before=repr(c)
    r=result(c)
    assert repr(c)==before
    assert r.original_evaluations==(a,)
    assert r.new_evaluation.evaluation_id != a.evaluation_id
    assert r.production_historical_continuity=="INCONCLUSIVE"
