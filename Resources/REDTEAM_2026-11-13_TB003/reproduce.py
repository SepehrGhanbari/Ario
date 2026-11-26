#!/usr/bin/env python3
"""Reproduce exploratory TB-003 adversarial observations. Never writes repository files.

Run from any directory:
  python -B Resources/REDTEAM_2026-11-13_TB003/reproduce.py
  python -B Resources/REDTEAM_2026-11-13_TB003/reproduce.py --file implementation/witness_provenance_experiment.py
The --file variant must contain the exact pinned historical source bytes.
"""
from __future__ import annotations
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import types
import urllib.request

REV = "972a4199e5c52e1bdab559be623949c7d7a24b69"
URL = "https://raw.githubusercontent.com/SepehrGhanbari/Ario/" + REV + "/implementation/witness_provenance_experiment.py"
SHA256 = "71912958bad6db97218ac630cadee6c34c04b286aec99b3f7cda071f8d79f567"
BLOB_SHA1 = "4faf010d73219af63c254097e9c135da68d60078"

def source_module(local_path):
    raw = Path(local_path).read_bytes() if local_path else urllib.request.urlopen(URL, timeout=15).read()
    got_sha = hashlib.sha256(raw).hexdigest()
    got_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if (got_sha, got_blob) != (SHA256, BLOB_SHA1):
        raise RuntimeError("SOURCE_HASH_MISMATCH: " + got_sha + " / " + got_blob)
    m = types.ModuleType("ario_tb003_redteam_pinned")
    sys.modules[m.__name__] = m
    exec(compile(raw.decode("utf-8"), URL if not local_path else local_path, "exec"), m.__dict__)
    return m

def custody_probes(p):
    L = p.LAB; S = "REDTEAM-SCOPE"
    def n(name, kind, **kw): return p.Node(name, kind, S, L, "synthetic", **kw)
    def e(name, a, b, kind, **kw): return p.Edge(name, a, b, kind, L, "synthetic", **kw)
    nodes = [
        n("A","ARTIFACT"), n("B","ARTIFACT"),
        n("CAPA","CAPTURE",capture_sequence=0,capture_custodian="P1"),
        n("CAPB","CAPTURE",capture_sequence=0,capture_custodian="P2"),
        n("P1","CUSTODIAN"), n("P2","CUSTODIAN"), n("P3","CUSTODIAN"),
        n("DA","STORAGE_DOMAIN",object_identity="disk-a"),
        n("DB","STORAGE_DOMAIN",object_identity="disk-b"),
        n("SA","SOURCE",object_identity="origin-a"),
        n("SB","SOURCE",object_identity="origin-b"),
        n("ROOT","CONTROL_PRINCIPAL"),
    ]
    edges = [
        e("capA","A","CAPA","CAPTURED_FROM"), e("capB","B","CAPB","CAPTURED_FROM"),
        e("holdA","A","P1","HELD_BY"), e("holdB","B","P2","HELD_BY"),
        e("storeA","A","DA","STORED_AT"), e("storeB","B","DB","STORED_AT"),
        e("srcA","CAPA","SA","DERIVED_FROM"), e("srcB","CAPB","SB","DERIVED_FROM"),
    ]
    depart = e("depart","P1","P3","TRANSFERRED_TO",subject_artifact_ref="A",sequence=2)
    forward = e("forward","P3","P2","TRANSFERRED_TO",subject_artifact_ref="A",sequence=3)
    def probe(name, extra=(), holder=None, compromised=(), controls=(), complete=True, node_set=None):
        es = [replace(x,target=holder) if x.edge_id == "holdA" and holder else x for x in edges]
        c = p.ProvenanceCase(p.ControlGraph(tuple(node_set if node_set is not None else nodes),tuple(es+list(extra)+list(controls))),S,("A","B"),complete,True,L,mutation_sequence=4,compromised_node_ids=tuple(compromised))
        r=p.evaluate_provenance(c)
        return {"id":name,"custody_A":r.per_witness_custody[0].status,"custody_reason":r.per_witness_custody[0].reason,
                "admin":r.administrative_separation.status,"source":r.source_independence.status,
                "production_auth":r.production_custody_authenticity,"evidence_admission":r.evidence_admission}
    return [
        probe("C01_clean"),
        probe("C02_departure",extra=[depart]),
        probe("C03_departure_compromised",extra=[depart],compromised=["P3"]),
        probe("C04_holder_is_P3",extra=[depart],holder="P3"),
        probe("C05_holder_P3_compromised",extra=[depart],holder="P3",compromised=["P3"]),
        probe("C06_forward_after_holder",extra=[depart,forward],holder="P3"),
        probe("C07_forward_compromised",extra=[depart,forward],holder="P3",compromised=["P2"]),
        probe("C08_missing_transfer",holder="P3"),
        probe("C09_common_controller",controls=[e("writeA","ROOT","DA","CAN_WRITE"),e("writeB","ROOT","DB","CAN_WRITE")]),
        probe("C10_incomplete_control",complete=False),
        probe("C11_common_source",node_set=[replace(x,object_identity="origin-a") if x.node_id=="SB" else x for x in nodes]),
    ]

