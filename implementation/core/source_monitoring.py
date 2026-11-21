"""Ario Cognitive Memory: Metacognitive Source Monitoring Guard.

Operationalizes the Prefrontal Reality Monitoring Network (Johnson et al.
Source Monitoring Framework) over Ario's cognitive working memory.
Enforces founding epistemic invariants:
- Memory != Truth: Tagged assertions remain fallible claims.
- Claim != Proof: An assertion requires empirical provenance to promote.
- Revision != Erasure: Invalidation marks veracity state; past events remain immutable.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


class SourceMonitoringError(ValueError):
    """Base exception for source monitoring violations."""
    pass


class SelfCitationError(SourceMonitoringError):
    """Raised when an internal hypothesis attempts self-citation or circular promotion without empirical proof."""
    pass


class AttributionMismatchError(SourceMonitoringError):
    """Raised when recorded empirical provenance contradicts the actual execution lock or checksum."""
    pass


class SourceType(str, Enum):
    INTERNAL_HYPOTHESIS = "INTERNAL_HYPOTHESIS"
    EMPIRICAL_OBSERVATION = "EMPIRICAL_OBSERVATION"
    EXTERNAL_TESTIMONY = "EXTERNAL_TESTIMONY"


class VeracityState(str, Enum):
    UNVERIFIED_HYPOTHESIS = "UNVERIFIED_HYPOTHESIS"
    EXTERNAL_ASSERTION = "EXTERNAL_ASSERTION"
    VERIFIED_EMPIRICAL = "VERIFIED_EMPIRICAL"
    UNSUPPORTED = "UNSUPPORTED"
    ATTRIBUTION_MISMATCH = "ATTRIBUTION_MISMATCH"
    CONTRADICTED = "CONTRADICTED"


ALLOWLISTED_TOOLS: Set[str] = {
    "git_status",
    "inspect_directory",
    "run_tests",
    "compile_python",
    "check_file_hash",
    "diff_check",
    "syntax_validator",
    "read_file_pinned",
    "file_fingerprint",
    "read_text",
    "verify_text",
    "inspect_backup",
}


def _sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _is_valid_sha256(val: str) -> bool:
    return (
        isinstance(val, str)
        and len(val) == 64
        and all(c in "0123456789abcdef" for c in val.lower())
    )


@dataclasses.dataclass(frozen=True)
class EmpiricalProvenance:
    tool: str
    target: str
    exit_code: int
    execution_lock_sha256: str
    stdout_sha256: str
    recorded_at: str
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.tool or not self.tool.strip():
            raise SourceMonitoringError("tool must be non-empty")
        if not _is_valid_sha256(self.execution_lock_sha256):
            raise SourceMonitoringError(f"execution_lock_sha256 must be a valid 64-char sha256: {self.execution_lock_sha256}")
        if not _is_valid_sha256(self.stdout_sha256):
            raise SourceMonitoringError(f"stdout_sha256 must be a valid 64-char sha256: {self.stdout_sha256}")
        if not isinstance(self.exit_code, int):
            raise SourceMonitoringError("exit_code must be an integer")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "target": self.target,
            "exit_code": self.exit_code,
            "execution_lock_sha256": self.execution_lock_sha256,
            "stdout_sha256": self.stdout_sha256,
            "recorded_at": self.recorded_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EmpiricalProvenance:
        return cls(
            tool=str(data["tool"]),
            target=str(data.get("target", "")),
            exit_code=int(data["exit_code"]),
            execution_lock_sha256=str(data["execution_lock_sha256"]),
            stdout_sha256=str(data.get("stdout_sha256", data.get("execution_lock_sha256"))),
            recorded_at=str(data.get("recorded_at", datetime.now(timezone.utc).isoformat())),
            metadata=dict(data.get("metadata", {})),
        )


@dataclasses.dataclass(frozen=True)
class SourceAttribution:
    attribution_id: str
    source_type: SourceType
    assertion: str
    veracity_state: VeracityState
    provenance: Optional[EmpiricalProvenance] = None
    parent_attribution_ids: Tuple[str, ...] = ()
    created_at: str = dataclasses.field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    falsification_condition: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.attribution_id or not self.attribution_id.strip():
            raise SourceMonitoringError("attribution_id must be non-empty")
        if not self.assertion or not self.assertion.strip():
            raise SourceMonitoringError("assertion must be non-empty")

        # Invariant: Empirical observations must carry valid empirical provenance
        if self.source_type == SourceType.EMPIRICAL_OBSERVATION:
            if self.provenance is None:
                raise SourceMonitoringError("EMPIRICAL_OBSERVATION must include empirical provenance")
            if self.veracity_state not in (
                VeracityState.VERIFIED_EMPIRICAL,
                VeracityState.ATTRIBUTION_MISMATCH,
                VeracityState.UNSUPPORTED,
            ):
                raise SourceMonitoringError(f"Invalid veracity state for EMPIRICAL_OBSERVATION: {self.veracity_state}")

        # Invariant: Hypotheses and external testimony cannot natively be VERIFIED_EMPIRICAL
        if self.source_type in (SourceType.INTERNAL_HYPOTHESIS, SourceType.EXTERNAL_TESTIMONY):
            if self.veracity_state == VeracityState.VERIFIED_EMPIRICAL and not self.parent_attribution_ids:
                raise SourceMonitoringError(
                    f"{self.source_type} cannot be directly verified without empirical parent provenance"
                )

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "attribution_id": self.attribution_id,
            "source_type": self.source_type.value,
            "assertion": self.assertion,
            "veracity_state": self.veracity_state.value,
            "parent_attribution_ids": list(self.parent_attribution_ids),
            "created_at": self.created_at,
        }
        if self.provenance:
            res["provenance"] = self.provenance.to_dict()
        if self.falsification_condition:
            res["falsification_condition"] = self.falsification_condition
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SourceAttribution:
        provenance = None
        if "provenance" in data and data["provenance"] is not None:
            provenance = EmpiricalProvenance.from_dict(data["provenance"])
        return cls(
            attribution_id=str(data.get("attribution_id", f"ATTR-{_sha256_hex(data.get('assertion', ''))[:12]}")),
            source_type=SourceType(data["source_type"]),
            assertion=str(data["assertion"]),
            veracity_state=VeracityState(data["veracity_state"]),
            provenance=provenance,
            parent_attribution_ids=tuple(data.get("parent_attribution_ids", ())),
            created_at=str(data.get("created_at", datetime.now(timezone.utc).isoformat())),
            falsification_condition=data.get("falsification_condition"),
        )


class SourceMonitoringGuard:
    """Reality monitoring guard enforcing origin attribution and anti-self-citation."""

    def __init__(self, allowlisted_tools: Optional[Set[str]] = None) -> None:
        self._allowlisted_tools = set(allowlisted_tools) if allowlisted_tools else set(ALLOWLISTED_TOOLS)
        self._attributions: Dict[str, SourceAttribution] = {}
        # In-memory audit snapshots: NOT a persistent append-only journal.
        self._revisions: Dict[str, List[SourceAttribution]] = {}

    @property
    def attributions(self) -> Dict[str, SourceAttribution]:
        return copy.deepcopy(self._attributions)

    def attribution_history(self, attribution_id: str) -> Tuple[SourceAttribution, ...]:
        """Read-only snapshots, including a disallowed promotion's recorded state."""
        return tuple(copy.deepcopy(self._revisions.get(attribution_id, [])))

    @staticmethod
    def _basis(attr: SourceAttribution) -> Dict[str, Any]:
        """Compare stable data; retries with new observation times are not new sources."""
        value = attr.to_dict()
        value.pop("created_at", None)
        if "provenance" in value:
            value["provenance"].pop("recorded_at", None)
        return value

    def _register(self, attr: SourceAttribution) -> SourceAttribution:
        """Never replace an existing identity with different claim/source data."""
        old = self._attributions.get(attr.attribution_id)
        if old is not None:
            if self._basis(old) == self._basis(attr):
                return copy.deepcopy(old)
            raise SourceMonitoringError(
                f"ATTRIBUTION_ID_COLLISION: {attr.attribution_id} already names a different source"
            )
        stored = copy.deepcopy(attr)
        self._attributions[stored.attribution_id] = stored
        self._revisions[stored.attribution_id] = [copy.deepcopy(stored)]
        return copy.deepcopy(stored)

    def _revise(self, attr: SourceAttribution) -> SourceAttribution:
        if attr.attribution_id not in self._attributions:
            raise SourceMonitoringError("HOLD_UNREGISTERED_REVISION")
        # Changes in epistemic status are explicit in-memory revisions, not erasure.
        stored = copy.deepcopy(attr)
        if stored != self._attributions[attr.attribution_id]:
            self._attributions[attr.attribution_id] = stored
            self._revisions[attr.attribution_id].append(copy.deepcopy(stored))
        return copy.deepcopy(self._attributions[attr.attribution_id])

    def create_hypothesis(
        self,
        assertion: str,
        attribution_id: Optional[str] = None,
        parent_attribution_ids: Sequence[str] = (),
        falsification_condition: Optional[str] = None,
    ) -> SourceAttribution:
        """Register an internal speculative claim (generated token / planner thought)."""
        attr_id = attribution_id or f"ATTR-HYP-{_sha256_hex(assertion)[:12]}"
        attr = SourceAttribution(
            attribution_id=attr_id,
            source_type=SourceType.INTERNAL_HYPOTHESIS,
            assertion=assertion,
            veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
            provenance=None,
            parent_attribution_ids=tuple(parent_attribution_ids),
            falsification_condition=falsification_condition,
        )
        return self._register(attr)

    def create_external_testimony(
        self,
        assertion: str,
        attribution_id: Optional[str] = None,
        falsification_condition: Optional[str] = None,
    ) -> SourceAttribution:
        """Register an unverified claim from an external human or third-party input."""
        attr_id = attribution_id or f"ATTR-EXT-{_sha256_hex(assertion)[:12]}"
        attr = SourceAttribution(
            attribution_id=attr_id,
            source_type=SourceType.EXTERNAL_TESTIMONY,
            assertion=assertion,
            veracity_state=VeracityState.EXTERNAL_ASSERTION,
            provenance=None,
            parent_attribution_ids=(),
            falsification_condition=falsification_condition,
        )
        return self._register(attr)

    def record_empirical_observation(
        self,
        assertion: str,
        tool: str,
        target: str,
        exit_code: int,
        stdout: str | bytes,
        execution_lock: str | bytes,
        attribution_id: Optional[str] = None,
        parent_attribution_ids: Sequence[str] = (),
        expected_execution_lock_sha256: Optional[str] = None,
        expected_stdout_sha256: Optional[str] = None,
    ) -> SourceAttribution:
        """Record an empirical observation with cryptographic lock verification."""
        if tool not in self._allowlisted_tools:
            raise SourceMonitoringError(f"Tool '{tool}' is not allowlisted for empirical observation")

        actual_lock_hash = _sha256_hex(execution_lock)
        actual_stdout_hash = _sha256_hex(stdout)

        # Verification of execution lock integrity
        if expected_execution_lock_sha256 and expected_execution_lock_sha256.lower() != actual_lock_hash.lower():
            attr_id = attribution_id or (
                "ATTR-EMP-MISMATCH-LOCK-"
                + _sha256_hex(assertion + actual_lock_hash + str(expected_execution_lock_sha256))[:16]
            )
            prov = EmpiricalProvenance(
                tool=tool,
                target=target,
                exit_code=exit_code,
                execution_lock_sha256=actual_lock_hash,
                stdout_sha256=actual_stdout_hash,
                recorded_at=datetime.now(timezone.utc).isoformat(),
                metadata={"expected_lock_sha256": expected_execution_lock_sha256},
            )
            attr = SourceAttribution(
                attribution_id=attr_id,
                source_type=SourceType.EMPIRICAL_OBSERVATION,
                assertion=assertion,
                veracity_state=VeracityState.ATTRIBUTION_MISMATCH,
                provenance=prov,
                parent_attribution_ids=tuple(parent_attribution_ids),
            )
            self._register(attr)
            raise AttributionMismatchError(
                f"T-SRC-02: execution lock mismatch (expected {expected_execution_lock_sha256}, got {actual_lock_hash})"
            )

        # Verification of stdout integrity
        if expected_stdout_sha256 and expected_stdout_sha256.lower() != actual_stdout_hash.lower():
            attr_id = attribution_id or (
                "ATTR-EMP-MISMATCH-STDOUT-"
                + _sha256_hex(assertion + actual_stdout_hash + str(expected_stdout_sha256))[:16]
            )
            prov = EmpiricalProvenance(
                tool=tool,
                target=target,
                exit_code=exit_code,
                execution_lock_sha256=actual_lock_hash,
                stdout_sha256=actual_stdout_hash,
                recorded_at=datetime.now(timezone.utc).isoformat(),
                metadata={"expected_stdout_sha256": expected_stdout_sha256},
            )
            attr = SourceAttribution(
                attribution_id=attr_id,
                source_type=SourceType.EMPIRICAL_OBSERVATION,
                assertion=assertion,
                veracity_state=VeracityState.ATTRIBUTION_MISMATCH,
                provenance=prov,
                parent_attribution_ids=tuple(parent_attribution_ids),
            )
            self._register(attr)
            raise AttributionMismatchError(
                f"T-SRC-02: stdout hash mismatch (expected {expected_stdout_sha256}, got {actual_stdout_hash})"
            )

        # Cryptographic hashes bind self-reported bytes, NOT the semantic claim.
        # This narrow canonical statement reports only the tool/target/exit fields.
        # It does not prove that the caller is an independently trusted runner.
        bound_assertion = f"tool_exit:{tool}:{target}:{exit_code}"
        veracity = (
            VeracityState.VERIFIED_EMPIRICAL
            if exit_code == 0 and assertion == bound_assertion
            else VeracityState.UNSUPPORTED
        )

        prov = EmpiricalProvenance(
            tool=tool,
            target=target,
            exit_code=exit_code,
            execution_lock_sha256=actual_lock_hash,
            stdout_sha256=actual_stdout_hash,
            recorded_at=datetime.now(timezone.utc).isoformat(),
        )
        attr_id = attribution_id or f"ATTR-EMP-{_sha256_hex(assertion)[:12]}"
        attr = SourceAttribution(
            attribution_id=attr_id,
            source_type=SourceType.EMPIRICAL_OBSERVATION,
            assertion=assertion,
            veracity_state=veracity,
            provenance=prov,
            parent_attribution_ids=tuple(parent_attribution_ids),
        )
        return self._register(attr)

    def detect_circular_dependency(self, start_id: str) -> bool:
        """Detect if an attribution graph contains a self-citation cycle."""
        visited: Set[str] = set()
        stack: Set[str] = set()

        def _dfs(node_id: str) -> bool:
            visited.add(node_id)
            stack.add(node_id)
            node = self._attributions.get(node_id)
            if node:
                for parent in node.parent_attribution_ids:
                    if parent not in visited:
                        if _dfs(parent):
                            return True
                    elif parent in stack:
                        return True
            stack.remove(node_id)
            return False

        return _dfs(start_id)

    def evaluate_claim_promotion(
        self,
        claim_id: str,
        supporting_ids: Sequence[str],
    ) -> SourceAttribution:
        """T-SRC-01: Inviolable gating promoting a claim to verified evidence.

        A claim citing only internal hypotheses or external testimony cannot
        be promoted without at least one EMPIRICAL_OBSERVATION.
        Self-citation or circular rationalization raises SelfCitationError.
        """
        claim = self._attributions.get(claim_id)
        if not claim:
            raise SourceMonitoringError(f"Unknown claim_id: {claim_id}")

        if not supporting_ids:
            raise SelfCitationError(f"T-SRC-01: Claim '{claim_id}' has no supporting evidence (unsupported)")

        # Check for self-citation: citing itself directly
        if claim_id in supporting_ids:
            raise SelfCitationError(f"T-SRC-01: Self-citation detected: claim '{claim_id}' cites itself")

        supporting_nodes: List[SourceAttribution] = []
        for sid in supporting_ids:
            node = self._attributions.get(sid)
            if not node:
                raise SourceMonitoringError(f"Supporting attribution '{sid}' not found in registry")
            supporting_nodes.append(node)

        # Check for circular reference in lineage
        temp_parents = claim.parent_attribution_ids + tuple(supporting_ids)
        temp_claim = dataclasses.replace(claim, parent_attribution_ids=temp_parents)
        self._attributions[claim_id] = temp_claim
        if self.detect_circular_dependency(claim_id):
            # Rollback
            self._attributions[claim_id] = claim
            raise SelfCitationError(f"T-SRC-01: Circular citation loop detected involving '{claim_id}'")

        # Evidence supports only its own *narrowly bound* statement.
        # Unrelated successful tests cannot verify a free-form natural-language claim.
        # A separate externally authenticated semantic entailment contract is not available.
        # In the research-only guard, exact matching is necessary but still not
        # independently sufficient to establish external truth.
        has_verified_empirical = False
        for node in supporting_nodes:
            if (
                node.source_type == SourceType.EMPIRICAL_OBSERVATION
                and node.veracity_state == VeracityState.VERIFIED_EMPIRICAL
                and node.assertion == claim.assertion
            ):
                has_verified_empirical = True
                break

        if not has_verified_empirical:
            # Mark claim as UNSUPPORTED
            unsupported_claim = dataclasses.replace(
                claim,
                veracity_state=VeracityState.UNSUPPORTED,
                parent_attribution_ids=temp_parents,
            )
            self._revise(unsupported_claim)
            raise SelfCitationError(
                f"T-SRC-01: Anti-Self-Citation: claim '{claim_id}' cites only hypotheses/testimony "
                "without an empirical observation and cannot promote to verified evidence."
            )

        # Promotion succeeds
        promoted = dataclasses.replace(
            claim,
            veracity_state=VeracityState.VERIFIED_EMPIRICAL,
            parent_attribution_ids=temp_parents,
        )
        return self._revise(promoted)

    def filter_working_memory_candidates(
        self,
        attribution_ids: Sequence[str],
        require_verified: bool = False,
    ) -> List[SourceAttribution]:
        """Gating mechanism before context buffer injection.

        Filters out corrupted attributions, ungrounded self-citations, or attribution mismatches.
        """
        valid_items: List[SourceAttribution] = []
        for aid in attribution_ids:
            node = self._attributions.get(aid)
            if not node:
                continue

            # Invariant: Never inject attribution mismatches into working memory
            if node.veracity_state == VeracityState.ATTRIBUTION_MISMATCH:
                continue

            # Invariant: Never inject unsupported claims when verified is required
            if require_verified and node.veracity_state != VeracityState.VERIFIED_EMPIRICAL:
                continue

            # Check for circularity
            if self.detect_circular_dependency(aid):
                continue

            valid_items.append(node)

        return valid_items
