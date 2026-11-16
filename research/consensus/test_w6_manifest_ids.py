#!/usr/bin/env python3
"""W6 read-only metamorphic check using pinned source archive JSON inputs.
Test fixtures are copied in RAM: never rewrite published source or local snapshot.
"""
import copy
import json
from pathlib import Path
import sys

import w6_verify_research_release_git_ids as w6

root=Path(__file__).parent
m=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
c=json.loads((root/"coverage.json").read_text(encoding="utf-8"))
commit=json.loads((root/"commit.json").read_text(encoding="utf-8"))
tree=json.loads((root/"tree.json").read_text(encoding="utf-8"))

results={}
found=w6.check(m,c,commit,tree)
assert found["status"]=="TREE_METADATA_ONLY_FAIL",found
assert len(found["error_codes"])==2,found
results["original_two_bad_tree_fields"]="EXPECTED_RED"

fixed_m=copy.deepcopy(m)
fixed_c=copy.deepcopy(c)
fixed_m["source_tree_sha"]=commit["tree"]["sha"]
fixed_c["source_git_tree"]=commit["tree"]["sha"]
positive=w6.check(fixed_m,fixed_c,commit,tree)
assert positive["status"]=="PASS",positive
results["metadata_only_repair_in_memory"]="GREEN"

corrupt=copy.deepcopy(fixed_m)
corrupt["included"][0]["git_blob_sha1"]="0"*40
bad=w6.check(corrupt,fixed_c,commit,tree)
assert bad["status"]=="FAIL" and any(x.startswith("BLOB_MISMATCH:") for x in bad["error_codes"]),bad
results["tampered_git_blob"]="EXPECTED_RED"

missing=copy.deepcopy(fixed_m)
missing["included"]=missing["included"][:-1]
bad=w6.check(missing,fixed_c,commit,tree)
assert bad["status"]=="FAIL" and "PATH_SET_MISMATCH" in bad["error_codes"],bad
results["missing_manifest_path"]="EXPECTED_RED"

sliced=copy.deepcopy(tree)
sliced["truncated"]=True
bad=w6.check(fixed_m,fixed_c,commit,sliced)
assert bad["status"]=="FAIL" and "TREE_OBJECT_MISMATCH_OR_TRUNCATED" in bad["error_codes"],bad
results["truncated_git_tree"]="EXPECTED_RED"

mismatched=copy.deepcopy(fixed_m)
mismatched["excluded"][0]["original_bytes"]+=1
bad=w6.check(mismatched,fixed_c,commit,tree)
assert bad["status"]=="FAIL" and any(x.startswith("SIZE_MISMATCH:") for x in bad["error_codes"]),bad
results["altered_source_file_size"]="EXPECTED_RED"

print(json.dumps({"status":"W6_METAMORPHIC_PASS","cases":len(results),
"actual_git_tree_sha":commit["tree"]["sha"],"cases_detail":results},sort_keys=True))
