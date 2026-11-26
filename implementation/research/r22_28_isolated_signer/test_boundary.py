"""Root-only disposable Linux lab; real distinct UIDs, synthetic key only."""
import concurrent.futures
import hashlib
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import time

S, P, X = 62027, 62028, 62029
assert os.geteuid() == 0
def raw(x): return json.dumps(x, separators=(",", ":"), ensure_ascii=False).encode()
def h(b): return hashlib.sha256(b).hexdigest()
def proc(args, uid, **kw):
    return subprocess.run(args, user=uid, group=uid, extra_groups=[], capture_output=True, timeout=8, **kw)
def check(name, cond):
    if not cond: raise AssertionError(name)
    print("PASS",name,flush=True)
CLIENT = """
import os,socket,sys
s=socket.socket(socket.AF_UNIX);s.settimeout(4);s.connect(sys.argv[1])
s.sendall(sys.stdin.buffer.read());s.shutdown(socket.SHUT_WR)
out=b''
while True:
 try:b=s.recv(8192)
 except ConnectionResetError:
  if not out:sys.exit(5)
  raise
 if not b:break
 out+=b
sys.stdout.buffer.write(out)
"""
with tempfile.TemporaryDirectory(prefix="r22-28-",dir="/tmp") as tmp:
    d=pathlib.Path(tmp);d.chmod(0o755)
    binary=d/"signer";shutil.copyfile(sys.argv[1],binary);binary.chmod(0o755)
    private=d/"private";sockdir=d/"socket";publisher=d/"publisher"
    for path,uid,mode in [(private,S,0o700),(sockdir,S,0o755),(publisher,P,0o700)]:
        path.mkdir();os.chown(path,uid,uid);path.chmod(mode)
    sock=sockdir/"sign.sock";state=private/"state";key=private/"key"
    init=proc([binary,"init",private],S)
    assert init.returncode==0,init.stderr
    g=json.loads(init.stdout);pin=g["Public"];initial=state.read_bytes()
    check("actual_distinct_uid_and_private_modes",S!=P and key.stat().st_uid==S and key.stat().st_mode&0o777==0o600 and private.stat().st_mode&0o777==0o700)
    log=d/"sign.log"; logf=log.open("ab",buffering=0); server=None
    def start():
        global server
        if sock.exists(): sock.unlink()
        server=subprocess.Popen([binary,"serve",private,sock,str(P)],user=S,group=S,extra_groups=[],stdout=logf,stderr=logf)
        for _ in range(100):
            if server.poll() is not None: raise RuntimeError("server exited")
            if sock.exists() and sock.stat().st_mode&0o777==0o666: return
            time.sleep(.02)
        raise RuntimeError("socket not ready")
    def stop():
        global server
        if server and server.poll() is None: server.kill();server.wait(timeout=5)
    def rpc(q,uid=P):
        b=raw(q) if isinstance(q,dict) else q
        r=proc([sys.executable,"-c",CLIENT,sock],uid,input=b)
        if uid!=P and r.returncode==5 and not r.stdout:
            print('UNAUTHORIZED_PEER_TRANSPORT_RESET_NO_RECEIPT',flush=True)
            return {'Status':'HOLD','Receipt':None}
        if r.returncode!=0: raise RuntimeError(r.stderr)
        return json.loads(r.stdout)
    def request(prev,label):
        return {"Generation":prev["Request"]["Generation"]+1,"Previous":h(raw(prev)),"Root":h(label.encode())}
    def signed(q):
        r=rpc(q);assert r["Status"]=="SIGNED_TEST_ONLY",r
        x=r["Receipt"];assert x["Public"]==pin and x["Request"]==q
        f=d/"verify.json";f.write_bytes(raw(x));f.chmod(0o644)
        assert proc([binary,"verify",f],P).returncode==0
        return x
    def hold(q,uid=P):
        return rpc(q,uid)=={"Status":"HOLD","Receipt":None}
    def signs(): return log.read_bytes().splitlines().count(b"SIGN")
    def denied(code,*args):
        r=proc([sys.executable,"-c",code,*map(str,args)],P)
        return r.returncode!=0 and b"PermissionError" in r.stderr
    try:
        start()
        check("server_real_uid",f"Uid:\t{S}\t{S}\t{S}\t{S}" in pathlib.Path(f"/proc/{server.pid}/status").read_text())
        check("publisher_cannot_read_key",denied("import pathlib,sys;pathlib.Path(sys.argv[1]).read_bytes()",key))
        check("publisher_cannot_read_floor",denied("import pathlib,sys;pathlib.Path(sys.argv[1]).read_bytes()",state))
        check("publisher_cannot_overwrite_floor",denied("import pathlib,sys;pathlib.Path(sys.argv[1]).write_bytes(b'old')",state))
        check("publisher_cannot_delete_floor",denied("import os,sys;os.unlink(sys.argv[1])",state))
        check("publisher_cannot_replace_socket",denied("import os,sys;os.unlink(sys.argv[1])",sock))
        check("publisher_cannot_signal_signer",denied("import os,sys;os.kill(int(sys.argv[1]),9)",server.pid))
        check("publisher_cannot_read_signer_mem",denied("import sys;open('/proc/'+sys.argv[1]+'/mem','rb')",server.pid))
        check("publisher_cannot_reprovision_signer_identity",proc([binary,"init",private],P).returncode!=0)
        q=request(g,"first");check("unauthorized_uid_rejected",hold(q,X) and signs()==0)
        check("raw_message_unknown_fields_rejected",hold(b'{"Message":"arbitrary"}') and signs()==0)
        check("duplicate_field_rejected",hold(raw(q)[:-1]+b',"Generation":1}') and signs()==0)
        r1=signed(q);check("authorized_advance_exact_receipt",signs()==1)
        check("exact_retry_no_new_sign",rpc(q)["Receipt"]==r1 and signs()==1)
        check("conflicting_same_generation_rejected",hold(request(g,"fork")) and signs()==1)
        skipped=request(r1,"skip");skipped["Generation"]+=1
        check("skipped_generation_rejected",hold(skipped) and signs()==1)
        # Actual publisher-owned snapshot rollback and deletion, not signer rollback.
        def write_pub(v):
            r=proc([sys.executable,"-c","import sys,pathlib;pathlib.Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read())",publisher/"state"],P,input=raw(v));assert r.returncode==0
        write_pub(g);write_pub(r1);write_pub(g)
        check("publisher_state_rollback_cannot_lower_floor",hold(request(g,"rolled back")) and signs()==1)
        assert proc([sys.executable,"-c","import os,sys;os.unlink(sys.argv[1])",publisher/"state"],P).returncode==0
        check("missing_publisher_state_no_genesis_fallback",hold(request(g,"lost")) and signs()==1)
        # SIGKILL and genuine restart with retained signer-owned state.
        stop();start()
        check("restart_exact_retry_no_resign",rpc(q)["Receipt"]==r1 and signs()==1)
        a,b=request(r1,"A"),request(r1,"B")
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            responses=list(pool.map(rpc,[a,b]))
        winners=[x["Receipt"] for x in responses if x["Status"]=="SIGNED_TEST_ONLY"]
        check("concurrent_publishers_only_one_winner",len(winners)==1 and signs()==2 and any(x["Status"]=="HOLD" for x in responses))
        r2=winners[0];saved=state.read_bytes()
        stop();state.unlink();start()
        check("signer_state_missing_fails_closed",hold(request(r2,"next")) and signs()==2)
        stop();state.write_bytes(saved);os.chown(state,S,S);state.chmod(0o600);start()
        check("restored_exact_signer_state_can_continue",signed(request(r2,"third"))["Request"]["Generation"]==3 and signs()==3)
        # Explicit RED: root controls the signer filesystem and can restore state
        # while retaining the same key. This is not a successful protection.
        stop();state.write_bytes(initial);os.chown(state,S,S);state.chmod(0o600);start()
        fork=signed(request(g,"root restored genesis"))
        check("RED_root_rollback_conflicting_valid_receipts",fork["Public"]==r1["Public"] and fork["Request"]["Generation"]==r1["Request"]["Generation"] and fork["Request"]["Root"]!=r1["Request"]["Root"] and signs()==4)
        check("RED_root_can_read_exportable_key",len(key.read_bytes())==64)
        print("R22_28_BOUNDARY_COMPLETE RESEARCH_ONLY HOLD KEY_ISOLATION_FROM_ROOT_NOT_ESTABLISHED",flush=True)
    finally:
        stop();logf.close()
