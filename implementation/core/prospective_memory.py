"""Ario Cognitive Memory: Prospective Memory Registry & Condition Gating.

Implements biological prospective memory (Brodmann Area 10 / Rostrolateral Prefrontal Cortex)
for managing delayed intentions and deferred action triggers under Ario's bounded runtime.

Epistemic & Safety Invariants:
- T-PROS-01: Safe Predicate Sandbox. Predicate strings are strictly parsed via Python AST.
  Any arbitrary calls, dunders, imports, lambdas, or assignments are rejected fail-closed.
- T-PROS-02: Deterministic Expiration. An intention evaluated after its TTL epoch transitions
  to EXPIRED and must never emit an action or trigger side effects.
- Revision != Erasure: Expired or triggered intentions remain in historical ledger.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class ProspectiveMemoryError(ValueError):
    """Base exception for prospective memory errors."""
    pass


class ProspectiveSecurityError(ProspectiveMemoryError):
    """Raised when an intention predicate violates the safe sandbox (T-PROS-01)."""
    pass


class IntentionStatus(str, Enum):
    PENDING = "PENDING"
    TRIGGERED = "TRIGGERED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


# Allowlisted AST nodes for safe condition predicates
_ALLOWED_AST_NODES: Set[type] = {
    ast.Expression,
    ast.Compare,
    ast.BoolOp,
    ast.UnaryOp,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Is,
    ast.IsNot,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Attribute,
    ast.Subscript,
    ast.List,
    ast.Tuple,
}


def _sha256_hex(val: str) -> str:
    return hashlib.sha256(val.encode("utf-8")).hexdigest()


def validate_predicate_ast(expr_str: str) -> ast.Expression:
    """Validate that expr_str contains only safe comparisons and boolean expressions.

    T-PROS-01: Disallows Call, Import, Lambda, Assign, dunders, or any syntax injection.
    """
    if not expr_str or not expr_str.strip():
        raise ProspectiveSecurityError("Predicate expression must be non-empty")

    # Reject dangerous keywords textually before parsing
    dangerous_tokens = ["__", "import", "eval", "exec", "open", "compile", "globals", "locals"]
    for tok in dangerous_tokens:
        if tok in expr_str:
            raise ProspectiveSecurityError(f"T-PROS-01: Prohibited token '{tok}' in predicate expression")

    try:
        parsed = ast.parse(expr_str.strip(), mode="eval")
    except SyntaxError as e:
        raise ProspectiveSecurityError(f"T-PROS-01: Invalid predicate syntax: {e}") from e

    for node in ast.walk(parsed):
        if type(node) not in _ALLOWED_AST_NODES:
            raise ProspectiveSecurityError(
                f"T-PROS-01: Disallowed AST node '{type(node).__name__}' in predicate"
            )
        # Extra guard: Disallow private/dunder attribute access
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise ProspectiveSecurityError(
                f"T-PROS-01: Prohibited private attribute access: {node.attr}"
            )

    return parsed


def evaluate_safe_predicate(parsed_ast: ast.Expression, context: Dict[str, Any]) -> bool:
    """Safely evaluate an allowlisted predicate AST against a context dictionary."""
    compiled = compile(parsed_ast, filename="<predicate>", mode="eval")
    # Execute with zero builtins and context variables only
    safe_globals: Dict[str, Any] = {"__builtins__": {}}
    try:
        res = eval(compiled, safe_globals, context)  # nosec: AST strictly vetted
        return bool(res)
    except Exception:
        # Any evaluation error fails closed as False
        return False


@dataclasses.dataclass(frozen=True)
class DelayedIntention:
    intention_id: str
    description: str
    predicate_expr: str
    action_payload: Dict[str, Any]
    created_at_epoch: float
    ttl_epoch: float
    status: IntentionStatus = IntentionStatus.PENDING
    source_attribution_id: Optional[str] = None
    triggered_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.intention_id or not self.intention_id.strip():
            raise ProspectiveMemoryError("intention_id must be non-empty")
        if not self.description or not self.description.strip():
            raise ProspectiveMemoryError("description must be non-empty")
        if self.ttl_epoch <= self.created_at_epoch:
            raise ProspectiveMemoryError("ttl_epoch must be strictly greater than created_at_epoch")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intention_id": self.intention_id,
            "description": self.description,
            "predicate_expr": self.predicate_expr,
            "action_payload": dict(self.action_payload),
            "created_at_epoch": self.created_at_epoch,
            "ttl_epoch": self.ttl_epoch,
            "status": self.status.value,
            "source_attribution_id": self.source_attribution_id,
            "triggered_at": self.triggered_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DelayedIntention:
        return cls(
            intention_id=str(data["intention_id"]),
            description=str(data["description"]),
            predicate_expr=str(data["predicate_expr"]),
            action_payload=dict(data.get("action_payload", {})),
            created_at_epoch=float(data["created_at_epoch"]),
            ttl_epoch=float(data["ttl_epoch"]),
            status=IntentionStatus(data.get("status", "PENDING")),
            source_attribution_id=data.get("source_attribution_id"),
            triggered_at=data.get("triggered_at"),
        )


class ProspectiveMemoryRegistry:
    """Bounded, deterministic registry for delayed intentions and situational condition gating."""

    def __init__(self, max_pending: int = 50) -> None:
        self._max_pending = max_pending
        self._intentions: Dict[str, DelayedIntention] = {}

    @property
    def intentions(self) -> Dict[str, DelayedIntention]:
        return dict(self._intentions)

    def register_intention(
        self,
        description: str,
        predicate_expr: str,
        action_payload: Dict[str, Any],
        created_at_epoch: float,
        ttl_epoch: float,
        intention_id: Optional[str] = None,
        source_attribution_id: Optional[str] = None,
    ) -> DelayedIntention:
        """Register a pending delayed intention after AST security validation (T-PROS-01)."""
        pending_count = sum(1 for i in self._intentions.values() if i.status == IntentionStatus.PENDING)
        if pending_count >= self._max_pending:
            raise ProspectiveMemoryError(f"Registry capacity reached (max_pending={self._max_pending})")

        # T-PROS-01: Inviolable AST security check
        validate_predicate_ast(predicate_expr)

        iid = intention_id or f"INT-{_sha256_hex(description + predicate_expr)[:12]}"
        intention = DelayedIntention(
            intention_id=iid,
            description=description,
            predicate_expr=predicate_expr,
            action_payload=action_payload,
            created_at_epoch=created_at_epoch,
            ttl_epoch=ttl_epoch,
            status=IntentionStatus.PENDING,
            source_attribution_id=source_attribution_id,
        )
        self._intentions[intention.intention_id] = intention
        return intention

    def evaluate_cues(
        self,
        cue_context: Dict[str, Any],
        current_epoch: float,
    ) -> List[DelayedIntention]:
        """T-PROS-02: Deterministically evaluate situational cues and enforce TTL expiration.

        - If current_epoch >= ttl_epoch, transitions to EXPIRED; never emits action.
        - If predicate evaluates True within TTL, transitions to TRIGGERED.
        """
        triggered: List[DelayedIntention] = []

        for iid, intention in list(self._intentions.items()):
            if intention.status != IntentionStatus.PENDING:
                continue

            # Invariant T-PROS-02: Strict TTL Expiration
            if current_epoch >= intention.ttl_epoch:
                expired = dataclasses.replace(intention, status=IntentionStatus.EXPIRED)
                self._intentions[iid] = expired
                continue

            # Evaluate predicate safely
            try:
                parsed_ast = validate_predicate_ast(intention.predicate_expr)
                is_triggered = evaluate_safe_predicate(parsed_ast, cue_context)
            except Exception:
                is_triggered = False

            if is_triggered:
                now_iso = datetime.now(timezone.utc).isoformat()
                active = dataclasses.replace(
                    intention,
                    status=IntentionStatus.TRIGGERED,
                    triggered_at=now_iso,
                )
                self._intentions[iid] = active
                triggered.append(active)

        return triggered

    def cancel_intention(self, intention_id: str) -> DelayedIntention:
        """Cancel a pending intention."""
        intention = self._intentions.get(intention_id)
        if not intention:
            raise ProspectiveMemoryError(f"Unknown intention_id: {intention_id}")
        if intention.status != IntentionStatus.PENDING:
            raise ProspectiveMemoryError(f"Cannot cancel intention in state: {intention.status}")

        cancelled = dataclasses.replace(intention, status=IntentionStatus.CANCELLED)
        self._intentions[intention_id] = cancelled
        return cancelled

    def get_pending_intentions(self) -> List[DelayedIntention]:
        return [i for i in self._intentions.values() if i.status == IntentionStatus.PENDING]

    def get_expired_intentions(self) -> List[DelayedIntention]:
        return [i for i in self._intentions.values() if i.status == IntentionStatus.EXPIRED]

    def get_triggered_intentions(self) -> List[DelayedIntention]:
        return [i for i in self._intentions.values() if i.status == IntentionStatus.TRIGGERED]

    def save_journal(self, journal_path: Path) -> int:
        """Atomically persist registered intentions to disk with cryptographic integrity checksum."""
        journal_path = Path(journal_path)
        journal_path.parent.mkdir(parents=True, exist_ok=True)

        records = [i.to_dict() for i in self._intentions.values()]
        canonical_bytes = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
        integrity_digest = hashlib.sha256(canonical_bytes).hexdigest()

        payload = {
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "max_pending": self._max_pending,
            "records_count": len(records),
            "integrity_digest": integrity_digest,
            "intentions": records,
        }

        tmp_path = journal_path.with_suffix(f".tmp.{os.getpid()}")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, journal_path)
        return len(records)

    @classmethod
    def load_journal(
        cls,
        journal_path: Path,
        max_pending: Optional[int] = None,
        enforce_ast_revalidation: bool = True,
    ) -> ProspectiveMemoryRegistry:
        """Load and reconstruct registry from journal with integrity and AST security validation."""
        journal_path = Path(journal_path)
        if not journal_path.exists():
            raise ProspectiveMemoryError(f"Journal path does not exist: {journal_path}")

        try:
            with open(journal_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as exc:
            raise ProspectiveMemoryError(f"Corrupt or unreadable journal JSON: {exc}") from exc

        if not isinstance(payload, dict) or "integrity_digest" not in payload or "intentions" not in payload:
            raise ProspectiveMemoryError("Malformed journal schema: missing required keys")

        records = payload["intentions"]
        if not isinstance(records, list):
            raise ProspectiveMemoryError("Malformed journal schema: 'intentions' must be a list")

        canonical_bytes = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
        expected_digest = hashlib.sha256(canonical_bytes).hexdigest()
        actual_digest = payload.get("integrity_digest", "")

        if actual_digest != expected_digest:
            raise ProspectiveSecurityError(
                f"T-PROS-01: Integrity digest mismatch on journal load (expected {expected_digest[:16]}..., got {actual_digest[:16]}...)"
            )

        limit = max_pending if max_pending is not None else int(payload.get("max_pending", 50))
        registry = cls(max_pending=limit)

        for item in records:
            if enforce_ast_revalidation:
                validate_predicate_ast(item.get("predicate_expr", ""))

            intention = DelayedIntention.from_dict(item)
            registry._intentions[intention.intention_id] = intention

        return registry

    def reconcile_expired_intentions(self, current_epoch: float) -> int:
        """T-PROS-02: Sweep pending intentions and transition any with ttl_epoch <= current_epoch to EXPIRED."""
        expired_count = 0
        for iid, intention in list(self._intentions.items()):
            if intention.status == IntentionStatus.PENDING and current_epoch >= intention.ttl_epoch:
                self._intentions[iid] = dataclasses.replace(intention, status=IntentionStatus.EXPIRED)
                expired_count += 1
        return expired_count
