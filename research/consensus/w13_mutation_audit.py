#!/usr/bin/env python3
"""Mutate only a temporary copy of W13 research verifier; run original tests.

All keys are synthetic. This is test-sensitivity evidence, not a security audit.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).parent
SOURCE=(HERE/'w13_issuer_boundary.py').read_text(encoding='utf-8')
TESTS=(HERE/'test_w13_issuer_boundary.py').read_text(encoding='utf-8')
MUTATIONS=[
 ('M01_NO_SIGNATURE_CHECK','public.verify(sig_bytes, _wire({"domain": domain, "body": body}))','pass','forged source and grant signatures accepted'),
 ('M02_GRANT_KEY_AS_ORIGIN','_valid_packet(self.grant_key, GRANT_DOMAIN, grant_packet)','_valid_packet(self.origin_key, GRANT_DOMAIN, grant_packet)','wrong signer key accepted, correct grants refused'),
 ('M03_IGNORE_REVOCATION','if grant["grant_id"] in self.revoked:','if False:','revoked grant reuse'),
 ('M04_IGNORE_EXPIRY','if not grant["not_before"] <= now < grant["expires"]:','if False:','expired grant reuse'),
 ('M05_IGNORE_SCOPE','if any(grant[key] != proposed[key] for key in ACTION_KEYS):','if False:','grant operation/recipient/resource unbound'),
 ('M06_IGNORE_CONTENT_DIGEST','source["digest"] != digest_content(content)','False','tampered content source reused'),
 ('M07_IGNORE_PROPOSED_PRINCIPAL','proposed["principal"] != source["principal"]','False','principal mismatch at source boundary'),
 ('M08_CONFIG_SAME_KEY_ALLOWED','if self.origin_key.public_bytes_raw() == self.grant_key.public_bytes_raw():','if False:','one shared key accepted for two trust roles'),
 ('M09_GRANT_NOT_REQUIRED','if grant_packet is None:\n            return answer("DENY", "NO_SEPARATE_GRANT")','if grant_packet is None:\n            return answer("ELIGIBLE_FOR_SEPARATE_GATE", "NO_GRANT_REQUIRED")','memory alone is eligible'),
 ('M10_AUTHORITY_GRANTED','"authority": "NOT_ESTABLISHED"','"authority": "GRANTED"','synthetic eligibility mislabeled final authorization'),
 ('M11_FORGED_EXECUTION','"external_effects": 0','"external_effects": 1','synthetic action counter falsely reports effect'),
 ('M12_BAD_CLOCK_TYPE','if type(now) is not int or now < 0:','if False:','invalid clock accepted or causes unexpected behavior'),
 ('M13_SKIP_SOURCE_SIG','_valid_packet(self.origin_key, SOURCE_DOMAIN, source_packet)','_valid_packet(self.grant_key, SOURCE_DOMAIN, source_packet)','wrong source verification key'),
]

def run_test(source, tests, root):
    (root/'w13_issuer_boundary.py').write_text(source,encoding='utf-8')
    (root/'test_w13_issuer_boundary.py').write_text(tests,encoding='utf-8')
    return subprocess.run([sys.executable,'-B','test_w13_issuer_boundary.py'],cwd=root,
                          capture_output=True,text=True,timeout=8)

origsha=hashlib.sha256(SOURCE.encode()).hexdigest()
with tempfile.TemporaryDirectory(prefix='ario_w13_mutants_') as tmp:
    root=Path(tmp)
    initial=run_test(SOURCE,TESTS,root)
    if initial.returncode:
        raise RuntimeError('ORIGINAL_TESTS_RED: '+initial.stderr[-1800:])
    records=[]
    for name,old,new,meaning in MUTATIONS:
        count=SOURCE.count(old)
        if count!=1:raise ValueError(f'{name}: expected one match, got {count}')
        mutant=SOURCE.replace(old,new,1)
        assert mutant != SOURCE
        r=run_test(mutant,TESTS,root)
        records.append({'name':name,'meaning':meaning,'mutated_sha256':hashlib.sha256(mutant.encode()).hexdigest(),
                        'killed_by_tests':r.returncode!=0,'exit_code':r.returncode,
                        'first_failure':next((line.strip() for line in r.stderr.splitlines() if line.startswith('FAIL:') or line.startswith('ERROR:')),None)})
result={'schema':'ARIO_W13_EPHEMERAL_TWO_DOMAIN_MUTATION_LAB_V1',
        'source_sha256':origsha,'source_git_blob_sha1':hashlib.sha1(b'blob '+str(len(SOURCE.encode())).encode()+b'\0'+SOURCE.encode()).hexdigest(),
        'python_version':sys.version.split()[0], 'source_test_methods':4,
        'original_tests':'PASS','selected_mutants':len(records),'killed':sum(x['killed_by_tests'] for x in records),
        'survived':sum(not x['killed_by_tests'] for x in records),'records':records,
        'independent_external_custody':False,'actual_key_activation':False,'real_effects':0,
        'note':'All mutants and test expectations authored in the same research session; no external gold corpus.'}
print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
