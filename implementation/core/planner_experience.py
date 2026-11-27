"""Opt-in local Planner experience adapter. Reports are not attestations."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import uuid

from core.ledger_memory_bridge import EpistemicLedgerBridge, MAX_LEDGER_BYTES
from core.memory_consolidation import ConsolidationEngine, NodeEpistemicStatus
from core.source_monitoring import SourceMonitoringGuard
from core.working_memory import WorkingMemoryBuffer
from research.w38_receipt_fd_guard import read_bounded_regular

PAIRS = (
    ("implementation/ario_planner.py", "implementation/tests/test_planner_runtime.py"),
    ("implementation/ario_workflow.py", "implementation/tests/test_workflow_runtime.py"),
)
MAX_RECORD = 256 * 1024
MAX_RECORDS = 1000
SCHEMA = "ARIO-LOCAL-PLANNER-EXPERIENCE-1"


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate experience field")
        out[key] = value
    return out


def native_events(raw, before, end, workflow_id, status):
    if (type(before) is not int or type(end) is not int or
            not 0 <= before < end <= len(raw)):
        raise ValueError("invalid native ledger range")
    if (before and raw[before-1:before] != b"\n") or raw[end-1:end] != b"\n":
        raise ValueError("incomplete native ledger range")
    events = [json.loads(line, object_pairs_hook=unique)
              for line in raw[before:end].splitlines() if line.strip()]
    if (not events or events[-1].get("event") != "WORKFLOW_FINISHED" or
            events[-1].get("workflow_id") != workflow_id or
            events[-1].get("status") != status):
        raise ValueError("native workflow finish is not bound to retained outcome")
    stages = [e for e in events if e.get("event") == "WORKFLOW_STAGE_OBSERVED"
              and e.get("workflow_id") == workflow_id]
    return stages


def fingerprint(root, paths):
    """Bounded observable condition, not a proof of all environmental conditions."""
    if tuple(sorted(paths)) not in tuple(tuple(sorted(p)) for p in PAIRS):
        return None
    entries = []
    for name in sorted(paths):
        path = root / name
        try:
            if path.resolve() != path.absolute():
                return None
            before = path.stat()
            raw = read_bounded_regular(path, 2 * 1024 * 1024)
            after = path.stat()
            if (before.st_size, before.st_mtime_ns, before.st_mode) != (
                    after.st_size, after.st_mtime_ns, after.st_mode):
                return None
            entries.append([name, digest(raw), stat.S_IMODE(after.st_mode)])
        except (OSError, ValueError):
            return None
    return digest(canonical(entries))


class Experience:
    """Immutable per-event files, local single-writer directory, recorded-only recall.

    The native execution ledger remains the observation source. The additional
    files bind decisions and revisions to its retained prefix; neither is an
    independent witness. An incomplete decision remains visible after a crash.
    """
    def __init__(self, directory, root, ledger, goal):
        self.root = Path(root).resolve()
        self.ledger = Path(ledger).resolve()
        self.directory = Path(directory).absolute()
        if (self.directory.resolve() != self.directory or
                self.directory == self.root or self.directory == self.ledger or
                self.directory in self.ledger.parents or
                self.directory == self.root / "implementation" or
                self.root / "implementation" in self.directory.parents):
            raise ValueError("experience directory must be dedicated and separate from source and execution ledger")
        self.directory.mkdir(exist_ok=True)
        self.lock = self.directory / ".active"
        self.lock.mkdir()  # refuse concurrent runs; interrupted lock requires inspection
        try:
            self.scope = digest(canonical([str(self.root), str(self.ledger), goal]))
            self.engine = ConsolidationEngine(node_id_version="v2",
                                              default_status=NodeEpistemicStatus.RECORDED)
            self.guard = SourceMonitoringGuard()
            self.bridge = EpistemicLedgerBridge(self.engine, self.guard)
            self.rows = self._load()
            self.raw_ledger = self._ledger_bytes()
            if self.raw_ledger:
                self.bridge.ingest_agent_ledger(self.ledger, expected_sha256=digest(self.raw_ledger))
            self.relevant = self._recall()
        except BaseException:
            self.close()
            raise

    def close(self):
        self.lock.rmdir()

    def _ledger_bytes(self):
        if not self.ledger.exists():
            return b""
        return read_bounded_regular(self.ledger, MAX_LEDGER_BYTES)

    def _load(self):
        rows = []
        for path in sorted(self.directory.glob("*.experience.json")):
            if len(rows) >= MAX_RECORDS:
                raise ValueError("experience record limit reached")
            raw = read_bounded_regular(path, MAX_RECORD)
            row = json.loads(raw, object_pairs_hook=unique)
            if (type(row) is not dict or set(row) != {"payload", "sha256"} or
                    digest(canonical(row["payload"])) != row["sha256"] or
                    row["payload"].get("schema") != SCHEMA or
                    path.name != row["sha256"] + ".experience.json"):
                raise ValueError("invalid retained experience")
            rows.append(row)
        return rows

    def _write(self, payload):
        if len(self.rows) >= MAX_RECORDS:
            raise ValueError("experience record limit reached")
        payload = {"schema": SCHEMA, "scope": self.scope, **payload}
        key = digest(canonical(payload))
        row = {"payload": payload, "sha256": key}
        raw = canonical(row) + b"\n"
        if len(raw) > MAX_RECORD:
            raise ValueError("experience record too large")
        with (self.directory / (key + ".experience.json")).open("xb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        self.rows.append(row)
        return key

    def _recall(self):
        decisions = {r["sha256"]: r["payload"] for r in self.rows
                     if r["payload"].get("kind") == "DECISION"}
        reports = []
        for row in self.rows:
            p = row["payload"]
            if p.get("scope") != self.scope or p.get("kind") != "OUTCOME":
                continue
            d = decisions.get(p.get("decision"))
            if not d or d.get("scope") != self.scope:
                continue
            n = p.get("ledger_bytes")
            if (type(n) is not int or n <= 0 or n > len(self.raw_ledger)
                    or digest(self.raw_ledger[:n]) != p.get("ledger_sha256")):
                continue
            if p.get("workflow_id") != d.get("workflow_id"):
                continue
            before = d.get("ledger_before_bytes")
            if (type(before) is not int or before < 0 or before >= n or
                    digest(self.raw_ledger[:before]) != d.get("ledger_before_sha256")):
                continue
            try:
                stages = native_events(self.raw_ledger, before, n, d["workflow_id"], p["status"])
            except (ValueError, KeyError, TypeError):
                continue
            paths = d.get("paths")
            if type(paths) is not list or tuple(paths) not in tuple(tuple(sorted(x)) for x in PAIRS):
                continue
            fb = p.get("feedback")
            failure = (fb.get("failure_kind") if type(fb) is dict else None)
            if failure not in ("READ_FAILED", "READ_BOUNDARY_CHANGED") or p["status"] != "STOPPED":
                failure = None
            if failure:
                observed = fb.get("observations")
                native_steps = stages[-1].get("task_result", {}).get("steps", []) if stages else []
                last = native_steps[-1] if native_steps else {}
                if (not isinstance(observed, list) or not observed or
                        last.get("status") != "FAILED" or last.get("tool") != "read_text" or
                        last.get("step_id") != observed[-1].get("step_id") or
                        last.get("observation", {}).get("ok") is not False):
                    failure = None
            now = fingerprint(self.root, paths)
            same = now is not None and now == d.get("conditions")
            report = {"record_sha256": row["sha256"], "decision_sha256": p["decision"],
                      "paths": paths, "status": p["status"], "failure_kind": failure,
                      "same_observed_conditions": same,
                      "failed_step": fb["observations"][-1] if failure else None,
                      "cause": "UNKNOWN",
                      "repair_verified": "UNKNOWN", "source": "REPORTED_UNVERIFIED",
                      "workflow_id": d["workflow_id"]}
            assertion = canonical(report).decode("ascii")
            attr = self.guard.record_unverified_ledger_report(assertion, record_sha256=row["sha256"])
            self.engine.ingest_event_stream([(row["sha256"], {"concept": "planner_experience:" + self.scope,
                                                                "assertion": assertion, "status": "RECORDED"})])
            reports.append((report, attr))
        self.engine.validate_lineage_integrity()
        recalled = {n.assertion for n in self.engine.retrieve_active_context("planner_experience:" + self.scope)}
        # prioritize same-condition failures, then other historical outcomes
        reports.sort(key=lambda pair: (not bool(pair[0]["same_observed_conditions"] and pair[0]["failure_kind"]),
                                       pair[0]["record_sha256"]))
        focus = WorkingMemoryBuffer(capacity=4, source_guard=self.guard)
        for report, attr in reports[:4]:
            if attr.assertion in recalled:
                focus.ingest("planner_experience:" + self.scope, attr.assertion, attr)
        self.context = [json.loads(c.assertion) for c in focus.active_chunks]
        return [r for r, _ in reports]

    def blocks(self, paths):
        current = fingerprint(self.root, paths)
        if current is None:
            return []
        return [r["record_sha256"] for r in self.relevant
                if r["failure_kind"] and r["paths"] == sorted(paths)
                # Re-evaluate the exact fingerprint used by the retained decision.
                and any(x["sha256"] == r["decision_sha256"] and
                        x["payload"].get("conditions") == current for x in self.rows)]

    def choice_only(self, choice, status, *, prior=None):
        return self._write({"kind": "CHOICE", "run": uuid.uuid4().hex,
                            "choice": choice, "status": status, "prior": prior,
                            "recalled": [r["record_sha256"] for r in self.context],
                            "failure": False})

    def begin(self, workflow, choice, paths, *, prior=None):
        if len(self.rows) + 2 > MAX_RECORDS:
            raise ValueError("insufficient retained experience capacity for decision and outcome")
        raw = self._ledger_bytes()
        return self._write({"kind": "DECISION", "run": uuid.uuid4().hex,
                            "ledger_before_bytes": len(raw), "ledger_before_sha256": digest(raw),
                            "workflow_id": workflow["workflow_id"], "workflow": workflow,
                            "choice": choice, "paths": sorted(paths or ()),
                            "conditions": fingerprint(self.root, paths or ()),
                            "prior": prior,
                            "recalled": [r["record_sha256"] for r in self.context]})

    def finish(self, decision, outcome, feedback):
        raw = self._ledger_bytes()
        d = next(r["payload"] for r in self.rows if r["sha256"] == decision)
        before = d["ledger_before_bytes"]
        if digest(raw[:before]) != d["ledger_before_sha256"]:
            raise ValueError("execution ledger prefix changed during attempt")
        native_events(raw, before, len(raw), d["workflow_id"], outcome["status"])
        return self._write({"kind": "OUTCOME", "decision": decision,
                            "status": outcome["status"], "workflow_id": outcome["workflow_id"],
                            "feedback": feedback, "result_sha256": digest(canonical(outcome)),
                            "ledger_bytes": len(raw), "ledger_sha256": digest(raw),
                            "claim_truth": "UNKNOWN", "benefit_verified": "UNKNOWN",
                            "repair_verified": "UNKNOWN"})
