import base64, hashlib, io, json, os, stat, subprocess, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch, Mock
import ario_integrity_gate as g

class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.output=self.root/'output'; self.output.mkdir()
        self.rel=g.load_dep('ario_verified_release'); self.cov=g.load_dep('ario_verify_coverage')
        self.raw={'a.txt':b'hello\n@@ARIO_END\n','nested/b.bin':b'\x00\xff\x80'}
        self.rows=[{'path':p,'mode':'100644','encoding':'raw-utf8' if p.endswith('txt') else 'base64','bytes':len(raw),'sha256':g.sha(raw),'git_blob_sha1':self.cov.object_id('blob',raw)} for p,raw in self.raw.items()]
        self.n=len(self.raw); self.total=sum(map(len,self.raw.values()))
        self.m=json.dumps({'format':'ARIO_FULL_SNAPSHOT_v1','source_repo':'https://github.com/SepehrGhanbari/Ario','commit':g.SOURCE,'tree':g.SOURCE_TREE,'tracked_files':self.n,'tracked_bytes':self.total,'files':self.rows}).encode()
        self.z=self.zip_bytes(); self.t=self.txt_bytes(); self.pin={'ario-full.zip':(len(self.z),g.sha(self.z)),'ario-full.txt':(len(self.t),g.sha(self.t)),'ario-manifest.json':(len(self.m),g.sha(self.m))}
        self.zip=self.root/'received.zip'; self.zip.write_bytes(self.z)
        self.txt=self.root/'received.txt'; self.txt.write_bytes(self.t)
    def zip_bytes(self,extra=False,bad=False,duplicate=False,alias=False):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:
            for p,raw in self.raw.items():
                i=zipfile.ZipInfo('ARIO_SOURCE/'+p); i.create_system=3;i.external_attr=(stat.S_IFREG|0o644)<<16
                z.writestr(i,b'X'*len(raw) if bad and p=='a.txt' else raw)
            z.writestr('EXPORT_META/ario-manifest.json',self.m);z.writestr('EXPORT_META/README-EXPORT.txt',b'guide');z.writestr('EXPORT_META/RESTORE_FROM_TXT.py',b'raise RuntimeError("must never execute")')
            if extra:z.writestr('../escape',b'bad')
            if duplicate:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore');z.writestr('ARIO_SOURCE/a.txt',b'evil')
        return stream.getvalue()
    def txt_bytes(self,footer=None,duplicate=False):
        out=f'ARIO_FULL_TEXT_EXPORT_V1\nrepo=https://github.com/SepehrGhanbari/Ario\ncommit={g.SOURCE}\ntree={g.SOURCE_TREE}\ntracked_files={self.n}\ntracked_bytes={self.total}\nmanifest_sha256={g.sha(self.m)}\n@@ARIO_BEGIN\n'.encode()
        for row in ([self.rows[0]]*2 if duplicate else self.rows):
            raw=self.raw[row['path']]; payload=base64.encodebytes(raw) if row['encoding']=='base64' else raw
            out+=b'@@ARIO_FILE '+json.dumps(dict(row,payload_bytes=len(payload))).encode()+b'\n'+payload+b'\n@@ARIO_END\n'
        return out+(footer if footer is not None else f'@@ARIO_COMPLETE files={self.n} commit={g.SOURCE}\n'.encode())
    def fixture_pins(self): return patch.multiple(g,ASSETS=self.pin,SOURCE_COUNT=self.n,SOURCE_TOTAL=self.total)
    def dest(self): return Path(tempfile.mkdtemp(dir=self.output))
    def report(self,commit=g.COMMIT):
        t,n,b=(g.TREE,g.COUNT,g.TOTAL) if commit==g.COMMIT else (g.SOURCE_TREE,self.n,self.total)
        return {'status':'TRACKED_FILE_BYTES_MATCH_GITHUB_TREE','commit':commit,'tree':t,'expected_files':n,'expected_bytes':b,'matched_files':n,'problems':[],'extra_paths':[]}
    def deps(self):return patch.object(g,'load_dep',side_effect=lambda n:self.rel if n=='ario_verified_release' else self.cov)
    def test_exact_dep_pins(self):self.assertEqual(g.sha((g.HERE/'ario_verified_release.py').read_bytes()),g.DEPS['ario_verified_release']);self.assertEqual(g.sha((g.HERE/'ario_verify_coverage.py').read_bytes()),g.DEPS['ario_verify_coverage'])
    def test_changed_dependency_stops_before_acquisition(self):
        with patch.dict(g.DEPS,{'ario_verified_release':'0'*64}),patch.object(g,'safe_git') as git:
            code,r=g.gate('clone',None,self.output)
        self.assertEqual(code,2);git.assert_not_called();self.assertEqual(list(self.output.iterdir()),[])
    def test_same_size_archive_rejected_before_network(self):
        self.zip.write_bytes(b'X'+self.z[1:])
        with self.fixture_pins(),self.deps(),patch.object(g,'verify_release_bytes') as v:
            code,r=g.gate('restore',self.zip,self.output)
        self.assertEqual(code,2);v.assert_not_called();self.assertEqual(list(self.output.iterdir()),[])
    def test_network_unknown_blocks_restore(self):
        with self.fixture_pins(),self.deps(),patch.object(g,'verify_release_bytes',side_effect=g.Unknown('offline')),patch.object(g,'restore_zip') as z:
            code,r=g.gate('restore',self.zip,self.output)
        self.assertEqual(code,3);z.assert_not_called();self.assertEqual(list(self.output.iterdir()),[])
    def test_unexpected_verifier_exception_fails_closed(self):
        with self.fixture_pins(),self.deps(),patch.object(g,'verify_release_bytes',side_effect=RuntimeError('unexpected')):
            code,r=g.gate('import',self.zip,self.output)
        self.assertEqual(code,3);self.assertNotIn('directory',r)
    def test_import_consumes_original_verified_bytes_not_reopened_input(self):
        def mutate(*_):self.zip.write_bytes(b'tampered after read');return {'status':'synthetic match'}
        with self.fixture_pins(),self.deps(),patch.object(g,'verify_release_bytes',side_effect=mutate):code,r=g.gate('import',self.zip,self.output)
        self.assertEqual(code,0);self.assertEqual((Path(r['directory'])/'ario-full.zip').read_bytes(),self.z);self.assertNotEqual(self.zip.read_bytes(),self.z)
    def test_zip_restores_exact_members_without_meta_execution(self):
        d=self.dest()
        with self.fixture_pins():g.restore_zip(self.cov,self.z,d)
        self.assertEqual({p.relative_to(d).as_posix():p.read_bytes() for p in d.rglob('*') if p.is_file()},self.raw)
    def test_zip_extra_path_rejected(self):
        with self.fixture_pins(),self.assertRaises(g.Rejected):g.restore_zip(self.cov,self.zip_bytes(extra=True),self.dest())
    def test_zip_duplicate_rejected(self):
        with self.fixture_pins(),self.assertRaises(g.Rejected):g.restore_zip(self.cov,self.zip_bytes(duplicate=True),self.dest())
    def test_zip_member_hash_rejected(self):
        with self.fixture_pins(),self.assertRaises(g.Rejected):g.restore_zip(self.cov,self.zip_bytes(bad=True),self.dest())
    def test_txt_short_historical_footer_and_embedded_delimiter(self):
        d=self.dest()
        with self.fixture_pins():g.restore_txt(self.cov,self.t,self.m,d)
        self.assertEqual({p.relative_to(d).as_posix():p.read_bytes() for p in d.rglob('*') if p.is_file()},self.raw)
    def test_txt_footer_prefix_and_trailing_data_rejected(self):
        with self.fixture_pins():
            for data in (self.txt_bytes(footer=b'@@ARIO_COMPLETE nonsense\n'),self.t+b'extra',self.t[:-1]):
                with self.subTest(data=data[-30:]),self.assertRaises(g.Rejected):g.restore_txt(self.cov,data,self.m,self.dest())
    def test_txt_duplicate_record_rejected(self):
        with self.fixture_pins(),self.assertRaises(g.Rejected):g.restore_txt(self.cov,self.txt_bytes(duplicate=True),self.m,self.dest())
    def test_manifest_pin_mismatch(self):
        with self.fixture_pins(),self.assertRaises(g.Rejected):g.manifest_entries(self.cov,self.m+b' ')
    def test_manifest_path_alias_rejected_even_if_pin_adjusted_in_fixture(self):
        obj=json.loads(self.m);obj['files'][1]['path']='A.TXT';data=json.dumps(obj).encode()
        with self.fixture_pins(),patch.dict(g.ASSETS,{'ario-manifest.json':(len(data),g.sha(data))}),self.assertRaises(g.Rejected):g.manifest_entries(self.cov,data)
    def test_restore_postcheck_failure_removes_only_fresh_stage(self):
        keep=self.output/'keep';keep.write_text('original')
        with self.fixture_pins(),self.deps(),patch.object(g,'verify_release_bytes',return_value={}),patch.object(g,'require_checkout',side_effect=g.Rejected('restored mismatch')):
            code,r=g.gate('restore',self.zip,self.output)
        self.assertEqual(code,2);self.assertEqual(list(self.output.iterdir()),[keep]);self.assertEqual(keep.read_text(),'original')
    def test_restore_zip_full_orchestration(self):
        with self.fixture_pins(),self.deps(),patch.object(g,'verify_release_bytes',return_value={}),patch.object(self.cov,'check_checkout',return_value=self.report(g.SOURCE)):
            code,r=g.gate('restore',self.zip,self.output)
        self.assertEqual(code,0);self.assertEqual((Path(r['directory'])/'a.txt').read_bytes(),self.raw['a.txt']);self.assertEqual(r['evidence']['commit'],g.SOURCE)
    def test_restore_txt_requires_manifest_and_postcheck(self):
        def download(asset,path):self.assertEqual(asset,'ario-manifest.json');path.write_bytes(self.m)
        with self.fixture_pins(),self.deps(),patch.object(g,'verify_release_bytes',return_value={}) as v,patch.object(self.rel,'download_asset',side_effect=download),patch.object(self.cov,'check_checkout',return_value=self.report(g.SOURCE)):
            code,r=g.gate('restore',self.txt,self.output)
        self.assertEqual(code,0);self.assertEqual(v.call_count,2);self.assertEqual((Path(r['directory'])/'nested/b.bin').read_bytes(),self.raw['nested/b.bin'])
    def test_download_restore_automatically_verifies_before_materializing(self):
        def download(asset,path):self.assertEqual(asset,'ario-full.zip');path.write_bytes(self.z)
        with self.fixture_pins(),self.deps(),patch.object(self.rel,'download_asset',side_effect=download),patch.object(g,'verify_release_bytes',return_value={}) as v,patch.object(self.cov,'check_checkout',return_value=self.report(g.SOURCE)):
            code,r=g.gate('download-restore',None,self.output)
        self.assertEqual(code,0);v.assert_called_once();self.assertEqual((Path(r['directory'])/'a.txt').read_bytes(),self.raw['a.txt'])
    def test_download_restore_bad_bytes_never_materialize(self):
        def download(asset,path):path.write_bytes(b'X'+self.z[1:])
        with self.fixture_pins(),self.deps(),patch.object(self.rel,'download_asset',side_effect=download),patch.object(g,'verify_release_bytes') as v:
            code,r=g.gate('download-restore',None,self.output)
        self.assertEqual(code,2);v.assert_not_called();self.assertEqual(list(self.output.iterdir()),[])
    def test_checkout_incomplete_reports_not_success(self):
        for changes in ({'status':'UNKNOWN'},{'tree':'0'*40},{'expected_files':True,'matched_files':True},{'matched_files':g.COUNT-1},{'extra_paths':['a']},{'problems':[{}]},{'commit':'0'*40}):
            with self.subTest(changes=changes),patch.object(self.cov,'check_checkout',return_value=dict(self.report(),**changes)),self.assertRaises(g.Unknown):g.require_checkout(self.cov,self.root,g.COMMIT)
    def test_clone_failure_no_handoff(self):
        with patch.object(g,'safe_git',side_effect=g.Unknown('offline')):code,r=g.gate('clone',None,self.output)
        self.assertEqual(code,3);self.assertEqual(list(self.output.iterdir()),[])
    def test_startup_not_called_on_unknown_or_rejection(self):
        for exc in (g.Unknown('offline'),g.Rejected('mismatch'),RuntimeError('unexpected')):
            with self.subTest(exc=exc),patch.object(g,'safe_git'),patch.object(g,'require_checkout',side_effect=exc),patch.object(g,'run_synthetic_audit') as start:
                code,r=g.gate('startup-probe',None,self.output)
            self.assertIn(code,(2,3));start.assert_not_called();self.assertEqual(list(self.output.iterdir()),[])
    def test_startup_order_and_explicit_pin(self):
        calls=[]
        with patch.object(g,'safe_git',side_effect=lambda *_:calls.append('clone')),patch.object(g,'require_checkout',side_effect=lambda *_:(calls.append('verify') or self.report())),patch.object(g,'run_synthetic_audit',side_effect=lambda *_:(calls.append('start') or {'verdict':'UNKNOWN'})):
            code,r=g.gate('startup-probe',None,self.output)
        self.assertEqual(code,0);self.assertEqual(calls,['clone','verify','start']);self.assertEqual(r['status'],'MATCH_RESEARCH_STARTUP_PROBE')
        with patch.object(g,'safe_git') as git:code,r=g.gate('startup-probe',None,self.output,'0'*40)
        self.assertEqual(code,3);git.assert_not_called()
    def test_startup_result_is_not_epistemic_pass(self):
        fake={'audit_id':'ARIO-INTEGRITY-GATE-SYNTHETIC','verdict':'PASS'}
        with patch.object(g.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps(fake).encode(),b'')),self.assertRaises(g.Unknown):g.run_synthetic_audit(self.root)
        fake['verdict']='UNKNOWN'
        with patch.object(g.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps(fake).encode(),b'')) as p:
            self.assertEqual(g.run_synthetic_audit(self.root)['verdict'],'UNKNOWN')
        args=p.call_args.args[0];self.assertIn('-I',args);self.assertIn('-S',args);self.assertNotIn('--ledger',args)
    def test_doi_extra_file_rejected(self):
        rec=self.cov.RECORDS[0];d=self.root/rec;d.mkdir();(d/'file.pdf').touch();(d/'extra').touch()
        rep={'record':rec,'doi':'10.5281/zenodo.'+rec,'status':'ALL_RECORD_FILES_MATCH_ZENODO_HTTPS','files':[{'file':'file.pdf','sha256':'0'*64,'status':'LOCAL_BYTES_MATCH_ZENODO_HTTPS'}]}
        with patch.object(self.cov,'check_doi',return_value=rep),self.assertRaises(g.Rejected):g.require_doi(self.cov,self.root,rec)
    def test_read_regular_symlink_or_special_file(self):
        if hasattr(os,'mkfifo'):
            f=self.root/'fifo';os.mkfifo(f)
            with self.assertRaises(g.Rejected):g.read_regular(f,10)
        try:
            l=self.root/'link';l.symlink_to(self.zip)
        except (OSError,NotImplementedError):return
        with self.assertRaises(g.Rejected):g.read_regular(l,100000)
    def test_git_uses_no_hooks_no_submodules_no_global_config(self):
        calls=[]
        def fake(args,**kw):
            calls.append((args,kw));return subprocess.CompletedProcess(args,0,(g.COMMIT+'\n').encode() if 'rev-parse' in args else b'',b'')
        control=self.root/'control';control.mkdir()
        with patch.object(g.shutil,'which',return_value='/trusted/git'),patch.object(g.subprocess,'run',side_effect=fake):g.safe_git(self.root,control,g.COMMIT)
        self.assertEqual(len(calls),5)
        for args,kw in calls:
            self.assertIn('core.autocrlf=false',args);self.assertTrue(any(a.startswith('core.hooksPath=') for a in args));self.assertEqual(kw['env']['GIT_CONFIG_NOSYSTEM'],'1');self.assertEqual(kw['env']['GIT_ALLOW_PROTOCOL'],'https')
        self.assertIn('--no-recurse-submodules',calls[1][0]);self.assertIn('--no-recurse-submodules',calls[3][0]);self.assertIn(g.REPO,calls[1][0])

    def runtime_request(self):
        return json.dumps({'audit_id':'USER-AUDIT','rule_versions':['M0-1.0'],
            'configuration_id':'EXPLICIT','execution_timestamp':'TEST-TIME','artifacts':{}}).encode()

    def runtime_report(self):
        return {'status':'TRACKED_FILE_BYTES_MATCH_GITHUB_TREE','commit':g.RUNTIME_COMMIT,
                'tree':g.RUNTIME_TREE,'expected_files':g.RUNTIME_COUNT,
                'expected_bytes':g.RUNTIME_TOTAL,'matched_files':g.RUNTIME_COUNT,
                'problems':[],'extra_paths':[]}

    def test_runtime_audit_runs_actual_merged_m0_cli(self):
        raw=self.runtime_request()
        result=g.run_runtime_audit(g.HERE.parent,raw)
        self.assertEqual(result['audit_id'],'USER-AUDIT')
        self.assertEqual(result['verdict'],'UNKNOWN')
        self.assertIsInstance(result['violations'],list)

    def test_runtime_audit_order_and_exact_data_copy(self):
        raw=self.runtime_request(); request=self.root/'request.json'; request.write_bytes(raw)
        order=[]
        with patch.object(g,'safe_git',side_effect=lambda *_:order.append('clone')),patch.object(self.cov,'check_checkout',side_effect=lambda *_:(order.append('verify') or self.runtime_report())),self.deps(),patch.object(g,'run_runtime_audit',side_effect=lambda root,data:(order.append('audit') or self.assertEqual(data,raw) or {'verdict':'UNKNOWN'})):
            code,report=g.gate('runtime-audit',request,self.output,g.RUNTIME_COMMIT)
        self.assertEqual(code,0);self.assertEqual(order,['clone','verify','audit'])
        self.assertEqual(report['status'],'MATCH_RUNTIME_AUDIT_COMPLETED')
        self.assertEqual(report['request_sha256'],g.sha(raw))
        self.assertEqual(report['claim_truth'],'UNKNOWN')
        self.assertEqual(request.read_bytes(),raw)

    def test_runtime_audit_wrong_tree_never_executes(self):
        request=self.root/'request.json';request.write_bytes(self.runtime_request())
        with self.deps(),patch.object(g,'safe_git'),patch.object(self.cov,'check_checkout',return_value=dict(self.runtime_report(),tree='0'*40)),patch.object(g,'run_runtime_audit') as audit:
            code,report=g.gate('runtime-audit',request,self.output,g.RUNTIME_COMMIT)
        self.assertEqual(code,3);audit.assert_not_called();self.assertEqual(list(self.output.iterdir()),[])

    def test_runtime_audit_refuses_unselected_commit_and_invalid_input(self):
        request=self.root/'request.json';request.write_bytes(self.runtime_request())
        with patch.object(g,'safe_git') as clone:
            self.assertEqual(g.gate('runtime-audit',request,self.output,'0'*40)[0],3)
            request.write_bytes(b'{"audit_id":"x","audit_id":"y"}')
            self.assertEqual(g.gate('runtime-audit',request,self.output,g.RUNTIME_COMMIT)[0],2)
            request.write_bytes(b' '* (g.RUNTIME_INPUT_MAX+1))
            self.assertEqual(g.gate('runtime-audit',request,self.output,g.RUNTIME_COMMIT)[0],2)
            clone.assert_not_called()

    def test_runtime_audit_cleans_stage_on_execution_error(self):
        request=self.root/'request.json';request.write_bytes(self.runtime_request())
        with self.deps(),patch.object(g,'safe_git'),patch.object(self.cov,'check_checkout',return_value=self.runtime_report()),patch.object(g,'run_runtime_audit',side_effect=g.Unknown('child failed')):
            code,report=g.gate('runtime-audit',request,self.output,g.RUNTIME_COMMIT)
        self.assertEqual(code,3);self.assertEqual(list(self.output.iterdir()),[])

    def test_runtime_audit_cli_selects_fixed_pin(self):
        with patch.object(g,'gate',return_value=(0,{})) as gate:
            self.assertEqual(g.main(['runtime-audit','--input',str(self.root/'input.json'),'--output-parent',str(self.output)]),0)
        self.assertEqual(gate.call_args.args[3],g.RUNTIME_COMMIT)

    def local_bundle(self):
        bundle=self.root/'downloaded'; bundle.mkdir()
        for name,data in (('ario-full.zip',self.z),('ario-full.txt',self.t),('ario-manifest.json',self.m)):
            (bundle/name).write_bytes(data)
        return bundle

    def test_bundle_restore_both_formats_without_redownloading_manifest(self):
        bundle=self.local_bundle()
        before={p.name:p.read_bytes() for p in bundle.iterdir()}
        for fmt in ('zip','txt'):
            with self.subTest(fmt=fmt),self.fixture_pins(),self.deps(),patch.object(g,'verify_release_bytes',side_effect=lambda rel,name,data,scratch:{'asset':name,'sha256':g.sha(data)}) as v,patch.object(self.rel,'download_asset') as download,patch.object(self.cov,'check_checkout',return_value=self.report(g.SOURCE)):
                code,result=g.gate('restore-bundle',bundle,self.output,archive_format=fmt)
            self.assertEqual(code,0,result)
            self.assertEqual(result['status'],'MATCH_VERIFIED_BUNDLE_RESTORE')
            self.assertEqual(result['archive_format'],fmt)
            self.assertEqual(v.call_count,3);download.assert_not_called()
            self.assertEqual({str(p.relative_to(result['directory'])).replace(os.sep,'/'):p.read_bytes() for p in Path(result['directory']).rglob('*') if p.is_file()},self.raw)
            self.assertEqual({p.name:p.read_bytes() for p in bundle.iterdir()},before)

    def test_bundle_invalid_unused_asset_rejected_before_network(self):
        bundle=self.local_bundle()
        (bundle/'ario-full.txt').write_bytes(b'X'+self.t[1:])
        with self.fixture_pins(),self.deps(),patch.object(g,'verify_release_bytes') as verify:
            code,result=g.gate('restore-bundle',bundle,self.output)
        self.assertEqual(code,2);verify.assert_not_called();self.assertEqual(list(self.output.iterdir()),[])

    def test_bundle_missing_manifest_does_not_restore_or_download(self):
        bundle=self.local_bundle();(bundle/'ario-manifest.json').unlink()
        with self.fixture_pins(),self.deps(),patch.object(g,'verify_release_bytes') as verify,patch.object(self.rel,'download_asset') as download:
            code,result=g.gate('restore-bundle',bundle,self.output,archive_format='txt')
        self.assertEqual(code,3);verify.assert_not_called();download.assert_not_called()
        self.assertEqual(list(self.output.iterdir()),[])

    def test_bundle_failed_reference_or_postcheck_cannot_handoff(self):
        bundle=self.local_bundle()
        with self.fixture_pins(),self.deps(),patch.object(g,'verify_release_bytes',side_effect=[{},g.Unknown('offline')]),patch.object(g,'restore_zip') as restore:
            code,result=g.gate('restore-bundle',bundle,self.output)
        self.assertEqual(code,3);restore.assert_not_called();self.assertEqual(list(self.output.iterdir()),[])
        with self.fixture_pins(),self.deps(),patch.object(g,'verify_release_bytes',return_value={}),patch.object(g,'require_checkout',side_effect=g.Rejected('mismatch')):
            code,result=g.gate('restore-bundle',bundle,self.output)
        self.assertEqual(code,2);self.assertEqual(list(self.output.iterdir()),[])

    def test_bundle_cli_uses_selected_format(self):
        with patch.object(g,'gate',return_value=(0,{})) as gate:
            self.assertEqual(g.main(['restore-bundle','--directory',str(self.root),'--output-parent',str(self.output),'--format','txt']),0)
        gate.assert_called_once_with('restore-bundle',self.root,self.output,archive_format='txt')

if __name__=='__main__':unittest.main()
