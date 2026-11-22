"""Issue #220: synthetic, non-persistent, non-authorizing human revision projection v0.2.

No identity authentication, memory writes, data retention decisions or real consent grants.
EXTERNALLY_VERIFIED is a CALLER ASSERTION, not a verifier implemented here.
"""
from __future__ import annotations

KINDS = frozenset({"RECORDED_STATEMENT", "SYSTEM_INTERPRETATION",
                   "PERSON_CORRECTION", "USE_PERMISSION", "USE_WITHDRAWAL",
                   "DISPUTE"})
FIELDS = frozenset({"event_id", "kind", "subject_ref", "actor_ref", "scope",
                    "ref", "target_ref", "authority"})
PERSON_ACTIONS = frozenset({"PERSON_CORRECTION", "USE_PERMISSION",
                            "USE_WITHDRAWAL", "DISPUTE"})


def project(events, *, subject_ref, scope):
    """Project a list of invented events; return a bounded recommendation only."""
    result = {
        "contract": "ARIO-HR-0.2", "status": "UNKNOWN",
        "historical_statement_refs": [], "system_interpretation_refs": [],
        "current_interpretation_ref": None, "permission": "UNKNOWN",
        "future_use": "WITHHOLD", "unresolved": [],
        "identity_authentication": "NOT_PERFORMED",
        "retention_decision": "NOT_PERFORMED", "memory_mutation": "NONE",
    }
    if (type(events) is not list or type(subject_ref) is not str or not subject_ref
            or type(scope) is not str or not scope):
        result["unresolved"].append("INVALID_PROJECTION_INPUT")
        return result
    seen, statements, interpretations = set(), set(), set()
    current, after_correction, permission = None, False, "UNKNOWN"
    for event in events:
        if (type(event) is not dict or set(event) != FIELDS
                or any(type(event[k]) is not str for k in FIELDS)
                or not event["event_id"] or not event["ref"]
                or event["kind"] not in KINDS):
            result["unresolved"].append("INVALID_EVENT_SCHEMA")
            continue
        eid, kind = event["event_id"], event["kind"]
        if eid in seen:
            result["unresolved"].append("DUPLICATE_EVENT_ID")
            continue
        seen.add(eid)
        if event["subject_ref"] != subject_ref:
            result["unresolved"].append("SUBJECT_MISMATCH")
            continue
        if event["scope"] != scope:
            # Cross-scope records are visible as non-applicable, not globally applied.
            result["unresolved"].append("OUT_OF_SCOPE_EVENT")
            continue
        if kind == "RECORDED_STATEMENT":
            statements.add(event["ref"])
            result["historical_statement_refs"].append(event["ref"])
            continue
        if kind == "SYSTEM_INTERPRETATION":
            if event["actor_ref"] != "SYNTHETIC_SYSTEM" or event["target_ref"] not in statements:
                result["unresolved"].append("UNSUPPORTED_SYSTEM_INTERPRETATION")
                continue
            interpretations.add(event["ref"])
            result["system_interpretation_refs"].append(event["ref"])
            # A late model summary must never overwrite an accepted correction.
            if not after_correction:
                if current != event["ref"] and permission == "GRANTED_FOR_CURRENT_ONLY":
                    permission = "UNKNOWN"  # permission was tied to prior interpretation
                current = event["ref"]
            continue
        if kind in PERSON_ACTIONS:
            if event["actor_ref"] != subject_ref or event["authority"] != "EXTERNALLY_VERIFIED":
                result["unresolved"].append("PERSON_AUTHORITY_NOT_ESTABLISHED")
                continue
            if kind == "PERSON_CORRECTION":
                if current is None or event["target_ref"] != current:
                    result["unresolved"].append("AMBIGUOUS_OR_STALE_CORRECTION_TARGET")
                    continue
                if current != event["ref"] and permission == "GRANTED_FOR_CURRENT_ONLY":
                    permission = "UNKNOWN"  # correction cannot inherit old consent
                current, after_correction = event["ref"], True
            elif kind == "USE_PERMISSION":
                if not current or event["target_ref"] != current:
                    result["unresolved"].append("PERMISSION_TARGET_MISMATCH")
                    continue
                permission = "GRANTED_FOR_CURRENT_ONLY"
            elif kind == "USE_WITHDRAWAL":
                # Withdrawal is a separate future-use decision; no deletion assertion.
                permission = "WITHDRAWN"
            elif kind == "DISPUTE":
                result["unresolved"].append("PERSON_DISPUTES_INTERPRETATION")
    result["current_interpretation_ref"] = current
    result["permission"] = permission
    result["unresolved"] = sorted(set(result["unresolved"]))
    if permission == "WITHDRAWN":
        result["status"], result["future_use"] = "WITHDRAWN", "DENY"
    elif result["unresolved"]:
        result["status"], result["future_use"] = "UNKNOWN", "WITHHOLD"
    elif current and permission == "GRANTED_FOR_CURRENT_ONLY":
        result["status"], result["future_use"] = "REVIEWABLE", "CURRENT_REF_ONLY"
    else:
        result["status"], result["future_use"] = "UNKNOWN", "WITHHOLD"
    return result
