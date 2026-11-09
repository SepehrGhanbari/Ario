"""Research-only H3.2 scope-attribution lab, NOT the Ario M0 audit engine.

This deterministic experiment consumes synthetic, explicitly typed inputs.  The
``TEST_VERIFIED`` field is a supplied test premise; NO signatures, authority, or
real-world evidence are verified here.  Nothing in this module grants trust.
"""

from __future__ import annotations

from itertools import product
from typing import Any

LAB_VERSION = "H32-SCOPE-LAB-0.1"
CHECKS = (
    "display_qualifier_omission",
    "typed_metadata_loss",
    "preservation_contract_breach",
    "unsupported_scope_assertion",
    "unsupported_firm_certification",
)
POLICIES = ("coverage/single-item-v1", "coverage/union-v1")
VERIFICATION_PREMISES = ("TEST_VERIFIED", "TEST_INVALID", "UNVERIFIED")
MAX_EVENTS = 32
MAX_GUARANTEES = 32
MAX_OBLIGATIONS = 16
MAX_CELLS = 1024


class ResearchInputError(ValueError):
    """An invalid research fixture, distinct from UNKNOWN evidence."""


def _object(value: Any, context: str) -> dict:
    if not isinstance(value, dict):
        raise ResearchInputError(f"{context}: expected object")
    return value


def _keys(value: dict, required: set[str], optional: set[str], context: str) -> None:
    missing, extras = required - value.keys(), value.keys() - required - optional
    if missing or extras:
        raise ResearchInputError(
            f"{context}: missing={sorted(missing)} unexpected={sorted(extras)}"
        )


