"""Research-only, read-only claim/receipt support *proposal* view.

Not an evidence verifier, memory adapter, signer, authority, or historical
migration. A caller-proposed SUPPORTS relation never proves entailment.
Never calls SourceMonitoringGuard.evaluate_claim_promotion().
"""
from __future__ import annotations

from typing import Any

from core.source_monitoring import SourceAttribution, SourceType, VeracityState

CONTRACT_VERSION = "ario_claim_support_readonly_view_v0_1"
MAX_REGISTRY = 256
MAX_RECEIPTS = 16
MAX_ID_LENGTH = 128
RELATIONS = frozenset({"SUPPORTS", "CONTRADICTS", "UNRELATED", "UNKNOWN"})


def _report() -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "review_status": "UNKNOWN",
        "reason_code": None,
        "claimed_support_count": 0,
        "unique_receipt_count": 0,
        "independent_support_count": 0,
        "execution_integrity": "NOT_ASSESSED",
        "source_authenticity": "UNKNOWN",
        "semantic_support": "NOT_ASSESSED",
        "claim_assessment": "NOT_ASSESSED",
        "admission_decision": "NOT_EVALUATED",
        "reviewer_authorization": "NOT_ESTABLISHED",
        "memory_mutation": "NONE",
        "history_mutation": "NONE",
        "contract_adoption": "NOT_ADOPTED",
    }


def _id_ok(value: object) -> bool:
    return type(value) is str and 0 < len(value) <= MAX_ID_LENGTH and bool(value.strip())


def _ancestors(
    receipt_id: str,
    registry: dict[str, SourceAttribution],
    claim_id: str,
) -> tuple[set[str], str | None]:
    """Bounded, nonrecursive DFS detecting both self and multi-node cycles.

    All ancestors are *declared*. Even a cycle-free graph does not prove
    real-world custody, independence, or historical authenticity.
    """
    done: set[str] = set()
    active: set[str] = set()
    stack: list[tuple[str, bool]] = [(receipt_id, False)]
    while stack:
        if len(stack) > 2 * MAX_REGISTRY:
            return done, "ANCESTRY_BUDGET_EXCEEDED"
        node_id, is_exit = stack.pop()
        if not _id_ok(node_id):
            return done, "INVALID_ANCESTRY_ID"
        if node_id == claim_id:
            return done, "CLAIM_CYCLE"
        if is_exit:
            active.remove(node_id)
            done.add(node_id)
            continue
        if node_id in active:
            return done, "EVIDENCE_CYCLE"
        if node_id in done:
            continue
        node = registry.get(node_id)
        if type(node) is not SourceAttribution:
            return done, "UNKNOWN_ANCESTRY"
        parents = node.parent_attribution_ids
        if type(parents) is not tuple:
            return done, "INVALID_ANCESTRY"
        # Bound BEFORE copying or expanding the caller-provided ancestry.
        if len(parents) > MAX_REGISTRY:
            return done, "ANCESTRY_BUDGET_EXCEEDED"
        if any(not _id_ok(parent) for parent in parents):
            return done, "INVALID_ANCESTRY_ID"
        active.add(node_id)
        stack.append((node_id, True))
        stack.extend((parent, False) for parent in reversed(parents))
    # Include the selected receipt itself. Otherwise A (a supporting receipt)
    # can be the direct or transitive parent of B (another supporting receipt)
    # without intersecting B's declared ancestry. That misclassifies a
    # known-dependent pair as if their recorded lineages were disjoint.
    return done, None

