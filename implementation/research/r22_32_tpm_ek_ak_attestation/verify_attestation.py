#!/usr/bin/env python3
"""Parse TPM2B_ATTEST/TPMS_ATTEST and verify challenge and identity fields."""
from __future__ import annotations

import argparse
from pathlib import Path


TPM_GENERATED = 0xFF544347
TPM_ST_ATTEST_QUOTE = 0x8018
TPM_ST_ATTEST_CREATION = 0x801A
TPM_ALG_SHA256 = 0x000B


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

    def u8(self) -> int:
        return int.from_bytes(self.take(1), "big")

    def u16(self) -> int:
        return int.from_bytes(self.take(2), "big")

    def u32(self) -> int:
        return int.from_bytes(self.take(4), "big")

    def u64(self) -> int:
        return int.from_bytes(self.take(8), "big")

    def tpm2b(self) -> bytes:
        size = self.u16()
        return self.take(size)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("quote", "creation"), required=True)
    parser.add_argument("--attest", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--ak-qualified-name", required=True)
    parser.add_argument("--object-name")
    parser.add_argument("--creation-hash")
    args = parser.parse_args()

    try:
        raw = Path(args.attest).read_bytes()
        # Some tools serialize TPM2B_ATTEST (2-byte size prefix), others write
        # the contained TPMS_ATTEST directly. Accept both encodings.
        if len(raw) >= 2 and int.from_bytes(raw[:2], "big") == len(raw) - 2:
            raw = raw[2:]

        reader = Reader(raw)
        magic = reader.u32()
        attest_type = reader.u16()
        qualified_signer = reader.tpm2b()
        extra_data = reader.tpm2b()
        reader.take(17)  # TPMS_CLOCK_INFO
        reader.u64()     # firmwareVersion

        if magic != TPM_GENERATED:
            raise ValueError(f"bad TPM_GENERATED magic: 0x{magic:08x}")
        expected_type = TPM_ST_ATTEST_QUOTE if args.mode == "quote" else TPM_ST_ATTEST_CREATION
        if attest_type != expected_type:
            raise ValueError(f"wrong attestation type: 0x{attest_type:04x}")
        if extra_data != bytes.fromhex(args.nonce):
            raise ValueError("qualifyingData does not match the fresh challenge")
        if qualified_signer != Path(args.ak_qualified_name).read_bytes():
            raise ValueError("qualifiedSigner does not match the enrolled AK")

        if args.mode == "creation":
            if not args.object_name or not args.creation_hash:
                raise ValueError("creation mode requires object Name and creation hash")
            object_name = reader.tpm2b()
            creation_hash = reader.tpm2b()
            if object_name != Path(args.object_name).read_bytes():
                raise ValueError("attested object Name mismatch")
            if creation_hash != Path(args.creation_hash).read_bytes():
                raise ValueError("attested creation hash mismatch")
            if reader.offset != len(reader.data):
                raise ValueError("unexpected trailing data in creation attestation")
        else:
            count = reader.u32()
            selections = []
            for _ in range(count):
                hash_alg = reader.u16()
                select_size = reader.u8()
                selections.append((hash_alg, reader.take(select_size)))
            pcr_digest = reader.tpm2b()
            expected_selection = [(TPM_ALG_SHA256, bytes((0x00, 0x00, 0x80)))]
            if selections != expected_selection:
                raise ValueError(f"unexpected PCR selection: {selections!r}")
            if len(pcr_digest) != 32:
                raise ValueError("quote PCR digest is not SHA-256 sized")
            if reader.offset != len(reader.data):
                raise ValueError("unexpected trailing data in quote attestation")

        print(f"PASS binary {args.mode} attestation: magic/type/challenge/signer/object binding")
        return 0
    except (OSError, ValueError) as exc:
        print(f"REJECT {exc}")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
