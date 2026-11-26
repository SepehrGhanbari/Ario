from __future__ import annotations

import hashlib
import importlib.util
import os
import struct
import subprocess
import sys
from pathlib import Path

import pytest

IMPLEMENTATION = Path(__file__).resolve().parents[1]
SCRIPT = IMPLEMENTATION / "research" / "r22_32_tpm_ek_ak_attestation" / "verify_nv_attestation.py"
RUNNER = IMPLEMENTATION / "research" / "r22_32_tpm_ek_ak_attestation" / "run_swtpm_attestation.sh"
SPEC = importlib.util.spec_from_file_location("r22_32_verify_nv_attestation", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)

NV_INDEX = 0x01500020
NV_ATTRIBUTES = (
    VERIFIER.TPMA_NV_OWNERWRITE
    | VERIFIER.TPMA_NV_AUTHWRITE
    | VERIFIER.TPMA_NV_OWNERREAD
    | VERIFIER.TPMA_NV_AUTHREAD
    | VERIFIER.TPMA_NV_WRITTEN
)
NONCE = bytes.fromhex("11" * 32)
AK_NAME = bytes.fromhex("22" * 34)
ROOT_COMMITMENT = hashlib.sha256(b"synthetic TPM storage-root claim").digest()


def tpm2b(value: bytes) -> bytes:
    return struct.pack(">H", len(value)) + value


def public_yaml(attributes: int = NV_ATTRIBUTES) -> str:
    return (
        "0x1500020:\n"
        "  hash algorithm:\n"
        "    friendly: sha256\n"
        "    value: 0xB\n"
        "  attributes:\n"
        "    friendly: ownerread|ownerwrite|authread|authwrite|written\n"
        f"    value: 0x{attributes:x}\n"
        "  size: 32\n"
        "  authorization policy:\n"
    )


def make_attestation(
    *,
    nv_name: bytes,
    signer: bytes = AK_NAME,
    nonce: bytes = NONCE,
    contents: bytes = ROOT_COMMITMENT,
    offset: int = 0,
    trailing: bytes = b"",
) -> bytes:
    body = (
        struct.pack(">IH", VERIFIER.TPM_GENERATED, VERIFIER.TPM_ST_ATTEST_NV)
        + tpm2b(signer)
        + tpm2b(nonce)
        + bytes(17)
        + bytes(8)
        + tpm2b(nv_name)
        + struct.pack(">H", offset)
        + tpm2b(contents)
        + trailing
    )
    return tpm2b(body)


def write_fixture(tmp_path: Path, *, attributes: int = NV_ATTRIBUTES):
    public_path = tmp_path / "nv-public.yaml"
    public_path.write_text(public_yaml(attributes), encoding="utf-8")
    nv_name, _, _ = VERIFIER.parse_nv_public(str(public_path), hex(NV_INDEX))
    attest_path = tmp_path / "attest.bin"
    attest_path.write_bytes(make_attestation(nv_name=nv_name))
    ak_path = tmp_path / "ak-qualified-name.bin"
    ak_path.write_bytes(tpm2b(AK_NAME))
    expected_path = tmp_path / "expected.bin"
    expected_path.write_bytes(ROOT_COMMITMENT)
    return public_path, nv_name, attest_path, ak_path, expected_path


def run_cli(tmp_path: Path, *, nonce: str = NONCE.hex(), signer_path: Path | None = None,
            index: str = hex(NV_INDEX), expected_path: Path | None = None,
            offset: int = 0, trailing: bytes = b"") -> subprocess.CompletedProcess[str]:
    public_path, nv_name, attest_path, ak_path, default_expected = write_fixture(tmp_path)
    if signer_path is not None:
        ak_path = signer_path
    if expected_path is not None:
        default_expected = expected_path
    if offset or trailing:
        attest_path.write_bytes(
            make_attestation(nv_name=nv_name, nonce=NONCE, offset=offset, trailing=trailing)
        )
    return subprocess.run(
        [
            sys.executable, str(SCRIPT),
            "--attest", str(attest_path),
            "--nonce", nonce,
            "--ak-qualified-name", str(ak_path),
            "--nv-public-yaml", str(public_path),
            "--nv-index", index,
            "--expected-contents", str(default_expected),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_nv_public_name_is_recomputed_from_written_public_area(tmp_path: Path) -> None:
    public_path, nv_name, _, _, _ = write_fixture(tmp_path)
    parsed_name, attributes, size = VERIFIER.parse_nv_public(str(public_path), hex(NV_INDEX))
    assert parsed_name == nv_name
    assert len(parsed_name) == 34
    assert attributes == NV_ATTRIBUTES
    assert size == 32


def test_nv_public_rejects_unwritten_index(tmp_path: Path) -> None:
    public_path = tmp_path / "nv-public.yaml"
    public_path.write_text(public_yaml(NV_ATTRIBUTES & ~VERIFIER.TPMA_NV_WRITTEN), encoding="utf-8")
    with pytest.raises(ValueError, match="required read/write/written attributes"):
        VERIFIER.parse_nv_public(str(public_path), hex(NV_INDEX))


def test_nv_public_rejects_unlisted_handle(tmp_path: Path) -> None:
    public_path = tmp_path / "nv-public.yaml"
    public_path.write_text(public_yaml(), encoding="utf-8")
    with pytest.raises(ValueError, match="absent"):
        VERIFIER.parse_nv_public(str(public_path), "0x01500021")


def test_cli_accepts_exact_nv_attestation_fields(tmp_path: Path) -> None:
    result = run_cli(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS TPM2_NV_Certify fields" in result.stdout


def test_cli_rejects_wrong_challenge(tmp_path: Path) -> None:
    result = run_cli(tmp_path, nonce="33" * 32)
    assert result.returncode == 3
    assert "qualifyingData" in result.stdout


def test_cli_rejects_wrong_contents(tmp_path: Path) -> None:
    wrong = tmp_path / "wrong-root.bin"
    wrong.write_bytes(hashlib.sha256(b"different root").digest())
    result = run_cli(tmp_path, expected_path=wrong)
    assert result.returncode == 3
    assert "contents do not match" in result.stdout


def test_cli_rejects_wrong_signer(tmp_path: Path) -> None:
    wrong_signer = tmp_path / "wrong-ak.bin"
    wrong_signer.write_bytes(tpm2b(bytes.fromhex("44" * 34)))
    result = run_cli(tmp_path, signer_path=wrong_signer)
    assert result.returncode == 3
    assert "Qualified Name" in result.stdout


def test_cli_rejects_nonzero_offset(tmp_path: Path) -> None:
    result = run_cli(tmp_path, offset=1)
    assert result.returncode == 3
    assert "offset" in result.stdout


def test_cli_rejects_trailing_attestation_bytes(tmp_path: Path) -> None:
    result = run_cli(tmp_path, trailing=b"extra")
    assert result.returncode == 3
    assert "trailing data" in result.stdout


def test_runner_negative_fixture_exists_before_use() -> None:
    runner = RUNNER.read_text(encoding="utf-8")
    created = runner.index('openssl rand -out "$ALT_ROOT_COMMITMENT" 32')
    used = runner.index('--expected-contents "$TMP/alternate-root.bin"')
    assert created < used
    assert "expect_reject" in runner


def test_runner_has_valid_bash_syntax() -> None:
    if os.name == "nt":
        pytest.skip("Bash syntax check is executed on Linux only")
    result = subprocess.run(["bash", "-n", str(RUNNER)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
