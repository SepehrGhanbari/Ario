#!/usr/bin/env python3
"""W1 blind-challenge intake, commitment, and post-reveal scoring.
RESEARCH_ONLY. Does not produce independent labels or authenticate custody.
All inputs are local and JSONL; no network, signer, model or Ario state.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

FORBIDDEN = {
    "gold", "ground_truth", "oracle", "answer", "latent", "secret",
    "hidden_edge", "hidden_root", "labeler", "adjudication", "solution"
}
MASKED_REQUIRED = {"case_id", "graph", "scope", "witness_artifact_refs",
                   "complete_control_surface", "complete_source_surface",
                   "completeness_origin"}
PRED_REQUIRED = {"case_id", "admin_status", "source_status",
                 "evaluator_blob_sha1", "runner_version"}
ORACLE_REQUIRED = {"case_id", "latent_admin_independent",
                   "latent_source_independent", "adjudication",
                   "labeler_a_ref", "labeler_b_ref", "rationale_ref"}
ADMIN = {"LAB_CONDITIONALLY_SEPARATE", "COMMON_CONTROL_DETECTED", "UNKNOWN"}
SOURCE = {"LAB_CONDITIONALLY_DISTINCT", "COMMON_SOURCE_DETECTED", "UNKNOWN"}

def fail(message):
    raise ValueError(message)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def strict_json(line):
    def pairs(items):
        d = {}
        for k, v in items:
            if k in d:
                fail("Duplicate JSON key: " + k)
            d[k] = v
        return d
    return json.loads(line, object_pairs_hook=pairs)

def records(path):
    p = Path(path)
    if not p.is_file() or p.stat().st_size > 16_000_000:
        fail("File missing or above 16MB cap: " + str(p))
    output = []
    ids = set()
    for i, line in enumerate(p.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            fail("Blank JSONL line: " + str(i))
        row = strict_json(line)
        if type(row) is not dict:
            fail("Each line must be object")
        name = row.get("case_id")
        if type(name) is not str or not name or len(name) > 128:
            fail("Invalid case_id on line " + str(i))
        if name in ids:
            fail("Duplicate case_id: " + name)
        ids.add(name)
        output.append(row)
    if not output or len(output) > 20000:
        fail("Empty or oversized record collection")
    return output

def assert_no_leaks(tree):
    if isinstance(tree, dict):
        for k, v in tree.items():
            key = str(k).lower().replace("-", "_")
            if any(mark in key for mark in FORBIDDEN):
                fail("Private-label key present in masked inputs: " + k)
            assert_no_leaks(v)
    elif isinstance(tree, list):
        for v in tree:
            assert_no_leaks(v)

def check_masked(rows):
    for x in rows:
        assert_no_leaks(x)
        if not MASKED_REQUIRED.issubset(x):
            fail("Missing masked fields in " + x["case_id"])
        if type(x["graph"]) is not dict or not {"nodes", "edges", "origin"}.issubset(x["graph"]):
            fail("Invalid graph envelope in " + x["case_id"])
        if not isinstance(x["graph"]["nodes"], list) or not isinstance(x["graph"]["edges"], list):
            fail("Malformed graph in " + x["case_id"])
        if type(x["complete_control_surface"]) is not bool or type(x["complete_source_surface"]) is not bool:
            fail("Completeness flags must be booleans")
        if type(x["witness_artifact_refs"]) is not list or len(x["witness_artifact_refs"]) != 2:
            fail("Expected exactly two witness artifact references")

def check_pred(rows):
    for x in rows:
        if not PRED_REQUIRED.issubset(x):
            fail("Missing prediction fields: " + x["case_id"])
        if x["admin_status"] not in ADMIN or x["source_status"] not in SOURCE:
            fail("Invalid prediction status: " + x["case_id"])
        if type(x["evaluator_blob_sha1"]) is not str or len(x["evaluator_blob_sha1"]) != 40:
            fail("Evaluator hash not a 40-digit blob digest")
        assert_no_leaks(x)

def check_oracle(rows):
    for x in rows:
        if not ORACLE_REQUIRED.issubset(x):
            fail("Incomplete oracle fields: " + x["case_id"])
        if x["adjudication"] not in {"AGREED", "DISPUTED", "UNDETERMINED"}:
            fail("Invalid adjudication")
        for field in ("latent_admin_independent", "latent_source_independent"):
            if x[field] is not None and type(x[field]) is not bool:
                fail("Oracle truth must be boolean or null")
        if x["adjudication"] != "AGREED" and (x["latent_admin_independent"] is not None or x["latent_source_independent"] is not None):
            fail("Disputed/undetermined oracle must not force binary truth")
        if x["labeler_a_ref"] == x["labeler_b_ref"]:
            fail("Independent labeler references cannot be identical (not proof of actual independence)")

def same_ids(left, right):
    a = {x["case_id"] for x in left}
    b = {x["case_id"] for x in right}
    if a != b:
        fail("Case ID sets differ; missing=" + str(len(a-b)) + " extra=" + str(len(b-a)))

def commitment(path, kind, rows):
    case_ids = "\n".join(sorted(x["case_id"] for x in rows)).encode()
    return {"schema": "ARIO-W1B-COMMIT-v1", "kind": kind,
            "sha256": sha(path), "count": len(rows),
            "ids_sha256": hashlib.sha256(case_ids).hexdigest(),
            "note": "File hash only; no time, identity or custody certification"}

def write_exclusive(path, object_):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(object_, f, indent=2, sort_keys=True)
        f.write("\n")

def freeze(args):
    rows = records(args.input)
    if args.kind == "masked":
        check_masked(rows)
    elif args.kind == "predictions":
        check_pred(rows)
    else:
        fail("Unsupported freeze stage")
    packet = commitment(args.input, args.kind, rows)
    write_exclusive(args.output, packet)
    print(json.dumps({"result": "COMMITMENT_WRITTEN", **packet}, sort_keys=True))

def verified(path, proof_path, kind, rows):
    proof = strict_json(Path(proof_path).read_text(encoding="utf-8"))
    expected = commitment(path, kind, rows)
    if any(proof.get(k) != v for k, v in expected.items()):
        fail("Commitment digest, count, ID set or schema mismatch: " + kind)

def score(args):
    masked = records(args.masked)
    pred = records(args.predictions)
    oracle = records(args.private_oracle)
    check_masked(masked)
    check_pred(pred)
    check_oracle(oracle)
    same_ids(masked, pred)
    same_ids(masked, oracle)
    verified(args.masked, args.masked_commit, "masked", masked)
    verified(args.predictions, args.predictions_commit, "predictions", pred)
    lookup = {x["case_id"]: x for x in pred}
    valid = [x for x in oracle if x["adjudication"] == "AGREED"]
    result = {"schema": "ARIO-W1B-POSTREVEAL-AGGREGATE-v1",
              "status": "POST_REVEAL_SCORING_NOT_EXTERNAL_CUSTODY_PROOF",
              "n_all": len(masked), "n_agreed": len(valid),
              "n_disputed_or_undetermined": len(masked)-len(valid),
              "prediction_commit_sha256": sha(args.predictions_commit),
              "masked_commit_sha256": sha(args.masked_commit),
              "axes": {}}
    for axis, field, positive in [
        ("admin", "latent_admin_independent", "LAB_CONDITIONALLY_SEPARATE"),
        ("source", "latent_source_independent", "LAB_CONDITIONALLY_DISTINCT")
    ]:
        usable = [x for x in valid if x[field] is not None]
        dependent = [x for x in usable if x[field] is False]
        independent = [x for x in usable if x[field] is True]
        positive_dep = sum(lookup[x["case_id"]][axis+"_status"] == positive for x in dependent)
        positive_ind = sum(lookup[x["case_id"]][axis+"_status"] == positive for x in independent)
        unknown = sum(lookup[x["case_id"]][axis+"_status"] == "UNKNOWN" for x in usable)
        result["axes"][axis] = {"adjudicated": len(usable), "unresolved_or_null": len(masked)-len(usable),
                                "dependent": len(dependent), "conditional_on_dependent": positive_dep,
                                "conditional_on_dependent_rate": (positive_dep/len(dependent) if dependent else None),
                                "independent": len(independent), "conditional_on_independent": positive_ind,
                                "unknown_on_adjudicated": unknown}
    write_exclusive(args.output, result)
    print(json.dumps({"result": "POST_REVEAL_AGGREGATE_WRITTEN", "n": len(masked),
                      "private_oracle_exported": False}, sort_keys=True))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--kind", choices=("masked", "predictions"), required=True)
    f.add_argument("--input", required=True)
    f.add_argument("--output", required=True)
    s = sub.add_parser("score")
    for name in ("masked", "masked-commit", "predictions", "predictions-commit", "private-oracle", "output"):
        s.add_argument("--"+name, required=True)
    args = parser.parse_args()
    try:
        {"freeze": freeze, "score": score}[args.command](args)
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print("HOLD: " + str(e), file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
