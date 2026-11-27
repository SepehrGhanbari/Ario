"""Real Ollama acceptance: actual bounded reads, controlled fixture fault, fresh processes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

GOAL = "Find a useful bounded source review of the test fixture; choose freely, or STOP."
FIXTURES = {
    "implementation/ario_planner.py": '# bounded planner fixture\ndef choose(intent):\n    if intent == "STOP":\n        return None\n    return intent\n',
    "implementation/tests/test_planner_runtime.py": '# bounded planner test fixture\ndef test_stop():\n    assert choose("STOP") is None\n',
    "implementation/ario_workflow.py": '# alternate review fixture\ndef result_status(failed):\n    return "STOPPED" if failed else "COMPLETED"\n',
    "implementation/tests/test_workflow_runtime.py": '# alternate review test fixture\ndef test_failure():\n    assert result_status(True) == "STOPPED"\n',
}


def child(args):
    import ario_planner
    root = Path(args.workspace)
    if args.fault:
        real = ario_planner.run_workflow
        injected = False

        def execute(workflow, workspace, ledger):
            nonlocal injected
            if not injected:
                path = workflow["stages"][0]["task"]["actions"][0]["path"]
                if path not in FIXTURES:
                    raise RuntimeError("fault target not a disposable fixture")
                target = root / path
                with target.open("ab") as f:
                    f.write(b"# injected source boundary change\n")
                injected = True
            return real(workflow, workspace, ledger)

        ario_planner.run_workflow = execute
    return ario_planner.main([
        "--goal", GOAL, "--workspace", str(root),
        "--ledger", str(root / "native.jsonl"),
        "--experience-dir", str(root / "experience"),
        "--model", args.model, "--ollama-url", args.ollama_url,
        "--timeout", str(args.timeout), "--deliberate", "--execute",
        "--revise-after-result",
    ])


def pair(report):
    workflow = report.get("workflow")
    if not workflow:
        return []
    return sorted({a["path"] for stage in workflow["stages"]
                   for a in stage["task"]["actions"] if a["tool"] == "read_text"})


def run_phase(args, root, name, fault=False):
    cmd = [sys.executable, str(Path(__file__).resolve()), "--child",
           "--workspace", str(root), "--model", args.model,
           "--ollama-url", args.ollama_url, "--timeout", str(args.timeout)]
    if fault:
        cmd.append("--fault")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        out, err = proc.communicate(timeout=2 * args.timeout + 90)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
    (root / (name + ".stdout.json")).write_bytes(out)
    (root / (name + ".stderr.txt")).write_bytes(err)
    try:
        result = json.loads(out)
    except (ValueError, UnicodeError):
        result = {"status": "UNRESOLVED", "stderr": err.decode("utf-8", errors="replace")[-500:]}
    print(json.dumps({"phase": name, "pid": proc.pid, "exit": proc.returncode,
                      "status": result.get("status"), "pair": pair(result),
                      "revision_status": (result.get("revision") or {}).get("status"),
                      "repair_verified": (result.get("revision") or {}).get("repair_verified"),
                      "experience": result.get("experience"),
                      "error": result.get("stderr")}, ensure_ascii=True), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11600")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--workspace", help=argparse.SUPPRESS)
    parser.add_argument("--fault", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        return child(args)
    root = Path(tempfile.mkdtemp(prefix="ario-planner-real-")).resolve()
    for name, value in FIXTURES.items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value, encoding="utf-8")
    initial = {name: (root / name).read_bytes() for name in FIXTURES}
    print(json.dumps({"fixture_workspace": str(root), "transport": "REAL_LOCAL_OLLAMA",
                      "fault": "one controlled fixture source boundary change"}), flush=True)
    first = run_phase(args, root, "01-initial", fault=True)
    failed = pair(first)
    if first.get("status") != "STOPPED" or not failed:
        print(json.dumps({"acceptance": "UNRESOLVED", "reason": "No concrete first failure; model choice preserved."}))
        return 1
    for name, data in initial.items():
        (root / name).write_bytes(data)  # disposable fixture only
    ledger = root / "native.jsonl"
    before = ledger.read_bytes()
    old = {p.name: p.read_bytes() for p in (root / "experience").glob("*.experience.json")}
    second = run_phase(args, root, "02-restart-same")
    same_block = second.get("status") == "RETAINED_FAILURE_SAME_CONDITIONS" and pair(second) == failed
    for name in failed:
        with (root / name).open("ab") as f:
            f.write(b"# changed stable condition\n")
    third = run_phase(args, root, "03-restart-changed")
    changed_execution = third.get("status") == "COMPLETED" and pair(third) == failed
    history_preserved = ledger.read_bytes().startswith(before) and all(
        (root / "experience" / name).read_bytes() == data for name, data in old.items())
    revised = (first.get("revision") or {}).get("status") == "ALTERNATIVE_REVIEW_COMPLETED"
    result = {"initial_alternative_completed": revised, "same_pair_execution_blocked": same_block,
              "changed_pair_executed": changed_execution, "history_preserved": history_preserved,
              "ledger_sha256": hashlib.sha256(ledger.read_bytes()).hexdigest(),
              "acceptance": "PASS" if all((revised, same_block, changed_execution, history_preserved))
              else "PARTIAL_OR_UNRESOLVED", "fixture_workspace": str(root),
              "subjective_consent": "UNKNOWN", "verified_benefit": "UNKNOWN"}
    (root / "acceptance.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result), flush=True)
    return 0 if result["acceptance"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
