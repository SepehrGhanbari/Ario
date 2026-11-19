#!/usr/bin/env python3
"""Research-only source mutations, applied to temporary copies, never to Ario."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).parent
source = (root / 'w16_custody_preflight.py').read_text()
tests = (root / 'test_w16_custody_preflight.py').read_text()
mutations = [
  ('M01_SAME_OWNER_AS_INDEPENDENT','if declared_roots == 1:', 'if False:'),
  ('M02_ROLLBACK_UNDETECTED',"if newest > local['epoch']:", 'if False:'),
  ('M03_FORGET_LOCAL_HIGHWATER',"if known_highwater is not None and local['epoch'] < known_highwater:", 'if False:'),
  ('M04_FORGET_REMOTE_HIGHWATER',"if known_highwater is not None and newest < known_highwater:", 'if False:'),
  ('M05_SPLIT_VIEW_IGNORED','if any(len(heads) > 1 for heads in by_epoch.values()):', 'if False:'),
  ('M06_DUPLICATE_KEY_ACCEPTED',"if entry['witness_key'] in seen_keys:", 'if False:'),
  ('M07_REMOTE_LAG_IGNORED',"if newest < local['epoch']:", 'if False:'),
  ('M08_SAME_EPOCH_HEAD_CONFUSION',"if local['head_sha256'] not in by_epoch.get(local['epoch'], set()):", 'if False:'),
  ('M09_FAKE_OPERATION_PERMISSION',"'operational_authority': 'NONE'", "'operational_authority': 'GRANTED'"),
  ('M10_FAKE_VERIFIED_CURRENTNESS',"'remote_currentness': 'NOT_ESTABLISHED'", "'remote_currentness': 'VERIFIED'"),
  ('M11_FAKE_IND_ADMIN_TRUST',"'independent_administrative_custody': 'NOT_ESTABLISHED'", "'independent_administrative_custody': 'VERIFIED'"),
  ('M12_ALL_PREVIEWS_ALLOWED',"'read_only_preview': preview", "'read_only_preview': True"),
  ('M13_FALSE_SIGNED_REFERENCE',"if entry['reported_signature_valid'] is False:", 'if False:'),
]
records=[]
with tempfile.TemporaryDirectory(prefix='w16_mutant_') as tmp:
    folder=Path(tmp)
    test_path=folder/'test_w16_custody_preflight.py'
    test_path.write_text(tests)
    (folder/'w16_custody_preflight.py').write_text(source)
    def run():
        return subprocess.run([sys.executable, '-B', '-m', 'unittest', '-q', 'test_w16_custody_preflight.py'],
                              cwd=folder,capture_output=True,text=True,timeout=8)
    baseline=run()
    if baseline.returncode:
        raise RuntimeError('BASELINE_FAILURE: '+baseline.stderr[-1000:])
    for name, old, new in mutations:
        if source.count(old)!=1:
            raise AssertionError(f'{name} matches {source.count(old)}')
        mutated=source.replace(old,new,1)
        (folder/'w16_custody_preflight.py').write_text(mutated)
        proc=run()
        records.append({'id':name,'killed':proc.returncode!=0,
                        'mutant_sha256':hashlib.sha256(mutated.encode()).hexdigest(),
                        'first_failure':next((line for line in proc.stderr.splitlines() if line.startswith(('FAIL:','ERROR:'))),None)})
        (folder/'w16_custody_preflight.py').write_text(source)
result={'schema':'ARIO_W16_PRECONDITION_MUTATION_AUDIT_V1','research_only':True,
        'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
        'source_git_blob_sha1':hashlib.sha1(b'blob '+str(len(source.encode())).encode()+b'\0'+source.encode()).hexdigest(),
        'run':{'unittest_groups':3,'case_matrix_rows':24,'selected_mutants':len(records),
               'killed':sum(x['killed'] for x in records),'survived':sum(not x['killed'] for x in records)},
        'mutations':records,'independent_oracle':False,'actual_authority':False,
        'note':'All mutations and tests are same-author design; passing does not imply independent administrative custody.'}
print(json.dumps(result,indent=2,sort_keys=True))
