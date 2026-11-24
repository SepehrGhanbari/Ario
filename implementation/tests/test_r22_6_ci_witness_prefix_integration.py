"""R22.6 lab integration: bind real R22.5 observer output to existing checkpoints.

The event list is a synthetic world oracle, not an authenticated GitHub feed.
The frozen control is retained by test convention, not a deployed custodian.
No production adapter, keys, admission, network, or trust activation.
"""
import copy
import hashlib
import json
from dataclasses import replace

import pytest

import checkpoint_prefix_experiment as prefix
import independent_witness_experiment as witness
from test_independent_witness_experiment import canonical, seal, ledger, checkpoint
from test_r22_5_replay_aba_boundary import sample, assert_no_authority

SCOPE = {
    "domain": prefix.DOMAIN,
    "ledger_id": "R22.6:SepehrGhanbari/Ario:PR295:" + "c" * 40,
    "epoch": "R22.6-SYNTHETIC-SESSION-1",
    "branch_id": "R22.6-OBSERVATION-LAB",
}
CONTEXT = prefix.Context(**SCOPE)
KEY = prefix.SYMBOLIC_KEY_A


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def observed_rows(world, observation, *, events=None):
    """Four bounded records: scope, actual observer transcript/result, two event slots.

    Event slots are explicit reports by the synthetic oracle. An empty slot
    cannot assert that an event never happened. Scope is independently chosen.
    """
    assert_no_authority(observation)
    wire = [(url, status, list(headers), body.hex())
            for url, status, headers, body in world.transcript]
    captured = list(world.events if events is None else events)
    assert len(captured) <= 2
    captured += ["NO_EVENT_REPORTED"] * (2 - len(captured))
    values = [
        digest(SCOPE),
        digest({"wire": wire, "observer_output": observation}),
        captured[0], captured[1],
    ]
    rows = []
    for i, value in enumerate(values):
        payload = {"claim_id": "R22.6-OBSERVATION",
                   "node_id": f"OBS-{i}", "value": value}
        if i:
            payload.update(lineage_from=f"OBS-{i-1}", lineage_to=f"OBS-{i}")
        rows.append({"record_id": f"ROW-{i}", "observed_at": f"LAB-STEP-{i}",
                     "payload": payload})
    return seal(rows)


def envelope(rows, role, count=4, scope=None):
    identity = f"TEST-KEEPER-{role}"
    parent = checkpoint(rows, 2, identity, scope=scope or SCOPE)
    child = (checkpoint(rows, 4, identity,
                        parent=json.loads(parent)["checkpoint_sha256"],
                        scope=scope or SCOPE) if count == 4 else parent)
    return witness.seal_test_envelope(
        role=role, witness_id=identity, custody_domain_label=f"LAB-GROUP-{role}",
        checkpoint_bytes=child,
        parent_checkpoint_bytes=parent if count == 4 else None,
        snapshot_reference=f"R22.6-{role}", capture_sequence=count,
        declared_provenance="SYNTHETIC-ORACLE-NOT-AUTHENTICATED",
    )


def control(rows, floor=4, count=4):
    return witness.WitnessControl(
        anchors=tuple(envelope(rows, role, count) for role in ("A", "B")),
        context=CONTEXT,
        symbolic_bindings=(("TEST-KEEPER-A", KEY), ("TEST-KEEPER-B", KEY)),
        known_floor=floor, laboratory_isolated_roles=("A", "B"),
    )


def compare(rows, retained, *, presented=None, compromised=False):
    report = witness.verify_witnesses(witness.WitnessCase(
        candidate_bytes=ledger(rows),
        presented=retained.anchors if presented is None else presented,
        control=retained, candidate_key_descriptor=KEY,
        attacker_capability="SYNTHETIC-CANDIDATE-REWRITE",
        controller_compromised=compromised,
    ))
    assert report.historical_custody_independence == "NOT_ESTABLISHED"
    assert report.cryptographic_witness_authenticity == "NOT_CHECKED"
    assert report.historical_event_truth == "UNKNOWN"
    assert report.production_historical_continuity == "INCONCLUSIVE"
    assert report.evidence_admission == "NOT_EVALUATED"
    assert report.human_authorization == "NOT_EVALUATED"
    return report


def test_retained_scope_and_four_record_checkpoint_correspond():
    w, o = sample("stable")
    rows = observed_rows(w, o)
    r = compare(rows, control(rows))
    assert r.aggregate_verdict == "CONDITIONAL_CORRESPONDENCE"
    assert r.known_floor_relation.status == "MATCH"
    assert r.candidate_history_relation.status == "MATCH"


@pytest.mark.parametrize("mode", ["aba", "final_replay", "full_replay"])
def test_retained_event_observation_distinguishes_identical_http_transcripts(mode):
    stable, a = sample("stable")
    changed, b = sample(mode)
    assert stable.transcript == changed.transcript
    assert a == b
    honest = observed_rows(changed, b)
    omitted = observed_rows(stable, a)
    assert honest[:2] == omitted[:2]
    assert honest[2:] != omitted[2:]
    r = compare(omitted, control(honest))
    assert r.aggregate_verdict == "DEFINITE_DISCREPANCY"
    assert r.candidate_history_relation.status == "MISMATCH"
    assert all(x.local_hash_validity.status == "MATCH" for x in r.inspections)


