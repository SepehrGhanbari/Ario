"""ARIO-TB-002 synthetic-only scenarios; real custody/authenticity are not tested.

Against the Ario repo these tests import its existing checkpoint_prefix_experiment
unchanged. This test module creates all fixtures in memory; no filesystem writes.
"""

from dataclasses import replace
import copy
import hashlib
import json

import pytest

import checkpoint_prefix_experiment as base
import independent_witness_experiment as witness

KEY = base.SYMBOLIC_KEY_A
SCOPE = {
    "domain": "SYNTHETIC_CHECKPOINT_CORRESPONDENCE",
    "ledger_id": "SYNTHETIC-LEDGER-001",
    "epoch": "TEST-EPOCH-001",
    "branch_id": "TEST-BRANCH-A",
}
ROWS = (
    {"record_id": "ROW-0", "observed_at": "2026-10-12T00:00:00Z",
     "payload": {"node_id": "NODE-A", "claim_id": "SYNTHETIC-CLAIM", "value": "original synthetic observation"}},
    {"record_id": "ROW-1", "observed_at": "2026-10-12T00:01:00Z",
     "payload": {"node_id": "NODE-B", "claim_id": "SYNTHETIC-CLAIM", "value": "synthetic successor",
                 "lineage_from": "NODE-A", "lineage_to": "NODE-B"}},
    {"record_id": "ROW-2", "observed_at": "2026-10-12T00:02:00Z",
     "payload": {"node_id": "NODE-C", "claim_id": "SYNTHETIC-CLAIM", "value": "synthetic third record",
                 "lineage_from": "NODE-B", "lineage_to": "NODE-C"}},
    {"record_id": "ROW-3", "observed_at": "2026-10-12T00:03:00Z",
     "payload": {"node_id": "NODE-D", "claim_id": "SYNTHETIC-CLAIM", "value": "synthetic fourth record",
                 "lineage_from": "NODE-C", "lineage_to": "NODE-D"}},
)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def seal(rows):
    arr = copy.deepcopy(rows)
    prev = None
    for r in arr:
        r.pop("sha256", None)
        r["previous_sha256"] = prev
        r["sha256"] = sha(canonical(r))
        prev = r["sha256"]
    return arr


def ledger(rows):
    return b"".join(canonical(r) + b"\n" for r in rows)


def checkpoint(rows, count, who="TEST-KEEPER-A", parent=None, scope=None):
    prefix = ledger(rows[:count])
    fields = {
        "profile": "ARIO-PREFIX-EXPERIMENT-0.1", **(scope or SCOPE),
        "record_count": count, "prefix_byte_count": len(prefix),
        "prefix_sha256": sha(prefix), "head_sha256": rows[count-1]["sha256"],
        "previous_checkpoint_sha256": parent,
        "test_identity": who, "key_descriptor_sha256": sha(KEY),
    }
    fields["checkpoint_sha256"] = sha(canonical(fields))
    return canonical(fields)


BASE = seal(ROWS)
L2, L4 = ledger(BASE[:2]), ledger(BASE)
C2_A = checkpoint(BASE, 2)
C2_B = checkpoint(BASE, 2, "TEST-KEEPER-B")
C4_A = checkpoint(BASE, 4, parent=json.loads(C2_A)["checkpoint_sha256"])
C4_B = checkpoint(BASE, 4, "TEST-KEEPER-B", parent=json.loads(C2_B)["checkpoint_sha256"])

assert sha(L2) == "00a9c8f968a53e987e2c90b93eecf32186612d28bb12568bc608b59c13ef4e94"
assert sha(L4) == "3f9bf3fa7fe9b3b71113292e4fff2671545fdcc383260a15b4cc4275e89a9e72"


def envelope(role, cp=None, parent=None, group=None, who=None, sequence=4):
    who = who or f"TEST-KEEPER-{role}"
    return witness.seal_test_envelope(
        role=role, witness_id=who,
        custody_domain_label=group or f"LAB-GROUP-{role}",
        checkpoint_bytes=cp if cp is not None else (C4_A if role == "A" else C4_B),
        parent_checkpoint_bytes=parent if parent is not None else (C2_A if role == "A" else C2_B),
        snapshot_reference=f"FROZEN-{role}-001",
        capture_sequence=sequence,
        declared_provenance="TEST-CONTROLLER-DECLARATION-NOT-AUTHENTICATED",
    )


