"""Disposable root-supervised Linux test, actual archived TSA replies."""
import concurrent.futures as cf
import os, shutil, sqlite3, subprocess, sys, tempfile, zipfile
from pathlib import Path
from nonce_ledger import CUSTODIAN,PUBLISHER,PINS,digest,verify
PIN='b7f1702b88241f6062c6e9c3975e5969620e98b6fc47321ca7e91956c7500f8e'

def run(archive):
    assert sys.platform=='linux' and os.geteuid()==0 and digest(archive.read_bytes())==PIN
    with tempfile.TemporaryDirectory(prefix='r22-19-') as d:
        root=Path(d); root.chmod(0o755); f=root/'fixtures'; f.mkdir()
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            for n in ('ca.pem','tsa.pem','a.tsq','b.tsq','a.tsr','b.tsr'):
                (f/n).write_bytes(z.read(n)); (f/n).chmod(0o444)
        f.chmod(0o555)
        for n,h in PINS.items(): assert digest((f/n).read_bytes())==h
        for n in ('lifecycle.py','nonce_ledger.py'):
            shutil.copyfile(Path(__file__).with_name(n),root/n); (root/n).chmod(0o444)
        ledger=root/'custodian'; ledger.mkdir(); os.chown(ledger,CUSTODIAN,CUSTODIAN); ledger.chmod(0o700)
        pub=root/'publisher'; pub.mkdir(); os.chown(pub,PUBLISHER,PUBLISHER); pub.chmod(0o755)
        db=ledger/'state.sqlite'; env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'}
        def child(uid,args): return subprocess.run(args,user=uid,group=uid,extra_groups=[],env=env,cwd=root,capture_output=True,text=True,timeout=40)
        def call(op,e=1,n='a.tsq',r='-',crash='none',uid=CUSTODIAN):
            p=child(uid,[sys.executable,'-B',str(root/'lifecycle.py'),str(db),str(f),op,str(e),n,str(f/r) if r!='-' else '-',crash])
            if p.returncode not in (0,75,76): raise AssertionError(p.stderr)
            return p.stdout.strip() if p.returncode==0 else p.returncode
        def state():
            with sqlite3.connect(db) as c: return c.execute('SELECT epoch FROM session').fetchone()[0],c.execute('SELECT epoch,state FROM challenges ORDER BY epoch,query_hash').fetchall()
        count=0
        def check(label,got,want):
            nonlocal count
            if got!=want: raise AssertionError((label,got,want))
            count+=1; print(label,got,'PASS',flush=True)
        check('01_init',call('init'),'INITIALIZED:1')
        check('02_old_response_crypto_valid',verify(f,(f/'a.tsq').read_bytes(),(f/'a.tsr').read_bytes()),True)
        check('03_unissued',call('consume',r='a.tsr'),'HOLD_NOT_ENROLLED')
        check('04_issue',call('issue'),'ISSUED:1')
        check('05_duplicate_issue',call('issue'),'HOLD_NONCE_ALREADY_ENROLLED')
        prior=db.read_bytes(); before=state()
        check('06_rotate_crash_before',call('rotate',crash='before'),75); assert state()==before
        check('07_rotate_crash_after',call('rotate',crash='after'),76); assert state()==(2,[(1,'ABANDONED')])
        check('08_retry_stale_rotate',call('rotate'),'HOLD_EPOCH_MISMATCH')
        check('09_old_epoch_response',call('consume',r='a.tsr'),'HOLD_EPOCH_MISMATCH')
        check('10_old_response_current_epoch',call('consume',2,r='a.tsr'),'HOLD_ABANDONED')
        check('11_reissue_abandoned_nonce',call('issue',2),'HOLD_NONCE_ALREADY_ENROLLED')
        check('12_issue_new',call('issue',2,'b.tsq'),'ISSUED:2')
        check('13_cross_response',call('consume',2,'b.tsq','a.tsr'),'HOLD_INVALID_RESPONSE')
        check('14_consume',call('consume',2,'b.tsq','b.tsr'),'CONSUMED_RESEARCH_ONLY')
        check('15_consumed_restart',call('consume',2,'b.tsq','b.tsr'),'HOLD_CONSUMED')
        check('16_cannot_abandon_consumed',call('abandon',2,'b.tsq'),'HOLD_CONSUMED')
        check('17_publisher_cannot_rotate',call('rotate',2,uid=PUBLISHER),'HOLD_WRONG_UID')
        p=child(PUBLISHER,[sys.executable,'-c','import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text("2"); p.write_text("1"); print(p.read_text())',str(pub/'epoch')]); assert p.returncode==0
        check('18_real_publisher_epoch_restore',call('consume',int(p.stdout),r='a.tsr'),'HOLD_EPOCH_MISMATCH')
        final=db.read_bytes(); db.rename(ledger/'offline')
        check('19_missing_ledger',call('rotate',2),'HOLD_LEDGER_OR_VERIFIER_UNAVAILABLE'); assert not db.exists(); (ledger/'offline').rename(db)
        check('20_reconnect',call('consume',2,r='a.tsr'),'HOLD_ABANDONED')
        db.write_bytes(prior)
        check('21_common_admin_rollback_RED',call('consume',r='a.tsr'),'CONSUMED_RESEARCH_ONLY')
        db.write_bytes(prior)
        with cf.ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(call,'rotate'); b=pool.submit(call,'consume',1,'a.tsq','a.tsr'); rotation,consumption=a.result(),b.result()
        assert rotation=='ROTATED:2' and consumption in ('CONSUMED_RESEARCH_ONLY','HOLD_EPOCH_MISMATCH')
        assert state() in ((2,[(1,'CONSUMED')]),(2,[(1,'ABANDONED')]))
        check('22_rotate_consume_serializable',True,True)
        check('23_after_race_old_epoch',call('consume',r='a.tsr'),'HOLD_EPOCH_MISMATCH')
        db.write_bytes(prior)
        check('24_explicit_abandon',call('abandon'),'ABANDONED')
        check('25_explicit_abandon_terminal',call('consume',r='a.tsr'),'HOLD_ABANDONED')
        db.write_bytes(final)
        check('26_consumed_survives_rotation',call('rotate',2),'ROTATED:3'); assert state()==(3,[(1,'ABANDONED'),(2,'CONSUMED')])
        check('27_consumed_nonce_never_reissued',call('issue',3,'b.tsq'),'HOLD_NONCE_ALREADY_ENROLLED')
        print(f'{count}/{count} PASS; COMMON_ADMIN_ROLLBACK=RED; LIVE_ISSUANCE=NOT_ESTABLISHED; TRUST=NO_GO; PRODUCTION=NO_GO')

if __name__=='__main__': run(Path(sys.argv[1]).resolve())
