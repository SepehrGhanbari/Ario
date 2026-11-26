from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import struct
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
R31_DIR = HERE.parent / "r22_31_custodian_monotonic_state"
DEFAULT_GATE = R31_DIR / "custodian_state.py"
LEGACY_GATE = R31_DIR / "custodian_state_legacy.py"
ISSUER = HERE / "issue_challenge.py"

sys.path.insert(0, str(HERE))
from attested_custodian import derived_nv_nonce, derived_transition_nonce  # noqa: E402


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def b64(value):
    return base64.b64encode(value).decode("ascii")


def keypair(directory: Path, stem: str):
    private = directory / f"{stem}.key"
    public = directory / f"{stem}.pub"
    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["openssl", "pkey", "-in", str(private), "-pubout", "-out", str(public)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return private, public


def spki_der(public: Path):
    return subprocess.run(
        ["openssl", "pkey", "-pubin", "-in", str(public), "-outform", "DER"],
        check=True, stdout=subprocess.PIPE,
    ).stdout


def sign(private: Path, payload: bytes):
    return subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", str(private)],
        input=payload, check=True, stdout=subprocess.PIPE,
    ).stdout


def verify(public: Path, payload: bytes, signature: bytes):
    with tempfile.NamedTemporaryFile() as stream:
        stream.write(signature)
        stream.flush()
        subprocess.run(
            ["openssl", "dgst", "-sha256", "-verify", str(public),
             "-signature", stream.name],
            input=payload, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


class AttestedCustodianTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ario-r22-33-")
        self.root = Path(self.temp.name)
        self.custodian_private, self.custodian_public = keypair(self.root, "custodian")
        self.verifier_private, self.verifier_public = keypair(self.root, "verifier")
        self.ek_private, self.ek_public = keypair(self.root, "ek")
        self.ak_private, self.ak_public = keypair(self.root, "ak")

        self.ek_spki = spki_der(self.ek_public)
        self.ak_spki = spki_der(self.ak_public)
        self.verifier_spki = spki_der(self.verifier_public)

        self.anchor = {
            "format": "ARIO-R22.31-ANCHOR-V1",
            "device_ek_sha256": digest(self.ek_spki),
            "storage_root_sha256": digest(b"initial-storage-root"),
            "epoch": 7,
            "head_sha256": digest(b"initial-head"),
        }
        self.anchor_path = self.root / "anchor.json"
        self.anchor_sig_path = self.root / "anchor.sig"
        self.anchor_path.write_bytes(canonical(self.anchor))
        self.anchor_sig_path.write_bytes(sign(self.custodian_private, canonical(self.anchor)))

        self.pin = {
            "format": "ARIO-R22.33-VERIFIER-PIN-V1",
            "attestation_verifier_spki_sha256": digest(self.verifier_spki),
            "policy_id": "R22.32_EK_AK_QUOTE_CERTIFYCREATION_V1",
        }
        self.pin_path = self.root / "verifier-pin.json"
        self.pin_sig_path = self.root / "verifier-pin.sig"
        self.pin_path.write_bytes(canonical(self.pin))
        self.pin_sig_path.write_bytes(sign(self.custodian_private, canonical(self.pin)))

        self.journal = self.root / "custodian.jsonl"
        self.lock = self.root / "custodian.lock"
        self.next_head = digest(b"next-head")
        self.challenge_path = self.root / "challenge.json"
        self.challenge_sig_path = self.root / "challenge.sig"
        result = subprocess.run([
            sys.executable, str(ISSUER),
            "--anchor", str(self.anchor_path),
            "--anchor-signature", str(self.anchor_sig_path),
            "--public-key", str(self.custodian_public),
            "--private-key", str(self.custodian_private),
            "--journal", str(self.journal),
            "--lock", str(self.lock),
            "--output", str(self.challenge_path),
            "--signature", str(self.challenge_sig_path),
            "--next-head-sha256", self.next_head,
        ], text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.challenge = json.loads(self.challenge_path.read_text())
        self.challenge_signature_b64 = b64(self.challenge_sig_path.read_bytes())

    def tearDown(self):
        self.temp.cleanup()

    def make_receipt(self, *, change=None):
        now = int(time.time())
        storage_attrs = (1 << 1) | (1 << 4) | (1 << 5) | (1 << 16) | (1 << 17)
        ak_attrs = (1 << 1) | (1 << 4) | (1 << 5) | (1 << 16) | (1 << 18)
        storage_public_area = b"\x00\x23\x00\x0b" + storage_attrs.to_bytes(4, "big") + b"storage-public-area"
        ak_public_area = b"\x00\x01\x00\x0b" + ak_attrs.to_bytes(4, "big") + b"ak-public-area"
        storage_name = storage_public_area[2:4] + hashlib.sha256(storage_public_area).digest()
        ak_name = ak_public_area[2:4] + hashlib.sha256(ak_public_area).digest()
        ak_qualified_name = b"\x00\x0b" + hashlib.sha256(b"synthetic AK qualified name").digest()
        nv_index_handle = 0x01500020
        nv_name_alg = 0x000B
        nv_attributes = 0x20060006
        nv_data_size = 32
        # TPM2B_DIGEST authPolicy is still marshalled as a two-byte zero length.
        # Keep this wire encoding identical to R22.32 verify_nv_attestation.py.
        nv_public_area = (
            struct.pack(">IHI", nv_index_handle, nv_name_alg, nv_attributes)
            + b"\x00\x00"
            + struct.pack(">H", nv_data_size)
        )
        assert ak_qualified_name[:2] == b"\x00\x0b"
        assert nv_public_area[10:12] == b"\x00\x00"
        nv_index_name = struct.pack(">H", nv_name_alg) + hashlib.sha256(nv_public_area).digest()
        storage_root = digest(storage_name)
        nv_contents = bytes.fromhex(storage_root)
        nv_nonce = derived_nv_nonce(self.challenge["nonce"])
        nv_attestation_sha256 = digest(b"synthetic NV attestation")
        nv_signature_sha256 = digest(b"synthetic NV signature")
        manifest = {
            "ek_certificate_sha256": digest(b"synthetic EK certificate"),
            "ek_spki_sha256": digest(self.ek_spki),
            "ak_name_sha256": digest(ak_name),
            "ak_public_sha256": digest(self.ak_spki),
            "storage_name_sha256": digest(storage_name),
            "storage_public_area_sha256": digest(storage_public_area),
            "ak_public_area_sha256": digest(ak_public_area),
            "ak_qualified_name_sha256": digest(ak_qualified_name),
            "nv_index_name_sha256": digest(nv_index_name),
            "nv_public_area_sha256": digest(nv_public_area),
            "nv_contents_sha256": digest(nv_contents),
            "nv_qualified_signer_sha256": digest(ak_qualified_name),
            "nv_nonce_sha256": digest(bytes.fromhex(nv_nonce)),
            "nv_attestation_sha256": nv_attestation_sha256,
            "nv_signature_sha256": nv_signature_sha256,
            "creation_attestation_sha256": digest(b"creation attest"),
            "creation_signature_sha256": digest(b"creation signature"),
            "quote_attestation_sha256": digest(b"quote attest"),
            "quote_signature_sha256": digest(b"quote signature"),
            "pcr_value_sha256": digest(b"PCR 23 value"),
            "creation_hash_sha256": digest(b"creation hash"),
        }
        receipt = {
            "format": "ARIO-R22.33-TPM-VERIFIER-RECEIPT-V1",
            "decision": "ACCEPTED",
            "challenge_sha256": digest(canonical(self.challenge)),
            "challenge_nonce": self.challenge["nonce"],
            "device_ek_sha256": digest(self.ek_spki),
            "ek_spki_der_b64": b64(self.ek_spki),
            "storage_name_b64": b64(storage_name),
            "storage_public_area_tpmt_b64": b64(storage_public_area),
            "storage_root_sha256": storage_root,
            "previous_storage_root_sha256": self.challenge["previous_storage_root_sha256"],
            "previous_epoch": self.challenge["previous_epoch"],
            "next_epoch": self.challenge["next_epoch"],
            "previous_head_sha256": self.challenge["previous_head_sha256"],
            "next_head_sha256": self.challenge["next_head_sha256"],
            "ak_name_b64": b64(ak_name),
            "ak_public_area_tpmt_b64": b64(ak_public_area),
            "ak_name_sha256": digest(ak_name),
            "ak_public_spki_der_b64": b64(self.ak_spki),
            "ak_public_sha256": digest(self.ak_spki),
            "ak_qualified_name_b64": b64(ak_qualified_name),
            "ak_qualified_name_sha256": digest(ak_qualified_name),
            "nv_index_handle": nv_index_handle,
            "nv_name_alg": nv_name_alg,
            "nv_attributes": nv_attributes,
            "nv_data_size": nv_data_size,
            "nv_auth_policy_b64": b64(b""),
            "nv_index_name_b64": b64(nv_index_name),
            "nv_contents_b64": b64(nv_contents),
            "nv_offset": 0,
            "nv_nonce": nv_nonce,
            "nv_qualified_signer_b64": b64(ak_qualified_name),
            "nv_attestation_sha256": nv_attestation_sha256,
            "nv_signature_sha256": nv_signature_sha256,
            "quote_attestation_sha256": manifest["quote_attestation_sha256"],
            "quote_signature_sha256": manifest["quote_signature_sha256"],
            "creation_attestation_sha256": manifest["creation_attestation_sha256"],
            "creation_signature_sha256": manifest["creation_signature_sha256"],
            "pcr_selection": "sha256:23",
            "pcr_digest_sha256": manifest["pcr_value_sha256"],
            "evidence_manifest": manifest,
            "evidence_bundle_sha256": digest(canonical(manifest)),
            "policy_id": "R22.32_EK_AK_QUOTE_CERTIFYCREATION_V1",
            "issued_at": max(now, self.challenge["issued_at"]),
            "expires_at": self.challenge["expires_at"],
            "verifier_spki_sha256": digest(self.verifier_spki),
        }
        if change:
            change(receipt)
        return receipt

    def make_request(self, *, receipt=None, challenge=None, challenge_signature_b64=None):
        challenge = challenge or self.challenge
        receipt = receipt or self.make_receipt()
        receipt_hash = digest(canonical(receipt))
        nonce = derived_transition_nonce(challenge["nonce"], receipt_hash)
        request = {
            "device_ek_sha256": challenge["device_ek_sha256"],
            "storage_root_sha256": receipt["storage_root_sha256"],
            "previous_epoch": challenge["previous_epoch"],
            "next_epoch": challenge["next_epoch"],
            "previous_head_sha256": challenge["previous_head_sha256"],
            "next_head_sha256": challenge["next_head_sha256"],
            "reason": challenge["reason"],
            "nonce": nonce,
            "attestation_challenge": challenge,
            "attestation_challenge_signature_b64": (
                challenge_signature_b64 or self.challenge_signature_b64
            ),
            "attestation_receipt": receipt,
            "attestation_receipt_signature_b64": b64(
                sign(self.verifier_private, canonical(receipt))
            ),
        }
        return request

    def invoke(self, request, *, suffix="default", extra=(),
               verifier_public_override=None, private_key_override=None,
               bundle_path_override=None):
        request_path = self.root / f"request-{suffix}.json"
        response_path = self.root / f"response-{suffix}.json"
        response_sig_path = self.root / f"response-{suffix}.sig"
        bundle_path = Path(bundle_path_override) if bundle_path_override else self.root / f"bundle-{suffix}.json"
        bundle_sig_path = self.root / f"bundle-{suffix}.sig"
        request_path.write_bytes(canonical(request))
        verifier_public = verifier_public_override or self.verifier_public
        custodian_private = private_key_override or self.custodian_private
        command = [
            sys.executable, str(DEFAULT_GATE),
            "--anchor", str(self.anchor_path),
            "--anchor-signature", str(self.anchor_sig_path),
            "--public-key", str(self.custodian_public),
            "--private-key", str(custodian_private),
            "--journal", str(self.journal),
            "--lock", str(self.lock),
            "--request", str(request_path),
            "--response", str(response_path),
            "--response-signature", str(response_sig_path),
            "--verifier-pin", str(self.pin_path),
            "--verifier-pin-signature", str(self.pin_sig_path),
            "--attestation-verifier-public-key", str(verifier_public),
            "--bundle", str(bundle_path),
            "--bundle-signature", str(bundle_sig_path),
            *extra,
        ]
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        return result, request_path, response_path, response_sig_path, bundle_path, bundle_sig_path

    def assert_rejected_without_commit(self, result, marker):
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn(marker, result.stdout)
        self.assertFalse(self.journal.exists())

    def test_valid_verifier_receipt_drives_one_custodian_transition(self):
        request = self.make_request()
        result, _, response, response_sig, bundle_path, bundle_sig = self.invoke(request)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ATTESTED_TRANSITION_BUNDLE_CREATED", result.stdout)
        bundle_raw = bundle_path.read_bytes()
        bundle_signature = bundle_sig.read_bytes()
        verify(self.custodian_public, bundle_raw, bundle_signature)
        bundle = json.loads(bundle_raw)
        self.assertEqual(bundle["provenance"], "PINNED_VERIFIER_SIGNED_TPM_ATTESTATION")
        self.assertEqual(bundle["inner_receipt_provenance"], "CALLER_SUPPLIED_UNATTESTED")
        verify(self.verifier_public, canonical(bundle["attestation_receipt"]),
               base64.b64decode(bundle["attestation_receipt_signature_b64"]))
        verify(self.custodian_public, response.read_bytes(), response_sig.read_bytes())
        self.assertEqual(bundle["custodian_receipt"]["request_sha256"],
                         digest(canonical(bundle["transition_request"])))
        self.assertEqual(len(self.journal.read_text().splitlines()), 1)

    def test_default_custodian_entrypoint_rejects_bare_caller_supplied_request(self):
        bare = {
            "device_ek_sha256": self.anchor["device_ek_sha256"],
            "storage_root_sha256": digest(b"caller-claimed-root"),
            "previous_epoch": 7, "next_epoch": 8,
            "previous_head_sha256": self.anchor["head_sha256"],
            "next_head_sha256": self.next_head,
            "reason": "TPM_CLEAR_RECOVERY", "nonce": "1" * 64,
        }
        result, *_ = self.invoke(bare, suffix="bare")
        self.assert_rejected_without_commit(result, "REJECT REQUEST_SCHEMA_INVALID")

    def test_request_cannot_substitute_storage_root_for_signed_tpm_name(self):
        request = self.make_request()
        request["storage_root_sha256"] = digest(b"caller-substituted-root")
        result, *_ = self.invoke(request, suffix="root-substitution")
        self.assert_rejected_without_commit(result, "REQUEST_ATTESTATION_BINDING_MISMATCH:storage_root_sha256")

    def test_request_cannot_substitute_device_ek_identity(self):
        request = self.make_request()
        request["device_ek_sha256"] = digest(b"another EK")
        result, *_ = self.invoke(request, suffix="ek-substitution")
        self.assert_rejected_without_commit(result, "REQUEST_ATTESTATION_BINDING_MISMATCH:device_ek_sha256")

    def test_mismatched_custodian_keypair_is_rejected_before_commit(self):
        wrong_private, _wrong_public = keypair(self.root, "wrong-custodian")
        request = self.make_request()
        result, *_ = self.invoke(
            request, suffix="wrong-custodian-keypair", private_key_override=wrong_private,
        )
        self.assert_rejected_without_commit(result, "REJECT CUSTODIAN_KEYPAIR_MISMATCH")

    def test_tampered_verifier_pin_signature_is_rejected(self):
        original = self.pin_sig_path.read_bytes()
        self.pin_sig_path.write_bytes(b"not-a-valid-signature")
        request = self.make_request()
        result, *_ = self.invoke(request, suffix="tampered-pin-signature")
        self.assert_rejected_without_commit(result, "REJECT VERIFIER_PIN_SIGNATURE_INVALID")
        self.pin_sig_path.write_bytes(original)

    def test_storage_tpm_public_area_must_recompute_the_attested_name(self):
        def mutate(receipt):
            raw = base64.b64decode(receipt["storage_public_area_tpmt_b64"])
            altered = raw[:-1] + bytes([raw[-1] ^ 1])
            receipt["storage_public_area_tpmt_b64"] = b64(altered)
            receipt["evidence_manifest"]["storage_public_area_sha256"] = digest(altered)
            receipt["evidence_bundle_sha256"] = digest(canonical(receipt["evidence_manifest"]))
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="storage-public-area-substitution")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_STORAGE_TPM_NAME_MISMATCH")

    def test_ak_tpm_public_area_must_recompute_the_attested_name(self):
        def mutate(receipt):
            raw = base64.b64decode(receipt["ak_public_area_tpmt_b64"])
            altered = raw[:-1] + bytes([raw[-1] ^ 1])
            receipt["ak_public_area_tpmt_b64"] = b64(altered)
            receipt["evidence_manifest"]["ak_public_area_sha256"] = digest(altered)
            receipt["evidence_bundle_sha256"] = digest(canonical(receipt["evidence_manifest"]))
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="ak-public-area-substitution")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_AK_TPM_NAME_MISMATCH")

    def test_storage_tpm_public_area_requires_fixed_identity_attributes(self):
        def mutate(receipt):
            raw = bytearray(base64.b64decode(receipt["storage_public_area_tpmt_b64"]))
            raw[7] &= ~(1 << 5)
            altered = bytes(raw)
            name = altered[2:4] + hashlib.sha256(altered).digest()
            receipt["storage_public_area_tpmt_b64"] = b64(altered)
            receipt["storage_name_b64"] = b64(name)
            receipt["storage_root_sha256"] = digest(name)
            receipt["evidence_manifest"]["storage_name_sha256"] = digest(name)
            receipt["evidence_manifest"]["storage_public_area_sha256"] = digest(altered)
            receipt["evidence_bundle_sha256"] = digest(canonical(receipt["evidence_manifest"]))
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="storage-attributes")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_STORAGE_ATTRIBUTES_INVALID")

    def test_ak_public_area_rejects_decrypt_usage_even_with_recomputed_name(self):
        def mutate(receipt):
            raw = bytearray(base64.b64decode(receipt["ak_public_area_tpmt_b64"]))
            attributes = int.from_bytes(raw[4:8], "big") | (1 << 17)
            raw[4:8] = attributes.to_bytes(4, "big")
            altered = bytes(raw)
            name = altered[2:4] + hashlib.sha256(altered).digest()
            receipt["ak_public_area_tpmt_b64"] = b64(altered)
            receipt["ak_name_b64"] = b64(name)
            receipt["ak_name_sha256"] = digest(name)
            receipt["evidence_manifest"]["ak_name_sha256"] = digest(name)
            receipt["evidence_manifest"]["ak_public_area_sha256"] = digest(altered)
            receipt["evidence_bundle_sha256"] = digest(canonical(receipt["evidence_manifest"]))
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="ak-forbidden-decrypt")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_AK_ATTRIBUTES_FORBIDDEN")

    def test_ak_public_area_requires_restricted_signing_bits(self):
        def mutate(receipt):
            raw = bytearray(base64.b64decode(receipt["ak_public_area_tpmt_b64"]))
            attributes = int.from_bytes(raw[4:8], "big") & ~(1 << 18)
            raw[4:8] = attributes.to_bytes(4, "big")
            altered = bytes(raw)
            name = altered[2:4] + hashlib.sha256(altered).digest()
            receipt["ak_public_area_tpmt_b64"] = b64(altered)
            receipt["ak_name_b64"] = b64(name)
            receipt["ak_name_sha256"] = digest(name)
            receipt["evidence_manifest"]["ak_name_sha256"] = digest(name)
            receipt["evidence_manifest"]["ak_public_area_sha256"] = digest(altered)
            receipt["evidence_bundle_sha256"] = digest(canonical(receipt["evidence_manifest"]))
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="ak-missing-sign")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_AK_ATTRIBUTES_INVALID")

    def test_storage_primary_rejects_sign_usage_even_with_recomputed_name(self):
        def mutate(receipt):
            raw = bytearray(base64.b64decode(receipt["storage_public_area_tpmt_b64"]))
            attributes = int.from_bytes(raw[4:8], "big") | (1 << 18)
            raw[4:8] = attributes.to_bytes(4, "big")
            altered = bytes(raw)
            name = altered[2:4] + hashlib.sha256(altered).digest()
            receipt["storage_public_area_tpmt_b64"] = b64(altered)
            receipt["storage_name_b64"] = b64(name)
            receipt["storage_root_sha256"] = digest(name)
            receipt["evidence_manifest"]["storage_name_sha256"] = digest(name)
            receipt["evidence_manifest"]["storage_public_area_sha256"] = digest(altered)
            receipt["evidence_bundle_sha256"] = digest(canonical(receipt["evidence_manifest"]))
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="storage-forbidden-sign")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_STORAGE_ATTRIBUTES_FORBIDDEN")

    def test_storage_primary_requires_restricted_decryption_bits(self):
        def mutate(receipt):
            raw = bytearray(base64.b64decode(receipt["storage_public_area_tpmt_b64"]))
            attributes = int.from_bytes(raw[4:8], "big") & ~(1 << 17)
            raw[4:8] = attributes.to_bytes(4, "big")
            altered = bytes(raw)
            name = altered[2:4] + hashlib.sha256(altered).digest()
            receipt["storage_public_area_tpmt_b64"] = b64(altered)
            receipt["storage_name_b64"] = b64(name)
            receipt["storage_root_sha256"] = digest(name)
            receipt["evidence_manifest"]["storage_name_sha256"] = digest(name)
            receipt["evidence_manifest"]["storage_public_area_sha256"] = digest(altered)
            receipt["evidence_bundle_sha256"] = digest(canonical(receipt["evidence_manifest"]))
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="storage-missing-decrypt")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_STORAGE_ATTRIBUTES_INVALID")

    def test_wrong_verifier_key_is_not_pinned(self):
        _private, wrong_public = keypair(self.root, "wrong-verifier")
        request = self.make_request()
        result, *_ = self.invoke(request, suffix="wrong-verifier", verifier_public_override=wrong_public)
        self.assert_rejected_without_commit(result, "REJECT VERIFIER_KEY_NOT_PINNED")

    def test_tampered_attestation_receipt_signature_is_rejected(self):
        request = self.make_request()
        request["attestation_receipt_signature_b64"] = b64(b"not-a-valid-signature")
        result, *_ = self.invoke(request, suffix="bad-receipt-signature")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_RECEIPT_SIGNATURE_INVALID")

    def test_tampered_custodian_challenge_signature_is_rejected(self):
        request = self.make_request()
        request["attestation_challenge_signature_b64"] = b64(b"bad-challenge-signature")
        result, *_ = self.invoke(request, suffix="bad-challenge-signature")
        self.assert_rejected_without_commit(result, "REJECT CHALLENGE_SIGNATURE_INVALID")

    def test_wrong_tpm_name_algorithm_is_rejected(self):
        def mutate(receipt):
            raw = b"\x00\x04" + hashlib.sha256(b"not-sha256-name").digest()
            receipt["storage_name_b64"] = b64(raw)
            receipt["storage_root_sha256"] = digest(raw)
            receipt["evidence_manifest"]["storage_name_sha256"] = digest(raw)
            receipt["evidence_bundle_sha256"] = digest(canonical(receipt["evidence_manifest"]))
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="wrong-name-alg")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_STORAGE_NAME_FORMAT_INVALID")

    def test_storage_root_must_be_derived_from_exact_tpm_name_bytes(self):
        def mutate(receipt):
            receipt["storage_root_sha256"] = digest(b"not-the-name")
            receipt["evidence_manifest"]["storage_name_sha256"] = receipt["storage_root_sha256"]
            receipt["evidence_bundle_sha256"] = digest(canonical(receipt["evidence_manifest"]))
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="bad-name-hash")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_STORAGE_ROOT_DERIVATION_MISMATCH")

    def test_evidence_manifest_must_bind_quote_and_creation_hashes(self):
        def mutate(receipt):
            receipt["evidence_manifest"]["quote_signature_sha256"] = digest(b"substituted signature")
            receipt["evidence_bundle_sha256"] = digest(canonical(receipt["evidence_manifest"]))
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="manifest-mismatch")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_MANIFEST_BINDING_MISMATCH:quote_signature_sha256")

    def test_invalid_ak_spki_der_is_rejected_even_with_matching_claimed_hash(self):
        def mutate(receipt):
            invalid = b"not a DER SubjectPublicKeyInfo"
            receipt["ak_public_spki_der_b64"] = b64(invalid)
            receipt["ak_public_sha256"] = digest(invalid)
            receipt["evidence_manifest"]["ak_public_sha256"] = digest(invalid)
            receipt["evidence_bundle_sha256"] = digest(canonical(receipt["evidence_manifest"]))
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="invalid-ak-spki")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_AK_PUBLIC_DER_INVALID")

    def test_expired_custodian_challenge_is_rejected(self):
        challenge = dict(self.challenge)
        challenge["issued_at"] = int(time.time()) - 400
        challenge["expires_at"] = int(time.time()) - 1
        signature = b64(sign(self.custodian_private, canonical(challenge)))
        request = self.make_request(
            challenge=challenge, challenge_signature_b64=signature,
        )
        result, *_ = self.invoke(request, suffix="expired-challenge")
        self.assert_rejected_without_commit(result, "REJECT CHALLENGE_EXPIRED")

    def test_nv_contents_must_equal_the_attested_storage_root(self):
        def mutate(receipt):
            contents = bytearray(base64.b64decode(receipt["nv_contents_b64"]))
            contents[0] ^= 0x01
            contents = bytes(contents)
            receipt["nv_contents_b64"] = b64(contents)
            receipt["evidence_manifest"]["nv_contents_sha256"] = digest(contents)
            receipt["evidence_bundle_sha256"] = digest(canonical(receipt["evidence_manifest"]))
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="nv-root-content-mismatch")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_NV_CONTENTS_STORAGE_ROOT_MISMATCH")

    def test_nv_index_name_must_be_recomputed_from_exact_public_fields(self):
        def mutate(receipt):
            name = bytearray(base64.b64decode(receipt["nv_index_name_b64"]))
            name[-1] ^= 0x01
            name = bytes(name)
            receipt["nv_index_name_b64"] = b64(name)
            receipt["evidence_manifest"]["nv_index_name_sha256"] = digest(name)
            receipt["evidence_bundle_sha256"] = digest(canonical(receipt["evidence_manifest"]))
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="nv-index-name-mismatch")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_NV_INDEX_NAME_MISMATCH")

    def test_nonempty_nv_auth_policy_is_rejected(self):
        request = self.make_request(receipt=self.make_receipt(
            change=lambda receipt: receipt.update({"nv_auth_policy_b64": b64(b"non-empty")})
        ))
        result, *_ = self.invoke(request, suffix="nv-nonempty-policy")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_NV_AUTH_POLICY_NOT_EMPTY")

    def test_nv_nonce_must_be_derived_from_custodian_challenge(self):
        def mutate(receipt):
            receipt["nv_nonce"] = "f" * 64
            receipt["evidence_manifest"]["nv_nonce_sha256"] = digest(bytes.fromhex(receipt["nv_nonce"]))
            receipt["evidence_bundle_sha256"] = digest(canonical(receipt["evidence_manifest"]))
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="nv-nonce-mismatch")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_NV_NONCE_NOT_CHALLENGE_DERIVED")

    def test_nv_cerification_signer_must_be_the_receipt_ak_qualified_name(self):
        def mutate(receipt):
            other = b"\x00\x0b" + hashlib.sha256(b"different AK qualified name").digest()
            receipt["nv_qualified_signer_b64"] = b64(other)
            receipt["evidence_manifest"]["nv_qualified_signer_sha256"] = digest(other)
            receipt["evidence_bundle_sha256"] = digest(canonical(receipt["evidence_manifest"]))
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="nv-signer-mismatch")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_NV_SIGNER_AK_QUALIFIED_NAME_MISMATCH")

    def test_nv_certification_requires_zero_offset(self):
        request = self.make_request(receipt=self.make_receipt(
            change=lambda receipt: receipt.update({"nv_offset": 1})
        ))
        result, *_ = self.invoke(request, suffix="nv-offset")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_NV_OFFSET_INVALID")

    def test_nv_index_attributes_are_exactly_pinned(self):
        request = self.make_request(receipt=self.make_receipt(
            change=lambda receipt: receipt.update({"nv_attributes": receipt["nv_attributes"] ^ 0x01})
        ))
        result, *_ = self.invoke(request, suffix="nv-attributes")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_NV_ATTRIBUTES_INVALID")

    def test_nv_index_handle_is_exactly_pinned(self):
        request = self.make_request(receipt=self.make_receipt(
            change=lambda receipt: receipt.update({"nv_index_handle": 0x01500021})
        ))
        result, *_ = self.invoke(request, suffix="nv-handle")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_NV_INDEX_HANDLE_INVALID")

    def test_nv_offset_float_is_rejected_as_non_integer(self):
        request = self.make_request(receipt=self.make_receipt(
            change=lambda receipt: receipt.update({"nv_offset": 0.0})
        ))
        result, *_ = self.invoke(request, suffix="nv-offset-float")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_NV_OFFSET_INVALID")

    def test_expired_attestation_receipt_is_rejected(self):
        def mutate(receipt):
            receipt["issued_at"] = int(time.time()) - 400
            receipt["expires_at"] = int(time.time()) - 1
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="expired-receipt")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_RECEIPT_EXPIRED")

    def test_future_attestation_receipt_is_rejected(self):
        def mutate(receipt):
            receipt["issued_at"] = int(time.time()) + 600
            receipt["expires_at"] = int(time.time()) + 700
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="future-receipt")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_RECEIPT_ISSUED_IN_FUTURE")

    def test_receipt_must_bind_the_exact_signed_challenge(self):
        def mutate(receipt):
            receipt["challenge_sha256"] = digest(b"different challenge")
        request = self.make_request(receipt=self.make_receipt(change=mutate))
        result, *_ = self.invoke(request, suffix="challenge-hash-mismatch")
        self.assert_rejected_without_commit(result, "REJECT ATTESTATION_CHALLENGE_HASH_MISMATCH")

    def test_request_nonce_is_derived_from_challenge_and_signed_receipt(self):
        request = self.make_request()
        request["nonce"] = "2" * 64
        result, *_ = self.invoke(request, suffix="derived-nonce-mismatch")
        self.assert_rejected_without_commit(result, "REJECT REQUEST_DERIVED_NONCE_MISMATCH")

    def test_exact_retry_replays_same_custodian_receipt_and_bundle(self):
        request = self.make_request()
        first, _, _, _, bundle1, sig1 = self.invoke(request, suffix="first")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        first_bundle, first_signature = bundle1.read_bytes(), sig1.read_bytes()
        retry, _, _, _, bundle2, sig2 = self.invoke(request, suffix="retry")
        self.assertEqual(retry.returncode, 0, retry.stdout + retry.stderr)
        self.assertIn("IDEMPOTENT_RECEIPT_REPLAY", retry.stdout)
        self.assertEqual(bundle2.read_bytes(), first_bundle)
        self.assertEqual(sig2.read_bytes(), first_signature)
        self.assertEqual(len(self.journal.read_text().splitlines()), 1)

    def test_different_receipt_cannot_reuse_consumed_challenge_transition(self):
        first_request = self.make_request()
        first, *_ = self.invoke(first_request, suffix="first")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)

        def alter_evidence(receipt):
            receipt["evidence_manifest"]["quote_attestation_sha256"] = digest(b"different quote")
            receipt["quote_attestation_sha256"] = receipt["evidence_manifest"]["quote_attestation_sha256"]
            receipt["evidence_bundle_sha256"] = digest(canonical(receipt["evidence_manifest"]))
        second_receipt = self.make_receipt(change=alter_evidence)
        second_request = self.make_request(receipt=second_receipt)
        second, *_ = self.invoke(second_request, suffix="second-proof")
        self.assertEqual(second.returncode, 3, second.stdout + second.stderr)
        self.assertIn("REJECT EPOCH_STALE", second.stdout)
        self.assertEqual(len(self.journal.read_text().splitlines()), 1)

    def test_bundle_output_cannot_alias_journal(self):
        request = self.make_request()
        result, *_ = self.invoke(
            request, suffix="bundle-alias", bundle_path_override=self.journal,
        )
        self.assert_rejected_without_commit(result, "REJECT PATH_ALIAS:journal:bundle")