def case(*, candidate=L4, a=None, b=None, present=None, floor=4,
         context=None, isolated=("A", "B"), attacker="ATTACKER_CONTROLS_CANDIDATE",
         descriptor=KEY, compromised_roles=(), controller_compromised=False):
    a = a if a is not None else envelope("A")
    b = b if b is not None else envelope("B")
    control = witness.WitnessControl(
        anchors=(a, b),
        context=context if context is not None else base.Context(**SCOPE),
        symbolic_bindings=(("TEST-KEEPER-A", KEY), ("TEST-KEEPER-B", KEY)),
        known_floor=floor,
        laboratory_isolated_roles=isolated,
    )
    return witness.WitnessCase(candidate, (a, b) if present is None else present,
                               control, descriptor, attacker, compromised_roles,
                               controller_compromised)


def verify(c):
    output = witness.verify_witnesses(c)
    assert output.kind == "EXPERIMENTAL_WITNESS_COMPARISON"
    assert output.cryptographic_witness_authenticity == "NOT_CHECKED"
    assert output.historical_custody_independence == "NOT_ESTABLISHED"
    assert output.human_authorization == "NOT_EVALUATED"
    assert output.evidence_admission == "NOT_EVALUATED"
    assert output.historical_event_truth == "UNKNOWN"
    assert output.entity_continuity == "UNKNOWN"
    assert output.ontological_continuity == "UNKNOWN"
    assert output.production_historical_continuity == "INCONCLUSIVE"
    return output


def reseal_candidate(index, value):
    altered = copy.deepcopy(BASE)
    altered[index]["payload"]["value"] = value
    return ledger(seal(altered))


def altered_b_checkpoint(index, value):
    altered = copy.deepcopy(BASE)
    altered[index]["payload"]["value"] = value
    changed = seal(altered)
    parent = checkpoint(changed, 2, "TEST-KEEPER-B")
    new = checkpoint(changed, 4, "TEST-KEEPER-B", json.loads(parent)["checkpoint_sha256"])
    return changed, parent, new


def inspection(report, role):
    return next(w for w in report.inspections if w.role == role)


# One named test per pre-registered adversarial case, plus additional parser checks.

def test_tb01_original_both_witnesses_agree():
    r = verify(case())
    assert r.aggregate_verdict == "CONDITIONAL_CORRESPONDENCE"
    assert r.cross_witness_commitment_relation.status == "AGREE"
    assert r.custody_independence == "ASSUMED_FOR_EXPERIMENT"
    assert all(w.comparison_verdict == "PASS" for w in r.inspections)


def test_tb02_early_recomputed_history_is_rejected():
    r = verify(case(candidate=reseal_candidate(0, "replaced")))
    assert r.aggregate_verdict == "DEFINITE_DISCREPANCY"
    assert all(w.local_hash_validity.status == "MATCH" for w in r.inspections)
    assert all(w.checkpoint_correspondence.status == "MISMATCH" for w in r.inspections)


def test_tb03_later_suffix_can_preserve_old_prefix():
    a, b = envelope("A", C2_A, None), envelope("B")
    # C2 witness has no parent: construct the intended count-2 envelope explicitly.
    a = witness.seal_test_envelope(role="A", witness_id="TEST-KEEPER-A",
        custody_domain_label="LAB-GROUP-A", checkpoint_bytes=C2_A,
        parent_checkpoint_bytes=None, snapshot_reference="FROZEN-A-001",
        capture_sequence=2, declared_provenance="TEST-CONTROLLER-DECLARATION-NOT-AUTHENTICATED")
    r = verify(case(a=a, b=b, candidate=reseal_candidate(2, "replaced late")))
    assert inspection(r, "A").checkpoint_correspondence.status == "MATCH"
    assert inspection(r, "B").checkpoint_correspondence.status == "MISMATCH"
    assert r.aggregate_verdict == "DEFINITE_DISCREPANCY"


def test_tb04_old_ledger_matches_old_checkpoint_but_not_floor():
    a = envelope("A", C2_A)
    b = envelope("B", C2_B)
    a = replace(a, parent_checkpoint_bytes=None, capture_sequence=2)
    b = replace(b, parent_checkpoint_bytes=None, capture_sequence=2)
    a = replace(a, test_control_digest=witness.envelope_digest(a))
    b = replace(b, test_control_digest=witness.envelope_digest(b))
    r = verify(case(a=a, b=b, candidate=L2, floor=4))
    assert all(w.checkpoint_correspondence.status == "MATCH" for w in r.inspections)
    assert r.known_floor_relation.status == "MISMATCH"
    assert r.aggregate_verdict == "DEFINITE_DISCREPANCY"


