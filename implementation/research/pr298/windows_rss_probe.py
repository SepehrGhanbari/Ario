"""PR #298 Windows fresh-process working-set test; synthetic data only.

Uses the SAME corpus builder, Task ID, and counting sink as Linux CI.
The reader runs in a separate, pinned Python process. No real ledger is read.
Windows PeakWorkingSetSize counts the CLI including streamed JSON emission;
the benchmark fails visibly if this peak exceeds the trial target.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

# The worker starts with -I; explicitly resolve this checked-out script dir.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import linux_rss_probe as fixture


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def working_set_peak_bytes() -> int:
    if sys.platform != "win32":
        raise RuntimeError("Windows process memory counter is available on Windows only")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.GetCurrentProcess.argtypes = []
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), ctypes.c_ulong
    ]
    values = PROCESS_MEMORY_COUNTERS()
    values.cb = ctypes.sizeof(values)
    if not psapi.GetProcessMemoryInfo(
        kernel.GetCurrentProcess(), ctypes.byref(values), values.cb
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(values.PeakWorkingSetSize)


def worker(ledger: Path) -> int:
    if sys.platform != "win32":
        raise SystemExit("Windows only; cannot assert an unmeasured Windows result")

    implementation = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(implementation))
    import ario_agent

    initial_peak = working_set_peak_bytes()
    sink = fixture.CountingSink()
    original_stdout = sys.stdout
    try:
        sys.stdout = sink
        code = ario_agent.main([
            "--inspect-task-id", fixture.TASK_ID, "--ledger", str(ledger)
        ])
    finally:
        sys.stdout = original_stdout

    peak = working_set_peak_bytes()
    print(json.dumps({
        "cli_exit": code,
        "startup_peak_working_set_bytes": initial_peak,
        "peak_working_set_bytes": peak,
        "output_characters": sink.chars,
        "output_utf8_bytes": sink.utf8_bytes,
        "output_sha256": sink.digest.hexdigest(),
        "output_write_calls": sink.writes,
        "max_output_fragment_chars": sink.max_write_chars,
    }, sort_keys=True))
    return 0 if code == 0 else 2


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        return worker(Path(sys.argv[2]))
    if len(sys.argv) != 1:
        raise SystemExit("usage: python research/pr298/windows_rss_probe.py")
    if sys.platform != "win32":
        raise SystemExit("Windows runner required; do not substitute a Linux number")

    with tempfile.TemporaryDirectory(prefix="pr298-windows-rss-") as tempdir:
        ledger = Path(tempdir) / "synthetic.jsonl"
        fixture.write_synthetic_ledger(ledger)
        before = fixture.sha256_file(ledger)
        process = subprocess.run(
            [sys.executable, "-I", "-B", str(Path(__file__).resolve()),
             "--worker", str(ledger)],
            capture_output=True, text=True, check=False, timeout=240,
        )
        after = fixture.sha256_file(ledger)
        if process.returncode:
            print(json.dumps({
                "status": "ERROR", "worker_exit": process.returncode,
                "error_tail": process.stderr[-1200:],
            }, sort_keys=True))
            return 2
        result = json.loads(process.stdout)
        result.update({
            "platform": sys.platform,
            "python": sys.version.split(" ")[0],
            "fixture_bytes": ledger.stat().st_size,
            "fixture_records": fixture.RECORDS,
            "source_sha256_before": before,
            "source_sha256_after": after,
            "threshold_bytes": fixture.PEAK_RSS_LIMIT,
            "status": "BENCHMARK_PASS" if (
                result["peak_working_set_bytes"] < fixture.PEAK_RSS_LIMIT
            ) else "BENCHMARK_FAIL",
        })
        if before != after:
            result["status"] = "LEDGER_MUTATED"
        if result["cli_exit"] != 0:
            result["status"] = "CLI_FAILURE"
        if result["output_utf8_bytes"] < 120 * 1024 * 1024:
            result["status"] = "INVALID_BENCHMARK_OUTPUT"
        if result["max_output_fragment_chars"] >= 2 * 1024 * 1024:
            result["status"] = "NON_STREAMED_OUTPUT"
        # Linux and Windows intentionally use the exact same synthetic
        # corpus and JSON wire format: unlike the older Codex Windows case.
        if before != "d7f498b157d7f9326e703ecff97846f8d6297857dd110e2e6a1d4a45d0b4496c":
            result["status"] = "UNEXPECTED_CORPUS_HASH"
        if result["output_sha256"] != "a5f64015f3c38a3bd0b9c3efa8d0697cf3cb1fa038684656480ab1cf79b4621b":
            result["status"] = "UNEXPECTED_OUTPUT_HASH"
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "BENCHMARK_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
