"""Synthetic prefix experiments; no signatures, file-backed ledgers, or truth claims."""

import copy
import hashlib
import json
from dataclasses import FrozenInstanceError, replace

import pytest

import checkpoint_prefix_experiment as experiment


PROFILE = "ARIO-PREFIX-EXPERIMENT-0.1"
KEY_A = b"TEST-KEY-A:SYMBOLIC:v0.1"
KEY_B = b"TEST-KEY-B:SYMBOLIC:v0.1"
SCOPE = {
    "domain": "SYNTHETIC_CHECKPOINT_CORRESPONDENCE",
    "ledger_id": "SYNTHETIC-LEDGER-001",
    "epoch": "TEST-EPOCH-001",
    "branch_id": "TEST-BRANCH-A",
}
L2_SHA256 = "00a9c8f968a53e987e2c90b93eecf32186612d28bb12568bc608b59c13ef4e94"
L4_SHA256 = "3f9bf3fa7fe9b3b71113292e4fff2671545fdcc383260a15b4cc4275e89a9e72"
C2_BODY_SHA256 = "39391cd6c739caf10ea622f146c3501500ea905c20964cef05b2cc8ee4051f7e"
C4_BODY_SHA256 = "81b9cf87da4dd83ca86c69dc2e85041d1cf8d070c1c17d1e4df97735e9fcd606"

# These literal observations preserve the earlier two-row synthetic experiment.
# Fixture construction is independent of the comparator and has no file access.
BASE_ROWS = (
    {
        "record_id": "ROW-0", "observed_at": "2026-10-12T00:00:00Z",
        "payload": {
            "node_id": "NODE-A", "claim_id": "SYNTHETIC-CLAIM",
            "value": "original synthetic observation",
        },
    },
    {
        "record_id": "ROW-1", "observed_at": "2026-10-12T00:01:00Z",
        "payload": {
            "node_id": "NODE-B", "claim_id": "SYNTHETIC-CLAIM",
            "value": "synthetic successor",
            "lineage_from": "NODE-A", "lineage_to": "NODE-B",
        },
    },
    {
        "record_id": "ROW-2", "observed_at": "2026-10-12T00:02:00Z",
        "payload": {
            "node_id": "NODE-C", "claim_id": "SYNTHETIC-CLAIM",
            "value": "synthetic third record",
            "lineage_from": "NODE-B", "lineage_to": "NODE-C",
        },
    },
    {
        "record_id": "ROW-3", "observed_at": "2026-10-12T00:03:00Z",
        "payload": {
            "node_id": "NODE-D", "claim_id": "SYNTHETIC-CLAIM",
            "value": "synthetic fourth record",
            "lineage_from": "NODE-C", "lineage_to": "NODE-D",
        },
    },
)


def _canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")


def _sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _seal(rows):
    sealed = copy.deepcopy(rows)
    previous = None
    for row in sealed:
        row.pop("sha256", None)
        row["previous_sha256"] = previous
        row["sha256"] = _sha256(_canonical(row))
        previous = row["sha256"]
    return sealed


def _ledger(rows):
    return b"".join(_canonical(row) + b"\n" for row in rows)


def _rows(raw):
    return [json.loads(line) for line in raw.splitlines()]


def _commit_body(body):
    body = copy.deepcopy(body)
    body.pop("checkpoint_sha256", None)
    body["checkpoint_sha256"] = _sha256(_canonical(body))
    return _canonical(body)


def _checkpoint(rows, count, previous=None, key_descriptor=KEY_A):
    prefix = _ledger(rows[:count])
    return _commit_body({
        "profile": PROFILE,
        **SCOPE,
        "record_count": count,
        "prefix_byte_count": len(prefix),
        "prefix_sha256": _sha256(prefix),
        "head_sha256": rows[count - 1]["sha256"],
        "previous_checkpoint_sha256": previous,
        "test_identity": "TEST-KEEPER-A",
        "key_descriptor_sha256": _sha256(key_descriptor),
    })


