"""Offline diagnostics for archived ARIO_REVIEW_EVIDENCE_V1 records.

Run from implementation: python -m research.review_evidence PIN FIRST LAST
No network, credential lookup, status publisher, or merge decision.
"""
import argparse
import html
import json
import re
from pathlib import Path

from bounded_json import MAX_JSON_FILE_BYTES, loads_bounded
from pr_ci_github_evidence import matches_id
from pr_claim_audit import Invalid, RUN_COMMAND
from pr_claim_audit_log_parser_v0_8 import extract_log

REPO_ID = 1401709791
FLOW_ID = 379498305
FLOW_PATH = ".github/workflows/implementation-regression.yml"
BOT_ID = 136622811
ACTIONS_ID = 15368
MARKER = "ARIO_REVIEW_EVIDENCE_V1"
SHA = re.compile(r"[0-9a-f]{40}")
RECORD_FIELDS = {"version", "scope", "reviewed_head_sha", "files", "red_run_ids",
                 "green_run_id", "risk_disposition", "limitations", "red_failure"}


class GateError(ValueError):
    """The supplied observations cannot support a consistency diagnostic."""


def require(condition, reason):
    if not condition:
        raise GateError(reason)


def positive(value):
    return type(value) is int and value > 0


def unique(pairs):
    obj = dict(pairs)
    require(len(obj) == len(pairs), "duplicate JSON member")
    return obj


def reject_constant(_):
    raise GateError("nonstandard JSON constant")


def decode(text):
    return loads_bounded(text, object_pairs_hook=unique, parse_constant=reject_constant)


def parse_record(body):
    require(isinstance(body, str) and len(body.encode("utf-8")) <= 256 * 1024, "invalid PR body")
    require(len(re.findall(r"<!--\s*" + MARKER, body)) == 1, "absent or ambiguous record")
    block = re.search(r"<!--[ \t]*" + MARKER + r"[ \t]*\r?\n(.*?)\r?\n-->", body, re.S)
    require(block, "incomplete record")
    try:
        obj = decode(block[1])
    except ValueError as exc:
        raise GateError("invalid record JSON") from exc
    require(isinstance(obj, dict) and obj.keys() == RECORD_FIELDS, "invalid V1 fields")
    require(matches_id(obj["version"], 1) and obj["scope"] == "ROUTINE_LAB"
            and obj["risk_disposition"] == "NO_KNOWN_BLOCKERS", "unsupported V1 declaration")
    require(isinstance(obj["reviewed_head_sha"], str) and SHA.fullmatch(obj["reviewed_head_sha"]),
            "invalid reviewed head")
    paths = obj["files"]
    require(isinstance(paths, list) and 2 <= len(paths) <= 20
            and all(isinstance(p, str) and 0 < len(p) <= 256 for p in paths)
            and len(set(paths)) == len(paths), "invalid declared file list")
    reds, green = obj["red_run_ids"], obj["green_run_id"]
    require(isinstance(reds, list) and 1 <= len(reds) <= 12 and all(positive(x) for x in reds)
            and len(set(reds)) == len(reds) and positive(green) and green not in reds, "invalid run IDs")
    for key in ("red_failure", "limitations"):
        require(isinstance(obj[key], str) and 24 <= len(obj[key]) <= 3000, "invalid V1 narrative")
    return obj


def validate_run_binding(pr, run):
    head, base = pr["head"], pr["base"]
    require(run["event"] == "pull_request" and run["status"] == "completed", "incomplete PR run")
    require(positive(pr["id"]) and positive(pr["number"]) and positive(head["repo"]["id"])
            and isinstance(head["ref"], str) and head["ref"]
            and matches_id(base["repo"]["id"], REPO_ID) and base["ref"] == "main", "invalid PR identity")
    require(matches_id(run["repository"]["id"], REPO_ID)
            and matches_id(run["head_repository"]["id"], head["repo"]["id"])
            and run["head_branch"] == head["ref"], "wrong run repository or branch")
    links = run["pull_requests"]
    require(isinstance(links, list), "missing PR associations")
    linked = [p for p in links if matches_id(p["id"], pr["id"]) or matches_id(p["number"], pr["number"])]
    require(len(linked) == 1, "missing or ambiguous PR association")
    link = linked[0]
    require(matches_id(link["id"], pr["id"]) and matches_id(link["number"], pr["number"])
            and link["head"]["ref"] == head["ref"] and link["base"]["ref"] == base["ref"]
            and matches_id(link["base"]["repo"]["id"], REPO_ID)
            and matches_id(link["head"]["repo"]["id"], head["repo"]["id"]), "wrong PR association")


