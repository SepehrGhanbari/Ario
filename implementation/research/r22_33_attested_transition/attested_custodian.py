#!/usr/bin/env python3
"""Strict proof-carrying wrapper around the R22.31 monotonic custodian gate."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
import struct
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

R31_DIR = Path(__file__).resolve().parents[1] / "r22_31_custodian_monotonic_state"
sys.path.insert(0, str(R31_DIR))
import custodian_state_legacy as legacy  # noqa: E402

POLICY_ID = "R22.32_EK_AK_QUOTE_CERTIFYCREATION_V1"
NV_INDEX_HANDLE = 0x01500020
NV_NAME_ALG = 0x000B
NV_ATTRIBUTES = 0x20060006
NV_DATA_SIZE = 32
CHALLENGE_FORMAT = "ARIO-R22.33-ATTESTATION-CHALLENGE-V1"
RECEIPT_FORMAT = "ARIO-R22.33-TPM-VERIFIER-RECEIPT-V1"
PIN_FORMAT = "ARIO-R22.33-VERIFIER-PIN-V1"
BUNDLE_FORMAT = "ARIO-R22.33-ATTESTED-TRANSITION-BUNDLE-V1"
HASH_RE = re.compile(r"^[0-9a-f]{64}$")

BASE_FIELDS = {
    "device_ek_sha256", "storage_root_sha256", "previous_epoch", "next_epoch",
    "previous_head_sha256", "next_head_sha256", "reason", "nonce",
}
REQUEST_FIELDS = BASE_FIELDS | {
    "attestation_challenge", "attestation_challenge_signature_b64",
    "attestation_receipt", "attestation_receipt_signature_b64",
}
CHALLENGE_FIELDS = {
    "format", "nonce", "device_ek_sha256", "previous_storage_root_sha256",
    "previous_epoch", "next_epoch", "previous_head_sha256", "next_head_sha256",
    "reason", "policy_id", "issued_at", "expires_at",
}
PIN_FIELDS = {"format", "attestation_verifier_spki_sha256", "policy_id"}
RECEIPT_FIELDS = {
    "format", "decision", "challenge_sha256", "challenge_nonce",
    "device_ek_sha256", "ek_spki_der_b64", "storage_name_b64",
    "storage_public_area_tpmt_b64", "storage_root_sha256", "previous_storage_root_sha256",
    "previous_epoch", "next_epoch", "previous_head_sha256", "next_head_sha256",
    "ak_name_b64", "ak_name_sha256", "ak_public_spki_der_b64", "ak_public_sha256",
    "ak_public_area_tpmt_b64", "ak_qualified_name_b64", "ak_qualified_name_sha256",
    "nv_index_handle", "nv_name_alg", "nv_attributes", "nv_data_size",
    "nv_auth_policy_b64", "nv_index_name_b64", "nv_contents_b64",
    "nv_offset", "nv_nonce", "creation_nonce", "quote_nonce",
    "nv_qualified_signer_b64", "nv_attestation_sha256", "nv_signature_sha256",
    "quote_attestation_sha256", "quote_signature_sha256",
    "creation_attestation_sha256", "creation_signature_sha256",
    "pcr_selection", "pcr_digest_sha256", "evidence_manifest",
    "evidence_bundle_sha256", "policy_id", "issued_at", "expires_at",
    "verifier_spki_sha256",
}
MANIFEST_FIELDS = {
    "ek_certificate_sha256", "ek_spki_sha256",
    "ak_name_sha256", "ak_public_sha256",
    "storage_name_sha256", "storage_public_area_sha256", "ak_public_area_sha256",
    "creation_attestation_sha256",
    "creation_signature_sha256", "quote_attestation_sha256",
    "quote_signature_sha256", "pcr_value_sha256", "creation_hash_sha256",
    "ak_qualified_name_sha256", "nv_index_name_sha256", "nv_public_area_sha256",
    "nv_contents_sha256", "nv_qualified_signer_sha256", "nv_nonce_sha256",
    "nv_attestation_sha256", "nv_signature_sha256",
}


def fail(code: str) -> None:
    raise legacy.GateError(code)


def require_exact_keys(value: Any, expected: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        fail(code)
    return value


def require_int(value: Any, expected: int, code: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value != expected:
        fail(code)


def validate_hash(value: Any, code: str) -> str:
    if not isinstance(value, str) or not HASH_RE.fullmatch(value):
        fail(code)
    return value


def decode_b64(value: Any, code: str) -> bytes:
    if not isinstance(value, str):
        fail(code)
    try:
        return base64.b64decode(value, validate=True)
    except Exception as exc:
        raise legacy.GateError(code) from exc


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def spki_der(public_key: Path) -> bytes:
    proc = subprocess.run(
        ["openssl", "pkey", "-pubin", "-in", str(public_key), "-outform", "DER"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0 or not proc.stdout:
        fail("PUBLIC_KEY_PARSE_FAILED")
    return proc.stdout

def private_spki_der(private_key: Path) -> bytes:
    proc = subprocess.run(
        ["openssl", "pkey", "-in", str(private_key), "-pubout", "-outform", "DER"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0 or not proc.stdout:
        fail("PRIVATE_KEY_PARSE_FAILED")
    return proc.stdout


def validate_custodian_keypair(public_key: Path, private_key: Path) -> None:
    if spki_der(public_key) != private_spki_der(private_key):
        fail("CUSTODIAN_KEYPAIR_MISMATCH")


def validate_tpm_public_area(public_area: bytes, name: bytes, object_kind: str) -> None:
    if len(public_area) < 8:
        fail("ATTESTATION_" + object_kind.upper() + "_TPMT_TRUNCATED")
    public_type = int.from_bytes(public_area[0:2], "big")
    name_alg = int.from_bytes(public_area[2:4], "big")
    attributes = int.from_bytes(public_area[4:8], "big")
    if name_alg != 0x000B:
        fail("ATTESTATION_" + object_kind.upper() + "_NAME_ALG_INVALID")
    if object_kind == "storage":
        if public_type != 0x0023:
            fail("ATTESTATION_STORAGE_PUBLIC_TYPE_INVALID")
        # A storage primary is a restricted decryption object, never a signer.
        required = (1 << 1) | (1 << 4) | (1 << 5) | (1 << 16) | (1 << 17)
        forbidden = (1 << 18)
    elif object_kind == "ak":
        if public_type != 0x0001:
            fail("ATTESTATION_AK_PUBLIC_TYPE_INVALID")
        # An AK is a restricted signing object, never a decrypt-capable key.
        required = (1 << 1) | (1 << 4) | (1 << 5) | (1 << 16) | (1 << 18)
        forbidden = (1 << 17)
    else:
        fail("ATTESTATION_PUBLIC_KIND_INVALID")
    if attributes & required != required:
        fail("ATTESTATION_" + object_kind.upper() + "_ATTRIBUTES_INVALID")
    if attributes & forbidden:
        fail("ATTESTATION_" + object_kind.upper() + "_ATTRIBUTES_FORBIDDEN")
    expected_name = public_area[2:4] + hashlib.sha256(public_area).digest()
    if name != expected_name:
        fail("ATTESTATION_" + object_kind.upper() + "_TPM_NAME_MISMATCH")


def validate_spki_der_bytes(data: bytes, code: str) -> None:
    with tempfile.NamedTemporaryFile(prefix="ario-r22-33-spki-", suffix=".der", delete=True) as stream:
        stream.write(data)
        stream.flush()
        proc = subprocess.run(
            ["openssl", "pkey", "-pubin", "-inform", "DER", "-in", stream.name, "-noout"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
    if proc.returncode != 0:
        fail(code)


def verify_signature_bytes(public_key: Path, payload: bytes, signature: bytes) -> bool:
    return legacy.openssl_verify(public_key, payload, signature)


def verify_signed_object(public_key: Path, value: dict[str, Any], signature_b64: str, code: str) -> None:
    signature = decode_b64(signature_b64, code)
    if not verify_signature_bytes(public_key, legacy.canonical(value), signature):
        fail(code)


def validate_time_window(issued: Any, expires: Any, now: int, code: str) -> None:
    if isinstance(issued, bool) or not isinstance(issued, int):
        fail(code + "_ISSUED_AT_INVALID")
    if isinstance(expires, bool) or not isinstance(expires, int):
        fail(code + "_EXPIRES_AT_INVALID")
    if issued > now + 30:
        fail(code + "_ISSUED_IN_FUTURE")
    if expires <= now or expires <= issued:
        fail(code + "_EXPIRED")
    if expires - issued > 300:
        fail(code + "_TTL_TOO_LONG")


def derived_nv_nonce(challenge_nonce: str) -> str:
    material = b"ARIO-R22.33-NV-ATTESTATION-NONCE-V1\x00" + bytes.fromhex(challenge_nonce)
    return sha256(material)


def derived_creation_nonce(challenge_nonce: str) -> str:
    material = b"ARIO-R22.33-CERTIFY-CREATION-NONCE-V1\x00" + bytes.fromhex(challenge_nonce)
    return sha256(material)


def derived_quote_nonce(challenge_nonce: str) -> str:
    material = b"ARIO-R22.33-PCR-QUOTE-NONCE-V1\x00" + bytes.fromhex(challenge_nonce)
    return sha256(material)


def derived_transition_nonce(challenge_nonce: str, receipt_sha256: str) -> str:
    material = (
        b"ARIO-R22.33-TRANSITION-NONCE-V1\x00"
        + bytes.fromhex(challenge_nonce)
        + bytes.fromhex(receipt_sha256)
    )
    return sha256(material)


def reject_path_aliases(named_paths: list[tuple[str, Path]]) -> None:
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
                fail(f"PATH_ALIAS:{prior_name}:{name}")
        seen.append((name, path, resolved))


def validate_challenge(challenge: Any, signature_b64: Any, public_key: Path, now: int) -> dict[str, Any]:
    challenge = require_exact_keys(challenge, CHALLENGE_FIELDS, "CHALLENGE_SCHEMA_INVALID")
    if challenge.get("format") != CHALLENGE_FORMAT:
        fail("CHALLENGE_FORMAT_INVALID")
    if challenge.get("policy_id") != POLICY_ID:
        fail("CHALLENGE_POLICY_INVALID")
    if challenge.get("reason") != "TPM_CLEAR_RECOVERY":
        fail("CHALLENGE_REASON_INVALID")
    validate_hash(challenge.get("nonce"), "CHALLENGE_NONCE_INVALID")
    for field in ("device_ek_sha256", "previous_storage_root_sha256",
                  "previous_head_sha256", "next_head_sha256"):
        validate_hash(challenge.get(field), "CHALLENGE_" + field.upper() + "_INVALID")
    previous = challenge.get("previous_epoch")
    following = challenge.get("next_epoch")
    if isinstance(previous, bool) or not isinstance(previous, int) or previous < 0:
        fail("CHALLENGE_PREVIOUS_EPOCH_INVALID")
    if isinstance(following, bool) or not isinstance(following, int) or following != previous + 1:
        fail("CHALLENGE_NEXT_EPOCH_INVALID")
    validate_time_window(challenge.get("issued_at"), challenge.get("expires_at"), now, "CHALLENGE")
    if not isinstance(signature_b64, str):
        fail("CHALLENGE_SIGNATURE_ENCODING_INVALID")
    verify_signed_object(public_key, challenge, signature_b64, "CHALLENGE_SIGNATURE_INVALID")
    return challenge


def validate_pin(pin_path: Path, pin_signature_path: Path, custodian_public_key: Path,
                 verifier_public_key: Path) -> str:
    pin, raw = legacy.read_json(pin_path)
    if raw != legacy.canonical(pin):
        fail("VERIFIER_PIN_NOT_CANONICAL")
    require_exact_keys(pin, PIN_FIELDS, "VERIFIER_PIN_SCHEMA_INVALID")
    if pin.get("format") != PIN_FORMAT or pin.get("policy_id") != POLICY_ID:
        fail("VERIFIER_PIN_FORMAT_INVALID")
    if not legacy.openssl_verify(custodian_public_key, raw, pin_signature_path.read_bytes()):
        fail("VERIFIER_PIN_SIGNATURE_INVALID")
    pinned = validate_hash(pin.get("attestation_verifier_spki_sha256"), "VERIFIER_PIN_HASH_INVALID")
    actual = sha256(spki_der(verifier_public_key))
    if actual != pinned:
        fail("VERIFIER_KEY_NOT_PINNED")
    return actual


def validate_receipt(receipt: Any, signature_b64: Any, challenge: dict[str, Any],
                     verifier_public_key: Path, verifier_fingerprint: str, now: int) -> dict[str, Any]:
    receipt = require_exact_keys(receipt, RECEIPT_FIELDS, "ATTESTATION_RECEIPT_SCHEMA_INVALID")
    if receipt.get("format") != RECEIPT_FORMAT or receipt.get("decision") != "ACCEPTED":
        fail("ATTESTATION_RECEIPT_DECISION_INVALID")
    if receipt.get("policy_id") != POLICY_ID or receipt.get("pcr_selection") != "sha256:23":
        fail("ATTESTATION_RECEIPT_POLICY_INVALID")
    if receipt.get("verifier_spki_sha256") != verifier_fingerprint:
        fail("ATTESTATION_RECEIPT_VERIFIER_MISMATCH")
    validate_time_window(receipt.get("issued_at"), receipt.get("expires_at"), now, "ATTESTATION_RECEIPT")
    if receipt["issued_at"] < challenge["issued_at"] or receipt["expires_at"] > challenge["expires_at"]:
        fail("ATTESTATION_RECEIPT_OUTSIDE_CHALLENGE_WINDOW")

    challenge_sha = sha256(legacy.canonical(challenge))
    if receipt.get("challenge_sha256") != challenge_sha:
        fail("ATTESTATION_CHALLENGE_HASH_MISMATCH")
    if receipt.get("challenge_nonce") != challenge["nonce"]:
        fail("ATTESTATION_CHALLENGE_NONCE_MISMATCH")

    for field in ("device_ek_sha256", "storage_root_sha256",
                  "previous_storage_root_sha256", "ak_name_sha256",
                  "ak_public_sha256", "quote_attestation_sha256",
                  "quote_signature_sha256", "creation_attestation_sha256",
                  "creation_signature_sha256", "pcr_digest_sha256",
                  "nv_nonce", "creation_nonce", "quote_nonce",
                  "nv_attestation_sha256", "nv_signature_sha256",
                  "ak_qualified_name_sha256", "evidence_bundle_sha256"):
        validate_hash(receipt.get(field), "ATTESTATION_" + field.upper() + "_INVALID")

    ek_spki = decode_b64(receipt.get("ek_spki_der_b64"), "ATTESTATION_EK_SPKI_INVALID")
    validate_spki_der_bytes(ek_spki, "ATTESTATION_EK_SPKI_DER_INVALID")
    if not ek_spki or sha256(ek_spki) != receipt["device_ek_sha256"]:
        fail("ATTESTATION_EK_SPKI_HASH_MISMATCH")
    if receipt["device_ek_sha256"] != challenge["device_ek_sha256"]:
        fail("ATTESTATION_EK_IDENTITY_MISMATCH")

    storage_name = decode_b64(receipt.get("storage_name_b64"), "ATTESTATION_STORAGE_NAME_INVALID")
    storage_public_area = decode_b64(
        receipt.get("storage_public_area_tpmt_b64"), "ATTESTATION_STORAGE_TPMT_INVALID"
    )
    if len(storage_name) != 34 or storage_name[:2] != b"\x00\x0b":
        fail("ATTESTATION_STORAGE_NAME_FORMAT_INVALID")
    validate_tpm_public_area(storage_public_area, storage_name, "storage")
    if sha256(storage_name) != receipt["storage_root_sha256"]:
        fail("ATTESTATION_STORAGE_ROOT_DERIVATION_MISMATCH")
    if receipt["previous_storage_root_sha256"] != challenge["previous_storage_root_sha256"]:
        fail("ATTESTATION_PREVIOUS_STORAGE_ROOT_MISMATCH")

    ak_name = decode_b64(receipt.get("ak_name_b64"), "ATTESTATION_AK_NAME_INVALID")
    ak_public_area = decode_b64(receipt.get("ak_public_area_tpmt_b64"), "ATTESTATION_AK_TPMT_INVALID")
    validate_tpm_public_area(ak_public_area, ak_name, "ak")
    if sha256(ak_name) != receipt["ak_name_sha256"]:
        fail("ATTESTATION_AK_NAME_MISMATCH")
    ak_public = decode_b64(receipt.get("ak_public_spki_der_b64"), "ATTESTATION_AK_PUBLIC_INVALID")
    validate_spki_der_bytes(ak_public, "ATTESTATION_AK_PUBLIC_DER_INVALID")
    if not ak_public or sha256(ak_public) != receipt["ak_public_sha256"]:
        fail("ATTESTATION_AK_PUBLIC_HASH_MISMATCH")

    ak_qualified_name = decode_b64(
        receipt.get("ak_qualified_name_b64"), "ATTESTATION_AK_QUALIFIED_NAME_INVALID"
    )
    if len(ak_qualified_name) < 34 or sha256(ak_qualified_name) != receipt["ak_qualified_name_sha256"]:
        fail("ATTESTATION_AK_QUALIFIED_NAME_MISMATCH")

    require_int(receipt.get("nv_index_handle"), NV_INDEX_HANDLE, "ATTESTATION_NV_INDEX_HANDLE_INVALID")
    require_int(receipt.get("nv_name_alg"), NV_NAME_ALG, "ATTESTATION_NV_NAME_ALG_INVALID")
    require_int(receipt.get("nv_attributes"), NV_ATTRIBUTES, "ATTESTATION_NV_ATTRIBUTES_INVALID")
    require_int(receipt.get("nv_data_size"), NV_DATA_SIZE, "ATTESTATION_NV_DATA_SIZE_INVALID")
    require_int(receipt.get("nv_offset"), 0, "ATTESTATION_NV_OFFSET_INVALID")

    nv_auth_policy = decode_b64(
        receipt.get("nv_auth_policy_b64"), "ATTESTATION_NV_AUTH_POLICY_INVALID"
    )
    if nv_auth_policy:
        fail("ATTESTATION_NV_AUTH_POLICY_NOT_EMPTY")
    # Match the exact TPMT_NV_PUBLIC wire encoding used by the R22.32
    # verifier: the empty TPM2B_DIGEST authPolicy still contributes its
    # two-byte zero length before dataSize in the marshalled public area.
    nv_public_area = (
        struct.pack(">IHI", NV_INDEX_HANDLE, NV_NAME_ALG, NV_ATTRIBUTES)
        + b"\x00\x00"
        + struct.pack(">H", NV_DATA_SIZE)
    )
    expected_nv_name = struct.pack(">H", NV_NAME_ALG) + hashlib.sha256(nv_public_area).digest()
    nv_index_name = decode_b64(
        receipt.get("nv_index_name_b64"), "ATTESTATION_NV_INDEX_NAME_INVALID"
    )
    if nv_index_name != expected_nv_name:
        fail("ATTESTATION_NV_INDEX_NAME_MISMATCH")

    nv_contents = decode_b64(
        receipt.get("nv_contents_b64"), "ATTESTATION_NV_CONTENTS_INVALID"
    )
    if len(nv_contents) != NV_DATA_SIZE or nv_contents != bytes.fromhex(receipt["storage_root_sha256"]):
        fail("ATTESTATION_NV_CONTENTS_STORAGE_ROOT_MISMATCH")

    nv_qualified_signer = decode_b64(
        receipt.get("nv_qualified_signer_b64"), "ATTESTATION_NV_QUALIFIED_SIGNER_INVALID"
    )
    if nv_qualified_signer != ak_qualified_name:
        fail("ATTESTATION_NV_SIGNER_AK_QUALIFIED_NAME_MISMATCH")
    if receipt.get("nv_nonce") != derived_nv_nonce(challenge["nonce"]):
        fail("ATTESTATION_NV_NONCE_NOT_CHALLENGE_DERIVED")
    if receipt.get("creation_nonce") != derived_creation_nonce(challenge["nonce"]):
        fail("ATTESTATION_CREATION_NONCE_NOT_CHALLENGE_DERIVED")
    if receipt.get("quote_nonce") != derived_quote_nonce(challenge["nonce"]):
        fail("ATTESTATION_QUOTE_NONCE_NOT_CHALLENGE_DERIVED")

    manifest = require_exact_keys(receipt.get("evidence_manifest"), MANIFEST_FIELDS,
                                  "ATTESTATION_EVIDENCE_MANIFEST_SCHEMA_INVALID")
    for key, value in manifest.items():
        validate_hash(value, "ATTESTATION_MANIFEST_" + key.upper() + "_INVALID")
    expected_manifest_values = {
        "ek_spki_sha256": receipt["device_ek_sha256"],
        "ak_name_sha256": receipt["ak_name_sha256"],
        "ak_public_sha256": receipt["ak_public_sha256"],
        "storage_name_sha256": receipt["storage_root_sha256"],
        "storage_public_area_sha256": sha256(storage_public_area),
        "ak_public_area_sha256": sha256(ak_public_area),
        "creation_attestation_sha256": receipt["creation_attestation_sha256"],
        "creation_signature_sha256": receipt["creation_signature_sha256"],
        "quote_attestation_sha256": receipt["quote_attestation_sha256"],
        "quote_signature_sha256": receipt["quote_signature_sha256"],
        "pcr_value_sha256": receipt["pcr_digest_sha256"],
        "ak_qualified_name_sha256": receipt["ak_qualified_name_sha256"],
        "nv_index_name_sha256": sha256(nv_index_name),
        "nv_public_area_sha256": sha256(nv_public_area),
        "nv_contents_sha256": sha256(nv_contents),
        "nv_qualified_signer_sha256": sha256(nv_qualified_signer),
        "nv_nonce_sha256": sha256(bytes.fromhex(receipt["nv_nonce"])),
        "nv_attestation_sha256": receipt["nv_attestation_sha256"],
        "nv_signature_sha256": receipt["nv_signature_sha256"],
    }
    for key, value in expected_manifest_values.items():
        if manifest[key] != value:
            fail("ATTESTATION_MANIFEST_BINDING_MISMATCH:" + key)
    if sha256(legacy.canonical(manifest)) != receipt["evidence_bundle_sha256"]:
        fail("ATTESTATION_EVIDENCE_BUNDLE_HASH_MISMATCH")

    for field in ("previous_epoch", "next_epoch", "previous_head_sha256", "next_head_sha256"):
        if receipt.get(field) != challenge[field]:
            fail("ATTESTATION_TRANSITION_BINDING_MISMATCH:" + field)

    verify_signed_object(
        verifier_public_key, receipt, signature_b64,
        "ATTESTATION_RECEIPT_SIGNATURE_INVALID",
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Require a custodian challenge and pinned verifier-signed TPM receipt."
    )
    for name in (
        "anchor", "anchor-signature", "public-key", "private-key", "journal",
        "lock", "request", "response", "response-signature",
        "verifier-pin", "verifier-pin-signature", "attestation-verifier-public-key",
        "bundle", "bundle-signature",
    ):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--test-delay-after-lock-ms", type=int, default=0)
    parser.add_argument("--crash-after-commit", action="store_true")
    args = parser.parse_args()

    try:
        if args.test_delay_after_lock_ms < 0 or args.test_delay_after_lock_ms > 2000:
            fail("TEST_DELAY_OUT_OF_RANGE")
        validate_custodian_keypair(args.public_key, args.private_key)
        reject_path_aliases([
            ("anchor", args.anchor), ("anchor_signature", args.anchor_signature),
            ("public_key", args.public_key), ("private_key", args.private_key),
            ("journal", args.journal), ("lock", args.lock), ("request", args.request),
            ("response", args.response), ("response_signature", args.response_signature),
            ("verifier_pin", args.verifier_pin),
            ("verifier_pin_signature", args.verifier_pin_signature),
            ("attestation_verifier_public_key", args.attestation_verifier_public_key),
            ("bundle", args.bundle), ("bundle_signature", args.bundle_signature),
        ])

        request, request_raw = legacy.read_json(args.request)
        if request_raw != legacy.canonical(request):
            fail("REQUEST_NOT_CANONICAL")
        request = require_exact_keys(request, REQUEST_FIELDS, "REQUEST_SCHEMA_INVALID")

        now = int(time.time())
        challenge = validate_challenge(
            request["attestation_challenge"],
            request["attestation_challenge_signature_b64"],
            args.public_key, now,
        )
        verifier_fingerprint = validate_pin(
            args.verifier_pin, args.verifier_pin_signature,
            args.public_key, args.attestation_verifier_public_key,
        )
        receipt = validate_receipt(
            request["attestation_receipt"],
            request["attestation_receipt_signature_b64"],
            challenge, args.attestation_verifier_public_key,
            verifier_fingerprint, now,
        )

        expected_request_fields = {
            "device_ek_sha256": challenge["device_ek_sha256"],
            "storage_root_sha256": receipt["storage_root_sha256"],
            "previous_epoch": challenge["previous_epoch"],
            "next_epoch": challenge["next_epoch"],
            "previous_head_sha256": challenge["previous_head_sha256"],
            "next_head_sha256": challenge["next_head_sha256"],
            "reason": challenge["reason"],
        }
        for field, expected in expected_request_fields.items():
            if request.get(field) != expected:
                fail("REQUEST_ATTESTATION_BINDING_MISMATCH:" + field)

        receipt_hash = sha256(legacy.canonical(receipt))
        expected_nonce = derived_transition_nonce(challenge["nonce"], receipt_hash)
        if request.get("nonce") != expected_nonce:
            fail("REQUEST_DERIVED_NONCE_MISMATCH")

        base_request = {key: request[key] for key in BASE_FIELDS}
        with tempfile.TemporaryDirectory(prefix="ario-r22-33-normalized-") as directory:
            normalized_request = Path(directory) / "normalized-request.json"
            legacy.atomic_write(normalized_request, legacy.canonical(base_request))
            command = [
                sys.executable,
                str(R31_DIR / "custodian_state_legacy.py"),
                "--anchor", str(args.anchor),
                "--anchor-signature", str(args.anchor_signature),
                "--public-key", str(args.public_key),
                "--private-key", str(args.private_key),
                "--journal", str(args.journal),
                "--lock", str(args.lock),
                "--request", str(normalized_request),
                "--response", str(args.response),
                "--response-signature", str(args.response_signature),
            ]
            if args.test_delay_after_lock_ms:
                command.extend(["--test-delay-after-lock-ms", str(args.test_delay_after_lock_ms)])
            if args.crash_after_commit:
                command.append("--crash-after-commit")
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            if result.stdout:
                sys.stdout.write(result.stdout)
            if result.stderr:
                sys.stderr.write(result.stderr)
            if result.returncode != 0:
                return result.returncode

        custodian_receipt_raw = args.response.read_bytes()
        custodian_signature = args.response_signature.read_bytes()
        if not legacy.openssl_verify(args.public_key, custodian_receipt_raw, args.response_signature.read_bytes()):
            fail("CUSTODIAN_RECEIPT_SIGNATURE_INVALID")
        custodian_receipt, _ = legacy.read_json(args.response)
        if custodian_receipt.get("request_sha256") != sha256(legacy.canonical(base_request)):
            fail("CUSTODIAN_RECEIPT_REQUEST_HASH_MISMATCH")

        bundle = {
            "format": BUNDLE_FORMAT,
            "provenance": "PINNED_VERIFIER_SIGNED_TPM_ATTESTATION",
            "policy_id": POLICY_ID,
            "inner_receipt_provenance": custodian_receipt.get("storage_root_provenance"),
            "attestation_challenge": challenge,
            "attestation_challenge_signature_b64": request["attestation_challenge_signature_b64"],
            "attestation_challenge_sha256": sha256(legacy.canonical(challenge)),
            "attestation_receipt": receipt,
            "attestation_receipt_signature_b64": request["attestation_receipt_signature_b64"],
            "attestation_receipt_sha256": receipt_hash,
            "transition_request": base_request,
            "transition_request_sha256": sha256(legacy.canonical(base_request)),
            "custodian_receipt": custodian_receipt,
            "custodian_receipt_signature_b64": base64.b64encode(custodian_signature).decode("ascii"),
            "custodian_receipt_sha256": sha256(custodian_receipt_raw),
        }
        bundle_raw = legacy.canonical(bundle)
        bundle_signature = legacy.openssl_sign(args.private_key, bundle_raw)
        legacy.atomic_write(args.bundle, bundle_raw)
        legacy.atomic_write(args.bundle_signature, bundle_signature)
        print("ATTESTED_TRANSITION_BUNDLE_CREATED")
        return 0
    except legacy.GateError as exc:
        print("REJECT " + exc.code)
        return 3
    except OSError as exc:
        print("REJECT IO_ERROR:" + type(exc).__name__)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
