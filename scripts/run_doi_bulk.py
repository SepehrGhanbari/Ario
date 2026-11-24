"""Research-only: download each exact Zenodo record, then separately re-read and compare.
No archive execution, extraction, overwrite or GitHub writes. No automatic redirects.
"""
import hashlib, json, os, sys, tempfile
from pathlib import Path
from urllib.parse import quote
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ario_verify_coverage as v


def download_one(root, rec, key, size, md5):
    target = root / rec / key
    h = hashlib.md5(usedforsecurity=False)
    n = 0
    with v.response('zenodo.org', f'/api/records/{rec}/files/{quote(key,safe="")}/content', size) as (r, declared):
        if declared is not None and declared != size:
            raise v.Unknown('metadata/response size disagreement')
        with target.open('xb') as f:
            for block in v.blocks(r, declared, size):
                f.write(block); h.update(block); n += len(block)
    if n != size or h.hexdigest() != md5:
        raise v.Unknown('download disagrees with record metadata')


def run(parent):
    root = Path(tempfile.mkdtemp(prefix='ario-doi-files-', dir=parent))
    rows = []
    total = 0
    # Catalog all records before download; never silently substitute another DOI.
    catalog = {}
    for rec in v.RECORDS:
        try:
            files = v.record_files(rec, v.get_json('zenodo.org', f'/api/records/{rec}'))
            total += sum(x[1] for x in files)
            catalog[rec] = files
        except (v.Unknown, v.Rejected, OSError) as e:
            rows.append({'record': rec, 'status':'UNKNOWN','reason':str(e)})
    if total > v.MAX_TOTAL:
        return {'status':'UNKNOWN','directory':str(root),'reason':'aggregate byte limit exceeded','records':rows}
    for rec, files in catalog.items():
        (root/rec).mkdir()
        errors=[]
        for key,size,md5 in files:
            print(f'Download {rec}: {key}',file=sys.stderr,flush=True)
            try: download_one(root,rec,key,size,md5)
            except (v.Unknown,v.Rejected,OSError) as e: errors.append({'file':key,'reason':str(e)})
        if errors:
            rows.append({'record':rec,'status':'UNKNOWN','download_errors':errors}); continue
        try:
            # Existing verifier issues fresh HTTPS requests and checks SHA-256 against local files.
            checked=v.check_doi(root,rec)
            expected=sorted(files)
            seen=sorted((f['file'],f['size'],f['metadata_md5']) for f in checked['files'])
            if seen != expected:
                checked['status']='UNKNOWN'; checked['reason']='catalog changed between observations'
            rows.append(checked)
        except (v.Unknown,v.Rejected,OSError) as e:
            rows.append({'record':rec,'status':'UNKNOWN','reason':str(e)})
    # Optional cross-reference using the exact pinned Git tree, not a claim of independent identity.
    mapping={'status':'UNKNOWN'}
    try:
        tree=v.validate_tree(v.get_json('api.github.com',f'/repos/SepehrGhanbari/Ario/git/trees/{v.TREE}?recursive=1'),v.TREE)
        if (len(tree),sum(x['size'] for x in tree.values()))!=(v.COUNT,v.TOTAL): raise v.Unknown('unexpected pinned tree scope')
        index={}
        for p,x in tree.items(): index.setdefault((x['size'],x['sha']),[]).append('/'.join(p))
        matched=0; checked_count=0; unknown=0
        for row in rows:
            if row['status']!='ALL_RECORD_FILES_MATCH_ZENODO_HTTPS': continue
            for f in row['files']:
                try:
                    # Re-read the local file: mapping is a separate observation.
                    if v.local_digest(root,(row['record'],f['file']),f['size'])!=f['sha256']:
                        raise v.Unknown('local bytes changed since Zenodo check')
                    git_id=v.local_digest(root,(row['record'],f['file']),f['size'],git=True)
                    f['github_blob_id']=git_id
                    f['github_paths_same_size_and_blob_id']=index.get((f['size'],git_id),[])
                    checked_count+=1; matched+=bool(f['github_paths_same_size_and_blob_id'])
                except (v.Unknown,v.Rejected,OSError) as e:
                    f['github_mapping_unknown']=str(e); unknown+=1
        mapping={'status':'UNKNOWN' if unknown else 'OBSERVED_GIT_BLOB_MAPPING','commit':v.COMMIT,'tree':v.TREE,'mapped_files':matched,'checked_files':checked_count,'unknown_files':unknown,'qualification':'Git SHA-1 blob ID and size match only; no GitHub file SHA-256 comparison. No-match is not corruption; files may exist only in Zenodo or other commits.'}
    except (v.Unknown,v.Rejected,OSError) as e:
        mapping['reason']=str(e)
    states=[x['status'] for x in rows]
    ok=len(rows)==len(v.RECORDS) and all(x=='ALL_RECORD_FILES_MATCH_ZENODO_HTTPS' for x in states)
    status='ALL_SELECTED_DOI_FILES_MATCH_ZENODO_HTTPS' if ok else 'REJECTED' if 'REJECTED' in states else 'UNKNOWN'
    return {'directory':str(root),'status':status,'records':rows,'catalog_files':sum(len(x) for x in catalog.values()),'catalog_bytes':total,'github_mapping':mapping}


def main():
    try: report=run(Path.cwd())
    except (v.Unknown,v.Rejected,OSError) as e: report={'status':'UNKNOWN','reason':str(e)}
    code=0 if report['status']=='ALL_SELECTED_DOI_FILES_MATCH_ZENODO_HTTPS' else 2 if report['status']=='REJECTED' else 3
    report.update(exit_code=code,qualification='RESEARCH_ONLY; two HTTPS observations from Zenodo, not independent publisher identity, permission to execute, or atomic snapshot. GitHub mapping is separate and may be UNKNOWN.')
    print(json.dumps(report,ensure_ascii=True,sort_keys=True)); return code

if __name__=='__main__': raise SystemExit(main())
