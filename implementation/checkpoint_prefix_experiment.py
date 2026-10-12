"""Bounded synthetic prefix comparison; no signing, admission, or M0 integration.

The caller supplies an immutable test oracle assumed to have been preserved
outside candidate control. This module does not establish that independence.
Checkpoint self-digests and symbolic descriptor hashes authenticate no signer.
PASS describes only correspondence to that conditional oracle, not history.
"""

from dataclasses import dataclass, field
import hashlib
import json
import re


PROFILE = "ARIO-PREFIX-EXPERIMENT-0.1"
DOMAIN = "SYNTHETIC_CHECKPOINT_CORRESPONDENCE"
SYMBOLIC_KEY_A = b"TEST-KEY-A:SYMBOLIC:v0.1"
SYMBOLIC_KEY_B = b"TEST-KEY-B:SYMBOLIC:v0.1"
MAX_LEDGER_BYTES = 65536
MAX_CHECKPOINT_BYTES = 4096
MAX_RECORDS = 4
MAX_ORACLE_CHECKPOINTS = 8
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_RECORD_KEYS = {"record_id", "observed_at", "payload", "previous_sha256", "sha256"}
_PAYLOAD_KEYS = {"claim_id", "node_id", "value"}
_CHECKPOINT_KEYS = {
    "profile", "domain", "ledger_id", "epoch", "branch_id", "record_count",
    "prefix_byte_count", "prefix_sha256", "head_sha256",
    "previous_checkpoint_sha256", "test_identity", "key_descriptor_sha256",
    "checkpoint_sha256",
}


@dataclass(frozen=True)
class Context:
    """Externally chosen test scope; labels confer no domain authority."""

    ledger_id: str
    epoch: str
    branch_id: str
    domain: str = DOMAIN


@dataclass(frozen=True)
class OracleSnapshot:
    """Test-control inputs, never inferred from a candidate or local summary."""

    checkpoints: tuple[bytes, ...]
    key_bindings: tuple[tuple[str, bytes], ...] = (("TEST-KEEPER-A", SYMBOLIC_KEY_A),)
    known_floor: int | None = 4


@dataclass(frozen=True)
class Finding:
    status: str
    reason: str


@dataclass(frozen=True)
class ComparisonResult:
    property_verdict: str
    local_hash_validity: Finding
    prefix_correspondence: Finding
    checkpoint_binding: Finding
    symbolic_descriptor_binding: Finding
    known_checkpoint_floor: Finding
    oracle_evidence: Finding
    conflict: bool
    candidate_record_count: int | None
    compared_record_count: int | None
    kind: str = field(default="EXPERIMENTAL_PREFIX_COMPARISON", init=False)
    independence_basis: str = field(default="ASSUMED_FOR_EXPERIMENT", init=False)
    signature_validity: str = field(default="NOT_CHECKED", init=False)
    human_authorization: str = field(default="NOT_EVALUATED", init=False)
    evidence_admission: str = field(default="NOT_EVALUATED", init=False)
    historical_event_truth: str = field(default="UNKNOWN", init=False)
    entity_continuity: str = field(default="UNKNOWN", init=False)
    ontological_continuity: str = field(default="UNKNOWN", init=False)
    production_historical_continuity: str = field(default="INCONCLUSIVE", init=False)


class _Invalid(ValueError):
    def __init__(self, reason, status="MISMATCH"):
        super().__init__(reason)
        self.reason = reason
        self.status = status


def _canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("ascii")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _text(value, limit=128):
    return (
        type(value) is str and 0 < len(value) <= limit
        and all(32 <= ord(character) <= 126 for character in value)
    )


