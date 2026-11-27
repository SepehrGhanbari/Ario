"""R10 synthetic durable observation floor — bounded research lab only.

This module can ingest ONLY two pinned R08 test fixtures, previously examined via
Sigsum's reference CLI. The pins are NOT a runtime Sigsum signature validator.
Both SQLite and the separate floor are in the SAME ADMINISTRATIVE trust domain
until a truly separate custodian is deployed. Nothing here authorizes Ario state.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Literal

SCOPE = "ARIO-R08-SIGSUM-SYNTHETIC-v1"  # a LOCAL monitor scope, not the R08 JSON field
KEYHASH = "b5eb8161748009b3bbacfa3f9d3aab40c0585b03a234914956753bda10134743"
# SHA256 of the *exact* public synthetic JSONs/proofs archived at GitHub #280.
FIXTURES = {
    1: ("70d69d3acc5c6969c057c1054e91eea0455b19c08f51e7dd28c28122236d9adc",
        "c4534dd331a1555588070d0a25ab198fb24a973e3d24c38264f0b5a1ced76ab3", 279179, "GENESIS"),
    2: ("91778c13fc733b2bf5388a7fc44550c10c019808d0df7c4100994c3a40eac720",
        "ea63efd7cc7e59deb3b294c9fd9081a3ef45e19d25712a04c9231eaaf50300d2", 279180,
        "70d69d3acc5c6969c057c1054e91eea0455b19c08f51e7dd28c28122236d9adc"),
}
GENESIS = "GENESIS"


class MonitorHold(Exception):
    """Fail closed; no decision/production admission is implied."""


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class PinnedObservation:
    seq: int
    payload_sha256: str
    proof_sha256: str
    leaf_index: int
    signer_keyhash: str = KEYHASH
    source: str = "R08_OFFLINE_VERIFIED_TEST_RECEIPT_PIN"

    def normalized(self) -> dict:
        if type(self.seq) is not int or self.seq not in FIXTURES:
            raise MonitorHold("HOLD_UNKNOWN_SEQUENCE")
        record = FIXTURES[self.seq]
        if (self.payload_sha256, self.proof_sha256, self.leaf_index) != record[:3]:
            raise MonitorHold("HOLD_UNPINNED_OR_INCORRECT_RECEIPT")
        if self.signer_keyhash != KEYHASH or self.source != "R08_OFFLINE_VERIFIED_TEST_RECEIPT_PIN":
            raise MonitorHold("HOLD_WRONG_SIGNER_OR_UNVERIFIED_SOURCE")
        return {
            "scope": SCOPE, "seq": self.seq,
            "payload_sha256": self.payload_sha256,
            "proof_sha256": self.proof_sha256,
            "prev_payload_sha256": record[3],
            "leaf_index": self.leaf_index, "signer_keyhash": self.signer_keyhash,
            "source": self.source,
        }


def fixture(seq: int) -> PinnedObservation:
    if seq not in FIXTURES:
        raise MonitorHold("HOLD_UNKNOWN_SEQUENCE")
    content, receipt, index, _ = FIXTURES[seq]
    return PinnedObservation(seq, content, receipt, index)


def _write_floor(path: Path, data: dict) -> None:
    """Atomic replace, file fsync and best-effort directory fsync.

    Cannot defend against administrator-controlled rollback or disk dishonesty.
    """
    raw = canonical(data) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".r10-floor-", suffix=".tmp", delete=False) as out:
            temporary = Path(out.name)
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
        temporary = None
        if os.name == "posix":
            dirfd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dirfd)
            finally:
                os.close(dirfd)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class DurableFixtureMonitor:
    """Two-process-restart-safe test-only floor; NOT independently operated."""

    def __init__(self, db: Path, floor: Path):
        self.db = Path(db)
        self.floor = Path(floor)

    def initialize_empty_lab(self) -> None:
        """Explicit bootstrap, never called on recovery; requires pristine paths."""
        if self.db.exists() or self.floor.exists():
            raise MonitorHold("HOLD_BOOTSTRAP_ALREADY_EXISTS")
        self.db.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.db, timeout=10)
        try:
            con.execute("PRAGMA journal_mode=DELETE")
            con.execute("PRAGMA synchronous=FULL")
            con.execute("CREATE TABLE observations(seq INTEGER PRIMARY KEY, blob TEXT NOT NULL, row_sha256 TEXT NOT NULL)")
            con.commit()
        finally:
            con.close()
        _write_floor(self.floor, {"scope": SCOPE, "seq": 0, "head": GENESIS})

    def _connection(self) -> sqlite3.Connection:
        if not self.db.exists():
            raise MonitorHold("HOLD_LOCAL_LEDGER_MISSING")
        con = sqlite3.connect(self.db, timeout=10)
        con.execute("PRAGMA synchronous=FULL")
        con.execute("PRAGMA journal_mode=DELETE")
        return con

    def _inspect(self, con: sqlite3.Connection) -> tuple[int, str]:
        if not self.floor.exists():
            raise MonitorHold("HOLD_RETAINED_FLOOR_MISSING")
        try:
            floor = json.loads(self.floor.read_bytes())
            if (type(floor) is not dict or floor.get("scope") != SCOPE
                or type(floor.get("seq")) is not int or not isinstance(floor.get("head"), str)):
                raise ValueError("invalid floor shape")
        except (OSError, ValueError) as exc:
            raise MonitorHold("HOLD_RETAINED_FLOOR_CORRUPT") from exc
        seq, head, previous_payload = 0, GENESIS, GENESIS
        try:
            rows = con.execute("SELECT seq, blob, row_sha256 FROM observations ORDER BY seq").fetchall()
        except sqlite3.Error as exc:
            raise MonitorHold("HOLD_LEDGER_UNREADABLE") from exc
        for number, blob, row_sha256 in rows:
            try:
                record = json.loads(blob)
                expected = fixture(record["seq"]).normalized()
                valid = (type(number) is int and number == seq + 1
                    and record == expected and record["prev_payload_sha256"] == previous_payload
                    and sha(canonical(record)) == row_sha256)
            except (ValueError, KeyError, TypeError, MonitorHold):
                valid = False
            if not valid:
                raise MonitorHold("HOLD_LEDGER_CHAIN_OR_ROW_TAMPER")
            seq, head, previous_payload = number, row_sha256, record["payload_sha256"]
        if floor["seq"] > seq:
            raise MonitorHold("HOLD_LEDGER_ROLLBACK_BEHIND_RETAINED_FLOOR")
        if floor["seq"] < seq:
            raise MonitorHold("HOLD_FLOOR_ROLLBACK_OR_UNCERTAIN_COMMIT")
        if floor["head"] != head:
            raise MonitorHold("HOLD_FORK_OR_MISMATCHED_FLOOR")
        return seq, head

    def status(self) -> dict:
        con = self._connection()
        try:
            seq, head = self._inspect(con)
            return {"state": "CONSISTENT_LOCAL_LAB_ONLY", "seq": seq, "head": head,
                    "independent_custody": False, "trust_activation": False}
        finally:
            con.close()

    def observe(self, observation: PinnedObservation, *, outage: bool = False,
                scan_complete: bool = True, fault: Literal["", "after_insert", "after_floor", "after_commit"] = "") -> str:
        """Persist one known test fixture with an explicit retained floor.

        Two-phase write is fail-closed on interrupted states: SQLite starts an
        immediate transaction; floor is fsynced and replaced *before* DB commit.
        An after-floor crash leaves a detectable HOLD, never silent repair.
        """
        record = observation.normalized()
        if outage:
            raise MonitorHold("HOLD_EXTERNAL_LOG_UNAVAILABLE")
        if not scan_complete:
            raise MonitorHold("HOLD_MONITOR_SCAN_INCOMPLETE")
        con = self._connection()
        try:
            con.execute("BEGIN IMMEDIATE")
            seq, head = self._inspect(con)
            digest = sha(canonical(record))
            if record["seq"] <= seq:
                if record["seq"] == seq and head == digest:
                    con.rollback()
                    return "IDEMPOTENT_ALREADY_RECORDED_NOT_FRESHNESS"
                raise MonitorHold("REJECT_STALE_OR_FORKED_CHECKPOINT")
            if record["seq"] != seq + 1:
                raise MonitorHold("HOLD_UNVERIFIED_SEQUENCE_GAP")
            if record["prev_payload_sha256"] != (GENESIS if seq == 0 else FIXTURES[seq][0]):
                raise MonitorHold("HOLD_PREDECESSOR_CHAIN_MISMATCH")
            con.execute("INSERT INTO observations(seq,blob,row_sha256) VALUES(?,?,?)",
                        (record["seq"], canonical(record).decode("ascii"), digest))
            self._lab_fault(fault, "after_insert")
            _write_floor(self.floor, {"scope": SCOPE, "seq": record["seq"], "head": digest})
            self._lab_fault(fault, "after_floor")
            con.commit()
            self._lab_fault(fault, "after_commit")
            return "RECORDED_SYNTHETIC_ONLY_NOT_TRUTH"
        except MonitorHold:
            con.rollback()
            raise
        finally:
            con.close()

    @staticmethod
    def _lab_fault(requested: str, phase: str) -> None:
        if requested == phase and os.getenv("ARIO_R10_ALLOW_LAB_CRASH") == "YES_TEST_ONLY":
            os._exit(83)

    def gate(self, proposed_seq: int, *, source_available: bool = True,
             scan_complete: bool = True, claim_payload_known: bool = True) -> str:
        """No accept/go verdict: only relative freshness diagnostics."""
        status = self.status()  # Always detect local rollback/corruption first.
        if not source_available:
            return "HOLD_EXTERNAL_LOG_UNAVAILABLE"
        if not scan_complete:
            return "HOLD_MONITOR_SCAN_INCOMPLETE"
        if not claim_payload_known:
            return "HOLD_OPAQUE_CHECKSUM_NO_PLAINTEXT_CHECKPOINT"
        if type(proposed_seq) is not int:
            return "HOLD_INVALID_PROPOSAL"
        if proposed_seq < status["seq"]:
            return "REJECT_STALE_PREFIX"
        if proposed_seq > status["seq"]:
            return "HOLD_UNOBSERVED_EXTENSION"
        return "SAME_CHECKPOINT_NOT_FRESHNESS_PROOF"
