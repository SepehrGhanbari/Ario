#!/usr/bin/env python3
"""Offline verification of an exported R22.32 public TPM evidence bundle.

This verifies the evidence bytes and signatures independently of the TPM runner.
It does not validate a custodian-signed challenge, establish challenge-before-
evidence ordering, or emit an R22.33 transition receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
R22_32 = HERE.parent / "r22_32_tpm_ek_ak_attestation"
sys.path.insert(0, str(R22_32))
sys.path.insert(0, str(HERE))

import verify_nv_attestation
from attested_custodian import derived_creation_nonce, derived_nv_nonce, derived_quote_nonce

MANIFEST_FORMAT = "ARIO-R22.32-SWTPM-EVIDENCE-MANIFEST-V1"
SUMMARY_FORMAT = "ARIO-R22.32-OFFLINE-VERIFIER-SUMMARY-V1"
EXPECTED_FILES = {
    "ak-name.bin", "ak-public-area.tpmt", "ak-public.pem", "ak-qualified-name.bin",
    "creation-attestation.bin", "creation-attestation.sig", "creation-nonce.txt",
    "custodian-challenge-nonce.txt", "ek-certificate.crt", "ek-lab-root.crt",
    "ek-public.pem", "ek-spki-sha256.txt", "nv-attestation.bin", "nv-attestation.sig",
    "nv-contents.bin", "nv-index.txt", "nv-nonce.txt", "nv-public.yaml",
    "pcr23-after.bin", "pcr23-before.bin", "pcr23-event-digest.txt",
    "quote-attestation.bin", "quote-attestation.sig", "quote-nonce.txt",
    "storage-creation-data.bin", "storage-creation-hash.bin", "storage-name.bin",
    "storage-public-area.tpmt", "storage-qualified-name.bin", "storage-root-commitment.bin",
    "storage-root-sha256.txt",
}


class VerificationError(Exception):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_hex(path: Path, label: str) -> str:
    value = path.read_text(encoding="ascii").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise VerificationError(f"{label}: expected exactly 32 bytes of hex")
    return value


def tpm2b_contents(data: bytes) -> bytes:
    if len(data) >= 2 and int.from_bytes(data[:2], "big") == len(data) - 2:
        return data[2:]
    return data


def run(cmd: list[str]) -> str:
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise VerificationError(f"required executable not found: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stdout or "") + (exc.stderr or "")
        raise VerificationError(f"verification command failed: {detail[-1600:]}") from exc
    return (result.stdout or "") + (result.stderr or "")


def verify_manifest(bundle: Path) -> None:
    try:
        manifest = json.loads((bundle / "evidence-manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError("evidence manifest is missing or malformed") from exc
    if not isinstance(manifest, dict) or set(manifest) != {"format", "files"}:
        raise VerificationError("manifest schema must contain exactly format and files")
    if manifest["format"] != MANIFEST_FORMAT:
        raise VerificationError("unsupported evidence manifest format")
    files = manifest["files"]
    if not isinstance(files, dict) or set(files) != EXPECTED_FILES:
        raise VerificationError("manifest file set does not match the R22.32 evidence contract")
    actual_names = set()
    for item in bundle.iterdir():
        if item.is_symlink() or not item.is_file():
            raise VerificationError(f"bundle contains a non-regular entry: {item.name}")
        if item.name != "evidence-manifest.json":
            actual_names.add(item.name)
    if actual_names != EXPECTED_FILES:
        raise VerificationError("bundle directory contains missing or unexpected files")
    for name, expected in files.items():
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise VerificationError(f"manifest contains an invalid hash for {name}")
        if sha256((bundle / name).read_bytes()) != expected:
            raise VerificationError(f"evidence file hash mismatch: {name}")


def verify_signature(public_key: Path, message: Path, signature: Path, temp: Path, label: str) -> None:
    raw = signature.read_bytes()
    if len(raw) < 6:
        raise VerificationError(f"{label}: truncated TPMT_SIGNATURE")
    if int.from_bytes(raw[:2], "big") != 0x0014:
        raise VerificationError(f"{label}: expected TPM_ALG_RSASSA")
    if int.from_bytes(raw[2:4], "big") != 0x000B:
        raise VerificationError(f"{label}: expected TPM_ALG_SHA256")
    size = int.from_bytes(raw[4:6], "big")
    if size != 256 or len(raw) != size + 6:
        raise VerificationError(f"{label}: expected a complete RSA-2048 signature")
    raw_sig = temp / f"{label}.sig"
    raw_sig.write_bytes(raw[6:])
    run(["openssl", "dgst", "-sha256", "-verify", str(public_key),
         "-signature", str(raw_sig), str(message)])


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def take(self, n: int) -> bytes:
        if n < 0 or self.offset + n > len(self.data):
            raise VerificationError("truncated TPM attestation/public area")
        result = self.data[self.offset:self.offset+n]
        self.offset += n
        return result

    def u16(self) -> int:
        return int.from_bytes(self.take(2), "big")

    def u32(self) -> int:
        return int.from_bytes(self.take(4), "big")

    def u64(self) -> int:
        return int.from_bytes(self.take(8), "big")

    def tpm2b(self) -> bytes:
        return self.take(self.u16())


def quote_pcr_digest(path: Path) -> tuple[list[tuple[int, bytes]], bytes]:
    raw = tpm2b_contents(path.read_bytes())
    reader = Reader(raw)
    if reader.u32() != 0xFF544347 or reader.u16() != 0x8018:
        raise VerificationError("quote has invalid TPM_GENERATED magic or attestation type")
    reader.tpm2b()  # qualifiedSigner
    reader.tpm2b()  # extraData
    reader.take(17)  # TPMS_CLOCK_INFO
    reader.u64()  # firmwareVersion
    selections = []
    for _ in range(reader.u32()):
        alg = reader.u16()
        size = reader.take(1)[0]
        selections.append((alg, reader.take(size)))
    digest = reader.tpm2b()
    if reader.offset != len(raw):
        raise VerificationError("quote contains trailing bytes")
    return selections, digest


def verify_bundle(bundle_path: Path) -> dict:
    if bundle_path.is_symlink():
        raise VerificationError("bundle path must not be a symlink")
    bundle = bundle_path.resolve(strict=True)
    if not bundle.is_dir():
        raise VerificationError("bundle path is not a directory")
    verify_manifest(bundle)

    with tempfile.TemporaryDirectory(prefix="ario-r22-32-offline-") as temp_name:
        temp = Path(temp_name)
        ek_cert = bundle / "ek-certificate.crt"
        ek_ca = bundle / "ek-lab-root.crt"
        ek_public = bundle / "ek-public.pem"
        run(["openssl", "verify", "-CAfile", str(ek_ca), str(ek_cert)])
        cert_pub_pem = temp / "ek-cert-public.pem"
        cert_pub_der = temp / "ek-cert-public.der"
        ek_pub_der = temp / "ek-public.der"
        cert_pub_pem.write_text(
            run(["openssl", "x509", "-in", str(ek_cert), "-pubkey", "-noout"]),
            encoding="ascii",
        )
        run(["openssl", "pkey", "-pubin", "-in", str(cert_pub_pem),
             "-outform", "DER", "-out", str(cert_pub_der)])
        run(["openssl", "pkey", "-pubin", "-in", str(ek_public),
             "-outform", "DER", "-out", str(ek_pub_der)])
        if cert_pub_der.read_bytes() != ek_pub_der.read_bytes():
            raise VerificationError("EK certificate and exported EK public key do not match")
        ek_spki_sha256 = sha256(ek_pub_der.read_bytes())
        if read_hex(bundle / "ek-spki-sha256.txt", "EK SPKI fingerprint") != ek_spki_sha256:
            raise VerificationError("EK SPKI fingerprint mismatch")

        ak_public = bundle / "ak-public.pem"
        ak_der = temp / "ak-public.der"
        run(["openssl", "pkey", "-pubin", "-in", str(ak_public),
             "-outform", "DER", "-out", str(ak_der)])
        ak_text = run(["openssl", "pkey", "-pubin", "-in", str(ak_public), "-text", "-noout"])
        if "Public-Key: (2048 bit)" not in ak_text:
            raise VerificationError("AK public key is not RSA-2048")

        run([sys.executable, str(R22_32 / "verify_tpm_public_name.py"),
             "--public-tpmt", str(bundle / "ak-public-area.tpmt"),
             "--name", str(bundle / "ak-name.bin"), "--require-ak"])
        run([sys.executable, str(R22_32 / "verify_tpm_public_name.py"),
             "--public-tpmt", str(bundle / "storage-public-area.tpmt"),
             "--name", str(bundle / "storage-name.bin"), "--require-storage-primary"])

        ak_qn = (bundle / "ak-qualified-name.bin").read_bytes()
        if len(ak_qn) != 34 or ak_qn[:2] != b"\x00\x0b":
            raise VerificationError("AK Qualified Name is not a SHA-256 TPM Name")
        storage_name = (bundle / "storage-name.bin").read_bytes()
        storage_root = sha256(storage_name)
        if (bundle / "storage-root-commitment.bin").read_bytes() != bytes.fromhex(storage_root):
            raise VerificationError("storage-root commitment is not SHA256(storage Name)")
        if read_hex(bundle / "storage-root-sha256.txt", "storage root") != storage_root:
            raise VerificationError("storage-root text fingerprint mismatch")

        creation_data = (bundle / "storage-creation-data.bin").read_bytes()
        creation_hash = tpm2b_contents((bundle / "storage-creation-hash.bin").read_bytes())
        if creation_hash != hashlib.sha256(creation_data).digest():
            raise VerificationError("CertifyCreation creationHash is not SHA256(creationData)")

        challenge_nonce = read_hex(bundle / "custodian-challenge-nonce.txt", "challenge nonce")
        creation_nonce = read_hex(bundle / "creation-nonce.txt", "creation nonce")
        quote_nonce = read_hex(bundle / "quote-nonce.txt", "quote nonce")
        nv_nonce = read_hex(bundle / "nv-nonce.txt", "NV nonce")
        if creation_nonce != derived_creation_nonce(challenge_nonce):
            raise VerificationError("CertifyCreation nonce is not derived from challenge nonce")
        if quote_nonce != derived_quote_nonce(challenge_nonce):
            raise VerificationError("PCR Quote nonce is not derived from challenge nonce")
        if nv_nonce != derived_nv_nonce(challenge_nonce):
            raise VerificationError("NV_Certify nonce is not derived from challenge nonce")

        run([sys.executable, str(R22_32 / "verify_attestation.py"),
             "--mode", "creation", "--attest", str(bundle / "creation-attestation.bin"),
             "--nonce", creation_nonce, "--ak-qualified-name", str(bundle / "ak-qualified-name.bin"),
             "--object-name", str(bundle / "storage-name.bin"),
             "--creation-hash", str(bundle / "storage-creation-hash.bin")])
        run([sys.executable, str(R22_32 / "verify_attestation.py"),
             "--mode", "quote", "--attest", str(bundle / "quote-attestation.bin"),
             "--nonce", quote_nonce, "--ak-qualified-name", str(bundle / "ak-qualified-name.bin")])
        run([sys.executable, str(R22_32 / "verify_nv_attestation.py"),
             "--attest", str(bundle / "nv-attestation.bin"), "--nonce", nv_nonce,
             "--ak-qualified-name", str(bundle / "ak-qualified-name.bin"),
             "--nv-public-yaml", str(bundle / "nv-public.yaml"),
             "--nv-index", (bundle / "nv-index.txt").read_text(encoding="ascii").strip(),
             "--expected-contents", str(bundle / "storage-root-commitment.bin")])

        verify_signature(ak_public, bundle / "creation-attestation.bin",
                         bundle / "creation-attestation.sig", temp, "creation")
        verify_signature(ak_public, bundle / "quote-attestation.bin",
                         bundle / "quote-attestation.sig", temp, "quote")
        verify_signature(ak_public, bundle / "nv-attestation.bin",
                         bundle / "nv-attestation.sig", temp, "nv")

        if (bundle / "nv-contents.bin").read_bytes() != (bundle / "storage-root-commitment.bin").read_bytes():
            raise VerificationError("NV readback does not equal storage-root commitment")
        nv_name, nv_attributes, nv_size = verify_nv_attestation.parse_nv_public(
            str(bundle / "nv-public.yaml"),
            (bundle / "nv-index.txt").read_text(encoding="ascii").strip(),
        )
        if nv_attributes != 0x20060006 or nv_size != 32:
            raise VerificationError("NV public area does not match exact R22.32 test profile")

        pcr_before = (bundle / "pcr23-before.bin").read_bytes()
        pcr_after = (bundle / "pcr23-after.bin").read_bytes()
        event_hex = read_hex(bundle / "pcr23-event-digest.txt", "PCR event digest")
        event_digest = bytes.fromhex(event_hex)
        if len(pcr_before) != 32 or len(pcr_after) != 32 or pcr_before != bytes(32):
            raise VerificationError("PCR 23 baseline/values do not match fresh SHA-256 PCR profile")
        if hashlib.sha256(pcr_before + event_digest).digest() != pcr_after:
            raise VerificationError("PCR 23 event extension does not match before/after values")
        selections, quoted_digest = quote_pcr_digest(bundle / "quote-attestation.bin")
        if selections != [(0x000B, b"\x00\x00\x80")]:
            raise VerificationError("quote does not select exactly SHA-256 PCR 23")
        if quoted_digest != hashlib.sha256(pcr_after).digest():
            raise VerificationError("quote PCR digest does not match exported PCR 23 value")

        return {
            "format": SUMMARY_FORMAT,
            "status": "VERIFIED",
            "evidence_source": "SWTPM",
            "checks": {
                "manifest_hashes_and_file_set": "PASS",
                "ek_certificate_chain": "PASS_LAB_CA_ONLY",
                "ek_certificate_public_key_binding": "PASS",
                "ak_public_name_and_profile": "PASS_RSA_2048_RSASSA_SHA256",
                "storage_public_name_and_profile": "PASS_ECC_NIST_P256",
                "storage_root_and_creation_hash": "PASS",
                "challenge_nonce_domain_separation": "PASS",
                "certify_creation_signature": "PASS_RSASSA_SHA256",
                "quote_signature": "PASS_RSASSA_SHA256",
                "nv_certify_signature_and_fields": "PASS_RSASSA_SHA256",
                "nv_contents_to_storage_root": "PASS",
                "pcr_extension_and_quote_digest": "PASS",
            },
            "derived": {
                "device_ek_sha256": ek_spki_sha256,
                "storage_root_sha256": storage_root,
                "ak_public_spki_sha256": sha256(ak_der.read_bytes()),
                "ak_name_sha256": sha256((bundle / "ak-name.bin").read_bytes()),
                "nv_index_name_b64": __import__("base64").b64encode(nv_name).decode("ascii"),
                "challenge_nonce": challenge_nonce,
            },
            "custodian_challenge_signature": "NOT_PROVIDED",
            "challenge_issue_order": "NOT_ESTABLISHED",
            "transition_receipt": "NOT_EMITTED",
            "limitations": [
                "software TPM evidence only",
                "laboratory EK CA only; no OEM/manufacturer trust chain",
                "nonce derivation checked, but no custodian-signed challenge was supplied",
                "this verifier does not establish that the challenge was issued before evidence generation",
                "no independent verifier-key custody or external rollback floor",
            ],
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-dir", required=True)
    parser.add_argument("--output", help="write JSON summary outside the evidence bundle")
    args = parser.parse_args()
    try:
        summary = verify_bundle(Path(args.bundle_dir))
        rendered = json.dumps(summary, sort_keys=True, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return 0
    except (OSError, ValueError, VerificationError) as exc:
        print(f"REJECT {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
