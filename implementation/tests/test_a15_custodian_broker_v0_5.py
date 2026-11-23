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
    script = ("import sys, json; sys.path.insert(0,sys.argv[1]);"
              "import a15_custodian_broker_v0_5 as m;"
              "s=m.Journal(sys.argv[2]);s.consume(json.loads(sys.argv[3]));"
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

    def journal(self):
        opened=broker.Journal(self.state)
        self.addCleanup(opened.conn.close)  # Windows holds SQLite files until explicit close
        return opened

    def test_frozen_policy_recalculation_fails_closed_on_forged_gate_claim(self):
        s=self.journal()
        req=request(changes={"preference":"DECLINE"},claim="ACCEPT")
        value=s.consume(req)
        self.assertEqual((value["status"],value["policy_decision"],value["reason_code"]),
                         ("EVIDENCE_CONFLICT_GATE_CLAIM","DECLINE","ROLE_DECLINED"))
        self.assertFalse(value["execution_authorized"])
        self.assertFalse(value["origin_attested"])
        self.assertEqual(s.verify()[0],1)

    def test_caller_origin_is_not_authenticated_even_for_policy_accept(self):
        s=self.journal()
        r=s.consume(request())
        self.assertEqual(r["status"],"INERT_RECORDED_UNATTESTED_ORIGIN")
        self.assertEqual(r["policy_decision"],"ACCEPT")
        self.assertFalse(r["execution_authorized"])
        self.assertFalse(r["origin_attested"])
        self.assertEqual(r["provider_receipt"],"UNKNOWN")
        self.assertEqual(r["independent_custody"],"NOT_ESTABLISHED")

    def test_idempotent_retry_after_new_journal_object_and_id_collision(self):
        first_req=request()
        a=self.journal()
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
        a=self.journal()
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
        a=self.journal()
        a.consume(request())
        a.conn.execute("UPDATE events SET hash=? WHERE seq=1", ("0"*64,))
        a.conn.close()
        with self.assertRaises(ValueError):
            self.journal()

    def test_truncated_database_fails_closed(self):
        a=self.journal()
        a.consume(request())
        a.conn.close()
        with open(self.state/"custodian.sqlite3","wb") as f:
            f.write(b"INTENTIONALLY_BROKEN_DATABASE")
        with self.assertRaises((sqlite3.DatabaseError,ValueError)):
            self.journal()

    def test_host_admin_valid_prefix_rollback_remains_undetectable_RED(self):
        a=self.journal()
        a.consume(request(attempt="ATT_V05_01"))
        a.conn.close()
        old=Path(self.tmp.name)/"old.sqlite3"
        shutil.copyfile(self.state/"custodian.sqlite3",old)
        b=self.journal()
        b.consume(request(attempt="ATT_V05_02"))
        b.conn.close()
        shutil.copyfile(old,self.state/"custodian.sqlite3")
        c=self.journal()
        self.assertEqual(c.verify()[0],1)  # a self-controlled floor CANNOT detect valid rollback
        ref=c.consume(request(attempt="ATT_V05_02"))
        self.assertFalse(ref["replayed"])
        self.assertEqual(ref["seq"],2)

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
