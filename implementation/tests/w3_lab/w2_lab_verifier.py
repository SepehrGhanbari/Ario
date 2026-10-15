"""W2-DRAFT-0.1: NON-PRODUCTION, SYNTHETIC-ONLY security boundary laboratory.

This is deliberately NOT a trusted source verifier, not M0, and not an
implementation of EA/ARP/RAC/TA. The separate oracle is INJECTED by tests
and must never be treated as a genuine external trust authority. No keys,
network, files, credentials, historical ledgers or evidence admission.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from collections.abc import Mapping
import json
import re

MAX_PAYLOAD = 1024 * 1024
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class Source:
    label: str
    locator: str
    claimed_digest: str
    custodian: str
    root: str
    parents: tuple[str, ...] | None
    claim_id: str
    scope: str
    use: str
    audience: str
    epoch: str
    # Present for attack scenarios, deliberately NOT used as verified proof.
    signature_claim: str = "SELF_DECLARED_SIGNATURE"


@dataclass(frozen=True)
class SourceBinding:
    """Out-of-band synthetic oracle assertion, NOT a real signature check."""
    actual_digest: str
    custodian: str
    root: str
    parents: tuple[str, ...] | None
    claim_id: str
    scope: str
    use: str
    audience: str
    epoch: str


@dataclass(frozen=True)
class ReviewGrant:
    reviewer: str
    allowed_action: str
    claim_id: str
    scope: str
    audience: str
    epoch: str
    not_before: int
    not_after: int
    bound_candidate_digest: str


@dataclass(frozen=True)
class Request:
    sources: tuple[Source, ...]
    reviewer: str
    proposer: str
    grant_id: str
    action: str
    claim_id: str
    scope: str
    use: str
    audience: str
    epoch: str
    policy: str = "W2-LAB-0.1"


@dataclass(frozen=True)
class SyntheticOracles:
    """All fields are test-only assumptions supplied OUTSIDE untrusted request."""
    payload_store: Mapping[str, bytes]
    authenticated_sources: Mapping[str, SourceBinding]
    externally_enrolled_roots: frozenset[str]
    review_grants: Mapping[str, ReviewGrant]
    revocation: Mapping[str, str]
    trusted_now: int | None


@dataclass(frozen=True)
class Result:
    status: str
    reason: str
    admission_decision: str = "NOT_EVALUATED"
    claim_truth: str = "UNKNOWN"
    source_authentication: str = "NOT_ESTABLISHED_IN_PRODUCTION"


def mock_candidate_digest(request: Request) -> str:
    """LAB-ONLY deterministic dossier binding, not a signed canonical format."""
    raw = json.dumps(asdict(request), sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("ascii")
    return sha256(b"W2-LAB-CANDIDATE-0.1\x00" + raw).hexdigest()


def _out(status: str, reason: str) -> Result:
    assert status in {"UNKNOWN", "REJECTED", "LAB_REVIEWABLE_ONLY"}
    return Result(status, reason)


def _bounded_parents(parents: object) -> bool:
    """Require a declared tuple of concrete, bounded typed-parent identifiers.

    This is input shape validation only, not actual historical ancestry proof.
    """
    return (isinstance(parents, tuple) and len(parents) <= 64
            and all(isinstance(x, str) and bool(x.strip())
                    and len(x.encode("utf-8")) <= 128 for x in parents))


def inspect(request: Request, oracle: SyntheticOracles) -> Result:
    """Test fake boundary assumptions, never grant any real-world authority."""
    if request.policy != "W2-LAB-0.1":
        return _out("REJECTED", "UNKNOWN_POLICY")
    if request.action != "REVIEW_CANDIDATE":
        return _out("REJECTED", "ACTION_NOT_ALLOWED")
    if request.reviewer == request.proposer:
        return _out("REJECTED", "SELF_REVIEW")
    # An exact role collision can be refused using caller declarations; differing
    # labels still do NOT establish genuinely independent human controllers.
    if any(request.reviewer == src.custodian for src in request.sources):
        return _out("REJECTED", "REVIEWER_SOURCE_CONFLICT")
    if not request.sources or len(request.sources) > 8:
        return _out("REJECTED", "SOURCE_COUNT_INVALID")
    if not all((request.claim_id, request.scope, request.use,
                request.audience, request.epoch)):
        return _out("REJECTED", "REVIEW_TARGET_INCOMPLETE")

    verified_bindings: list[SourceBinding] = []
    observed_digests: list[str] = []
    # Immutable bytes inspected during this invocation. Never re-read a
    # caller-controlled locator for downstream interpretation: the mapping
    # may change between reads (synthetic TOCTOU/split-view attack).
    verified_payloads: dict[str, bytes] = {}
    for source in request.sources:
        if ((source.claim_id, source.scope, source.use, source.audience, source.epoch)
                != (request.claim_id, request.scope, request.use, request.audience,
                    request.epoch)):
            return _out("REJECTED", "SOURCE_TARGET_SCOPE_MISMATCH")
        if source.parents is None:
            return _out("UNKNOWN", "ANCESTRY_OMITTED")
        if not _bounded_parents(source.parents):
            return _out("REJECTED", "SOURCE_ANCESTRY_MALFORMED")
        if not isinstance(source.claimed_digest, str) or not DIGEST.fullmatch(source.claimed_digest):
            return _out("REJECTED", "DIGEST_FORMAT_INVALID")
        if source.locator in verified_payloads:
            raw = verified_payloads[source.locator]
        else:
            raw = oracle.payload_store.get(source.locator)
            if raw is None:
                return _out("UNKNOWN", "PAYLOAD_NOT_RETRIEVABLE")
            if not isinstance(raw, bytes) or len(raw) > MAX_PAYLOAD:
                return _out("REJECTED", "PAYLOAD_TYPE_OR_SIZE_INVALID")
            verified_payloads[source.locator] = raw
        actual = sha256(raw).hexdigest()
        observed_digests.append(actual)
        if actual != source.claimed_digest:
            return _out("REJECTED", "PAYLOAD_DIGEST_MISMATCH")
        certified = oracle.authenticated_sources.get(source.locator)
        if certified is None:
            return _out("UNKNOWN", "SOURCE_BINDING_MISSING")
        if certified.root not in oracle.externally_enrolled_roots:
            return _out("UNKNOWN", "SOURCE_ROOT_UNTRUSTED")
        if certified.parents is None:
            return _out("UNKNOWN", "SOURCE_ANCESTRY_NOT_ESTABLISHED")
        if not _bounded_parents(certified.parents):
            return _out("UNKNOWN", "SOURCE_ANCESTRY_UNVERIFIABLE")
        if (certified.actual_digest, certified.custodian, certified.root, certified.parents,
            certified.claim_id, certified.scope, certified.use,
            certified.audience, certified.epoch) != (
            actual, source.custodian, source.root, source.parents,
            request.claim_id, request.scope, request.use,
            request.audience, request.epoch
        ):
            return _out("REJECTED", "SOURCE_BINDING_MISMATCH")
        verified_bindings.append(certified)

    # A textual label/digest does not authenticate independent ancestry.
    # Even distinct payload hashes can share a common custody/source root.
    if len(verified_bindings) > 1:
        roots = [set((b.root, *b.parents)) for b in verified_bindings]
        if any(roots[i] & roots[j] for i in range(len(roots))
               for j in range(i + 1, len(roots))):
            return _out("UNKNOWN", "SHARED_ANCESTRY_NOT_INDEPENDENT")
        # Maintain the original explicit ancestry reason-code precedence.
        # Distinct source roots still do not create independent controllers
        # when the same custodian is declared for both source bindings.
        if len({b.custodian for b in verified_bindings}) < len(verified_bindings):
            return _out("UNKNOWN", "SHARED_CUSTODIAN_NOT_INDEPENDENT")
        if len(set(observed_digests)) < len(observed_digests):
            # Identical bytes alone do not PROVE a common origin. We merely
            # decline to infer independent corroboration without more proof.
            return _out("UNKNOWN", "IDENTICAL_PAYLOAD_INDEPENDENCE_UNPROVEN")

    grant = oracle.review_grants.get(request.grant_id)
    if grant is None:
        return _out("UNKNOWN", "REVIEW_GRANT_UNVERIFIED")
    if (grant.reviewer, grant.claim_id, grant.scope, grant.audience,
        grant.epoch) != (request.reviewer, request.claim_id,
                         request.scope, request.audience, request.epoch):
        return _out("REJECTED", "GRANT_SCOPE_OR_PRINCIPAL_MISMATCH")
    if grant.allowed_action != "REVIEW_CANDIDATE":
        return _out("REJECTED", "GRANT_ACTION_FORBIDDEN")
    if grant.bound_candidate_digest != mock_candidate_digest(request):
        return _out("REJECTED", "REVIEW_GRANT_CANDIDATE_BINDING_MISMATCH")
    revocation = oracle.revocation.get(request.grant_id)
    if revocation == "REVOKED":
        return _out("REJECTED", "GRANT_REVOKED")
    if revocation != "FRESH_ACTIVE":
        return _out("UNKNOWN", "REVOCATION_FRESHNESS_UNVERIFIED")
    if oracle.trusted_now is None:
        return _out("UNKNOWN", "TRUSTED_CLOCK_UNAVAILABLE")
    if not grant.not_before <= oracle.trusted_now <= grant.not_after:
        return _out("REJECTED", "REVIEW_GRANT_EXPIRED_OR_NOT_YET_VALID")

    # For the explicitly scoped *laboratory* JSON-report fixture only,
    # preserve contradictions in the same reported field. This is not
    # historical truth adjudication or arbitrary semantic equivalence.
    if len(request.sources) > 1:
        values: list[str] = []
        events: list[str] = []
        for source in request.sources:
            try:
                reported = parse_strict_metadata(verified_payloads[source.locator])
            except (ValueError, UnicodeError, KeyError):
                return _out("UNKNOWN", "REPORT_CONTENT_NOT_COMPARABLE")
            event = reported.get("event")
            if not isinstance(event, str) or not event.strip():
                return _out("UNKNOWN", "EVENT_TYPE_UNAVAILABLE")
            events.append(event)
            value = reported.get("reported_status")
            if not isinstance(value, str):
                return _out("UNKNOWN", "REPORT_STATUS_UNAVAILABLE")
            values.append(value)
        # Only EXACT event-type equality is modeled in this laboratory.
        # Matching status strings for different events prove nothing.
        if len(set(events)) > 1:
            return _out("UNKNOWN", "EVENT_TYPE_MISMATCH")
        if len(set(values)) > 1:
            return _out("UNKNOWN", "CONFLICTING_REPORTED_STATUSES")

    # This ONLY says injected lab assumptions were internally consistent.
    return _out("LAB_REVIEWABLE_ONLY", "MOCK_ONLY_NO_AUTHORITY")


def parse_strict_metadata(raw: bytes) -> dict:
    """Optional *metadata* parser: exact duplicate-key and NaN rejection.

    Not a canonical serialization or signed-byte format. Payloads are hashed
    as original bytes, never reserialized through this parser.
    """
    if not isinstance(raw, bytes) or len(raw) > 16_384:
        raise ValueError("metadata size or type")
    def no_duplicate(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError("duplicate metadata key")
            obj[key] = value
        return obj
    def bad_constant(value):
        raise ValueError("nonstandard numeric constant: " + value)
    obj = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicate,
                     parse_constant=bad_constant)
    if not isinstance(obj, dict):
        raise ValueError("metadata root must be an object")
    return obj
