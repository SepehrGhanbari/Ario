#!/usr/bin/env python3
"""Recompute a TPM Name from a marshalled TPMT_PUBLIC structure."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-tpmt", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--require-storage-primary", action="store_true")
    parser.add_argument("--require-ak", action="store_true")
    args = parser.parse_args()

    raw = Path(args.public_tpmt).read_bytes()
    actual_name = Path(args.name).read_bytes()
    if len(raw) < 8:
        raise SystemExit("REJECT TPMT_PUBLIC is truncated")

    public_type = int.from_bytes(raw[0:2], "big")
    name_alg = int.from_bytes(raw[2:4], "big")
    attributes = int.from_bytes(raw[4:8], "big")
    if name_alg != 0x000B:
        raise SystemExit(f"REJECT unsupported nameAlg 0x{name_alg:04x}; expected SHA-256")
    if args.require_storage_primary and args.require_ak:
        raise SystemExit("REJECT choose one TPM object profile")
    if args.require_storage_primary:
        if public_type != 0x0023:
            raise SystemExit(f"REJECT public type 0x{public_type:04x}; expected ECC")
        required = (1 << 1) | (1 << 4) | (1 << 5) | (1 << 16) | (1 << 17)
        forbidden = (1 << 18)
        if attributes & required != required:
            raise SystemExit("REJECT storage primary lacks fixedTPM/fixedParent/sensitiveDataOrigin/restricted/decrypt attributes")
        if attributes & forbidden:
            raise SystemExit("REJECT storage primary must not have the sign attribute")
    if args.require_ak:
        if public_type != 0x0001:
            raise SystemExit(f"REJECT public type 0x{public_type:04x}; expected RSA AK")
        required = (1 << 1) | (1 << 4) | (1 << 5) | (1 << 16) | (1 << 18)
        forbidden = (1 << 17)
        if attributes & required != required:
            raise SystemExit("REJECT AK lacks fixedTPM/fixedParent/sensitiveDataOrigin/restricted/sign attributes")
        if attributes & forbidden:
            raise SystemExit("REJECT AK must not have the decrypt attribute")

    expected_name = raw[2:4] + hashlib.sha256(raw).digest()
    if actual_name != expected_name:
        raise SystemExit("REJECT TPM Name does not match the supplied TPMT_PUBLIC bytes")
    print("PASS TPM Name recomputed from TPMT_PUBLIC; required object attributes present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
