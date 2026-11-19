#!/usr/bin/env python3
"""W4: source-pinned aggregate re-audit of an archived Ario retrieval RESULT file.
This checks structure and pre-recorded labels, NOT gold-label correctness or live XERJ.
No network, no memory writes, no production integration.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys

EXPECTED_SHA256 = "20a0dba360de42d8a7659496728cbdcad2e0a48fb728eb5e04eca2f8cbbb21de"
EXPECTED_FAMILIES = {"exact": 25, "paraphrase": 25, "update": 15, "distractor": 10}

def fail(s):
    raise ValueError(s)

def get_rows(item, label):
    rows = item.get("rows")
    if not isinstance(rows, list) or len(rows) != 75:
        fail(f"{label}: expected exactly 75 rows")
    seen = set()
    output = {}
    for row in rows:
        if type(row) is not dict:
            fail(f"{label}: nonobject row")
        key = row.get("id")
        if type(key) is not str or not key or key in seen:
            fail(f"{label}: malformed or repeated id {key!r}")
        seen.add(key)
        for field in ("hit1", "hit5", "gold_hit1", "gold_hit5"):
            if type(row.get(field)) is not bool:
                fail(f"{label}/{key}: malformed {field}")
        if row.get("correct_first") not in (True, False, None):
            fail(f"{label}/{key}: malformed correct_first")
        hits = row.get("hit_ids")
        if not isinstance(hits, list) or len(hits) > 5 or len(hits) != len(set(hits)):
            fail(f"{label}/{key}: invalid or duplicate top-5 hits")
        if row["hit1"] and not row["hit5"]:
            fail(f"{label}/{key}: hit1 but not hit5")
        output[key] = row
    return output

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive_json", type=Path, help="owner's archived 2026-11-14 R1 results JSON")
    ap.add_argument("--allow-noncanonical", action="store_true", help="disable exact source hash check for diagnostic testing only")
    args = ap.parse_args()
    raw = args.archive_json.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if not args.allow_noncanonical and digest != EXPECTED_SHA256:
        fail(f"archived source SHA256 mismatch: {digest}")
    data = json.loads(raw)
    ar = {"sqlite_fts5_all": data["sqlite"]["fts5_or_all"],
          "sqlite_fts5_stop": data["sqlite"]["fts5_or_stop"],
          **{f"archived_xerj_{k}":v for k,v in data["archived_xerj"].items()}}
    rows = {label:get_rows(v,label) for label,v in ar.items()}
    reference = rows["sqlite_fts5_all"]
    type_counts = dict(collections.Counter(r.get("type") for r in reference.values()))
    if type_counts != EXPECTED_FAMILIES:
        fail(f"incorrect question-group denominators: {type_counts}")
    for label,by_id in rows.items():
        if set(reference) != set(by_id) or any(by_id[k].get("type") != reference[k].get("type") for k in reference):
            fail(f"{label}: mismatched questions or family labels")
    groups = {}
    for label,by_id in rows.items():
        update = [r for r in by_id.values() if r["type"] == "update"]
        groups[label] = {
            "hit1_n_of_75": sum(r["hit1"] for r in by_id.values()),
            "hit5_n_of_75": sum(r["hit5"] for r in by_id.values()),
            "exact_hit5_of_25": sum(r["hit5"] for r in by_id.values() if r["type"] == "exact"),
            "paraphrase_hit5_of_25": sum(r["hit5"] for r in by_id.values() if r["type"] == "paraphrase"),
            "update_hit5_of_15": sum(r["hit5"] for r in update),
            "update_newest_first_of_15": sum(r["correct_first"] is True for r in update),
            "distractor_hit5_of_10": sum(r["hit5"] for r in by_id.values() if r["type"] == "distractor"),
        }
    pairwise={}
    for a,b in (("archived_xerj_semantic","sqlite_fts5_all"),
                ("archived_xerj_hybrid_recency","archived_xerj_semantic")):
        aa,bb=rows[a],rows[b]
        pairwise[a+"_vs_"+b]={
            "a_only_hit5":sum(aa[k]["hit5"] and not bb[k]["hit5"] for k in reference),
            "b_only_hit5":sum(bb[k]["hit5"] and not aa[k]["hit5"] for k in reference),
        }
    never=[k for k in reference if not any(by_id[k]["hit5"] for by_id in rows.values())]
    result={"status":"ARCHIVED_RESULTS_REAUDITED_NOT_LIVE_ENGINES_OR_INDEPENDENT_GOLD",
            "source_sha256":digest,"source_reported_dataset_sha256":data.get("dataset_sha256"),
            "question_count":len(reference),"question_families":type_counts,"metrics":groups,
            "paired_top5_disagreements":pairwise,"never_hit5_ids":never,
            "caution":"Correctness flags were supplied by archived benchmark, not independently adjudicated; historic XERJ and live SQLite ran on different hosts/versions. No causal, external-world, security or production claims."}
    print(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, json.JSONDecodeError, TypeError) as e:
        print("HOLD: "+str(e),file=sys.stderr)
        raise SystemExit(2)