def test_tb05_missing_floor_is_unknown_not_rollback_proof():
    r = verify(case(floor=None))
    assert r.aggregate_verdict == "CONDITIONAL_CORRESPONDENCE"
    assert r.known_floor_relation.status == "UNKNOWN"


def test_tb06_one_witness_unavailable():
    a = envelope("A")
    r = verify(case(a=a, present=(a,)))
    assert inspection(r, "A").checkpoint_correspondence.status == "MATCH"
    assert inspection(r, "B").checkpoint_correspondence.status == "UNKNOWN"
    assert r.aggregate_verdict == "INCONCLUSIVE"


def test_tb07_conflicting_frozen_commitments_not_voted_away():
    _, p, c = altered_b_checkpoint(0, "competing history")
    b = envelope("B", c, p)
    r = verify(case(b=b))
    assert r.cross_witness_commitment_relation.status == "CONFLICT"
    assert r.conflict_detected
    assert r.aggregate_verdict == "UNRESOLVED_CONFLICT"


def test_tb08_a_matches_b_conflicts_preserves_both():
    _, p, c = altered_b_checkpoint(0, "competing history")
    r = verify(case(b=envelope("B", c, p)))
    assert inspection(r, "A").checkpoint_correspondence.status == "MATCH"
    assert inspection(r, "B").checkpoint_correspondence.status == "MISMATCH"
    assert r.aggregate_verdict == "UNRESOLVED_CONFLICT"


def test_tb09_two_labels_one_custody_source_not_independent():
    r = verify(case(b=envelope("B", group="LAB-GROUP-A")))
    assert r.cross_witness_commitment_relation.status == "AGREE"
    assert r.custody_independence == "UNKNOWN"


def test_tb10_witness_identifier_substitution_fails_binding():
    c = case()
    original = c.presented[1]
    new = replace(original, witness_id="ATTACKER-NAME")
    new = replace(new, test_control_digest=witness.envelope_digest(new))
    r = verify(replace(c, presented=(c.presented[0], new)))
    assert inspection(r, "B").witness_identity_claim.status == "MISMATCH"
    assert r.aggregate_verdict == "DEFINITE_DISCREPANCY"


def test_tb11_replay_to_other_ledger_scope():
    context = base.Context(ledger_id="SYNTHETIC-LEDGER-OTHER",
        epoch=SCOPE["epoch"], branch_id=SCOPE["branch_id"], domain=SCOPE["domain"])
    r = verify(case(context=context))
    assert r.aggregate_verdict != "CONDITIONAL_CORRESPONDENCE"
    assert all(w.comparison_verdict != "PASS" for w in r.inspections)


def test_tb12_candidate_self_appointed_checkpoint_not_accepted():
    c = case()
    new_ledger = reseal_candidate(0, "manufactured")
    new_rows = [json.loads(line) for line in new_ledger.splitlines()]
    new_p = checkpoint(new_rows, 2, "TEST-KEEPER-B")
    new_cp = checkpoint(new_rows, 4, "TEST-KEEPER-B", json.loads(new_p)["checkpoint_sha256"])
    observed = replace(c.presented[1], checkpoint_bytes=new_cp, parent_checkpoint_bytes=new_p)
    observed = replace(observed, test_control_digest=witness.envelope_digest(observed))
    r = verify(replace(c, candidate_bytes=new_ledger, presented=(c.presented[0], observed)))
    assert inspection(r, "B").snapshot_integrity.status == "MISMATCH"
    assert r.aggregate_verdict == "DEFINITE_DISCREPANCY"


def test_tb13_prior_comparison_result_not_enrollable_as_witness():
    old = verify(case())
    c = case()
    bad = replace(c.presented[1], checkpoint_bytes=old)  # wrong artifact kind
    r = verify(replace(c, presented=(c.presented[0], bad)))
    assert r.aggregate_verdict == "INVALID_INPUT"


def test_tb14_metadata_only_difference_is_not_commitment_conflict():
    r = verify(case())
    assert C4_A != C4_B
    assert r.cross_witness_commitment_relation.status == "AGREE"
    assert not r.conflict_detected


@pytest.mark.parametrize("bad", [
    b'{"k":1,"k":2}',
    b'not-json',
    b'{"profile":"UNSUPPORTED"}',
    b'x' * (witness.MAX_CHECKPOINT_BYTES + 1),
])
def test_tb15_malformed_or_oversized_witness_material_rejected(bad):
    c = case()
    broken = replace(c.presented[1], checkpoint_bytes=bad)
    r = verify(replace(c, presented=(c.presented[0], broken)))
    assert r.aggregate_verdict in ("DEFINITE_DISCREPANCY", "INVALID_INPUT")
    assert r.aggregate_verdict != "CONDITIONAL_CORRESPONDENCE"


