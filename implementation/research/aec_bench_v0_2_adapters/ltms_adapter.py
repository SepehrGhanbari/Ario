"""Bounded LTMS adapter for simple assumption/dependency fixtures.

Only conjunction-of-premises support and assumption retraction are mapped.
Scope, provenance roots, time, authentication, and composition firewalls are
not inferred by this adapter.
"""
from __future__ import annotations

from typing import Any


def _fact(name: str, value: str) -> tuple[str, str]:
    return (name, value)


def evaluate_dependency_case(fixture: Any) -> dict[str, Any]:
    """Use LTRE assumptions to evaluate a simple required-premise conjunction.

    Complex composition flags are explicitly marked not comparable instead
    of being silently ignored.
    """
    if fixture.family != "composition_dependencies":
        raise ValueError("LTMS adapter currently supports composition_dependencies only")

    d = fixture.input
    unsupported = (
        "incompatible", "shared_dependency", "cycle", "time_incompatible",
        "scope_incompatible", "claim_kind_mismatch", "local_validity_only",
        "partial_overlap", "firewall_bypassed",
    )
    present = [flag for flag in unsupported if d.get(flag)]
    if present:
        return {
            "comparable": False,
            "status": "NOT_COMPARABLE",
            "reason": "UNMAPPED_COMPOSITION_SEMANTICS",
            "unmapped_flags": present,
        }

    try:
        from ltms import LTRE
    except ImportError as exc:  # pragma: no cover - exercised in adapter env
        raise RuntimeError(
            "LTMS adapter dependency missing; install requirements-adapters.txt"
        ) from exc

    engine = LTRE(title=f"AEC-{fixture.case_id}")
    required = [_fact("premise", str(p)) for p in d["requirements"]]
    conclusion = _fact("composed", fixture.case_id)

    if not required:
        return {
            "comparable": False,
            "status": "NOT_COMPARABLE",
            "reason": "EMPTY_REQUIREMENT_SET",
            "unmapped_flags": [],
        }

    antecedent = required[0] if len(required) == 1 else ("and", *required)
    engine.assert_(("implies", antecedent, conclusion))

    for premise in d["premises"]:
        engine.assume(_fact("premise", str(premise)), informant="aec-bench-fixture")

    return {
        "comparable": True,
        "status": "SUPPORTED" if engine.is_true(conclusion) else "UNKNOWN",
        "conclusion_known": engine.is_known(conclusion),
        "missing_requirements": sorted(set(d["requirements"]) - set(d["premises"])),
    }


def assumption_retraction_probe() -> dict[str, bool]:
    """Positive control: a derived belief becomes unknown when its sole
    retractable premise assumption is removed.
    """
    from ltms import LTRE

    engine = LTRE(title="AEC-LTMS-retraction-probe")
    premise = _fact("premise", "R1")
    conclusion = _fact("claim", "derived")
    engine.assert_(("implies", premise, conclusion))
    engine.assume(premise, informant="aec-bench-probe")
    before = engine.is_true(conclusion)
    engine.retract(premise, informant="aec-bench-probe")
    after = engine.is_unknown(conclusion)
    return {"supported_before_retraction": before, "unknown_after_retraction": after}
