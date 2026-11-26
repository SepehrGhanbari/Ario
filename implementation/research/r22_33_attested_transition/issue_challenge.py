#!/usr/bin/env python3
"""Issue a custodian-signed, short-lived challenge for one recovery transition."""
from __future__ import annotations

import argparse
import fcntl
import secrets
import subprocess
import sys
import time
from pathlib import Path

R31_DIR = Path(__file__).resolve().parents[1] / "r22_31_custodian_monotonic_state"
sys.path.insert(0, str(R31_DIR))
import custodian_state_legacy as legacy  # noqa: E402

POLICY_ID = "R22.32_EK_AK_QUOTE_CERTIFYCREATION_V1"
CHALLENGE_FORMAT = "ARIO-R22.33-ATTESTATION-CHALLENGE-V1"


def reject_aliases(named_paths: list[tuple[str, Path]]) -> None:
    seen: list[tuple[str, Path, Path]] = []
    for name, path in named_paths:
        try:
            resolved = path.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise legacy.GateError("PATH_RESOLUTION_FAILED") from exc
        for prior_name, prior_path, prior_resolved in seen:
            aliases = resolved == prior_resolved
            if not aliases:
                try:
                    aliases = path.exists() and prior_path.exists() and path.samefile(prior_path)
                except OSError:
                    aliases = False
            if aliases:
                raise legacy.GateError(f"PATH_ALIAS:{prior_name}:{name}")
        seen.append((name, path, resolved))


def custodian_keypair_matches(public_key: Path, private_key: Path) -> bool:
    public = subprocess.run(
        ["openssl", "pkey", "-pubin", "-in", str(public_key), "-outform", "DER"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    private = subprocess.run(
        ["openssl", "pkey", "-in", str(private_key), "-pubout", "-outform", "DER"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if public.returncode != 0 or private.returncode != 0:
        raise legacy.GateError("CUSTODIAN_KEY_PARSE_FAILED")
    return bool(public.stdout) and public.stdout == private.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("anchor", "anchor-signature", "public-key", "private-key",
                 "journal", "lock", "output", "signature"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--next-head-sha256", required=True)
    parser.add_argument("--ttl-seconds", type=int, default=120)
    args = parser.parse_args()

    try:
        if not 30 <= args.ttl_seconds <= 300:
            raise legacy.GateError("CHALLENGE_TTL_OUT_OF_RANGE")
        legacy.validate_hash(args.next_head_sha256, "NEXT_HEAD_INVALID")
        if not custodian_keypair_matches(args.public_key, args.private_key):
            raise legacy.GateError("CUSTODIAN_KEYPAIR_MISMATCH")
        reject_aliases([
            ("anchor", args.anchor), ("anchor_signature", args.anchor_signature),
            ("public_key", args.public_key), ("private_key", args.private_key),
            ("journal", args.journal), ("lock", args.lock),
            ("output", args.output), ("signature", args.signature),
        ])
        args.lock.parent.mkdir(parents=True, exist_ok=True)
        with args.lock.open("a+b") as lock_stream:
            fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)
            anchor, anchor_raw = legacy.read_json(args.anchor)
            if anchor_raw != legacy.canonical(anchor):
                raise legacy.GateError("ANCHOR_NOT_CANONICAL")
            if not legacy.openssl_verify(
                args.public_key, anchor_raw, args.anchor_signature.read_bytes()
            ):
                raise legacy.GateError("ANCHOR_SIGNATURE_INVALID")
            anchor = legacy.validate_anchor(anchor)
            state, _records, _tail_hash = legacy.load_journal(
                args.journal, args.public_key, anchor
            )
            issued_at = int(time.time())
            challenge = {
                "format": CHALLENGE_FORMAT,
                "nonce": secrets.token_hex(32),
                "device_ek_sha256": state["device_ek_sha256"],
                "previous_storage_root_sha256": state["storage_root_sha256"],
                "previous_epoch": state["epoch"],
                "next_epoch": state["epoch"] + 1,
                "previous_head_sha256": state["head_sha256"],
                "next_head_sha256": args.next_head_sha256,
                "reason": "TPM_CLEAR_RECOVERY",
                "policy_id": POLICY_ID,
                "issued_at": issued_at,
                "expires_at": issued_at + args.ttl_seconds,
            }
            payload = legacy.canonical(challenge)
            signature = legacy.openssl_sign(args.private_key, payload)
            legacy.atomic_write(args.output, payload)
            legacy.atomic_write(args.signature, signature)
        print(f"CHALLENGE_ISSUED epoch={challenge['next_epoch']} expires_at={challenge['expires_at']}")
        return 0
    except legacy.GateError as exc:
        print("REJECT " + exc.code)
        return 3
    except OSError as exc:
        print("REJECT IO_ERROR:" + type(exc).__name__)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