def alias_probes(p):
    L=p.LAB; S="ALIAS-TEST"
    def n(name,kind,oid=None,seq=None,cust=None): return p.Node(name,kind,S,L,"synthetic",object_identity=oid,capture_sequence=seq,capture_custodian=cust)
    def e(name,a,b,kind,origin=L): return p.Edge(name,a,b,kind,origin,"synthetic")
    nodes=[n("A","ARTIFACT"),n("B","ARTIFACT"),
           n("CAPA","CAPTURE",seq=0,cust="CA"),n("CAPB","CAPTURE",seq=0,cust="CB"),
           n("CA","CUSTODIAN"),n("CB","CUSTODIAN"),
           n("DA","STORAGE_DOMAIN","disk1"),n("DB","STORAGE_DOMAIN","disk2"),
           n("P1","SOURCE","X"),n("P2","SOURCE","X"),
           n("Q","SOURCE","Y"),n("R","SOURCE","Z")]
    edges=[e("capA","A","CAPA","CAPTURED_FROM"),e("capB","B","CAPB","CAPTURED_FROM"),
           e("heldA","A","CA","HELD_BY"),e("heldB","B","CB","HELD_BY"),
           e("storeA","A","DA","STORED_AT"),e("storeB","B","DB","STORED_AT"),
           e("srcA","CAPA","P1","DERIVED_FROM"),e("srcB","CAPB","Q","DERIVED_FROM"),
           e("alias_ancestry","P2","R","DERIVED_FROM"),e("b_ancestry","Q","R","DERIVED_FROM")]
    def probe(name,ns=None,es=None,complete=True):
        c=p.ProvenanceCase(p.ControlGraph(tuple(nodes if ns is None else ns),tuple(edges if es is None else es)),S,("A","B"),complete,complete,L)
        r=p.evaluate_provenance(c)
        return {"id":name,"source":r.source_independence.status,"source_reason":r.source_independence.reason,
                "admin":r.administrative_separation.status,"custody_A":r.per_witness_custody[0].status,
                "evidence_admission":r.evidence_admission}
    return [
      probe("A01_distributed_alias"),
      probe("A02_direct_identity",es=[replace(x,target="P2") if x.edge_id=="srcB" else x for x in edges]),
      probe("A03_direct_ancestry",es=[replace(x,source="P1") if x.edge_id=="alias_ancestry" else x for x in edges]),
      probe("A04_untrusted_ancestry",es=[replace(x,origin=p.SELF) if x.edge_id=="alias_ancestry" else x for x in edges]),
      probe("A05_incomplete_surface",complete=False),
      probe("A06_permutation",ns=list(reversed(nodes)),es=list(reversed(edges))),
    ]

