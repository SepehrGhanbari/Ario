#!/usr/bin/env python3
"""Explicit research-only comparison of a checkout or local DOI files.
No Git commands, execution of inspected files, downloads to disk or writes.
Trust this verifier and the OS/runtime independently of the inspected files.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from contextlib import contextmanager
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import ssl
import stat
import sys
from urllib.parse import quote

COMMIT = 'd12d511e0ae1a19560a13dadaafb77a700fd20ef'
TREE = 'd101d77191f4df34538c8385538655fc053e4616'
COUNT = 456
TOTAL = 96284142
RECORDS = ('23259916','23326995','23375350','23375401','23376521','23376577','23441596','23600820','23651704','23771218','24041161','24054535','24136175','24230572','24343618')
MAX_META = 8 * 1024 * 1024
MAX_FILE = 512 * 1024 * 1024
MAX_TOTAL = 2 * 1024 * 1024 * 1024
CHUNK = 1024 * 1024
HOSTS = ('api.github.com', 'zenodo.org')

class Unknown(Exception): pass
class Rejected(Exception): pass


def sha1(data=b''):
    # Git's historical object-ID format; not an independent SHA-256 pin.
    return hashlib.sha1(data, usedforsecurity=False)


def object_id(kind, data):
    return sha1(f'{kind} {len(data)}\0'.encode('ascii') + data).hexdigest()


def hex40(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{40}', value) is not None


def safe_part(s):
    if (not isinstance(s, str) or not s or s in ('.','..') or s.casefold() == '.git'
            or s.endswith(('.', ' ')) or any(ord(c) < 32 or c in '<>:"/\\|?*' for c in s)
            or re.fullmatch(r'(?i:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])', s.split('.')[0])):
        raise Unknown('unsupported or unsafe reference path component')
    try:
        s.encode('utf-8', 'strict')
    except UnicodeError as exc:
        raise Unknown('unsupported reference filename encoding') from exc
    return s


def parts(path):
    if not isinstance(path, str): raise Unknown('invalid path')
    if len(path)>1024 or path.count('/')>=64: raise Unknown('reference path exceeds limit')
    return tuple(safe_part(p) for p in path.split('/'))


def unique_pairs(pairs):
    result = {}
    for k, v in pairs:
        if k in result: raise Unknown('duplicate JSON key')
        result[k] = v
    return result


@contextmanager
def response(host, path, limit):
    """Only fixed HTTPS hosts; no proxies, redirect following, or credentials."""
    if host not in HOSTS or not path.startswith('/') or path.startswith('//'):
        raise Unknown('unsupported endpoint')
    conn = None
    try:
        conn = http.client.HTTPSConnection(host, timeout=15, context=ssl.create_default_context())
        conn.request('GET', path, headers={'User-Agent':'Ario-research-coverage/0.1', 'Accept-Encoding':'identity', 'Connection':'close'})
        with conn.getresponse() as r:
            if r.status != 200: raise Unknown(f'{host} HTTP {r.status}')
            enc = r.headers.get_all('Content-Encoding', [])
            if enc and [x.strip().lower() for x in enc] != ['identity']: raise Unknown('unsupported response content coding')
            cl = r.headers.get_all('Content-Length', [])
            te = r.headers.get_all('Transfer-Encoding', [])
            if cl:
                v = cl[0].strip(' \t')
                if len(cl) != 1 or te or not re.fullmatch('[0-9]{1,12}', v) or int(v)>limit or r.chunked or r.length!=int(v):
                    raise Unknown('unsupported response length/framing')
            elif [x.strip(' \t').lower() for x in te] != ['chunked'] or r.chunked is not True:
                raise Unknown('unsupported response framing')
            yield r, int(v) if cl else None
    except (OSError, ValueError, http.client.HTTPException) as exc:
        raise Unknown(f'{host}: HTTPS response unavailable') from exc
    finally:
        if conn: conn.close()


def blocks(r, declared, limit):
    n = 0
    while declared is None or n < declared:
        size = min(CHUNK, limit - n + 1, declared-n if declared is not None else CHUNK)
        b = r.read(size)
        if not b: break
        n += len(b)
        if n > limit: raise Unknown('response exceeds byte limit')
        yield b
    if declared is not None and n != declared: raise Unknown('incomplete response')


def get_json(host, path):
    with response(host,path,MAX_META) as (r,n):
        data=b''.join(blocks(r,n,MAX_META))
    try:
        obj=json.loads(data,object_pairs_hook=unique_pairs)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Unknown('invalid reference JSON') from exc
    if not isinstance(obj,dict): raise Unknown('invalid reference object')
    return obj


def validate_tree(obj, root):
    if obj.get('sha') != root or obj.get('truncated') is not False or not isinstance(obj.get('tree'),list):
        raise Unknown('tree incomplete or not the requested root')
    entries, folded, children = {}, set(), defaultdict(list)
    for row in obj['tree']:
        if not isinstance(row,dict): raise Unknown('invalid tree row')
        p=parts(row.get('path')); k='/'.join(p); f=k.casefold()
        if f in folded: raise Unknown('duplicate or case-colliding tree path')
        folded.add(f)
        mode, typ, h = row.get('mode'), row.get('type'),row.get('sha')
        if not hex40(h) or (mode,typ) not in (('040000','tree'),('100644','blob'),('100755','blob')):
            raise Unknown('unsupported tree object (symlinks/submodules are not covered)')
        if typ=='blob' and (type(row.get('size')) is not int or not 0 <= row['size'] <= MAX_FILE):
            raise Unknown('unsupported blob size')
        entries[p]=row
        children[p[:-1]].append((p[-1].encode('utf-8'),mode,h))
    for p in entries:
        if p[:-1] and (p[:-1] not in entries or entries[p[:-1]]['type']!='tree'):
            raise Unknown('tree parent missing')
    for p in [()]+[p for p,row in entries.items() if row['type']=='tree']:
        items=children[p]
        raw=b''.join((b'40000' if m=='040000' else m.encode('ascii'))+b' '+name+b'\0'+bytes.fromhex(h)
                     for name,m,h in sorted(items,key=lambda x:x[0]+(b'/' if x[1]=='040000' else b'')))
        if object_id('tree',raw)!=(entries[p]['sha'] if p else root): raise Unknown('Git tree object-ID reconstruction mismatch')
    return {p:r for p,r in entries.items() if r['type']=='blob'}


def is_link(st):
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024))


def locate(root,p):
    path=root
    for i,part in enumerate(p):
        path=path/part
        st=path.lstat()
        if is_link(st): raise Rejected('symlink/reparse point in inspected path')
        if i<len(p)-1 and not stat.S_ISDIR(st.st_mode): raise Rejected('non-directory parent')
    return path,st


def stamp(st):
    # Windows ctime semantics may differ between stat methods; mtime/identity
    # checks here are observations, not an atomic filesystem snapshot.
    return (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)


def local_digest(root,p,size,git=False):
    try:
        path,st=locate(root,p)
        if not stat.S_ISREG(st.st_mode) or st.st_size!=size: raise Rejected('file type or size mismatch')
        flags=os.O_RDONLY | getattr(os,'O_BINARY',0) | getattr(os,'O_NONBLOCK',0) | getattr(os,'O_NOFOLLOW',0)
        with os.fdopen(os.open(path,flags),'rb') as f:
            first=os.fstat(f.fileno())
            if not stat.S_ISREG(first.st_mode) or stamp(first)!=stamp(st): raise Unknown('file changed before reading')
            h=sha1(f'blob {size}\0'.encode('ascii')) if git else hashlib.sha256()
            left=size
            while left:
                b=f.read(min(CHUNK,left))
                if not b: raise Unknown('file changed during reading')
                left-=len(b); h.update(b)
            if f.read(1) or stamp(os.fstat(f.fileno()))!=stamp(first): raise Unknown('file changed during reading')
        _,last=locate(root,p)
        if stamp(last)!=stamp(first): raise Unknown('path changed during reading')
        return h.hexdigest()
    except FileNotFoundError as exc: raise Rejected('expected file missing') from exc
    except OSError as exc: raise Unknown('local file inaccessible') from exc


def extras(root,expected):
    found=[]; expected_dirs={p[:i] for p in expected for i in range(1,len(p))}
    def walk(d, parent):
        try:
            with os.scandir(d) as items:
                for e in items:
                    if not parent and e.name=='.git': continue
                    p=parent+(e.name,)
                    st=e.stat(follow_symlinks=False)
                    if p in expected_dirs and stat.S_ISDIR(st.st_mode) and not is_link(st): walk(e.path,p)
                    elif p not in expected: found.append('/'.join(p))
                    if len(found)>10000: raise Unknown('too many extra paths')
        except OSError as exc: raise Unknown('directory enumeration unavailable') from exc
    walk(root,())
    return sorted(found)


def check_checkout(root,commit):
    if not hex40(commit): raise Unknown('exact 40-character commit required')
    c=get_json('api.github.com',f'/repos/SepehrGhanbari/Ario/git/commits/{commit}')
    tree=c.get('tree')
    if c.get('sha')!=commit or not isinstance(tree,dict) or not hex40(tree.get('sha')): raise Unknown('invalid commit response')
    root_id=tree['sha']
    if commit==COMMIT and root_id!=TREE: raise Unknown('pinned root differs')
    files=validate_tree(get_json('api.github.com',f'/repos/SepehrGhanbari/Ario/git/trees/{root_id}?recursive=1'),root_id)
    total=sum(r['size'] for r in files.values())
    if not files or total>MAX_TOTAL or (commit==COMMIT and (len(files),total)!=(COUNT,TOTAL)): raise Unknown('unexpected tree scope')
    problems=[]; matched=0
    for p,r in sorted(files.items()):
        try:
            if local_digest(root,p,r['size'],git=True)!=r['sha']: raise Rejected('Git blob mismatch')
            matched+=1
        except (Unknown,Rejected) as exc:
            problems.append({'path':'/'.join(p),'status':'REJECTED' if isinstance(exc,Rejected) else 'UNKNOWN','reason':str(exc)})
    extra=extras(root,files)
    state='REJECTED' if extra or any(x['status']=='REJECTED' for x in problems) else 'UNKNOWN' if problems else 'TRACKED_FILE_BYTES_MATCH_GITHUB_TREE'
    return {'status':state,'commit':commit,'tree':root_id,'expected_files':len(files),'expected_bytes':total,'matched_files':matched,'problems':problems,'extra_paths':extra,'scope':'WORKTREE_RAW_FILE_BYTES_ONLY; .git EXCLUDED; MODES NOT ATTESTED; GIT SHA1 OBJECT IDS; NO HISTORY OR IDENTITY CLAIM'}


def record_files(record,obj):
    if str(obj.get('id'))!=record or obj.get('doi')!=f'10.5281/zenodo.{record}': raise Unknown('exact record DOI mismatch (concept DOI not accepted)')
    rows=obj.get('files')
    if isinstance(rows,dict):
        if rows.get('enabled') is False or not isinstance(rows.get('entries'),dict): raise Unknown('record files unavailable')
        rows=list(rows['entries'].values())
    if not isinstance(rows,list) or not rows or len(rows)>1000: raise Unknown('record files missing or unsupported')
    seen=set(); out=[]
    for row in rows:
        if not isinstance(row,dict): raise Unknown('invalid file metadata')
        key=safe_part(row.get('key')); size=row.get('size'); ck=row.get('checksum')
        if key.casefold() in seen or type(size) is not int or not 0<=size<=MAX_FILE or not isinstance(ck,str) or not re.fullmatch('md5:[0-9a-fA-F]{32}',ck): raise Unknown('unsupported file metadata')
        seen.add(key.casefold());out.append((key,size,ck[4:].lower()))
    if sum(x[1] for x in out)>MAX_TOTAL: raise Unknown('record byte limit exceeded')
    return out


def check_doi(root,record,catalog=False):
    files=record_files(record,get_json('zenodo.org',f'/api/records/{record}'))
    result={'doi':f'10.5281/zenodo.{record}','record':record,'files':[]}
    for key,size,md5 in files:
        entry={'file':key,'size':size,'metadata_md5':md5}; result['files'].append(entry)
        if catalog:
            entry['status']='METADATA_ONLY'; continue
        try:
            local=local_digest(root,(record,key),size)
            h=hashlib.sha256(); m=hashlib.md5(usedforsecurity=False); count=0
            with response('zenodo.org',f'/api/records/{record}/files/{quote(key,safe="")}/content',size) as (r,n):
                if n is not None and n!=size: raise Unknown('Zenodo metadata/response size mismatch')
                for b in blocks(r,n,size): h.update(b); m.update(b); count+=len(b)
            if count!=size or m.hexdigest()!=md5: raise Unknown('Zenodo response disagrees with metadata')
            if h.hexdigest()!=local: raise Rejected('local SHA-256 differs from Zenodo response')
            entry.update(status='LOCAL_BYTES_MATCH_ZENODO_HTTPS',sha256=local)
        except (Rejected,Unknown) as exc:
            entry.update(status='REJECTED' if isinstance(exc,Rejected) else 'UNKNOWN',reason=str(exc))
    states=[x['status'] for x in result['files']]
    result['status']='METADATA_ONLY' if catalog else 'REJECTED' if 'REJECTED' in states else 'UNKNOWN' if 'UNKNOWN' in states else 'ALL_RECORD_FILES_MATCH_ZENODO_HTTPS'
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['checkout','doi-catalog','doi-check'])
    p.add_argument('--directory',type=Path,default=Path.cwd())
    p.add_argument('--commit',default=COMMIT)
    p.add_argument('--record',choices=RECORDS,action='append')
    a=p.parse_args(argv)
    try:
        root=a.directory.absolute()
        if a.mode!='doi-catalog':
            # Reject a selected root which is itself a link. Ancestor control is
            # a stated environmental assumption, not a race-proof confinement.
            st=root.lstat()
            if is_link(st) or not stat.S_ISDIR(st.st_mode): raise Rejected('selected root must be a real directory')
        if a.mode=='checkout':
            report=check_checkout(root,a.commit)
        else:
            rows=[]
            for rec in dict.fromkeys(a.record or RECORDS):
                try: rows.append(check_doi(root,rec,a.mode=='doi-catalog'))
                except (Unknown,Rejected) as exc: rows.append({'record':rec,'status':'REJECTED' if isinstance(exc,Rejected) else 'UNKNOWN','reason':str(exc)})
            states=[x['status'] for x in rows]
            report={'status':'REJECTED' if 'REJECTED' in states else 'UNKNOWN' if 'UNKNOWN' in states else 'METADATA_ONLY' if a.mode=='doi-catalog' else 'ALL_SELECTED_DOI_FILES_MATCH_ZENODO_HTTPS','records':rows}
    except (Unknown,Rejected,OSError) as exc:
        report={'status':'REJECTED' if isinstance(exc,Rejected) else 'UNKNOWN','reason':str(exc)}
    code=2 if report['status']=='REJECTED' else 0 if report['status'] in ('TRACKED_FILE_BYTES_MATCH_GITHUB_TREE','ALL_SELECTED_DOI_FILES_MATCH_ZENODO_HTTPS') else 3
    report.update(exit_code=code,qualification='RESEARCH_ONLY; observed bytes, not independent publisher identity, custody, DOI-to-GitHub equivalence, or permission to execute. No hostile-runtime or atomic-snapshot guarantee.')
    print(json.dumps(report,ensure_ascii=True,sort_keys=True));return code

if __name__=='__main__': raise SystemExit(main())
