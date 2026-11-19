#!/usr/bin/env python3
"""W20 disposable selected mutants, same-author (NOT independent review)."""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

HERE=Path(__file__).parent
VERIFIER=(HERE/'w20_independent_monitor.py').read_text('utf-8')
SOURCES={n:(HERE/n).read_text('utf-8') for n in (
    'w20_merkle_producer.py','test_w20_native_log.py')}
MUTANTS=[
 ('M01_IGNORE_CONSISTENCY', "if not verify_consistency(m, n, old_body['root_sha256'], next_body['root_sha256'], consistency):", 'if False:'),
 ('M02_IGNORE_INCLUSION', "if not verify_inclusion(raw, ix, body['size'], body['root_sha256'], item['proof']):", 'if False:'),
 ('M03_UNPREFIXED_LEAF', "return hashlib.sha256(b'\\x00' + data).digest()", 'return hashlib.sha256(data).digest()'),
 ('M04_UNPREFIXED_BRANCH', "return hashlib.sha256(b'\\x01' + left + right).digest()", 'return hashlib.sha256(left + right).digest()'),
 ('M05_IGNORE_RETAINED_PRIOR', "if known_prior is None:", "if False:"),
 ('M06_IGNORE_SIZE_ROLLBACK', 'if n < m:', 'if False:'),
 ('M07_IGNORE_FORK', "if old_body['root_sha256'] != next_body['root_sha256']:", 'if False:'),
 ('M08_FALSE_ACTION_AUTHORITY', "'operational_authority': 'NONE'", "'operational_authority': 'GRANTED'"),
 ('M09_FALSE_NATIVE_LOG_WITNESS', "'real_ario_log_witnessed': 'NOT_ESTABLISHED'", "'real_ario_log_witnessed': 'YES'"),
 ('M10_IGNORE_EVENT_SCHEMA', 'if not valid_public_synthetic_event(event, ix):', 'if False:'),
 ('M11_IGNORE_ORIGIN_BINDING', "or body['origin'] != expected_origin", 'or False'),
 ('M12_OMIT_FULL_INCLUSION_SET_CHECK', 'if seen != set(range(len(events))):', 'if False:'),
 ('M13_IGNORE_SIGNATURE_ERRORS', "except (InvalidSignature, ValueError, TypeError):\n        return None", "except (InvalidSignature, ValueError, TypeError):\n        return body"),
]

def gitblob(src: str) -> str:
    data=src.encode('utf8')
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def run_in(folder: Path, source: str):
    (folder/'w20_independent_monitor.py').write_text(source,'utf8')
    r=subprocess.run([sys.executable,'-B','-m','unittest','-q','test_w20_native_log.py'],
                     cwd=folder,capture_output=True,text=True,timeout=20)
    first=next((line.strip() for line in r.stderr.splitlines() if line.startswith(('FAIL:','ERROR:'))),None)
    return r.returncode,first,r.stderr[-700:]

with TemporaryDirectory(prefix='ario_w20_mutants_') as temp:
    folder=Path(temp)
    for name,src in SOURCES.items():
        (folder/name).write_text(src,'utf8')
    code,first,err=run_in(folder,VERIFIER)
    if code:
        raise RuntimeError('BASELINE_FAIL: '+err)
    results=[]
    for name,old,new in MUTANTS:
        count=VERIFIER.count(old)
        if count !=1:
            raise RuntimeError(f'{name} matched {count} times, expected one')
        mutated=VERIFIER.replace(old,new,1)
        rc,first,error=run_in(folder,mutated)
        results.append({'id':name,'mutant_git_blob_sha1':gitblob(mutated),
                        'killed':rc!=0,'first_failing_group':first,
                        'exit_code':rc})
    output={
        'schema':'ARIO_W20_SELECTED_MUTATION_RESULTS_V1',
        'source_verifier_git_blob_sha1':gitblob(VERIFIER),
        'baseline_unit_methods':6,
        'baseline_tests':'PASS',
        'mutants_selected':len(results),
        'mutants_killed':sum(x['killed'] for x in results),
        'mutants_survived':sum(not x['killed'] for x in results),
        'mutants':results,
        'research_status':'SAME_AUTHOR_NONBLIND','real_external_signatures':0,
        'real_ario_memory_events':0,'operational_authority':'NONE',
        'note':'Mutant survival may indicate redundant defenses or insufficient controls; do not call 100% security if all selected mutants die.'
    }
    print(json.dumps(output,indent=2,sort_keys=True))
