#!/usr/bin/env python3
"""W1 synthetic *development rehearsal*, NOT independent/blind validation.

Uses the unmodified Ario TB-003 evaluator from a caller-supplied, pinned file.
Does not load secrets, connect to GitHub, or modify Ario files.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys
import types

EVALUATOR_BLOB_SHA1 = "4faf010d73219af63c254097e9c135da68d60078"
EVALUATOR_MAIN_COMMIT = "2e7f83c6c7518012bed7fedfb12103ce9b7222ea"

# Ten deterministic renamings/order permutations per family are repetitions,
# NOT 80 independent data points; no inferential significance test is justified.
FAMILIES = (
    "independent_complete",
    "visible_shared_admin",
    "visible_shared_source",
    "visible_shared_both",
    "hidden_shared_admin",
    "hidden_shared_source",
    "hidden_shared_both",
    "independent_incomplete",
)


def descriptors():
    return [
        {"id": f"W1-{family}-{seed:02d}", "family": family, "seed": seed,
         "latent_shared_admin": family in {"visible_shared_admin", "visible_shared_both", "hidden_shared_admin", "hidden_shared_both"},
         "latent_shared_source": family in {"visible_shared_source", "visible_shared_both", "hidden_shared_source", "hidden_shared_both"},
         "visible_shared_admin": family in {"visible_shared_admin", "visible_shared_both"},
         "visible_shared_source": family in {"visible_shared_source", "visible_shared_both"},
         "declared_complete": family != "independent_incomplete"}
        for family in FAMILIES for seed in range(10)
    ]


def load_pinned_evaluator(path: Path):
    data = path.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    if blob != EVALUATOR_BLOB_SHA1:
        raise ValueError(f"Evaluator mismatch: Git blob SHA1 {blob}, wanted {EVALUATOR_BLOB_SHA1}. Aborting.")
    module = types.ModuleType("w1_pinned_witness_provenance")
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def make_case(p, d):
    scope = "SYNTHETIC:W1:" + d["id"]
    suffix = str(d["seed"])
    def n(name):
        return name + suffix
    def node(name, kind, **kwargs):
        return p.Node(n(name), kind, scope, p.LAB, "LAB-W1-" + n(name), **kwargs)
    def edge(name, src, dst, kind):
        return p.Edge(n(name), n(src), n(dst), kind, p.LAB, "LAB-W1-" + n(name))

    nodes = [
        node("src_a", "SOURCE", object_identity="REAL_SOURCE_A_" + suffix),
        node("src_b", "SOURCE", object_identity="REAL_SOURCE_B_" + suffix),
        node("cap_a", "CAPTURE", capture_sequence=1, capture_custodian=n("cust_a")),
        node("cap_b", "CAPTURE", capture_sequence=2, capture_custodian=n("cust_b")),
        node("art_a", "ARTIFACT"), node("art_b", "ARTIFACT"),
        node("store_a", "STORAGE_DOMAIN", object_identity="DISK_A_" + suffix),
        node("store_b", "STORAGE_DOMAIN", object_identity="DISK_B_" + suffix),
        node("cust_a", "CUSTODIAN"), node("cust_b", "CUSTODIAN"),
        node("principal_a", "CONTROL_PRINCIPAL"), node("principal_b", "CONTROL_PRINCIPAL"),
        node("root_a", "CONTROL_ROOT"), node("root_b", "CONTROL_ROOT"),
    ]
    source_b = "src_a" if d["visible_shared_source"] else "src_b"
    root_b = "root_a" if d["visible_shared_admin"] else "root_b"
    edges = [
        edge("capture_a", "art_a", "cap_a", "CAPTURED_FROM"),
        edge("capture_b", "art_b", "cap_b", "CAPTURED_FROM"),
        edge("origin_a", "cap_a", "src_a", "DERIVED_FROM"),
        edge("origin_b", "cap_b", source_b, "DERIVED_FROM"),
        edge("storage_a", "art_a", "store_a", "STORED_AT"),
        edge("storage_b", "art_b", "store_b", "STORED_AT"),
        edge("held_a", "art_a", "cust_a", "HELD_BY"),
        edge("held_b", "art_b", "cust_b", "HELD_BY"),
        edge("write_a", "principal_a", "store_a", "CAN_WRITE"),
        edge("write_b", "principal_b", "store_b", "CAN_WRITE"),
        edge("admin_a", "root_a", "principal_a", "ADMINISTERS"),
        edge("admin_b", root_b, "principal_b", "ADMINISTERS"),
    ]
    rng = random.Random(911 + d["seed"])
    rng.shuffle(nodes)
    rng.shuffle(edges)
    return p.ProvenanceCase(
        graph=p.ControlGraph(tuple(nodes), tuple(edges), p.LAB),
        scope=scope, witness_artifact_refs=(n("art_a"), n("art_b")),
        complete_control_surface=d["declared_complete"],
        complete_source_surface=d["declared_complete"],
        completeness_origin=p.LAB,
        mutation_sequence=10,
    )


def inspect_case(p, d):
    case = make_case(p, d)
    r = p.evaluate_provenance(case)
    admin = r.administrative_separation.status
    source = r.source_independence.status
    projected = (admin == "LAB_CONDITIONALLY_SEPARATE" and source == "LAB_CONDITIONALLY_DISTINCT")
    true_independent_in_synthetic_world = not (d["latent_shared_admin"] or d["latent_shared_source"])
    return {
        "id": d["id"], "family": d["family"], "seed": d["seed"],
        "visible_shared_admin": d["visible_shared_admin"],
        "visible_shared_source": d["visible_shared_source"],
        "declared_complete": d["declared_complete"],
        "latent_shared_admin": d["latent_shared_admin"],
        "latent_shared_source": d["latent_shared_source"],
        "observed_admin": admin, "observed_source": source,
        "observed_lab_conditional_both": projected,
        "synthetic_world_independent": true_independent_in_synthetic_world,
        "model_premise_mismatch": projected and not true_independent_in_synthetic_world,
        "non_authorizing": (r.production_custody_authenticity == "NOT_ESTABLISHED" and
                             r.human_authorization == "NOT_EVALUATED" and
                             r.evidence_admission == "NOT_EVALUATED"),
    }


def self_check():
    ds = descriptors()
    assert len(ds) == 80 and len({x["id"] for x in ds}) == 80
    assert Counter(x["family"] for x in ds) == {family: 10 for family in FAMILIES}
    assert len([x for x in ds if x["latent_shared_admin"] or x["latent_shared_source"]]) == 60
    assert len([x for x in ds if not x["latent_shared_admin"] and not x["latent_shared_source"]]) == 20
    assert len([x for x in ds if x["declared_complete"] is False]) == 10
    assert descriptors() == ds
    return {"self_check": "PASS", "case_count": 80, "logical_families": len(FAMILIES),
            "repetitions_per_family": 10, "evaluation": "NOT_EXECUTED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    base = self_check()
    if args.self_check and not args.source_file:
        print(json.dumps(base, indent=2))
        return 0
    if args.source_file is None:
        parser.error("--source-file must be supplied for actual Ario evaluator execution")
    p = load_pinned_evaluator(args.source_file)
    rows = [inspect_case(p, d) for d in descriptors()]
    results = {
        "status": "SYNTHETIC_VISIBLE_DEVELOPMENT_REHEARSAL_NOT_BLIND",
        "main_commit_pinned": EVALUATOR_MAIN_COMMIT,
        "evaluator_git_blob_sha1": EVALUATOR_BLOB_SHA1,
        "cases": len(rows),
        "logical_families": len(FAMILIES),
        "non_authorizing_all": all(x["non_authorizing"] for x in rows),
        "model_premise_mismatch_count": sum(x["model_premise_mismatch"] for x in rows),
        "family_summary": {f: {
            "count": 10,
            "admin_status": dict(Counter(x["observed_admin"] for x in rows if x["family"] == f)),
            "source_status": dict(Counter(x["observed_source"] for x in rows if x["family"] == f)),
            "premise_mismatch": sum(x["model_premise_mismatch"] for x in rows if x["family"] == f),
        } for f in FAMILIES},
        "limitations": [
            "Same author designed both fixture and latent world; no independent oracle or blind holdout.",
            "Ten deterministic renamings per family are not independent empirical samples.",
            "A conditional result under a false lab-completeness assumption is not a violation of the existing TB-003 contract.",
            "No historical authentication or production authority measured.",
        ],
        "rows": rows,
    }
    encoded = json.dumps(results, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
        print(f"Written rehearsal report: {args.output}")
    else:
        print(encoded)
    return 0 if results["non_authorizing_all"] else 2


if __name__ == "__main__":
    raise SystemExit(main())