"""R63 G3: synthetic-only Windows witness under restricted writer token.

- Source-pinned genuine frozen V9 V2 sidecar and canonical V1 journal.
- Independent loopback RPC writer process; restricted readers have only read ACL.
- Win32 cooperative exclusive lockfile for concurrency, DACL for direct denial.
- Pre-V2/post-V2/post-V1 process exits with durable uncertainty marker.
- No V9 signer, CNG, real actor/keys, independent admin custody, or atomic 2-file commit.
"""
from __future__ import annotations
import concurrent.futures
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import socket
import socketserver
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spend_chain_v2 as sidecar

PIN = 'c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd'
ROW0 = [('a'*64, '1'*64), ('b'*64, '2'*64)]
PHASES = ('pre_v2', 'post_v2', 'post_v1')
MAXLINE = 384
WINDOWS = os.name == 'nt'


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def exact_source():
    if sha(Path(sidecar.__file__).read_bytes()) != PIN:
        raise RuntimeError('FROZEN_V9_V2_SOURCE_MISMATCH')


def canonical_v1(pairs):
    return b''.join(sidecar.canonical(list(p))+b'\n' for p in pairs)


def durable_new(path: Path, data: bytes):
    with path.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def durable_append(path: Path, data: bytes):
    with path.open('ab') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def prepare(case: Path):
    exact_source()
    case.mkdir(parents=True, exist_ok=False)
    journal = b''
    for nonce,ident in ROW0:
        journal,result=sidecar.append(journal,nonce,ident)
        if result != 'NEW_NEEDS_DURABLE_APPEND':
            raise RuntimeError('INITIAL_STATE_WRONG')
    durable_new(case/'v1.jsonl',canonical_v1(ROW0))
    durable_new(case/'v2.jsonl',journal)
    durable_new(case/'journal.lock',b'')
    return inspect(case)


def inspect(case:Path):
    raw1=(case/'v1.jsonl').read_bytes()
    raw2=(case/'v2.jsonl').read_bytes()
    state=sidecar.review(raw2)
    intact = (raw1 == canonical_v1(state.pairs))
    if raw1 and not raw1.endswith(b'\n'):
        intact = False
    flag=(case/'uncertain.flag').read_bytes() if (case/'uncertain.flag').exists() else None
    return {
        'v1_lines':len(raw1.splitlines()),'v2_events':state.seq,
        'v1_sha256':sha(raw1),'v2_sha256':sha(raw2),
        'v2_head':state.head,'coherent':intact,
        'flag_present':flag is not None,
        'flag_sha256':sha(flag) if flag is not None else None,
        'flag_len':len(flag) if flag is not None else None,
    }


class ExclusiveFile:
    """Share-mode-zero Win32 file lock for cooperating writer operations only."""
    def __init__(self, path:Path, wait_s:float=5):
        self.path=str(path)
        self.wait_s=wait_s
        self.handle=None
    def __enter__(self):
        if not WINDOWS:
            raise RuntimeError('WIN32_LOCK_REQUIRES_WINDOWS')
        k=ctypes.WinDLL('kernel32',use_last_error=True)
        create=k.CreateFileW
        create.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,
                         ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
        create.restype=wintypes.HANDLE
        self._close=k.CloseHandle
        self._close.argtypes=[wintypes.HANDLE]
        self._close.restype=wintypes.BOOL
        bad=ctypes.c_void_p(-1).value
        end=time.monotonic()+self.wait_s
        while True:
            h=create(self.path,0xc0000000,0,None,3,128,None) # OPEN_EXISTING
            if h not in (None,bad):
                self.handle=h
                return self
            e=ctypes.get_last_error()
            if e not in (32,33):
                raise OSError(e,'CreateFileW OS lock (file ACL may deny)')
            if time.monotonic()>end:
                raise TimeoutError('OS_LOCK_BUSY')
            time.sleep(.015)
    def __exit__(self,*exc):
        if self.handle is not None:
            self._close(self.handle)
            self.handle=None


def token_info():
    if not WINDOWS:
        return {'sid':'NON_WINDOWS_TEST','is_admin':False,'pid':os.getpid()}
    import ctypes.wintypes
    # whoami under the *actual* child process token, no self-stated role label.
    r=subprocess.run(['whoami.exe','/user','/fo','csv','/nh'],text=True,
                     capture_output=True,timeout=10)
    if r.returncode:
        raise RuntimeError('WHOAMI_SID_READBACK_FAILED')
    import csv,io
    row=next(csv.reader(io.StringIO(r.stdout)))
    if len(row)<2 or not row[1].startswith('S-1-5-'):
        raise RuntimeError('INVALID_CHILD_TOKEN_SID')
    return {'sid':row[1], 'username':row[0], 'pid':os.getpid()}