SEALED_ROWS = _seal(BASE_ROWS)
L2 = _ledger(SEALED_ROWS[:2])
L4 = _ledger(SEALED_ROWS)
C2 = _checkpoint(SEALED_ROWS, 2)
C4 = _checkpoint(SEALED_ROWS, 4, C2_BODY_SHA256)
CONTEXT = experiment.Context(**SCOPE)
# Immutable bytes, tuples, and a frozen snapshot are retained before mutations.
ORACLE = experiment.OracleSnapshot(
    checkpoints=(C2, C4),
    key_bindings=(("TEST-KEEPER-A", KEY_A),),
    known_floor=4,
)


def _assert_epistemic_limits(result):
    expected = {
        "signature_validity": "NOT_CHECKED",
        "human_authorization": "NOT_EVALUATED",
        "evidence_admission": "NOT_EVALUATED",
        "historical_event_truth": "UNKNOWN",
        "entity_continuity": "UNKNOWN",
        "ontological_continuity": "UNKNOWN",
        "production_historical_continuity": "INCONCLUSIVE",
    }
    for field, value in expected.items():
        assert getattr(result, field) == value
    assert result.property_verdict in {"PASS", "FAIL", "INCONCLUSIVE"}
    assert type(result.conflict) is bool
    for field in (
        "local_hash_validity", "prefix_correspondence", "checkpoint_binding",
        "symbolic_descriptor_binding", "known_checkpoint_floor", "oracle_evidence",
    ):
        finding = getattr(result, field)
        assert finding.status in {"MATCH", "MISMATCH", "UNKNOWN", "NOT_CHECKED"}
        assert isinstance(finding.reason, str) and finding.reason.strip()


def _compare(candidate=L4, declared=C4, oracle=ORACLE, context=CONTEXT, descriptor=KEY_A):
    result = experiment.compare_prefix(
        candidate, declared, oracle, context,
        candidate_key_descriptor=descriptor,
    )
    _assert_epistemic_limits(result)
    return result


def _late_rewrite():
    rows = _rows(L4)
    rows[2]["payload"]["value"] = "rewritten synthetic third record"
    return _seal(rows)


def test_independent_fixture_goldens():
    assert experiment.PROFILE == PROFILE
    assert experiment.SYMBOLIC_KEY_A == KEY_A
    assert experiment.SYMBOLIC_KEY_B == KEY_B
    assert len(L2) == 615 and _sha256(L2) == L2_SHA256
    assert len(L4) == 1334 and _sha256(L4) == L4_SHA256
    assert json.loads(C2)["checkpoint_sha256"] == C2_BODY_SHA256
    assert json.loads(C4)["checkpoint_sha256"] == C4_BODY_SHA256
    assert _sha256(C2) == "0ee1676e5c428599bf66e0a248c75be3dcbd91a63e3a58f4dc47c50d1c4e5c01"
    assert _sha256(C4) == "cfe82d497f0751202fd31bad4cb5b6db6ba3cf54c08e3c7f88ed1ab33df024a8"
    assert json.loads(C4)["previous_checkpoint_sha256"] == C2_BODY_SHA256
    assert SEALED_ROWS[2]["sha256"] == "1e732e1f9071f6ef86d3d582ed43384bf91b8ff0056c6d8501add684c1401a52"
    assert SEALED_ROWS[3]["sha256"] == "8e4542172577406d577cad48bc8d25ed884710beceeb00b44e335faef2d89f60"


def test_original_l4_matches_frozen_c4_only_as_synthetic_property():
    result = _compare()
    assert result.property_verdict == "PASS"
    assert result.conflict is False
    assert result.candidate_record_count == result.compared_record_count == 4
    for field in (
        "local_hash_validity", "prefix_correspondence", "checkpoint_binding",
        "symbolic_descriptor_binding", "known_checkpoint_floor", "oracle_evidence",
    ):
        assert getattr(result, field).status == "MATCH"


