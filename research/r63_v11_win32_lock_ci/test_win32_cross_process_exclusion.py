"""R63 V11: OS-enforced Windows CreateFileW file-share exclusion, independent PIDs.

This is a compact primitive audit, not the full Sandbox witness RPC driver.
All operations on disposable CI temp files. No signer, service, key or ACL.
"""
from __future__ import annotations
import concurrent.futures,ctypes,hashlib,json,os,pathlib,subprocess,sys,time
from ctypes import wintypes
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"r63_v10_source_gate"))
import spend_chain_v2 as v2
K=ctypes.WinDLL("kernel32",use_last_error=True)
OPEN=K.CreateFileW
OPEN.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
OPEN.restype=wintypes.HANDLE
CLOSE=K.CloseHandle
CLOSE.argtypes=[wintypes.HANDLE]
CLOSE.restype=wintypes.BOOL
BAD=ctypes.c_void_p(-1).value
PIN="c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd"

class Lock:
    def __init__(self,root,seconds=3):
        self.path=str(root/"win32.lock");self.seconds=seconds
        self.handle=None
    def __enter__(self):
        end=time.monotonic()+self.seconds
        while True:
            h=OPEN(self.path,0xc0000000,0,None,4,128,None)
            if h not in (None,BAD):
                self.handle=h
                return self
            err=ctypes.get_last_error()
            if err not in (32,33):raise OSError(err,"CreateFileW")
            if time.monotonic()>=end:raise TimeoutError("OS_LOCK_BUSY")
            time.sleep(.015)
    def __exit__(self,*args):
        if self.handle is not None:
            CLOSE(self.handle)
            self.handle=None

def durable(path,raw,append=False):
    with path.open("ab" if append else "xb") as f:
        f.write(raw);f.flush();os.fsync(f.fileno())

def child(root,op,n,k):
    with Lock(root,5):
        v1=(root/"v1").read_bytes()
        v2raw=(root/"v2").read_bytes()
        state=v2.review(v2raw)
        if v1!=b"".join(v2.canonical(list(p))+b"\n" for p in state.pairs):
            print("HOLD_UNCERTAIN");return
        if any(a==n or b==k for a,b in state.pairs):
            print("DUPLICATE");return
        new,kind=v2.append(v2raw,n,k)
        if kind!="NEW_NEEDS_DURABLE_APPEND":raise RuntimeError("INVALID_APPEND")
        durable(root/"v2",new[len(v2raw):],True)
        durable(root/"v1",v2.canonical([n,k])+b"\n",True)
        print("RESERVED_ONLY")

def holder(root):
    with Lock(root,5):
        durable(root/"ready",str(os.getpid()).encode())
        time.sleep(3.0)
        os._exit(73)

def launch(root,op,n,k):
    cmd=[sys.executable,"-B",str(pathlib.Path(__file__)),"--client",str(root),op,n,k]
    p=subprocess.run(cmd,capture_output=True,timeout=25)
    if p.returncode!=0:raise RuntimeError("child failed: "+str(p.stderr[-300:]))
    return p.stdout.decode().strip()

def test():
    if os.getenv("RUNNER_OS")!="Windows" or os.getenv("GITHUB_REPOSITORY")!="SepehrGhanbari/Ario":
        raise RuntimeError("REFUSE_NON_WINDOWS_CI")
    if hashlib.sha256(pathlib.Path(v2.__file__).read_bytes()).hexdigest()!=PIN:
        raise RuntimeError("FROZEN_SOURCE_MISMATCH")
    root=pathlib.Path(os.environ["RUNNER_TEMP"])/"r63-v11-win32-exclusion"
    root.mkdir(exist_ok=False)
    durable(root/"v1",b"")
    durable(root/"v2",b"")
    p=subprocess.Popen([sys.executable,"-B",str(pathlib.Path(__file__)),"--holder",str(root)])
    deadline=time.monotonic()+12
    while time.monotonic()<deadline and not (root/"ready").exists():
        if p.poll() is not None:raise RuntimeError("holder exited early")
        time.sleep(.02)
    if not (root/"ready").exists():raise RuntimeError("holder readiness timeout")
    blocked=False
    try:
        with Lock(root,.2):pass
    except TimeoutError:blocked=True
    if not blocked:raise RuntimeError("OS_LOCK_BYPASSED_BY_SECOND_PROCESS")
    # Counterexample: locking a *different* lockfile does NOT stop
    # an uncooperative process from modifying a journal file directly.
    if p.poll() is not None:
        raise RuntimeError("holder already dead before uncooperative-writer probe")
    q=subprocess.run([sys.executable,"-B",str(pathlib.Path(__file__)),
                      "--intruder",str(root)],capture_output=True,timeout=10)
    if q.returncode!=0 or (root/"v1").read_bytes()!=b"X":
        raise RuntimeError("uncooperative-writer counterexample not reproduced")
    if p.poll() is not None:
        raise RuntimeError("holder exited during uncooperative-writer probe")
    (root/"v1").write_bytes(b"")
    print("UNCOOPERATIVE_WRITER_CAN_BYPASS_LOCK=EXPECTED_COUNTEREXAMPLE")
    if p.wait(timeout=10)!=73:raise RuntimeError("wrong holder exit")
    with Lock(root,.5):pass
    print("EXCLUSIVE_WIN32_SECOND_PROCESS_BLOCKED=PASS")
    print("CRASH_RELEASED_OS_LOCK=PASS")
    totals=[]
    for count in (2,8,16):
        nonce=format(5000+count,"064x");ident=format(6000+count,"064x")
        with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:
            replies=list(pool.map(lambda _:launch(root,"reserve",nonce,ident),range(count)))
        if replies.count("RESERVED_ONLY")!=1 or replies.count("DUPLICATE")!=count-1:
            raise RuntimeError("concurrent append incorrect: "+repr(replies))
        raw1=(root/"v1").read_bytes();raw2=(root/"v2").read_bytes()
        state=v2.review(raw2)
        if len(raw1.splitlines())!=state.seq or state.seq!=len(totals)+1:
            raise RuntimeError("source state mismatch")
        totals.append(count)
        print("MULTIPROCESS_CLIENTS_"+str(count)+"=PASS")
    print("CROSS_PROCESS_EXCLUSION=PASS")
    print("SOURCE_V9_V2_SHA256="+PIN)
    print("NATIVE_V9_RPC_PARENT=NOT_EXECUTED")
    print("INDEPENDENT_ADMIN_CUSTODY=NOT_ESTABLISHED")
    print("CNG_OR_SIGNER_USED=NO")

if __name__=="__main__":
    if sys.argv[1:2]==["--holder"] and len(sys.argv)==3:
        holder(pathlib.Path(sys.argv[2]))
    elif sys.argv[1:2]==["--client"] and len(sys.argv)==6:
        child(pathlib.Path(sys.argv[2]),sys.argv[3],sys.argv[4],sys.argv[5])
    elif sys.argv[1:2]==["--intruder"] and len(sys.argv)==3:
        with (pathlib.Path(sys.argv[2])/"v1").open("ab") as fd:
            fd.write(b"X")
            fd.flush()
            os.fsync(fd.fileno())
    elif sys.argv[1:]==["--ci"]:
        test()
    else:raise SystemExit("invalid args")
