"""PR #298: opt-in Linux peak-RSS probe, synthetic input only.

This test deliberately uses 128 * 1 MiB JSONL records, one Task ID, and the
real streamed ario_agent.main --inspect-task-id CLI with a counting sink.
No real ledger, signer, or runtime source is modified. A pass says nothing
about other workloads or platforms; the >256 MiB case fails visibly.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

RECORD_BYTES = 1024 * 1024
RECORDS = 128
TASK_ID = "PR298-RSS-SYNTHETIC"
PEAK_RSS_LIMIT = 256 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _exact_record(frame: dict, varying_field: str) -> bytes:
    """Create a JSONL record of exactly RECORD_BYTES, with a bounded buffer."""
    data = dict(frame)
    data[varying_field] = ""
    empty = json.dumps(data, ensure_ascii=False, sort_keys=True)
    need = RECORD_BYTES - len(empty.encode("utf-8")) - 1
    if need < 0:
        raise AssertionError("fixture header too large")
    data[varying_field] = "X" * need
    raw = (json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    if len(raw) != RECORD_BYTES:
        raise AssertionError("synthetic physical record is not exactly 1 MiB")
    return raw


def write_synthetic_ledger(path: Path) -> None:
    """Write 128 bounded physical records without retaining the full corpus."""
    with path.open("wb") as sink:
        sink.write(_exact_record({
            "event": "TASK_STARTED", "task_id": TASK_ID,
            "goal": "Synthetic performance test", "step_ids": [],
            "success_criteria_ids": [],
        }, "padding"))
        for i in range(RECORDS - 2):
            # Large retained projected tool fields exercise report serialization.
            sink.write(_exact_record({
                "event": "STEP_OBSERVED", "task_id": TASK_ID,
                "step_id": f"s{i}", "status": "SUCCEEDED", "timestamp": "t",
            }, "tool"))
        sink.write(_exact_record({
            "event": "TASK_FINISHED", "task_id": TASK_ID,
            "status": "STOPPED",
        }, "padding"))
    if path.stat().st_size != RECORD_BYTES * RECORDS:
        raise AssertionError("synthetic corpus total byte count mismatch")


class CountingSink:
    """Consume CLI output immediately; never retain the complete report."""
    def __init__(self):
        self.digest = hashlib.sha256()
        self.chars = 0
        self.utf8_bytes = 0
        self.writes = 0
        self.max_write_chars = 0

    def write(self, text: str) -> int:
        if not isinstance(text, str):
            raise AssertionError("CLI emitted non-text stdout")
        raw = text.encode("utf-8")
        self.digest.update(raw)
        self.chars += len(text)
        self.utf8_bytes += len(raw)
        self.writes += 1
        self.max_write_chars = max(self.max_write_chars, len(text))
        return len(text)

    def flush(self):
        return None


def worker(path: Path) -> int:
    if sys.platform != "linux":
        print("Linux-only RSS evidence worker", file=sys.stderr)
        return 2
    import resource

    # python -I excludes cwd from sys.path; import exact checked-out code.
    implementation = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(implementation))
    import ario_agent

    baseline = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    sink = CountingSink()
    stdout = sys.stdout
    try:
        sys.stdout = sink
        exit_code = ario_agent.main([
            "--inspect-task-id", TASK_ID, "--ledger", str(path)
        ])
    finally:
        sys.stdout = stdout
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    result = {
        "cli_exit": exit_code,
        "peak_rss_bytes": peak,
        "startup_peak_rss_bytes": baseline,
        "output_characters": sink.chars,
        "output_utf8_bytes": sink.utf8_bytes,
        "output_sha256": sink.digest.hexdigest(),
        "output_write_calls": sink.writes,
        "max_output_fragment_chars": sink.max_write_chars,
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if exit_code == 0 else 2


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        return worker(Path(sys.argv[2]))
    if len(sys.argv) != 1:
        raise SystemExit("usage: python research/pr298/linux_rss_probe.py")
    if sys.platform != "linux":
        raise SystemExit("Linux runner only; no fabricated cross-platform measurement")

    with tempfile.TemporaryDirectory(prefix="pr298-rss-synthetic-") as temporary:
        path = Path(temporary) / "synthetic.jsonl"
        write_synthetic_ledger(path)
        before = sha256_file(path)
        proc = subprocess.run(
            [sys.executable, "-I", "-B", str(Path(__file__).resolve()),
             "--worker", str(path)],
            capture_output=True, text=True, check=False, timeout=240,
        )
        after = sha256_file(path)
        if proc.returncode:
            print(json.dumps({"status": "ERROR", "worker_exit": proc.returncode,
                              "error_tail": proc.stderr[-1200:]}, sort_keys=True))
            return 2
        result = json.loads(proc.stdout)
        result.update({
            "platform": sys.platform,
            "python": sys.version.split(" ")[0],
            "fixture_bytes": RECORD_BYTES * RECORDS,
            "fixture_records": RECORDS,
            "source_sha256_before": before,
            "source_sha256_after": after,
            "threshold_bytes": PEAK_RSS_LIMIT,
            "status": "BENCHMARK_PASS" if result["peak_rss_bytes"] < PEAK_RSS_LIMIT
                      else "BENCHMARK_FAIL",
        })
        if before != after:
            result["status"] = "LEDGER_MUTATED"
        if result["output_utf8_bytes"] < 120 * 1024 * 1024:
            result["status"] = "INVALID_BENCHMARK_OUTPUT"
        if result["max_output_fragment_chars"] >= 2 * 1024 * 1024:
            result["status"] = "NON_STREAMED_OUTPUT"
        if result["cli_exit"] != 0:
            result["status"] = "CLI_FAILURE"
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "BENCHMARK_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
