"""R22.13: actual publisher-file restore, archived TEST receipts, two Linux UIDs.
No administrative-independence or global-freshness claim. Root is the lab supervisor.
"""
import argparse
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parent.parent / 'r22_12_authentic_replay'))
import replay

PUBLISHER, CUSTODIAN = 65534, 65533
MATCH = 'MATCH_RETAINED_FLOOR_NOT_FRESHNESS'
ROLLBACK = 'HOLD_ROLLBACK_BELOW_FLOOR'


def bounded(path, limit=16384):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
            raise ValueError('not a regular file')
        raw = f.read(limit + 1)
        if not 0 < len(raw) <= limit:
            raise ValueError('size')
        return raw


def evidence(path, structural):
    raw = bounded(path)
    kind = next((k for k in ('old', 'new') if replay.sha(raw) == replay.PINS[k]), None)
    if kind is None:
        raise ValueError('unknown archive')
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'snapshot.zip'
        p.write_bytes(raw)
        parts = replay.read_archive(p, kind)
    if not structural and not replay.verify(parts):
        raise ValueError('official proof failed')
    return replay.describe(parts), parts[0]


def probe(root, structural):
    if os.getuid() != CUSTODIAN:
        raise RuntimeError('wrong verifier UID')
    try:
        floor, raw = evidence(root / 'custodian/floor.zip', structural)
        if raw != bounded(root / 'custodian/content.json', 4096):
            raise ValueError('floor content mismatch')
    except (OSError, ValueError, subprocess.SubprocessError):
        return 'HOLD_FLOOR_UNAVAILABLE_OR_INVALID'
    try:
        candidate, _ = evidence(root / 'publisher/current.zip', structural)
    except (OSError, ValueError, subprocess.SubprocessError):
        return 'HOLD_CANDIDATE_UNAVAILABLE_OR_INVALID'
    return replay.decide(candidate, floor)


