"""Task 1: measure what a TPM policy session alone actually guarantees.

This experiment deliberately tries to obtain more than one signature from one
approved, counter-bound TPM policy.  Every observation is recorded; a success
is preserved as a counterexample, never relabeled as an expected pass.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .common import LabError, ensure_clean_dir, log, log_json, read_bytes, sha256_hex
from .tpm import TpmLab, provision, restore_state, snapshot_state, verify_with_openssl


class BoundaryLab:
    def __init__(self, base: Path) -> None:
        self.base = base
        ensure_clean_dir(base)
        self.tpm = TpmLab(base)
        self.work = self.tpm.work
        self.authority_private = self.work / "policy-authority.pem"
        self.authority_public = self.work / "policy-authority.pub.pem"
        self.authority_ctx = self.work / "authority.ctx"
        self.authority_name = self.work / "authority.name"
        self.info: dict[str, Any] = {}
        self.events: list[dict[str, Any]] = []

    def setup(self) -> None:
        self.info = provision(
            self.tpm,
            authority_private=self.authority_private,
            authority_public=self.authority_public,
        )
        self.tpm.tpm(
            [
                "tpm2_loadexternal",
                "-C",
                "o",
                "-G",
                "rsa",
                "-u",
                str(self.authority_public),
                "-c",
                str(self.authority_ctx),
                "-n",
                str(self.authority_name),
            ]
        )
        if read_bytes(self.authority_name).hex() != self.info["authority_name_hex"]:
            raise LabError("authority name changed during provisioning")
        log_json(
            "BOUNDARY_SETUP",
            key_name=self.info["key_name_hex"],
            authority_name=self.info["authority_name_hex"],
            counter=self.tpm.read_counter(),
        )

    def authorize(self, message: Path, counter: int, tag: str) -> dict[str, Any]:
        cp_hash = self.work / f"{tag}.cphash"
        approved_policy = self.work / f"{tag}.policy"
        signature = self.work / f"{tag}.policy.sig"
        ticket = self.work / f"{tag}.ticket"
        self.tpm.cp_hash(message, cp_hash)
        self.tpm.trial_policy(counter, cp_hash, approved_policy, tag)
        from .common import run

        run(
            [
                "openssl",
                "dgst",
                "-sha256",
                "-sign",
                str(self.authority_private),
                "-out",
                str(signature),
                str(approved_policy),
            ],
            timeout=30,
        )
        self.tpm.tpm(
            [
                "tpm2_verifysignature",
                "-c",
                str(self.authority_ctx),
                "-g",
                "sha256",
                "-m",
                str(approved_policy),
                "-s",
                str(signature),
                "-t",
                str(ticket),
                "-f",
                "rsassa",
            ]
        )
        # tpm2_verifysignature can reload an external object from its context.
        # Preserve policy sessions; release transient objects only (as in R22.29).
        self.tpm.flush_all()
        return {
            "tag": tag,
            "message": str(message),
            "counter": counter,
            "cp_hash": str(cp_hash),
            "approved_policy": str(approved_policy),
            "policy_signature": str(signature),
            "ticket": str(ticket),
        }

    def session(self, auth: dict[str, Any], tag: str) -> Path:
        session = self.work / f"{tag}.session"
        self.tpm.start_policy_session(
            counter=auth["counter"],
            cp_hash=Path(auth["cp_hash"]),
            approved_policy=Path(auth["approved_policy"]),
            authority_name=self.authority_name,
            ticket=Path(auth["ticket"]),
            session=session,
        )
        return session

    def sign(self, auth: dict[str, Any], session: Path, tag: str) -> tuple[bool, str]:
        signature = self.work / f"{tag}.signature"
        try:
            self.tpm.sign_with_session(Path(auth["message"]), session, signature)
        except LabError as exc:
            return False, str(exc)
        finally:
            self.tpm.tpm(["tpm2_flushcontext", str(session)], check=False)
        tpm_ok = self.tpm.verify_with_tpm(Path(auth["message"]), signature)
        ssl_ok = verify_with_openssl(self.authority_public.parent / "signer.pem", Path(auth["message"]), signature)
        if not (tpm_ok and ssl_ok):
            raise LabError("signature produced but independent verification failed; probe inconclusive")
        return True, sha256_hex(read_bytes(signature))

    def record(
        self,
        name: str,
        outcome: str,
        *,
        counterexample: bool,
        detail: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        event = {
            "event": "BOUNDARY_PROBE",
            "name": name,
            "outcome": outcome,
            "counterexample": counterexample,
            "detail": detail,
            **(extra or {}),
        }
        self.events.append(event)
        log_json(**event)

    def run(self) -> dict[str, Any]:
        self.setup()
        message_a = self.work / "message-a.bin"
        message_b = self.work / "message-b.bin"
        message_c = self.work / "message-c.bin"
        message_a.write_bytes(b"Ario commitment A - generation 1\n")
        message_b.write_bytes(b"Ario conflicting commitment B - generation 1\n")
        message_c.write_bytes(b"Ario commitment C - generation 2\n")

        c1 = self.tpm.read_counter()
        auth_a_c1 = self.authorize(message_a, c1, "a-c1")
        auth_b_c1 = self.authorize(message_b, c1, "b-c1")

        # Baseline: exact approved command succeeds and verifies independently.
        session = self.session(auth_a_c1, "baseline")
        ok, detail = self.sign(auth_a_c1, session, "baseline")
        self.record(
            "baseline-exact-command",
            "SIGNED" if ok else "FAILED",
            counterexample=False,
            detail=detail,
        )
        if not ok:
            raise LabError("baseline exact-command signing did not succeed")

        # Probe 1: two pre-authorized sessions for the same command and counter.
        s1 = self.session(auth_a_c1, "two-session-1")
        s2 = self.session(auth_a_c1, "two-session-2")
        ok1, d1 = self.sign(auth_a_c1, s1, "two-session-1")
        ok2, d2 = self.sign(auth_a_c1, s2, "two-session-2")
        self.record(
            "two-preauthorized-sessions-one-command",
            "SIGNED_TWICE" if ok1 and ok2 else "REJECTED_ONE_OR_BOTH",
            counterexample=ok1 and ok2,
            detail=json.dumps({"first": [ok1, d1], "second": [ok2, d2]}, sort_keys=True),
        )

        # Probe 2: conflicting commands authorized at the same counter/generation.
        a = self.session(auth_a_c1, "conflict-a")
        b = self.session(auth_b_c1, "conflict-b")
        oka, da = self.sign(auth_a_c1, a, "conflict-a")
        okb, db = self.sign(auth_b_c1, b, "conflict-b")
        self.record(
            "conflicting-commands-same-counter",
            "BOTH_SIGNED" if oka and okb else "ONE_OR_BOTH_REJECTED",
            counterexample=oka and okb,
            detail=json.dumps({"A": [oka, da], "B": [okb, db]}, sort_keys=True),
        )

        # Probe 3: genuine concurrent signing of the same command.
        c1 = self.tpm.read_counter()
        auth_conc = self.authorize(message_a, c1, "concurrent")
        s3 = self.session(auth_conc, "concurrent-1")
        s4 = self.session(auth_conc, "concurrent-2")
        env = os.environ.copy()
        env.update(self.tpm.env)
        sig3 = self.work / "concurrent-1.signature"
        sig4 = self.work / "concurrent-2.signature"
        commands = [
            [
                "tpm2_sign",
                "-c",
                "0x81000002",
                "-g",
                "sha256",
                "-o",
                str(sig3),
                "-p",
                f"session:{s3}",
                str(message_a),
            ],
            [
                "tpm2_sign",
                "-c",
                "0x81000002",
                "-g",
                "sha256",
                "-o",
                str(sig4),
                "-p",
                f"session:{s4}",
                str(message_a),
            ],
        ]
        processes = [
            subprocess.Popen(cmd, cwd=str(self.work), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for cmd in commands
        ]
        results = [process.communicate(timeout=60) for process in processes]
        codes = [process.returncode for process in processes]
        verified = []
        for sig in (sig3, sig4):
            if sig.exists():
                verified.append(
                    self.tpm.verify_with_tpm(message_a, sig)
                    and verify_with_openssl(self.work / "signer.pem", message_a, sig)
                )
            else:
                verified.append(False)
        if any(code == 0 and not ok for code, ok in zip(codes, verified)):
            raise LabError("concurrent command succeeded but signature verification failed")
        self.record(
            "actual-concurrent-signing",
            "BOTH_SIGNED" if codes == [0, 0] else f"CODES_{codes}",
            counterexample=codes == [0, 0] and all(verified),
            detail=json.dumps(
                {
                    "returncodes": codes,
                    "verified": verified,
                    "stderr": [item[1].decode("utf-8", "replace") for item in results],
                },
                sort_keys=True,
            ),
        )
        for session in (s3, s4):
            self.tpm.tpm(["tpm2_flushcontext", str(session)], check=False)

        # Probe 4: counter advances between policy evaluation and TPM2_Sign.
        c1 = self.tpm.read_counter()
        auth_advance = self.authorize(message_c, c1, "advance")
        s5 = self.session(auth_advance, "advance")
        counter_after = self.tpm.increment_counter()
        ok_adv, d_adv = self.sign(auth_advance, s5, "advance")
        self.record(
            "counter-advance-between-evaluation-and-sign",
            "SIGNED_AFTER_ADVANCE" if ok_adv else "REJECTED_AFTER_ADVANCE",
            counterexample=ok_adv,
            detail=json.dumps(
                {"counter_at_policy": c1, "counter_at_sign": counter_after, "sign": [ok_adv, d_adv]},
                sort_keys=True,
            ),
            extra={"counter_before": c1, "counter_after": counter_after},
        )

        # Probe 5: save a policy context, simulate process failure, advance the
        # counter, restore the context and try to sign.
        c_now = self.tpm.read_counter()
        auth_saved = self.authorize(message_a, c_now, "saved")
        s6 = self.session(auth_saved, "saved")
        blob = self.work / "saved.session.blob"
        loaded = self.work / "saved.session.loaded"
        save_ok = True
        try:
            self.tpm.tpm(["tpm2_contextsave", "-c", str(s6), "-o", str(blob)])
            self.tpm.tpm(["tpm2_flushcontext", str(s6)], check=False)
        except (LabError, FileNotFoundError) as exc:
            save_ok = False
            save_error = str(exc)
        if save_ok:
            new_counter = self.tpm.increment_counter()
            load_ok = True
            try:
                self.tpm.tpm(["tpm2_contextload", "-c", str(loaded), "-o", str(blob)])
            except (LabError, FileNotFoundError) as exc:
                load_ok = False
                load_error = str(exc)
            if load_ok:
                ok_saved, d_saved = self.sign(auth_saved, loaded, "saved")
                self.record(
                    "saved-policy-context-after-counter-advance",
                    "SIGNED_AFTER_CONTEXT_RESTORE" if ok_saved else "REJECTED_AFTER_CONTEXT_RESTORE",
                    counterexample=ok_saved,
                    detail=json.dumps(
                        {
                            "counter_at_policy": c_now,
                            "counter_at_restore": new_counter,
                            "sign": [ok_saved, d_saved],
                        },
                        sort_keys=True,
                    ),
                )
            else:
                self.record(
                    "saved-policy-context-after-counter-advance",
                    "CONTEXT_LOAD_UNSUPPORTED",
                    counterexample=False,
                    detail=load_error,
                )
        else:
            self.record(
                "saved-policy-context-after-counter-advance",
                "CONTEXT_SAVE_UNSUPPORTED",
                counterexample=False,
                detail=save_error,
            )

        # Probe 6: rollback the whole emulator state and replay an old token.
        c_now = self.tpm.read_counter()
        auth_rollback = self.authorize(message_a, c_now, "rollback")
        self.tpm.flush_all()
        snapshot = self.base / "tpm-snapshot-before-increment"
        snapshot_state(self.tpm, snapshot)
        s7 = self.session(auth_rollback, "rollback-first")
        ok_first, d_first = self.sign(auth_rollback, s7, "rollback-first")
        advanced = self.tpm.increment_counter()
        restore_state(self.tpm, snapshot)
        restored = self.tpm.read_counter()
        s8 = self.session(auth_rollback, "rollback-replay")
        ok_replay, d_replay = self.sign(auth_rollback, s8, "rollback-replay")
        self.record(
            "emulator-state-rollback-replay",
            "REPLAY_SIGNED" if ok_replay else "REPLAY_REJECTED",
            counterexample=ok_replay,
            detail=json.dumps(
                {
                    "snapshot_counter": c_now,
                    "counter_after_advance": advanced,
                    "counter_after_restore": restored,
                    "first_sign": [ok_first, d_first],
                    "replay": [ok_replay, d_replay],
                },
                sort_keys=True,
            ),
            extra={"snapshot_counter": c_now, "restored_counter": restored},
        )

        summary = {
            "profile": "ARIO-R22.30-BOUNDARY-v1",
            "research_only": True,
            "counterexamples": [event for event in self.events if event.get("counterexample")],
            "probes": self.events,
        }
        (self.base / "boundary-results.json").write_bytes(
            json.dumps(summary, sort_keys=True, indent=2).encode("utf-8") + b"\n"
        )
        return summary


def main() -> int:
    base = Path(os.environ.get("ARIO2230_BOUNDARY_DIR", "/tmp/ario-r2230-boundary"))
    lab = BoundaryLab(base)
    try:
        summary = lab.run()
    finally:
        lab.tpm.stop()
    log(
        "BOUNDARY_COMPLETE "
        + json.dumps(
            {
                "probes": len(summary["probes"]),
                "counterexamples": [item["name"] for item in summary["counterexamples"]],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