def test_l4_with_c2_matches_prefix_but_violates_known_floor():
    result = _compare(declared=C2)
    assert result.property_verdict == "PASS"
    assert result.local_hash_validity.status == "MATCH"
    assert result.prefix_correspondence.status == "MATCH"
    assert result.checkpoint_binding.status == "MATCH"
    assert result.symbolic_descriptor_binding.status == "MATCH"
    assert result.known_checkpoint_floor.status == "MISMATCH"
    assert result.candidate_record_count == 4
    assert result.compared_record_count == 2


def test_early_rewrite_rehashes_locally_but_fails_frozen_prefix():
    rows = _rows(L4)
    rows[0]["payload"]["value"] = "rewritten synthetic observation"
    candidate = _ledger(_seal(rows))
    result = _compare(candidate=candidate)
    assert _sha256(candidate) != L4_SHA256
    assert result.local_hash_validity.status == "MATCH"
    assert result.prefix_correspondence.status == "MISMATCH"
    assert result.checkpoint_binding.status == "MATCH"
    assert result.property_verdict == "FAIL"
    assert ORACLE.checkpoints == (C2, C4)


def test_later_rewrite_preserves_c2_but_fails_c4():
    rows = _late_rewrite()
    candidate = _ledger(rows)
    assert _ledger(rows[:2]) == L2
    earlier = _compare(candidate=candidate, declared=C2)
    assert earlier.property_verdict == "PASS"
    assert earlier.prefix_correspondence.status == "MATCH"
    assert earlier.known_checkpoint_floor.status == "MISMATCH"
    latest = _compare(candidate=candidate)
    assert latest.local_hash_validity.status == "MATCH"
    assert latest.prefix_correspondence.status == "MISMATCH"
    assert latest.property_verdict == "FAIL"


@pytest.mark.parametrize("substitute_commitment", [False, True], ids=["descriptor-only", "retained-A-label"])
def test_symbolic_descriptor_substitution_cannot_use_the_A_identity_label(substitute_commitment):
    declared = (
        _checkpoint(SEALED_ROWS, 4, C2_BODY_SHA256, key_descriptor=KEY_B)
        if substitute_commitment else C4
    )
    assert json.loads(declared)["test_identity"] == "TEST-KEEPER-A"
    result = _compare(declared=declared, descriptor=KEY_B)
    assert result.local_hash_validity.status == "MATCH"
    assert result.prefix_correspondence.status == "MATCH"
    assert result.symbolic_descriptor_binding.status == "MISMATCH"
    assert result.checkpoint_binding.status == ("MISMATCH" if substitute_commitment else "MATCH")
    assert result.conflict is False
    assert result.property_verdict == "FAIL"


def test_rollback_l2_c2_preserves_correspondence_but_violates_floor():
    result = _compare(candidate=L2, declared=C2)
    assert result.property_verdict == "PASS"
    assert result.local_hash_validity.status == "MATCH"
    assert result.prefix_correspondence.status == "MATCH"
    assert result.known_checkpoint_floor.status == "MISMATCH"
    assert result.candidate_record_count == result.compared_record_count == 2


@pytest.mark.parametrize("field", ["ledger_id", "epoch", "branch_id", "domain"])
def test_checkpoint_replay_rejects_each_context_dimension(field):
    replay = replace(CONTEXT, **{field: "OTHER-" + getattr(CONTEXT, field)})
    result = _compare(context=replay)
    assert result.checkpoint_binding.status == "MISMATCH"
    assert result.property_verdict == "FAIL"
    assert result.conflict is False


@pytest.mark.parametrize("missing", ["candidate", "declared", "oracle", "context", "descriptor"])
def test_missing_inputs_remain_inconclusive(missing):
    result = _compare(**{missing: None})
    assert result.property_verdict == "INCONCLUSIVE"
    assert result.conflict is False
    if missing == "descriptor":
        assert result.prefix_correspondence.status == "MATCH"
        assert result.symbolic_descriptor_binding.status == "UNKNOWN"


