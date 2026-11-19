"""Research-only, fail-closed archival checks for R04's real *pending* OTS receipt.

No ledger memory, trust promotion, finality, independent custody, or online I/O by
this module. OTS cryptographic verification requires the official external CLI.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
FILE_NAME = "synthetic_checkpoint_r04.json"
RECEIPT_NAME = "synthetic_checkpoint_r04.ots.b64"
FILE_SHA256 = "c37da68d045da9c85a90dc679857c017ed0bbd1454e51d9033ef9a48e799a68a"
RECEIPT_SHA256 = "5b7fc36d470560adbc8fd4620436451ea43ea0578bf50e7ca6104ce0280c3bf6"
LAB_HISTORY_SHA256 = "519b9b0b20b06256ed77b1a24059ea8ec3f244d7fa1ad8f545c08d6d6ab5c780"
SCOPE = "LAB-E101"  # This scope describes the toy history, NOT authenticated origin.
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ArchiveError(ValueError):
    pass


def _pairs_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ArchiveError("duplicate JSON key")
        result[key] = value
    return result


def _read_exact(path: Path, max_bytes: int) -> bytes:
    content = path.read_bytes()
    if not content or len(content) > max_bytes:
        raise ArchiveError("missing or oversized archival input")
    return content


def audit_archive(checkpoint: Path, receipt_b64: Path) -> dict:
    """Check exact archived test bytes; this is NOT a blockchain verification."""
    raw = _read_exact(checkpoint, 16_384)
    enc = _read_exact(receipt_b64, 32_768)
    if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), FILE_SHA256):
        raise ArchiveError("checkpoint checksum mismatch")
    try:
        decoded = base64.b64decode(b"".join(enc.split()), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ArchiveError("invalid receipt encoding") from exc
    if not hmac.compare_digest(hashlib.sha256(decoded).hexdigest(), RECEIPT_SHA256):
        raise ArchiveError("receipt checksum mismatch")
    try:
        manifest = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs_no_duplicates)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise ArchiveError("invalid checkpoint JSON") from exc
    if not isinstance(manifest, dict):
        raise ArchiveError("checkpoint must be an object")
    if (type(manifest.get("historical_record_count")) is not int
            or manifest["historical_record_count"] != 6
            or manifest.get("historical_record_sha256") != LAB_HISTORY_SHA256
            or manifest.get("authority_to_modify_memory") is not False
            or manifest.get("independent_custody") != "NOT_ESTABLISHED"
            or manifest.get("clock_trust") != "NOT_ESTABLISHED"):
        raise ArchiveError("unexpected synthetic scope or authority claim")
    return {
        "status": "EXACT_ARCHIVED_BYTES_MATCHED",
        "receipt_bytes": len(decoded),
        "checkpoint_bytes": len(raw),
        "checkpoint_sha256": FILE_SHA256,
        "receipt_sha256": RECEIPT_SHA256,
        "bitcoin_inclusion": "NOT_DETERMINED_BY_OFFLINE_CHECK",
        "history_completeness": "NOT_ESTABLISHED",
        "independent_custody": "NOT_ESTABLISHED",
        "real_memory_admission": False,
    }


def compare_external_floor(candidate: dict, retained_floor: dict | None) -> str:
    """Pure comparison. Caller must authenticate + retain floor OUTSIDE publisher.

    Equal-sequence matching is not freshness proof. A higher sequence is held
    until a separately validated append-only consistency proof is provided.
    Merely calling a dict 'independent' cannot confer independent custody.
    """
    def valid(x):
        return (type(x) is dict and x.get("scope") == SCOPE
                and type(x.get("last_seq")) is int and 0 <= x["last_seq"] <= 2**63 - 1
                and isinstance(x.get("history_sha256"), str)
                and bool(HEX64.fullmatch(x["history_sha256"])))

    if not valid(candidate):
        return "REJECT_INVALID_CANDIDATE"
    if retained_floor is None:
        return "HOLD_MISSING_EXTERNAL_FLOOR"
    if not valid(retained_floor):
        return "HOLD_INVALID_EXTERNAL_FLOOR"
    if candidate["last_seq"] < retained_floor["last_seq"]:
        return "ROLLBACK_REJECTED_RELATIVE_TO_SUPPLIED_FLOOR"
    if candidate["last_seq"] == retained_floor["last_seq"]:
        return ("SAME_CHECKPOINT_NOT_FRESHNESS_PROOF" if
                hmac.compare_digest(candidate["history_sha256"], retained_floor["history_sha256"])
                else "HOLD_SPLIT_VIEW")
    return "HOLD_UNVERIFIED_EXTENSION"


def official_ots_check(checkpoint: Path, receipt_bytes: bytes, ots_executable: str) -> dict:
    """Optional bounded external CLI check. No upgrades or file modification.

    Exit 0 on this call is attributed to a caller-provided CLI, not a guarantee
    of a trusted Bitcoin node, source completeness, or independent witness.
    """
    import tempfile
    with tempfile.TemporaryDirectory(prefix="ario-r04-ots-") as tmp:
        proof = Path(tmp) / (checkpoint.name + ".ots")
        proof.write_bytes(receipt_bytes)
        try:
            completed = subprocess.run(
                [ots_executable, "verify", "--timeout", "10", "-f", str(checkpoint), str(proof)],
                capture_output=True, text=True, timeout=35, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"status": "HOLD_VERIFIER_UNAVAILABLE", "error": type(exc).__name__}
        detail = (completed.stdout + "\n" + completed.stderr)[-2500:]
        return {
            "status": ("OTS_CLI_REPORTED_SUCCESS_SOURCE_NEEDS_REVIEW" if completed.returncode == 0
                       else "OTS_CLI_DID_NOT_VERIFY"),
            "exit_code": completed.returncode,
            "output_tail": detail,
            "real_memory_admission": False,
        }


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Ario R04 research archive verifier — NO TRUST ACTIVATION")
    parser.add_argument("--checkpoint", type=Path, default=HERE / FILE_NAME)
    parser.add_argument("--receipt-b64", type=Path, default=HERE / RECEIPT_NAME)
    parser.add_argument("--ots", metavar="PATH", help="Optionally run the independently installed official OTS verifier")
    args = parser.parse_args(argv)
    try:
        output = audit_archive(args.checkpoint, args.receipt_b64)
    except (ArchiveError, OSError) as exc:
        print(json.dumps({"status": "REJECT", "reason": str(exc)}, sort_keys=True))
        return 2
    if args.ots:
        proof = base64.b64decode(b"".join(args.receipt_b64.read_bytes().split()), validate=True)
        output["external_check"] = official_ots_check(args.checkpoint, proof, args.ots)
    print(json.dumps(output, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
