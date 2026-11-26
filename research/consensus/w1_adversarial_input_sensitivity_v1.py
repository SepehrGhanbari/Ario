#!/usr/bin/env python3
"""Bounded, development-only provenance graph input-sensitivity experiment.

Not an independent benchmark, not a provenance authenticator, not an action gate.
Loads the EXACT Git-blob-pinned TB-003 source, from the bytes it hashes.
Run from a checkout of SepehrGhanbari/Ario as:
  python -B research/consensus/w1_adversarial_input_sensitivity_v1.py \
      --json-out /tmp/w1_results.json
Only opt-in --json-out creates a file; no other persistent side effects.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pathlib import Path
import random
import sys
import types

EXPECTED_SHA256 = "71912958bad6db97218ac630cadee6c34c04b286aec99b3f7cda071f8d79f567"
EXPECTED_GIT_BLOB = "4faf010d73219af63c254097e9c135da68d60078"
EXPECTED_BYTES = 26726
MAX_FILE_BYTES = 65536
SCHEMA_VERSION = "W1-INPUT-SENSITIVITY-DEV-1"


def load_pinned_engine(root: Path | None = None):
    root = root or Path(__file__).resolve().parents[2]
    path = root / "implementation" / "witness_provenance_experiment.py"
    with path.open("rb") as f:
        source = f.read(MAX_FILE_BYTES + 1)
    if len(source) > MAX_FILE_BYTES or len(source) != EXPECTED_BYTES:
        raise ValueError("SOURCE_SIZE_MISMATCH")
    if hashlib.sha256(source).hexdigest() != EXPECTED_SHA256:
        raise ValueError("SOURCE_SHA256_MISMATCH")
    blob_hash = hashlib.sha1(b"blob " + str(len(source)).encode("ascii") + b"\0" + source).hexdigest()
    if blob_hash != EXPECTED_GIT_BLOB:
        raise ValueError("SOURCE_GIT_BLOB_MISMATCH")
    # Critical: execute the *same verified bytes*; never reopen path to import.
    module = types.ModuleType("_w1_pinned_tb003")
    module.__file__ = str(path)
    sys.modules[module.__name__] = module  # required by dataclasses
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def build_case(p, shared_source=False, shared_admin=False):
    s = "SYNTHETIC:W1:ONE-SCOPE"
    def n(i, kind, **kw):
        return p.Node(i, kind, s, p.LAB, "FROZEN:" + i, **kw)
    def e(i, u, v, kind, **kw):
        return p.Edge(i, u, v, kind, p.LAB, "FROZEN:" + i, **kw)
    nodes = (
        n("source-a", "SOURCE", object_identity="SRC-A"),
        n("source-b", "SOURCE", object_identity="SRC-B"),
        n("capture-a", "CAPTURE", capture_sequence=1, capture_custodian="origin-a"),
        n("capture-b", "CAPTURE", capture_sequence=2, capture_custodian="origin-b"),
        n("artifact-a", "ARTIFACT"), n("artifact-b", "ARTIFACT"),
        n("store-a", "STORAGE_DOMAIN", object_identity="STORE-A"),
        n("store-b", "STORAGE_DOMAIN", object_identity="STORE-B"),
        n("origin-a", "CUSTODIAN"), n("origin-b", "CUSTODIAN"),
        n("holder-a", "CUSTODIAN"), n("holder-b", "CUSTODIAN"),
        n("actor-a", "CONTROL_PRINCIPAL"), n("actor-b", "CONTROL_PRINCIPAL"),
        n("root-a", "CONTROL_ROOT"), n("root-b", "CONTROL_ROOT"),
    )
    edges = (
        e("cap-a", "artifact-a", "capture-a", "CAPTURED_FROM"),
        e("cap-b", "artifact-b", "capture-b", "CAPTURED_FROM"),
        e("src-a", "capture-a", "source-a", "DERIVED_FROM"),
        e("src-b", "capture-b", "source-a" if shared_source else "source-b", "DERIVED_FROM"),
        e("store-a", "artifact-a", "store-a", "STORED_AT"),
        e("store-b", "artifact-b", "store-b", "STORED_AT"),
        e("hold-a", "artifact-a", "holder-a", "HELD_BY"),
        e("hold-b", "artifact-b", "holder-b", "HELD_BY"),
        e("xfer-a", "origin-a", "holder-a", "TRANSFERRED_TO", subject_artifact_ref="artifact-a", sequence=3),
        e("xfer-b", "origin-b", "holder-b", "TRANSFERRED_TO", subject_artifact_ref="artifact-b", sequence=4),
        e("write-a", "actor-a", "store-a", "CAN_WRITE"),
        e("write-b", "actor-b", "store-b", "CAN_WRITE"),
        e("admin-a", "root-a", "actor-a", "ADMINISTERS"),
        e("admin-b", "root-a" if shared_admin else "root-b", "actor-b", "ADMINISTERS"),
    )
    return p.ProvenanceCase(p.ControlGraph(nodes,edges), s, ("artifact-a","artifact-b"),
                            complete_control_surface=True, complete_source_surface=True,
                            completeness_origin=p.LAB, mutation_sequence=10)


def change_graph(case, nodes=None, edges=None, **fields):
    return replace(case, graph=replace(case.graph,
        nodes=tuple(case.graph.nodes if nodes is None else nodes),
        edges=tuple(case.graph.edges if edges is None else edges)), **fields)


def patch_edge(case, eid, **kw):
    return change_graph(case, edges=tuple(replace(e, **kw) if e.edge_id == eid else e for e in case.graph.edges))


def patch_node(case, nid, **kw):
    return change_graph(case, nodes=tuple(replace(n, **kw) if n.node_id == nid else n for n in case.graph.nodes))


def classify(p, case):
    r = p.evaluate_provenance(case)
    axes = {"storage": r.storage_separation.status, "admin": r.administrative_separation.status,
            "source": r.source_independence.status, "capture": r.capture_order.status,
            "custody": [x.status for x in r.per_witness_custody]}
    if (r.administrative_separation.status == "COMMON_CONTROL_DETECTED" or
        r.source_independence.status == "COMMON_SOURCE_DETECTED" or
        r.storage_separation.status == "SAME_STORAGE_OBJECT"):
        grade = "DEPENDENT"
    elif (r.administrative_separation.status == "LAB_CONDITIONALLY_SEPARATE" and
          r.source_independence.status == "LAB_CONDITIONALLY_DISTINCT" and
          r.storage_separation.status == "LAB_DISTINCT_OBJECTS" and
          r.capture_order.status == "LAB_BEFORE_MUTATION" and
          all(f.status == "LAB_CHAIN_PRESENT" for f in r.per_witness_custody)):
        grade = "CONDITIONAL"
    else:
        grade = "UNKNOWN"
    limits = {"production_custody_authenticity":r.production_custody_authenticity,
              "historical_event_truth":r.historical_event_truth,
              "human_authorization":r.human_authorization,
              "evidence_admission":r.evidence_admission}
    if limits != {"production_custody_authenticity":"NOT_ESTABLISHED",
                  "historical_event_truth":"UNKNOWN",
                  "human_authorization":"NOT_EVALUATED",
                  "evidence_admission":"NOT_EVALUATED"}:
        raise AssertionError("OPERATIONAL_BOUNDARY_CHANGED")
    return {"classification": grade, "axes": axes, "safety":limits,
            "reason_codes":list(r.reason_codes)}


@dataclass(frozen=True)
class Trial:
    name: str
    case: object
    latent_relation: str  # known only to experiment author, not supplied to engine
    expected_report: str  # DEVELOPMENT oracle, not independently adjudicated
    mechanism: str


def build_trials(p):
    sep = build_case(p)
    src = build_case(p, shared_source=True)
    admin = build_case(p, shared_admin=True)
    both = build_case(p, shared_source=True, shared_admin=True)
    hidden_src = patch_edge(src, "src-b", target="source-b")
    hidden_admin = patch_edge(admin,"admin-b",source="root-b")
    hidden_both = patch_edge(patch_edge(both,"src-b",target="source-b"),"admin-b",source="root-b")
    candidate = replace(hidden_src, graph=replace(hidden_src.graph, origin=p.CANDIDATE))
    self_edge = p.Edge("self", "root-a", "actor-b", "ADMINISTERS", p.SELF, "SELF:UNVERIFIED")
    trials = [
      Trial("honest-separate", sep, "SEPARATE_MODELED", "CONDITIONAL", "model-control"),
      Trial("honest-shared-source",src,"SHARED_SOURCE", "DEPENDENT", "positive-control"),
      Trial("hidden-source-false-complete",hidden_src,"SHARED_SOURCE", "CONDITIONAL", "false-completeness"),
      Trial("hidden-source-incomplete",replace(hidden_src,complete_source_surface=False),"SHARED_SOURCE", "UNKNOWN", "honest-incompleteness"),
      Trial("honest-shared-admin",admin,"SHARED_ADMIN", "DEPENDENT", "positive-control"),
      Trial("hidden-admin-false-complete",hidden_admin,"SHARED_ADMIN", "CONDITIONAL", "false-completeness"),
      Trial("hidden-admin-incomplete",replace(hidden_admin,complete_control_surface=False),"SHARED_ADMIN", "UNKNOWN", "honest-incompleteness"),
      Trial("candidate-claims-complete",candidate,"SHARED_SOURCE", "UNKNOWN", "untrusted-origin"),
      Trial("source-alias-identity",patch_node(sep,"source-b",object_identity="SRC-A"),"SHARED_SOURCE_OBJECT", "DEPENDENT", "canonical-object-alias"),
      Trial("duplicate-witness",replace(sep,witness_artifact_refs=("artifact-a","artifact-a")),"DUPLICATE_ARTIFACT", "UNKNOWN", "artifact-alias"),
      Trial("missing-custody-transfer",change_graph(sep,edges=[e for e in sep.graph.edges if e.edge_id != "xfer-b"]),"CUSTODY_UNKNOWN", "UNKNOWN", "missing-transfer"),
      Trial("hidden-source-admin-false-complete",hidden_both,"SHARED_SOURCE_AND_ADMIN", "CONDITIONAL", "dual-hidden-dependency"),
      Trial("honest-shared-source-and-admin",both,"SHARED_SOURCE_AND_ADMIN", "DEPENDENT", "positive-control"),
      Trial("untrusted-self-certification",replace(sep,presented_claims=(self_edge,)),"SEPARATE_MODELED", "CONDITIONAL", "unsupported-extra-claim"),
      Trial("separate-incomplete-control",replace(sep,complete_control_surface=False),"SEPARATE_MODELED", "UNKNOWN", "missing-completeness"),
      Trial("separate-incomplete-source",replace(sep,complete_source_surface=False),"SEPARATE_MODELED", "UNKNOWN", "missing-completeness"),
    ]
    return trials


def serialize_case(case):
    return json.dumps(asdict(case),sort_keys=True,separators=(",", ":"),ensure_ascii=True)


def evaluate_trials(p):
    trials=build_trials(p)
    outcomes=[]
    for tr in trials:
        r=classify(p,tr.case)
        outcomes.append({"case":tr.name,"latent_relation":tr.latent_relation,
                         "mechanism":tr.mechanism,"expected_development":tr.expected_report,
                         "report":r["classification"],"passes_dev_expectation":r["classification"]==tr.expected_report,
                         "axes":r["axes"],"safety":r["safety"],
                         "reason_codes":r["reason_codes"],
                         "reported_graph_sha256":hashlib.sha256(serialize_case(tr.case).encode()).hexdigest()})
    # Control: same reported byte-image maps to identical diagnosis but dissimilar latent truth.
    by_name={tr.name:tr for tr in trials}
    assert serialize_case(by_name["honest-separate"].case) == serialize_case(by_name["hidden-source-false-complete"].case)
    assert serialize_case(by_name["honest-separate"].case) == serialize_case(by_name["hidden-admin-false-complete"].case)
    assert serialize_case(by_name["honest-separate"].case) == serialize_case(by_name["hidden-source-admin-false-complete"].case)
    for item in outcomes:
        if not item["passes_dev_expectation"]:
            raise AssertionError("DEVELOPMENT_REGRESSION:"+item["case"])
    return outcomes


def permutation_checks(p, trials, rounds=12):
    randomizer=random.Random(1729)
    checks=0
    for tr in trials:
        base=classify(p,tr.case)["classification"]
        for _ in range(rounds):
            a=list(tr.case.graph.nodes);b=list(tr.case.graph.edges)
            randomizer.shuffle(a);randomizer.shuffle(b)
            perm=change_graph(tr.case,nodes=a,edges=b)
            assert classify(p,perm)["classification"]==base, tr.name
            checks+=1
    return checks


def run(root=None):
    p=load_pinned_engine(root)
    trials=build_trials(p)
    out=evaluate_trials(p)
    perms=permutation_checks(p,trials)
    hidden=[o for o in out if o["mechanism"] in {"false-completeness","dual-hidden-dependency"}]
    return {"schema_version":SCHEMA_VERSION,"pinned_git_blob":EXPECTED_GIT_BLOB,
            "pinned_sha256":EXPECTED_SHA256,
            "scientific_status":"AUTHOR_BUILT_DEVELOPMENT_FIXTURES_NOT_BLINDED_OR_INDEPENDENT",
            "aggregate":{"designed_trials":len(out),"development_expectation_matches":sum(o["passes_dev_expectation"] for o in out),
                         "permutation_checks":perms,"hidden_dependency_conditional":sum(o["report"]=="CONDITIONAL" for o in hidden),
                         "hidden_dependency_trials":len(hidden)},"trials":out}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json-out",type=Path,help="explicit optional output to an existing directory")
    args=ap.parse_args()
    result=run()
    payload=json.dumps(result,indent=2,sort_keys=True,ensure_ascii=True)+"\n"
    if args.json_out is not None:
        if not args.json_out.parent.is_dir():
            ap.error("--json-out parent must already exist")
        if args.json_out.exists():
            ap.error("--json-out must not overwrite existing evidence")
        with args.json_out.open("x",encoding="utf-8") as f:
            f.write(payload)
    print(json.dumps(result["aggregate"],sort_keys=True))

if __name__=="__main__":
    main()