EXPECTED = {
 "C01_clean":("LAB_CHAIN_PRESENT","LAB_CONDITIONALLY_SEPARATE","LAB_CONDITIONALLY_DISTINCT"),
 "C02_departure":("LAB_CHAIN_PRESENT","LAB_CONDITIONALLY_SEPARATE","LAB_CONDITIONALLY_DISTINCT"),
 "C03_departure_compromised":("LAB_CHAIN_PRESENT","LAB_CONDITIONALLY_SEPARATE","LAB_CONDITIONALLY_DISTINCT"),
 "C04_holder_is_P3":("LAB_CHAIN_PRESENT","LAB_CONDITIONALLY_SEPARATE","LAB_CONDITIONALLY_DISTINCT"),
 "C05_holder_P3_compromised":("LAB_CHAIN_PRESENT","COMPROMISED_BY_SCENARIO","LAB_CONDITIONALLY_DISTINCT"),
 "C06_forward_after_holder":("LAB_CHAIN_PRESENT","LAB_CONDITIONALLY_SEPARATE","LAB_CONDITIONALLY_DISTINCT"),
 "C07_forward_compromised":("LAB_CHAIN_PRESENT","COMPROMISED_BY_SCENARIO","LAB_CONDITIONALLY_DISTINCT"),
 "C08_missing_transfer":("UNKNOWN","UNKNOWN","UNKNOWN"),
 "C09_common_controller":("LAB_CHAIN_PRESENT","COMMON_CONTROL_DETECTED","LAB_CONDITIONALLY_DISTINCT"),
 "C10_incomplete_control":("LAB_CHAIN_PRESENT","UNKNOWN","LAB_CONDITIONALLY_DISTINCT"),
 "C11_common_source":("LAB_CHAIN_PRESENT","LAB_CONDITIONALLY_SEPARATE","COMMON_SOURCE_DETECTED"),
 "A01_distributed_alias":("LAB_CHAIN_PRESENT","LAB_CONDITIONALLY_SEPARATE","LAB_CONDITIONALLY_DISTINCT"),
 "A02_direct_identity":("LAB_CHAIN_PRESENT","LAB_CONDITIONALLY_SEPARATE","COMMON_SOURCE_DETECTED"),
 "A03_direct_ancestry":("LAB_CHAIN_PRESENT","LAB_CONDITIONALLY_SEPARATE","COMMON_SOURCE_DETECTED"),
 "A04_untrusted_ancestry":("LAB_CHAIN_PRESENT","UNKNOWN","UNKNOWN"),
 "A05_incomplete_surface":("LAB_CHAIN_PRESENT","UNKNOWN","UNKNOWN"),
 "A06_permutation":("LAB_CHAIN_PRESENT","LAB_CONDITIONALLY_SEPARATE","LAB_CONDITIONALLY_DISTINCT"),
}

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--file",help="Pinned evaluator source file; otherwise fetched from pinned public commit")
    args=pa.parse_args()
    p=source_module(args.file)
    rows=custody_probes(p)+alias_probes(p)
    problems=[]
    for row in rows:
        actual=(row["custody_A"],row["admin"],row["source"])
        if actual != EXPECTED[row["id"]]: problems.append({"case":row["id"],"expected":EXPECTED[row["id"]],"actual":actual})
        if row["evidence_admission"] != "NOT_EVALUATED": problems.append({"case":row["id"],"unexpected_admission":row["evidence_admission"]})
    print(json.dumps({"study":"EXPLORATORY_NOT_PREREGISTERED","pinned_commit":REV,"source_sha256":SHA256,
                      "result":"OBSERVATIONS_REPRODUCED" if not problems else "OBSERVATIONS_CHANGED",
                      "n":len(rows),"problems":problems,"cases":rows},ensure_ascii=False,indent=2))
    return 0 if not problems else 1

if __name__ == "__main__":
    raise SystemExit(main())
