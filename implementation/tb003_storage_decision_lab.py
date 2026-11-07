"""TB-003 read-only diagnostic overlay; original evaluator is unchanged.

Encryption alone does NOT prove separate physical storage, administration or
source authenticity. Storage and administrative findings remain separate axes.
This function must never grant trust, production status or M0 admission.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ReadOnlyDecision:
    administrative_status: str
    storage_status: str
    proposed_inference: str
    scope: str = "SYNTHETIC_RESEARCH_ONLY"
    m0_admission: str = "NOT_EVALUATED"
    production_authentication: str = "NOT_ESTABLISHED"


def inspect_separation(*, administrative_status: str,
                       storage_status: str) -> ReadOnlyDecision:
    if storage_status == "SAME_STORAGE_OBJECT":
        inference = "BLOCK_SEPARATION_KNOWN_SHARED_STORAGE"
    elif administrative_status in ("COMMON_CONTROL_DETECTED", "COMPROMISED_BY_SCENARIO"):
        inference = "BLOCK_SEPARATION_KNOWN_CONTROL_OR_COMPROMISE"
    elif (administrative_status == "LAB_CONDITIONALLY_SEPARATE"
          and storage_status == "LAB_DISTINCT_OBJECTS"):
        inference = "LAB_CONDITIONAL_ONLY_NEVER_PRODUCTION_AUTHORITY"
    else:
        inference = "BLOCK_SEPARATION_UNKNOWN"
    return ReadOnlyDecision(administrative_status, storage_status, inference)
