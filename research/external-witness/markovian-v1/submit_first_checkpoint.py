"""One authorized synthetic checkpoint handoff; no secrets, no retries."""
import base64, hashlib, pathlib, subprocess, tempfile, urllib.request, urllib.error, os
P=pathlib.Path("research/external-witness/markovian-v1")
ORIGIN="github.com/SepehrGhanbari/Ario/kladje-test-v1"
LOG_VKEY=ORIGIN+"+50e6b45c+AQUBDEa9qhxEeT6UJrwEbedbzLvmntBhPS1oJO0hUw3s"
WITNESS_VKEY="markovianprotocol.com/witness+41b8827f+BJKLl8rBYM0oUxSaWh9rjTldTprEpYj/SWVIGgacA9XC"
BASE="https://witness.markovianprotocol.com"
CHECK=BASE+"/"+hashlib.sha256(ORIGIN.encode()).hexdigest()+"/checkpoint"
UA="Ario-research/0.1 (+https://github.com/SepehrGhanbari/Ario)"
def b64(s):
    v=base64.b64decode(s,validate=True)
    assert base64.b64encode(v)==s
    return v
def key(vkey,alg):
    name,k,p=vkey.split("+")
    raw=b64(p.encode())
    assert len(raw)==33 and raw[0]==alg
    assert hashlib.sha256(name.encode()+b"\n"+raw).hexdigest()[:8]==k
    return name,bytes.fromhex(k),raw[1:]
def edverify(pub,signature,message):
    with tempfile.TemporaryDirectory() as d:
        p=pathlib.Path(d)
        (p/"key").write_bytes(bytes.fromhex("302a300506032b6570032100")+pub)
        (p/"sig").write_bytes(signature); (p/"message").write_bytes(message)
        subprocess.run(["openssl","pkeyutl","-verify","-pubin","-keyform","DER","-inkey",str(p/"key"),"-rawin","-in",str(p/"message"),"-sigfile",str(p/"sig")],check=True,capture_output=True)
cp=(P/"checkpoint").read_bytes()
assert hashlib.sha256(cp).hexdigest()=="84ef0c4abc6e06033219f3a34b12c5d4b3893e0a8bd3f082bc7fed1d6e5047cd"
assert (P/"vkey.txt").read_text().strip()==LOG_VKEY
body,sigblock=cp.split(b"\n\n",1); body+=b"\n"
ln,lk,lp=key(LOG_VKEY,1); wn,wk,wp=key(WITNESS_VKEY,4)
prefix=("— "+ln+" ").encode()
assert sigblock.startswith(prefix) and sigblock.count(b"\n")==1
raw=b64(sigblock[len(prefix):-1]); assert len(raw)==68 and raw[:4]==lk
edverify(lp,raw[4:],body)
origin,size,root=body.decode().splitlines(); assert origin==ORIGIN and size=="1"
entry=(P/"entries").read_bytes(); assert entry.endswith(b"\n") and entry.count(b"\n")==1
assert hashlib.sha256(b"\x00"+entry[:-1]).digest()==b64(root.encode())
def witness_sig(line):
    prefix=("— "+wn+" ").encode()
    assert line.startswith(prefix) and line.endswith(b"\n") and line.count(b"\n")==1
    raw=b64(line[len(prefix):-1]); assert len(raw)==76 and raw[:4]==wk
    ts=int.from_bytes(raw[4:12],"big")
    edverify(wp,raw[12:],b"cosignature/v1\ntime "+str(ts).encode()+b"\n"+body)
    return ts
def verify_note(note):
    assert note.startswith(cp)
    line=note[len(cp):]
    ts=witness_sig(line)
    return ts
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None
opener=urllib.request.build_opener(NoRedirect())
def request(url,data=None):
    req=urllib.request.Request(url,data=data,headers={"User-Agent":UA,"Content-Type":"text/plain; charset=utf-8"},method="POST" if data is not None else "GET")
    try:
        with opener.open(req,timeout=25) as r:
            return r.status,r.read(16385)
    except urllib.error.HTTPError as e:
        return e.code,e.read(16385)
out=pathlib.Path("markovian-first-receipt"); out.mkdir(exist_ok=True)
assert os.environ.get("GITHUB_RUN_ATTEMPT")=="1","No automatic repeat"
print("LOCAL_SIGNATURE_AND_MERKLE_ROOT_VERIFIED")
status,prior=request(CHECK)
print("PRECHECK_HTTP",status)
if status==200:
    ts=verify_note(prior)
    (out/"cosigned-checkpoint").write_bytes(prior)
    print("ALREADY_COSIGNED_VERIFIED",ts,"NO_POST")
elif status==404:
    print("ONE_POST_ATTEMPT",flush=True)
    status,reply=request(BASE+"/add-checkpoint",b"old 0\n\n"+cp)
    print("POST_HTTP",status)
    (out/"response.txt").write_bytes(reply)
    if status!=200:
        print("NOT_CONFIRMED; no retry")
        raise SystemExit(1)
    ts=witness_sig(reply)
    (out/"cosigned-checkpoint").write_bytes(cp+reply)
    print("WITNESS_COSIGNATURE_VERIFIED",ts)
    print("PUBLIC_COSIGNATURE",reply.decode().strip())
    status,note=request(CHECK)
    print("READBACK_HTTP",status)
    if status!=200: raise SystemExit("Signed response verified, readback unconfirmed")
    ts2=verify_note(note)
    (out/"readback-checkpoint").write_bytes(note)
    print("READBACK_VERIFIED",ts2)
else:
    raise SystemExit("Precheck not 404; no POST")
print("COSIGNED_NOTE_SHA256",hashlib.sha256((out/"cosigned-checkpoint").read_bytes()).hexdigest())
