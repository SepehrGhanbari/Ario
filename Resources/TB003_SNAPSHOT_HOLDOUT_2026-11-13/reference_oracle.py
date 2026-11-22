#!/usr/bin/env python3
"""Proposed snapshot-final custody semantics; NOT existing TB-003 contract.
Pure bounded synthetic reference, not a source of real-world authority.
"""
from __future__ import annotations
from typing import Any

def adjudicate(item: dict[str, Any]) -> dict[str, Any]:
    """Exclusive-token custody: each LAB event moves the one synthetic token."""
    snapshot = item["snapshot_sequence"]
    capture = item["capture"]
    declared = item["declared_holder"]
    report = {"case_id": item["case_id"], "final_holder": None,
              "holder_status": "UNKNOWN", "chain_independence": "UNKNOWN",
              "source_independence": "UNKNOWN", "reason": []}
    if item.get("other_witness_custodians") != ["P2"]:
        raise ValueError("UNSUPPORTED_WITNESS_B_CONFIGURATION")
    # Independent raw declarations: never hide these behind an invalid holder
    # or incomplete transfer sequence. They are NOT authenticated real custody.
    compromised = set(item.get("compromised_custodians", []))
    witness_b = set(item["other_witness_custodians"])
    declared_facts = []
    if item["common_control"]:
        declared_facts.append("DECLARED_COMMON_ADMIN_CONTROL")
    if item["shared_storage"]:
        declared_facts.append("DECLARED_SHARED_STORAGE")
    if item["common_source"]:
        declared_facts.append("DECLARED_COMMON_SOURCE")
    if compromised & witness_b:
        declared_facts.append("DECLARED_COMPROMISED_WITNESS_B")
    if item["declared_holder"] in compromised:
        declared_facts.append("DECLARED_COMPROMISED_NOMINATED_HOLDER")
    transfer_actors = {v for move in item["transfers"]
                       for v in (move["from"], move["to"])}
    if compromised & transfer_actors:
        declared_facts.append("DECLARED_COMPROMISED_TRANSFER_ACTOR")
    report["declared_negative_facts"] = sorted(set(declared_facts))
    report["transfer_surface_authentication"] = "NOT_ESTABLISHED"
    report["independence_authority"] = "LAB_DECLARED_ONLY"
    # Source provenance is an orthogonal axis, not conditional on custody validity.
    if item["common_source"]:
        report["source_independence"] = "COMMON_SOURCE_DETECTED"
    elif item["complete_source_surface"]:
        report["source_independence"] = "LAB_CONDITIONALLY_DISTINCT"
    if not item["complete_transfer_surface"]:
        report["reason"].append("INCOMPLETE_TRANSFER_SURFACE")
        return report
    if capture["sequence"] > snapshot:
        report["reason"].append("CAPTURE_AFTER_SNAPSHOT")
        return report
    in_scope = [e for e in item["transfers"] if e["sequence"] <= snapshot]
    seqs = [e["sequence"] for e in in_scope]
    if len(set(seqs)) != len(seqs):
        report["reason"].append("AMBIGUOUS_SAME_SEQUENCE")
        return report
    cursor = capture["custodian"]
    path = [cursor]
    before = capture["sequence"]
    for event in sorted(in_scope, key=lambda x: x["sequence"]):
        if (event["sequence"] <= before or event["origin"] != "LAB"
                or event["from"] != cursor or event["to"] in path):
            report["reason"].append("UNSUPPORTED_OR_DISCONNECTED_TRANSFER")
            return report
        cursor = event["to"]
        path.append(cursor)
        before = event["sequence"]
    report["final_holder"] = cursor
    if declared != cursor:
        report["holder_status"] = "MISMATCH"
        report["reason"].append("DECLARED_HOLDER_NOT_SNAPSHOT_ENDPOINT")
        return report
    report["holder_status"] = "MATCH"
    compromised = set(item.get("compromised_custodians", []))
    other_witness = set(item.get("other_witness_custodians", ["P2"]))
    if compromised.intersection(set(path) | other_witness):
        report["chain_independence"] = "COMPROMISED_BY_SCENARIO"
        report["reason"].append("COMPROMISED_IN_SCOPE_CUSTODY_ACTOR")
    elif (item["common_control"] or item["shared_storage"]
          or other_witness.intersection(path)):
        report["chain_independence"] = "COMMON_CONTROL_DETECTED"
        report["reason"].append("COMMON_CONTROL_STORAGE_OR_CUSTODIAN")
    elif not item["complete_control_surface"]:
        report["reason"].append("INCOMPLETE_CONTROL_SURFACE")
    else:
        report["chain_independence"] = "LAB_CONDITIONALLY_SEPARATE"
        report["reason"].append("BOUNDED_LAB_CHAIN_SEPARATION")
    return report
