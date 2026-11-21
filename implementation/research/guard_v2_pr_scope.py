"""GUARD V2 sandbox: PR-scoped reviewability, never authorization to merge.

This pure verifier accepts *supplied* GitHub metadata: it does not fetch live data,
execute PR code, publish a Check Run, hold credentials, or merge anything.
Even a structurally coherent positive returns REVIEWABLE_ONLY, with all authority
bits false. Native commit-SHA status checks are NOT PR-specific authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "ARIO-GUARD-V2-PR-SCOPE-LAB-0.1"
CHECK_NAME = "ario-r1d-lab-app-gate"
APP_ID = 5747504  # historical disposable GitHub App, NEVER a production credential
SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
LAB_EXTERNAL_ID = re.compile(r"R1I-LAB-ONLY:PR([1-9][0-9]*):([0-9a-f]{40}):RUN([1-9][0-9]*)\Z")
MAX_BYTES = 1_048_576


class EvidenceError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise EvidenceError(code)


def positive(value: Any) -> bool:
    return type(value) is int and value > 0


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          allow_nan=False, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, OverflowError, RecursionError) as exc:
        raise EvidenceError("INVALID_CANONICAL_DATA") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def strict_json(raw: bytes) -> Any:
    require(isinstance(raw, bytes) and len(raw) <= MAX_BYTES, "INVALID_INPUT_SIZE")

    def unique(pairs):
        obj = {}
        for k, v in pairs:
            require(k not in obj, "DUPLICATE_JSON_MEMBER")
            obj[k] = v
        return obj

    def bad_constant(_):
        raise EvidenceError("NONSTANDARD_JSON_CONSTANT")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=bad_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, EvidenceError):
            raise
        raise EvidenceError("MALFORMED_JSON") from exc


def _collection(evidence: dict, name: str) -> list:
    page = evidence.get(name)
    require(isinstance(page, dict) and not page.get("errors"), "FAILED_OR_MISSING_" + name.upper())
    nodes = page.get("nodes")
    total = page.get("totalCount")
    require(type(total) is int and 0 <= total <= 100
            and isinstance(nodes, list) and len(nodes) == total
            and page.get("hasNextPage") is False,
            "INCOMPLETE_" + name.upper())
    ids = []
    for item in nodes:
        require(isinstance(item, dict), "INVALID_" + name.upper() + "_ITEM")
        item_id = item.get("id")
        require((isinstance(item_id, str) and bool(item_id)) if name == "threads"
                else positive(item_id), "INVALID_" + name.upper() + "_ID")
        ids.append(item_id)
        if name == "threads":
            require(type(item.get("isResolved")) is bool and item["isResolved"],
                    "UNRESOLVED_THREAD")
    require(len(set(ids)) == len(ids), "DUPLICATE_" + name.upper() + "_ID")
    return nodes


def _validate_pin(pin: dict) -> None:
    require(isinstance(pin, dict), "INVALID_PIN")
    for key in ("repository_id", "pr_id", "pr_number"):
        require(positive(pin.get(key)), "INVALID_PIN_" + key.upper())
    for key in ("head_sha", "base_sha"):
        require(isinstance(pin.get(key), str) and SHA_PATTERN.fullmatch(pin[key]),
                "INVALID_PIN_" + key.upper())
    require(isinstance(pin.get("review_digest"), str)
            and DIGEST_PATTERN.fullmatch(pin["review_digest"]), "INVALID_REVIEW_DIGEST")


def _validate_snapshot(pin: dict, snapshot: dict) -> str:
    require(isinstance(snapshot, dict), "INVALID_SNAPSHOT")
    pr = snapshot.get("pr")
    require(isinstance(pr, dict), "MISSING_PR")
    for key, src in (("repository_id", "repository_id"), ("id", "pr_id"),
                     ("number", "pr_number")):
        require(positive(pr.get(key)) and pr[key] == pin[src], "PR_IDENTITY_MISMATCH")
    require(pr.get("head_sha") == pin["head_sha"]
            and pr.get("base_sha") == pin["base_sha"], "STALE_PR_REVISION")
    require(pr.get("state") == "open" and pr.get("draft") is False,
            "PR_NOT_READY")
    evidence = snapshot.get("evidence")
    require(isinstance(evidence, dict), "MISSING_REVIEW_EVIDENCE")
    for name in ("reviews", "comments", "threads"):
        _collection(evidence, name)
    return digest(evidence)


def assess(pin: dict, first: dict, last: dict, check_capture: dict,
           self_audit: dict | None = None) -> dict:
    """Return REVIEWABLE_ONLY for coherent supplied evidence, otherwise HOLD.

    A positive diagnostic can *never* authorize merge, Check publication, runtime
    trust, or independence. A real enforcement broker must verify evidence under
    separate execution and reread the exact PR immediately before action.
    """
    result = {
        "schema": SCHEMA, "disposition": "HOLD", "reason": "UNASSESSED",
        "merge_authorized": False, "check_publish_authorized": False,
        "trust_activated": False, "independent_attestation": "NOT_ESTABLISHED",
        "source": "CALLER_SUPPLIED_RESEARCH_FIXTURE",
        "native_status_not_sufficient": True,
    }
    try:
        _validate_pin(pin)
        first_digest = _validate_snapshot(pin, first)
        second_digest = _validate_snapshot(pin, last)
        require(canonical(first) == canonical(last), "SNAPSHOT_CHANGED_BETWEEN_READS")
        require(first_digest == second_digest == pin["review_digest"],
                "STALE_OR_CHANGED_REVIEW_EVIDENCE")
        require(isinstance(check_capture, dict) and check_capture.get("errors") in (None, []),
                "FAILED_CHECK_CAPTURE")
        checks = check_capture.get("check_runs")
        count = check_capture.get("total_count")
        require(isinstance(checks, list) and type(count) is int and count == len(checks)
                and 0 <= count <= 100 and check_capture.get("hasNextPage") is False,
                "INCOMPLETE_CHECK_CAPTURE")
        ids = [entry.get("id") for entry in checks if isinstance(entry, dict)]
        require(len(ids) == len(checks) and all(positive(i) for i in ids)
                and len(set(ids)) == len(ids), "INVALID_CHECK_IDS")
        matching = [c for c in checks if c.get("name") == CHECK_NAME
                    and isinstance(c.get("app"), dict)
                    and positive(c["app"].get("id")) and c["app"]["id"] == APP_ID]
        require(len(matching) == 1, "MISSING_OR_AMBIGUOUS_APP_CHECK")
        check = matching[0]
        require(check.get("head_sha") == pin["head_sha"]
                and check.get("status") == "completed"
                and check.get("conclusion") == "success", "APP_CHECK_NOT_SUCCESS")
        external = check.get("external_id")
        match = LAB_EXTERNAL_ID.fullmatch(external) if isinstance(external, str) else None
        require(match is not None and int(match[1]) == pin["pr_number"]
                and match[2] == pin["head_sha"], "CHECK_PR_ID_MISMATCH")
        links = check.get("pull_requests")
        require(isinstance(links, list) and len(links) == 1
                and isinstance(links[0], dict)
                and positive(links[0].get("id"))
                and positive(links[0].get("number"))
                and links[0]["id"] == pin["pr_id"]
                and links[0]["number"] == pin["pr_number"],
                "CHECK_PR_ASSOCIATION_MISMATCH")
        if self_audit is not None:
            require(isinstance(self_audit, dict)
                    and self_audit.get("status") == "UNKNOWN"
                    and self_audit.get("merge_authorized") is False,
                    "SELF_AUDIT_NOT_NONAUTHORITATIVE")
        result.update(disposition="REVIEWABLE_ONLY", reason="SUPPLIED_METADATA_CONSISTENT")
    except (EvidenceError, KeyError, TypeError, ValueError, IndexError,
            RecursionError, OverflowError) as exc:
        result["reason"] = str(exc) if isinstance(exc, EvidenceError) else "MALFORMED_EVIDENCE"
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pin", type=Path)
    p.add_argument("first", type=Path)
    p.add_argument("last", type=Path)
    p.add_argument("checks", type=Path)
    args = p.parse_args(argv)
    try:
        objects = [strict_json(path.read_bytes()) for path in
                   (args.pin, args.first, args.last, args.checks)]
        result = assess(*objects)
    except (EvidenceError, OSError, ValueError, TypeError, OverflowError):
        result = assess({}, {}, {}, {})
        result["reason"] = "UNREADABLE_OR_INVALID_INPUT"
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 1  # Nonzero even for REVIEWABLE_ONLY: cannot be a required GREEN gate.


if __name__ == "__main__":
    raise SystemExit(main())
