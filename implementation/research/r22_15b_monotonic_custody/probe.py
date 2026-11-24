"""Disposable Linux UID boundary test with real external TEST receipts."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import custody as c

PUB=65534
WIT=65533
def main(source,pin,verifier,scanner):
    assert os.geteuid()==0 and sys.platform.startswith("linux")
    source,pin,verifier,scanner=map(Path,(source,pin,verifier,scanner))
    with tempfile.TemporaryDirectory(prefix="r22-15b-",dir="/tmp") as td:
        root=Path(td);root.chmod(0o755)
        for name,src in (("custody.py",Path(c.__file__)),("sigsum-verify",verifier),("scanner",scanner),
                         ("pin.json",pin),("key.pub",source/"key.pub")):
            dst=root/name;shutil.copyfile(src,dst);dst.chmod(0o555 if name in ("sigsum-verify","scanner") else 0o444)
        pub,wit=root/"publisher",root/"witness"
        for p,uid,mode in ((pub,PUB,0o755),(wit,WIT,0o700)):
            p.mkdir();os.chown(p,uid,uid);p.chmod(mode)
        for name in ("four","six"):
            dst=pub/name;shutil.copytree(source/name,dst)
            for p in [dst,*dst.iterdir()]:
                os.chown(p,PUB,PUB);p.chmod(0o755 if p.is_dir() else 0o644)
        state=wit/"floor.json"
        def child(uid,code,*args):
            return subprocess.run([sys.executable,"-I","-B","-c",code,*map(str,args)],cwd=root,
                 user=uid,group=uid,extra_groups=[],env={"PATH":"/usr/bin:/bin","HOME":str(root)},
                 capture_output=True,text=True,timeout=400,check=True).stdout.strip()
        def call(action,candidate,expected,crash=False):
            p=subprocess.run([sys.executable,"-I","-B",str(root/"custody.py"),"request",action,str(state),str(candidate),
                  str(root/"key.pub"),str(root/"sigsum-verify"),str(root/"scanner"),str(root/"pin.json"),"crash" if crash else "normal"],
                  cwd=root,user=WIT,group=WIT,extra_groups=[],env={"PATH":"/usr/bin:/bin","HOME":str(root)},
                  capture_output=True,text=True,timeout=400)
            assert p.returncode==(75 if crash else 0),(p.returncode,p.stdout,p.stderr)
            if not crash: assert p.stdout.strip()==expected,(p.stdout,p.stderr,expected)
            print(json.dumps({"case":action,"expected":expected,"exit":p.returncode}),flush=True)
        four,six=pub/"four",pub/"six"
        call("assess",four,"HOLD_MISSING_RETAINED_STATE")
        call("bootstrap",four,"PROVISIONED_4_LAB_ONLY")
        old=state.read_bytes()
        call("assess",four,"MATCH_RETAINED_NOT_FRESHNESS")
        call("assess",six,"HOLD_HISTORY_MISMATCH")
        call("bootstrap",six,"HOLD_ALREADY_PROVISIONED")
        mutate="from pathlib import Path;import sys;p=Path(sys.argv[1]);p.write_bytes(bytes.fromhex(sys.argv[2]))"
        clean=(six/"ledger.jsonl").read_bytes()
        child(PUB,mutate,six/"ledger.jsonl",(clean+b"x").hex())
        call("advance",six,"HOLD_INVALID_OR_UNAVAILABLE_EVIDENCE")
        assert state.read_bytes()==old
        child(PUB,mutate,six/"ledger.jsonl",clean.hex())
        call("advance",six,"COMMITTED_RESPONSE_LOST",crash=True)
        current=state.read_bytes(); assert current!=old
        retained=c.parse(current)
        assert retained["current"]["envelope"]["record"]["seq"]==6 and retained["live_tree"] is not None
        assert state.stat().st_uid==WIT
        call("advance",six,"MATCH_RETAINED_NOT_FRESHNESS")
        assert state.read_bytes()==current
        # The publisher controls all its own files. Restore its complete directory
        # to the original four-record snapshot; retained file and lock stay outside it.
        restore="""from pathlib import Path
import shutil,sys
p=Path(sys.argv[1]);shutil.rmtree(p/'six')
shutil.copytree(p/'four',p/'six')
print('PUBLISHER_RESTORED')
"""
        assert child(PUB,restore,pub)=="PUBLISHER_RESTORED"
        call("assess",six,"HOLD_HISTORY_MISMATCH")
        call("advance",six,"HOLD_NON_ADVANCING")
        call("bootstrap",four,"HOLD_ALREADY_PROVISIONED")
        attack="""import os,sys
from pathlib import Path
f,p,k=map(Path,sys.argv[1:4])
staged=p/'old-floor.json';staged.write_bytes(bytes.fromhex(sys.argv[4]))
def tryit(fn):
    try:fn()
    except PermissionError:return 'DENIED'
    return 'UNEXPECTED_SUCCESS'
for fn in (lambda:f.read_bytes(),lambda:f.write_bytes(staged.read_bytes()),lambda:os.replace(staged,f),lambda:f.unlink(),lambda:f.chmod(0o666),lambda:f.parent.rename(p/'witness'),lambda:(f.parent/'lock').unlink(),lambda:k.write_bytes(b'bad')):
    print(tryit(fn))
"""
        denied=child(PUB,attack,state,pub,root/"key.pub",old.hex()).splitlines()
        assert denied==["DENIED"]*8,denied
        assert state.read_bytes()==current
        # Fresh process, valid six bytes reintroduced from supervisor's withheld copy.
        child(PUB,mutate,six/"ledger.jsonl",clean.hex())
        call("assess",six,"MATCH_RETAINED_NOT_FRESHNESS")
        assert state.read_bytes()==current
        # Real common-root reset, explicitly not a security success.
        state.write_bytes(old)
        call("assess",four,"MATCH_RETAINED_NOT_FRESHNESS")
        print(json.dumps(dict(result="R22_15B_UID_CUSTODY_ADVANCE_RESTART_PASS",
            publisher_access_denials=len(denied),retained_seq=6,retained_sha256=c.sha(current),
            live_tree=retained["live_tree"],signed_commitment=retained["current"]["proof"],
            ledger_sha256=retained["current"]["envelope"]["record"]["ledger_sha256"],
            response_lost_recovered=True,publisher_rollback_rejected=True,common_root_reset_residual=True,
            independent_administration="NOT_ESTABLISHED",signer_continuity="NOT_ESTABLISHED",history_truth="UNKNOWN",
            trust_activation="NO_GO",production="NO_GO",merge_authorized=False),sort_keys=True),flush=True)
if __name__=="__main__":main(*sys.argv[1:])
