#!/usr/bin/env python3
"""ARIO INTEGRITY GATE V1: explicit research-only acquisition and restore.
Run from a separately trusted package with python -I -B. Received archives are never executed.
Only explicit startup-probe and runtime-audit modes run fixed pinned checkouts; runtime-audit accepts data-only M0 input.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import types
import unicodedata
import zipfile

HERE = Path(__file__).resolve().parent
COMMIT = '89ef7ba466db2e7a267ee7780df348ee9e5920e6'
TREE = '7b1566d33a52b5bb609976f94501bc63f69d2a09'
COUNT, TOTAL = 473, 96396968
# Preserve the tested V1 pin. This separate pin selects the existing merged runtime.
RUNTIME_COMMIT = 'f158695b60bd2c10061531f6cc56e2ed12db1ca0'
RUNTIME_TREE = 'c5c374fce05e0bbc17193ae00dffc67525ed201b'
RUNTIME_COUNT, RUNTIME_TOTAL = 636, 97610980
RUNTIME_INPUT_MAX = 20_000
SOURCE = '05ba5c960aaea96fc6bb80504b53b4d47e7d42f5'
SOURCE_TREE = '8a9429d396c09fe17682a61dd91cb43672d3cb79'
SOURCE_COUNT, SOURCE_TOTAL = 204, 16183258
REPO = 'https://github.com/SepehrGhanbari/Ario.git'
DEPS = {'ario_verified_release': '4ed09089c5f8cd3ad3999155bded21f7391921bff152f730a82fc692848fef46',
        'ario_verify_coverage': '40ceabfd72f4b9779e19b35cb1f599f83a6ea2c91901267fbc1ac30fbdc3bdba'}
ASSETS = {'ario-full.zip': (6524694,'d11269dc593f9cbb70e7d622a8acc31d0fe36d292a935225aca6b8f98d5c5d51'),
          'ario-full.txt': (17751878,'86aafca0e20fb356bdee14c05815d017b3212ef68afed8757fa16f1a1b746af6'),
          'ario-manifest.json': (63205,'f86fb10ef3eb71dd6e3c348b3f0c9b42c88b3837ae889918c33d8f5d62fe11d8')}
QUAL = ('RESEARCH_ONLY; verified preparation, not execution authorization, publisher identity, '
        'independent custody, atomic filesystem snapshot, freshness, or protection against hostile local OS/runtime. '
        'Checkout checks Git SHA-1 raw worktree bytes, excludes .git and does not attest modes/history. '
        'Explicit startup probe is synthetic M0; runtime-audit is bounded M0 only. No general runtime enforcement or sandbox guarantee.')
class Unknown(Exception): pass
class Rejected(Exception): pass

def sha(data): return hashlib.sha256(data).hexdigest()
def link(st): return stat.S_ISLNK(st.st_mode) or bool(getattr(st,'st_file_attributes',0)&1024)
def stamp(st): return st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns

def read_regular(path, limit, exact=None):
    """Read bounded regular bytes; refuse observed links, races and special files."""
    try:
        before=path.lstat()
        if link(before) or not stat.S_ISREG(before.st_mode): raise Rejected('not a regular file')
        if before.st_size>limit or (exact is not None and before.st_size!=exact): raise Rejected('file size differs or exceeds limit')
        fd=os.open(path,os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NONBLOCK',0)|getattr(os,'O_NOFOLLOW',0))
        with os.fdopen(fd,'rb') as f:
            first=os.fstat(f.fileno())
            if not stat.S_ISREG(first.st_mode) or stamp(first)!=stamp(before): raise Unknown('file changed before read')
            data=f.read(limit+1)
            if len(data)!=before.st_size or stamp(os.fstat(f.fileno()))!=stamp(first): raise Unknown('file changed during read')
        last=path.lstat()
        if link(last) or stamp(last)!=stamp(before): raise Unknown('file path changed')
        return data
    except OSError as e: raise Unknown('file unavailable') from e

def real_dir(path):
    path=path.absolute()
    try: st=path.lstat()
    except OSError as e: raise Unknown('directory unavailable') from e
    if link(st) or not stat.S_ISDIR(st.st_mode): raise Rejected('not a real directory')
    return path

def load_dep(name):
    p=HERE/(name+'.py'); data=read_regular(p,65536)
    if sha(data)!=DEPS[name]: raise Rejected('trusted helper pin mismatch: '+name)
    mod=types.ModuleType(name); mod.__file__=str(p)
    exec(compile(data,str(p),'exec'),mod.__dict__) # ONLY exact, trusted helper bytes, never input
    return mod

def exact_asset(asset,data):
    if asset not in ASSETS: raise Unknown('unsupported historical asset')
    n,h=ASSETS[asset]
    if len(data)!=n or sha(data)!=h: raise Rejected('pinned release asset SHA-256 mismatch')
    return data

def verify_release_bytes(rel,asset,data,scratch):
    exact_asset(asset,data)
    # Run the previously reviewed R1.4 on a private copy, then keep the same
    # immutable data object for parsing. No reuse of the original pathname.
    verifier=scratch/'r14.py'
    if not verifier.exists():
        verifier.write_bytes(rel.pinned_verifier())
    elif sha(read_regular(verifier,65536))!=rel.VERIFIER_SHA: raise Rejected('R1.4 temporary copy changed')
    target=scratch/asset
    with target.open('xb') as f: f.write(data)
    result=rel.verify_asset(verifier,asset,target)
    if sha(read_regular(target,ASSETS[asset][0],ASSETS[asset][0]))!=ASSETS[asset][1]: raise Rejected('staged bytes changed')
    return result

def require_checkout(cov,root,commit):
    if not cov.hex40(commit): raise Unknown('exact commit SHA required')
    report=cov.check_checkout(real_dir(root),commit)
    state=report.get('status')
    if state=='REJECTED': raise Rejected('checkout bytes or extra paths differ')
    n=report.get('expected_files'); b=report.get('expected_bytes')
    if (state!='TRACKED_FILE_BYTES_MATCH_GITHUB_TREE' or report.get('commit')!=commit or
        not cov.hex40(report.get('tree')) or type(n) is not int or n<=0 or type(b) is not int or b<0 or
        type(report.get('matched_files')) is not int or report['matched_files']!=n or
        report.get('problems')!=[] or report.get('extra_paths')!=[]): raise Unknown('incomplete checkout evidence')
    expected={COMMIT:(TREE,COUNT,TOTAL),SOURCE:(SOURCE_TREE,SOURCE_COUNT,SOURCE_TOTAL),
              RUNTIME_COMMIT:(RUNTIME_TREE,RUNTIME_COUNT,RUNTIME_TOTAL)}.get(commit)
    if expected and (report['tree'],n,b)!=expected: raise Unknown('checkout differs from pinned tree/count/bytes')
    return report

def safe_git(root,control,commit):
    if not re.fullmatch('[0-9a-f]{40}',commit): raise Unknown('exact commit SHA required')
    git=shutil.which('git')
    if not git: raise Unknown('Git not installed')
    # Resolve trusted Git before any working-directory change. Never run a
    # command from the downloaded tree; no hooks, global config, or submodules.
    git=str(Path(git).absolute())
    empty=control/'empty'; empty.mkdir(); config=control/'empty-config'; config.touch()
    env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_SYSTEM=str(config),GIT_CONFIG_GLOBAL=str(config),
               GIT_TERMINAL_PROMPT='0',GIT_ASKPASS='',GIT_ALLOW_PROTOCOL='https',GIT_LFS_SKIP_SMUDGE='1',
               HOME=str(control),XDG_CONFIG_HOME=str(control))
    options=['-c','core.hooksPath='+str(empty),'-c','core.autocrlf=false','-c','core.symlinks=false',
             '-c','credential.helper=','-c','http.followRedirects=false','-c','fetch.fsckObjects=true',
             '-c','protocol.allow=never','-c','protocol.https.allow=always']
    def run(*args):
        try:
            p=subprocess.run([git,*options,'-C',str(root),*args],env=env,stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=300,check=False)
        except (OSError,subprocess.TimeoutExpired) as e: raise Unknown('Git operation unavailable') from e
        if p.returncode: raise Unknown('Git operation failed: '+args[0])
        return p.stdout
    run('init','--template='+str(empty))
    run('fetch','--depth=1','--no-tags','--no-recurse-submodules',REPO,commit)
    if run('rev-parse','FETCH_HEAD').strip()!=commit.encode(): raise Unknown('fetched commit differs')
    # Check out only the explicitly selected commit, never submodules.
    run('checkout','--detach','--no-recurse-submodules',commit)
    if run('rev-parse','HEAD').strip()!=commit.encode(): raise Unknown('checked-out commit differs')

def run_synthetic_audit(root):
    """Fixed research startup only, explicitly invoked after pinned clone check."""
    with tempfile.TemporaryDirectory(prefix='ario-startup-probe-') as d:
        scratch=Path(d); request=scratch/'request.json'
        audit_id='ARIO-INTEGRITY-GATE-SYNTHETIC'
        request.write_text(json.dumps({'audit_id':audit_id,'rule_versions':['M0-1.0'],
            'configuration_id':'INTEGRITY-GATE-RESEARCH', 'execution_timestamp':'SYNTHETIC-TIME',
            'artifacts':{}}),encoding='utf-8')
        # No caller-provided script, input, ledger, environment secrets or args.
        # This is NOT an OS sandbox. Only the fixed, owner-selected official pin.
        bootstrap=('import runpy,sys,pathlib; p=pathlib.Path(sys.argv[1]); '
                   'sys.path.insert(0,str(p.parent)); sys.argv=[str(p),"--input",sys.argv[2]]; '
                   'runpy.run_path(str(p),run_name="__main__")')
        env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','COMSPEC','PATHEXT','LANG','LC_ALL'}}
        env.update(HOME=str(scratch),USERPROFILE=str(scratch),TMP=str(scratch),TEMP=str(scratch),TMPDIR=str(scratch))
        try:
            p=subprocess.run([sys.executable,'-I','-B','-S','-c',bootstrap,
                              str(root/'implementation/ario_cli.py'),str(request)],
                             cwd=scratch,env=env,stdin=subprocess.DEVNULL,capture_output=True,timeout=60,check=False)
            if p.returncode or len(p.stdout)>1024*1024: raise Unknown('synthetic startup probe failed')
            result=parse_json(p.stdout)
            if not isinstance(result,dict) or result.get('audit_id')!=audit_id or result.get('verdict')!='UNKNOWN':
                raise Unknown('unexpected synthetic audit result')
        except (OSError,subprocess.TimeoutExpired) as e: raise Unknown('synthetic startup unavailable') from e
        return {'audit_id':audit_id,'verdict':'UNKNOWN','scope':'SYNTHETIC_M0_NO_LEDGER'}

def run_runtime_audit(root, raw):
    """Run only the pinned M0 CLI on a private copy of explicitly supplied JSON."""
    if type(raw) is not bytes or len(raw)>RUNTIME_INPUT_MAX:
        raise Rejected('runtime audit input size exceeds bound')
    request_data=parse_json(raw)
    if not isinstance(request_data,dict) or type(request_data.get('audit_id')) is not str:
        raise Rejected('runtime audit requires an M0 request object with audit_id')
    with tempfile.TemporaryDirectory(prefix='ario-runtime-audit-') as d:
        scratch=Path(d); request=scratch/'request.json'
        with request.open('xb') as f: f.write(raw)
        bootstrap=('import runpy,sys,pathlib; p=pathlib.Path(sys.argv[1]); '
                   'sys.path.insert(0,str(p.parent)); sys.argv=[str(p),"--input",sys.argv[2]]; '
                   'runpy.run_path(str(p),run_name="__main__")')
        env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','COMSPEC','PATHEXT','LANG','LC_ALL'}}
        env.update(HOME=str(scratch),USERPROFILE=str(scratch),TMP=str(scratch),TEMP=str(scratch),TMPDIR=str(scratch),
                   PYTHONIOENCODING='utf-8')
        try:
            child=subprocess.run([sys.executable,'-I','-B','-S','-X','utf8','-c',bootstrap,
                                  str(root/'implementation/ario_cli.py'),str(request)],
                                 cwd=scratch,env=env,stdin=subprocess.DEVNULL,capture_output=True,timeout=60,check=False)
        except (OSError,subprocess.TimeoutExpired) as e:
            raise Unknown('runtime audit unavailable') from e
        if child.returncode or len(child.stdout)>1024*1024:
            raise Unknown('runtime audit did not return a bounded result')
        result=parse_json(child.stdout)
        if (not isinstance(result,dict) or result.get('audit_id')!=request_data['audit_id']
                or result.get('verdict') not in ('PASS','FAIL','UNKNOWN')
                or type(result.get('violations')) is not list
                or type(result.get('verdict_basis')) is not str):
            raise Unknown('unexpected runtime audit result')
        return result

def unique(pairs):
    d={}
    for k,v in pairs:
        if k in d: raise Rejected('duplicate JSON key')
        d[k]=v
    return d

def parse_json(data):
    def bad(_): raise Rejected('nonfinite JSON')
    try: return json.loads(data,object_pairs_hook=unique,parse_constant=bad)
    except (ValueError,UnicodeError,RecursionError) as e: raise Rejected('invalid JSON') from e

def manifest_entries(cov,data):
    exact_asset('ario-manifest.json',data)
    obj=parse_json(data)
    if not isinstance(obj,dict) or any(obj.get(k)!=v for k,v in {'format':'ARIO_FULL_SNAPSHOT_v1',
       'source_repo':'https://github.com/SepehrGhanbari/Ario','commit':SOURCE,'tree':SOURCE_TREE,
       'tracked_files':SOURCE_COUNT,'tracked_bytes':SOURCE_TOTAL}.items()): raise Rejected('wrong source manifest')
    rows=obj.get('files')
    if not isinstance(rows,list) or len(rows)!=SOURCE_COUNT: raise Rejected('manifest count mismatch')
    entries={}; aliases={}; dirs=set(); total=0
    for row in rows:
        if not isinstance(row,dict): raise Rejected('bad manifest row')
        p=cov.parts(row.get('path')); name='/'.join(p)
        if row.get('mode') not in ('100644','100755') or row.get('encoding') not in ('raw-utf8','base64') or not cov.hex40(row.get('git_blob_sha1')): raise Rejected('unsupported source member')
        n=row.get('bytes'); h=row.get('sha256')
        if type(n) is not int or not 0<=n<=64*1024*1024 or not isinstance(h,str) or not re.fullmatch('[0-9a-f]{64}',h): raise Rejected('bad manifest digest/size')
        if name in entries or name in dirs: raise Rejected('duplicate or file-directory collision')
        for i in range(1,len(p)+1):
            s='/'.join(p[:i]); k=unicodedata.normalize('NFC',s.casefold())
            if aliases.setdefault(k,s)!=s or (i<len(p) and s in entries): raise Rejected('path alias or conflict')
            if i<len(p): dirs.add(s)
        entries[name]=row; total+=n
    if total!=SOURCE_TOTAL: raise Rejected('source byte count mismatch')
    return entries

def emit_member(cov,root,row,raw):
    if len(raw)!=row['bytes'] or sha(raw)!=row['sha256'] or cov.object_id('blob',raw)!=row['git_blob_sha1']: raise Rejected('source member differs from manifest')
    path=root.joinpath(*cov.parts(row['path'])); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f: f.write(raw)

def restore_zip(cov,data,root):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos=z.infolist(); names=[i.filename for i in infos]
        if len(names)!=len(set(names)) or len(names)!=SOURCE_COUNT+3: raise Rejected('ZIP member count or duplicates')
        meta='EXPORT_META/ario-manifest.json'
        mi=z.getinfo(meta)
        if mi.file_size!=ASSETS['ario-manifest.json'][0]: raise Rejected('embedded manifest size')
        entries=manifest_entries(cov,z.read(mi))
        allowed={'ARIO_SOURCE/'+name for name in entries}|{'EXPORT_META/'+name for name in ('ario-manifest.json','README-EXPORT.txt','RESTORE_FROM_TXT.py')}
        if set(names)!=allowed: raise Rejected('ZIP member set differs')
        for name,row in entries.items():
            info=z.getinfo('ARIO_SOURCE/'+name)
            if info.file_size!=row['bytes'] or info.is_dir() or stat.S_IFMT(info.external_attr>>16)!=stat.S_IFREG: raise Rejected('ZIP member type or size mismatch')
            with z.open(info) as f: raw=f.read(row['bytes']+1)
            emit_member(cov,root,row,raw)
    # Never extract or execute EXPORT_META scripts.

def restore_txt(cov,data,manifest,root):
    entries=manifest_entries(cov,manifest); f=io.BytesIO(data)
    if f.readline(4097)!=b'ARIO_FULL_TEXT_EXPORT_V1\n': raise Rejected('wrong TXT format')
    header={}; header_bytes=0
    while True:
        line=f.readline(4097); header_bytes+=len(line)
        if not line or len(line)>4096 or header_bytes>16384: raise Rejected('invalid TXT header')
        if line==b'@@ARIO_BEGIN\n': break
        if b'=' in line:
            k,v=line.rstrip(b'\n').split(b'=',1)
            if k in header: raise Rejected('duplicate TXT header')
            header[k]=v
    expected={b'repo':b'https://github.com/SepehrGhanbari/Ario',b'commit':SOURCE.encode(),b'tree':SOURCE_TREE.encode(),
              b'tracked_files':str(SOURCE_COUNT).encode(),b'tracked_bytes':str(SOURCE_TOTAL).encode(),b'manifest_sha256':sha(manifest).encode()}
    if any(header.get(k)!=v for k,v in expected.items()): raise Rejected('TXT header differs from manifest')
    seen=set()
    for _ in range(SOURCE_COUNT):
        line=f.readline(65537)
        if len(line)>65536 or not line.startswith(b'@@ARIO_FILE '): raise Rejected('invalid TXT record')
        row=parse_json(line[len(b'@@ARIO_FILE '):]); name=row.get('path') if isinstance(row,dict) else None
        if not isinstance(name,str) or name not in entries or name in seen: raise Rejected('unexpected TXT member')
        ref=entries[name]; n=row.get('payload_bytes')
        if any(row.get(k)!=v for k,v in ref.items()) or type(n) is not int or not 0<=n<=90*1024*1024: raise Rejected('TXT member metadata mismatch')
        raw=f.read(n)
        if len(raw)!=n or f.read(len(b'\n@@ARIO_END\n'))!=b'\n@@ARIO_END\n': raise Rejected('TXT framing mismatch')
        if ref['encoding']=='base64':
            try: raw=base64.b64decode(raw.translate(None,b' \t\r\n\v\f'),validate=True)
            except ValueError as e: raise Rejected('invalid Base64') from e
        else: raw.decode('utf-8','strict')
        emit_member(cov,root,ref,raw); seen.add(name)
    # The original 11-Nov publication has the short footer. Its entire
    # byte sequence and external manifest are already SHA-256 pinned.
    foot=f'@@ARIO_COMPLETE files={SOURCE_COUNT} commit={SOURCE}\n'.encode()
    if f.read()!=foot or seen!=set(entries): raise Rejected('TXT footer or member set mismatch')

def require_doi(cov,root,record):
    if record not in cov.RECORDS: raise Unknown('DOI record not in fixed allowlist')
    root=real_dir(root); real_dir(root/record)
    report=cov.check_doi(root,record)
    if report.get('status')=='REJECTED': raise Rejected('DOI content mismatch')
    files=report.get('files')
    if (report.get('record')!=record or report.get('doi')!='10.5281/zenodo.'+record or
        report.get('status')!='ALL_RECORD_FILES_MATCH_ZENODO_HTTPS' or not isinstance(files,list) or not files or
        any(not isinstance(x,dict) or x.get('status')!='LOCAL_BYTES_MATCH_ZENODO_HTTPS' or not isinstance(x.get('sha256'),str) or not re.fullmatch('[0-9a-f]{64}',x['sha256']) for x in files)):
        raise Unknown('incomplete DOI byte evidence')
    names=[cov.safe_part(x.get('file')) for x in files]
    if len(names)!=len(set(names)) or set(names)!={p.name for p in (root/record).iterdir()}: raise Rejected('extra or duplicate DOI files')
    return report

def gate(mode, path, parent, commit=COMMIT, record=None):
    """Return a scoped verdict. No caller-supplied evidence or bypass switch."""
    report={'mode':mode,'status':'UNKNOWN','qualification':QUAL}; stage=None; passed=False
    try:
        rel=load_dep('ario_verified_release'); cov=load_dep('ario_verify_coverage')
        if mode=='check': report['evidence']=require_checkout(cov,path,commit)
        elif mode=='doi-check': report['evidence']=require_doi(cov,path,record)
        elif mode in ('clone','startup-probe','runtime-audit'):
            if mode=='startup-probe' and commit!=COMMIT: raise Unknown('startup probe requires exact fixed official commit')
            if mode=='runtime-audit':
                if commit!=RUNTIME_COMMIT: raise Unknown('runtime audit requires exact fixed runtime commit')
                raw=read_regular(path,RUNTIME_INPUT_MAX)
                data=parse_json(raw)
                if not isinstance(data,dict) or type(data.get('audit_id')) is not str:
                    raise Rejected('runtime audit requires an M0 request object with audit_id')
                report['request_sha256']=sha(raw)
            stage=Path(tempfile.mkdtemp(prefix='ario-gate-stage-',dir=real_dir(parent)))
            with tempfile.TemporaryDirectory(prefix='ario-git-control-') as control:
                safe_git(stage,Path(control),commit)
            report['evidence']=require_checkout(cov,stage,commit)
            if mode=='startup-probe':
                report['startup_attempted']=True
                report['startup_result']=run_synthetic_audit(stage)
            if mode=='runtime-audit':
                report['runtime_attempted']=True
                report['runtime_result']=run_runtime_audit(stage,raw)
                report['runtime_scope']='EXPLICIT_M0_DATA_ONLY_NO_LEDGER'
                report['claim_truth']='UNKNOWN'
                report['independent_admission_authority']='NONE'
        elif mode in ('import','restore','download-restore'):
            with tempfile.TemporaryDirectory(prefix='ario-integrity-private-') as s:
                scratch=Path(s)
                if mode=='download-restore':
                    asset='ario-full.zip'; path=scratch/'received.zip'; rel.download_asset(asset,path)
                else:
                    asset={'.zip':'ario-full.zip','.txt':'ario-full.txt'}.get(path.suffix.lower())
                if asset is None: raise Unknown('only pinned 11-Nov ZIP or TXT supported')
                data=exact_asset(asset,read_regular(path,ASSETS[asset][0],ASSETS[asset][0]))
                report['release_evidence']=verify_release_bytes(rel,asset,data,scratch)
                # No output directory is made until the archive's external evidence passes.
                stage=Path(tempfile.mkdtemp(prefix='ario-gate-stage-',dir=real_dir(parent)))
                if mode=='import':
                    with (stage/asset).open('xb') as f: f.write(data)
                    if sha(read_regular(stage/asset,len(data),len(data)))!=ASSETS[asset][1]: raise Unknown('output bytes changed')
                else:
                    if asset=='ario-full.zip': restore_zip(cov,data,stage)
                    else:
                        mf=scratch/'downloaded-manifest'; rel.download_asset('ario-manifest.json',mf)
                        manifest=exact_asset('ario-manifest.json',read_regular(mf,ASSETS['ario-manifest.json'][0],ASSETS['ario-manifest.json'][0]))
                        verify_release_bytes(rel,'ario-manifest.json',manifest,scratch)
                        restore_txt(cov,data,manifest,stage)
                    report['evidence']=require_checkout(cov,stage,SOURCE)
        else: raise Unknown('unsupported gate mode')
        report['status']={'startup-probe':'MATCH_RESEARCH_STARTUP_PROBE',
                          'runtime-audit':'MATCH_RUNTIME_AUDIT_COMPLETED'}.get(mode,'MATCH_PREPARATION_ONLY'); passed=True
        if stage is not None: report['directory']=str(stage)
        return 0,report
    except Exception as e:
        # Fail closed even on unexpected dependency exceptions. Never accept
        # stdout text or cached success. Avoid leaking user paths in errors.
        name=type(e).__name__
        if isinstance(e,Rejected) or name=='Rejected': code=2; report['status']='REJECTED'
        else: code=3; report['status']='UNKNOWN'
        report['reason']=str(e) if type(e) in (Unknown,Rejected) else 'verification or preparation failed: '+name
        return code,report
    finally:
        if stage is not None and not passed:
            try: shutil.rmtree(stage)
            except OSError: report['cleanup']='FAILED; do not use unfinished stage'; report['unaccepted_directory']=str(stage)

def interactive():
    # No shell interpretation of paths entered by the operator. New report and
    # stage directories are created under the trusted package, not source data.
    parent=HERE.parent
    print("ARIO INTEGRITY GATE V1 -- RESEARCH ONLY")
    print("1. Clone + verify + synthetic M0 startup probe (official fixed commit)")
    print("2. Download + verify + restore the official 204-file ZIP (no execution)")
    print("3. Verify and restore a local 11-Nov ZIP or TXT (no execution)")
    print("4. Clone + verify only (official fixed commit; no execution)")
    print("5. Verify an existing checkout (enter exact commit)")
    print("6. Verify a local Zenodo record folder (no execution)")
    print("7. Clone + verify fixed runtime + execute an explicit M0 JSON audit (no ledger)")
    try:
        choice=input("Choose 1-7: ").strip(); path=None; commit=COMMIT; record=None
        if choice=='1': mode='startup-probe'
        elif choice=='2': mode='download-restore'
        elif choice=='3':
            mode='restore'; path=Path(input('Archive path: ').strip().strip('"'))
        elif choice=='4': mode='clone'
        elif choice=='5':
            mode='check'; path=Path(input('Checkout folder: ').strip().strip('"'))
            commit=input('Exact full commit SHA: ').strip()
        elif choice=='6':
            mode='doi-check'; path=Path(input('Parent folder containing the record-ID directory: ').strip().strip('"'))
            record=input('Zenodo record ID: ').strip()
        elif choice=='7':
            mode='runtime-audit'; commit=RUNTIME_COMMIT
            path=Path(input('M0 JSON request path: ').strip().strip('"'))
        else: print('No operation selected.'); return 3
        code,report=gate(mode,path,parent,commit,record)
        report['exit_code']=code
        body=json.dumps(report,ensure_ascii=True,sort_keys=True)
        print(body)
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',prefix='INTEGRITY_GATE_RESULTS-',suffix='.json',dir=parent,delete=False) as f:
            f.write(body+'\n'); name=f.name
        print('Report: '+name); return code
    except (OSError,EOFError,KeyboardInterrupt): print('Interrupted/unavailable. No success verdict.'); return 3

def main(argv=None):
    if (sys.argv[1:] if argv is None else argv)==['--menu']: return interactive()
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='mode',required=True)
    for name in ('check','clone','import','restore','doi-check','startup-probe','download-restore','runtime-audit'):
        q=sub.add_parser(name)
        if name in ('check','doi-check'): q.add_argument('--directory',type=Path,required=True)
        if name in ('check','clone'): q.add_argument('--commit',default=COMMIT)
        if name in ('clone','import','restore','startup-probe','download-restore','runtime-audit'): q.add_argument('--output-parent',type=Path,required=True)
        if name in ('import','restore','runtime-audit'): q.add_argument('--input',type=Path,required=True)
        if name=='doi-check': q.add_argument('--record',required=True)
    a=p.parse_args(argv)
    code,report=gate(a.mode,getattr(a,'directory',getattr(a,'input',None)),getattr(a,'output_parent',None),getattr(a,'commit',RUNTIME_COMMIT if a.mode=='runtime-audit' else COMMIT),getattr(a,'record',None))
    report['exit_code']=code; print(json.dumps(report,ensure_ascii=True,sort_keys=True)); return code
if __name__=='__main__': raise SystemExit(main())
