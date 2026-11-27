"""UCD reference-conditioned shared discordance: report-only, no status changes.

The reference is supplied, not authenticated truth. Agreement on it is not
a copy signal. Shared departures can have causes other than copying.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from bounded_json import loads_bounded
from research.w38_receipt_fd_guard import read_bounded_regular
from undeclared_copy_dependence_probe import pairwise_agreement

SCHEMA = "ARIO-UCD-REFERENCE-DIAGNOSTIC-0.1"
MAX_BYTES = 2 * 1024 * 1024
MAX_SOURCES = 32
MAX_ITEMS = 2000
MIN_JOINT = 8
MIN_SHARED = 8
MIN_SHARED_FRACTION = 0.5


def _text(x):
    return type(x) is str and 0 < len(x) <= 256 and bool(x.strip())


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON member")
        out[key] = value
    return out


def _constant(_):
    raise ValueError("nonfinite JSON constant")


def _base():
    return {
        "schema": SCHEMA, "status": "UNKNOWN",
        "reference_authentication": "UNKNOWN",
        "independence": "UNKNOWN", "dependence": "UNKNOWN",
        "claim_truth": "UNKNOWN", "automatic_downgrade": False,
        "pair_results": [],
        "parameters": {"min_joint_discordance": MIN_JOINT,
                       "min_shared_discordance": MIN_SHARED,
                       "min_shared_fraction": MIN_SHARED_FRACTION},
        "limitations": [
            "Reference values are caller-supplied declarations, not authenticated truth.",
            "Shared discordance can arise from common causes, biased references, chance or copying.",
            "Insufficient or unflagged pairs do not establish independence.",
            "No calibrated probability, clustering, voting, evidence or automatic status changes.",
        ],
    }


def assess(request):
    report = _base()
    if type(request) is not dict or set(request) != {"item_ids", "reference", "sources"}:
        return {**report, "reason": "INVALID_REQUEST"}
    items, reference, sources = (request[k] for k in ("item_ids", "reference", "sources"))
    if (type(items) is not list or not 1 <= len(items) <= MAX_ITEMS
            or not all(_text(x) for x in items) or len(set(items)) != len(items)
            or type(reference) is not dict or set(reference) != {"source_id", "values"}
            or not _text(reference["source_id"])
            or type(sources) is not dict or not 2 <= len(sources) <= MAX_SOURCES
            or not all(_text(x) for x in sources) or reference["source_id"] in sources):
        return {**report, "reason": "INVALID_ALIGNMENT_OR_SOURCE_IDS"}

    def valid_values(values):
        return (type(values) is list and len(values) == len(items)
                and all(_text(x) for x in values))

    if not valid_values(reference["values"]) or not all(valid_values(x) for x in sources.values()):
        return {**report, "reason": "INVALID_ALIGNED_VALUES"}
    claims = {s: tuple(values) for s, values in sources.items()}
    ref = reference["values"]
    pairs = []
    for (a, b), agreement in pairwise_agreement(claims).items():
        joint = shared = 0
        for x, y, baseline in zip(claims[a], claims[b], ref):
            if x != baseline and y != baseline:
                joint += 1
                shared += x == y
        fraction = shared / joint if joint else None
        if joint < MIN_JOINT:
            signal = "INSUFFICIENT_JOINT_DISCORDANCE"
        elif shared >= MIN_SHARED and fraction >= MIN_SHARED_FRACTION:
            signal = "SHARED_DISCORDANCE_SIGNAL_NOT_EVIDENCE"
        else:
            signal = "NO_SIGNAL_AT_STATED_THRESHOLDS"
        pairs.append({"sources": [a, b], "agreement": agreement,
                      "joint_discordance": joint, "shared_discordance": shared,
                      "shared_fraction": fraction, "signal": signal})
    report.update(status="DIAGNOSTIC", reference_id=reference["source_id"],
                  item_count=len(items), pair_results=pairs)
    return report


def inspect_file(path):
    report = _base()
    try:
        raw = read_bounded_regular(Path(path), MAX_BYTES)
    except (OSError, ValueError):
        return {**report, "reason": "INPUT_UNAVAILABLE"}
    digest = hashlib.sha256(raw).hexdigest()
    try:
        data = loads_bounded(raw.decode("utf-8"), object_pairs_hook=_pairs,
                             parse_constant=_constant)
        report = assess(data)
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        report["reason"] = "INVALID_JSON"
    report["input_sha256"] = digest
    return report
