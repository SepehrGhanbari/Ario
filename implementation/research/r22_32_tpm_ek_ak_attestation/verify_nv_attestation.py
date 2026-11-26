#!/usr/bin/env python3
"""Verify TPM2_NV_Certify attestation fields and the NV index Name.

The signature itself must be verified separately with tpm2_verifysignature.
This verifier checks that the signed TPMS_ATTEST binds the expected AK,
fresh challenge, NV index identity, offset, and exact 32-byte contents.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import struct
from pathlib import Path

TPM_GENERATED = 0xFF544347
TPM_ST_ATTEST_NV = 0x8014
TPM_ALG_SHA256 = 0x000B
TPMA_NV_OWNERWRITE = 1 << 1
TPMA_NV_AUTHWRITE = 1 << 2
TPMA_NV_OWNERREAD = 1 << 17
TPMA_NV_AUTHREAD = 1 << 18
TPMA_NV_WRITTEN = 1 << 29
REQUIRED_NV_ATTRIBUTES = (
    TPMA_NV_OWNERWRITE | TPMA_NV_AUTHWRITE |
    TPMA_NV_OWNERREAD | TPMA_NV_AUTHREAD | TPMA_NV_WRITTEN
)


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def take(self, count: int) -> bytes:
        if count < 0 or self.offset + count > len(self.data):
            raise ValueError("truncated TPMS_ATTEST structure")
        value = self.data[self.offset:self.offset + count]
        self.offset += count
        return value

    def u16(self) -> int:
        return int.from_bytes(self.take(2), "big")

    def u32(self) -> int:
        return int.from_bytes(self.take(4), "big")

    def u64(self) -> int:
        return int.from_bytes(self.take(8), "big")

    def tpm2b(self) -> bytes:
        return self.take(self.u16())


def tpm2b_contents(path: str) -> bytes:
    data = Path(path).read_bytes()
    if len(data) >= 2 and int.from_bytes(data[:2], "big") == len(data) - 2:
        return data[2:]
    return data


def parse_nv_public(yaml_path: str, handle_text: str) -> tuple[bytes, int, int]:
    try:
        handle = int(handle_text, 0)
    except ValueError as exc:
        raise ValueError("NV handle must be an integer or 0x-prefixed handle") from exc
    if not 0x01000000 <= handle <= 0x01FFFFFF:
        raise ValueError("NV handle is outside TPM2_HR_NV_INDEX range")

    lines = Path(yaml_path).read_text(encoding="utf-8").splitlines()
    start = None
    for i, line in enumerate(lines):
        match = re.fullmatch(r"\s*(0x[0-9a-fA-F]+):\s*", line)
        if match and int(match.group(1), 16) == handle:
            start = i
            break
    if start is None:
        raise ValueError("requested NV index is absent from TPM2_NV_ReadPublic output")

    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.fullmatch(r"(0x[0-9a-fA-F]+):\s*", lines[i]):
            end = i
            break
    block = lines[start + 1:end]

    def nested_value(section: str) -> int:
        marker = next((i for i, line in enumerate(block)
                       if line.strip() == section + ":"), None)
        if marker is None:
            raise ValueError(f"NV public output lacks {section}")
        for line in block[marker + 1:]:
            if line and not line[0].isspace():
                break
            match = re.search(r"\bvalue:\s*(0x[0-9a-fA-F]+)\s*$", line.strip())
            if match:
                return int(match.group(1), 16)
        raise ValueError(f"NV public output lacks {section} numeric value")

    name_alg = nested_value("hash algorithm")
    attributes = nested_value("attributes")
    size_line = next((line for line in block if re.fullmatch(r"\s*size:\s*\d+\s*", line)), None)
    if size_line is None:
        raise ValueError("NV public output lacks data size")
    size = int(re.search(r"\d+", size_line).group(0))

    # tpm2-tools 5.6 omits an empty authorization-policy field entirely.
    # If a version prints it, accept only explicit empty/zero-length forms.
    policy_line = next((line for line in block if line.strip().startswith("authorization policy:")), None)
    if policy_line is not None:
        policy_inline = policy_line.split(":", 1)[1].strip().lower()
        if policy_inline not in ("", "0x", "0x0", "0", "none", "null"):
            raise ValueError("this bounded verifier requires an empty NV authorization policy")
        policy_idx = block.index(policy_line)
        policy_tail = [line.strip().lower() for line in block[policy_idx + 1:] if line.strip()]
        if policy_tail:
            empty_policy_forms = (
                ["friendly: none", "value: 0x0"],
                ["friendly: none", "value: 0"],
                ["friendly: sha256", "value: 0x"],
                ["friendly: sha256", "value: 0x0"],
                ["friendly: (null)", "value: 0x0"],
            )
            if policy_tail not in empty_policy_forms:
                raise ValueError("unexpected non-empty NV authorization policy output")

    if name_alg != TPM_ALG_SHA256:
        raise ValueError(f"unsupported NV nameAlg 0x{name_alg:04x}")
    if size != 32:
        raise ValueError(f"expected a 32-byte NV index, found {size}")
    if attributes & REQUIRED_NV_ATTRIBUTES != REQUIRED_NV_ATTRIBUTES:
        raise ValueError(f"NV index lacks required read/write/written attributes: 0x{attributes:08x}")

    # TPMS_NV_PUBLIC wire encoding: nvIndex, nameAlg, attributes,
    # TPM2B_DIGEST authPolicy (zero length), dataSize.
    public_area = (
        struct.pack(">IHI", handle, name_alg, attributes)
        + b"\x00\x00"
        + struct.pack(">H", size)
    )
    name = struct.pack(">H", name_alg) + hashlib.sha256(public_area).digest()
    reported_line = next((line for line in block if line.strip().startswith("name:")), None)
    if reported_line is None:
        raise ValueError("TPM2_NV_ReadPublic output lacks the TPM-reported NV Name")
    try:
        reported_name = bytes.fromhex(reported_line.split(":", 1)[1].strip())
    except ValueError as exc:
        raise ValueError("TPM2_NV_ReadPublic returned a malformed NV Name") from exc
    if reported_name != name:
        raise ValueError("TPM-reported NV Name does not match the independently recomputed public Name")
    return name, attributes, size


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attest", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--ak-qualified-name", required=True)
    parser.add_argument("--nv-public-yaml", required=True)
    parser.add_argument("--nv-index", required=True)
    parser.add_argument("--expected-contents", required=True)
    args = parser.parse_args()

    try:
        nonce = bytes.fromhex(args.nonce)
        if len(nonce) != 32:
            raise ValueError("nonce must be exactly 32 bytes")
        ak_name = tpm2b_contents(args.ak_qualified_name)
        expected_contents = Path(args.expected_contents).read_bytes()
        if len(expected_contents) != 32:
            raise ValueError("expected NV contents must be exactly 32 bytes")

        expected_nv_name, attributes, size = parse_nv_public(args.nv_public_yaml, args.nv_index)

        raw = Path(args.attest).read_bytes()
        if len(raw) >= 2 and int.from_bytes(raw[:2], "big") == len(raw) - 2:
            raw = raw[2:]

        reader = Reader(raw)
        magic = reader.u32()
        attest_type = reader.u16()
        qualified_signer = reader.tpm2b()
        extra_data = reader.tpm2b()
        reader.take(17)  # TPMS_CLOCK_INFO
        reader.u64()     # firmwareVersion
        index_name = reader.tpm2b()
        offset = reader.u16()
        nv_contents = reader.tpm2b()

        if magic != TPM_GENERATED:
            raise ValueError(f"bad TPM_GENERATED magic: 0x{magic:08x}")
        if attest_type != TPM_ST_ATTEST_NV:
            raise ValueError(f"wrong attestation type: 0x{attest_type:04x}")
        if extra_data != nonce:
            raise ValueError("qualifyingData does not match the fresh challenge")
        if qualified_signer != ak_name:
            raise ValueError("qualifiedSigner does not match the enrolled AK")
        if index_name != expected_nv_name:
            raise ValueError("attested NV index Name does not match the independently recomputed public Name")
        if offset != 0:
            raise ValueError(f"unexpected NV certification offset {offset}; expected 0")
        if len(nv_contents) != size:
            raise ValueError(f"attested NV contents length {len(nv_contents)} does not match index size {size}")
        if nv_contents != expected_contents:
            raise ValueError("attested NV contents do not match the expected storage-root commitment")
        if reader.offset != len(reader.data):
            raise ValueError("unexpected trailing data in NV attestation")

        print(
            "PASS TPM2_NV_Certify fields: "
            f"handle={args.nv_index} nameAlg=SHA256 attributes=0x{attributes:08x} "
            "fresh challenge/AK/index Name/offset/exact contents"
        )
        print("NOTE signature must be separately verified with tpm2_verifysignature")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"REJECT {exc}")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
