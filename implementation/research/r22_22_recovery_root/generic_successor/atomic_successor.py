"""R22.22H: validate exact external successor bytes, then atomically advance a disposable retained floor.

Research-only. This is not a production admission gate, trust root, or global-latest oracle.
"""
from dataclasses import dataclass, replace
import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import event_codec as f
import successor as s

CUSTODIAN_UID = 65533
PUBLISHER_UID = 65534
MAX_PREPARED_AGE_NS = 600 * 1_000_000_000
MAX_FLOOR = 65536
RETAINED_HEAD_SIZE = 282787
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_SEAL = object()


@dataclass(frozen=True)
class Prepared:
    old_ledger: bytes
    new_ledger: bytes
    old_seq: int
    new_seq: int
    old_event_id: str
    new_event_id: str
    old_index: int
    new_index: int
    sampled_tree_size: int
    sampled_tree_root: str
    candidate_message_sha256: str
    prepared_ns: int
    _seal: object


def _write_snapshot(directory, name, data):
    path = Path(directory) / name
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return path


def prepare(anchor_path, candidate_path, verifier, live_verifier):
    """Read each archive once; verify the exact bytes that will later be committed."""
    old_raw, old_proof, submit_key = s.bundle(Path(anchor_path), True)
    new_raw, new_proof, _ = s.bundle(Path(candidate_path), False)
    old_event, new_event, old_env, new_env, new_ledger = s.link(old_raw, new_raw, s.NOSTR)
    _, verified_old_env, old_ledger, _ = f.verify_event(old_event, s.NOSTR)
    if verified_old_env["seq"] != old_env["seq"]:
        raise ValueError("HOLD_OLD_ENVELOPE_MISMATCH")
    if not new_ledger.startswith(old_ledger) or len(new_ledger) <= len(old_ledger):
        raise ValueError("HOLD_LEDGER_NOT_EXTENDED")

    old_msg = f.event_leaf_message(old_event)
    new_msg = f.event_leaf_message(new_event)
    old_size, old_index, _ = s.coordinates(old_proof)
    new_size, new_index, _ = s.coordinates(new_proof)
    if not (new_index > old_index and new_size >= old_size):
        raise ValueError("HOLD_EXTERNAL_ORDER")

    with tempfile.TemporaryDirectory(prefix="r22-22h-verified-snapshot-") as td:
        old_proof_file = _write_snapshot(td, "old.proof", old_proof)
        new_proof_file = _write_snapshot(td, "new.proof", new_proof)
        old_msg_file = _write_snapshot(td, "old.msg", old_msg)
        new_msg_file = _write_snapshot(td, "new.msg", new_msg)
        submit_file = _write_snapshot(td, "submit.pub", submit_key)
        for prefix, proof_file, msg in (("old", old_proof_file, old_msg), ("new", new_proof_file, new_msg)):
            result = subprocess.run(
                [str(Path(verifier).resolve()), "-k", str(submit_file), "-P", s.POLICY, str(proof_file)],
                input=msg, capture_output=True, timeout=30,
            )
            if result.returncode != 0:
                raise ValueError("HOLD_OFFICIAL_SIGSUM_PROOF_" + prefix.upper())
        live = subprocess.run([str(Path(live_verifier).resolve())], cwd=td, capture_output=True, timeout=150)
        if live.returncode != 0:
            raise ValueError("HOLD_LIVE_CONSISTENCY: " + live.stderr.decode("utf-8", "replace")[:300])
        live_data = json.loads(live.stdout)
        candidate_msg_hash = f.sha(new_msg)
        if not (
            live_data.get("result") == "VERIFIED_COMMON_HEAD"
            and live_data.get("old_index") == old_index
            and live_data.get("new_index") == new_index
            and live_data.get("candidate_message_sha256") == candidate_msg_hash
            and live_data.get("consistency") == "PASS"
            and type(live_data.get("sampled_tree_size")) is int
            and live_data["sampled_tree_size"] >= max(RETAINED_HEAD_SIZE, new_size)
            and type(live_data.get("sampled_tree_root")) is str
            and f.HEX64.fullmatch(live_data["sampled_tree_root"])
            and live_data.get("global_latest") == "UNKNOWN"
        ):
            raise ValueError("HOLD_LIVE_RESULT_BINDING")
        sampled_size = live_data["sampled_tree_size"]
        sampled_root = live_data["sampled_tree_root"]

    return Prepared(
        old_ledger=old_ledger,
        new_ledger=new_ledger,
        old_seq=old_env["seq"],
        new_seq=new_env["seq"],
        old_event_id=old_event["id"],
        new_event_id=new_event["id"],
        old_index=old_index,
        new_index=new_index,
        sampled_tree_size=sampled_size,
        sampled_tree_root=sampled_root,
        candidate_message_sha256=candidate_msg_hash,
        prepared_ns=time.monotonic_ns(),
        _seal=_SEAL,
    )