def collection(page, *, threads=False):
    require(isinstance(page, dict) and not page.get("errors"), "invalid or failed collection")
    nodes = page["nodes"]
    count = page["totalCount"]
    require(page["pageInfo"]["hasNextPage"] is False and isinstance(nodes, list)
            and type(count) is int and len(nodes) == count, "incomplete collection")
    ids = [node["id"] for node in nodes]
    valid_ids = all(isinstance(i, str) and i for i in ids) if threads else all(positive(i) for i in ids)
    require(valid_ids and len(set(ids)) == count, "invalid or repeated item ID")
    return nodes


def observed_ancestor(comparison, ancestor, head):
    commits = comparison["commits"]
    return (ancestor != head and comparison["status"] == "ahead"
            and comparison["base_commit"]["sha"] == comparison["merge_base_commit"]["sha"] == ancestor
            and isinstance(commits, list) and bool(commits)
            and matches_id(comparison["total_commits"], len(commits)) and commits[-1]["sha"] == head)


def known_blocker(body):
    visible = re.sub(r"<[^>]*>", "", html.unescape(body))
    return re.search(r"(?:\*\*|alt=[\"'])\s*(?:Severity:\s*)?(?:Major|Critical)\b",
                     body + "\n" + visible, re.I)


def check_run(pr, entry, is_green):
    run, suite, jobs = entry["run"], entry["suite"], entry["jobs"]
    validate_run_binding(pr, run)
    outcome = "success" if is_green else "failure"
    revision = run["head_sha"]
    require(positive(run["id"]) and positive(run["run_attempt"]) and SHA.fullmatch(revision)
            and run["conclusion"] == outcome and matches_id(run["workflow_id"], FLOW_ID)
            and run["path"] == FLOW_PATH, "wrong workflow or outcome")
    require(positive(run["check_suite_id"]) and matches_id(suite["id"], run["check_suite_id"])
            and suite["head_sha"] == revision and matches_id(suite["app"]["id"], ACTIONS_ID),
            "wrong check suite or app")
    if is_green:
        require(revision == pr["head"]["sha"], "wrong GREEN revision")
    else:
        require(observed_ancestor(entry["comparison"], revision, pr["head"]["sha"]),
                "missing RED ancestry observation")
    items = jobs["jobs"]
    require(isinstance(items, list) and items and matches_id(jobs["total_count"], len(items)),
            "incomplete job collection")
    ids = [job["id"] for job in items]
    require(all(positive(i) for i in ids) and len(set(ids)) == len(ids), "invalid or repeated job ID")
    selected = [job for job in items if job["name"] == "m0-regression"]
    require(len(selected) == 1, "missing or ambiguous canonical job")
    job = selected[0]
    require(matches_id(job["run_id"], run["id"]) and matches_id(job["run_attempt"], run["run_attempt"])
            and job["head_sha"] == revision and job["status"] == "completed"
            and job["conclusion"] == outcome, "job binding mismatch")
    log = entry["log"]
    require(matches_id(log["job_id"], job["id"]) and log["complete"] is True, "missing job log")
    counts = extract_log(log["text"])
    require(counts["python_version"].startswith("3.13."), "wrong canonical Python version")
    checkout = entry["checkout"]
    pre_test_log = log["text"].partition("##[group]Run " + RUN_COMMAND)[0]
    revisions = re.findall(r"(?m)^(?:[0-9T:.\-]+Z )?\[command\]/usr/bin/git log -1 --format=%H\r?\n"
                           r"(?:[0-9T:.\-]+Z )?([0-9a-f]{40})\r?$", pre_test_log)
    require(revisions == [checkout["sha"]] and len(checkout["parents"]) == 2
            and checkout["parents"][1]["sha"] == revision, "checkout revision mismatch")
    tested_base = checkout["parents"][0]["sha"]
    if tested_base != pr["base"]["sha"]:
        require(not is_green and SHA.fullmatch(tested_base)
                and observed_ancestor(entry["base_comparison"], tested_base, pr["base"]["sha"]),
                "checkout base mismatch")
    if is_green:
        require(counts["passed"] > 0 and counts["failed"] == 0, "GREEN count mismatch")
    else:
        require(counts["failed"] > 0, "RED count mismatch")


