"""Thin, explicit wrappers around disposable swtpm/tpm2-tools operations."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from .common import LabError, atomic_write, read_bytes, run, run_ok, sha256_hex


class TpmLab:
    def __init__(self, base: Path, *, nv_index: str = "0x01500030") -> None:
        self.base = base
        self.state = base / "tpm-state"
        self.socket = base / "tpm.sock"
        self.ctrl = base / "tpm.sock.ctrl"
        self.log = base / "swtpm.log"
        self.work = base / "tpm-work"
        self.nv_index = nv_index
        self.process: subprocess.Popen[bytes] | None = None
        self.state.mkdir(parents=True, exist_ok=True)
        os.chmod(self.state, 0o700)
        self.work.mkdir(parents=True, exist_ok=True)
        os.chmod(self.work, 0o700)

    @property
    def env(self) -> dict[str, str]:
        return {"TPM2TOOLS_TCTI": f"swtpm:path={self.socket}"}

    def start(self) -> None:
        if self.process is not None and self.process.poll() is None:
            return
        log_handle = self.log.open("ab")
        self.process = subprocess.Popen(
            [
                "swtpm",
                "socket",
                "--tpm2",
                "--tpmstate",
                f"dir={self.state}",
                "--server",
                f"type=unixio,path={self.socket}",
                "--ctrl",
                f"type=unixio,path={self.ctrl}",
                "--flags",
                "not-need-init,startup-clear",
            ],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
        )
        log_handle.close()
        deadline = time.monotonic() + 20
        last_error = "socket not ready"
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                last_error = f"swtpm exited with {self.process.returncode}"
                break
            if self.socket.exists() and self.ctrl.exists():
                try:
                    run(["tpm2_getrandom", "8"], env=self.env, timeout=3)
                    os.chmod(self.socket, 0o660)
                    return
                except (LabError, subprocess.TimeoutExpired) as exc:
                    last_error = str(exc)
            time.sleep(0.1)
        diagnostic = self.log.read_text(errors="replace")[-4000:]
        self.stop()
        raise LabError(f"swtpm readiness failed: {last_error}\n{diagnostic}")

    def stop(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
        self.process = None
        for path in (self.socket, self.ctrl):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def restart(self) -> None:
        self.stop()
        self.start()

    def tpm(self, argv: list[str], *, timeout: int = 60, check: bool = True, cwd: Path | None = None):
        return run(argv, cwd=cwd or self.work, env=self.env, timeout=timeout, check=check)

    def tpm_ok(self, argv: list[str], *, timeout: int = 60) -> bool:
        return run_ok(argv, cwd=self.work, env=self.env, timeout=timeout)

    def read_counter(self) -> int:
        out = self.work / "counter-read.bin"
        self.tpm(["tpm2_nvread", "-C", "o", "-s", "8", "-o", str(out), self.nv_index])
        return int.from_bytes(read_bytes(out), "big")

    def write_counter_file(self, path: Path, value: int) -> None:
        atomic_write(path, value.to_bytes(8, "big"), mode=0o600)

    def increment_counter(self) -> int:
        self.tpm(["tpm2_nvincrement", "-C", "o", self.nv_index])
        return self.read_counter()

    def key_name(self) -> bytes:
        out = self.work / "signer.name"
        self.tpm(["tpm2_readpublic", "-c", "0x81000002", "-n", str(out)])
        return read_bytes(out)

    def authority_name(self, public_pem: Path) -> bytes:
        out = self.work / "authority.name"
        ctx = self.work / "authority-probe.ctx"
        self.tpm(
            [
                "tpm2_loadexternal",
                "-C",
                "o",
                "-G",
                "rsa",
                "-u",
                str(public_pem),
                "-c",
                str(ctx),
                "-n",
                str(out),
            ]
        )
        self.tpm(["tpm2_flushcontext", str(ctx)], check=False)
        return read_bytes(out)

    def cp_hash(self, message: Path, out: Path) -> bytes:
        self.tpm(
            [
                "tpm2_sign",
                "--cphash",
                str(out),
                "-c",
                "0x81000002",
                "-g",
                "sha256",
                str(message),
            ]
        )
        raw = read_bytes(out)
        if len(raw) != 32:
            raise LabError(f"unexpected cpHash length {len(raw)}")
        return raw

    def trial_policy(self, counter: int, cp_hash: Path, out_policy: Path, tag: str) -> bytes:
        counter_file = self.work / f"{tag}.counter.bin"
        self.write_counter_file(counter_file, counter)
        ctx = self.work / f"{tag}.trial.ctx"
        self.tpm(["tpm2_startauthsession", "-S", str(ctx)])
        try:
            self.tpm(["tpm2_policycommandcode", "-S", str(ctx), "TPM2_CC_Sign"])
            self.tpm(
                ["tpm2_policynv", "-S", str(ctx), "-C", "o", self.nv_index, "eq", "-i", str(counter_file)]
            )
            self.tpm(
                ["tpm2_policycphash", "-S", str(ctx), "-L", str(out_policy), "--cphash", str(cp_hash)]
            )
        finally:
            self.tpm(["tpm2_flushcontext", str(ctx)], check=False)
        raw = read_bytes(out_policy)
        if len(raw) != 32:
            raise LabError("approved policy digest is not 32 bytes")
        return raw

    def start_policy_session(
        self,
        *,
        counter: int,
        cp_hash: Path,
        approved_policy: Path,
        authority_name: Path,
        ticket: Path,
        session: Path,
    ) -> None:
        counter_file = session.with_suffix(".counter.bin")
        self.write_counter_file(counter_file, counter)
        self.tpm(["tpm2_startauthsession", "--policy-session", "-S", str(session)])
        self.tpm(["tpm2_policycommandcode", "-S", str(session), "TPM2_CC_Sign"])
        self.tpm(
            ["tpm2_policynv", "-S", str(session), "-C", "o", self.nv_index, "eq", "-i", str(counter_file)]
        )
        self.tpm(["tpm2_policycphash", "-S", str(session), "--cphash", str(cp_hash)])
        self.tpm(
            [
                "tpm2_policyauthorize",
                "-S",
                str(session),
                "-i",
                str(approved_policy),
                "-n",
                str(authority_name),
                "-t",
                str(ticket),
            ]
        )

    def sign_with_session(self, message: Path, session: Path, signature: Path) -> None:
        self.tpm(
            [
                "tpm2_sign",
                "-c",
                "0x81000002",
                "-g",
                "sha256",
                "-o",
                str(signature),
                "-p",
                f"session:{session}",
                str(message),
            ]
        )

    def verify_with_tpm(self, message: Path, signature: Path) -> bool:
        return self.tpm_ok(
            [
                "tpm2_verifysignature",
                "-c",
                "0x81000002",
                "-g",
                "sha256",
                "-m",
                str(message),
                "-s",
                str(signature),
            ]
        )

    def flush_all(self) -> None:
        self.tpm(["tpm2_flushcontext", "-t"], check=False)


def verify_with_openssl(public_pem: Path, message: Path, signature: Path) -> bool:
    return run_ok(
        [
            "openssl",
            "dgst",
            "-sha256",
            "-verify",
            str(public_pem),
            "-signature",
            str(signature),
            str(message),
        ],
        timeout=30,
    )


def provision(
    tpm: TpmLab,
    *,
    authority_private: Path,
    authority_public: Path,
    run_as: tuple[int, int, list[int]] | None = None,
) -> dict[str, Any]:
    """Create a disposable TPM key, policy authority key and NV counter."""
    if run_as is None:
        run(
            [
                "openssl",
                "genpkey",
                "-algorithm",
                "RSA",
                "-pkeyopt",
                "rsa_keygen_bits:2048",
                "-out",
                str(authority_private),
            ],
            timeout=120,
        )
        run(
            [
                "openssl",
                "pkey",
                "-in",
                str(authority_private),
                "-pubout",
                "-out",
                str(authority_public),
            ],
            timeout=30,
        )
        os.chmod(authority_private, 0o600)
        os.chmod(authority_public, 0o644)
    else:
        uid, gid, groups = run_as
        from .common import setpriv

        setpriv(
            uid,
            gid,
            groups,
            [
                "openssl",
                "genpkey",
                "-algorithm",
                "RSA",
                "-pkeyopt",
                "rsa_keygen_bits:2048",
                "-out",
                str(authority_private),
            ],
            timeout=120,
        )
        setpriv(
            uid,
            gid,
            groups,
            [
                "openssl",
                "pkey",
                "-in",
                str(authority_private),
                "-pubout",
                "-out",
                str(authority_public),
            ],
            timeout=30,
        )
        os.chmod(authority_public, 0o644)

    tpm.start()
    tpm.tpm(["tpm2_createprimary", "-C", "o", "-G", "ecc", "-g", "sha256", "-c", "primary.ctx"])
    tpm.tpm(["tpm2_evictcontrol", "-C", "o", "-c", "primary.ctx", "0x81000001"])
    tpm.tpm(["tpm2_flushcontext", "-t"], check=False)

    authority_ctx = tpm.work / "authority.ctx"
    authority_name_file = tpm.work / "authority.name"
    tpm.tpm(
        [
            "tpm2_loadexternal",
            "-C",
            "o",
            "-G",
            "rsa",
            "-u",
            str(authority_public),
            "-c",
            str(authority_ctx),
            "-n",
            str(authority_name_file),
        ]
    )
    trial = tpm.work / "key-trial.ctx"
    key_policy = tpm.work / "key-auth.policy"
    tpm.tpm(["tpm2_startauthsession", "-S", str(trial)])
    try:
        tpm.tpm(
            [
                "tpm2_policyauthorize",
                "-S",
                str(trial),
                "-n",
                str(authority_name_file),
                "-L",
                str(key_policy),
            ]
        )
    finally:
        tpm.tpm(["tpm2_flushcontext", str(trial)], check=False)

    tpm.tpm(
        [
            "tpm2_create",
            "-C",
            "0x81000001",
            "-G",
            "ecc",
            "-g",
            "sha256",
            "-L",
            str(key_policy),
            "-a",
            "fixedtpm|fixedparent|sensitivedataorigin|sign|noda",
            "-u",
            "signer.public",
            "-r",
            "signer.private",
        ]
    )
    tpm.tpm(["tpm2_load", "-C", "0x81000001", "-u", "signer.public", "-r", "signer.private", "-c", "signer.ctx"])
    tpm.tpm(["tpm2_evictcontrol", "-C", "o", "-c", "signer.ctx", "0x81000002"])
    tpm.tpm(["tpm2_flushcontext", "-t"], check=False)

    signer_pem = tpm.work / "signer.pem"
    signer_name = tpm.work / "signer.name"
    tpm.tpm(["tpm2_readpublic", "-c", "0x81000002", "-f", "pem", "-o", str(signer_pem)])
    tpm.tpm(["tpm2_readpublic", "-c", "0x81000002", "-n", str(signer_name)])

    tpm.tpm(
        [
            "tpm2_nvdefine",
            "-C",
            "o",
            "-a",
            "nt=counter|ownerread|ownerwrite",
            tpm.nv_index,
        ]
    )
    tpm.tpm(["tpm2_nvincrement", "-C", "o", tpm.nv_index])
    counter = tpm.read_counter()
    if counter != 1:
        raise LabError(f"unexpected initial counter {counter}")

    return {
        "nv_index": tpm.nv_index,
        "key_handle": "0x81000002",
        "key_name_hex": read_bytes(signer_name).hex(),
        "signer_public_pem": str(signer_pem),
        "authority_name_hex": read_bytes(authority_name_file).hex(),
        "authority_public_pem": str(authority_public),
        "authority_private_pem": str(authority_private),
        "initial_counter": counter,
    }


def snapshot_state(tpm: TpmLab, destination: Path) -> None:
    tpm.stop()
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(tpm.state, destination)
    tpm.start()


def restore_state(tpm: TpmLab, source: Path) -> None:
    tpm.stop()
    if tpm.state.exists():
        shutil.rmtree(tpm.state)
    shutil.copytree(source, tpm.state)
    tpm.start()


def signature_digest(path: Path) -> str:
    return sha256_hex(read_bytes(path))
