"""R22.12: offline replay of archived Sigsum TEST receipts; no authority."""
import argparse
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

PINS = {
    'old': '337fc0e36441c0eb3d4ebeb1736cb83bbea8cb958dd8b5aba846a8c1230fc16d',
    'new': '652ff3f19ce4470b82aaf70acf9c2f6e4b0f3aa00a7f7c17a0adc916ba0fd56e',
    'key': '4e17320953d8d08894b8e4301cf51b4c9261e1b5c75c29b66309b56004054b9f',
    'policy': 'efd91055479db94ebc296e65cad1a9876b10b18a6852d1e24fcae9cd5fb5bb44',
}
LOG = '4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d'
SIGNER = '32c199644b404b666091e142334a932293920b59a1e3143ae058759e2b19409d'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def commitment(raw):
    return sha(hashlib.sha256(raw).digest())

@dataclass(frozen=True)
class Evidence:
    scope: str
    signer: str
    log: str
    policy: str
    count: int
    checksum: str
    previous: str
    index: int
    size: int
    root: str


def read_archive(path, which):
    raw = path.read_bytes()
    if sha(raw) != PINS[which]:
        raise ValueError('archive pin mismatch')
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None or len(z.namelist()) != len(set(z.namelist())):
            raise ValueError('archive integrity')
        parts = tuple(z.read(n) for n in ('envelope.json','envelope.json.proof','synthetic-key.pub','policy.txt'))
    if sha(parts[2]) != PINS['key'] or sha(parts[3]) != PINS['policy']:
        raise ValueError('trust configuration mismatch')
    return parts


def verify(parts):
    raw, proof, key, policy = parts
    if sha(key) != PINS['key'] or sha(policy) != PINS['policy']:
        raise ValueError('trust configuration mismatch')
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p/'key.pub').write_bytes(key)
        (p/'receipt').write_bytes(proof)
        # Check that the official named policy resolves to the archived pinned bytes.
        actual = subprocess.run(['sigsum-policy','show','sigsum-test1-2025'], capture_output=True, check=True, timeout=15).stdout
        if actual != policy:
            raise ValueError('policy alias changed')
        return subprocess.run(['sigsum-verify','-k',str(p/'key.pub'),'-P','sigsum-test1-2025',str(p/'receipt')], input=raw, capture_output=True, timeout=15).returncode == 0


def describe(parts):
    # Only call for decision-making AFTER verify(parts) succeeded. Structural mode is a model test.
    raw, proof, key, policy = parts
    x = json.loads(raw)
    fields = {}
    for line in proof.decode('ascii').splitlines():
        k, _, v = line.partition('=')
        if k in ('log','leaf','size','root_hash','leaf_index'):
            if k in fields:
                raise ValueError('duplicate receipt field')
            fields[k] = v
    if (fields['log'] != LOG or fields['leaf'].split()[0] != SIGNER or
            x['synthetic'] is not True or x['authoritative'] is not False or
            x['trust_activation'] != 'NO_GO' or x['production'] != 'NO_GO' or
            x['profile'] != 'ARIO-R22.10-PUBLIC-SYNTHETIC-FLOOR-v1' or
            type(x['record_count']) is not int or x['record_count'] <= 0):
        raise ValueError('invalid research evidence')
    return Evidence(x['scope'], SIGNER, LOG, sha(policy), x['record_count'], commitment(raw), x['previous_checksum'], int(fields['leaf_index']), int(fields['size']), fields['root_hash'])