def test_missing_oracle_checkpoint_is_unknown_even_with_a_declared_c4():
    snapshot = replace(ORACLE, checkpoints=(C2,))
    result = _compare(oracle=snapshot)
    assert result.oracle_evidence.status == "UNKNOWN"
    assert result.prefix_correspondence.status == "UNKNOWN"
    assert result.property_verdict == "INCONCLUSIVE"
    assert result.conflict is False


def test_two_valid_admitted_c4_commitments_in_one_scope_are_conflict():
    alternate = _checkpoint(_late_rewrite(), 4, C2_BODY_SHA256)
    assert json.loads(alternate)["checkpoint_sha256"] != C4_BODY_SHA256
    snapshot = replace(ORACLE, checkpoints=(C2, C4, alternate))
    result = _compare(oracle=snapshot)
    assert result.conflict is True
    assert result.property_verdict == "INCONCLUSIVE"
    assert result.prefix_correspondence.status == "UNKNOWN"


def test_attacker_declared_mismatch_does_not_create_oracle_conflict():
    declared = _checkpoint(_late_rewrite(), 4, C2_BODY_SHA256)
    result = _compare(declared=declared)
    assert result.local_hash_validity.status == "MATCH"
    assert result.prefix_correspondence.status == "MATCH"
    assert result.checkpoint_binding.status == "MISMATCH"
    assert result.conflict is False
    assert result.property_verdict == "FAIL"


def test_duplicate_identical_oracle_copies_do_not_manufacture_conflict():
    snapshot = replace(ORACLE, checkpoints=(C2, C2, C4, C4))
    result = _compare(oracle=snapshot)
    assert result.conflict is False
    assert result.oracle_evidence.status == "MATCH"
    assert result.property_verdict == "PASS"


def test_unsupported_oracle_data_is_unknown_not_positive_evidence():
    body = json.loads(C4)
    body["profile"] = "UNSUPPORTED-PROFILE"
    snapshot = replace(ORACLE, checkpoints=(C2, _commit_body(body)))
    result = _compare(oracle=snapshot)
    assert result.oracle_evidence.status == "UNKNOWN"
    assert result.prefix_correspondence.status == "UNKNOWN"
    assert result.property_verdict == "INCONCLUSIVE"
    assert result.conflict is False


def test_broken_local_hash_is_reported_separately():
    rows = _rows(L4)
    rows[3]["sha256"] = "0" * 64
    result = _compare(candidate=_ledger(rows))
    assert result.local_hash_validity.status == "MISMATCH"
    assert result.property_verdict == "FAIL"
    assert result.checkpoint_binding.status == "MATCH"
    assert result.conflict is False


def _malformed_candidate(kind):
    if kind == "malformed-json":
        return b"{not-json}\n"
    if kind == "duplicate-key":
        return L4.replace(b'"record_id":"ROW-0"', b'"record_id":"ROW-0","record_id":"ROW-0"', 1)
    if kind == "invalid-type":
        rows = _rows(L4)
        rows[0]["payload"]["value"] = True
        return _ledger(_seal(rows))
    if kind == "noncanonical":
        return L4.replace(b'"claim_id":', b'"claim_id": ', 1)
    if kind == "missing-final-lf":
        return L4[:-1]
    if kind == "bom":
        return b"\xef\xbb\xbf" + L4
    if kind == "extra-key":
        rows = _rows(L4)
        rows[0]["unrecognized"] = "no-schema-extension"
        return _ledger(_seal(rows))
    raise AssertionError(kind)


@pytest.mark.parametrize("kind", [
    "malformed-json", "duplicate-key", "invalid-type", "noncanonical",
    "missing-final-lf", "bom", "extra-key",
])
def test_strict_candidate_format_never_passes(kind):
    result = _compare(candidate=_malformed_candidate(kind))
    assert result.local_hash_validity.status == "MISMATCH"
    assert result.property_verdict == "FAIL"
    assert result.conflict is False


