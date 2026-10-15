"""Deterministic W4-C snapshot *shape fingerprints*, NOT trust signatures."""
import json
from dataclasses import replace
from pathlib import Path
from hashlib import sha256
from test_w4c_distributed_lab import registry,enrollment
import w4c_distributed_lab as w4c

HERE=Path(__file__).resolve().parent

def snapshot_array(view):
    return [view.revision,view.root_ref,view.epoch,view.checked_at,view.expires_at,
            view.frozen,view.predecessor_digest,
            [[e.key_id,e.public_key.hex(),e.witness_id,e.source_id,e.custodian_id,
              e.controller_id,e.control_group_id,e.epoch,e.permitted_action] for e in view.enrollments],
            [[r.key_id,r.revoked_at,r.reason_code] for r in view.revocations]]

s=registry()
cases={
 "TWO_DISTINCT_DECLARATIONS": s,
 "FROZEN": replace(s,frozen=True),
 "REVOCATION_AT_110": replace(s,revocations=(w4c.Revocation(enrollment(0).key_id,110,"COMPROMISED"),)),
 "DIVERGENT_NEW_ROOT": replace(s,root_ref="SELF_CLAIMED_NEW_ROOT"),
 "REORDERED_RECORDS": replace(s,enrollments=tuple(reversed(s.enrollments))),
}
rows=[]
for name,v in cases.items():
    a=snapshot_array(v)
    calc=sha256(json.dumps(a,separators=(',',':'),ensure_ascii=True).encode('ascii')).hexdigest()
    assert calc==w4c._digest(v),name
    rows.append({"name":name,"declared_snapshot_array":a,"sha256_of_minimal_ascii_json":calc})
content={"version":"ARIO-W4C-REGISTRY-VIEW-SHAPE-TEST-ONLY-V0.1",
         "warning":"A hash of an injected registry view is not an authenticated network root or quorum certificate.",
         "cases":rows}
path=HERE/'W4C_TEST_REGISTRY_VECTORS.json'
path.write_text(json.dumps(content,ensure_ascii=True,sort_keys=True,indent=2)+'\n','utf-8')
print('CREATED',path,'CASES',len(rows))
