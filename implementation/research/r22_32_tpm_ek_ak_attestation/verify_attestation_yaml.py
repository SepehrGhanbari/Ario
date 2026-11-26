#!/usr/bin/env python3
"""Check decoded TPM2_ATTEST fields emitted by tpm2_print.

Signature verification is deliberately performed separately by tpm2_checkquote
or tpm2_verifysignature. This helper checks the challenge and object identity
fields that a successful signature alone does not appraise.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def scalar(document: str, key: str) -> str:
    pattern = re.compile(rf"(?m)^\\s*{re.escape(key)}:\\s*(.*?)\\s*$")
    match = pattern.search(document)
    if not match:
        raise ValueError(f"missing field: {key}")
    return match.group(1).strip().strip('"').strip("'")


def hex_value(value: str) -> str:
    value = value.strip().lower()
    if value.startswith("0x"):
        value = value[2:]
    return "".join(ch for ch in value if ch in "0123456789abcdef")


def file_hex(path: str) -> str:
    return Path(path).read_bytes().hex()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("quote", "certify"), required=True)
    parser.add_argument("--yaml", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--ak-qualified-name", required=True)
    parser.add_argument("--object-name")
    parser.add_argument("--object-qualified-name")
    args = parser.parse_args()

    try:
        document = Path(args.yaml).read_text(encoding="utf-8")
        magic = scalar(document, "magic").lower()
        kind = scalar(document, "type")
        extra = hex_value(scalar(document, "extraData"))
        signer = hex_value(scalar(document, "qualifiedSigner"))
        expected_nonce = args.nonce.lower().removeprefix("0x")
        expected_signer = file_hex(args.ak_qualified_name)

        if "tpm_generated_value" not in magic and hex_value(magic) != "ff544347":
            raise ValueError(f"not TPM-generated attestation: {magic}")
        expected_type = "TPM_ST_ATTEST_QUOTE" if args.mode == "quote" else "TPM_ST_ATTEST_CERTIFY"
        numeric_type = "8018" if args.mode == "quote" else "8017"
        if expected_type not in kind and hex_value(kind) != numeric_type:
            raise ValueError(f"wrong attestation type: {kind}")
        if extra != expected_nonce:
            raise ValueError("qualifyingData does not match the fresh challenge")
        if signer != expected_signer:
            raise ValueError("qualifiedSigner does not match the enrolled AK")

        if args.mode == "certify":
            if not args.object_name or not args.object_qualified_name:
                raise ValueError("certify mode requires object Name and Qualified Name")
            actual_name = hex_value(scalar(document, "name"))
            actual_qname = hex_value(scalar(document, "qualifiedName"))
            if actual_name != file_hex(args.object_name):
                raise ValueError("certified object Name mismatch")
            if actual_qname != file_hex(args.object_qualified_name):
                raise ValueError("certified object Qualified Name mismatch")

        print(f"PASS decoded {args.mode} attestation fields, challenge and signer binding")
        return 0
    except (OSError, ValueError) as exc:
        print(f"REJECT {exc}")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