def assess(pin, first, last):
    result = {"gate": "HOLD", "metadata": "UNKNOWN", "merge_authorized": False,
              "execution_attestation": "UNKNOWN", "review_states": []}
    try:
        require(all(isinstance(obj, dict) for obj in (pin, first, last)), "invalid evidence object")
        # Structural equality in Python treats a JSON boolean as an integer.
        require(json.dumps(first, sort_keys=True, allow_nan=False) ==
                json.dumps(last, sort_keys=True, allow_nan=False), "observations changed")
        require(not first.get("errors"), "capture reports errors")
        pr = first["pr"]
        for key in ("id", "number"):
            require(positive(pin[key]) and matches_id(pr[key], pin[key]), "wrong PR")
        for side in ("head", "base"):
            revision = pin[side + "_sha"]
            require(SHA.fullmatch(revision) and pr[side]["sha"] == revision, "wrong PR revision")
        require(pr["state"] == "open" and positive(pin["head_repo_id"])
                and matches_id(pr["head"]["repo"]["id"], pin["head_repo_id"]), "wrong head repository")
        rec = parse_record(pr["body"])
        require(rec["reviewed_head_sha"] == pin["head_sha"], "stale declaration")
        files = first["files"]
        require(isinstance(files, list) and matches_id(pr["changed_files"], len(files))
                and len(files) == len(rec["files"]) and set(files) == set(rec["files"]),
                "declared files differ from observed diff")
        runs = first["runs"]
        expected = {*rec["red_run_ids"], rec["green_run_id"]}
        require(isinstance(runs, list) and len(runs) == len(expected)
                and {r["run"]["id"] for r in runs} == expected, "missing or extra RED/GREEN evidence")
        for entry in runs:
            check_run(pr, entry, entry["run"]["id"] == rec["green_run_id"])

        author = pr["user"]["id"]
        require(positive(author), "unknown author")
        pr_url = f"https://api.github.com/repos/SepehrGhanbari/Ario/pulls/{pr['number']}"
        reviews = collection(first["reviews"])
        require(all(r["pull_request_url"] == pr_url for r in reviews), "review from another PR")
        require(all(r["state"] in {"COMMENTED", "APPROVED", "DISMISSED", "PENDING"}
                    for r in reviews), "blocking or unknown review state")
        matched = [r for r in reviews if matches_id(r["user"]["id"], BOT_ID) and author != BOT_ID
                   and r["user"]["login"] == "coderabbitai[bot]" and r["user"]["type"] == "Bot"
                   and r["commit_id"] == pin["head_sha"] and r["state"] in {"COMMENTED", "APPROVED"}]
        require(matched and all(isinstance(r["body"], str) and not known_blocker(r["body"])
                                for r in matched), "missing or blocking exact-head review")
        require(matches_id(first["threads"]["pr_id"], pr["id"]), "wrong thread connection")
        require(all(t["isResolved"] is True for t in collection(first["threads"], threads=True)), "open or unknown thread")
        require(all(c["pull_request_url"] == pr_url and isinstance(c["body"], str)
                    and not known_blocker(c["body"]) and SHA.fullmatch(c["commit_id"])
                    for c in collection(first["comments"])), "unknown inline comment")
        result.update(metadata="CONSISTENT", review_states=sorted({r["state"] for r in matched}))
    except (ValueError, KeyError, TypeError, Invalid, IndexError, OverflowError, RecursionError) as exc:
        result["reason"] = str(exc) if isinstance(exc, GateError) else "malformed or incomplete evidence"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, nargs=3, metavar="JSON")
    args = parser.parse_args()
    values = []
    try:
        for path in args.inputs:
            with path.open("rb") as stream:
                raw = stream.read(MAX_JSON_FILE_BYTES + 1)
            require(len(raw) <= MAX_JSON_FILE_BYTES, "input size limit")
            values.append(decode(raw.decode("utf-8")))
        result = assess(*values)
    except (OSError, ValueError, RecursionError):
        result = {"gate": "HOLD", "metadata": "UNKNOWN", "merge_authorized": False,
                  "execution_attestation": "UNKNOWN", "review_states": [], "reason": "unreadable input"}
    print(json.dumps(result, sort_keys=True))
    return 1  # Deliberately unusable as a passing governance status.


if __name__ == "__main__":
    raise SystemExit(main())
