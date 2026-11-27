"""RESEARCH_ONLY. One authorized size-2 request and separate-process readback."""
import base64, hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile, urllib.request, urllib.error
ORIGIN="github.com/SepehrGhanbari/Ario/kladje-test-v1"
LOG=ORIGIN+"+50e6b45c+AQUBDEa9qhxEeT6UJrwEbedbzLvmntBhPS1oJO0hUw3s"
WIT="markovianprotocol.com/witness+41b8827f+BJKLl8rBYM0oUxSaWh9rjTldTprEpYj/SWVIGgacA9XC"
BASE="https://witness.markovianprotocol.com"
CHECK=BASE+"/"+hashlib.sha256(ORIGIN.encode()).hexdigest()+"/checkpoint"
UA="Ario-research/0.1 (+https://github.com/SepehrGhanbari/Ario)"
def sha(x): return hashlib.sha256(x).digest()
def b64(s):
    v=base64.b64decode(s,validate=True)
    assert base64.b64encode(v)==s
    return v
def key(v,alg):
    n,k,p=v.split("+"); raw=b64(p.encode())
    assert len(raw)==33 and raw[0]==alg and sha(n.encode()+b"\n"+raw).hex()[:8]==k
    return n,bytes.fromhex(k),raw[1:]
def ed(pub,sig,msg):
    with tempfile.TemporaryDirectory() as d:
        p=pathlib.Path(d)
        (p/"key").write_bytes(bytes.fromhex("302a300506032b6570032100")+pub)
        (p/"sig").write_bytes(sig); (p/"msg").write_bytes(msg)
        subprocess.run(["openssl","pkeyutl","-verify","-pubin","-keyform","DER","-inkey",str(p/"key"),"-rawin","-in",str(p/"msg"),"-sigfile",str(p/"sig")],check=True,capture_output=True)
def verify(note,witness):
    assert len(note)<8192 and note.endswith(b"\n")
    body,sigs=note.split(b"\n\n",1); body+=b"\n"
    o,n,r=body.decode("ascii").splitlines()
    assert o==ORIGIN and n in ("1","2") and len(b64(r.encode()))==32
    lines=sigs.splitlines(); assert len(lines)==(2 if witness else 1)
    name,k,pub=key(LOG,1); prefix=("— "+name+" ").encode()
    assert lines[0].startswith(prefix)
    raw=b64(lines[0][len(prefix):]); assert len(raw)==68 and raw[:4]==k
    ed(pub,raw[4:],body)
    if witness:
        name,k,pub=key(WIT,4); prefix=("— "+name+" ").encode()
        assert lines[1].startswith(prefix)
        raw=b64(lines[1][len(prefix):]); assert len(raw)==76 and raw[:4]==k
        ts=int.from_bytes(raw[4:12],"big")
        ed(pub,raw[12:],b"cosignature/v1\ntime "+str(ts).encode()+b"\n"+body)
    return int(n),b64(r.encode())
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*a,**kw): return None
def request(url,data=None):
    req=urllib.request.Request(url,data=data,headers={"User-Agent":UA,"Cache-Control":"no-cache","Content-Type":"text/plain; charset=utf-8"},method="POST" if data is not None else "GET")
    try:
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=25) as r:
            return r.status,r.read(8193)
    except urllib.error.HTTPError as e: return e.code,e.read(8193)
def readback(local):
    try:
        a=verify(local,False)
        status,note=request(CHECK); assert status==200
        b=verify(note,True)
        if a[0]<b[0]: verdict="REJECT_STALE_LOCAL_COPY"
        elif a[0]>b[0]: verdict="HOLD_EXTERNAL_BEHIND_LOCAL"
        elif a[1]!=b[1]: verdict="HOLD_ROOT_CONFLICT"
        else: verdict="MATCH_OBSERVED_FLOOR_NOT_LATESTNESS"
        pathlib.Path("observed-note").write_bytes(note)
        print("FRESH_PROCESS_READBACK",a[0],b[0],verdict)
        return verdict
    except Exception as e:
        print("HOLD_INVALID_OR_UNAVAILABLE_EVIDENCE",type(e).__name__)
        return "HOLD_INVALID_OR_UNAVAILABLE_EVIDENCE"