def _regular_fd(dir_fd, name, flags, expected_mode=0o600):
    fd = os.open(name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_uid != CUSTODIAN_UID or st.st_nlink != 1:
        os.close(fd)
        raise ValueError("HOLD_UNSAFE_FILE")
    if stat.S_IMODE(st.st_mode) != expected_mode:
        os.close(fd)
        raise ValueError("HOLD_UNSAFE_MODE")
    return fd


def _read_bounded(fd):
    chunks = []
    remaining = MAX_FLOOR + 1
    while remaining:
        part = os.read(fd, min(8192, remaining))
        if not part:
            break
        chunks.append(part)
        remaining -= len(part)
    raw = b"".join(chunks)
    if not 0 < len(raw) <= MAX_FLOOR:
        raise ValueError("HOLD_FLOOR_BOUNDS")
    return raw


def _write_all(fd, raw):
    view = memoryview(raw)
    while view:
        n = os.write(fd, view)
        if n <= 0:
            raise OSError("short write")
        view = view[n:]


def commit(root, expected_sha256, prepared, crash="none"):
    """CAS + atomic replace. Only validated in-memory snapshot bytes are eligible for commit."""
    if os.geteuid() != CUSTODIAN_UID:
        return "HOLD_WRONG_UID"
    if type(prepared) is not Prepared or prepared._seal is not _SEAL:
        return "HOLD_UNPREPARED_BYTES"
    if time.monotonic_ns() - prepared.prepared_ns > MAX_PREPARED_AGE_NS:
        return "HOLD_PREPARED_EXPIRED"
    if type(expected_sha256) is not str or not HEX64.fullmatch(expected_sha256):
        return "HOLD_EXPECTED_HASH_FORMAT"
    if expected_sha256 != hashlib.sha256(prepared.old_ledger).hexdigest():
        return "HOLD_CAS_MISMATCH"
    if not prepared.new_ledger.startswith(prepared.old_ledger) or len(prepared.new_ledger) <= len(prepared.old_ledger):
        return "HOLD_UNPREPARED_TRANSITION"

    dir_fd = -1
    lock_fd = -1
    try:
        dir_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        dst = os.fstat(dir_fd)
        if not stat.S_ISDIR(dst.st_mode) or dst.st_uid != CUSTODIAN_UID or stat.S_IMODE(dst.st_mode) != 0o700:
            return "HOLD_UNSAFE_DIRECTORY"
        lock_fd = _regular_fd(dir_fd, "lock", os.O_RDWR)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        floor_fd = _regular_fd(dir_fd, "floor", os.O_RDONLY)
        try:
            current = _read_bounded(floor_fd)
        finally:
            os.close(floor_fd)
        if current == prepared.new_ledger:
            return "HOLD_ALREADY_RETAINED"
        if current != prepared.old_ledger:
            return "HOLD_FLOOR_NOT_PREDECESSOR"
        if hashlib.sha256(current).hexdigest() != expected_sha256:
            return "HOLD_CAS_MISMATCH"

        try:
            pending_fd = _regular_fd(dir_fd, "pending", os.O_RDONLY)
        except FileNotFoundError:
            pending_fd = -1
        if pending_fd >= 0:
            try:
                pending = _read_bounded(pending_fd)
            finally:
                os.close(pending_fd)
            if pending != prepared.new_ledger:
                return "HOLD_PENDING_CONFLICT"
            os.replace("pending", "floor", src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
            os.fsync(dir_fd)
            return "ADVANCED_RESEARCH_ONLY_RECOVERED_PENDING"

        pending_fd = os.open("pending", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dir_fd)
        st = os.fstat(pending_fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != CUSTODIAN_UID or st.st_nlink != 1:
            os.close(pending_fd)
            return "HOLD_UNSAFE_PENDING"
        try:
            _write_all(pending_fd, prepared.new_ledger)
            os.fsync(pending_fd)
        finally:
            os.close(pending_fd)
        os.fsync(dir_fd)
        if crash == "before":
            os._exit(75)
        os.replace("pending", "floor", src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
        os.fsync(dir_fd)
        if crash == "after":
            os._exit(76)
        return "ADVANCED_RESEARCH_ONLY"
    except (OSError, ValueError, TypeError):
        return "HOLD_STORE_OR_VALIDATION"
    finally:
        if lock_fd >= 0:
            os.close(lock_fd)
        if dir_fd >= 0:
            os.close(dir_fd)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _create_box(parent, name, old_bytes, pending=None):
    box = Path(parent) / name
    box.mkdir()
    os.chown(box, CUSTODIAN_UID, CUSTODIAN_UID)
    os.chmod(box, 0o700)
    for filename, raw in (("floor", old_bytes), ("lock", b"")):
        path = box / filename
        path.write_bytes(raw)
        os.chown(path, CUSTODIAN_UID, CUSTODIAN_UID)
        os.chmod(path, 0o600)
    if pending is not None:
        path = box / "pending"
        path.write_bytes(pending)
        os.chown(path, CUSTODIAN_UID, CUSTODIAN_UID)
        os.chmod(path, 0o600)
    return box


def _as_uid(uid, fn):
    os.seteuid(uid)
    try:
        return fn()
    finally:
        os.seteuid(0)


def exercise(prepared, candidate_copy):
    if os.geteuid() != 0:
        raise RuntimeError("test harness requires root to model separate UIDs")
    import shutil
    import tempfile
    checks = []
    roots = []

    def check(name, got, want):
        if got != want:
            raise AssertionError((name, got, want))
        checks.append(name)
        print(name + " PASS", flush=True)

    def box(name, floor=None, pending=None):
        parent = tempfile.mkdtemp(prefix="r22-22h-")
        roots.append(parent)
        os.chmod(parent, 0o755)
        return _create_box(parent, name, prepared.old_ledger if floor is None else floor, pending)

    try:
        b = box("wronguid")
        check("01_publisher_cannot_commit", _as_uid(PUBLISHER_UID, lambda: commit(b, sha(prepared.old_ledger), prepared)), "HOLD_WRONG_UID")

        b = box("permissions")
        def publisher_read_write():
            results=[]
            for flags in (os.O_RDONLY, os.O_WRONLY):
                try:
                    fd=os.open(b/"floor", flags); os.close(fd); results.append(False)
                except PermissionError:
                    results.append(True)
            try:
                os.unlink(b/"floor"); results.append(False)
            except PermissionError:
                results.append(True)
            return results
        check("02_publisher_read_write_delete_denied", _as_uid(PUBLISHER_UID, publisher_read_write), [True, True, True])

        b = box("wrongcas")
        check("03_wrong_expected_hash", _as_uid(CUSTODIAN_UID, lambda: commit(b, "0"*64, prepared)), "HOLD_CAS_MISMATCH")

        b = box("badfloor", floor=b"not-the-retained-ledger")
        check("04_wrong_floor_bytes", _as_uid(CUSTODIAN_UID, lambda: commit(b, sha(prepared.old_ledger), prepared)), "HOLD_FLOOR_NOT_PREDECESSOR")

        forged = replace(prepared, _seal=None)
        b = box("forgedprepared")
        check("05_forged_prepared_object", _as_uid(CUSTODIAN_UID, lambda: commit(b, sha(prepared.old_ledger), forged)), "HOLD_UNPREPARED_BYTES")

        expired = replace(prepared, prepared_ns=time.monotonic_ns() - MAX_PREPARED_AGE_NS - 1)
        b = box("expired")
        check("06_expired_validation", _as_uid(CUSTODIAN_UID, lambda: commit(b, sha(prepared.old_ledger), expired)), "HOLD_PREPARED_EXPIRED")

        b = box("pendingconflict", pending=b"attacker bytes")
        check("07_pending_conflict", _as_uid(CUSTODIAN_UID, lambda: commit(b, sha(prepared.old_ledger), prepared)), "HOLD_PENDING_CONFLICT")

        b = box("symlinkfloor")
        (b/"floor").unlink(); (b/"floor").symlink_to("lock")
        check("08_floor_symlink", _as_uid(CUSTODIAN_UID, lambda: commit(b, sha(prepared.old_ledger), prepared)), "HOLD_STORE_OR_VALIDATION")

        b = box("symlinklock")
        (b/"lock").unlink(); (b/"lock").symlink_to("floor")
        check("09_lock_symlink", _as_uid(CUSTODIAN_UID, lambda: commit(b, sha(prepared.old_ledger), prepared)), "HOLD_STORE_OR_VALIDATION")

        b = box("valid")
        check("10_exact_validated_advance", _as_uid(CUSTODIAN_UID, lambda: commit(b, sha(prepared.old_ledger), prepared)), "ADVANCED_RESEARCH_ONLY")
        check("11_exact_candidate_bytes_retained", (b/"floor").read_bytes(), prepared.new_ledger)
        check("12_retry_is_idempotent_hold", _as_uid(CUSTODIAN_UID, lambda: commit(b, sha(prepared.old_ledger), prepared)), "HOLD_ALREADY_RETAINED")

        b = box("crashbefore")
        pid=os.fork()
        if pid==0:
            os.seteuid(CUSTODIAN_UID)
            commit(b, sha(prepared.old_ledger), prepared, "before")
            os._exit(99)
        _,status=os.waitpid(pid,0)
        check("13_crash_before_replace_exit", os.waitstatus_to_exitcode(status), 75)
        check("14_crash_before_keeps_old_floor", (b/"floor").read_bytes(), prepared.old_ledger)
        check("15_crash_before_pending_exact", (b/"pending").read_bytes(), prepared.new_ledger)
        check("16_retry_recovers_pending", _as_uid(CUSTODIAN_UID, lambda: commit(b, sha(prepared.old_ledger), prepared)), "ADVANCED_RESEARCH_ONLY_RECOVERED_PENDING")
        check("17_recovered_pending_floor", (b/"floor").read_bytes(), prepared.new_ledger)

        b = box("crashafter")
        pid=os.fork()
        if pid==0:
            os.seteuid(CUSTODIAN_UID)
            commit(b, sha(prepared.old_ledger), prepared, "after")
            os._exit(99)
        _,status=os.waitpid(pid,0)
        check("18_crash_after_replace_exit", os.waitstatus_to_exitcode(status), 76)
        check("19_crash_after_floor_is_new", (b/"floor").read_bytes(), prepared.new_ledger)
        check("20_retry_after_commit", _as_uid(CUSTODIAN_UID, lambda: commit(b, sha(prepared.old_ledger), prepared)), "HOLD_ALREADY_RETAINED")

        b = box("concurrent")
        from concurrent.futures import ThreadPoolExecutor
        def parallel():
            with ThreadPoolExecutor(max_workers=8) as pool:
                return list(pool.map(lambda _: commit(b, sha(prepared.old_ledger), prepared), range(8)))
        outcomes = _as_uid(CUSTODIAN_UID, parallel)
        check("21_concurrent_one_advance", outcomes.count("ADVANCED_RESEARCH_ONLY"), 1)
        check("22_concurrent_seven_idempotent_holds", outcomes.count("HOLD_ALREADY_RETAINED"), 7)
        check("23_concurrent_final_bytes", (b/"floor").read_bytes(), prepared.new_ledger)

        b = box("rootrollback")
        check("24_root_rollback_initial_advance", _as_uid(CUSTODIAN_UID, lambda: commit(b, sha(prepared.old_ledger), prepared)), "ADVANCED_RESEARCH_ONLY")
        (b/"floor").write_bytes(prepared.old_ledger)
        os.chown(b/"floor", CUSTODIAN_UID, CUSTODIAN_UID); os.chmod(b/"floor", 0o600)
        check("25_same_root_rollback_replay", _as_uid(CUSTODIAN_UID, lambda: commit(b, sha(prepared.old_ledger), prepared)), "ADVANCED_RESEARCH_ONLY")

        # The candidate archive is deliberately changed after prepare(). Commit must use only the immutable snapshot.
        Path(candidate_copy).write_bytes(b"replaced after validation")
        b = box("snapshot")
        check("26_candidate_path_changed_after_prepare", _as_uid(CUSTODIAN_UID, lambda: commit(b, sha(prepared.old_ledger), prepared)), "ADVANCED_RESEARCH_ONLY")
        check("27_snapshot_committed_exact_bytes", (b/"floor").read_bytes(), prepared.new_ledger)

        print("27/27 EXPECTED CONTROLS PASS; SAME_ROOT_ROLLBACK=RED; GLOBAL_LATEST=UNKNOWN; TRUST=NO_GO; PRODUCTION=NO_GO")
        return checks
    finally:
        for parent in roots:
            shutil.rmtree(parent, ignore_errors=True)


def main(argv):
    if len(argv) != 6 or argv[1] != "test":
        raise SystemExit("usage: atomic_successor.py test ANCHOR.zip CANDIDATE.zip SIGSUM-VERIFY LIVE-VERIFIER")
    import shutil
    with tempfile.TemporaryDirectory(prefix="r22-22h-input-") as td:
        candidate_copy = Path(td)/"candidate.zip"
        shutil.copyfile(argv[3], candidate_copy)
        prepared = prepare(argv[2], candidate_copy, argv[4], argv[5])
        print(json.dumps({"prepare":"LINKED_SUCCESSOR_RESEARCH_ONLY","old_seq":prepared.old_seq,"new_seq":prepared.new_seq,"old_index":prepared.old_index,"new_index":prepared.new_index,"sampled_tree_size":prepared.sampled_tree_size,"sampled_tree_root":prepared.sampled_tree_root,"ledger_sha256":sha(prepared.new_ledger),"global_latest":"UNKNOWN","admission":False},sort_keys=True),flush=True)
        exercise(prepared, candidate_copy)

if __name__ == "__main__":
    main(sys.argv)
