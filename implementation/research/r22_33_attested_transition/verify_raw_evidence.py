#!/usr/bin/env python3
"""Verify the raw R22.32 TPM evidence bundle and issue an R22.33 verifier receipt.

This is a research verifier. It checks the complete exported software-TPM
bundle, TPM signatures, Names, challenge-derived nonces, EK lab certificate,
NV contents, CertifyCreation and PCR Quote before signing the receipt.
It does not establish OEM EK trust, physical TPM identity, or independent
custody of the verifier key.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
R31_DIR = HERE.parent / "r22_31_custodian_monotonic_state"
R32_DIR = HERE.parent / "r22_32_tpm_ek_ak_attestation"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(R31_DIR))
sys.path.insert(0, str(R32_DIR))

import attested_custodian as gate  # noqa: E402
import verify_attestation as attest  # noqa: E402
import verify_nv_attestation as nv  # noqa: E402

POLICY_ID = gate.POLICY_ID
MANIFEST_FORMAT = "ARIO-R22.32-SWTPM-EVIDENCE-MANIFEST-V1"
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_RAW_FILES = {
    "ak-name.bin", "ak-public-area.tpmt", "ak-public.pem", "ak-qualified-name.bin",
    "creation-attestation.bin", "creation-attestation.sig", "creation-nonce.txt",
    "custodian-challenge-nonce.txt", "custodian-public.pem", "custodian-anchor.json",
    "custodian-anchor.sig", "custodian-challenge.json", "custodian-challenge.sig",
    "ek-certificate.crt", "ek-lab-root.crt", "ek-public.pem", "ek-spki-sha256.txt",
    "nv-attestation.bin", "nv-attestation.sig", "nv-contents.bin", "nv-index.txt",
    "nv-nonce.txt", "nv-public.yaml", "pcr23-after.bin", "pcr23-before.bin",
    "pcr23-event-digest.txt", "quote-attestation.bin", "quote-attestation.sig",
    "quote-nonce.txt", "storage-creation-data.bin", "storage-creation-hash.bin",
    "storage-name.bin", "storage-public-area.tpmt", "storage-qualified-name.bin",
    "storage-root-commitment.bin", "storage-root-sha256.txt",
}
NV_INDEX_HANDLE = 0x01500020
NV_NAME_ALG = 0x000B
NV_ATTRIBUTES = 0x20060006
NV_DATA_SIZE = 32
TPM_GENERATED = 0xFF544347
TPM_ST_ATTEST_NV = 0x8014
TPM_ST_ATTEST_CREATION = 0x801A
TPM_ST_ATTEST_QUOTE = 0x8018
TPM_ALG_SHA256 = 0x000B
TPM_ALG_RSASSA = 0x0014


def reject(code: str) -> None:
    raise gate.legacy.GateError(code)


def canonical(value: Any) -> bytes:
    return gate.legacy.canonical(value)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_text_hex(path: Path, code: str) -> str:
    value = path.read_text(encoding="ascii").strip()
    if not HASH_RE.fullmatch(value):
        reject(code)
    return value


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def run_checked(command: list[str], code: str) -> bytes:
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        reject(code)
    return proc.stdout


def spki_der(public_key: Path) -> bytes:
    result = run_checked(
        ["openssl", "pkey", "-pubin", "-in", str(public_key), "-outform", "DER"],
        "PUBLIC_KEY_PARSE_FAILED",
    )
    if not result:
        reject("PUBLIC_KEY_PARSE_FAILED")
    return result


def private_spki_der(private_key: Path) -> bytes:
    result = run_checked(
        ["openssl", "pkey", "-in", str(private_key), "-pubout", "-outform", "DER"],
        "PRIVATE_KEY_PARSE_FAILED",
    )
    if not result:
        reject("PRIVATE_KEY_PARSE_FAILED")
    return result


def verify_openssl_signature(public_key: Path, payload: bytes, tpm_signature: bytes, code: str) -> None:
    if len(tpm_signature) < 6:
        reject(code)
    sig_alg = int.from_bytes(tpm_signature[0:2], "big")
    hash_alg = int.from_bytes(tpm_signature[2:4], "big")
    sig_size = int.from_bytes(tpm_signature[4:6], "big")
    signature = tpm_signature[6:]
    if sig_alg != TPM_ALG_RSASSA or hash_alg != TPM_ALG_SHA256:
        reject(code + "_ALGORITHM_INVALID")
    if sig_size != len(signature) or sig_size != 256:
        reject(code + "_LENGTH_INVALID")
    with tempfile.NamedTemporaryFile(prefix="ario-r22-33-tpm-signature-", delete=True) as stream:
        stream.write(signature)
        stream.flush()
        proc = subprocess.run(
            ["openssl", "dgst", "-sha256", "-verify", str(public_key),
             "-signature", stream.name],
            input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
    # openssl dgst -verify reads the message from stdin when no file is supplied.
    if proc.returncode != 0 or b"Verified OK" not in proc.stdout:
        reject(code + "_CRYPTOGRAPHIC_VERIFICATION_FAILED")


def der_length(length: int) -> bytes:
    if length < 0x80:
        return bytes([length])
    raw = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(raw)]) + raw


def der_tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + der_length(len(value)) + value


def der_integer(value: bytes) -> bytes:
    value = value.lstrip(b"\x00") or b"\x00"
    if value[0] & 0x80:
        value = b"\x00" + value
    return der_tlv(0x02, value)


def rsa_spki_from_tpm_public(public_area: bytes) -> bytes:
    reader = attest.Reader(public_area)
    public_type = reader.u16()
    name_alg = reader.u16()
    attributes = reader.u32()
    auth_policy = reader.tpm2b()
    if public_type != 0x0001 or name_alg != TPM_ALG_SHA256:
        reject("AK_TPMT_PUBLIC_PROFILE_INVALID")
    if auth_policy:
        reject("AK_TPMT_PUBLIC_AUTH_POLICY_NOT_EMPTY")
    symmetric_alg = reader.u16()
    scheme = reader.u16()
    scheme_hash = reader.u16()
    key_bits = reader.u16()
    exponent = reader.u32()
    modulus = reader.tpm2b()
    if reader.offset != len(reader.data):
        reject("AK_TPMT_PUBLIC_TRAILING_DATA")
    if symmetric_alg != 0x0010 or scheme != TPM_ALG_RSASSA or scheme_hash != TPM_ALG_SHA256:
        reject("AK_TPMT_PUBLIC_SCHEME_INVALID")
    if key_bits != 2048 or len(modulus) != 256:
        reject("AK_TPMT_PUBLIC_RSA_SIZE_INVALID")
    if exponent == 0:
        exponent = 65537
    if exponent != 65537:
        reject("AK_TPMT_PUBLIC_RSA_EXPONENT_INVALID")
    pkcs1 = der_tlv(0x30, der_integer(modulus) + der_integer(exponent.to_bytes(
        (exponent.bit_length() + 7) // 8, "big"
    )))
    algorithm = der_tlv(
        0x30,
        der_tlv(0x06, bytes.fromhex("2a864886f70d010101")) + der_tlv(0x05, b""),
    )
    bit_string = der_tlv(0x03, b"\x00" + pkcs1)
    return der_tlv(0x30, algorithm + bit_string)




def validate_storage_ecc_public(public_area: bytes) -> None:
    reader = attest.Reader(public_area)
    public_type = reader.u16()
    name_alg = reader.u16()
    attributes = reader.u32()
    auth_policy = reader.tpm2b()
    symmetric = reader.u16()
    scheme = reader.u16()
    curve = reader.u16()
    kdf = reader.u16()
    x = reader.tpm2b()
    y = reader.tpm2b()
    if reader.offset != len(reader.data):
        reject("STORAGE_TPMT_PUBLIC_TRAILING_DATA")
    if public_type != 0x0023 or name_alg != TPM_ALG_SHA256 or auth_policy:
        reject("STORAGE_TPMT_PUBLIC_TYPE_OR_POLICY_INVALID")
    if symmetric != 0x0010 or scheme != 0x0010 or curve != 0x0003 or kdf != 0x0010:
        reject("STORAGE_TPMT_PUBLIC_MUST_BE_ECC_NIST_P256")
    if len(x) != 32 or len(y) != 32:
        reject("STORAGE_TPMT_PUBLIC_ECC_POINT_LENGTH_INVALID")


def validate_raw_manifest(root: Path) -> tuple[dict[str, Any], bytes]:
    manifest_path = root / "evidence-manifest.json"
    try:
        raw = manifest_path.read_bytes()
        manifest = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        reject("RAW_EVIDENCE_MANIFEST_UNREADABLE")
    if raw != canonical(manifest):
        reject("RAW_EVIDENCE_MANIFEST_NOT_CANONICAL")
    if not isinstance(manifest, dict) or set(manifest) != {"format", "files"}:
        reject("RAW_EVIDENCE_MANIFEST_SCHEMA_INVALID")
    if manifest.get("format") != MANIFEST_FORMAT or not isinstance(manifest.get("files"), dict):
        reject("RAW_EVIDENCE_MANIFEST_FORMAT_INVALID")
    actual_names: set[str] = set()
    for item in root.iterdir():
        if item.name == "evidence-manifest.json":
            continue
        if item.is_symlink() or not item.is_file():
            reject("RAW_EVIDENCE_UNEXPECTED_FILESYSTEM_ENTRY")
        actual_names.add(item.name)
    files = manifest["files"]
    if set(files) != actual_names or actual_names != EXPECTED_RAW_FILES:
        reject("RAW_EVIDENCE_MANIFEST_FILE_SET_MISMATCH")
    for name, expected in files.items():
        if Path(name).name != name or not isinstance(expected, str) or not HASH_RE.fullmatch(expected):
            reject("RAW_EVIDENCE_MANIFEST_ENTRY_INVALID")
        if sha256((root / name).read_bytes()) != expected:
            reject("RAW_EVIDENCE_FILE_HASH_MISMATCH:" + name)
    return manifest, raw


def validate_anchor_and_challenge(root: Path, now: int) -> tuple[dict[str, Any], dict[str, Any], bytes, Path]:
    custodian_public = root / "custodian-public.pem"
    anchor_path = root / "custodian-anchor.json"
    anchor_sig = (root / "custodian-anchor.sig").read_bytes()
    anchor, anchor_raw = gate.legacy.read_json(anchor_path)
    if anchor_raw != canonical(anchor):
        reject("CUSTODIAN_ANCHOR_NOT_CANONICAL")
    if not gate.legacy.openssl_verify(custodian_public, anchor_raw, anchor_sig):
        reject("CUSTODIAN_ANCHOR_SIGNATURE_INVALID")
    anchor = gate.legacy.validate_anchor(anchor)

    challenge_path = root / "custodian-challenge.json"
    challenge_sig = (root / "custodian-challenge.sig").read_bytes()
    challenge, challenge_raw = gate.legacy.read_json(challenge_path)
    if challenge_raw != canonical(challenge):
        reject("CUSTODIAN_CHALLENGE_NOT_CANONICAL")
    challenge = gate.validate_challenge(
        challenge, b64(challenge_sig), custodian_public, now
    )
    if challenge["device_ek_sha256"] != anchor["device_ek_sha256"]:
        reject("CHALLENGE_ANCHOR_EK_MISMATCH")
    if challenge["previous_storage_root_sha256"] != anchor["storage_root_sha256"]:
        reject("CHALLENGE_ANCHOR_ROOT_MISMATCH")
    if challenge["previous_epoch"] != anchor["epoch"]:
        reject("CHALLENGE_ANCHOR_EPOCH_MISMATCH")
    if challenge["previous_head_sha256"] != anchor["head_sha256"]:
        reject("CHALLENGE_ANCHOR_HEAD_MISMATCH")
    nonce_file = (root / "custodian-challenge-nonce.txt").read_text(encoding="ascii").strip()
    if nonce_file != challenge["nonce"]:
        reject("CHALLENGE_NONCE_FILE_MISMATCH")
    return anchor, challenge, challenge_sig, custodian_public


def read_tpm2b_file(path: Path, expected_size: int | None = None) -> bytes:
    raw = path.read_bytes()
    if len(raw) < 2:
        reject("TPM2B_FILE_TRUNCATED:" + path.name)
    size = int.from_bytes(raw[:2], "big")
    if size != len(raw) - 2:
        reject("TPM2B_FILE_LENGTH_MISMATCH:" + path.name)
    value = raw[2:]
    if expected_size is not None and len(value) != expected_size:
        reject("TPM2B_FILE_CONTENT_LENGTH_INVALID:" + path.name)
    return value


def parse_nv_attestation(raw: bytes) -> tuple[bytes, bytes, bytes, int, bytes]:
    reader = nv.Reader(raw)
    magic = reader.u32()
    kind = reader.u16()
    signer = reader.tpm2b()
    nonce = reader.tpm2b()
    reader.take(17)
    reader.u64()
    index_name = reader.tpm2b()
    offset = reader.u16()
    contents = reader.tpm2b()
    if reader.offset != len(reader.data):
        reject("NV_ATTESTATION_TRAILING_DATA")
    if magic != TPM_GENERATED or kind != TPM_ST_ATTEST_NV:
        reject("NV_ATTESTATION_MAGIC_OR_TYPE_INVALID")
    return signer, nonce, index_name, offset, contents


def parse_creation_attestation(raw: bytes) -> tuple[bytes, bytes, bytes, bytes]:
    reader = attest.Reader(raw)
    magic = reader.u32()
    kind = reader.u16()
    signer = reader.tpm2b()
    nonce = reader.tpm2b()
    reader.take(17)
    reader.u64()
    object_name = reader.tpm2b()
    creation_hash = reader.tpm2b()
    if reader.offset != len(reader.data):
        reject("CREATION_ATTESTATION_TRAILING_DATA")
    if magic != TPM_GENERATED or kind != TPM_ST_ATTEST_CREATION:
        reject("CREATION_ATTESTATION_MAGIC_OR_TYPE_INVALID")
    return signer, nonce, object_name, creation_hash


def parse_quote_attestation(raw: bytes) -> tuple[bytes, bytes, list[tuple[int, bytes]], bytes]:
    reader = attest.Reader(raw)
    magic = reader.u32()
    kind = reader.u16()
    signer = reader.tpm2b()
    nonce = reader.tpm2b()
    reader.take(17)
    reader.u64()
    count = reader.u32()
    selections: list[tuple[int, bytes]] = []
    for _ in range(count):
        hash_alg = reader.u16()
        select_size = reader.u8()
        selections.append((hash_alg, reader.take(select_size)))
    pcr_digest = reader.tpm2b()
    if reader.offset != len(reader.data):
        reject("QUOTE_ATTESTATION_TRAILING_DATA")
    if magic != TPM_GENERATED or kind != TPM_ST_ATTEST_QUOTE:
        reject("QUOTE_ATTESTATION_MAGIC_OR_TYPE_INVALID")
    return signer, nonce, selections, pcr_digest


def verify_bundle(root: Path, challenge: dict[str, Any], now: int) -> tuple[dict[str, Any], dict[str, bytes]]:
    ek_public = root / "ek-public.pem"
    ek_certificate = root / "ek-certificate.crt"
    ek_root = root / "ek-lab-root.crt"
    ek_spki = spki_der(ek_public)
    ek_fingerprint = sha256(ek_spki)
    if ek_fingerprint != read_text_hex(root / "ek-spki-sha256.txt", "EK_FINGERPRINT_INVALID"):
        reject("EK_PUBLIC_FINGERPRINT_MISMATCH")
    if ek_fingerprint != challenge["device_ek_sha256"]:
        reject("EK_IDENTITY_DOES_NOT_MATCH_CUSTODIAN_CHALLENGE")
    run_checked(
        ["openssl", "verify", "-CAfile", str(ek_root), "-purpose", "any", str(ek_certificate)],
        "EK_LAB_CERTIFICATE_CHAIN_INVALID",
    )
    with tempfile.NamedTemporaryFile(prefix="ario-r22-33-ek-cert-", suffix=".pem", delete=True) as stream:
        run_checked(
            ["openssl", "x509", "-in", str(ek_certificate), "-pubkey", "-noout", "-out", stream.name],
            "EK_CERTIFICATE_PUBLIC_KEY_EXTRACTION_FAILED",
        )
        if spki_der(Path(stream.name)) != ek_spki:
            reject("EK_CERTIFICATE_SPKI_MISMATCH")

    ak_public = root / "ak-public.pem"
    ak_spki = spki_der(ak_public)
    ak_public_area = (root / "ak-public-area.tpmt").read_bytes()
    ak_name = (root / "ak-name.bin").read_bytes()
    gate.validate_tpm_public_area(ak_public_area, ak_name, "ak")
    if rsa_spki_from_tpm_public(ak_public_area) != ak_spki:
        reject("AK_TPMT_PUBLIC_DOES_NOT_MATCH_AK_SPKI")
    ak_qualified_name = (root / "ak-qualified-name.bin").read_bytes()
    if len(ak_qualified_name) != 34 or ak_qualified_name[:2] != b"\x00\x0b":
        reject("AK_QUALIFIED_NAME_FORMAT_INVALID")

    storage_public_area = (root / "storage-public-area.tpmt").read_bytes()
    storage_name = (root / "storage-name.bin").read_bytes()
    gate.validate_tpm_public_area(storage_public_area, storage_name, "storage")
    validate_storage_ecc_public(storage_public_area)
    storage_qualified_name = (root / "storage-qualified-name.bin").read_bytes()
    if len(storage_qualified_name) != 34 or storage_qualified_name[:2] != b"\x00\x0b":
        reject("STORAGE_QUALIFIED_NAME_FORMAT_INVALID")
    storage_root = sha256(storage_name)
    if storage_root != read_text_hex(root / "storage-root-sha256.txt", "STORAGE_ROOT_HASH_INVALID"):
        reject("STORAGE_ROOT_HASH_MISMATCH")
    root_bytes = bytes.fromhex(storage_root)
    if (root / "storage-root-commitment.bin").read_bytes() != root_bytes:
        reject("STORAGE_ROOT_COMMITMENT_MISMATCH")

    creation_data = read_tpm2b_file(root / "storage-creation-data.bin")
    creation_hash = read_tpm2b_file(root / "storage-creation-hash.bin", 32)
    if hashlib.sha256(creation_data).digest() != creation_hash:
        reject("STORAGE_CREATION_HASH_MISMATCH")

    nv_index_text = (root / "nv-index.txt").read_text(encoding="ascii").strip()
    try:
        nv_index_handle = int(nv_index_text, 0)
    except ValueError:
        reject("NV_INDEX_HANDLE_INVALID")
    if nv_index_handle != NV_INDEX_HANDLE:
        reject("NV_INDEX_HANDLE_NOT_PINNED")
    nv_index_name, nv_attributes, nv_size = nv.parse_nv_public(
        str(root / "nv-public.yaml"), nv_index_text
    )
    if nv_attributes != NV_ATTRIBUTES or nv_size != NV_DATA_SIZE:
        reject("NV_PUBLIC_PROFILE_INVALID")
    nv_public_area = (
        struct.pack(">IHI", nv_index_handle, NV_NAME_ALG, nv_attributes)
        + b"\x00\x00"
        + struct.pack(">H", nv_size)
    )
    expected_nv_name = struct.pack(">H", NV_NAME_ALG) + hashlib.sha256(nv_public_area).digest()
    if nv_index_name != expected_nv_name:
        reject("NV_PUBLIC_NAME_DERIVATION_MISMATCH")
    nv_contents = (root / "nv-contents.bin").read_bytes()
    if len(nv_contents) != NV_DATA_SIZE or nv_contents != root_bytes:
        reject("NV_CONTENTS_DO_NOT_MATCH_STORAGE_ROOT")

    nv_nonce = (root / "nv-nonce.txt").read_text(encoding="ascii").strip()
    creation_nonce = (root / "creation-nonce.txt").read_text(encoding="ascii").strip()
    quote_nonce = (root / "quote-nonce.txt").read_text(encoding="ascii").strip()
    if nv_nonce != gate.derived_nv_nonce(challenge["nonce"]):
        reject("NV_NONCE_NOT_CHALLENGE_DERIVED")
    if creation_nonce != gate.derived_creation_nonce(challenge["nonce"]):
        reject("CREATION_NONCE_NOT_CHALLENGE_DERIVED")
    if quote_nonce != gate.derived_quote_nonce(challenge["nonce"]):
        reject("QUOTE_NONCE_NOT_CHALLENGE_DERIVED")

    nv_attestation = (root / "nv-attestation.bin").read_bytes()
    nv_signature = (root / "nv-attestation.sig").read_bytes()
    nv_signer, nv_extra, nv_attested_name, nv_offset, nv_attested_contents = parse_nv_attestation(nv_attestation)
    if nv_signer != ak_qualified_name:
        reject("NV_ATTESTATION_AK_QUALIFIED_NAME_MISMATCH")
    if nv_extra != bytes.fromhex(nv_nonce):
        reject("NV_ATTESTATION_NONCE_MISMATCH")
    if nv_attested_name != nv_index_name or nv_offset != 0:
        reject("NV_ATTESTATION_INDEX_OR_OFFSET_MISMATCH")
    if nv_attested_contents != nv_contents:
        reject("NV_ATTESTATION_CONTENTS_MISMATCH")
    verify_openssl_signature(ak_public, nv_attestation, nv_signature, "NV_ATTESTATION_SIGNATURE_INVALID")

    creation_attestation = (root / "creation-attestation.bin").read_bytes()
    creation_signature = (root / "creation-attestation.sig").read_bytes()
    creation_signer, creation_extra, created_name, created_hash = parse_creation_attestation(creation_attestation)
    if creation_signer != ak_qualified_name or creation_extra != bytes.fromhex(creation_nonce):
        reject("CREATION_ATTESTATION_SIGNER_OR_NONCE_MISMATCH")
    if created_name != storage_name or created_hash != creation_hash:
        reject("CREATION_ATTESTATION_OBJECT_OR_HASH_MISMATCH")
    verify_openssl_signature(
        ak_public, creation_attestation, creation_signature, "CREATION_ATTESTATION_SIGNATURE_INVALID"
    )

    pcr_before = (root / "pcr23-before.bin").read_bytes()
    pcr_after = (root / "pcr23-after.bin").read_bytes()
    event_digest = bytes.fromhex(
        (root / "pcr23-event-digest.txt").read_text(encoding="ascii").strip()
    )
    if len(pcr_before) != 32 or len(pcr_after) != 32 or len(event_digest) != 32:
        reject("PCR23_EVIDENCE_LENGTH_INVALID")
    if hashlib.sha256(pcr_before + event_digest).digest() != pcr_after:
        reject("PCR23_EXTEND_RECOMPUTATION_MISMATCH")

    quote_attestation = (root / "quote-attestation.bin").read_bytes()
    quote_signature = (root / "quote-attestation.sig").read_bytes()
    quote_signer, quote_extra, selections, quote_pcr_digest = parse_quote_attestation(quote_attestation)
    expected_selection = [(TPM_ALG_SHA256, bytes((0x00, 0x00, 0x80)))]
    if quote_signer != ak_qualified_name or quote_extra != bytes.fromhex(quote_nonce):
        reject("QUOTE_ATTESTATION_SIGNER_OR_NONCE_MISMATCH")
    if selections != expected_selection:
        reject("QUOTE_PCR_SELECTION_MISMATCH")
    pcr_digest_sha256 = sha256(pcr_after)
    if quote_pcr_digest != bytes.fromhex(pcr_digest_sha256):
        reject("QUOTE_PCR_DIGEST_MISMATCH")
    verify_openssl_signature(ak_public, quote_attestation, quote_signature, "QUOTE_ATTESTATION_SIGNATURE_INVALID")

    raw_manifest_bytes = (root / "evidence-manifest.json").read_bytes()
    manifest = {
        "ek_certificate_sha256": sha256(ek_certificate.read_bytes()),
        "ek_spki_sha256": ek_fingerprint,
        "ak_name_sha256": sha256(ak_name),
        "ak_public_sha256": sha256(ak_spki),
        "storage_name_sha256": storage_root,
        "storage_public_area_sha256": sha256(storage_public_area),
        "ak_public_area_sha256": sha256(ak_public_area),
        "creation_attestation_sha256": sha256(creation_attestation),
        "creation_signature_sha256": sha256(creation_signature),
        "quote_attestation_sha256": sha256(quote_attestation),
        "quote_signature_sha256": sha256(quote_signature),
        "pcr_value_sha256": pcr_digest_sha256,
        "creation_hash_sha256": sha256(creation_hash),
        "ak_qualified_name_sha256": sha256(ak_qualified_name),
        "nv_index_name_sha256": sha256(nv_index_name),
        "nv_public_area_sha256": sha256(nv_public_area),
        "nv_contents_sha256": sha256(nv_contents),
        "nv_qualified_signer_sha256": sha256(nv_signer),
        "nv_nonce_sha256": sha256(bytes.fromhex(nv_nonce)),
        "nv_attestation_sha256": sha256(nv_attestation),
        "nv_signature_sha256": sha256(nv_signature),
        "raw_evidence_manifest_sha256": sha256(raw_manifest_bytes),
    }
    if set(manifest) != gate.MANIFEST_FIELDS:
        reject("VERIFIER_MANIFEST_SCHEMA_MISMATCH")

    receipt_values = {
        "device_ek_sha256": ek_fingerprint,
        "ek_spki_der_b64": b64(ek_spki),
        "ek_certificate_sha256": manifest["ek_certificate_sha256"],
        "creation_hash_sha256": manifest["creation_hash_sha256"],
        "raw_evidence_manifest_sha256": manifest["raw_evidence_manifest_sha256"],
        "storage_name_b64": b64(storage_name),
        "storage_public_area_tpmt_b64": b64(storage_public_area),
        "storage_root_sha256": storage_root,
        "previous_storage_root_sha256": challenge["previous_storage_root_sha256"],
        "previous_epoch": challenge["previous_epoch"],
        "next_epoch": challenge["next_epoch"],
        "previous_head_sha256": challenge["previous_head_sha256"],
        "next_head_sha256": challenge["next_head_sha256"],
        "ak_name_b64": b64(ak_name),
        "ak_name_sha256": sha256(ak_name),
        "ak_public_spki_der_b64": b64(ak_spki),
        "ak_public_sha256": sha256(ak_spki),
        "ak_public_area_tpmt_b64": b64(ak_public_area),
        "ak_qualified_name_b64": b64(ak_qualified_name),
        "ak_qualified_name_sha256": sha256(ak_qualified_name),
        "nv_index_handle": nv_index_handle,
        "nv_name_alg": NV_NAME_ALG,
        "nv_attributes": nv_attributes,
        "nv_data_size": nv_size,
        "nv_auth_policy_b64": b64(b""),
        "nv_index_name_b64": b64(nv_index_name),
        "nv_contents_b64": b64(nv_contents),
        "nv_offset": nv_offset,
        "nv_nonce": nv_nonce,
        "creation_nonce": creation_nonce,
        "quote_nonce": quote_nonce,
        "nv_qualified_signer_b64": b64(nv_signer),
        "nv_attestation_sha256": manifest["nv_attestation_sha256"],
        "nv_signature_sha256": manifest["nv_signature_sha256"],
        "quote_attestation_sha256": manifest["quote_attestation_sha256"],
        "quote_signature_sha256": manifest["quote_signature_sha256"],
        "creation_attestation_sha256": manifest["creation_attestation_sha256"],
        "creation_signature_sha256": manifest["creation_signature_sha256"],
        "pcr_selection": "sha256:23",
        "pcr_digest_sha256": pcr_digest_sha256,
        "evidence_manifest": manifest,
        "evidence_bundle_sha256": sha256(canonical(manifest)),
        "policy_id": POLICY_ID,
    }
    receipt_values.update({
        "format": gate.RECEIPT_FORMAT,
        "decision": "ACCEPTED",
        "challenge_sha256": sha256(canonical(challenge)),
        "challenge_nonce": challenge["nonce"],
        "issued_at": max(now, challenge["issued_at"]),
        "expires_at": min(challenge["expires_at"], max(now, challenge["issued_at"]) + 120),
    })
    return receipt_values, {
        "ek_spki": ek_spki,
        "ak_spki": ak_spki,
        "ak_public_area": ak_public_area,
        "storage_public_area": storage_public_area,
        "storage_name": storage_name,
        "nv_index_name": nv_index_name,
        "nv_contents": nv_contents,
        "nv_attestation": nv_attestation,
        "nv_signature": nv_signature,
        "creation_attestation": creation_attestation,
        "creation_signature": creation_signature,
        "quote_attestation": quote_attestation,
        "quote_signature": quote_signature,
        "raw_manifest": raw_manifest_bytes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify raw R22.32 evidence and issue a signed R22.33 verifier receipt.")
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--verifier-private-key", required=True, type=Path)
    parser.add_argument("--verifier-public-key", required=True, type=Path)
    parser.add_argument("--receipt-output", required=True, type=Path)
    parser.add_argument("--receipt-signature-output", required=True, type=Path)
    parser.add_argument("--request-output", required=True, type=Path)
    args = parser.parse_args()

    try:
        if args.evidence_dir.is_symlink():
            reject("RAW_EVIDENCE_DIRECTORY_SYMLINK")
        root = args.evidence_dir.resolve(strict=True)
        if not root.is_dir():
            reject("RAW_EVIDENCE_DIRECTORY_INVALID")
        raw_manifest, _manifest_raw = validate_raw_manifest(root)
        now = int(time.time())
        _anchor, challenge, challenge_signature, custodian_public = validate_anchor_and_challenge(root, now)
        receipt, _evidence = verify_bundle(root, challenge, now)

        verifier_spki = spki_der(args.verifier_public_key)
        if verifier_spki != private_spki_der(args.verifier_private_key):
            reject("VERIFIER_KEYPAIR_MISMATCH")
        verifier_fingerprint = sha256(verifier_spki)
        receipt["verifier_spki_sha256"] = verifier_fingerprint

        if receipt["issued_at"] >= receipt["expires_at"]:
            reject("VERIFIER_RECEIPT_WINDOW_EXPIRED")
        with tempfile.NamedTemporaryFile(prefix="ario-r22-33-receipt-", delete=True) as payload:
            payload.write(canonical(receipt))
            payload.flush()
            signature = run_checked(
                ["openssl", "dgst", "-sha256", "-sign", str(args.verifier_private_key), payload.name],
                "VERIFIER_RECEIPT_SIGNING_FAILED",
            )
        gate.validate_receipt(
            receipt, b64(signature), challenge, args.verifier_public_key,
            verifier_fingerprint, int(time.time()),
        )

        receipt_hash = sha256(canonical(receipt))
        request = {
            "device_ek_sha256": challenge["device_ek_sha256"],
            "storage_root_sha256": receipt["storage_root_sha256"],
            "previous_epoch": challenge["previous_epoch"],
            "next_epoch": challenge["next_epoch"],
            "previous_head_sha256": challenge["previous_head_sha256"],
            "next_head_sha256": challenge["next_head_sha256"],
            "reason": challenge["reason"],
            "nonce": gate.derived_transition_nonce(challenge["nonce"], receipt_hash),
            "attestation_challenge": challenge,
            "attestation_challenge_signature_b64": b64(challenge_signature),
            "attestation_receipt": receipt,
            "attestation_receipt_signature_b64": b64(signature),
        }
        args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
        args.receipt_signature_output.parent.mkdir(parents=True, exist_ok=True)
        args.request_output.parent.mkdir(parents=True, exist_ok=True)
        gate.legacy.atomic_write(args.receipt_output, canonical(receipt))
        gate.legacy.atomic_write(args.receipt_signature_output, signature)
        gate.legacy.atomic_write(args.request_output, canonical(request))
        print("PASS raw evidence manifest: every exported file hash verified")
        print("PASS synthetic EK certificate chain and EK SPKI identity")
        print("PASS AK TPMT_PUBLIC, RSA SPKI, Name and restricted-signing profile")
        print("PASS storage TPMT_PUBLIC Name and restricted-decryption profile")
        print("PASS NV_Certify signature, challenge, index Name, offset and exact root contents")
        print("PASS CertifyCreation signature, challenge, AK signer, storage Name and creation hash")
        print("PASS PCR 23 extend, Quote signature, selection and quoted digest")
        print("PASS all TPM nonces derived from the signed custodian challenge")
        print("PASS pinned-schema verifier receipt signed and request normalized")
        return 0
    except gate.legacy.GateError as exc:
        print("REJECT " + exc.code)
        return 3
    except (OSError, ValueError, struct.error, subprocess.SubprocessError) as exc:
        print("REJECT RAW_EVIDENCE_ERROR:" + type(exc).__name__)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
