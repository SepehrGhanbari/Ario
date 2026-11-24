"""Disposable Linux UID/SQLite test; supervisor has common root power."""
import concurrent.futures as cf
import hashlib,os,shutil,sqlite3,subprocess,sys,tempfile,zipfile
from pathlib import Path
from nonce_ledger import CUSTODIAN,PUBLISHER,PINS,digest
PIN='b7f1702b88241f6062c6e9c3975e5969620e98b6fc47321ca7e91956c7500f8e'

def run(archive):
    assert sys.platform=='linux' and os.geteuid()==0
    assert digest(archive.read_bytes())==PIN
    with tempfile.TemporaryDirectory(prefix='r22-18-') as d:
        root=Path(d); root.chmod(0o755)
        fixtures=root/'fixtures'; fixtures.mkdir()
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            for n in ['ca.pem','tsa.pem','a.tsq','b.tsq','a.tsr','b.tsr']:
                (fixtures/n).write_bytes(z.read(n)); (fixtures/n).chmod(0o444)
        fixtures.chmod(0o555)
        for n,h in PINS.items(): assert digest((fixtures/n).read_bytes())==h
        ledger=root/'custodian'; ledger.mkdir(); os.chown(ledger,CUSTODIAN,CUSTODIAN); ledger.chmod(0o700)
        pub=root/'publisher'; pub.mkdir(); os.chown(pub,PUBLISHER,PUBLISHER); pub.chmod(0o755)
        script=root/'nonce_ledger.py'; shutil.copyfile(Path(__file__).with_name('nonce_ledger.py'),script); script.chmod(0o444)
        db=ledger/'ledger.sqlite'; env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'}
        def child(uid,args): return subprocess.run(args,user=uid,group=uid,extra_groups=[],env=env,cwd=root,capture_output=True,text=True,timeout=40)
        def call(q='a.tsq',r='a.tsr',crash='none',uid=CUSTODIAN):
            qp=fixtures/q if isinstance(q,str) else q; rp=fixtures/r if isinstance(r,str) else r
            return child(uid,[sys.executable,'-I','-B',str(script),str(db),str(fixtures),'consume',str(qp),str(rp),crash])
        def check(name,got,want):
            if got!=want: raise AssertionError((name,got,want))
            print(name,got,'PASS',flush=True)
        def result(**kw):
            r=call(**kw)
            if r.returncode: raise AssertionError((r.returncode,r.stderr))
            return r.stdout.strip()
        def rows():
            with sqlite3.connect(db) as c: return c.execute('SELECT nonce,response_hash FROM challenges ORDER BY nonce').fetchall()
        # Publisher actually installs and later restores its own request-state file.
        install='import os,pathlib,sys; p=pathlib.Path(sys.argv[2]); q=p.with_suffix(".tmp"); q.write_bytes(pathlib.Path(sys.argv[1]).read_bytes()); os.replace(q,p)'
        def restore(name):
            r=child(PUBLISHER,[sys.executable,"-c",install,str(fixtures/name),str(pub/"current")]); assert r.returncode==0,r.stderr
            assert (pub/"current").read_bytes()==(fixtures/name).read_bytes()
        restore("a.tsq")
        init=child(CUSTODIAN,[sys.executable,'-I','-B',str(script),str(db),str(fixtures),'init']); assert init.returncode==0,init.stderr
        initial=db.read_bytes(); old=rows(); assert len(old)==2 and all(v is None for _,v in old)
        a=digest((fixtures/'a.tsr').read_bytes()); b=digest((fixtures/'b.tsr').read_bytes()); used='HOLD_ALREADY_CONSUMED:'; success='CONSUMED_RESEARCH_ONLY:'
        check('01_cross_replay_before_consume',result(r='b.tsr'),'HOLD_INVALID_RESPONSE'); assert rows()==old
        tamper=root/'tampered.tsr'; raw=bytearray((fixtures/'a.tsr').read_bytes()); raw[-1]^=1; tamper.write_bytes(raw)
        check('02_tampered_response',result(r=tamper),'HOLD_INVALID_RESPONSE'); assert rows()==old
        unknown=root/'unknown.tsq'; unknown.write_bytes((fixtures/'a.tsq').read_bytes()+b'\0')
        check('03_unknown_request',result(q=unknown),'HOLD_UNKNOWN_REQUEST')
        check('04_crash_before_commit',call(crash='before').returncode,75); assert rows()==old
        check('05_retry_after_precommit_crash',result(),success+a)
        check('06_restart_replay',result(),used+a)
        check('07_publisher_direct_consume',result(uid=PUBLISHER),'HOLD_WRONG_UID')
        restore("b.tsq"); restore("a.tsq")
        before=db.read_bytes()
        for label,expr in [('08_read_ledger','p.read_bytes()'),('09_overwrite_ledger','p.write_bytes(b"reset")'),('10_delete_ledger','p.unlink()')]:
            r=child(PUBLISHER,[sys.executable,'-c','import pathlib,sys; p=pathlib.Path(sys.argv[1]);\ntry:\n '+expr+'\nexcept PermissionError:\n print("DENIED")\nelse:\n sys.exit(99)',str(db)])
            assert r.returncode==0,r.stderr; check(label,r.stdout.strip(),'DENIED')
        assert db.read_bytes()==before
        check('11_publisher_rollback_replay',result(q=pub/'current'),used+a)
        db.rename(ledger/'offline'); check('12_ledger_outage',result(),'HOLD_LEDGER_OR_VERIFIER_UNAVAILABLE'); assert not db.exists(); (ledger/'offline').rename(db)
        check('13_reconnect',result(),used+a)
        check('14_crash_after_commit',call('b.tsq','b.tsr','after').returncode,76)
        check('15_retry_after_postcommit_crash',result(q='b.tsq',r='b.tsr'),used+b)
        final=db.read_bytes()
        # Common root restores initial DB while no children run. This is deliberately RED.
        db.write_bytes(initial)
        check('16_common_admin_rollback_RED',result(),success+a)
        # Reset ONLY test fixture under supervisor, preserve actual concurrency results afterwards.
        db.write_bytes(initial)
        with cf.ThreadPoolExecutor(max_workers=8) as pool:
            outcomes=list(pool.map(lambda _:result(),range(8)))
        check('17_eight_concurrent_one_consumer',outcomes.count(success+a),1)
        check('18_seven_concurrent_replays',outcomes.count(used+a),7)
        assert len(rows())==2 and sum(v is not None for _,v in rows())==1
        # Restore fully consumed reference; demonstrate that it holds both.
        db.write_bytes(final); check('19_both_consumed_after_restore',result(q='b.tsq',r='b.tsr'),used+b)
        check('20_first_still_consumed',result(),used+a)
    print('20/20 PASS; COMMON_ADMIN_ROLLBACK=RED; INDEPENDENT_CUSTODY=NOT_ESTABLISHED; TRUST=NO_GO; PRODUCTION=NO_GO')

if __name__=='__main__': run(Path(sys.argv[1]).resolve())