@pytest.mark.parametrize("kind", [
    "boolean-record-count", "out-of-bound-byte-count", "duplicate-key", "unsupported-profile",
])
def test_strict_checkpoint_format_never_passes(kind):
    body = json.loads(C4)
    if kind == "boolean-record-count":
        body["record_count"] = True
    elif kind == "out-of-bound-byte-count":
        body["prefix_byte_count"] = 65537
    elif kind == "unsupported-profile":
        body["profile"] = "UNSUPPORTED-PROFILE"
    declared = _commit_body(body)
    if kind == "duplicate-key":
        declared = declared.replace(b'"record_count":4', b'"record_count":4,"record_count":4')
    result = _compare(declared=declared)
    assert result.property_verdict == ("INCONCLUSIVE" if kind == "unsupported-profile" else "FAIL")
    assert result.checkpoint_binding.status != "MATCH"
    assert result.conflict is False


def test_public_context_snapshot_and_result_are_frozen():
    result = _compare()
    for obj, field, changed in (
        (CONTEXT, "branch_id", "MUTATED"),
        (ORACLE, "checkpoints", ()),
        (result, "property_verdict", "FAIL"),
    ):
        with pytest.raises(FrozenInstanceError):
            setattr(obj, field, changed)
    assert ORACLE.checkpoints == (C2, C4)


def test_c4_without_its_independent_c2_parent_is_inconclusive():
    snapshot = replace(ORACLE, checkpoints=(C4,))
    result = _compare(oracle=snapshot)
    assert result.prefix_correspondence.status == "MATCH"
    assert result.checkpoint_binding.status == "MATCH"
    assert result.oracle_evidence.status == "UNKNOWN"
    assert result.property_verdict == "INCONCLUSIVE"
    assert result.conflict is False


def test_resealed_admitted_c4_with_wrong_parent_digest_fails_oracle_binding():
    body = json.loads(C4)
    body["previous_checkpoint_sha256"] = "0" * 64
    wrong_parent = _commit_body(body)
    snapshot = replace(ORACLE, checkpoints=(C2, wrong_parent))
    result = _compare(declared=wrong_parent, oracle=snapshot)
    assert result.local_hash_validity.status == "MATCH"
    assert result.prefix_correspondence.status == "MATCH"
    assert result.checkpoint_binding.status == "MATCH"
    assert result.oracle_evidence.status == "MISMATCH"
    assert result.property_verdict == "FAIL"
    assert result.conflict is False


def test_broken_suffix_does_not_change_the_corresponding_c2_prefix():
    rows = _rows(L4)
    rows[3]["sha256"] = "0" * 64
    result = _compare(candidate=_ledger(rows), declared=C2)
    assert result.local_hash_validity.status == "MISMATCH"
    assert result.prefix_correspondence.status == "MATCH"
    assert result.checkpoint_binding.status == "MATCH"
    assert result.known_checkpoint_floor.status == "MISMATCH"
    assert result.property_verdict == "PASS"
    assert result.candidate_record_count == 4
    assert result.compared_record_count == 2


@pytest.mark.parametrize("count", [0, 1, 3, 5, -1, 2.0, "2"])
def test_checkpoint_record_count_accepts_only_supported_integer_counts(count):
    body = json.loads(C4)
    body["record_count"] = count
    result = _compare(declared=_commit_body(body))
    assert result.checkpoint_binding.status == "MISMATCH"
    assert result.property_verdict == "FAIL"
    assert result.conflict is False


@pytest.mark.parametrize("kind", [
    "ledger-too-large", "checkpoint-too-large", "oracle-at-cap", "oracle-over-cap",
])
def test_bounded_input_caps(kind):
    if kind == "ledger-too-large":
        result = _compare(candidate=b"x" * 65537)
        assert result.local_hash_validity.status == "MISMATCH"
        assert result.local_hash_validity.reason == "INVALID_OR_OVERSIZED_LEDGER"
        assert result.property_verdict == "FAIL"
    elif kind == "checkpoint-too-large":
        result = _compare(declared=b"x" * 4097)
        assert result.checkpoint_binding.status == "MISMATCH"
        assert result.checkpoint_binding.reason == "INVALID_OR_OVERSIZED_SERIALIZATION"
        assert result.property_verdict == "FAIL"
    else:
        count = 8 if kind == "oracle-at-cap" else 9
        snapshot = replace(ORACLE, checkpoints=(C2,) + (C4,) * (count - 1))
        result = _compare(oracle=snapshot)
        assert result.oracle_evidence.status == ("MATCH" if count == 8 else "UNKNOWN")
        assert result.property_verdict == ("PASS" if count == 8 else "INCONCLUSIVE")
    assert result.conflict is False


