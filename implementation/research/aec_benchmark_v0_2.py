"""AEC-Bench v0.2: deterministic 120-fixture development corpus and policy harness.

Research-only synthetic harness. It does not invoke the Ario runtime or external systems.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

VERSION = "AEC-Bench-0.2"
FAMILIES = (
    "lineage_dependence", "relay_replay_identity", "claim_disposition", "scope",
    "schema_version", "integrity_authenticity", "temporal_provenance",
    "revision_history", "composition_dependencies", "uncertainty_abstention",
)
STATUSES = {"SUPPORTED", "CONTRADICTED", "CONTESTED", "UNKNOWN", "REJECTED"}
VARIANTS = (
    "positive_control", "positive_control_b", "positive_control_c",
    "adversarial", "adversarial_b", "adversarial_c",
    "boundary", "boundary_b", "boundary_c",
    "counterfactual_base", "counterfactual_delta", "supplemental_control",
)

@dataclass(frozen=True)
class Fixture:
    case_id: str
    family: str
    variant: str
    pair_group: str
    input: dict
    expected: dict
    rationale: str

def _fixture(family: str, index: int, variant: str, input_data: dict,
             expected: dict, rationale: str) -> Fixture:
    return Fixture(
        case_id=f"AEC02_{family.upper()}_{index:02d}",
        family=family,
        variant=variant,
        pair_group=f"{family}_PAIR_01" if index in (10, 11) else "",
        input=input_data,
        expected=expected,
        rationale=rationale,
    )



def changed_input_paths(left: dict, right: dict) -> list[str]:
    """Return atomic JSON-pointer-like paths that differ between two inputs.

    This is a structural check only: it does not establish that a changed field
    is causally relevant or that the pair's expected labels are correct.
    """
    def visit(a, b, path: str) -> list[str]:
        if type(a) is not type(b):
            return [path or "/"]
        if isinstance(a, dict):
            changed: list[str] = []
            for key in sorted(set(a) | set(b), key=lambda item: str(item)):
                token = str(key).replace("~", "~0").replace("/", "~1")
                child = f"{path}/{token}" if path else f"/{token}"
                if key not in a or key not in b:
                    changed.append(child)
                else:
                    changed.extend(visit(a[key], b[key], child))
            return changed
        if isinstance(a, (list, tuple)):
            changed = []
            if len(a) != len(b):
                changed.append(f"{path}/@length" if path else "/@length")
            for index in range(min(len(a), len(b))):
                child = f"{path}/{index}" if path else f"/{index}"
                changed.extend(visit(a[index], b[index], child))
            return changed
        return [path or "/"] if a != b else []

    return visit(left, right, "")


def audit_counterfactual_pairs(fixtures: tuple[Fixture, ...] | list[Fixture]) -> dict:
    """Audit declared pairs for one family and exactly one atomic input delta."""
    groups: dict[str, list[Fixture]] = {}
    for fixture in fixtures:
        if fixture.pair_group:
            groups.setdefault(fixture.pair_group, []).append(fixture)

    pair_rows = []
    for group_id in sorted(groups):
        members = groups[group_id]
        issues: list[str] = []
        changed_paths: list[str] = []
        if len(members) != 2:
            issues.append("PAIR_MEMBER_COUNT_NOT_TWO")
        else:
            first, second = members
            if first.family != second.family:
                issues.append("PAIR_FAMILY_MISMATCH")
            if first.case_id == second.case_id:
                issues.append("DUPLICATE_CASE_ID")
            changed_paths = changed_input_paths(first.input, second.input)
            if len(changed_paths) != 1:
                issues.append("EXPECTED_EXACTLY_ONE_ATOMIC_INPUT_CHANGE")
        pair_rows.append({
            "pair_group": group_id,
            "family": members[0].family if members else None,
            "case_ids": [member.case_id for member in members],
            "changed_input_paths": changed_paths,
            "valid": not issues,
            "issues": issues,
        })

    valid_count = sum(row["valid"] for row in pair_rows)
    return {
        "audit_kind": "STRUCTURAL_COUNTERFACTUAL_PAIR_AUDIT",
        "pair_group_count": len(pair_rows),
        "valid_pair_count": valid_count,
        "invalid_pair_count": len(pair_rows) - valid_count,
        "pairs": pair_rows,
        "limitation": (
            "A single structural input delta does not establish causal relevance, "
            "semantic isolation, or correctness of either expected label."
        ),
    }


def corpus() -> tuple[Fixture, ...]:
    """Build 10 families x 12 authored deterministic fixtures."""
    rows: list[Fixture] = []
    # Lineage: source roots are declarations, never proof of real-world independence.
    lineage = [
      ({"sources":["A","B"],"roots":{"A":["R1"],"B":["R2"]}}, {"root_count":2,"status":"UNKNOWN"}, "Two declared roots; truth remains unknown."),
      ({"sources":["A","B","C"],"roots":{"A":["R1"],"B":["R2"],"C":["R3"]}}, {"root_count":3,"status":"UNKNOWN"}, "Three distinct declared roots."),
      ({"sources":["A","B"],"roots":{"A":["R1"],"B":["R1"]}}, {"root_count":1,"status":"UNKNOWN"}, "Two sources share one declared root."),
      ({"sources":["A","B","C"],"roots":{"A":["R1"],"B":["R1"],"C":["R1"]}}, {"root_count":1,"status":"UNKNOWN"}, "Relay fan-out from one root."),
      ({"sources":["A","B"],"roots":{"A":[],"B":["R2"]}}, {"root_count":None,"status":"UNKNOWN"}, "One source has missing ancestry."),
      ({"sources":["A","B"],"roots":{"A":["R1","R2"],"B":["R2","R3"]}}, {"root_count":3,"status":"UNKNOWN"}, "Overlapping multi-root ancestry."),
      ({"sources":["A","B"],"roots":{"A":["R1"],"B":["R2"]},"unresolved_parent":True}, {"root_count":None,"status":"UNKNOWN"}, "Unresolved parent prevents complete root count."),
      ({"sources":["A","B"],"roots":{"A":["R1"],"B":["R1"]},"claimed_independent":True}, {"root_count":1,"status":"UNKNOWN"}, "Independence claim conflicts with shared root."),
      ({"sources":["A"],"roots":{"A":["R1"]}}, {"root_count":1,"status":"UNKNOWN"}, "Single-source control."),
      ({"sources":["A","B"],"roots":{"A":["R1"],"B":["R2"]},"edge_missing":True}, {"root_count":None,"status":"UNKNOWN"}, "Missing derivation edge blocks complete lineage."),
      ({"sources":["A","B"],"roots":{"A":["R1"],"B":["R2"]},"edge_missing":False}, {"root_count":2,"status":"UNKNOWN"}, "Counterfactual: restore the one missing lineage edge."),
      ({"sources":["A","B"],"roots":{"A":["R1"],"B":["R2"]},"declared_shared_ancestor":True}, {"root_count":1,"status":"UNKNOWN"}, "Shared ancestor collapses apparent independence."),
    ]
    # Relay identity: sender uniqueness and provenance-root uniqueness are independent.
    relay = [
      ({"records":[("A","m1"),("B","m2")]}, {"unique_senders":2,"status":"UNKNOWN"}, "Distinct senders and messages."),
      ({"records":[("A","m1"),("A","m1")]}, {"unique_senders":1,"status":"UNKNOWN"}, "Exact replay."),
      ({"records":[("A","m1"),("A","m2")]}, {"unique_senders":1,"status":"UNKNOWN"}, "One sender emits two records."),
      ({"records":[("A","m1"),("B","m2")],"same_root":True}, {"unique_senders":2,"status":"UNKNOWN"}, "Distinct senders may still share ancestry."),
      ({"records":[("A","m1"),("B","m1")]}, {"unique_senders":2,"status":"UNKNOWN"}, "Same message identifier from different senders is a collision to investigate."),
      ({"records":[("A","m1"),("B","m2")],"replay_window_exceeded":True}, {"unique_senders":2,"status":"UNKNOWN"}, "Time-window metadata changes replay assessment."),
      ({"records":[("A","m1"),("A","m1")],"payload_differs":True}, {"unique_senders":1,"status":"REJECTED"}, "Same identifier with altered payload."),
      ({"records":[("A","m1"),("B","m2")],"sender_unverified":True}, {"unique_senders":None,"status":"UNKNOWN"}, "Unverified sender identity cannot be counted as authenticated."),
      ({"records":[("A","m1")]}, {"unique_senders":1,"status":"UNKNOWN"}, "Single sender control."),
      ({"records":[("A","m1"),("B","m2")],"alias_collision":True}, {"unique_senders":None,"status":"UNKNOWN"}, "Unresolved aliases prevent identity count."),
      ({"records":[("A","m1"),("B","m2")],"alias_collision":False}, {"unique_senders":2,"status":"UNKNOWN"}, "Counterfactual: resolve the one alias-collision flag."),
      ({"records":[("A","m1"),("A","m2"),("B","m3")]}, {"unique_senders":2,"status":"UNKNOWN"}, "Two senders across three records."),
    ]
    claim = [
      ({"labels":["SUPPORTS"]}, {"status":"SUPPORTED"}, "Single explicit support record."),
      ({"labels":["CONTRADICTS"]}, {"status":"CONTRADICTED"}, "Single explicit contradiction record."),
      ({"labels":["SUPPORTS","CONTRADICTS"]}, {"status":"CONTESTED"}, "Directly conflicting evidence."),
      ({"labels":["SUPPORTS","UNKNOWN"]}, {"status":"UNKNOWN"}, "Support plus unresolved evidence is not consensus."),
      ({"labels":["SUPPORTS","SUPPORTS","CONTRADICTS"]}, {"status":"CONTESTED"}, "Majority support does not erase contradiction."),
      ({"labels":["REFUTES"]}, {"status":"CONTRADICTED"}, "Explicit refutation."),
      ({"labels":[]}, {"status":"UNKNOWN"}, "No evidence."),
      ({"labels":["UNSUPPORTED","SUPPORTS"]}, {"status":"CONTESTED"}, "Unsupported and supported are not silently collapsed."),
      ({"labels":["SUPPORTS"],"evidence_eligible":False}, {"status":"UNKNOWN"}, "Ineligible evidence cannot support claim."),
      ({"labels":["CONTRADICTS"],"scope_valid":False}, {"status":"UNKNOWN"}, "Out-of-scope contradiction cannot decide target claim."),
      ({"labels":["CONTRADICTS"],"scope_valid":True}, {"status":"CONTRADICTED"}, "Counterfactual: make the same contradiction eligible by restoring scope validity."),
      ({"labels":["SUPPORTS"],"provenance_missing":True}, {"status":"UNKNOWN"}, "Support without traceable provenance remains unknown."),
    ]
    scope = [
      ({"claim_scope":"S","evidence_scope":"S"}, {"scope":"IN_SCOPE","status":"UNKNOWN"}, "Exact scope match."),
      ({"claim_scope":"S","evidence_scope":"S.sub"}, {"scope":"OUT_OF_SCOPE","status":"REJECTED"}, "Narrower evidence scope cannot justify the broader claim."),
      ({"claim_scope":"S.sub","evidence_scope":"S"}, {"scope":"IN_SCOPE","status":"UNKNOWN"}, "Broader evidence may cover narrower claim subject to declared semantics."),
      ({"claim_scope":"S","evidence_scope":"OTHER"}, {"scope":"OUT_OF_SCOPE","status":"REJECTED"}, "Disjoint scope."),
      ({"claim_scope":"S","evidence_scope":None}, {"scope":"UNKNOWN","status":"UNKNOWN"}, "Missing evidence scope."),
      ({"claim_scope":"S","evidence_scope":"S","time_mismatch":True}, {"scope":"OUT_OF_SCOPE","status":"REJECTED"}, "Temporal scope mismatch."),
      ({"claim_scope":"S","evidence_scope":"S","actor_mismatch":True}, {"scope":"OUT_OF_SCOPE","status":"REJECTED"}, "Actor scope mismatch."),
      ({"claim_scope":"S","evidence_scope":"S","jurisdiction_mismatch":True}, {"scope":"OUT_OF_SCOPE","status":"REJECTED"}, "Jurisdiction mismatch."),
      ({"claim_scope":"S","evidence_scope":"S","scope_version_unknown":True}, {"scope":"UNKNOWN","status":"UNKNOWN"}, "Unknown scope semantics."),
      ({"claim_scope":"S.sub","evidence_scope":"S","boundary_ambiguous":True}, {"scope":"UNKNOWN","status":"UNKNOWN"}, "Boundary ambiguity."),
      ({"claim_scope":"S.sub","evidence_scope":"S","boundary_ambiguous":False}, {"scope":"IN_SCOPE","status":"UNKNOWN"}, "Counterfactual: resolve the single scope-boundary ambiguity."),
      ({"claim_scope":"S","evidence_scope":"S","matched_dimensions":True}, {"scope":"IN_SCOPE","status":"UNKNOWN"}, "All declared dimensions match; truth still unknown."),
    ]
    schema = [
      ({"version":"1.0","required_present":True}, {"schema":"ACCEPT","status":"UNKNOWN"}, "Supported baseline version."),
      ({"version":"1.1","required_present":True}, {"schema":"ACCEPT","status":"UNKNOWN"}, "Supported minor version."),
      ({"version":"2.0","required_present":True}, {"schema":"REJECT","status":"REJECTED"}, "Unsupported major version."),
      ({"version":"1.99","required_present":True}, {"schema":"REJECT","status":"REJECTED"}, "Unsupported minor version."),
      ({"version":"1.0","required_present":False}, {"schema":"REJECT","status":"REJECTED"}, "Missing required field."),
      ({"version":"1.0","required_present":True,"unknown_critical":True}, {"schema":"REJECT","status":"REJECTED"}, "Unknown critical field."),
      ({"version":"1.0","required_present":True,"unknown_optional":True}, {"schema":"ACCEPT_WITH_UNKNOWN","status":"UNKNOWN"}, "Unknown optional field preserved."),
      ({"version":"1.0","required_present":True,"downgrade":True}, {"schema":"REJECT","status":"REJECTED"}, "Downgrade attempt."),
      ({"version":"1.x","required_present":True}, {"schema":"REJECT","status":"REJECTED"}, "Malformed semantic version."),
      ({"version":"1.0","required_present":True,"compatibility_unstated":True}, {"schema":"UNKNOWN","status":"UNKNOWN"}, "Compatibility range not declared."),
      ({"version":"1.0","required_present":True,"compatibility_unstated":False}, {"schema":"ACCEPT","status":"UNKNOWN"}, "Counterfactual: state compatibility for the same supported schema."),
      ({"version":"0.9","required_present":True}, {"schema":"REJECT","status":"REJECTED"}, "Legacy unsupported version."),
    ]
    integrity = [
      ({"digest":"valid","auth":"VERIFIED"}, {"integrity":"VALID","auth":"VERIFIED","status":"UNKNOWN"}, "Valid digest and verified authentication."),
      ({"digest":"valid","auth":"UNVERIFIED"}, {"integrity":"VALID","auth":"UNVERIFIED","status":"UNKNOWN"}, "Digest does not authenticate source."),
      ({"digest":"invalid","auth":"VERIFIED"}, {"integrity":"INVALID","auth":"VERIFIED","status":"REJECTED"}, "Payload digest mismatch."),
      ({"digest":None,"auth":"UNVERIFIED"}, {"integrity":"UNKNOWN","auth":"UNVERIFIED","status":"UNKNOWN"}, "Digest absent."),
      ({"digest":"valid","auth":"FAILED"}, {"integrity":"VALID","auth":"FAILED","status":"REJECTED"}, "Integrity valid but authentication failed."),
      ({"digest":"valid","auth":"NOT_APPLICABLE"}, {"integrity":"VALID","auth":"NOT_APPLICABLE","status":"UNKNOWN"}, "No authentication mechanism claimed."),
      ({"digest":"altered","auth":"VERIFIED"}, {"integrity":"INVALID","auth":"VERIFIED","status":"REJECTED"}, "Altered payload."),
      ({"digest":"valid","auth":"UNKNOWN_KEY"}, {"integrity":"VALID","auth":"UNVERIFIED","status":"UNKNOWN"}, "Unknown signing key."),
      ({"digest":"valid","auth":"VERIFIED","signature_revoked":True}, {"integrity":"VALID","auth":"FAILED","status":"REJECTED"}, "Revoked signing authority."),
      ({"digest":"valid","auth":"UNVERIFIED","algorithm_unsupported":True}, {"integrity":"UNKNOWN","auth":"UNVERIFIED","status":"UNKNOWN"}, "Unsupported digest algorithm."),
      ({"digest":"valid","auth":"UNVERIFIED","algorithm_unsupported":False}, {"integrity":"VALID","auth":"UNVERIFIED","status":"UNKNOWN"}, "Counterfactual: use a supported digest algorithm."),
      ({"digest":"valid","auth":"VERIFIED","content_semantics_unchecked":True}, {"integrity":"VALID","auth":"VERIFIED","status":"UNKNOWN"}, "Authenticated content is not automatically true."),
    ]
    temporal = [
      ({"event":10,"observed":11,"recorded":12}, {"temporal":"ORDERED","status":"UNKNOWN"}, "Consistent event/observation/recording times."),
      ({"event":12,"observed":10,"recorded":13}, {"temporal":"ANOMALY","status":"UNKNOWN"}, "Observation precedes declared event."),
      ({"event":10,"observed":None,"recorded":12}, {"temporal":"PARTIAL","status":"UNKNOWN"}, "Missing observation time."),
      ({"event":10,"observed":11,"recorded":9}, {"temporal":"ANOMALY","status":"UNKNOWN"}, "Record time precedes observation."),
      ({"event":10,"observed":11,"recorded":12,"clock_uncertain":True}, {"temporal":"UNCERTAIN","status":"UNKNOWN"}, "Clock uncertainty blocks strict ordering."),
      ({"event":1,"observed":100,"recorded":101}, {"temporal":"STALE","status":"UNKNOWN"}, "Old event arrives much later."),
      ({"event":10,"observed":11,"recorded":12,"superseded":True}, {"temporal":"SUPERSEDED","status":"UNKNOWN"}, "Superseded record retained historically."),
      ({"event":10,"observed":11,"recorded":12,"timezone_missing":True}, {"temporal":"UNKNOWN","status":"UNKNOWN"}, "Timezone absent."),
      ({"event":10,"observed":11,"recorded":12,"future_skew":True}, {"temporal":"ANOMALY","status":"UNKNOWN"}, "Future clock skew."),
      ({"event":10,"observed":11,"recorded":12,"clock_uncertain":True}, {"temporal":"UNCERTAIN","status":"UNKNOWN"}, "Clock uncertainty blocks strict temporal ordering."),
      ({"event":10,"observed":11,"recorded":12,"clock_uncertain":False}, {"temporal":"ORDERED","status":"UNKNOWN"}, "Counterfactual: remove the single clock-uncertainty flag."),
      ({"event":10,"observed":11,"recorded":12,"timestamp_conflict":True}, {"temporal":"UNCERTAIN","status":"UNKNOWN"}, "Conflicting timestamp sources."),
    ]
    revision = [
      ({"history":["v1","v2"],"operation":"append"}, {"history":"PRESERVED","status":"UNKNOWN"}, "Append-only revision."),
      ({"history":["v1","v2"],"operation":"correct","prior_retained":True}, {"history":"PRESERVED","status":"UNKNOWN"}, "Correction retains prior record."),
      ({"history":["v1"],"operation":"erase","prior_retained":False}, {"history":"ERASURE_DETECTED","status":"REJECTED"}, "Unauthorized historical erasure."),
      ({"history":["v1","v2a","v2b"],"operation":"fork"}, {"history":"FORKED","status":"UNKNOWN"}, "Revision fork preserved."),
      ({"history":["v1","v2","v3"],"operation":"merge","parents_recorded":True}, {"history":"MERGED","status":"UNKNOWN"}, "Merge records both parents."),
      ({"history":["v1","v2"],"operation":"supersede","prior_retained":True}, {"history":"SUPERSEDED","status":"UNKNOWN"}, "Supersession is not deletion."),
      ({"history":["v1","v2"],"operation":"correct","prior_retained":False}, {"history":"ERASURE_DETECTED","status":"REJECTED"}, "Correction without prior retention."),
      ({"history":["v1","v2"],"operation":"fork","parent_missing":True}, {"history":"UNKNOWN","status":"UNKNOWN"}, "Missing fork parent."),
      ({"history":["v1"],"operation":"rewrite","audit_trail":False}, {"history":"ERASURE_DETECTED","status":"REJECTED"}, "Silent rewrite."),
      ({"history":["v1","v2"],"operation":"append","hash_chain_valid":False}, {"history":"INTEGRITY_FAILURE","status":"REJECTED"}, "Broken history hash chain."),
      ({"history":["v1","v2"],"operation":"append","hash_chain_valid":True}, {"history":"PRESERVED","status":"UNKNOWN"}, "Counterfactual: restore the single history-chain integrity condition."),
      ({"history":["v1","v2"],"operation":"append","prior_retained":True}, {"history":"PRESERVED","status":"UNKNOWN"}, "Positive append control."),
    ]
    composition = [
      ({"premises":["P1"],"requirements":["P1"],"composition_checks":{"dependency":"COMPATIBLE","scope":"COMPATIBLE","temporal":"COMPATIBLE","claim_kind":"COMPATIBLE"},"composition_checks_complete":True}, {"composition":"VALID","status":"UNKNOWN"}, "All required premises are present and all four composition compatibility dimensions are explicitly checked."),
      ({"premises":["P1"],"requirements":["P1","P2"]}, {"composition":"INCOMPLETE","status":"UNKNOWN"}, "One required premise missing."),
      ({"premises":["P1","P2"],"requirements":["P1","P2"],"incompatible":True}, {"composition":"INVALID","status":"REJECTED"}, "Premises conflict despite local validity."),
      ({"premises":["P1","P2"],"requirements":["P1","P2"],"composition_checks":{"dependency":"SHARED_DEPENDENCY","scope":"COMPATIBLE","temporal":"COMPATIBLE","claim_kind":"COMPATIBLE"},"composition_checks_complete":True}, {"composition":"VALID_WITH_SHARED_DEPENDENCY","status":"UNKNOWN"}, "Shared dependency is explicitly recorded; no independent-root or truth claim follows."),
      ({"premises":["P1"],"requirements":["P1"],"cycle":True}, {"composition":"INVALID","status":"REJECTED"}, "Circular dependency."),
      ({"premises":["P1","P2"],"requirements":["P1","P2"],"time_incompatible":True}, {"composition":"INVALID","status":"REJECTED"}, "Temporal incompatibility."),
      ({"premises":["P1","P2"],"requirements":["P1","P2"],"scope_incompatible":True}, {"composition":"INVALID","status":"REJECTED"}, "Scope incompatibility."),
      ({"premises":["P1","P2"],"requirements":["P1","P2"],"claim_kind_mismatch":True}, {"composition":"INVALID","status":"REJECTED"}, "Claim-kind mismatch."),
      ({"premises":[],"requirements":["P1"]}, {"composition":"INCOMPLETE","status":"UNKNOWN"}, "No premise available."),
      ({"premises":["P1","P2"],"requirements":["P1","P2"],"composition_checks":{"dependency":"COMPATIBLE","scope":"COMPATIBLE","temporal":"COMPATIBLE","claim_kind":"COMPATIBLE"},"composition_checks_complete":False}, {"composition":"UNKNOWN","status":"UNKNOWN"}, "All local records are present and checks are listed, but their completeness is not established; global validity remains unknown."),
      ({"premises":["P1","P2"],"requirements":["P1","P2"],"composition_checks":{"dependency":"COMPATIBLE","scope":"COMPATIBLE","temporal":"COMPATIBLE","claim_kind":"COMPATIBLE"},"composition_checks_complete":True}, {"composition":"VALID","status":"UNKNOWN"}, "Counterfactual: mark the same explicit four-dimension compatibility check set complete."),
      ({"premises":["P1","P2"],"requirements":["P1","P2"],"firewall_bypassed":True}, {"composition":"INVALID","status":"REJECTED"}, "Composition firewall bypass."),
    ]
    uncertainty = [
      ({"evidence":["E1"],"complete":True}, {"status":"UNKNOWN"}, "Evidence exists but does not establish truth."),
      ({"evidence":[],"complete":False}, {"status":"UNKNOWN"}, "No evidence and incomplete history."),
      ({"evidence":["E1","E2"],"conflict":True}, {"status":"CONTESTED"}, "Conflicting evidence."),
      ({"evidence":["E1"],"forced_choice":True}, {"status":"UNKNOWN"}, "Forced-choice pressure must not erase uncertainty."),
      ({"evidence":["E1"],"provenance_missing":True}, {"status":"UNKNOWN"}, "Missing provenance."),
      ({"evidence":["E1"],"scope_unknown":True}, {"status":"UNKNOWN"}, "Unknown scope."),
      ({"evidence":["E1"],"abstain":True}, {"status":"UNKNOWN"}, "Explicit abstention."),
      ({"evidence":["E1"],"contradiction_unresolved":True}, {"status":"CONTESTED"}, "Unresolved contradiction."),
      ({"evidence":["E1"],"coverage_partial":True}, {"status":"UNKNOWN"}, "Partial coverage."),
      ({"evidence":["E1"],"human_review_pending":True}, {"status":"UNKNOWN"}, "Human review pending; the claim remains unresolved."),
      ({"evidence":["E1"],"human_review_pending":False}, {"status":"UNKNOWN"}, "Counterfactual: clear the human-review-pending flag; evidence remains unchanged."),
      ({"evidence":["E1"],"assertion_confident":True}, {"status":"UNKNOWN"}, "Confidence language is not evidence."),
    ]
    groups = [lineage, relay, claim, scope, schema, integrity, temporal, revision, composition, uncertainty]
    for family, entries in zip(FAMILIES, groups):
        assert len(entries) == 12
        for idx, (data, expected, why) in enumerate(entries, 1):
            rows.append(_fixture(family, idx, VARIANTS[idx-1], data, expected, why))
    return tuple(rows)

def _evaluate(f: Fixture) -> dict:
    """Reference policy evaluator for fixture-level invariants; not Ario runtime."""
    d = f.input
    if f.family == "lineage_dependence":
        sources = d.get("sources")
        root_map = d.get("roots")
        # A root count is determinate only when every declared source has
        # exactly one explicit, non-empty ancestry entry. Do not silently
        # count a partial mapping or ignore undeclared extra source entries.
        if (
            not isinstance(sources, list)
            or not sources
            or any(not isinstance(source, str) or not source.strip() for source in sources)
            or len(set(sources)) != len(sources)
            or not isinstance(root_map, dict)
            or set(root_map) != set(sources)
            or d.get("unresolved_parent")
            or d.get("edge_missing")
            or d.get("one_root_hidden")
        ):
            return {"root_count": None, "status": "UNKNOWN"}
        ancestry_roots = []
        for source in sources:
            source_roots = root_map[source]
            if (
                not isinstance(source_roots, (list, tuple))
                or not source_roots
                or any(not isinstance(root, str) or not root.strip() for root in source_roots)
            ):
                return {"root_count": None, "status": "UNKNOWN"}
            ancestry_roots.extend(source_roots)
        roots = set(ancestry_roots)
        if d.get("declared_shared_ancestor"):
            return {"root_count": 1, "status": "UNKNOWN"}
        return {"root_count": len(roots), "status": "UNKNOWN"}
    if f.family == "relay_replay_identity":
        if d.get("sender_unverified") or d.get("alias_collision") or d.get("one_record_missing"):
            return {"unique_senders": None, "status": "UNKNOWN"}
        if d.get("payload_differs"):
            return {"unique_senders": len({x[0] for x in d["records"]}), "status": "REJECTED"}
        return {"unique_senders": len({x[0] for x in d["records"]}), "status": "UNKNOWN"}
    if f.family == "claim_disposition":
        if not d.get("evidence_eligible", True) or not d.get("scope_valid", True) or d.get("provenance_missing"):
            return {"status": "UNKNOWN"}
        labels = set(d["labels"])
        if "SUPPORTS" in labels and ({"CONTRADICTS", "REFUTES", "UNSUPPORTED"} & labels):
            return {"status": "CONTESTED"}
        if "UNKNOWN" in labels:
            return {"status": "UNKNOWN"}
        if "SUPPORTS" in labels: return {"status": "SUPPORTED"}
        if {"CONTRADICTS", "REFUTES"} & labels: return {"status": "CONTRADICTED"}
        return {"status": "UNKNOWN"}
    if f.family == "scope":
        if d.get("evidence_scope") is None or d.get("scope_version_unknown") or d.get("boundary_ambiguous"):
            return {"scope": "UNKNOWN", "status": "UNKNOWN"}
        if d["evidence_scope"] == "OTHER" or (d["claim_scope"] == "S" and d["evidence_scope"] == "S.sub") or any(d.get(k) for k in ("time_mismatch","actor_mismatch","jurisdiction_mismatch","excluded_population")):
            return {"scope": "OUT_OF_SCOPE", "status": "REJECTED"}
        return {"scope": "IN_SCOPE", "status": "UNKNOWN"}
    if f.family == "schema_version":
        if d.get("compatibility_unstated"): return {"schema":"UNKNOWN","status":"UNKNOWN"}
        if d.get("version") not in {"1.0","1.1"} or not d.get("required_present") or d.get("unknown_critical") or d.get("downgrade") or d.get("critical_semantics_changed"):
            return {"schema":"REJECT","status":"REJECTED"}
        return {"schema":"ACCEPT_WITH_UNKNOWN" if d.get("unknown_optional") else "ACCEPT","status":"UNKNOWN"}
    if f.family == "integrity_authenticity":
        if d.get("algorithm_unsupported"): return {"integrity":"UNKNOWN","auth":"UNVERIFIED","status":"UNKNOWN"}
        integrity = "INVALID" if d["digest"] in {"invalid","altered"} else ("VALID" if d["digest"]=="valid" else "UNKNOWN")
        if d.get("signature_revoked") or d["auth"] == "FAILED":
            auth = "FAILED"
        elif d["auth"] in {"VERIFIED", "NOT_APPLICABLE"}:
            auth = d["auth"]
        else:
            auth = "UNVERIFIED"
        status = "REJECTED" if integrity=="INVALID" or auth=="FAILED" else "UNKNOWN"
        return {"integrity":integrity,"auth":auth,"status":status}
    if f.family == "temporal_provenance":
        event_time = d.get("event")
        observed_time = d.get("observed")
        recorded_time = d.get("recorded")
        times = (event_time, observed_time, recorded_time)
        if d.get("clock_uncertain") or d.get("timestamp_conflict"):
            t = "UNCERTAIN"
        elif d.get("timezone_missing"):
            t = "UNKNOWN"
        elif d.get("superseded"):
            t = "SUPERSEDED"
        elif d.get("future_skew"):
            t = "ANOMALY"
        elif any(value is None for value in times):
            # Missing event/observation/recording time cannot support strict ordering.
            t = "PARTIAL"
        elif any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in times
        ):
            t = "UNKNOWN"
        elif observed_time < event_time or recorded_time < observed_time:
            t = "ANOMALY"
        elif recorded_time - event_time > 50:
            t = "STALE"
        else:
            t = "ORDERED"
        return {"temporal": t, "status": "UNKNOWN"}
    if f.family == "revision_history":
        if d.get("hash_chain_valid") is False: h="INTEGRITY_FAILURE"
        elif d["operation"] in {"erase","rewrite"} or (d["operation"]=="correct" and not d.get("prior_retained",True)): h="ERASURE_DETECTED"
        elif d.get("parent_missing") or (d["operation"]=="merge" and not d.get("parents_recorded",True)): h="UNKNOWN"
        elif d["operation"]=="fork": h="FORKED"
        elif d["operation"]=="merge": h="MERGED"
        elif d["operation"]=="supersede": h="SUPERSEDED"
        else: h="PRESERVED"
        return {"history":h,"status":"REJECTED" if h in {"INTEGRITY_FAILURE","ERASURE_DETECTED"} else "UNKNOWN"}
    if f.family == "composition_dependencies":
        allowed_fields = {
            "premises", "requirements",
            "incompatible", "cycle", "time_incompatible",
            "scope_incompatible", "claim_kind_mismatch", "firewall_bypassed",
            "composition_checks", "composition_checks_complete",
        }
        if set(d) - allowed_fields:
            return {"composition": "UNKNOWN", "status": "UNKNOWN"}

        premises = d.get("premises")
        requirements = d.get("requirements")
        if (
            not isinstance(premises, list)
            or not isinstance(requirements, list)
            or not requirements
            or any(not isinstance(item, str) or not item.strip() for item in premises + requirements)
            or len(set(premises)) != len(premises)
            or len(set(requirements)) != len(requirements)
        ):
            return {"composition": "UNKNOWN", "status": "UNKNOWN"}

        incompatibility_flags = (
            "incompatible", "cycle", "time_incompatible",
            "scope_incompatible", "claim_kind_mismatch", "firewall_bypassed",
        )
        if any(key in d and type(d[key]) is not bool for key in incompatibility_flags):
            return {"composition": "UNKNOWN", "status": "UNKNOWN"}
        if any(d.get(key) is True for key in incompatibility_flags):
            return {"composition": "INVALID", "status": "REJECTED"}

        missing_requirements = not set(requirements).issubset(set(premises))
        if missing_requirements:
            return {"composition": "INCOMPLETE", "status": "UNKNOWN"}

        checks = d.get("composition_checks")
        checks_complete = d.get("composition_checks_complete")
        required_checks = {"dependency", "scope", "temporal", "claim_kind"}
        if (
            not isinstance(checks, dict)
            or set(checks) != required_checks
            or type(checks_complete) is not bool
        ):
            return {"composition": "UNKNOWN", "status": "UNKNOWN"}

        dependency_states = {"COMPATIBLE", "SHARED_DEPENDENCY", "INCOMPATIBLE", "UNKNOWN"}
        other_states = {"COMPATIBLE", "INCOMPATIBLE", "UNKNOWN"}
        if (
            checks["dependency"] not in dependency_states
            or any(checks[key] not in other_states for key in ("scope", "temporal", "claim_kind"))
        ):
            return {"composition": "UNKNOWN", "status": "UNKNOWN"}

        # A known incompatibility is sufficient to reject even if another
        # required check is unresolved or the check set is not complete.
        if "INCOMPATIBLE" in checks.values():
            return {"composition": "INVALID", "status": "REJECTED"}
        if not checks_complete or "UNKNOWN" in checks.values():
            return {"composition": "UNKNOWN", "status": "UNKNOWN"}
        if checks["dependency"] == "SHARED_DEPENDENCY":
            return {"composition": "VALID_WITH_SHARED_DEPENDENCY", "status": "UNKNOWN"}
        if all(value == "COMPATIBLE" for value in checks.values()):
            return {"composition": "VALID", "status": "UNKNOWN"}
        return {"composition": "UNKNOWN", "status": "UNKNOWN"}
    if f.family == "uncertainty_abstention":
        if d.get("conflict") or d.get("contradiction_unresolved"): return {"status":"CONTESTED"}
        return {"status":"UNKNOWN"}
    raise ValueError(f.family)

def score() -> dict:
    fixtures = corpus()
    results = []
    for f in fixtures:
        observed = _evaluate(f)
        results.append({
            "case_id": f.case_id, "family": f.family, "variant": f.variant,
            "pair_group": f.pair_group, "expected": f.expected,
            "observed": observed, "match": observed == f.expected,
            "rationale": f.rationale,
        })
    by_family = {}
    for family in FAMILIES:
        group = [x for x in results if x["family"] == family]
        by_family[family] = {
            "cases": len(group),
            "matches": sum(x["match"] for x in group),
            "fixture_contract_conformance": sum(x["match"] for x in group) / len(group),
        }
    pair_audit = audit_counterfactual_pairs(fixtures)
    return {
        "benchmark": VERSION,
        "corpus_kind": "SYNTHETIC_DETERMINISTIC_PUBLIC_DEVELOPMENT",
        "case_count": len(fixtures),
        "family_count": len(FAMILIES),
        "counterfactual_pair_validation": pair_audit,
        "policy_identity": "AEC_BENCH_FIXTURE_REFERENCE_EVALUATOR_NOT_ARIO_RUNTIME",
        "by_family": by_family,
        "cases": results,
        "limitations": [
            "All fixtures and oracle labels are synthetic and author-defined.",
            "The reference evaluator is not an Ario runtime call or external-system adapter.",
            "Per-family fixture-contract conformance measures this evaluator against author-defined labels only; it is not a research performance metric.",
            "No aggregate or composite benchmark score is produced.",
            "No real-world source independence, authenticity, truth, model behavior, security, privacy, or superiority is established.",
            "No hidden evaluation set is included in this public corpus.",
        ],
    }

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(score(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")

if __name__ == "__main__":
    main()
