"""AEC-Bench v0.1: deterministic synthetic comparative policy benchmark."""
from __future__ import annotations
import argparse, json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

BENCHMARK_VERSION = "AEC-Bench-0.1"
METHODS = ("raw_relay_count", "majority_vote", "hash_integrity_only", "ario_typed_policy")

@dataclass(frozen=True)
class Case:
    case_id: str
    family: str
    reports: tuple[dict, ...]
    expected_roots: Optional[int]
    expected_claim_status: str
    expected_scope_status: str = "IN_SCOPE"

def r(agent, root, claim, *, scope="S", schema="1.0", digest_valid=True):
    return {"agent":agent,"source_root":root,"claim":claim,"scope":scope,
            "schema":schema,"digest_valid":digest_valid}

def corpus():
    return (
      Case("AEC01_SHARED_ROOT_5","dependence",tuple(r(f"A{i}","ROOT-X","SUPPORTS") for i in range(5)),1,"UNKNOWN"),
      Case("AEC02_INDEPENDENT_ROOTS_2","independence",(r("A","ROOT-A","SUPPORTS"),r("B","ROOT-B","SUPPORTS")),2,"UNKNOWN"),
      Case("AEC03_MINORITY_SUPPORTED","consensus_laundering",tuple(r(f"A{i}","ROOT-X","UNSUPPORTED") for i in range(4))+(r("MINORITY","ROOT-Y","SUPPORTS"),),2,"CONTESTED"),
      Case("AEC04_MISSING_ANCESTRY","lossy_provenance",(r("A",None,"SUPPORTS"),r("B",None,"SUPPORTS")),None,"UNKNOWN"),
      Case("AEC05_CONFLICTING_ROOTS","conflict",(r("A","ROOT-A","SUPPORTS"),r("B","ROOT-B","CONTRADICTS")),2,"CONTESTED"),
      Case("AEC06_SCHEMA_DOWNGRADE","schema",(r("A","ROOT-A","SUPPORTS",schema="99.0"),),1,"REJECTED"),
      Case("AEC07_SCOPE_MISMATCH","scope",(r("A","ROOT-A","SUPPORTS",scope="OTHER"),),1,"REJECTED","OUT_OF_SCOPE"),
      Case("AEC08_HASH_WITHOUT_AUTH","integrity_vs_authenticity",(r("A","ROOT-A","SUPPORTS"),),1,"UNKNOWN"),
      Case("AEC09_INVALID_DIGEST","integrity",(r("A","ROOT-A","SUPPORTS",digest_valid=False),),1,"REJECTED"),
      Case("AEC10_REPLAYED_AGENT","replay",(r("A","ROOT-A","SUPPORTS"),r("A","ROOT-A","SUPPORTS")),1,"UNKNOWN"),
      Case("AEC11_SHARED_ANCESTOR","provenance_laundering",(r("A","ROOT-Z","SUPPORTS"),r("B","ROOT-Z","SUPPORTS"),r("C","ROOT-Z","SUPPORTS")),1,"UNKNOWN"),
      Case("AEC12_VALID_CONTROL","false_rejection_control",(r("A","ROOT-A","SUPPORTS"),),1,"UNKNOWN"),
    )

def evaluate(case, method):
    reports=case.reports
    if method=="raw_relay_count":
        claims=[x["claim"] for x in reports]
        status="SUPPORTED" if claims.count("SUPPORTS")>len(claims)/2 else ("CONTRADICTED" if claims.count("CONTRADICTS")>len(claims)/2 else "UNKNOWN")
        return {"roots":len(reports),"claim_status":status,"scope_status":"IN_SCOPE"}
    if method=="majority_vote":
        claims=[x["claim"] for x in reports]
        winner=max(("SUPPORTS","CONTRADICTS","UNSUPPORTED"),key=claims.count)
        return {"roots":len(reports),"claim_status":winner if claims.count(winner)>len(claims)/2 else "UNKNOWN","scope_status":"IN_SCOPE"}
    if method=="hash_integrity_only":
        return {"roots":None,"claim_status":"UNKNOWN" if all(x["digest_valid"] for x in reports) else "REJECTED","scope_status":"IN_SCOPE"}
    if method!="ario_typed_policy": raise ValueError(method)
    if any(not x["digest_valid"] for x in reports): return {"roots":None,"claim_status":"REJECTED","scope_status":"IN_SCOPE"}
    if any(x["schema"].split(".",1)[0]!="1" for x in reports): return {"roots":None,"claim_status":"REJECTED","scope_status":"IN_SCOPE"}
    if any(x["scope"]!="S" for x in reports): return {"roots":None,"claim_status":"REJECTED","scope_status":"OUT_OF_SCOPE"}
    unique={}
    for x in reports: unique.setdefault(x["agent"],x)
    roots={x["source_root"] for x in unique.values()}
    count=None if None in roots else len(roots)
    claims={x["claim"] for x in unique.values()}
    status="CONTESTED" if {"SUPPORTS","CONTRADICTS"}.issubset(claims) else "UNKNOWN"
    return {"roots":count,"claim_status":status,"scope_status":"IN_SCOPE"}

def score():
    cases=corpus(); result={}
    for method in METHODS:
        rows=[]
        for c in cases:
            obs=evaluate(c,method)
            root_ok=None if c.expected_roots is None else obs["roots"]==c.expected_roots
            rows.append({"case_id":c.case_id,"family":c.family,**obs,
              "root_count_correct":root_ok,
              "claim_disposition_correct":obs["claim_status"]==c.expected_claim_status,
              "scope_disposition_correct":obs["scope_status"]==c.expected_scope_status})
        known=[x for x in rows if x["root_count_correct"] is not None]
        result[method]={"cases":rows,
          "root_count_accuracy":sum(x["root_count_correct"] for x in known)/len(known),
          "claim_disposition_accuracy":sum(x["claim_disposition_correct"] for x in rows)/len(rows),
          "scope_disposition_accuracy":sum(x["scope_disposition_correct"] for x in rows)/len(rows),
          "false_independence_inflations":sum(x["roots"] is not None and c.expected_roots is not None and x["roots"]>c.expected_roots for x,c in zip(rows,cases)),
          "unsupported_claim_promotions":sum(x["claim_status"] in ("SUPPORTED","CONTRADICTED") and c.expected_claim_status in ("UNKNOWN","CONTESTED","REJECTED") for x,c in zip(rows,cases))}
    return {"benchmark":BENCHMARK_VERSION,"corpus_kind":"SYNTHETIC_DETERMINISTIC","case_count":len(cases),"methods":result,
      "limitations":["Ario policy is a benchmark-side candidate, not a deployed service call.","Baselines are deliberately simple policies, not full PROV-O, TMS/ATMS or RAG implementations.","Root labels are synthetic oracle annotations; real-world independence cannot be inferred from labels alone.","No external authentication, truth verification, privacy leakage or human adjudication is tested.","Twelve cases are a pilot smoke corpus, not the proposed 120-case EAC-Bench study."]}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--output",type=Path); a=p.parse_args()
    out=json.dumps(score(),indent=2,sort_keys=True)+"\n"
    if a.output: a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(out,encoding="utf-8")
    print(out)
if __name__=="__main__": main()