class ChallengeIssuerTests(unittest.TestCase):
    def test_challenge_is_signed_fresh_and_does_not_mutate_journal(self):
        with tempfile.TemporaryDirectory(prefix="ario-r22-33-challenge-") as directory:
            root = Path(directory)
            private, public = keypair(root, "custodian")
            ek_private, ek_public = keypair(root, "ek")
            anchor = {
                "format": "ARIO-R22.31-ANCHOR-V1",
                "device_ek_sha256": digest(spki_der(ek_public)),
                "storage_root_sha256": digest(b"old-root"),
                "epoch": 12,
                "head_sha256": digest(b"old-head"),
            }
            anchor_path = root / "anchor.json"
            anchor_sig = root / "anchor.sig"
            anchor_path.write_bytes(canonical(anchor))
            anchor_sig.write_bytes(sign(private, canonical(anchor)))
            journal = root / "journal.jsonl"
            lock = root / "lock"
            challenge_path = root / "challenge.json"
            signature_path = root / "challenge.sig"
            next_head = digest(b"next-head")
            result = subprocess.run([
                sys.executable, str(ISSUER),
                "--anchor", str(anchor_path),
                "--anchor-signature", str(anchor_sig),
                "--public-key", str(public),
                "--private-key", str(private),
                "--journal", str(journal),
                "--lock", str(lock),
                "--output", str(challenge_path),
                "--signature", str(signature_path),
                "--next-head-sha256", next_head,
                "--ttl-seconds", "90",
            ], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            challenge = json.loads(challenge_path.read_text())
            verify(public, challenge_path.read_bytes(), signature_path.read_bytes())
            self.assertEqual(challenge["previous_epoch"], 12)
            self.assertEqual(challenge["next_epoch"], 13)
            self.assertEqual(challenge["next_head_sha256"], next_head)
            self.assertGreater(challenge["expires_at"], challenge["issued_at"])
            self.assertFalse(journal.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