def run(old_zip, new_zip, external, structural):
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise RuntimeError('requires disposable Linux root lab')
    old_parts = replay.read_archive(old_zip, 'old')
    new_parts = replay.read_archive(new_zip, 'new')
    if bounded(external, 4096) != new_parts[0]:
        raise ValueError('external content mismatch')
    if not structural and not (replay.verify(old_parts) and replay.verify(new_parts)):
        raise ValueError('official initial proofs failed')
    print('MODE', 'STRUCTURAL_ONLY' if structural else 'OFFICIAL_OFFLINE_VERIFICATION', flush=True)
    print('EXTERNAL_INPUT_MATCH', replay.commitment(new_parts[0]), flush=True)
    with tempfile.TemporaryDirectory(prefix='r22-13-') as d:
        root = Path(d)
        root.chmod(0o755)
        for name, uid, mode in [('publisher', PUBLISHER, 0o755), ('custodian', CUSTODIAN, 0o700)]:
            p = root / name
            p.mkdir(); os.chown(p, uid, uid); p.chmod(mode)
        for src, name in [(Path(__file__), 'isolation.py'), (Path(replay.__file__), 'replay.py'), (old_zip, 'old.zip'), (new_zip, 'new.zip')]:
            dst = root / name
            shutil.copyfile(src, dst); dst.chmod(0o644)
        pub = root / 'publisher/current.zip'
        floor = root / 'custodian/floor.zip'
        content = root / 'custodian/content.json'
        env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1', 'LANG': 'C.UTF-8'}

        def child(uid, code, *args):
            return subprocess.run([sys.executable, '-I', '-B', '-c', code, *map(str, args)], cwd=root, env=env, user=uid, group=uid, extra_groups=[], capture_output=True, text=True, timeout=90)

        def publisher_restore(src):
            r = child(PUBLISHER, 'import os, pathlib, sys; assert os.getuid()==65534; p=pathlib.Path(sys.argv[2]); q=p.with_suffix(".tmp"); q.write_bytes(pathlib.Path(sys.argv[1]).read_bytes()); os.chmod(q,0o644); os.replace(q,p)', src, pub)
            if r.returncode or pub.read_bytes() != src.read_bytes():
                raise AssertionError(('publisher restore', r.stderr))

        def set_floor(src, raw):
            for p, data in [(floor, src.read_bytes()), (content, raw)]:
                p.write_bytes(data); os.chown(p, CUSTODIAN, CUSTODIAN); p.chmod(0o600)

        def check(label, expected):
            r = child(CUSTODIAN, 'import sys; sys.path.insert(0,sys.argv[1]); import isolation; from pathlib import Path; print(isolation.probe(Path(sys.argv[1]),sys.argv[2]=="1"))', root, int(structural))
            if r.returncode or r.stdout.strip() != expected:
                raise AssertionError((label, r.stdout, r.stderr, expected))
            print(label, expected, 'PASS', flush=True)

        set_floor(new_zip, bounded(external, 4096))
        pin = (replay.sha(floor.read_bytes()), replay.sha(content.read_bytes()))
        publisher_restore(root / 'new.zip')
        check('01_new_matches_floor', MATCH)
        publisher_restore(root / 'old.zip')
        check('02_real_publisher_restore', ROLLBACK)
        # Actual permission denials, not mocks. The shared root retains override power.
        for label, expr in [('03_read_floor', 'p.read_bytes()'), ('04_overwrite_floor', 'p.write_bytes(b"bad")'), ('05_unlink_floor', 'p.unlink()'), ('06_rename_floor', 'p.rename(p.with_name("old"))'), ('07_replace_floor', 'os.replace(s,p)'), ('08_chmod_floor_dir', 'p.parent.chmod(0o777)')]:
            r = child(PUBLISHER, 'import pathlib,os,sys; p=pathlib.Path(sys.argv[1]); s=pathlib.Path(sys.argv[2]);\ntry:\n '+expr+'\nexcept PermissionError:\n print("DENIED")\nelse:\n sys.exit(99)', floor, pub)
            if r.returncode or r.stdout.strip() != 'DENIED':
                raise AssertionError((label, r.stdout, r.stderr))
            print(label, 'PERMISSION_DENIED PASS', flush=True)
        # Present a valid old floor in the publisher's own namespace; fixed custodian path wins.
        spoof = root / 'publisher/floor.zip'
        r = child(PUBLISHER, 'import pathlib,sys; pathlib.Path(sys.argv[2]).write_bytes(pathlib.Path(sys.argv[1]).read_bytes())', root/'old.zip', spoof)
        if r.returncode or spoof.read_bytes() != old_zip.read_bytes():
            raise AssertionError('spoof setup')
        check('09_publisher_floor_replay_ignored', ROLLBACK)
        assert (replay.sha(floor.read_bytes()), replay.sha(content.read_bytes())) == pin
        floor.rename(floor.with_suffix('.offline'))
        check('10_floor_outage_no_fallback', 'HOLD_FLOOR_UNAVAILABLE_OR_INVALID')
        floor.with_suffix('.offline').rename(floor)
        check('11_floor_reconnect', ROLLBACK)
        content.write_bytes(old_parts[0])
        check('12_old_content_new_receipt', 'HOLD_FLOOR_UNAVAILABLE_OR_INVALID')
        content.write_bytes(new_parts[0])
        r = child(PUBLISHER, 'import os,sys; os.unlink(sys.argv[1]); os.symlink(sys.argv[2],sys.argv[1])', pub, floor)
        if r.returncode:
            raise AssertionError(r.stderr)
        check('13_symlink_candidate', 'HOLD_CANDIDATE_UNAVAILABLE_OR_INVALID')
        publisher_restore(root / 'old.zip')
        assert (replay.sha(floor.read_bytes()), replay.sha(content.read_bytes())) == pin
        # Deliberate negative control: common administrator really can reset both domains.
        set_floor(old_zip, old_parts[0])
        check('14_common_admin_joint_rollback_RED', MATCH)
        set_floor(new_zip, new_parts[0])
        check('15_restore_custodian_after_control', ROLLBACK)
        publisher_restore(root/'new.zip')
        check('16_new_again_matches', MATCH)
        assert (replay.sha(floor.read_bytes()), replay.sha(content.read_bytes())) == pin
    print('16/16 PASS; SHARED_ROOT_RESET=RED; INDEPENDENT_ADMIN=NOT_ESTABLISHED; TRUST=NO_GO; PRODUCTION=NO_GO')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('old', type=Path); p.add_argument('new', type=Path); p.add_argument('external', type=Path)
    p.add_argument('--structural-only', action='store_true')
    a = p.parse_args()
    run(a.old.resolve(), a.new.resolve(), a.external.resolve(), a.structural_only)