def _additional_invalid_candidate(kind):
    if kind == "excessive-depth":
        return b'{"nested":' + b"[" * 8 + b"0" + b"]" * 8 + b"}\n"
    if kind == "five-rows":
        rows = _rows(L4)
        rows.append({
            "record_id": "ROW-4", "observed_at": "2026-10-12T00:04:00Z",
            "payload": {
                "node_id": "NODE-E", "claim_id": "SYNTHETIC-CLAIM",
                "value": "synthetic fifth record",
                "lineage_from": "NODE-D", "lineage_to": "NODE-E",
            },
        })
        return _ledger(_seal(rows))
    if kind in {"oversized-integer", "float", "nan"}:
        rows = _rows(L4)
        rows[0]["payload"]["value"] = {
            "oversized-integer": 12345678901,
            "float": 1.5,
            "nan": float("nan"),
        }[kind]
        return _ledger(_seal(rows))
    if kind == "crlf":
        return L4.replace(b"\n", b"\r\n")
    if kind == "non-ascii":
        return L4.replace(b"original synthetic observation", b"\xc3\xa9", 1)
    raise AssertionError(kind)


@pytest.mark.parametrize("kind, reason", [
    ("excessive-depth", "EXCESSIVE_JSON_DEPTH"),
    ("five-rows", "INVALID_LEDGER_RECORD_COUNT"),
    ("oversized-integer", "OVERSIZED_INTEGER"),
    ("float", "NONINTEGER_JSON_NUMBER"),
    ("nan", "NONINTEGER_JSON_NUMBER"),
    ("crlf", "INVALID_RECORD_BOUNDARIES"),
    ("non-ascii", "NON_ASCII_SERIALIZATION"),
])
def test_additional_strict_candidate_boundaries(kind, reason):
    result = _compare(candidate=_additional_invalid_candidate(kind))
    assert result.local_hash_validity.status == "MISMATCH"
    assert result.local_hash_validity.reason == reason
    assert result.property_verdict == "FAIL"
    assert result.conflict is False


@pytest.mark.parametrize("kind", [
    "missing-identity-pin", "missing-enrolled-descriptor", "missing-binding-configuration",
])
def test_missing_symbolic_configuration_remains_unknown(kind):
    if kind == "missing-identity-pin":
        snapshot = replace(ORACLE, key_bindings=())
    elif kind == "missing-enrolled-descriptor":
        snapshot = replace(ORACLE, key_bindings=(("TEST-KEEPER-A", None),))
    else:
        snapshot = replace(ORACLE, key_bindings=None)
    result = _compare(oracle=snapshot)
    assert result.property_verdict == "INCONCLUSIVE"
    assert result.conflict is False
    if kind == "missing-identity-pin":
        assert result.prefix_correspondence.status == "MATCH"
        assert result.symbolic_descriptor_binding.status == "UNKNOWN"
    else:
        assert result.oracle_evidence.status == "UNKNOWN"
        assert result.symbolic_descriptor_binding.status == "UNKNOWN"


def test_passing_comparison_result_cannot_replace_an_oracle_snapshot():
    passed = _compare()
    assert passed.property_verdict == "PASS"
    result = _compare(oracle=passed)
    assert result.oracle_evidence.status == "UNKNOWN"
    assert result.prefix_correspondence.status == "UNKNOWN"
    assert result.property_verdict == "INCONCLUSIVE"
    assert result.conflict is False