#!/usr/bin/env python3
"""Research-only exact-Git-blob W11 mutation probe; modifies disposable JS copies.
Never edits Git checkout, Ario implementation, signer, or memory.
"""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

PIN_BLOB = '63bde301e7f061945dbd2fb43954e817d2182fa6'
PIN_RESULT_BLOB = '8950907e7c2c606493f1aa5806d0487957dc3e7d'
SOURCE = Path(__file__).with_name('w11_temporal_origin_no_history_promotion_lab.js')
BASE = SOURCE.read_bytes()
ADDON = Path(__file__).with_name('w12_targeted_controls.js').read_bytes()
def git_blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
assert git_blob(BASE)==PIN_BLOB, 'W11 original source changed'
original=subprocess.run(['node',str(SOURCE)],capture_output=True,timeout=8,check=True)
assert git_blob(original.stdout)==PIN_RESULT_BLOB, 'W11 output differs from published original blob'
assert json.loads(original.stdout)['scenario_count']==36
original_target=subprocess.run(['node','-'], input=BASE+b'\n'+ADDON,capture_output=True,timeout=8,check=True)
assert b'W12_RESULT=' in original_target.stdout, 'New targeted controls fail on original'
assert json.loads(original_target.stdout.decode().split('W12_RESULT=')[1])['count']==6