def main():
    if len(sys.argv)>1 and sys.argv[1]=="cold":
        assert set(os.listdir("."))=={"verifier.py","local-checkpoint"}
        return 0 if readback(pathlib.Path("local-checkpoint").read_bytes())==sys.argv[2] else 1
    assert os.environ.get("GITHUB_RUN_ATTEMPT")=="1"
    p=pathlib.Path(__file__).parent
    q=p/"phase2"
    cp=(q/"checkpoint").read_bytes(); old=(p/"cosigned-checkpoint-size-1.txt").read_bytes()
    assert sha(cp).hex()=="9f480ba76a115046dfdd0cabbeb01eb473c3bd5ca8840f921f12939b34212baf"
    assert sha(old).hex()=="979b57d71dbf0793d3daab94a82fcb23e03588fc950c04fb90e6e48fdad4d4c2"
    n,a=verify(old,True); m,root=verify(cp,False); assert (n,m)==(1,2)
    entries=(q/"entries").read_bytes().splitlines(); assert len(entries)==2
    b=sha(b"\x00"+entries[1]); assert sha(b"\x00"+entries[0])==a
    proof=(q/"consistency-proof.txt").read_bytes(); assert b64(proof.rstrip(b"\n"))==b and sha(b"\x01"+a+b)==root
    for i,leaf in enumerate(entries,1):
        cap=(q/f"capsule-size-{i}.json").read_bytes()[:-1]; v=json.loads(leaf)
        assert v["capsule_sha256"]==sha(cap).hex() and v["capsule_bytes"]==len(cap)
    assert json.loads((q/"capsule-size-2.json").read_bytes())["events"][:3]==json.loads((q/"capsule-size-1.json").read_bytes())["events"]
    out=pathlib.Path("markovian-phase2-evidence").resolve(); out.mkdir()
    status,prior=request(CHECK); print("PRECHECK_HTTP",status); assert status==200
    state=verify(prior,True)
    if state==(1,a):
        print("ONE_POST_ATTEMPT",flush=True)
        status,reply=request(BASE+"/add-checkpoint",b"old 1\n"+proof+b"\n"+cp)
        print("POST_HTTP",status); (out/"response.txt").write_bytes(reply)
        assert status==200,"No retry"
        cosigned=cp+reply; assert verify(cosigned,True)==(2,root)
    elif state==(2,root):
        print("ALREADY_COSIGNED_NO_POST"); cosigned=prior
    else: raise RuntimeError("unexpected external floor; no POST")
    (out/"cosigned-checkpoint-size-2.txt").write_bytes(cosigned)
    print("SIZE_2_COSIGNED_VERIFIED",sha(cosigned).hex())
    print("PUBLIC_COSIGNATURE",cosigned.splitlines()[-1].decode())
    status,obs=request(CHECK); print("READBACK_HTTP",status)
    assert status==200 and verify(obs,True)==(2,root)
    (out/"direct-readback.txt").write_bytes(obs)
    # Separate subprocesses receive only verifier and restored publisher checkpoint.
    old_log=b"\n".join(old.split(b"\n")[:-2])+b"\n"
    assert verify(old_log,False)==(1,a)
    for label,local,want in (("rollback",old_log,"REJECT_STALE_LOCAL_COPY"),("current",cp,"MATCH_OBSERVED_FLOOR_NOT_LATESTNESS")):
        with tempfile.TemporaryDirectory() as d:
            t=pathlib.Path(d); shutil.copyfile(__file__,t/"verifier.py")
            (t/"local-checkpoint").write_bytes(local)
            run=subprocess.run([sys.executable,"verifier.py","cold",want],cwd=t,capture_output=True,text=True)
            print(run.stdout, end=""); assert run.returncode==0,run.stderr
            (out/(label+"-readback.txt")).write_bytes((t/"observed-note").read_bytes())
            assert verify((t/"observed-note").read_bytes(),True)==(2,root)
    # Historical replay control: equal old authentic signatures alone cannot establish freshness.
    assert verify(old_log,False)==verify(old,True)
    print("OLD_OLD_REPLAY_LIMITATION_CONFIRMED")
    print("PHASE2_PASS_BOUNDED_EXTERNAL_FLOOR")
    return 0
if __name__=="__main__": sys.exit(main())
