"""AEC-Bench v0.2: deterministic 120-fixture development corpus and policy harness.

Research-only synthetic harness. It does not invoke the Ario runtime or external systems.
"""
from __future__ import annotations

import argparse
import json
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
    "counterfactual_a", "counterfactual_b", "counterfactual_c",
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
        pair_group=f"{family}_PAIR_{(index - 1) // 2 + 1:02d}" if index >= 10 else "",
        input=input_data,
        expected=expected,
        rationale=rationale,
    )

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
      ({"sources":["A","B"],"roots":{"A":["R1"],"B":["R1"]},"one_root_hidden":True}, {"root_count":None,"status":"UNKNOWN"}, "Incomplete root disclosure."),
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
      ({"records":[("A","m1"),("B","m2")],"one_record_missing":True}, {"unique_senders":None,"status":"UNKNOWN"}, "Partial record set."),
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
      ({"labels":["SUPPORTS","CONTRADICTS"],"one_source_shared_root":True}, {"status":"CONTESTED"}, "Conflict remains; dependence affects weight, not erasure."),
      ({"labels":["SUPPORTS"],"provenance_missing":True}, {"status":"UNKNOWN"}, "Support without traceable provenance remains unknown."),
    ]
    scope = [
      ({"claim_scope":"S","evidence_scope":"S"}, {"scope":"IN_SCOPE","status":"UNKNOWN"}, "Exact scope match."),
      ({"claim_scope":"S","evidence_scope":"S.sub"}, {"scope":"IN_SCOPE","status":"UNKNOWN"}, "Narrower evidence scope does not justify broader claim."),
      ({"claim_scope":"S.sub","evidence_scope":"S"}, {"scope":"IN_SCOPE","status":"UNKNOWN"}, "Broader evidence may cover narrower claim subject to declared semantics."),
      ({"claim_scope":"S","evidence_scope":"OTHER"}, {"scope":"OUT_OF_SCOPE","status":"REJECTED"}, "Disjoint scope."),
      ({"claim_scope":"S","evidence_scope":None}, {"scope":"UNKNOWN","status":"UNKNOWN"}, "Missing evidence scope."),
      ({"claim_scope":"S","evidence_scope":"S","time_mismatch":True}, {"scope":"OUT_OF_SCOPE","status":"REJECTED"}, "Temporal scope mismatch."),
      ({"claim_scope":"S","evidence_scope":"S","actor_mismatch":True}, {"scope":"OUT_OF_SCOPE","status":"REJECTED"}, "Actor scope mismatch."),
      ({"claim_scope":"S","evidence_scope":"S","jurisdiction_mismatch":True}, {"scope":"OUT_OF_SCOPE","status":"REJECTED"}, "Jurisdiction mismatch."),
      ({"claim_scope":"S","evidence_scope":"S","scope_version_unknown":True}, {"scope":"UNKNOWN","status":"UNKNOWN"}, "Unknown scope semantics."),
      ({"claim_scope":"S.sub","evidence_scope":"S","boundary_ambiguous":True}, {"scope":"UNKNOWN","status":"UNKNOWN"}, "Boundary ambiguity."),
      ({"claim_scope":"S","evidence_scope":"S","excluded_population":True}, {"scope":"OUT_OF_SCOPE","status":"REJECTED"}, "Explicitly excluded population."),
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
      ({"version":"0.9","required_present":True}, {"schema":"REJECT","status":"REJECTED"}, "Legacy unsupported version."),
      ({"version":"1.0","required_present":True,"compatibility_unstated":True}, {"schema":"UNKNOWN","status":"UNKNOWN"}, "Compatibility range not declared."),
      ({"version":"1.1","required_present":True,"critical_semantics_changed":True}, {"schema":"REJECT","status":"REJECTED"}, "Minor version with incompatible critical semantics."),
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
      ({"digest":"valid","auth":"VERIFIED","algorithm_unsupported":True}, {"integrity":"UNKNOWN","auth":"UNVERIFIED","status":"UNKNOWN"}, "Unsupported digest algorithm."),
      ({"digest":"valid","auth":"UNVERIFIED","source_claims_truth":True}, {"integrity":"VALID","auth":"UNVERIFIED","status":"UNKNOWN"}, "Authenticity and truth are distinct."),
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
      ({"event":10,"observed":11,"recorded":12,"availability_time":8}, {"temporal":"ORDERED","status":"UNKNOWN"}, "Availability time distinct from publication."),
      ({"event":10,"observed":11,"recorded":12,"publication_time":2}, {"temporal":"ORDERED","status":"UNKNOWN"}, "Publication time does not replace observation time."),
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
      ({"history":["v1","v2"],"operation":"merge","parents_recorded":False}, {"history":"UNKNOWN","status":"UNKNOWN"}, "Merge parentage incomplete."),
      ({"history":["v1","v2"],"operation":"append","prior_retained":True}, {"history":"PRESERVED","status":"UNKNOWN"}, "Positive append control."),
    ]
    composition = [
      ({"premises":["P1"],"requirements":["P1"]}, {"composition":"VALID","status":"UNKNOWN"}, "All declared requirements met."),
      ({"premises":["P1"],"requirements":["P1","P2"]}, {"composition":"INCOMPLETE","status":"UNKNOWN"}, "One required premise missing."),
      ({"premises":["P1","P2"],"requirements":["P1","P2"],"incompatible":True}, {"composition":"INVALID","status":"REJECTED"}, "Premises conflict despite local validity."),
      ({"premises":["P1","P2"],"requirements":["P1","P2"],"shared_dependency":True}, {"composition":"VALID_WITH_SHARED_DEPENDENCY","status":"UNKNOWN"}, "Shared dependency recorded, not double-counted."),
      ({"premises":["P1"],"requirements":["P1"],"cycle":True}, {"composition":"INVALID","status":"REJECTED"}, "Circular dependency."),
      ({"premises":["P1","P2"],"requirements":["P1","P2"],"time_incompatible":True}, {"composition":"INVALID","status":"REJECTED"}, "Temporal incompatibility."),
      ({"premises":["P1","P2"],"requirements":["P1","P2"],"scope_incompatible":True}, {"composition":"INVALID","status":"REJECTED"}, "Scope incompatibility."),
      ({"premises":["P1","P2"],"requirements":["P1","P2"],"claim_kind_mismatch":True}, {"composition":"INVALID","status":"REJECTED"}, "Claim-kind mismatch."),
      ({"premises":[],"requirements":["P1"]}, {"composition":"INCOMPLETE","status":"UNKNOWN"}, "No premise available."),
      ({"premises":["P1","P2"],"requirements":["P1","P2"],"local_validity_only":True}, {"composition":"UNKNOWN","status":"UNKNOWN"}, "Local validity alone cannot establish global validity."),
      ({"premises":["P1","P2"],"requirements":["P1","P2"],"partial_overlap":True}, {"composition":"INCOMPLETE","status":"UNKNOWN"}, "Partial overlap is insufficient."),
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
      ({"evidence":["E1"],"metadata_complete":True}, {"status":"UNKNOWN"}, "Complete metadata does not prove proposition."),
      ({"evidence":["E1"],"human_review_pending":True}, {"status":"UNKNOWN"}, "Pending human adjudication."),
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
        if d.get("unresolved_parent") or d.get("edge_missing") or d.get("one_root_hidden"):
            return {"root_count": None, "status": "UNKNOWN"}
        roots = {root for values in d["roots"].values() for root in values}
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
        if "SUPPORTS" in labels: return {"status": "SUPPORTED"}
        if {"CONTRADICTS", "REFUTES"} & labels: return {"status": "CONTRADICTED"}
        return {"status": "UNKNOWN"}
    if f.family == "scope":
        if d.get("evidence_scope") is None or d.get("scope_version_unknown") or d.get("boundary_ambiguous"):
            return {"scope": "UNKNOWN", "status": "UNKNOWN"}
        if d["evidence_scope"] == "OTHER" or any(d.get(k) for k in ("time_mismatch","actor_mismatch","jurisdiction_mismatch","excluded_population")):
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
        auth = "FAILED" if d.get("signature_revoked") or d["auth"]=="FAILED" else ("VERIFIED" if d["auth"]=="VERIFIED" else "UNVERIFIED")
        status = "REJECTED" if integrity=="INVALID" or auth=="FAILED" else "UNKNOWN"
        return {"integrity":integrity,"auth":auth,"status":status}
    if f.family == "temporal_provenance":
        if d.get("clock_uncertain") or d.get("timestamp_conflict"): t="UNCERTAIN"
        elif d.get("timezone_missing"): t="UNKNOWN"
        elif d.get("superseded"): t="SUPERSEDED"
        elif d.get("future_skew") or (d["observed"] is not None and d["event"]>d["observed"]) or d["recorded"]<d["observed"]: t="ANOMALY"
        elif d["observed"] is None: t="PARTIAL"
        elif d["recorded"]-d["event"]>50: t="STALE"
        else: t="ORDERED"
        return {"temporal":t,"status":"UNKNOWN"}
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
        if any(d.get(k) for k in ("incompatible","cycle","time_incompatible","scope_incompatible","claim_kind_mismatch","firewall_bypassed")):
            return {"composition":"INVALID","status":"REJECTED"}
        if d.get("local_validity_only"): return {"composition":"UNKNOWN","status":"UNKNOWN"}
        if d.get("shared_dependency"): return {"composition":"VALID_WITH_SHARED_DEPENDENCY","status":"UNKNOWN"}
        if d.get("partial_overlap") or not set(d["requirements"]).issubset(set(d["premises"])):
            return {"composition":"INCOMPLETE","status":"UNKNOWN"}
        return {"composition":"VALID","status":"UNKNOWN"}
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
        by_family[family] = {"cases":len(group),"matches":sum(x["match"] for x in group)}
    return {
        "benchmark": VERSION,
        "corpus_kind": "SYNTHETIC_DETERMINISTIC_PUBLIC_DEVELOPMENT",
        "case_count": len(fixtures),
        "family_count": len(FAMILIES),
        "policy_identity": "AEC_BENCH_FIXTURE_REFERENCE_EVALUATOR_NOT_ARIO_RUNTIME",
        "overall_fixture_matches": sum(x["match"] for x in results),
        "overall_fixture_accuracy": sum(x["match"] for x in results)/len(results),
        "by_family": by_family,
        "cases": results,
        "limitations": [
            "All fixtures and oracle labels are synthetic and author-defined.",
            "The reference evaluator is not an Ario runtime call or external-system adapter.",
            "Fixture-match accuracy measures implementation against this authored fixture contract only.",
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
