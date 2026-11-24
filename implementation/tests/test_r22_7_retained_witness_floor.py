"""R22.7: R22.6 checkpoint evidence + unchanged R10 durable floor writer.

A bounded laboratory adapter, not a runtime custodian or an event feed.
The controller supplies synthetic observed events. A separate Linux UID
experiment tests actual filesystem exclusion, not administrative independence.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest

import checkpoint_prefix_experiment as prefix
import independent_witness_experiment as witness
from research.r10_durable_monitor import monitor as r10
from test_r22_6_ci_witness_prefix_integration import (
    SCOPE, CONTEXT, KEY, control, observed_rows, ledger,
)
from test_r22_5_replay_aba_boundary import sample


def floor_record(rows, count):
    retained = control(rows, floor=count, count=count)
    records = []
    for anchor in retained.anchors:
        records.append({
            "role": anchor.role,
            "checkpoint": anchor.checkpoint_bytes.decode("ascii"),
            "parent": (None if anchor.parent_checkpoint_bytes is None else
                       anchor.parent_checkpoint_bytes.decode("ascii")),
        })
    raw = ledger(rows[:count])
    return {
        "scope": SCOPE, "seq": count,
        "head": rows[count - 1]["sha256"],
        "prefix_sha256": hashlib.sha256(raw).hexdigest(),
        "anchors": records,
    }


def read_floor(path):
    """Read and validate the retained *laboratory* record, never a candidate pin."""
    with path.open("rb") as stream:
        raw = stream.read(32769)
    if len(raw) > 32768:
        raise ValueError("oversized floor")
    record = json.loads(raw.decode("ascii"))
    if (type(record) is not dict
            or set(record) != {"scope", "seq", "head", "prefix_sha256", "anchors"}
            or record["scope"] != SCOPE
            or type(record["seq"]) is not int or record["seq"] not in (2, 4)
            or raw != r10.canonical(record) + b"\n"
            or type(record["anchors"]) is not list or len(record["anchors"]) != 2):
        raise ValueError("invalid floor")
    anchors = []
    for role, entry in zip(("A", "B"), record["anchors"]):
        if (type(entry) is not dict or set(entry) != {"role", "checkpoint", "parent"}
                or entry["role"] != role or type(entry["checkpoint"]) is not str):
            raise ValueError("invalid retained anchor")
        cp_raw = entry["checkpoint"].encode("ascii")
        cp = prefix._checkpoint(cp_raw)  # reuse existing strict bounded parser
        if (any(cp[k] != v for k, v in SCOPE.items())
                or cp["test_identity"] != f"TEST-KEEPER-{role}"
                or cp["record_count"] != record["seq"]
                or cp["head_sha256"] != record["head"]
                or cp["prefix_sha256"] != record["prefix_sha256"]):
            raise ValueError("anchor/floor mismatch")
        parent_raw = None
        if record["seq"] == 4:
            if type(entry["parent"]) is not str:
                raise ValueError("missing parent")
            parent_raw = entry["parent"].encode("ascii")
            parent = prefix._checkpoint(parent_raw)
            if (any(parent[k] != v for k, v in SCOPE.items())
                    or parent["record_count"] != 2
                    or parent["test_identity"] != cp["test_identity"]
                    or parent["checkpoint_sha256"] != cp["previous_checkpoint_sha256"]):
                raise ValueError("retained parent mismatch")
        elif entry["parent"] is not None:
            raise ValueError("unexpected parent")
        anchors.append(witness.seal_test_envelope(
            role=role, witness_id=f"TEST-KEEPER-{role}",
            custody_domain_label=f"LAB-GROUP-{role}", checkpoint_bytes=cp_raw,
            parent_checkpoint_bytes=parent_raw,
            snapshot_reference=f"R22.7-{role}", capture_sequence=record["seq"],
            declared_provenance="SYNTHETIC-DURABLE-ORACLE-NOT-AUTHENTICATED",
        ))
    return record, witness.WitnessControl(
        anchors=tuple(anchors), context=CONTEXT,
        symbolic_bindings=(("TEST-KEEPER-A", KEY), ("TEST-KEEPER-B", KEY)),
        known_floor=record["seq"], laboratory_isolated_roles=("A", "B"),
    )


def compare_bytes(raw, retained):
    report = witness.verify_witnesses(witness.WitnessCase(
        candidate_bytes=raw, presented=retained.anchors, control=retained,
        candidate_key_descriptor=KEY, attacker_capability="SYNTHETIC-PUBLISHER-ROLLBACK",
    ))
    assert report.historical_custody_independence == "NOT_ESTABLISHED"
    assert report.historical_event_truth == "UNKNOWN"
    assert report.evidence_admission == "NOT_EVALUATED"
    assert report.production_historical_continuity == "INCONCLUSIVE"
    return report


def provision(path, rows):
    if path.exists():
        raise ValueError("explicit bootstrap only")
    r10._write_floor(path, floor_record(rows, 2))


def advance(path, independently_observed_rows):
    """Sequential bounded 2->4 advancement by the laboratory controller.

    No candidate-supplied floor, no automatic recovery or concurrent writer
    semantics. R10's writer is a persistence primitive, not an access policy.
    """
    previous, retained = read_floor(path)
    proposed = floor_record(independently_observed_rows, 4)
    if proposed == previous:
        return "SAME_CHECKPOINT_NOT_FRESHNESS_PROOF"
    if previous["seq"] != 2:
        raise ValueError("no forward transition in this bounded lab")
    report = compare_bytes(ledger(independently_observed_rows), retained)
    if (report.aggregate_verdict != "CONDITIONAL_CORRESPONDENCE"
            or report.known_floor_relation.status != "MATCH"
            or any(new["parent"] != old["checkpoint"]
                   for new, old in zip(proposed["anchors"], previous["anchors"]))):
        raise ValueError("prefix or predecessor mismatch")
    r10._write_floor(path, proposed)
    return "ADVANCED_LAB_FLOOR_ONLY"


def assess(raw, floor_path):
    try:
        floor, retained = read_floor(floor_path)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        return "HOLD_FLOOR_MISSING_OR_INVALID"
    report = compare_bytes(raw, retained)
    if report.aggregate_verdict == "DEFINITE_DISCREPANCY":
        return "HOLD_RETAINED_HISTORY_DISCREPANCY"
    if (report.aggregate_verdict != "CONDITIONAL_CORRESPONDENCE"
            or report.known_floor_relation.status != "MATCH"):
        return "HOLD_INCONCLUSIVE"
    if hashlib.sha256(raw).hexdigest() != floor["prefix_sha256"]:
        return "HOLD_UNOBSERVED_EXTENSION"
    return "MATCH_RETAINED_LAB_CHECKPOINT_ONLY"


def history():
    world, observation = sample("aba")
    return observed_rows(world, observation)


def test_publisher_restore_does_not_rewind_retained_floor(tmp_path):
    rows = history()
    publisher = tmp_path / "publisher.jsonl"
    floor = tmp_path / "witness" / "floor.json"
    provision(floor, rows)
    publisher.write_bytes(ledger(rows[:2]))
    saved = publisher.read_bytes()
    assert assess(saved, floor) == "MATCH_RETAINED_LAB_CHECKPOINT_ONLY"
    assert advance(floor, rows) == "ADVANCED_LAB_FLOOR_ONLY"
    publisher.write_bytes(ledger(rows))
    assert assess(publisher.read_bytes(), floor) == "MATCH_RETAINED_LAB_CHECKPOINT_ONLY"
    retained = floor.read_bytes()
    publisher.write_bytes(saved)
    assert assess(publisher.read_bytes(), floor) == "HOLD_RETAINED_HISTORY_DISCREPANCY"
    assert floor.read_bytes() == retained
    assert read_floor(floor)[0]["seq"] == 4


def test_unobserved_extension_is_not_freshness(tmp_path):
    rows = history()
    floor = tmp_path / "floor.json"
    provision(floor, rows)
    assert assess(ledger(rows), floor) == "HOLD_UNOBSERVED_EXTENSION"
    assert read_floor(floor)[0]["seq"] == 2


def test_advance_idempotency_and_same_sequence_fork(tmp_path):
    rows = history()
    floor = tmp_path / "floor.json"
    provision(floor, rows)
    advance(floor, rows)
    old = floor.read_bytes()
    assert advance(floor, rows) == "SAME_CHECKPOINT_NOT_FRESHNESS_PROOF"
    w, o = sample("stable")
    fork = observed_rows(w, o)
    with pytest.raises(ValueError, match="no forward transition"):
        advance(floor, fork)
    assert assess(ledger(fork), floor) == "HOLD_RETAINED_HISTORY_DISCREPANCY"
    assert floor.read_bytes() == old


def test_bad_predecessor_cannot_advance(tmp_path):
    rows = history()
    floor = tmp_path / "floor.json"
    provision(floor, rows)
    old = floor.read_bytes()
    w, o = sample("visible_pr")
    other = observed_rows(w, o)
    with pytest.raises(ValueError, match="prefix or predecessor"):
        advance(floor, other)
    assert floor.read_bytes() == old


@pytest.mark.parametrize("mutation", ["delete", "truncate", "wrong_head", "wrong_scope",
                                     "wrong_seq", "wrong_parent"])
def test_missing_or_inconsistent_floor_fails_closed(tmp_path, mutation):
    rows = history()
    floor = tmp_path / "floor.json"
    provision(floor, rows)
    advance(floor, rows)
    data, _ = read_floor(floor)
    if mutation == "delete":
        floor.unlink()
    elif mutation == "truncate":
        floor.write_bytes(b"{")
    else:
        if mutation == "wrong_head":
            data["head"] = "0" * 64
        elif mutation == "wrong_scope":
            data["scope"] = {**SCOPE, "epoch": "WRONG"}
        elif mutation == "wrong_seq":
            data["seq"] = 2
        elif mutation == "wrong_parent":
            data["anchors"][0]["parent"] = data["anchors"][1]["parent"]
        r10._write_floor(floor, data)
    assert assess(ledger(rows), floor) == "HOLD_FLOOR_MISSING_OR_INVALID"


def test_common_admin_joint_restore_remains_residual(tmp_path):
    rows = history()
    floor = tmp_path / "floor.json"
    provision(floor, rows)
    saved = floor.read_bytes()
    advance(floor, rows)
    assert assess(ledger(rows[:2]), floor) == "HOLD_RETAINED_HISTORY_DISCREPANCY"
    floor.write_bytes(saved)  # common administrator resets the retained state
    assert assess(ledger(rows[:2]), floor) == "MATCH_RETAINED_LAB_CHECKPOINT_ONLY"


LINUX_ROOT = sys.platform.startswith("linux") and getattr(os, "geteuid", lambda: -1)() == 0


@pytest.mark.skipif(not LINUX_ROOT, reason="requires disposable Linux root supervisor")
def test_linux_publisher_uid_cannot_restore_witness_floor():
    """Actual UID denial with positive writes by both separate principals.

    Root supervises the synthetic lab. Common root remains capable of reset.
    No claim of a real remote custodian, service/IPC or independent admin.
    """
    rows = history()
    old, new = floor_record(rows, 2), floor_record(rows, 4)
    publisher_uid, witness_uid = 65534, 65533
    with tempfile.TemporaryDirectory(prefix="r22-7-", dir="/tmp") as directory:
        root = Path(directory)
        root.chmod(0o755)
        shutil.copyfile(r10.__file__, root / "monitor.py")
        (root / "monitor.py").chmod(0o444)
        pub, wit = root / "publisher", root / "witness"
        for path, uid in ((pub, publisher_uid), (wit, witness_uid)):
            path.mkdir(mode=0o700)
            os.chown(path, uid, uid)
        floor = wit / "floor.json"
        candidate = pub / "candidate.jsonl"

        def child(uid, code, *args):
            return subprocess.run(
                [sys.executable, "-I", "-B", "-c", code, *map(str, args)],
                cwd=root, user=uid, group=uid, extra_groups=[],
                env={"PATH": "/usr/bin:/bin", "HOME": str(root)},
                capture_output=True, text=True, timeout=12, check=True,
            ).stdout.strip()

        persist = (
            "import json,sys; from pathlib import Path; "
            "sys.path.insert(0,sys.argv[1]); from monitor import _write_floor; "
            "_write_floor(Path(sys.argv[2]),json.loads(sys.argv[3])); "
            "print('WITNESS_WRITE_OK')"
        )
        publish = (
            "import sys; from pathlib import Path; "
            "Path(sys.argv[1]).write_bytes(bytes.fromhex(sys.argv[2])); "
            "print('PUBLISHER_WRITE_OK')"
        )
        assert child(witness_uid, persist, root, floor, json.dumps(old)) == "WITNESS_WRITE_OK"
        assert child(publisher_uid, publish, candidate, ledger(rows[:2]).hex()) == "PUBLISHER_WRITE_OK"
        assert assess(candidate.read_bytes(), floor) == "MATCH_RETAINED_LAB_CHECKPOINT_ONLY"
        assert child(witness_uid, persist, root, floor, json.dumps(new)) == "WITNESS_WRITE_OK"
        assert child(publisher_uid, publish, candidate, ledger(rows).hex()) == "PUBLISHER_WRITE_OK"
        assert assess(candidate.read_bytes(), floor) == "MATCH_RETAINED_LAB_CHECKPOINT_ONLY"
        protected = floor.read_bytes()
        assert child(publisher_uid, publish, candidate, ledger(rows[:2]).hex()) == "PUBLISHER_WRITE_OK"

        attacks = """import os, sys
