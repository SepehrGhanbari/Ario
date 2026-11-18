#!/usr/bin/env python3
"""W29 Windows/Linux research falsifiers with ORIGINAL published W22 signed notes."""
from __future__ import annotations
import base64
import json
import multiprocessing
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from w29_dual_observer_rollback_lab import observe, readback, compare, worker

HERE=Path(__file__).resolve().parent
FIX=json.loads((HERE/"W22_PUBLIC_SYNTHETIC_SIGNED_NOTES_2026-11-17.json").read_text("utf-8"))
W20=json.loads((HERE/"W20_SYNTHETIC_LOG_CHECKPOINTS_AND_PROOFS_2026-11-17.json").read_text("utf-8"))
KEY=FIX["public_vkey_for_synthetic_demo_only"]
OLD=FIX["previous_checkpoint"].encode()
NEW=FIX["current_checkpoint"].encode()
FORK=FIX["same_signer_fork_checkpoint"].encode()
PROOF=W20["consistency_proof"]


class W29(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="w29_")
        self.addCleanup(self.tmp.cleanup)
        self.a=str(Path(self.tmp.name)/"observer-A.sqlite3")
        self.b=str(Path(self.tmp.name)/"observer-B.sqlite3")

    def write(self,path,old_size=0,note=OLD,proof=None,crash=None):
        return observe(path,old_size=old_size,signed_note=note,
                       pinned_log_vkey=KEY,proof=proof,crash=crash)
    def initial(self):
        self.assertEqual(self.write(self.a)["status"],"COMMITTED_UNSIGNED_OBSERVATION")
        self.assertEqual(self.write(self.b)["status"],"COMMITTED_UNSIGNED_OBSERVATION")
    def grow(self,path):
        return self.write(path,3,NEW,PROOF)
    def advanced(self):
        self.initial()
        self.assertEqual(self.grow(self.a)["status"],"COMMITTED_UNSIGNED_OBSERVATION")
        self.assertEqual(self.grow(self.b)["status"],"COMMITTED_UNSIGNED_OBSERVATION")
    def inspect(self,**kw):
        return compare(readback(self.a),readback(self.b),pinned_log_vkey=KEY,**kw)
    def _crash(self,path,stage,old_size=3,note=NEW,proof=PROOF):
        code=("import json,sys;from w29_dual_observer_rollback_lab import observe;"
              "a=json.loads(sys.stdin.read());"
              "observe(a['p'],old_size=a['old'],signed_note=a['note'].encode(),"
              "pinned_log_vkey=a['key'],proof=a['proof'],crash=a['stage'])")
        return subprocess.run([sys.executable,"-B","-c",code],cwd=str(HERE),
                              input=json.dumps({"p":path,"old":old_size,"note":note.decode(),
                                                "key":KEY,"proof":proof,"stage":stage}),
                              capture_output=True,text=True,timeout=20)

    def test_01_both_observe_initial_size3(self):
        self.initial()
        r=self.inspect()
        self.assertEqual(r["reason"],"TWO_VIEWS_AGREE_WITHOUT_INDEPENDENT_CUSTODY")
        self.assertEqual(r["size"],3)
    def test_02_both_grow_to8_and_preserve_unsigned_status(self):
        self.advanced()
        self.assertEqual(self.inspect()["size"],8)
        self.assertEqual(readback(self.a)["observer_channel_authentication"],"NOT_ESTABLISHED")
    def test_03_missing_observer_b_holds(self):
        self.write(self.a)
        self.assertEqual(self.inspect()["reason"],"ONE_OR_BOTH_OBSERVERS_UNAVAILABLE")
    def test_04_missing_both_holds(self):
        self.assertEqual(self.inspect()["reason"],"ONE_OR_BOTH_OBSERVERS_UNAVAILABLE")
    def test_05_one_lags_with_valid_merkle_proof(self):
        self.initial();self.grow(self.a)
        r=self.inspect(proof_small_to_large=PROOF)
        self.assertEqual(r["reason"],"ONE_OBSERVER_LAGS_BUT_CONSISTENCY_PROVEN_FOR_SUPPLIED_NOTES")
        self.assertEqual(r["sizes"],[8,3])
    def test_06_reverse_observer_lag(self):
        self.initial();self.grow(self.b)
        self.assertEqual(self.inspect(proof_small_to_large=PROOF)["sizes"],[3,8])
    def test_07_lag_without_proof_is_not_accepted(self):
        self.initial();self.grow(self.a)
        self.assertEqual(self.inspect()["reason"],"DIFFERING_VIEWS_NO_CONSISTENCY_PROOF")
    def test_08_lag_with_tampered_proof_is_not_accepted(self):
        self.initial();self.grow(self.a)
        bad=PROOF.copy();bad[0]="0"*64
        self.assertEqual(self.inspect(proof_small_to_large=bad)["reason"],"DIFFERING_VIEWS_NO_CONSISTENCY_PROOF")
    def test_09_valid_signed_fork_same_size_detected(self):
        self.write(self.a,0,NEW)
        self.write(self.b,0,FORK)
        self.assertEqual(self.inspect()["reason"],"TWO_SIGNED_SAME_SIZE_FORK")
    def test_10_fork_rejected_by_retained_ledger(self):
        self.advanced()
        self.assertEqual(self.write(self.a,8,FORK,[])["status"],"DENY")
        self.assertEqual(self.inspect()["size"],8)
    def test_11_local_rollback_one_file_visible_against_other(self):
        self.initial()
        prior=Path(self.tmp.name)/"A_old.sqlite3"
        shutil.copyfile(self.a,prior)
        self.grow(self.a);self.grow(self.b)
        shutil.copyfile(prior,self.a)
        self.assertEqual(self.inspect()["reason"],"DIFFERING_VIEWS_NO_CONSISTENCY_PROOF")
    def test_12_one_rolled_back_below_supplied_size8_floor(self):
        self.initial();backup=Path(self.tmp.name)/"a_old.sqlite3"
        shutil.copyfile(self.a,backup);self.grow(self.a);self.grow(self.b)
        shutil.copyfile(backup,self.a)
        self.assertEqual(self.inspect(floor_note=NEW)["reason"],"OBSERVER_BELOW_SUPPLIED_FLOOR")
    def test_13_coordinated_both_store_rollback_without_floor_not_detected(self):
        self.initial()
        old_a=Path(self.tmp.name)/"old_a";old_b=Path(self.tmp.name)/"old_b"
        shutil.copyfile(self.a,old_a);shutil.copyfile(self.b,old_b)
        self.grow(self.a);self.grow(self.b)
        shutil.copyfile(old_a,self.a);shutil.copyfile(old_b,self.b)
        r=self.inspect()
        self.assertEqual(r["reason"],"TWO_VIEWS_AGREE_WITHOUT_INDEPENDENT_CUSTODY")
        self.assertEqual(r["size"],3)
    def test_14_both_rollback_detected_only_against_unrestored_floor(self):
        self.initial()
        old_a=Path(self.tmp.name)/"old_a";old_b=Path(self.tmp.name)/"old_b"
        shutil.copyfile(self.a,old_a);shutil.copyfile(self.b,old_b)
        self.grow(self.a);self.grow(self.b)
        shutil.copyfile(old_a,self.a);shutil.copyfile(old_b,self.b)
        self.assertEqual(self.inspect(floor_note=NEW)["reason"],"OBSERVER_BELOW_SUPPLIED_FLOOR")
    def test_15_self_supplied_rollback_floor_is_not_authenticated(self):
        self.initial()
        r=self.inspect(floor_note=OLD)
        self.assertEqual(r["reason"],"TWO_VIEWS_AGREE_WITHOUT_INDEPENDENT_CUSTODY")
        self.assertEqual(r["externally_protected_floor"],"NOT_ESTABLISHED")
    def test_16_floor3_to_both8_without_proof_holds(self):
        self.advanced()
        self.assertEqual(self.inspect(floor_note=OLD)["reason"],"FLOOR_TO_OBSERVER_PROOF_UNVERIFIED")
    def test_17_floor3_to_both8_with_valid_proof_still_not_independent(self):
        self.advanced()
        r=self.inspect(floor_note=OLD,floor_proofs={"a":PROOF,"b":PROOF})
        self.assertEqual(r["reason"],"TWO_VIEWS_AGREE_WITHOUT_INDEPENDENT_CUSTODY")
        self.assertEqual(r["floor_evidence"],"CALLER_SUPPLIED_ONLY")
    def test_18_floor8_matches_both8_but_no_operator_authentication(self):
        self.advanced()
        r=self.inspect(floor_note=NEW)
        self.assertEqual(r["reason"],"TWO_VIEWS_AGREE_WITHOUT_INDEPENDENT_CUSTODY")
        self.assertEqual(r["observer_channel_authentication"],"NOT_ESTABLISHED")
    def test_19_floor8_conflicts_with_fork_size8(self):
        self.write(self.a,0,NEW);self.write(self.b,0,FORK)
        self.assertEqual(self.inspect(floor_note=NEW)["reason"],"OBSERVER_FORK_VS_SUPPLIED_FLOOR")
    def test_20_forged_or_invalid_floor_note_rejected(self):
        self.initial()
        altered=OLD.replace(b"\n3\n",b"\n4\n")
        self.assertEqual(self.inspect(floor_note=altered)["reason"],"INVALID_SUPPLIED_FLOOR")
    def test_21_corrupt_one_database_fails_closed(self):
        self.initial()
        Path(self.b).write_bytes(b"malformed SQLite file")
        self.assertEqual(self.inspect()["reason"],"ONE_OR_BOTH_OBSERVERS_UNAVAILABLE")
    def test_22_corrupt_retained_note_detected_on_readback(self):
        self.initial()
        c=sqlite3.connect(self.a)
        try:c.execute("UPDATE head SET note=?",(NEW,));c.commit()
        finally:c.close()
        self.assertEqual(self.inspect()["reason"],"INVALID_OR_TAMPERED_READBACK_NOTE")
    def test_23_tampered_readback_metadata_rejected(self):
        self.initial()
        a=readback(self.a);a["size"]=8
        r=compare(a,readback(self.b),pinned_log_vkey=KEY)
        self.assertEqual(r["reason"],"INVALID_OR_TAMPERED_READBACK_NOTE")
    def test_24_noncanonical_readback_note_rejected(self):
        self.initial()
        a=readback(self.a);a["note_b64"]="not/base64***"
        self.assertEqual(compare(a,readback(self.b),pinned_log_vkey=KEY)["reason"],
                         "INVALID_OR_TAMPERED_READBACK_NOTE")
    def test_25_observe_signed_note_body_corruption_denied(self):
        self.assertEqual(self.write(self.a,0,OLD.replace(b"\n3\n",b"\n4\n"))["status"],"DENY")
    def test_26_wrong_old_size_conflict(self):
        self.initial()
        self.assertEqual(self.write(self.a,0,NEW,PROOF)["status"],"CONFLICT")
    def test_27_bad_growth_proof_denied_without_mutating_head(self):
        self.initial()
        bad=PROOF.copy();bad[0]="0"*64
        self.assertEqual(self.write(self.a,3,NEW,bad)["status"],"DENY")
        self.assertEqual(readback(self.a)["size"],3)
    def test_28_same_checkpoint_idempotence(self):
        self.advanced()
        self.assertEqual(self.write(self.a,8,NEW,[])["status"],"COMMITTED_UNSIGNED_OBSERVATION")
    def test_29_crash_before_commit_ledger_retained(self):
        self.initial()
        p=self._crash(self.a,"before_commit")
        self.assertEqual(p.returncode,91,p.stderr)
        self.assertEqual(readback(self.a)["size"],3)
        self.assertEqual(self.grow(self.a)["status"],"COMMITTED_UNSIGNED_OBSERVATION")
    def test_30_crash_after_commit_lost_response_ledger_retained(self):
        self.initial()
        p=self._crash(self.a,"after_commit")
        self.assertEqual(p.returncode,92,p.stderr)
        self.assertEqual(p.stdout,"")
        self.assertEqual(readback(self.a)["size"],8)
        self.assertEqual(self.write(self.a,8,NEW,[])["status"],"COMMITTED_UNSIGNED_OBSERVATION")
    def test_31_two_separate_processes_two_files(self):
        kw={"old_size":0,"signed_note":OLD,"pinned_log_vkey":KEY,"proof":[]}
        with multiprocessing.get_context("spawn").Pool(2) as pool:
            out=pool.map(worker,[("observe",self.a,kw),("observe",self.b,kw)])
        self.assertTrue(all(x["status"]=="COMMITTED_UNSIGNED_OBSERVATION" for x in out))
        self.assertEqual(self.inspect()["size"],3)
    def test_32_parallel_same_file_requests_one_conflicts(self):
        self.initial()
        kw={"old_size":3,"signed_note":NEW,"pinned_log_vkey":KEY,"proof":PROOF}
        with multiprocessing.get_context("spawn").Pool(2) as pool:
            out=pool.map(worker,[("observe",self.a,kw)]*2)
        self.assertEqual(sorted(x["status"] for x in out),["COMMITTED_UNSIGNED_OBSERVATION","CONFLICT"])
    def test_33_synthetic_reused_observer_path_not_independence(self):
        self.write(self.a)
        snap=readback(self.a)
        r=compare(snap,snap,pinned_log_vkey=KEY)
        self.assertEqual(r["reason"],"TWO_VIEWS_AGREE_WITHOUT_INDEPENDENT_CUSTODY")
        self.assertEqual(r["independent_operator_custody"],"NOT_ESTABLISHED")
    def test_34_forged_separate_names_do_not_authenticate_readbacks(self):
        self.initial()
        snap=readback(self.a);snap2=dict(snap)
        snap["display_name"]="Keeper A";snap2["display_name"]="Keeper B"
        r=compare(snap,snap2,pinned_log_vkey=KEY)
        self.assertEqual(r["observer_channel_authentication"],"NOT_ESTABLISHED")
    def test_35_loss_of_both_observers_does_not_create_authority(self):
        r=self.inspect()
        self.assertEqual(r["authority"],"NONE")
        self.assertEqual(r["production"],"NO_GO")
    def test_36_all_outputs_never_admit_memory(self):
        self.advanced()
        for r in (readback(self.a),self.inspect(),self.inspect(floor_note=NEW)):
            self.assertFalse(r["memory_admitted"])
            self.assertEqual(r["trust_activation"],"NO_GO")
            self.assertEqual(r["cosignatures_issued"],0)
    def test_37_no_auto_inference_of_world_freshness(self):
        self.advanced()
        self.assertEqual(self.inspect(floor_note=NEW)["world_freshness"],"UNKNOWN")
    def test_38_boolean_old_size_denied(self):
        self.assertEqual(self.write(self.a,True,OLD)["status"],"DENY")
    def test_39_bad_proof_envelope_denied(self):
        self.initial()
        self.assertEqual(self.inspect(proof_small_to_large="bad")["reason"],"INVALID_PROOF_ENVELOPE")
    def test_40_worker_disallows_unknown_operation(self):
        with self.assertRaises(ValueError):worker(("sign",self.a,{}))

if __name__=="__main__":unittest.main(verbosity=2)