def decide(e, floor):
    """Both inputs are modeled verified evidence; floor must be separately retained.
    No input here can establish freshness, admission, or permission to sign.
    """
    if floor is None:
        return 'HOLD_FRESHNESS_UNKNOWN'
    if (e.scope,e.signer,e.log,e.policy) != (floor.scope,floor.signer,floor.log,floor.policy):
        return 'HOLD_CONTEXT_MISMATCH'
    if e.size == floor.size and e.root != floor.root:
        return 'HOLD_HEAD_CONFLICT'
    if e.count == floor.count and e.checksum != floor.checksum:
        return 'HOLD_SEQUENCE_CONFLICT'
    if e.count < floor.count or e.index < floor.index or e.size < floor.size:
        return 'HOLD_ROLLBACK_BELOW_FLOOR'
    if e == floor:
        return 'MATCH_RETAINED_FLOOR_NOT_FRESHNESS'
    return 'HOLD_ADVANCE_UNPROVEN'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('old',type=Path)
    p.add_argument('new',type=Path)
    p.add_argument('--structural-only',action='store_true')
    a = p.parse_args()
    old, new = read_archive(a.old,'old'), read_archive(a.new,'new')
    print('MODE', 'STRUCTURAL_MODEL_NO_CRYPTO_VERIFICATION' if a.structural_only else 'OFFICIAL_OFFLINE_VERIFICATION',flush=True)
    if not a.structural_only:
        for name, parts in [('old',old),('new',new),('old_replay',old)]:
            if not verify(parts):
                raise AssertionError(name+' proof invalid')
            print(name,'OFFICIAL_PROOF_PASS',flush=True)
        for name, parts in [('wrong_receipt',(old[0],new[1],old[2],old[3])),('changed_bytes',(old[0]+b' ',*old[1:]))]:
            if verify(parts):
                raise AssertionError(name+' accepted')
            print(name,'OFFICIAL_PROOF_REJECTED',flush=True)
    x,y = describe(old),describe(new)
    if not (x.count == 2 and y.count == 4 and x.scope == y.scope and y.previous == x.checksum and x.size < y.size and x.index < y.index):
        raise AssertionError('fixture relationship')
    # The old authentic pair is indistinguishable from a current pair without retained information.
    cases = [
        ('old_without_floor',x,None,'HOLD_FRESHNESS_UNKNOWN'),
        ('new_without_floor',y,None,'HOLD_FRESHNESS_UNKNOWN'),
        ('old_with_new_floor',x,y,'HOLD_ROLLBACK_BELOW_FLOOR'),
        ('new_with_new_floor',y,y,'MATCH_RETAINED_FLOOR_NOT_FRESHNESS'),
        ('old_with_rolled_back_floor',x,x,'MATCH_RETAINED_FLOOR_NOT_FRESHNESS'),
        ('new_with_old_floor',y,x,'HOLD_ADVANCE_UNPROVEN'),
        ('wrong_scope',replace(y,scope='other'),y,'HOLD_CONTEXT_MISMATCH'),
        ('wrong_signer',replace(y,signer='other'),y,'HOLD_CONTEXT_MISMATCH'),
        ('wrong_log',replace(y,log='other'),y,'HOLD_CONTEXT_MISMATCH'),
        ('wrong_policy',replace(y,policy='other'),y,'HOLD_CONTEXT_MISMATCH'),
        ('same_size_other_root',replace(y,root='0'*64),y,'HOLD_HEAD_CONFLICT'),
        ('same_count_other_checksum',replace(y,checksum='0'*64),y,'HOLD_SEQUENCE_CONFLICT'),
        ('older_head',replace(y,size=x.size),y,'HOLD_ROLLBACK_BELOW_FLOOR'),
        ('older_index',replace(y,index=x.index),y,'HOLD_ROLLBACK_BELOW_FLOOR'),
        ('higher_count_unproven',replace(y,count=5),y,'HOLD_ADVANCE_UNPROVEN'),
    ]
    for name,e,f,want in cases:
        got = decide(e,f)
        if got != want:
            raise AssertionError((name,got,want))
        print(name,got,'PASS')
    print('15/15 POLICY CASES PASS; FLOOR_ROLLBACK_REMAINS_RED; GLOBAL_FRESHNESS=NOT_ESTABLISHED; TRUST=NO_GO; PRODUCTION=NO_GO')

if __name__ == '__main__':
    main()