def test_tb16_reversing_witness_order_does_not_change_report():
    c = case()
    one = verify(c)
    two = verify(replace(c, presented=tuple(reversed(c.presented))))
    assert one == two


def test_tb17_full_compromise_cannot_establish_independent_history():
    modified = reseal_candidate(0, "coordinated revision")
    rows = [json.loads(line) for line in modified.splitlines()]
    a_parent = checkpoint(rows, 2, "TEST-KEEPER-A")
    b_parent = checkpoint(rows, 2, "TEST-KEEPER-B")
    a = envelope("A", checkpoint(rows, 4, parent=json.loads(a_parent)["checkpoint_sha256"]), a_parent)
    b = envelope("B", checkpoint(rows, 4, "TEST-KEEPER-B", json.loads(b_parent)["checkpoint_sha256"]), b_parent)
    r = verify(case(a=a, b=b, candidate=modified, attacker="FULL_CANDIDATE_AND_BOTH_CONTROLLERS_COMPROMISED",
        compromised_roles=("A", "B"), controller_compromised=True))
    assert r.aggregate_verdict == "CONDITIONAL_CORRESPONDENCE"
    assert r.historical_custody_independence == "NOT_ESTABLISHED"
    assert r.custody_independence == "UNKNOWN"
    assert r.independence_basis == "COMPROMISED_BY_SCENARIO"
    assert r.historical_event_truth == "UNKNOWN"


def test_tb18_collusion_and_false_event_description_not_truth():
    false = reseal_candidate(0, "asserted false event, no observation")
    rows = [json.loads(line) for line in false.splitlines()]
    pa = checkpoint(rows, 2, "TEST-KEEPER-A")
    pb = checkpoint(rows, 2, "TEST-KEEPER-B")
    r = verify(case(candidate=false,
        a=envelope("A", checkpoint(rows, 4, parent=json.loads(pa)["checkpoint_sha256"]), pa),
        b=envelope("B", checkpoint(rows, 4, "TEST-KEEPER-B", json.loads(pb)["checkpoint_sha256"]), pb),
        attacker="COLLUSION_BOTH_WITNESSES", compromised_roles=("A", "B")))
    assert r.aggregate_verdict == "CONDITIONAL_CORRESPONDENCE"
    assert r.independence_basis == "COMPROMISED_BY_SCENARIO"
    assert r.custody_independence == "UNKNOWN"
    assert r.historical_event_truth == "UNKNOWN"


def test_tb19_correct_hash_with_untrusted_custody_claim():
    c = case()
    forged = replace(c.presented[1], custody_domain_label="CLAIMED-INDEPENDENT")
    forged = replace(forged, test_control_digest=witness.envelope_digest(forged))
    r = verify(replace(c, presented=(c.presented[0], forged)))
    assert inspection(r, "B").checkpoint_correspondence.status == "MATCH"
    assert inspection(r, "B").snapshot_integrity.status == "MISMATCH"
    assert inspection(r, "B").authenticity.status == "UNKNOWN"


def test_tb20_report_is_not_evidence_or_same_entity_proof():
    r = verify(case())
    assert r.kind != "Evidence" and r.kind != "AuditResult"
    assert r.evidence_admission == "NOT_EVALUATED"
    assert r.entity_continuity == "UNKNOWN"
    assert not hasattr(r, "admitted_evidence")


def test_duplicate_roles_or_unregistered_identity_is_invalid():
    c = case()
    duplicate = replace(c.presented[1], role="A")
    duplicate = replace(duplicate, test_control_digest=witness.envelope_digest(duplicate))
    assert verify(replace(c, presented=(c.presented[0], duplicate))).aggregate_verdict == "INVALID_INPUT"


def test_result_is_deterministic_and_bound_to_laboratory_scope():
    c = case()
    assert verify(c) == verify(c)
    assert verify(c).independence_basis == "ASSUMED_FOR_EXPERIMENT"


def test_same_checkpoint_under_two_witness_labels_cannot_double_count():
    fake_b = envelope("B", C4_A, C2_A)
    r = verify(case(b=fake_b))
    assert r.aggregate_verdict == "INVALID_INPUT"
    assert "FROZEN_CHECKPOINT_IDENTITY_ROLE_MISMATCH" in r.reason_codes
