"""R22.22E: exact retained-content guard, not an admission or freshness oracle."""
import base64, hashlib, json, os, subprocess, sys, tempfile, zipfile
from pathlib import Path
PIN='2f4dc31993e113e884ebdc0befd6b7e7a21b28282093b32e35f68531bcf0faa0'
FIRST_ZIP='2bedc6d0cc85857cfaed3ceafeb5d7700d78923057e661d9c5675d6925e6262b'
D_ZIP='e866c11714f642244fcdecbd4647942877f72b735e76ed0e6c26106552d80b78'
PREFIX='ARIO R22.20 public synthetic floor (no personal data): '
def sha(b): return hashlib.sha256(b).hexdigest()
def decide(local, retained):
    # No index report is accepted by this interface, even if signed by an index.
    if type(retained) is not bytes or len(retained)>65536 or sha(retained)!=PIN:
        return 'HOLD_RETAINED_UNAVAILABLE_OR_CHANGED'
    if type(local) is not bytes or not 0<len(local)<=65536:
        return 'HOLD_LOCAL_UNAVAILABLE'
    if local==retained: return 'HOLD_MATCH_RETAINED_FRESHNESS_UNKNOWN'
    if local.endswith(b'\n') and retained.startswith(local): return 'HOLD_LOCAL_BELOW_RETAINED'
    return 'HOLD_LOCAL_NOT_PINNED'
def emit(name,got,want):
    if got!=want: raise AssertionError((name,got,want))
    print(name,got,'PASS',flush=True)
def old_bytes(raw):
    e=json.loads(raw); assert e['content'].startswith(PREFIX)
    return base64.b64decode(e['content'][len(PREFIX):].split('.')[1],validate=True)
def exercise(old,new):
    assert sha(new)==PIN and new.startswith(old) and len(old.splitlines())==6 and len(new.splitlines())==8
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/'publisher.jsonl'; q=p.with_suffix('.tmp'); p.write_bytes(new)
        emit('01_matching_before_restore',decide(p.read_bytes(),new),'HOLD_MATCH_RETAINED_FRESHNESS_UNKNOWN')
        q.write_bytes(old); os.replace(q,p); assert p.read_bytes()==old
        emit('02_actual_file_restore',decide(p.read_bytes(),new),'HOLD_LOCAL_BELOW_RETAINED')
        for i,name in enumerate(('empty_index','old_only_index','fabricated_latest','index_unavailable','valid_later_hint'),3):
            # Index values are intentionally outside the guard API: they cannot lower the floor.
            emit(f'{i:02d}_{name}',decide(p.read_bytes(),new),'HOLD_LOCAL_BELOW_RETAINED')
        emit('08_floor_missing',decide(old,None),'HOLD_RETAINED_UNAVAILABLE_OR_CHANGED')
        emit('09_floor_restored_to_old',decide(old,old),'HOLD_RETAINED_UNAVAILABLE_OR_CHANGED')
        emit('10_floor_mutation',decide(old,new[:-1]+b'!'),'HOLD_RETAINED_UNAVAILABLE_OR_CHANGED')
        emit('11_local_missing',decide(None,new),'HOLD_LOCAL_UNAVAILABLE')
        emit('12_local_mutation',decide(new[:-1]+b'!',new),'HOLD_LOCAL_NOT_PINNED')
        emit('13_unverified_extension',decide(new+b'{}\n',new),'HOLD_LOCAL_NOT_PINNED')
        emit('14_no_admission_even_on_exact_match',decide(new,new),'HOLD_MATCH_RETAINED_FRESHNESS_UNKNOWN')
    print('14/14 POLICY CONTROLS PASS; NO_ADMISSION; GLOBAL_LATEST=UNKNOWN',flush=True)
def archives(a,b):
    assert sha(a.read_bytes())==FIRST_ZIP and sha(b.read_bytes())==D_ZIP
    with zipfile.ZipFile(a) as x,zipfile.ZipFile(b) as y:
        assert x.testzip() is None and y.testzip() is None
        exercise(old_bytes(x.read('event.json')),y.read('recovered/ledger.jsonl'))
def live(first,recovered,scanner,hints,out):
    old=old_bytes((first/'event.json').read_bytes());new=(recovered/'ledger.jsonl').read_bytes();exercise(old,new)
    hs=json.loads(hints.read_bytes());assert len(hs)==5
    out.mkdir(); binary=scanner/'scan'; reports=[]
    # Actual fresh subprocess and live inclusion proof verification for each feed.
    cases=[('empty',[],0,0,0,0),('old_only',[hs[0]],0,1,0,1),('forged_only',[hs[2],hs[3]],0,0,2,0),('later_only',[hs[1]],1,1,0,0),('mixed',hs,1,3,2,1)]
    with tempfile.TemporaryDirectory() as d:
        local=Path(d)/'publisher.jsonl'; temp=local.with_suffix('.tmp');local.write_bytes(new)
        temp.write_bytes(old);os.replace(temp,local)
        for name,feed,n,requests,rejected,replays in cases:
            (scanner/'hints.json').write_text(json.dumps(feed))
            p=subprocess.run([str(binary.resolve())],cwd=scanner,capture_output=True,timeout=150,check=True)
            (out/(name+'.json')).write_bytes(p.stdout);r=json.loads(p.stdout)
            assert r['complete_sampled_suffix'] is False and r['global_latest']=='NOT_ESTABLISHED' and r['freshness']=='UNKNOWN' and r['trust_activation']=='NO_GO' and r['production']=='NO_GO' and r['merge_authorized'] is False
            assert r['bootstrap_consistency']==r['retained_floor_consistency']=='PASS'
            assert len(r['matching_signed_leaves'])==n and r['proof_requests']==requests and r['rejected']==rejected and r['bootstrap_replays']==replays and r['get_leaves_requests']==0
            assert r['result']==('HOLD_LATER_HINT_INCLUSION_VERIFIED' if n else 'HOLD_NO_VERIFIED_HINT_COMPLETENESS_UNKNOWN')
            decision=decide(local.read_bytes(),new);assert decision=='HOLD_LOCAL_BELOW_RETAINED'
            reports.append({'case':name,'index_result':r['result'],'head_size':r['sampled_tree_size'],'proof_requests':requests,'local_decision':decision})
            print(json.dumps(reports[-1],sort_keys=True),flush=True)
    (out/'summary.json').write_text(json.dumps(reports,sort_keys=True,indent=2)+'\n')
    print('5/5 LIVE HOSTILE FEEDS PASS; NO_ADMISSION; NO_PUBLICATION',flush=True)
if __name__=='__main__':
    if sys.argv[1]=='archive' and len(sys.argv)==4: archives(*map(Path,sys.argv[2:]))
    elif sys.argv[1]=='live' and len(sys.argv)==7: live(*[Path(x).resolve() for x in sys.argv[2:]])
    else: raise SystemExit('arity')