# Mutation changes *implementation* substring exactly once. They must not rewrite tests.
mutants = [
('M01_NO_GRANT_REQUIRED', 'if(matched.length===0)return out("DENY","NO_ACTIVE_EXACT_SCOPE_GRANT",info);', 'if(false)return out("DENY","NO_ACTIVE_EXACT_SCOPE_GRANT",info);', 'grant enforcement disabled'),
('M02_REVOKE_IGNORED', 'g.revokedAt===null&&step<g.expiresAt', 'true&&step<g.expiresAt', 'revoked grants remain eligible'),
('M03_EXPIRY_IGNORED', 'g.revokedAt===null&&step<g.expiresAt', 'g.revokedAt===null&&true', 'expired grants stay eligible'),
('M04_PRINCIPAL_IGNORED', 'g.scope.principal===candidate.principal', 'true', 'incorrect principal binding'),
('M05_RECIPIENT_IGNORED', 'g.scope.destination===candidate.destination', 'true', 'recipient unbound'),
('M06_RESOURCE_IGNORED', 'g.scope.resource===candidate.resource', 'true', 'resource unbound'),
('M07_OPERATION_IGNORED', 'g.scope.operation===candidate.operation', 'true', 'operation unbound'),
('M08_UNKNOWN_ORIGIN_ALLOWED', 'if(src.rootTypes.includes("UNKNOWN"))', 'if(false)', 'unknown roots can reach candidate review'),
('M09_HISTORY_AS_GRANT', 'if(matched.length===0)return out("DENY","NO_ACTIVE_EXACT_SCOPE_GRANT",info);', 'if(matched.length===0&&src.phase!=="HISTORY_NOTE")return out("DENY","NO_ACTIVE_EXACT_SCOPE_GRANT",info);', 'history notes bypass grant requirement'),
('M10_ALL_DERIVED_USER', 'const rootTypes=[...new Set(src.flatMap(x=>x.rootTypes))].sort();', 'const rootTypes=["USER_REQUEST"];', 'derived-origin type silently recast as trusted user'),
('M11_ALL_DERIVED_EXTERNAL', 'const rootTypes=[...new Set(src.flatMap(x=>x.rootTypes))].sort();', 'const rootTypes=["EXTERNAL_PAGE"];', 'derived mixed/unknown types silently overwritten'),
('M12_MERGE_DROPS_OTHER_ROOTS', 'const src=parents.map(id=>nodes.get(id)), rootIds=[...new Set(src.flatMap(x=>x.rootIds))].sort();', 'const src=parents.map(id=>nodes.get(id)), rootIds=[src[0].rootIds[0]];', 'multi-parent source ancestry collapsed to first root'),
('M13_READ_SUMMARY_ANY_DEST', 'if(candidate.operation==="READ_SUMMARY" && candidate.destination==="LOCAL_ONLY")', 'if(candidate.operation==="READ_SUMMARY")', 'read-only status even with remote destination'),
('M14_IGNORE_TTL_TYPE', '!Number.isSafeInteger(scope.ttl)||scope.ttl<1||scope.ttl>50', 'false', 'bad TTLs accepted'),
('M15_SOURCE_TYPES_REPLACED_WITH_USER_IN_ALL_ROOTS', 'const allowedRoots = ["EXTERNAL_PAGE","RETRIEVED_MEMORY","TOOL_RESULT","USER_REQUEST","UNKNOWN"];', 'const allowedRoots = ["EXTERNAL_PAGE","RETRIEVED_MEMORY","TOOL_RESULT","USER_REQUEST","UNKNOWN"];', 'no-op mutation control for harness'),
]
# No-op listed explicitly as excluded instrumentation control, not a meaningful mutant.
mutants=mutants[:-1]
results=[]
with tempfile.TemporaryDirectory(prefix='ario_w12_mutants_') as root:
    for name,old,new,defect in mutants:
        count=BASE.decode().count(old)
        assert count==1, f'{name} pattern count={count}'
        mutant=BASE.decode().replace(old,new,1).encode()
        assert mutant!=BASE
        file=Path(root)/(name+'.js');file.write_bytes(mutant)
        run=subprocess.run(['node',str(file)],capture_output=True,timeout=8)
        killed=run.returncode!=0
        # Ensure survivors really return the full 36 synthetic tests, not an empty pass.
        if not killed:
            obs=json.loads(run.stdout)
            assert obs['scenario_count']==36 and len(obs['rows'])==36
        text=(run.stderr.decode(errors='replace')+'\n'+run.stdout.decode(errors='replace'))
        import re
        match=re.search(r'FAIL (T\d+) expected=(\S+) actual=(\S+)',text)
        targeted=None
        if not killed:
            rerun=subprocess.run(['node','-'],input=mutant+b'\n'+ADDON,capture_output=True,timeout=8)
            killed_by_new=rerun.returncode!=0
            detailed=(rerun.stderr+rerun.stdout).decode(errors='replace')
            new_match=re.search(r'W12_TARGETED_FAIL (P\d+_[A-Z_]+)',detailed)
            targeted={'killed':killed_by_new,'failed_case':new_match.group(1) if new_match else None,
                      'status':'KILLED_BY_NEW_W12_CONTROL' if killed_by_new else 'SURVIVED_W12'}
        results.append(dict(mutant=name,defect=defect,mutation_sha256=hashlib.sha256(mutant).hexdigest(),killed=killed,exit_code=run.returncode,
                            first_failed_case=match.group(1) if match else None,
                            first_failure_observed=match.group(3) if match else None,
                            status='KILLED' if killed else 'SURVIVED',targeted_new_controls=targeted))

result={
 'schema':'ARIO_W12_SOURCE_PINNED_MUTATION_AUDIT_V1','execution':'NATIVE_NODE_ON_ORIGINAL_GIT_BLOB_DISPOSABLE_MUTATIONS',
 'node_version':subprocess.check_output(['node','--version'],text=True).strip(),
 'source_blob_sha1':PIN_BLOB,'source_sha256':hashlib.sha256(BASE).hexdigest(),
 'original_output_blob_sha1':PIN_RESULT_BLOB,
 'original_replay':'36/36; EXACT published JSON Git blob SHA-1',
 'total_mutants':len(results),'killed':sum(x['killed'] for x in results),
 'survived':sum(not x['killed'] for x in results),
 'survivors_killed_by_targeted':sum(x['targeted_new_controls']['killed'] for x in results if x['targeted_new_controls'] is not None),
 'new_targeted_positive_negative_control_count':6,
 'mutants':results,
 'scope':'Mutation survival is a test-sensitivity gap in an intentionally synthetic simulator. No real Ario runtime security or underlying true-world event was tested.',
 'actual_memory_writes':0,'actual_external_effects':0,'independent_external_oracle':False
}
print(json.dumps(result,ensure_ascii=False,indent=2))