def test_old_checkpoint_can_match_prefix_but_fails_retained_floor():
    w, o = sample("aba")
    rows = observed_rows(w, o)
    retained = control(rows)
    old = tuple(envelope(rows, role, 2) for role in ("A", "B"))
    cp2, cp4 = retained.anchors[0].parent_checkpoint_bytes, retained.anchors[0].checkpoint_bytes
    oracle = prefix.OracleSnapshot((cp2, cp4), known_floor=4)
    local = prefix.compare_prefix(ledger(rows[:2]), cp2, oracle, CONTEXT,
                                  candidate_key_descriptor=KEY)
    assert local.property_verdict == "PASS"  # only prefix correspondence
    assert local.known_checkpoint_floor.status == "MISMATCH"
    r = compare(rows[:2], retained, presented=old)
    assert r.aggregate_verdict == "DEFINITE_DISCREPANCY"
    assert r.known_floor_relation.status == "MISMATCH"


@pytest.mark.parametrize("mutation", ["delete_event", "replace_event", "swap_events"])
def test_resealed_event_rewrite_cannot_match_retained_hash(mutation):
    w, o = sample("aba")
    original = observed_rows(w, o)
    edited = copy.deepcopy(original)
    if mutation == "delete_event":
        edited[2]["payload"]["value"] = "NO_EVENT_REPORTED"
    elif mutation == "replace_event":
        edited[2]["payload"]["value"] = "DIFFERENT_EVENT"
    else:
        edited[2]["payload"]["value"], edited[3]["payload"]["value"] = (
            edited[3]["payload"]["value"], edited[2]["payload"]["value"])
    edited = seal(edited)
    assert len(edited) == len(original)
    r = compare(edited, control(original))
    assert r.aggregate_verdict == "DEFINITE_DISCREPANCY"
    assert r.candidate_history_relation.status == "MISMATCH"
    assert all(x.local_hash_validity.status == "MATCH" for x in r.inspections)


def test_same_count_fork_with_resealed_checkpoint_detected():
    w, o = sample("aba")
    original = observed_rows(w, o)
    fork = observed_rows(w, o, events=[])
    presented = tuple(envelope(fork, role) for role in ("A", "B"))
    r = compare(fork, control(original), presented=presented)
    assert r.aggregate_verdict == "DEFINITE_DISCREPANCY"
    assert all(x.snapshot_integrity.status == "MISMATCH" for x in r.inspections)


def test_conflicting_retained_witnesses_are_not_resolved_by_candidate():
    w, o = sample("aba")
    original = observed_rows(w, o)
    fork = observed_rows(w, o, events=[])
    retained = control(original)
    retained = replace(retained, anchors=(retained.anchors[0], envelope(fork, "B")))
    r = compare(original, retained)
    assert r.aggregate_verdict == "UNRESOLVED_CONFLICT"
    assert r.cross_witness_commitment_relation.status == "CONFLICT"


def test_absent_witness_does_not_establish_two_witness_agreement():
    w, o = sample("aba")
    rows = observed_rows(w, o)
    retained = control(rows)
    r = compare(rows, retained, presented=retained.anchors[:1])
    assert r.aggregate_verdict == "INCONCLUSIVE"
    assert r.cross_witness_commitment_relation.status == "UNKNOWN"


def test_missing_floor_cannot_establish_freshness():
    w, o = sample("stable")
    rows = observed_rows(w, o)
    r = compare(rows, control(rows, floor=None))
    assert r.known_floor_relation.status == "UNKNOWN"


def test_scope_replay_of_resealed_checkpoints_is_not_correspondence():
    w, o = sample("stable")
    rows = observed_rows(w, o)
    wrong_scope = dict(SCOPE, epoch="DIFFERENT-EPOCH")
    presented = tuple(envelope(rows, role, scope=wrong_scope) for role in ("A", "B"))
    r = compare(rows, control(rows), presented=presented)
    assert r.aggregate_verdict == "DEFINITE_DISCREPANCY"


def test_common_admin_rollback_remains_indistinguishable_if_floor_is_reset():
    w, o = sample("aba")
    rows = observed_rows(w, o)
    old = rows[:2]
    retained = control(rows)
    assert compare(old, retained).aggregate_verdict == "DEFINITE_DISCREPANCY"
    reset = control(old, floor=2, count=2)
    r = compare(old, reset, compromised=True)
    assert r.aggregate_verdict == "CONDITIONAL_CORRESPONDENCE"
    assert r.known_floor_relation.status == "MATCH"
    assert r.custody_independence == "UNKNOWN"
    assert r.independence_basis == "COMPROMISED_BY_SCENARIO"


def test_events_not_seen_by_witness_remain_indistinguishable():
    stable, a = sample("stable")
    changed, b = sample("aba")
    assert changed.events == ["PR_A_TO_B", "PR_B_TO_A"]
    original = observed_rows(stable, a)
    missed = observed_rows(changed, b, events=[])
    assert original == missed
    r = compare(missed, control(original))
    assert r.aggregate_verdict == "CONDITIONAL_CORRESPONDENCE"
    assert r.historical_event_truth == "UNKNOWN"
