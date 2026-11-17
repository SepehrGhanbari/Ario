#!/usr/bin/env python3
"""Research-only mutation audit against W22. No real keys or external network.

11 author-chosen mutations of only W22 note monitor; 7 test methods rerun
in disposable, isolated temp directories. This is NOT external human review.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

BASE=Path(__file__).parent
ORIGINAL=(BASE/'w22_note_monitor.py').read_text(encoding='utf8')
SOURCES=['w22_note_monitor.py','w22_tile_server.py','w20_independent_monitor.py',
         'test_w22_checkpoint_interop.py','W22_PUBLIC_SYNTHETIC_SIGNED_NOTES_2026-11-17.json',
         'W20_SYNTHETIC_LOG_CHECKPOINTS_AND_PROOFS_2026-11-17.json']
MUTANTS=[
 ('M01_SKIP_ED25519_VERIFY',"Ed25519PublicKey.from_public_bytes(raw_pub).verify(signature[4:], note_text)","None"),
 ('M02_SKIP_VKEY_KEYID_BINDING',"if bytes.fromhex(keyid)!=expected_id:","if False:"),
 ('M03_SKIP_MERKLE_ROOT_MATCH',"if root_from_leaves(hashes).hex()!=candidate['root']:","if False:"),
 ('M04_SKIP_LEAF_TILE_BINDING',"if hashlib.sha256(b'\\x00'+event).digest()!=hashes[i]:","if False:"),
 ('M05_ALLOW_HISTORY_ROLLBACK',"if n<highwater['size']:","if False:"),
 ('M06_ALLOW_SAME_SIZE_FORK',"if n==highwater['size'] and candidate['root']!=highwater['root']:","if False:"),
 ('M07_FOLLOW_HTTP_REDIRECTS',"class NoRedirect(HTTPRedirectHandler):\n    def redirect_request(self,*args):\n        return None","class NoRedirect(HTTPRedirectHandler):\n    def redirect_request(self,*args):\n        return super().redirect_request(*args)"),
 ('M08_SKIP_COMPACT_CONSISTENCY',"or not verify_consistency(prior['size'],n,prior['root'],candidate['root'],proof['nodes'])):","or False):"),
 ('M09_FAKE_ACTION_AUTHORITY',"'operational_authority':'NONE'","'operational_authority':'GRANTED'"),
 ('M10_DROP_HIGHWATER_REQUIRED',"if retained_highwater is None:return result('HOLD_UNCERTAIN','NO_RETAINED_HIGHWATER')", "if False:return result('HOLD_UNCERTAIN','NO_RETAINED_HIGHWATER')"),
 ('M11_ALLOW_HTTP_ENV_PROXY', '_OPENER=build_opener(ProxyHandler({}), NoRedirect)', '_OPENER=build_opener(NoRedirect)')
]

def blob_sha(s):
    b=s.encode('utf8')
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\x00'+b).hexdigest()

CASES = {
    'M01_SKIP_ED25519_VERIFY':'test_01_note_grammar_and_independent_verifier',
    'M02_SKIP_VKEY_KEYID_BINDING':'test_01_note_grammar_and_independent_verifier',
    'M03_SKIP_MERKLE_ROOT_MATCH':'test_06_signed_fork_and_malformed_bytes',
    'M04_SKIP_LEAF_TILE_BINDING':'test_06_signed_fork_and_malformed_bytes',
    'M05_ALLOW_HISTORY_ROLLBACK':'test_04_rollback_and_two_old_limitation',
    'M06_ALLOW_SAME_SIZE_FORK':'test_06_signed_fork_and_malformed_bytes',
    'M07_FOLLOW_HTTP_REDIRECTS':'test_07_redirect_target_was_not_contacted',
    'M08_SKIP_COMPACT_CONSISTENCY':'test_06_signed_fork_and_malformed_bytes',
    'M09_FAKE_ACTION_AUTHORITY':'test_03_valid_partial_tiles_and_continuity',
    'M10_DROP_HIGHWATER_REQUIRED':'test_05_wrong_trust_inputs_hold',
    'M11_ALLOW_HTTP_ENV_PROXY':'test_08_env_proxy_cannot_intercept_loopback'
}

def check(name,old,new):
    assert ORIGINAL.count(old)==1,(name,ORIGINAL.count(old))
    changed=ORIGINAL.replace(old,new,1)
    with tempfile.TemporaryDirectory(prefix='ario_w22_mutant_') as tmp:
        d=Path(tmp)
        for file in SOURCES:
            (d/file).write_bytes((BASE/file).read_bytes())
        (d/'w22_note_monitor.py').write_text(changed,encoding='utf8')
        proc=subprocess.run([sys.executable,'-B','-m','unittest','-q',
                             'test_w22_checkpoint_interop.W22.'+CASES[name]],
                            cwd=d,capture_output=True,text=True,timeout=12)
        first=next((s for s in proc.stderr.splitlines() if s.startswith(('FAIL:','ERROR:'))),'NONE')
        return {'mutation':name,'mutated_sha256':hashlib.sha256(changed.encode()).hexdigest(),
                'detected':proc.returncode!=0,'first_failed_test':first,
                'test_process_returncode':proc.returncode}


def main():
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=list(pool.map(lambda t:check(*t),MUTANTS))
    obj={'schema':'ARIO_W22_SELECTED_SOURCE_MUTATIONS_V1','source_git_blob_sha1':blob_sha(ORIGINAL),
         'selected':len(MUTANTS),'detected':sum(j['detected'] for j in jobs),
         'survivors':[j['mutation'] for j in jobs if not j['detected']],
         'not_independent_audit':True,'mutations':jobs,
         'scope':'W22 Python monitor in temporary files, synthetic keys and localhost only, no external publication'}
    print(json.dumps(obj,indent=2,sort_keys=True))

if __name__=='__main__':main()