def request_once(case:Path, nonce:str, ident:str, *, expect_crash=False):
    port=int((case/'port.txt').read_text('ascii'))
    msg=json.dumps({'op':'reserve','nonce':nonce,'id':ident},
                   sort_keys=True,separators=(',',':')).encode()+b'\n'
    try:
        with socket.create_connection(('127.0.0.1',port),timeout=8) as s:
            s.settimeout(8)
            s.sendall(msg)
            s.shutdown(socket.SHUT_WR)
            raw=s.recv(1024)
        if not raw and expect_crash:
            return 'NO_ACK'
        return raw.decode('ascii').strip()
    except (ConnectionResetError, ConnectionAbortedError):
        if expect_crash:
            return 'NO_ACK'
        raise


class WitnessServer(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=False
    request_queue_size=128


def handler(case:Path,phase:str):
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            try:
                with self.request.makefile('rb') as f:
                    request=f.readline(MAXLINE+1)
                if len(request)>MAXLINE or not request.endswith(b'\n'):
                    self.request.sendall(b'HOLD_INVALID\n');return
                obj=json.loads(request)
                if type(obj) is not dict or set(obj)!={'op','nonce','id'} or obj['op']!='reserve':
                    self.request.sendall(b'HOLD_INVALID\n');return
                n,k=obj['nonce'],obj['id']
                if not sidecar.ishash(n) or not sidecar.ishash(k):
                    self.request.sendall(b'HOLD_INVALID\n');return
                with ExclusiveFile(case/'journal.lock'):
                    if (case/'uncertain.flag').exists():
                        self.request.sendall(b'HOLD_UNCERTAIN\n');return
                    raw1=(case/'v1.jsonl').read_bytes()
                    raw2=(case/'v2.jsonl').read_bytes()
                    state=sidecar.review(raw2)
                    if raw1!=canonical_v1(state.pairs):
                        self.request.sendall(b'HOLD_UNCERTAIN\n');return
                    if phase=='recovery':
                        # No cryptographically verified historical receipt in this test.
                        self.request.sendall(b'HOLD_UNCERTAIN\n');return
                    if (n,k) in state.pairs:
                        self.request.sendall(b'ALREADY_RESERVED_NO_APPEND\n');return
                    if any(a==n or b==k for a,b in state.pairs):
                        self.request.sendall(b'HOLD_DUPLICATE_CONFLICT\n');return
                    next2,status=sidecar.append(raw2,n,k)
                    if status!='NEW_NEEDS_DURABLE_APPEND':
                        self.request.sendall(b'HOLD_UNCERTAIN\n');return
                    if phase in PHASES:
                        durable_new(case/'uncertain.flag',
                            ('SYNTHETIC_CRASH_WINDOW='+phase+'\n').encode())
                        if phase!='pre_v2':
                            durable_append(case/'v2.jsonl',next2[len(raw2):])
                        if phase=='post_v1':
                            durable_append(case/'v1.jsonl',sidecar.canonical([n,k])+b'\n')
                        os._exit(73)
                    if phase!='normal':
                        self.request.sendall(b'HOLD_INVALID_PHASE\n');return
                    # Deliberately two separate fsynced files: process death can split.
                    durable_append(case/'v2.jsonl',next2[len(raw2):])
                    durable_append(case/'v1.jsonl',sidecar.canonical([n,k])+b'\n')
                    self.request.sendall(b'RESERVED_ONLY_NO_SIGN\n')
            except (ValueError,OSError,TimeoutError,TypeError,RuntimeError):
                try:self.request.sendall(b'HOLD_UNCERTAIN\n')
                except OSError:pass
    return Handler


def server(case:Path,phase:str,count:int,expected_sid:str):
    exact_source()
    if not WINDOWS:
        raise RuntimeError('WINDOWS_GUEST_CI_ONLY')
    identity=token_info()
    if identity['sid']!=expected_sid:
        raise RuntimeError('WRITER_TOKEN_SID_MISMATCH')
    if phase not in ('normal','recovery',*PHASES):
        raise RuntimeError('INVALID_PHASE')
    with WitnessServer(('127.0.0.1',0),handler(case,phase)) as s:
        (case/'port.txt').write_text(str(s.server_address[1]),encoding='ascii')
        (case/'writer-identity.json').write_text(json.dumps(identity),encoding='ascii')
        for _ in range(count):
            s.handle_request()


def client_batch(case:Path,n:str,k:str,count:int,expected_sid:str):
    actual=token_info()
    if actual['sid']!=expected_sid:
        raise RuntimeError('READER_TOKEN_SID_MISMATCH')
    # Every request uses a separate native OS child process inheriting this SID.
    def once(_):
        r=subprocess.run([sys.executable,'-I','-B',str(Path(__file__).resolve()),
                 '--client',str(case),n,k,'normal',expected_sid],
                 capture_output=True,text=True,timeout=25)
        if r.returncode:
            raise RuntimeError('CLIENT_PROCESS_FAILED '+r.stderr[-200:])
        return r.stdout.strip()
    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as ex:
        results=list(ex.map(once,range(count)))
    print(json.dumps({'token':actual,'count':count,'replies':results},sort_keys=True))


def restricted_direct(case:Path,expected_sid:str,flag_expected:bool):
    actual=token_info()
    if actual['sid']!=expected_sid:
        raise RuntimeError('READER_TOKEN_SID_MISMATCH')
    # Positive control: restricted reader can actually read the protected records.
    readable = {name: len((case/name).read_bytes()) for name in ('v1.jsonl','v2.jsonl')}
    if flag_expected:
        readable['uncertain.flag'] = len((case/'uncertain.flag').read_bytes())
    attempted={}
    def try_write(name,do):
        try:
            do()
        except PermissionError as exc:
            # On Windows ERROR_ACCESS_DENIED is WinError 5, not sharing violation 32.
            if exc.winerror not in (5,None):
                raise RuntimeError('WRONG_WINERROR '+str(exc.winerror))
            attempted[name]='ACCESS_DENIED'
            return
        raise RuntimeError('DIRECT_WRITE_WAS_ALLOWED '+name)
    try_write('append_v1',lambda:durable_append(case/'v1.jsonl',b'ILLEGAL\n'))
    try_write('append_v2',lambda:durable_append(case/'v2.jsonl',b'ILLEGAL\n'))
    try_write('overwrite_v1',lambda:(case/'v1.jsonl').write_bytes(b'ILLEGAL'))
    try_write('create_sibling',lambda:(case/'illegal.txt').write_bytes(b'ILLEGAL'))
    if flag_expected:
        try_write('delete_flag',lambda:(case/'uncertain.flag').unlink())
    print(json.dumps({'token':actual,'readable':readable,'denials':attempted},sort_keys=True))


def cli():
    args=sys.argv[1:]
    if len(args)==2 and args[0]=='--prepare':
        print(json.dumps(prepare(Path(args[1])),sort_keys=True))
    elif len(args)==2 and args[0]=='--inspect':
        print(json.dumps(inspect(Path(args[1])),sort_keys=True))
    elif len(args)==5 and args[0]=='--server':
        server(Path(args[1]),args[2],int(args[3]),args[4])
    elif len(args)==6 and args[0]=='--batch':
        client_batch(Path(args[1]),args[2],args[3],int(args[4]),args[5])
    elif len(args)==6 and args[0]=='--client':
        if token_info()['sid']!=args[5]:raise RuntimeError('CHILD_SID_MISMATCH')
        print(request_once(Path(args[1]),args[2],args[3],expect_crash=args[4]=='crash'))
    elif len(args)==4 and args[0]=='--direct':
        restricted_direct(Path(args[1]),args[2],args[3]=='flag')
    elif len(args)==1 and args[0]=='--test':
        exact_source()
        import tempfile
        with tempfile.TemporaryDirectory(prefix='ario_r63_g3_pure_') as td:
            case=Path(td)/'case'
            s=prepare(case)
            assert s['v1_lines']==2 and s['v2_events']==2 and s['coherent']
            assert sha((case/'v2.jsonl').read_bytes())==s['v2_sha256']
            raw=(case/'v2.jsonl').read_bytes()
            new,r=sidecar.append(raw,'c'*64,'3'*64)
            assert r=='NEW_NEEDS_DURABLE_APPEND'
            durable_append(case/'v2.jsonl',new[len(raw):])
            assert not inspect(case)['coherent']
        print('PURE_JOURNAL_MODEL=PASS')
    else:
        raise SystemExit('INVALID_ARGS')


if __name__=='__main__':
    cli()
