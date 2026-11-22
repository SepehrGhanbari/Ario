"""R63 G7: bind a disposable Windows CNG signature to the exact G6 seq4 *candidate*.
Research-only, never an Ario approval, signer, custody or latest-state activation.
No keys are generated here; CI calls existing disposable NCryptSignHash pilot only
after this preflight. Verification must separately verify ECDSA signature bytes.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

G7 = Path(__file__).resolve().parent
G6 = G7.parent / "offline_minimum_extension"
sys.path.insert(0, str(G6))
import g6_extension_gate as g6

DOMAIN = b"ARIO-R63/G7/DISPOSABLE-SYNTHETIC-CNG-CANDIDATE/1\0"
SEQ4_HEAD = "52e1f33cf8bcf325a2cb817abe16473aa2e6a799fc76406b8cf831b912fd6d8c"
NO_AUTHORITY = "SYNTHETIC_SIGNATURE_NOT_SIGNER_APPROVAL"
EXPECTED_PIN = {"epoch": g6.PINNED_EPOCH, "seq": 3, "head": g6.PINNED_HEAD}

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")

class Hold(ValueError):
    pass

def build(base_v1: bytes, base_v2: bytes, candidate_v1: bytes,
          candidate_v2: bytes, pin: dict, source: Path) -> tuple[bytes, dict]:
    """No self-reported phone attestation: compare exact old raw bytes and extension."""
    if g6.pin_check(pin) != "PIN_FIELDS_MATCH_STATIC_RESEARCH_BASELINE":
        raise Hold("HOLD_PIN_REBOUND")
    if sha(source.read_bytes()) != g6.FROZEN_V9_SHA:
        raise Hold("HOLD_FROZEN_SOURCE_CHANGED")
    if sha(base_v1) != g6.G4_RAW_V1_SHA or sha(base_v2) != g6.G4_RAW_V2_SHA:
        raise Hold("HOLD_G4_PREFIX_CHANGED")
    try:
        expected_v1, expected_v2 = g6.build_candidate(base_v1, base_v2, source)
        old = g6.audited_journals(base_v1, base_v2)
        state = g6.audited_journals(candidate_v1, candidate_v2)
    except (ValueError, RuntimeError, TypeError, UnicodeError) as e:
        raise Hold("HOLD_CHAIN_INVALID") from e
    if (old["seq"], old["head"]) != (3, g6.PINNED_HEAD):
        raise Hold("HOLD_OLD_HEAD_NOT_PINNED")
    if state["seq"] != 4 or state["prefix_head"] != g6.PINNED_HEAD:
        raise Hold("HOLD_ROLLBACK_OR_FORK")
    if candidate_v1 != expected_v1 or candidate_v2 != expected_v2:
        raise Hold("HOLD_NOT_EXACT_REVIEWED_EXTENSION")
    if state["head"] != SEQ4_HEAD:
        raise Hold("HOLD_UNEXPECTED_SEQ4_HEAD")
    body = {
        "domain": "ARIO_R63_G7_DISPOSABLE_CNG_CANDIDATE_V1",
        "epoch": g6.PINNED_EPOCH,
        "previous": {"seq": 3, "head": g6.PINNED_HEAD},
        "candidate": {"seq": 4, "head": SEQ4_HEAD,
                      "v1_sha256": state["v1_sha256"],
                      "v2_sha256": state["v2_sha256"]},
        "frozen_v9_v2_sha256": g6.FROZEN_V9_SHA,
        "signing_purpose": NO_AUTHORITY,
        "phone_floor_advanced": False,
        "external_latest": "NOT_ESTABLISHED",
        "native_v9_signer": "NOT_EXECUTED",
        "production": "NO_GO",
    }
    payload = DOMAIN + canonical(body)
    return payload, body

def paths(g6_dir: Path) -> tuple[Path, Path, Path, Path, Path, Path]:
    return (g6_dir / "g4_source_v1.jsonl",
            g6_dir / "g4_source_v2.jsonl",
            g6_dir / "candidate_seq4_v1.jsonl",
            g6_dir / "candidate_seq4_v2.jsonl",
            g6_dir / "G6_PHONE_NOTE_UNCHANGED_SEQ3_RESEARCH_INPUT.json",
            g6_dir.parent / "spend_chain_v2.py")

def run(mode: str, g6_dir: Path, root: Path, candidate_v2_override: Path | None = None) -> str:
    orig1, orig2, next1, next2, phone_pin, src = paths(g6_dir)
    try:
        pin = json.loads(phone_pin.read_text("utf-8"))
        payload, body = build(orig1.read_bytes(), orig2.read_bytes(),
                             next1.read_bytes(),
                             (candidate_v2_override or next2).read_bytes(), pin, src)
    except (OSError, json.JSONDecodeError, UnicodeError) as e:
        raise Hold("HOLD_INPUT_UNAVAILABLE") from e
    if mode == "prepare":
        if root.exists():
            raise Hold("HOLD_REFUSE_EXISTING_OUTPUT")
        root.mkdir(parents=False)
        (root / "payload.bin").write_bytes(payload)
        (root / "candidate-metadata.json").write_bytes(canonical(body) + b"\n")
        return "G7_BOUND_SYNTHETIC_CANDIDATE_NO_AUTHORITY"
    if mode == "verify":
        try:
            saved_payload = (root / "payload.bin").read_bytes()
            saved_metadata = (root / "candidate-metadata.json").read_bytes()
        except OSError as e:
            raise Hold("HOLD_SIGNED_PAYLOAD_UNAVAILABLE") from e
        if saved_payload != payload or saved_metadata != canonical(body) + b"\n":
            raise Hold("HOLD_CHANGED_JOURNAL_AFTER_SIGN")
        # Signature itself MUST be verified by the existing native public verifier.
        return "G7_BYTES_BOUND_PUBLIC_SIGNATURE_STILL_SEPARATE"
    raise Hold("HOLD_INVALID_MODE")

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=["prepare", "verify"], required=True)
    p.add_argument("--g6-dir", type=Path, default=G6)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--candidate-v2-override", type=Path)
    a = p.parse_args()
    try:
        print(run(a.mode, a.g6_dir, a.out, a.candidate_v2_override))
        return 0
    except Hold as e:
        print(str(e))
        return 2

if __name__ == "__main__":
    sys.exit(main())
