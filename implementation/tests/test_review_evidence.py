"""Offline contract tests. No GitHub credentials, requests or status publications."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from research import review_evidence as gate


HEAD, BASE, RED = "a" * 40, "b" * 40, "c" * 40
REPO = 1401709791
PR_URL = "https://api.github.com/repos/SepehrGhanbari/Ario/pulls/7"
PIN = {"number": 7, "id": 107, "head_sha": HEAD, "base_sha": BASE, "head_repo_id": REPO}


def record():
    return {"version": 1, "scope": "ROUTINE_LAB", "reviewed_head_sha": HEAD,
            "files": ["implementation/example.py", "implementation/tests/test_example.py"],
            "red_run_ids": [31], "green_run_id": 32, "risk_disposition": "NO_KNOWN_BLOCKERS",
            "limitations": "Synthetic local metadata without external custody.",
            "red_failure": "The example regression originally returned an incorrect count."}


def body(value):
    return "<!-- ARIO_REVIEW_EVIDENCE_V1\n" + value + "\n-->"


def branch(ref, sha):
    return {"ref": ref, "sha": sha, "repo": {"id": REPO}}


def pr():
    return {"number": 7, "id": 107, "state": "open", "draft": True, "changed_files": 2, "user": {"id": 99},
            "head": branch("research/example", HEAD), "base": branch("main", BASE),
            "body": body(json.dumps(record()))}


def run(rid, sha, result):
    target = pr()
    link = {k: target[k] for k in ("id", "number", "head", "base")}
    return {"id": rid, "head_sha": sha, "head_branch": target["head"]["ref"],
            "repository": {"id": REPO}, "head_repository": {"id": REPO},
            "pull_requests": [link], "status": "completed", "event": "pull_request",
            "run_attempt": 1, "workflow_id": 379498305,
            "path": ".github/workflows/implementation-regression.yml",
            "conclusion": result, "check_suite_id": rid + 10}


class RecordContract(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(gate.parse_record(pr()["body"]), record())

    def test_crlf(self):
        self.assertEqual(gate.parse_record(pr()["body"].replace("\n", "\r\n")), record())

    def test_version_is_integer(self):
        with self.assertRaises(gate.GateError):
            gate.parse_record(body(json.dumps(dict(record(), version=True))))

    def test_duplicate_member(self):
        text = json.dumps(record()).replace('"version": 1', '"version": 1, "version": 1')
        with self.assertRaises(gate.GateError):
            gate.parse_record(body(text))

    def test_incomplete_second_record(self):
        with self.assertRaises(gate.GateError):
            gate.parse_record(pr()["body"] + "\n<!-- ARIO_REVIEW_EVIDENCE_V1")


class AssociationContract(unittest.TestCase):
    def test_valid(self):
        gate.validate_run_binding(pr(), run(32, HEAD, "success"))

    def test_pr_database_id_must_match(self):
        obj = run(32, HEAD, "success")
        obj["pull_requests"][0]["id"] += 1
        with self.assertRaises(gate.GateError):
            gate.validate_run_binding(pr(), obj)

    def test_float_repository_id_is_malformed(self):
        obj = run(32, HEAD, "success")
        obj["pull_requests"][0]["base"]["repo"]["id"] = float(REPO)
        with self.assertRaises(gate.GateError):
            gate.validate_run_binding(pr(), obj)


def page(*nodes):
    return {"nodes": list(nodes), "totalCount": len(nodes), "pageInfo": {"hasNextPage": False}}


def observation():
    runs = []
    for rid, sha, result, summary in [(31, RED, "failure", "1 failed"), (32, HEAD, "success", "2 passed")]:
        job = {"id": 1000 + rid, "name": "m0-regression", "run_id": rid, "run_attempt": 1,
               "head_sha": sha, "status": "completed", "conclusion": result}
        checkout = "d" * 40 if rid == 31 else "e" * 40
        runs.append({"checkout": {"sha": checkout, "parents": [{"sha": BASE}, {"sha": sha}]},
                     "run": run(rid, sha, result), "suite": {"id": rid + 10, "app": {"id": 15368},
                                                             "head_sha": sha},
                     "jobs": {"total_count": 1, "jobs": [job]},
                     "log": {"job_id": job["id"], "complete": True,
                             "text": "[command]/usr/bin/git log -1 --format=%H\n" + checkout
                                     + "\nPython 3.13.5\n##[group]Run python -m pytest -q tests\n"
                                     + summary + " in 1.0s"}})
    runs[0]["comparison"] = {"status": "ahead", "base_commit": {"sha": RED},
                             "merge_base_commit": {"sha": RED}, "total_commits": 1,
                             "commits": [{"sha": HEAD}]}
    review = {"id": 13, "pull_request_url": PR_URL, "commit_id": HEAD, "state": "COMMENTED", "body": "Synthetic review",
              "user": {"id": 136622811, "login": "coderabbitai[bot]", "type": "Bot"}}
    return {"pr": pr(), "files": record()["files"], "reviews": page(review),
            "threads": dict(page(), pr_id=107), "comments": page(),
            "runs": runs}


class DiagnosticContract(unittest.TestCase):
    def assess(self, first, last=None):
        out = gate.assess(PIN, first, copy.deepcopy(first) if last is None else last)
        self.assertEqual(out["gate"], "HOLD")
        self.assertIs(out["merge_authorized"], False)
        return out

    def test_consistent_snapshot_is_only_a_diagnostic(self):
        out = self.assess(observation())
        self.assertEqual(out["metadata"], "CONSISTENT")
        self.assertEqual(out["review_states"], ["COMMENTED"])
        self.assertEqual(out["execution_attestation"], "UNKNOWN")

    def test_native_approved_state_is_preserved(self):
        data = observation()
        data["reviews"]["nodes"][0]["state"] = "APPROVED"
        self.assertEqual(self.assess(data)["review_states"], ["APPROVED"])

    def test_incomplete_or_mismatched_evidence(self):
        self.assertEqual(self.assess([])["metadata"], "UNKNOWN")
        changes = [
            (("reviews",), []), (("comments",), []),
            (("runs", 1, "log", "text"), observation()["runs"][1]["log"]["text"].replace("3.13.5", "3.14.1")),
            (("comments", "pageInfo", "hasNextPage"), True),
            (("runs", 1, "run", "pull_requests", 0, "number"), 8),
            (("runs", 1, "run", "repository", "id"), 42),
            (("runs", 1, "jobs", "jobs", 0, "name"), "different job"),
            (("runs", 1, "run", "event"), "push"),
            (("files",), ["other"]), (("reviews", "nodes", 0, "pull_request_url"), PR_URL + "8"),
            (("reviews", "nodes", 0, "body"), "**Severity: Major**"),
            (("runs", 1, "checkout", "parents", 0, "sha"), RED),
            (("runs", 1, "checkout", "sha"), BASE), (("threads", "pr_id"), 101),
            (("runs",), []), (("runs", 0, "run", "conclusion"), "success"),
            (("runs", 0, "run", "head_sha"), HEAD), (("runs", 1, "run", "head_sha"), RED),
            (("runs", 1, "run", "workflow_id"), 3), (("runs", 1, "run", "path"), "other.yml"),
            (("runs", 1, "suite", "app", "id"), 3), (("runs", 1, "suite", "id"), 11),
            (("runs", 1, "jobs", "total_count"), 2), (("runs", 1, "log", "complete"), False),
            (("runs", 1, "jobs", "jobs", 0, "run_attempt"), 3),
            (("runs", 0, "comparison", "status"), "diverged"),
            (("runs", 0, "comparison", "commits"), []),
            (("runs", 0, "log", "text"), "0 tests collected"),
            (("pr", "user", "id"), 136622811), (("reviews", "nodes", 0, "commit_id"), RED),
            (("reviews", "nodes", 0, "user", "id"), 23), (("reviews",), page()),
            (("reviews", "nodes", 0, "state"), "CHANGES_REQUESTED"),
            (("reviews", "nodes", 0, "body"), None),
            (("threads",), dict(page({"id": "t1", "isResolved": False}), pr_id=107)),
            (("threads",), dict(page({"id": "t1", "isResolved": "true"}), pr_id=107)),
            (("comments", "pageInfo", "hasNextPage"), None), (("reviews", "totalCount"), 2),
            (("pr", "base", "sha"), RED),
        ]
        for path, value in changes:
            with self.subTest(path=path):
                data = observation()
                target = data
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                self.assertEqual(self.assess(data)["metadata"], "UNKNOWN")

    def test_changes_between_reads_invalidate_prior_diagnostic(self):
        for kind in ("edit", "delete", "head", "base"):
            with self.subTest(kind=kind):
                first = observation()
                first["comments"] = page({"id": 19, "pull_request_url": PR_URL, "body": "initial note", "commit_id": HEAD})
                last = copy.deepcopy(first)
                if kind == "edit":
                    last["comments"]["nodes"][0]["body"] = "revised note"
                elif kind == "delete":
                    last["comments"] = page()
                else:
                    last["pr"][kind]["sha"] = RED
                out = self.assess(first, last)
                self.assertEqual(out["metadata"], "UNKNOWN")
                self.assertEqual(out["review_states"], [])

    def test_cli_always_holds_and_rejects_invalid_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / name for name in ("pin.json", "first.json", "last.json")]
            for path, item in zip(paths, (PIN, observation(), observation())):
                path.write_text(json.dumps(item), encoding="utf-8")
            def run_cli():
                return subprocess.run([sys.executable, "-B", "-m", "research.review_evidence", *paths],
                                      cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
            child = run_cli()
            self.assertEqual(child.returncode, 1, child.stderr)
            self.assertEqual(json.loads(child.stdout)["metadata"], "CONSISTENT")
            for malformed in (b'{"number":7,"number":7}', b'{"x": NaN}', b'\xff'):
                with self.subTest(malformed=malformed):
                    paths[0].write_bytes(malformed)
                    child = run_cli()
                    self.assertEqual(child.returncode, 1, child.stderr)
                    self.assertEqual(json.loads(child.stdout)["metadata"], "UNKNOWN")
                    self.assertEqual(child.stderr, "")