from pathlib import Path
f, p = Path(sys.argv[1]), Path(sys.argv[2])
replacement = bytes.fromhex(sys.argv[3])
staged = p / 'old-floor.json'
staged.write_bytes(replacement)
def attempt(fn):
    try:
        fn()
    except PermissionError:
        return 'DENIED'
    return 'UNEXPECTED_SUCCESS'
for fn in (
    lambda: f.read_bytes(),
    lambda: f.write_bytes(replacement),
    lambda: os.replace(staged, f),
    lambda: f.unlink(),
    lambda: f.chmod(0o666),
    lambda: f.parent.rename(p / 'stolen-witness'),
):
    print(attempt(fn))
"""
        assert child(publisher_uid, attacks, floor, pub,
                     (r10.canonical(old) + b"\n").hex()).splitlines() == ["DENIED"] * 6
        assert floor.read_bytes() == protected
        assert floor.stat().st_uid == witness_uid
        assert read_floor(floor)[0]["seq"] == 4
        assert assess(candidate.read_bytes(), floor) == "HOLD_RETAINED_HISTORY_DISCREPANCY"

        # Explicit common-root reset: actual residual, never anti-rollback PASS.
        floor.write_bytes(r10.canonical(old) + b"\n")
        assert assess(candidate.read_bytes(), floor) == "MATCH_RETAINED_LAB_CHECKPOINT_ONLY"