def inspect_claim_support(
    registry: dict[str, SourceAttribution],
    *,
    claim_id: str,
    supporting_ids: tuple[str, ...],
    proposed_relations: dict[str, str],
) -> dict[str, Any]:
    """Inspect an already materialized read-only snapshot; metadata only.

    - Tool execution metadata is not a truth claim.
    - Relation strings are supplied by an UNAUTHENTICATED proposer.
    - Even an apparent SUPPORTS outcome is REVIEWABLE_ONLY, never VERIFIED.
    - Counts are diagnostic, and independent_support_count is always zero
      until a separately authorized source-authentication contract exists.
    """
    out = _report()
    if (
        type(registry) is not dict or len(registry) > MAX_REGISTRY
        or not _id_ok(claim_id)
        or type(supporting_ids) is not tuple
        or type(proposed_relations) is not dict
        or len(supporting_ids) > MAX_RECEIPTS
        or len(proposed_relations) > MAX_RECEIPTS
    ):
        out["reason_code"] = "INVALID_OR_OVERSIZED_INPUT"
        return out
    if any(not _id_ok(k) or type(v) is not SourceAttribution
           or v.attribution_id != k for k, v in registry.items()):
        out["reason_code"] = "INVALID_REGISTRY"
        return out
    claim = registry.get(claim_id)
    if type(claim) is not SourceAttribution or claim.source_type not in (
        SourceType.INTERNAL_HYPOTHESIS, SourceType.EXTERNAL_TESTIMONY,
    ):
        out["reason_code"] = "INVALID_CLAIM"
        return out
    if not supporting_ids:
        out["reason_code"] = "NO_RECEIPTS"
        return out
    if any(not _id_ok(k) for k in supporting_ids):
        out["reason_code"] = "INVALID_RECEIPT_ID"
        return out
    unique = set(supporting_ids)
    out["unique_receipt_count"] = len(unique)
    if len(unique) != len(supporting_ids):
        out["reason_code"] = "DUPLICATE_RECEIPT"
        return out
    if set(proposed_relations) != unique or any(
        type(value) is not str or value not in RELATIONS
        for value in proposed_relations.values()
    ):
        out["reason_code"] = "MISSING_OR_INVALID_RELATION"
        return out
    if claim_id in unique:
        out["reason_code"] = "SELF_REFERENCE"
        return out
    for receipt_id in supporting_ids:
        receipt = registry.get(receipt_id)
        if (
            type(receipt) is not SourceAttribution
            or receipt.source_type is not SourceType.EMPIRICAL_OBSERVATION
            or receipt.veracity_state is not VeracityState.VERIFIED_EMPIRICAL
            or receipt.provenance is None
            or type(receipt.provenance.exit_code) is not int
            or receipt.provenance.exit_code != 0
        ):
            out["reason_code"] = "NO_ELIGIBLE_EXECUTION_RECEIPT"
            return out
    out["execution_integrity"] = "LEGACY_REPORTED_VERIFIED"
    ancestries: list[set[str]] = []
    for receipt_id in supporting_ids:
        ancestor_ids, err = _ancestors(receipt_id, registry, claim_id)
        if err is not None:
            out["reason_code"] = err
            return out
        ancestries.append(ancestor_ids)
    # A shared recorded ancestor disproves independent *recorded* lineage.
    # Conversely disjoint declarations do NOT establish real independence.
    for i, left in enumerate(ancestries):
        for right in ancestries[i + 1:]:
            if left & right:
                out["reason_code"] = "SHARED_DECLARED_ANCESTRY"
                return out
    if "CONTRADICTS" in proposed_relations.values():
        out["reason_code"] = "DECLARED_CONTRADICTION"
        return out
    if "UNRELATED" in proposed_relations.values():
        out["reason_code"] = "DECLARED_UNRELATED"
        return out
    if "UNKNOWN" in proposed_relations.values():
        out["reason_code"] = "RELATION_UNKNOWN"
        return out

    # Caller claimed SUPPORTS for every receipt. That proposal is only an
    # invitation to independently review precise passages and source custody.
    # Not even a matching claim string or valid hash authorizes promotion.
    out["claimed_support_count"] = len(unique)
    out["review_status"] = "REVIEWABLE_ONLY"
    out["reason_code"] = "UNAUTHENTICATED_SUPPORT_PROPOSAL"
    return out
