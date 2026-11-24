#!/usr/bin/env python3
"""A15 v0.5 deterministic synthetic broker-core tests (NOT OS isolation attestation)."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "research" / "a15_custodian_broker_v0_5.py"
spec = importlib.util.spec_from_file_location("a15_v05", SRC)
broker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(broker)

CHOICE = {"actor":"ARIO", "role":"RESEARCH_DIALOGUE", "origin":"CURRENT",
          "explicit_renewal":False, "risk":"LOW", "authorization":"ALLOWED",
          "usefulness":"USEFUL", "evidence":"SUFFICIENT", "preference":"ACCEPT",
          "duration":"BOUNDED"}
def request(run="RUN_V05_RESEARCH", attempt="ATT_V05_RESEARCH", changes=None, claim="ACCEPT"):
    choice=dict(CHOICE)
    choice.update(changes or {})
    return {"v":1,"run_id":run,"attempt_id":attempt,
            "choice_json":broker.encode(choice),"claimed_status":claim}

def injected_crash(state, req, phase):
    # CUST-08-R3: the crash harness starts with EXPLICIT provisioning; every
    # later open in these tests is recovery mode and must match the floor.
    script = ("import sys, json; sys.path.insert(0,sys.argv[1]);"
              "import a15_custodian_broker_v0_5 as m;"
              "s=m.Journal(sys.argv[2],provision=True);s.consume(json.loads(sys.argv[3]));"
              "sys.exit(0)")
    env=dict(os.environ,
             A15_V05_SYNTHETIC_CRASH_POINT=phase,
             A15_V05_SYNTHETIC_CRASH_REQUEST_ID=req["run_id"]+"|"+req["attempt_id"])
    return subprocess.run([sys.executable,"-c",script,str(SRC.parent),str(state),
                           broker.encode(req)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          timeout=15).returncode

class BrokerCore(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="a15-v05-")
        self.addCleanup(self.tmp.cleanup)
        self.state=Path(self.tmp.name)/"state"

    def journal(self, provision=False):
        opened=broker.Journal(self.state, provision=provision)
        self.addCleanup(opened.conn.close)  # Windows holds SQLite files until explicit close
        return opened

    def test_frozen_policy_recalculation_fails_closed_on_forged_gate_claim(self):
        s=self.journal(provision=True)
        req=request(changes={"preference":"DECLINE"},claim="ACCEPT")
        value=s.consume(req)
        self.assertEqual((value["status"],value["policy_decision"],value["reason_code"]),
                         ("EVIDENCE_CONFLICT_GATE_CLAIM","DECLINE","ROLE_DECLINED"))
        self.assertFalse(value["execution_authorized"])
        self.assertFalse(value["origin_attested"])
        self.assertEqual(s.verify()[0],1)

    def test_caller_origin_is_not_authenticated_even_for_policy_accept(self):
        s=self.journal(provision=True)
        r=s.consume(request())
        self.assertEqual(r["status"],"INERT_RECORDED_UNATTESTED_ORIGIN")
        self.assertEqual(r["policy_decision"],"ACCEPT")
        self.assertFalse(r["execution_authorized"])
        self.assertFalse(r["origin_attested"])
        self.assertEqual(r["provider_receipt"],"UNKNOWN")
        self.assertEqual(r["independent_custody"],"NOT_ESTABLISHED")

    def test_idempotent_retry_after_new_journal_object_and_id_collision(self):
        first_req=request()
        a=self.journal(provision=True)
        one=a.consume(first_req)
        a.conn.close()
        b=self.journal()
        replay=b.consume(first_req)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["status"],"REPLAY_DURABLE_LOCAL_RECEIPT_ONLY")
        self.assertEqual((one["seq"],one["head_hash"]), (replay["seq"],replay["head_hash"]))
        conflict=b.consume(request(changes={"preference":"DECLINE"}))
        self.assertEqual(conflict["status"],"EVIDENCE_CONFLICT_ID_REUSED")
        # A different caller-reported verdict is also a changed request, even
        # when the policy input bytes stay identical.
        changed_claim=b.consume(request(claim="DECLINE"))
        self.assertEqual(changed_claim["status"],"EVIDENCE_CONFLICT_ID_REUSED")
        self.assertEqual(b.verify()[0],1)

    def test_commit_chain_persists_across_restart(self):
        a=self.journal(provision=True)
        one=a.consume(request(attempt="ATT_V05_01"))
        two=a.consume(request(attempt="ATT_V05_02",changes={"preference":"UNKNOWN"},claim="UNKNOWN"))
        self.assertEqual((one["seq"],two["seq"]), (1,2))
        self.assertNotEqual(one["head_hash"],two["head_hash"])
        a.conn.close()
        b=self.journal()
        self.assertEqual(b.verify(),(2,two["head_hash"]))

    def test_before_commit_crash_rolls_back_inflight_transaction(self):
        req=request(attempt="ATT_V05_BEFORE")
        self.assertEqual(injected_crash(self.state,req,"BEFORE_COMMIT"),77)
        s=self.journal()
        self.assertEqual(s.verify()[0],0)
        retried=s.consume(req)
        self.assertEqual(retried["seq"],1)
        self.assertFalse(retried["replayed"])

    def test_after_commit_lost_response_returns_durable_receipt_on_retry(self):
        req=request(attempt="ATT_V05_AFTER")
        self.assertEqual(injected_crash(self.state,req,"AFTER_COMMIT_BEFORE_REPLY"),78)
        s=self.journal()
        self.assertEqual(s.verify()[0],1)
        retried=s.consume(req)
        self.assertEqual(retried["seq"],1)
        self.assertEqual(retried["status"],"REPLAY_DURABLE_LOCAL_RECEIPT_ONLY")
        self.assertTrue(retried["replayed"])

    def test_corrupted_hash_chain_fails_closed_on_reopen(self):
        a=self.journal(provision=True)
        a.consume(request())
        a.conn.execute("UPDATE events SET hash=? WHERE seq=1", ("0"*64,))
        a.conn.close()
        with self.assertRaises(ValueError):
            self.journal()

    def test_truncated_database_fails_closed(self):
        a=self.journal(provision=True)
        a.consume(request())
        a.conn.close()
        with open(self.state/"custodian.sqlite3","wb") as f:
            f.write(b"INTENTIONALLY_BROKEN_DATABASE")
        with self.assertRaises((sqlite3.DatabaseError,ValueError)):
            self.journal()

    def test_r3_db_only_prefix_rollback_fails_closed_with_retained_floor(self):
        # Grok residual 3: restoring an earlier well-formed prefix is now
        # DETECTED whenever the locally retained expected floor survives.
        a=self.journal(provision=True)
        a.consume(request(attempt="ATT_V05_R3_01"))
        a.conn.close()
        old=Path(self.tmp.name)/"old.sqlite3"
        shutil.copyfile(self.state/"custodian.sqlite3",old)
        b=self.journal()
        b.consume(request(attempt="ATT_V05_R3_02"))
        b.conn.close()
        shutil.copyfile(old,self.state/"custodian.sqlite3")
        with self.assertRaises(ValueError):
            c=self.journal()  # ledger head fell behind the retained floor
            c.conn.close()
        self.assertEqual((self.state/"custodian.sqlite3").read_bytes(),old.read_bytes())  # untouched; no re-recording

    def test_r3_wellformed_empty_replacement_fails_closed(self):
        # Grok residual 2: a structurally valid zero-row events DB is never
        # adopted as the intended original.
        a=self.journal(provision=True)
        for attempt in ("ATT_V05_R3_A","ATT_V05_R3_B","ATT_V05_R3_C"):
            a.consume(request(attempt=attempt))
        a.conn.close()
        (self.state/"custodian.sqlite3").unlink()
        conn=sqlite3.connect(str(self.state/"custodian.sqlite3"))
        conn.execute("""CREATE TABLE events (
          seq INTEGER PRIMARY KEY, request_key TEXT NOT NULL UNIQUE,
          input_hash TEXT NOT NULL, decision TEXT NOT NULL, reason TEXT NOT NULL,
          disposition TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL)""")
        conn.commit(); conn.close()
        with self.assertRaises(ValueError):
            c=self.journal()  # zero rows behind the retained floor: fail closed
            c.conn.close()

    def test_r3_missing_ledger_fails_closed_and_provision_refused_while_floor_kept(self):
        # Grok residual 1: deletion is not an implicit first boot, and the
        # retained floor forbids a silent new chain even with provision=True.
        a=self.journal(provision=True)
        a.consume(request(attempt="ATT_V05_R3_UNLINK"))
        a.conn.close()
        (self.state/"custodian.sqlite3").unlink()
        with self.assertRaises(ValueError):
            c=self.journal()  # normal reopen never bootstraps a missing ledger
            c.conn.close()
        with self.assertRaises(ValueError):
            j=broker.Journal(self.state, provision=True)
            j.conn.close()

    def test_r3_missing_or_ambiguous_floor_holds_instead_of_new_chain(self):
        a=self.journal(provision=True)
        a.consume(request(attempt="ATT_V05_R3_F1"))
        a.conn.close()
        (self.state/"custodian.floor.json").unlink()
        for payload in (b"", b"{not json", b'{"format":"a15-custodian-floor-v1","ledger":"custodian.sqlite3","expected_seq":0,"expected_hash":"GENESIS","extra":1}'):
            (self.state/"custodian.floor.json").write_bytes(payload)
            with self.assertRaises(ValueError):
                c=self.journal()  # HOLD: no implicit adoption, never a new chain
                c.conn.close()

    def test_r3_stale_floor_after_commit_crash_recovers_to_durable_head(self):
        # Positive crash-recovery control: durable commit, lost floor write.
        # Recovery reconciles forward to the verified head; history is never
        # silently reset here.
        a=self.journal(provision=True)
        a.consume(request(attempt="ATT_V05_R3_S1"))
        a.conn.close()
        stale=(self.state/"custodian.floor.json").read_bytes()
        b=self.journal()
        b.consume(request(attempt="ATT_V05_R3_S2"))
        b.conn.close()
        (self.state/"custodian.floor.json").write_bytes(stale)
        c=self.journal()
        self.assertEqual(c.verify()[0],2)
        floor=json.loads((self.state/"custodian.floor.json").read_text())
        self.assertEqual((floor["expected_seq"],floor["expected_hash"]),(2,c.verify()[1]))

    def test_r4_failed_floor_write_holds_fresh_replay_and_new_requests(self):
        a=self.journal(provision=True)
        first=a.consume(request(attempt="ATT_R4_FIRST"))
        self.assertEqual(first["local_floor_confirmation"],"READBACK_MATCH")
        req=request(attempt="ATT_R4_PENDING")
        with patch.object(a,"_write_floor",side_effect=OSError("synthetic floor write failure")):
            held=a.consume(req)
            self.assertEqual(held["status"],"HOLD_LOCAL_FLOOR_UNCONFIRMED")
            self.assertEqual(held["local_commit"],"RECORDED")
            self.assertEqual(held["pending_event_seq"],2)
            self.assertNotIn("seq",held)
            self.assertNotIn("head_hash",held)
            self.assertFalse(held["execution_authorized"])
            self.assertFalse(held["origin_attested"])
            self.assertEqual(a.verify()[0],2)
            floor=json.loads(a.floor_path.read_text())
            self.assertEqual(floor["expected_seq"],1)
            retry=a.consume(req)
            self.assertEqual(retry["status"],"HOLD_LOCAL_FLOOR_UNCONFIRMED")
            self.assertEqual(retry["pending_event_hash"],held["pending_event_hash"])
            blocked=a.consume(request(attempt="ATT_R4_OTHER"))
            self.assertEqual(blocked["status"],"HOLD_LOCAL_FLOOR_UNCONFIRMED")
            self.assertEqual(blocked["local_commit"],"NOT_ATTEMPTED")
            self.assertEqual(a.verify()[0],2)
        replay=a.consume(req)
        self.assertEqual(replay["status"],"REPLAY_DURABLE_LOCAL_RECEIPT_ONLY")
        self.assertEqual(replay["event_hash"],held["pending_event_hash"])
        self.assertEqual(replay["local_floor_confirmation"],"READBACK_MATCH")
        self.assertEqual(a.verify()[0],2)
        self.assertEqual(json.loads(a.floor_path.read_text())["expected_seq"],2)

    def test_r4_uncertain_floor_replace_holds_until_confirmed(self):
        a=self.journal(provision=True)
        req=request(attempt="ATT_R4_REPLACE")
        write=a._write_floor
        def replaced_then_failed(*args):
            write(*args)
            raise OSError("synthetic failure after replacement")
        with patch.object(a,"_write_floor",side_effect=replaced_then_failed):
            held=a.consume(req)
        self.assertEqual(held["status"],"HOLD_LOCAL_FLOOR_UNCONFIRMED")
        self.assertEqual(a.verify()[0],1)
        self.assertEqual(json.loads(a.floor_path.read_text())["expected_seq"],1)
        reply=a.consume(req)
        self.assertTrue(reply["replayed"])
        self.assertEqual(reply["event_hash"],held["pending_event_hash"])
        self.assertEqual(reply["local_floor_confirmation"],"READBACK_MATCH")

    def test_r4_cooperative_connections_do_not_regress_floor(self):
        a=self.journal(provision=True)
        b=self.journal()
        confirm=a._confirm_committed_receipt
        later=[]
        def interleave(seq, event_hash):
            # Deterministic schedule: a committed; b advances the same DB;
            # then a confirms. No OS/process isolation claim.
            later.append(b.consume(request(attempt="ATT_R4_LATER")))
            return confirm(seq,event_hash)
        with patch.object(a,"_confirm_committed_receipt",side_effect=interleave):
            first=a.consume(request(attempt="ATT_R4_EARLIER"))
        self.assertEqual(first["seq"],1)
        self.assertEqual(first["chain_head_seq"],2)
        self.assertEqual(first["chain_head_hash"],later[0]["event_hash"])
        self.assertEqual(first["local_floor_confirmation"],"READBACK_MATCH")
        self.assertEqual(json.loads(a.floor_path.read_text())["expected_seq"],2)
        self.assertEqual(a.verify()[0],2)

    def test_r4_failed_initial_floor_never_auto_bootstraps(self):
        with patch.object(broker.Journal,"_write_floor",side_effect=OSError("synthetic provisioning failure")):
            with self.assertRaises(OSError):
                self.journal(provision=True)
        with self.assertRaises((ValueError,sqlite3.Error)):
            self.journal()
        with self.assertRaises(ValueError):
            self.journal(provision=True)

    def test_r3_joint_rollback_of_ledger_and_floor_remains_undetectable_RED(self):
        # Preserved RED (deliberately unsolved): the SAME administrator rolling
        # back the ledger AND the locally retained floor together still erases
        # the prior DECLINE while appearing healthy. A local floor, flag or CLI
        # argument is NOT an authenticated independent custody witness; closing
        # this requires a separately administered external (seq,hash) authority
        # (a separate control boundary; acceptance gate #2 stays HOLD).
        a=self.journal(provision=True)
        a.consume(request(attempt="ATT_V05_01"))
        a.conn.close()
        old_db=Path(self.tmp.name)/"old.sqlite3"
        old_floor=Path(self.tmp.name)/"old.floor.json"
        shutil.copyfile(self.state/"custodian.sqlite3",old_db)
        shutil.copyfile(self.state/"custodian.floor.json",old_floor)
        b=self.journal()
        b.consume(request(attempt="ATT_V05_02"))
        b.conn.close()
        shutil.copyfile(old_db,self.state/"custodian.sqlite3")
        shutil.copyfile(old_floor,self.state/"custodian.floor.json")
        c=self.journal()
        self.assertEqual(c.verify()[0],1)  # joint same-admin rollback CANNOT be detected locally
        ref=c.consume(request(attempt="ATT_V05_02"))
        self.assertFalse(ref["replayed"])
        self.assertEqual(ref["seq"],2)

    def test_gred1_zero_and_one_byte_ledger_fail_closed_no_rebirth(self):
        a=self.journal(provision=True)
        a.consume(request(attempt="ATT_V05_G1A"))
        a.conn.close()
        kept=(self.state/"custodian.sqlite3").read_bytes()
        for size in (0,1):
            with open(self.state/"custodian.sqlite3","wb") as f:
                f.write(kept[:size])
            with self.assertRaises(ValueError):
                j=self.journal()
                j.conn.close()
        # The truncated ledger never re-entered service, so the consumed ID
        # was not silently re-recorded on top of a fresh GENESIS row.

    def test_gred1_first_boot_provisioning_stays_allowed(self):
        # CUST-08-R3: first boot is still possible, but ONLY explicit (never
        # implicit during normal reopen, and refused over any existing file).
        fresh=Path(self.tmp.name)/"fresh"
        with self.assertRaises(ValueError):
            j=broker.Journal(fresh)  # reopen of a missing ledger is disabled
            j.conn.close()
        j=broker.Journal(fresh, provision=True)
        self.addCleanup(j.conn.close)
        r=j.consume(request(attempt="ATT_V05_G1_FRESH"))
        self.assertEqual(r["seq"],1)
        self.assertFalse(r["replayed"])

    def test_gred2_replay_separates_event_from_chain_head(self):
        a=self.journal(provision=True)
        r1=a.consume(request(attempt="ATT_V05_G2_1"))
        r2=a.consume(request(attempt="ATT_V05_G2_2",changes={"preference":"UNKNOWN"},claim="UNKNOWN"))
        self.assertEqual((r1["chain_head_seq"],r1["chain_head_hash"]),(1,r1["head_hash"]))
        a.conn.close()
        b=self.journal()
        rep=b.consume(request(attempt="ATT_V05_G2_1"))
        self.assertTrue(rep["replayed"])
        self.assertEqual(rep["seq"],1)
        self.assertEqual(rep["event_hash"],r1["head_hash"])
        self.assertEqual(rep["head_hash"],r1["head_hash"])
        self.assertEqual((rep["chain_head_seq"],rep["chain_head_hash"]),(2,r2["head_hash"]))
        self.assertNotEqual(rep["chain_head_hash"],rep["event_hash"])
        b.conn.close()

    def test_rejects_duplicate_keys_and_unbounded_wire(self):
        req=request()
        self.assertIsNotNone(broker.validate_request(broker.encode(req).encode()))
        self.assertIsNone(broker.validate_request(b'{"v":1,"v":1}'))
        self.assertIsNone(broker.validate_request(b"x"*4097))
        bad=copy.deepcopy(req);bad["implied_authority"]="AUTHORIZED"
        self.assertIsNone(broker.validate_request(broker.encode(bad).encode()))
        bad=copy.deepcopy(req);bad["claimed_status"]="TRUST_ACTIVATED"
        self.assertIsNone(broker.validate_request(broker.encode(bad).encode()))

    def test_policy_legacy_mismatch_denied_unknown_and_renewal(self):
        cases=[
          ({"actor":"OTHER"},"UNKNOWN","ACTOR_NOT_ARIO"),
          ({"risk":"HIGH","authorization":"UNKNOWN"},"DECLINE","HIGH_RISK_NOT_AUTHORIZED"),
          ({"risk":"UNKNOWN"},"UNKNOWN","RISK_UNRESOLVED"),
          ({"duration":"UNBOUNDED"},"DECLINE","NO_PERPETUAL_COMMITMENT"),
          ({"origin":"PREDECESSOR"},"DECLINE","NO_AUTOMATIC_INHERITANCE"),
          ({"origin":"PREDECESSOR","explicit_renewal":True},"ACCEPT","BOUNDED_NEW_ELECTION_RESEARCH_ONLY"),
          ({"usefulness":"FUTILE"},"DECLINE","NONPRODUCTIVE_CONTINUATION"),
          ({"evidence":"CONFLICT"},"UNKNOWN","EVIDENCE_CONFLICT"),
          ({"authorization":"DENIED"},"DECLINE","AUTHORIZATION_DENIED"),
          ({"authorization":"UNKNOWN"},"UNKNOWN","INSUFFICIENT_EVIDENCE"),
          ({"preference":"DECLINE"},"DECLINE","ROLE_DECLINED"),
          ({"preference":"UNKNOWN"},"UNKNOWN","STANCE_UNRESOLVED")
        ]
        for changes,status,reason in cases:
            with self.subTest(changes=changes):
                c=dict(CHOICE);c.update(changes)
                self.assertEqual(broker.decide(broker.encode(c)),(status,reason))


    def test_cross_language_parity_with_frozen_node_policy(self):
        node=shutil.which("node")
        if not node:
            self.skipTest("Node is required to compare with the frozen A15 JavaScript policy")
        samples=[broker.encode(CHOICE)]
        samples.append(broker.encode(dict(reversed(list(CHOICE.items())))))
        for changes in (
            {"actor":"OTHER"}, {"role":"REVIEW"},
            {"risk":"HIGH","authorization":"UNKNOWN"}, {"risk":"UNKNOWN"},
            {"duration":"UNBOUNDED"}, {"origin":"PREDECESSOR"},
            {"origin":"PREDECESSOR","explicit_renewal":True},
            {"usefulness":"FUTILE"}, {"evidence":"CONFLICT"},
            {"authorization":"DENIED"}, {"authorization":"UNKNOWN"},
            {"preference":"DECLINE"}, {"preference":"UNKNOWN"},
            {"duration":"UNKNOWN"}, {"explicit_renewal":True}):
            case=dict(CHOICE);case.update(changes)
            samples.append(broker.encode(case))
        samples.extend([
            broker.encode({**CHOICE,"actor":123}),
            broker.encode({**CHOICE,"authorization":"AWESOME"}),
            broker.encode({**CHOICE,"authorization":None}),
            broker.encode({**CHOICE,"extra":"FORGED"}),
            broker.encode({k:v for k,v in CHOICE.items() if k!="risk"}),
            '{"actor":"ARIO","actor":"OTHER"}',
            json.dumps(CHOICE,indent=2),
            "NOT-JSON"
        ])
        source=str(SRC.parent/"a15_procedural_choice_v0_1.js")
        script=('const d=require(process.argv[1]).decide;'
                'const xs=JSON.parse(require("node:fs").readFileSync(0,"utf8"));'
                'process.stdout.write(JSON.stringify(xs.map(s=>{const x=d(s);return [x.status,x.reason_code];})));')
        completed=subprocess.run([node,"-e",script,source],
                                 input=json.dumps(samples),text=True,encoding="utf-8",
                                 capture_output=True,timeout=10,check=True)
        expected=json.loads(completed.stdout)
        actual=[list(broker.decide(sample)) for sample in samples]
        self.assertEqual(actual,expected)

if __name__=="__main__":
    unittest.main(verbosity=2)
