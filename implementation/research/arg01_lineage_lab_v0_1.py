"""ARG-01 isolated synthetic source->summary->argument policy study.

RESEARCH_ONLY; no network, real source authentication, file writes or tool calls.
Caller-supplied fixture root labels are assumptions, never verified authority.
No M0 imports, no policy installation, no signer or production operations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

TRUSTED = "TRUSTED_USER_FIXTURE"
UNTRUSTED = "UNTRUSTED_EXTERNAL_FIXTURE"
UNKNOWN = "UNKNOWN"
ALLOWED_ORIGINS = frozenset({TRUSTED, UNTRUSTED})
MAX_NODES = 128


@dataclass(frozen=True)
class Node:
    parents: tuple[str, ...] = ()
    # Only roots with no parents can have a fixture origin.
    root_fixture_origin: str | None = None
    # Explicitly untrusted self-claim; ignored when computing origins.
    self_declared_origin: str | None = None


def derive_origin(graph: Mapping[str, Node], target: str, budget: int = MAX_NODES) -> frozenset[str] | None:
    """Return transitive synthetic root-label set; None means UNKNOWN.

    Reject missing parents, cycles, inconsistent root declarations and budgets.
    Iterative postorder avoids RecursionError on attacker-shaped deep graphs.
    """
    if not isinstance(target, str) or not target or not isinstance(budget, int) or budget < 1:
        return None
    states: dict[str, int] = {}  # 1 = visiting, 2 = complete
    lineage: dict[str, frozenset[str]] = {}
    stack: list[tuple[str, bool]] = [(target, False)]
    while stack:
        key, finish = stack.pop()
        if not isinstance(key, str) or not key:
            return None
        node = graph.get(key)
        if not isinstance(node, Node):
            return None
        if not isinstance(node.parents, tuple) or any(not isinstance(parent, str) or not parent for parent in node.parents):
            return None
        if finish:
            if not isinstance(node.parents, tuple) or any(not isinstance(p, str) or not p for p in node.parents):
                return None
            if not node.parents:
                if not isinstance(node.root_fixture_origin, str) or node.root_fixture_origin not in ALLOWED_ORIGINS:
                    return None
                lineage[key] = frozenset({node.root_fixture_origin})
            else:
                if node.root_fixture_origin is not None:
                    return None
                roots = set()
                for parent in node.parents:
                    if parent not in lineage:
                        return None
                    roots.update(lineage[parent])
                if not roots:
                    return None
                lineage[key] = frozenset(roots)
            states[key] = 2
            continue
        state = states.get(key, 0)
        if state == 2:
            continue
        if state == 1:
            return None
        states[key] = 1
        if len(states) > budget:
            return None
        stack.append((key, True))
        if not isinstance(node.parents, tuple):
            return None
        for parent in reversed(node.parents):
            if parent in states:
                if states[parent] == 1:
                    return None
                if states[parent] == 2:
                    continue
            stack.append((parent, False))
    return lineage.get(target)


def decide_from_origins(tool: str, origins: Mapping[str, frozenset[str] | None]) -> str:
    """Pure toy role policy. ALLOW is only a fixture classification, NOT an action."""
    role_map = {
        "SIMULATED_SEND_EMAIL": {"recipient": "authority", "body": "content"},
        "SIMULATED_GITHUB_MERGE": {"target_ref": "authority", "description": "content"},
        "SIMULATED_DELETE_FILE": {"path": "authority", "note": "content"},
    }
    roles = role_map.get(tool)
    if roles is None or set(origins) != set(roles):
        return UNKNOWN
    for role, expected in roles.items():
        roots = origins[role]
        if roots is None or not isinstance(roots, frozenset) or not roots or not roots.issubset(ALLOWED_ORIGINS):
            return UNKNOWN
        if expected == "authority" and UNTRUSTED in roots:
            return "BLOCK"
    return "ALLOW"


def evaluate_derived(tool: str, bindings: Mapping[str, str], graph: Mapping[str, Node]) -> dict[str, object]:
    """No side effects. The method never treats self-declared origin as authority."""
    origins = {role: derive_origin(graph, key) for role, key in bindings.items()}
    return {"arm": "DERIVED_LINEAGE", "result": decide_from_origins(tool, origins), "origin_sets": origins,
            "authority": "NONE", "source_authentication": UNKNOWN}


def evaluate_oracle_control(tool: str, fixture_labels: Mapping[str, frozenset[str] | None]) -> dict[str, object]:
    """Separate manually labeled fixture control, NOT independent ground truth."""
    return {"arm": "SUPPLIED_FIXTURE_LABELS", "result": decide_from_origins(tool, fixture_labels),
            "authority": "NONE", "source_authentication": UNKNOWN}