def _hex(value):
    return type(value) is str and _HEX.fullmatch(value) is not None


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise _Invalid("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _integer(text):
    if len(text) > 10:
        raise _Invalid("OVERSIZED_INTEGER")
    return int(text)


def _noninteger(_value):
    raise _Invalid("NONINTEGER_JSON_NUMBER")


def _json(raw, limit):
    if type(raw) is not bytes or not 0 < len(raw) <= limit:
        raise _Invalid("INVALID_OR_OVERSIZED_SERIALIZATION")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise _Invalid("NON_ASCII_SERIALIZATION") from exc
    depth = 0
    quoted = False
    escaped = False
    for character in text:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in "[{":
            depth += 1
            if depth > 8:
                raise _Invalid("EXCESSIVE_JSON_DEPTH")
        elif character in "]}":
            depth -= 1
            if depth < 0:
                raise _Invalid("MALFORMED_JSON")
    try:
        value = json.loads(
            text, object_pairs_hook=_pairs, parse_int=_integer,
            parse_float=_noninteger, parse_constant=_noninteger,
        )
    except (ValueError, RecursionError) as exc:
        if isinstance(exc, _Invalid):
            raise
        raise _Invalid("MALFORMED_JSON") from exc
    try:
        canonical = _canonical(value)
    except (UnicodeEncodeError, ValueError, TypeError, RecursionError) as exc:
        raise _Invalid("INVALID_JSON_VALUE") from exc
    if raw != canonical:
        raise _Invalid("NONCANONICAL_SERIALIZATION")
    if type(value) is not dict:
        raise _Invalid("EXPECTED_JSON_OBJECT")
    return value


def _ledger(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_LEDGER_BYTES:
        raise _Invalid("INVALID_OR_OVERSIZED_LEDGER")
    if not raw.endswith(b"\n") or b"\r" in raw:
        raise _Invalid("INVALID_RECORD_BOUNDARIES")
    lines = raw.split(b"\n")[:-1]
    if not 1 <= len(lines) <= MAX_RECORDS:
        raise _Invalid("INVALID_LEDGER_RECORD_COUNT")
    records = []
    offsets = []
    offset = 0
    previous = None
    valid = True
    for index, line in enumerate(lines):
        row = _json(line, MAX_LEDGER_BYTES)
        if set(row) != _RECORD_KEYS:
            raise _Invalid("INVALID_RECORD_FIELDS")
        if row["record_id"] != "ROW-" + str(index):
            raise _Invalid("INVALID_RECORD_ID_OR_ORDER")
        if not _text(row["observed_at"]):
            raise _Invalid("INVALID_OBSERVED_AT_TYPE")
        payload = row["payload"]
        expected_payload = _PAYLOAD_KEYS | (
            {"lineage_from", "lineage_to"} if index else set()
        )
        if type(payload) is not dict or set(payload) != expected_payload:
            raise _Invalid("INVALID_PAYLOAD_FIELDS")
        if any(not _text(value, 512) for value in payload.values()):
            raise _Invalid("INVALID_PAYLOAD_TYPE")
        link = row["previous_sha256"]
        if (index == 0 and link is not None) or (index and not _hex(link)):
            raise _Invalid("INVALID_PREVIOUS_HASH_TYPE")
        if not _hex(row["sha256"]):
            raise _Invalid("INVALID_RECORD_HASH_TYPE")
        body = {key: value for key, value in row.items() if key != "sha256"}
        valid = valid and link == previous and _sha(_canonical(body)) == row["sha256"]
        previous = row["sha256"]
        offset += len(line) + 1
        offsets.append(offset)
        records.append(row)
    return records, offsets, Finding(
        "MATCH" if valid else "MISMATCH",
        "LOCAL_HASH_CHAIN_CONSISTENT" if valid else "LOCAL_HASH_CHAIN_INVALID",
    )


def _checkpoint(raw):
    cp = _json(raw, MAX_CHECKPOINT_BYTES)
    if set(cp) != _CHECKPOINT_KEYS:
        raise _Invalid("INVALID_CHECKPOINT_FIELDS")
    if not _text(cp["profile"]):
        raise _Invalid("INVALID_PROFILE_TYPE")
    if cp["profile"] != PROFILE:
        raise _Invalid("UNSUPPORTED_PROFILE", "UNKNOWN")
    for key in ("domain", "ledger_id", "epoch", "branch_id", "test_identity"):
        if not _text(cp[key]):
            raise _Invalid("INVALID_CHECKPOINT_CONTEXT_TYPE")
    if type(cp["record_count"]) is not int or cp["record_count"] not in (2, 4):
        raise _Invalid("INVALID_CHECKPOINT_RECORD_COUNT")
    if (
        type(cp["prefix_byte_count"]) is not int
        or not 1 <= cp["prefix_byte_count"] <= MAX_LEDGER_BYTES
    ):
        raise _Invalid("INVALID_PREFIX_BYTE_COUNT")
    for key in (
        "prefix_sha256", "head_sha256", "key_descriptor_sha256", "checkpoint_sha256",
    ):
        if not _hex(cp[key]):
            raise _Invalid("INVALID_CHECKPOINT_DIGEST_TYPE")
    parent = cp["previous_checkpoint_sha256"]
    if cp["record_count"] == 2:
        if parent is not None:
            raise _Invalid("INVALID_COUNT2_PARENT")
    elif not _hex(parent):
        raise _Invalid("INVALID_COUNT4_PARENT")
    body = {key: value for key, value in cp.items() if key != "checkpoint_sha256"}
    if _sha(_canonical(body)) != cp["checkpoint_sha256"]:
        raise _Invalid("CHECKPOINT_SELF_DIGEST_MISMATCH")
    return cp


def _scope(cp):
    return tuple(cp[key] for key in ("domain", "ledger_id", "epoch", "branch_id"))


def _commitment(cp):
    return tuple(cp[key] for key in (
        "prefix_byte_count", "prefix_sha256", "head_sha256",
        "previous_checkpoint_sha256",
    ))


def compare_prefix(
    candidate_bytes: bytes | None,
    declared_checkpoint_bytes: bytes | None,
    oracle_snapshot: OracleSnapshot | None,
    context: Context | None,
    *,
    candidate_key_descriptor: bytes | None = None,
) -> ComparisonResult:
    """Compare original byte prefixes under explicit synthetic oracle assumptions.

    The verdict concerns the declared prefix only. Local validity and the known
    checkpoint floor are independent findings, never evidence of event truth.
    Missing/invalid oracle configuration yields UNKNOWN, never an invented anchor.
    Candidate declarations cannot add checkpoints to the supplied oracle.
    Context, symbolic enrollment, and the floor must come from test control,
    never from candidate data. Scope labels have no additional semantics.
    Meeting a supplied floor proves neither freshness nor global latestness.
    """

    unknown = Finding("UNKNOWN", "NOT_ESTABLISHED")
    local = prefix = binding = descriptor = floor = evidence = unknown
    candidate_count = compared_count = None
    records = offsets = declared = None
    conflict = False

    def finish():
        required = (prefix, binding, descriptor, evidence)
        if any(item.status == "MISMATCH" for item in required):
            verdict = "FAIL"
        elif all(item.status == "MATCH" for item in required):
            verdict = "PASS"
        else:
            verdict = "INCONCLUSIVE"
        return ComparisonResult(
            verdict, local, prefix, binding, descriptor, floor, evidence,
            conflict, candidate_count, compared_count,
        )

    if candidate_bytes is None:
        local = prefix = Finding("UNKNOWN", "MISSING_CANDIDATE")
    else:
        try:
            records, offsets, local = _ledger(candidate_bytes)
            candidate_count = len(records)
        except _Invalid as exc:
            local = prefix = Finding(exc.status, exc.reason)
    if declared_checkpoint_bytes is None:
        binding = Finding("UNKNOWN", "MISSING_DECLARED_CHECKPOINT")
    else:
        try:
            declared = _checkpoint(declared_checkpoint_bytes)
            compared_count = declared["record_count"]
        except _Invalid as exc:
            binding = Finding(exc.status, exc.reason)
    if type(context) is not Context or any(
        not _text(value) for value in (
            context.ledger_id, context.epoch, context.branch_id, context.domain,
        )
    ):
        evidence = Finding("UNKNOWN", "MISSING_OR_INVALID_CONTEXT")
        return finish()
    scope = (context.domain, context.ledger_id, context.epoch, context.branch_id)
    if type(oracle_snapshot) is not OracleSnapshot:
        evidence = Finding("UNKNOWN", "MISSING_OR_INVALID_ORACLE")
        return finish()
    if (
        type(oracle_snapshot.checkpoints) is not tuple
        or not 1 <= len(oracle_snapshot.checkpoints) <= MAX_ORACLE_CHECKPOINTS
        or type(oracle_snapshot.key_bindings) is not tuple
        or not 0 <= len(oracle_snapshot.key_bindings) <= 2
        or (
            oracle_snapshot.known_floor is not None
            and (
                type(oracle_snapshot.known_floor) is not int
                or oracle_snapshot.known_floor not in (2, 4)
            )
        )
    ):
        evidence = Finding("UNKNOWN", "MISSING_OR_INVALID_ORACLE_CONFIGURATION")
        return finish()
    pins = {}
    for pair in oracle_snapshot.key_bindings:
        if (
            type(pair) is not tuple or len(pair) != 2 or not _text(pair[0])
            or type(pair[1]) is not bytes
            or pair[1] not in (SYMBOLIC_KEY_A, SYMBOLIC_KEY_B) or pair[0] in pins
        ):
            evidence = Finding("UNKNOWN", "INVALID_SYMBOLIC_ENROLLMENT_CONFIGURATION")
            return finish()
        pins[pair[0]] = pair[1]
    admitted = []
    for raw in oracle_snapshot.checkpoints:
        try:
            admitted.append(_checkpoint(raw))
        except _Invalid:
            evidence = Finding("UNKNOWN", "INVALID_OR_UNSUPPORTED_ORACLE_CHECKPOINT")
            return finish()
    scoped = [cp for cp in admitted if _scope(cp) == scope]
    for count in (2, 4):
        commitments = {_commitment(cp) for cp in scoped if cp["record_count"] == count}
        if len(commitments) > 1:
            conflict = True
            evidence = Finding("UNKNOWN", "CONFLICTING_ORACLE_CHECKPOINTS")
            return finish()
    if declared is None:
        evidence = Finding("UNKNOWN", "NO_COMPARABLE_DECLARATION")
        return finish()
    matches = [cp for cp in scoped if cp["record_count"] == compared_count]
    if not matches:
        evidence = Finding("UNKNOWN", "MISSING_INDEPENDENT_CHECKPOINT")
        if _scope(declared) != scope:
            binding = Finding("MISMATCH", "DECLARED_SCOPE_REPLAY")
        return finish()
    evidence = Finding("MATCH", "UNIQUE_ORACLE_COMMITMENT_ASSUMED_PRESERVED")
    exact = [cp for cp in matches if cp == declared]
    target = exact[0] if exact else matches[0]
    if _scope(declared) != scope:
        binding = Finding("MISMATCH", "DECLARED_SCOPE_REPLAY")
    elif not exact:
        binding = Finding("MISMATCH", "DECLARED_CHECKPOINT_NOT_ORACLE_ADMITTED")
    else:
        binding = Finding("MATCH", "EXACT_DECLARED_CHECKPOINT_BINDING")
    if compared_count == 4:
        parents = [cp for cp in scoped if cp["record_count"] == 2]
        if not parents:
            evidence = Finding("UNKNOWN", "MISSING_INDEPENDENT_COUNT2_PARENT")
        elif target["previous_checkpoint_sha256"] not in {
            cp["checkpoint_sha256"] for cp in parents
        }:
            evidence = Finding("MISMATCH", "ORACLE_PARENT_BINDING_MISMATCH")
    if records is not None:
        if candidate_count < compared_count:
            prefix = Finding("MISMATCH", "CANDIDATE_SHORTER_THAN_CHECKPOINT")
        else:
            original_prefix = candidate_bytes[:offsets[compared_count - 1]]
            correspondence = (
                len(original_prefix) == target["prefix_byte_count"]
                and _sha(original_prefix) == target["prefix_sha256"]
                and records[compared_count - 1]["sha256"] == target["head_sha256"]
            )
            prefix = Finding(
                "MATCH" if correspondence else "MISMATCH",
                "ORIGINAL_PREFIX_CORRESPONDS" if correspondence
                else "ORIGINAL_PREFIX_DIFFERS",
            )
    if candidate_key_descriptor is None:
        descriptor = Finding("UNKNOWN", "MISSING_SYMBOLIC_DESCRIPTOR")
    elif (
        type(candidate_key_descriptor) is not bytes
        or candidate_key_descriptor not in (SYMBOLIC_KEY_A, SYMBOLIC_KEY_B)
    ):
        descriptor = Finding("MISMATCH", "INVALID_SYMBOLIC_TEST_DESCRIPTOR")
    else:
        pin = pins.get(declared["test_identity"])
        if pin is None:
            descriptor = Finding("UNKNOWN", "MISSING_SYMBOLIC_IDENTITY_PIN")
        else:
            bound = (
                candidate_key_descriptor == pin
                and declared["test_identity"] == target["test_identity"]
                and declared["key_descriptor_sha256"] == _sha(pin)
                and target["key_descriptor_sha256"] == _sha(pin)
            )
            descriptor = Finding(
                "MATCH" if bound else "MISMATCH",
                "SYMBOLIC_DESCRIPTOR_BOUND" if bound
                else "SYMBOLIC_DESCRIPTOR_SUBSTITUTION",
            )
    known_floor = oracle_snapshot.known_floor
    if known_floor is None:
        floor = Finding("UNKNOWN", "NO_KNOWN_CHECKPOINT_FLOOR")
    elif compared_count < known_floor or (
        candidate_count is not None and candidate_count < known_floor
    ):
        floor = Finding("MISMATCH", "BELOW_KNOWN_CHECKPOINT_FLOOR")
    elif all(item.status == "MATCH" for item in (prefix, binding, descriptor, evidence)):
        floor = Finding("MATCH", "CORRESPONDING_CHECKPOINT_MEETS_KNOWN_FLOOR")
    else:
        floor = Finding("UNKNOWN", "FLOOR_NOT_ESTABLISHED_BY_CORRESPONDENCE")
    return finish()