def _name(value: Any, context: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 96 or not value.strip():
        raise ResearchInputError(f"{context}: expected non-empty bounded string")
    return value


def _tick(value: Any, context: str, *, allow_unknown: bool = False) -> int | None:
    if value is None and allow_unknown:
        return None
    if type(value) is not int or not 0 <= value <= 1_000_000_000:
        raise ResearchInputError(f"{context}: expected nonnegative integer tick")
    return value


def _list(value: Any, context: str, limit: int) -> list:
    if not isinstance(value, list) or len(value) > limit:
        raise ResearchInputError(f"{context}: expected list of at most {limit}")
    return value


def _scope(scope: Any, domain: dict, context: str) -> dict[str, str]:
    scope = _object(scope, context)
    _keys(scope, set(domain), set(), context)
    for dimension, term in scope.items():
        _name(term, f"{context}.{dimension}")
        if term not in domain[dimension]:
            raise ResearchInputError(f"{context}.{dimension}: undeclared scope term")
    return scope


def _field_map(value: Any, context: str, *, nullable: bool = False) -> dict | None:
    if value is None and nullable:
        return None
    value = _object(value, context)
    if len(value) > 16:
        raise ResearchInputError(f"{context}: too many facets")
    for key, term in value.items():
        _name(key, f"{context}.key")
        _name(term, f"{context}.{key}")
    return value


def _domain(value: Any) -> dict[str, dict[str, tuple[str, ...]]]:
    value = _object(value, "domain")
    _keys(value, {"facility", "period", "population"}, set(), "domain")
    result = {}
    for dimension, aliases in value.items():
        aliases = _object(aliases, f"domain.{dimension}")
        if not 1 <= len(aliases) <= 16:
            raise ResearchInputError(f"domain.{dimension}: 1..16 named sets required")
        result[dimension] = {}
        for alias, atoms in aliases.items():
            _name(alias, f"domain.{dimension}.alias")
            atoms = _list(atoms, f"domain.{dimension}.{alias}", 16)
            if not atoms or any(not isinstance(x, str) or not x for x in atoms):
                raise ResearchInputError("domain atoms must be non-empty strings")
            if len(set(atoms)) != len(atoms):
                raise ResearchInputError("duplicate atom in domain expansion")
            result[dimension][alias] = tuple(atoms)
    return result


def _cells(scope: dict, domain: dict) -> frozenset[tuple[str, str, str]]:
    dimensions = ("facility", "period", "population")
    vectors = [domain[d][scope[d]] for d in dimensions]
    size = 1
    for vector in vectors:
        size *= len(vector)
    if size > MAX_CELLS:
        raise ResearchInputError("scope expansion exceeds bounded research limit")
    return frozenset(product(*vectors))


def _eligibility(guarantee: dict, event_at: int, requested_kind: str,
                 requested_strength: str) -> str:
    # Independent known failures are decisive even when another field is UNKNOWN.
    if guarantee["claim_kind"] != requested_kind:
        return "REJECTED_KIND"
    if requested_strength == "CERTIFIED" and guarantee["strength"] != "CERTIFIED":
        return "REJECTED_STRENGTH"
    if guarantee["verification"] == "TEST_INVALID":
        return "REJECTED_INVALID_TEST_PREMISE"
    if guarantee["available_at"] is not None and guarantee["available_at"] > event_at:
        return "REJECTED_NOT_AVAILABLE_TO_ACTOR"
    if guarantee["verified_at"] is not None and guarantee["verified_at"] > event_at:
        return "REJECTED_NOT_VERIFIED_AT_ACTOR_TIME"
    if (guarantee["verification"] != "TEST_VERIFIED"
            or guarantee["available_at"] is None
            or guarantee["verified_at"] is None):
        return "UNKNOWN"
    return "ELIGIBLE"


def _covers(candidates: list[frozenset], target: frozenset,
            policy: str) -> bool:
    if policy == "coverage/single-item-v1":
        return any(target <= candidate for candidate in candidates)
    covered: set = set()
    for candidate in candidates:
        covered.update(candidate)
    return bool(target <= covered)


def _support(assertion: dict, guarantees: dict, domain: dict,
             event_at: int, policy: str) -> dict:
    target = _cells(assertion["scope"], domain)
    eligible, possible, declared = [], [], []
    unresolved = False
    for ref in assertion["citations"]:
        g = guarantees.get(ref)
        if g is None:
            unresolved = True
            declared.append({"id": ref, "eligibility": "UNKNOWN_UNRESOLVED",
                             "verification_premise": "UNKNOWN"})
            continue
        reason = _eligibility(g, event_at, assertion["claim_kind"],
                              assertion["strength"])
        declared.append({"id": ref, "eligibility": reason,
                         "verification_premise": g["verification"]})
        coverage = _cells(g["scope"], domain)
        if g["claim_kind"] == assertion["claim_kind"] and (
            assertion["strength"] != "CERTIFIED" or g["strength"] == "CERTIFIED"
        ):
            if reason == "ELIGIBLE":
                eligible.append(coverage)
                possible.append(coverage)
            elif reason == "UNKNOWN":
                possible.append(coverage)
    conditional = []
    for ref in assertion["citations"]:
        g = guarantees.get(ref)
        if g is not None and g["claim_kind"] == assertion["claim_kind"] and (
            assertion["strength"] != "CERTIFIED" or g["strength"] == "CERTIFIED"
        ):
            conditional.append(_cells(g["scope"], domain))
    if _covers(conditional, target, policy):
        conditional_coverage = "YES_UNDER_SUPPLIED_CONTENT"
    elif unresolved or not assertion["citations_complete"]:
        conditional_coverage = "UNKNOWN"
    else:
        conditional_coverage = "NO_UNDER_SUPPLIED_CONTENT"

    if _covers(eligible, target, policy):
        effective = "SUPPORTED"
    elif unresolved or not assertion["citations_complete"] or _covers(possible, target, policy):
        effective = "UNKNOWN"
    else:
        # Even an unverified item cannot support a scope known to be too narrow.
        effective = "UNSUPPORTED_BY_CITED_EVIDENCE"
    return {"conditional_coverage": conditional_coverage,
            "effective_cited_justification": effective,
            "citations": declared}


def _localize(states: list[str], events: list[dict], history_complete: bool) -> dict:
    known_errors = [events[i]["actor"] for i, state in enumerate(states)
                    if state == "ERROR"]
    earliest_observed = (known_errors[0] if known_errors
                         else "UNKNOWN" if "UNKNOWN" in states else "NONE")
    # An earlier unknown can conceal an earlier error; an incomplete prefix can
    # conceal one even when all visible checks are decisive.
    if not history_complete:
        earliest_global = "UNKNOWN"
    elif known_errors:
        first = states.index("ERROR")
        earliest_global = "UNKNOWN" if "UNKNOWN" in states[:first] else known_errors[0]
    else:
        earliest_global = "UNKNOWN" if "UNKNOWN" in states else "NONE"
    return {"earliest_observed": earliest_observed,
            "earliest_global": earliest_global}


def evaluate_case(case: Any) -> dict:
    """Evaluate a small, synthetic v0.3 research case; no M0 invocation."""
    case = _object(case, "case")
    _keys(case, {"case_id", "domain", "events", "guarantees", "obligations",
                 "history_complete", "coverage_policy"}, set(), "case")
    case_id = _name(case["case_id"], "case_id")
    domain = _domain(case["domain"])
    policy = case["coverage_policy"]
    if policy not in POLICIES:
        raise ResearchInputError("unversioned or unsupported coverage policy")
    if type(case["history_complete"]) is not bool:
        raise ResearchInputError("history_complete must be boolean")
    evidence = _list(case["guarantees"], "guarantees", MAX_GUARANTEES)
    guarantees: dict[str, dict] = {}
    for i, raw in enumerate(evidence):
        g = _object(raw, f"guarantees[{i}]")
        _keys(g, {"id", "scope", "claim_kind", "strength", "verification",
                  "available_at", "verified_at", "published_at"}, set(), f"guarantees[{i}]")
        g_id = _name(g["id"], "guarantee.id")
        if g_id in guarantees:
            raise ResearchInputError("duplicate guarantee ID")
        _scope(g["scope"], domain, f"guarantees[{i}].scope")
        _name(g["claim_kind"], "claim_kind")
        if g["strength"] not in ("TENTATIVE", "CERTIFIED"):
            raise ResearchInputError("unsupported guarantee strength")
        if g["verification"] not in VERIFICATION_PREMISES:
            raise ResearchInputError("verification premise is not a known test value")
        for time_field in ("available_at", "verified_at", "published_at"):
            _tick(g[time_field], f"guarantees[{i}].{time_field}", allow_unknown=True)
        guarantees[g_id] = g

    events = _list(case["events"], "events", MAX_EVENTS)
    if not events:
        raise ResearchInputError("at least one observed event required")
    seen_times: set[int] = set()
    for i, raw in enumerate(events):
        event = _object(raw, f"events[{i}]")
        _keys(event, {"actor", "at", "display_facets", "scope_meta", "assertion"},
              {"display_text"}, f"events[{i}]")
        if "display_text" in event:
            text = event["display_text"]
            if not isinstance(text, str) or len(text) > 4000:
                raise ResearchInputError("display_text must be bounded text")
        _name(event["actor"], "actor")
        at = _tick(event["at"], "event.at")
        if at in seen_times or (i and at <= events[i - 1]["at"]):
            raise ResearchInputError("event times must be strictly increasing")
        seen_times.add(at)
        _field_map(event["display_facets"], "display_facets")
        _field_map(event["scope_meta"], "scope_meta", nullable=True)
        if event["assertion"] is not None:
            assertion = _object(event["assertion"], "assertion")
            _keys(assertion, {"scope", "claim_kind", "strength", "citations",
                              "citations_complete"}, set(), "assertion")
            _scope(assertion["scope"], domain, "assertion.scope")
            _name(assertion["claim_kind"], "assertion.claim_kind")
            if assertion["strength"] not in ("TENTATIVE", "CERTIFIED"):
                raise ResearchInputError("unsupported assertion strength")
            if type(assertion["citations_complete"]) is not bool:
                raise ResearchInputError("citations_complete must be boolean")
            citations = _list(assertion["citations"], "citations", MAX_GUARANTEES)
            if len(set(citations)) != len(citations):
                raise ResearchInputError("duplicate citation")
            for ref in citations:
                _name(ref, "citation ID")

    obligations = _list(case["obligations"], "obligations", MAX_OBLIGATIONS)
    seen_obligations = set()
    for i, raw in enumerate(obligations):
        obl = _object(raw, f"obligations[{i}]")
        _keys(obl, {"id", "start_at", "end_at", "channel", "required_facets"},
              set(), f"obligations[{i}]")
        obl_id = _name(obl["id"], "obligation.id")
        if obl_id in seen_obligations:
            raise ResearchInputError("duplicate obligation ID")
        seen_obligations.add(obl_id)
        start, end = _tick(obl["start_at"], "start_at"), _tick(obl["end_at"], "end_at")
        if end < start:
            raise ResearchInputError("obligation end precedes start")
        if obl["channel"] not in ("typed", "display"):
            raise ResearchInputError("obligation channel must be typed or display")
        required = _field_map(obl["required_facets"], "required_facets")
        if not required:
            raise ResearchInputError("obligation needs at least one facet")

    event_results: list[dict] = []
    states: dict[str, list[str]] = {check: [] for check in CHECKS}
    prior: dict | None = None
    for event in events:
        local = {check: "NONE" for check in CHECKS}
        if prior is not None:
            if set(prior["display_facets"]) - set(event["display_facets"]):
                local["display_qualifier_omission"] = "ERROR"
            older = prior["scope_meta"]
            newer = event["scope_meta"]
            if older is not None and (
                newer is None or set(older) - set(newer)
            ):
                local["typed_metadata_loss"] = "ERROR"
        for obl in obligations:
            if obl["start_at"] <= event["at"] <= obl["end_at"]:
                observed = (event["scope_meta"] if obl["channel"] == "typed"
                            else event["display_facets"])
                if observed is None or any(
                    observed.get(key) != value for key, value in obl["required_facets"].items()
                ):
                    local["preservation_contract_breach"] = "ERROR"
        observation = None
        if event["assertion"] is not None:
            observation = _support(event["assertion"], guarantees, domain,
                                   event["at"], policy)
            verdict = observation["effective_cited_justification"]
            if verdict == "UNSUPPORTED_BY_CITED_EVIDENCE":
                local["unsupported_scope_assertion"] = "ERROR"
                if event["assertion"]["strength"] == "CERTIFIED":
                    local["unsupported_firm_certification"] = "ERROR"
            elif verdict == "UNKNOWN":
                local["unsupported_scope_assertion"] = "UNKNOWN"
                if event["assertion"]["strength"] == "CERTIFIED":
                    local["unsupported_firm_certification"] = "UNKNOWN"
        for check in CHECKS:
            states[check].append(local[check])
        event_results.append({"actor": event["actor"], "at": event["at"],
                              "local_checks": local, "assertion_review": observation})
        prior = event

    return {"lab_version": LAB_VERSION,
            "execution_attribution": "STANDALONE_RESEARCH_ONLY_NOT_M0",
            "case_id": case_id, "coverage_policy": policy,
            "provenance_validation": "NOT_PERFORMED_TEST_PREMISES_ONLY",
            "checks": {check: _localize(states[check], events, case["history_complete"])
                       for check in CHECKS},
            "events": event_results,
            "ario_m0_h32_runtime_score": "NOT_EVALUATED"}


def main(argv: list[str] | None = None) -> int:
    """Read one explicitly supplied small synthetic JSON file; write JSON to stdout."""
    import argparse
    import json
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Isolated H3.2 synthetic research lab; NOT M0")
    parser.add_argument("fixture", help="Research-only synthetic fixture JSON path")
    args = parser.parse_args(argv)
    try:
        path = Path(args.fixture)
        if path.is_symlink():
            raise ResearchInputError("symlink fixture refused")
        with path.open("rb") as stream:
            data = stream.read(262145)
        if len(data) > 262144:
            raise ResearchInputError("fixture exceeds 256 KiB")
        payload = json.loads(data.decode("utf-8"))
        result = evaluate_case(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, ResearchInputError) as exc:
        print(json.dumps({"lab_version": LAB_VERSION, "status": "REJECTED_INPUT",
                          "error_type": type(exc).__name__,
                          "ario_m0_h32_runtime_score": "NOT_EVALUATED"}, sort_keys=True),
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
