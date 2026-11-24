import unittest
import copy
import json
import floor_recovery as r
from test_r22_5_replay_aba_boundary import sample
from test_r22_6_ci_witness_prefix_integration import observed_rows

class FloorRecovery(unittest.TestCase):
    def setUp(self):
        w,o=sample("aba")
        self.rows=observed_rows(w,o,events=["SYNTHETIC-A","SYNTHETIC-B"])
        self.old=r.floor_record(self.rows,2)
        self.new=r.floor_record(self.rows,4)
        self.a=r.r10.canonical(self.old)+b"\n"
        self.b=r.r10.canonical(self.new)+b"\n"
        self.la=r.ledger(self.rows[:2])
        self.lb=r.ledger(self.rows)
        first=dict(profile=r.env.PROFILE,scope="a"*48,record_count=2,previous_checksum="GENESIS",
                   floor_commitment_sha256=r.commitment(self.old),synthetic_nonce="b"*64,
                   synthetic=True,authoritative=False,historical_event_truth="UNKNOWN",
                   trust_activation="NO_GO",production="NO_GO")
        self.ea=r.env.canonical(first)
        self.pin=r.env.checksum(self.ea)
        self.eb=r.env.canonical(dict(first,record_count=4,previous_checksum=self.pin,
                                  floor_commitment_sha256=r.commitment(self.new),synthetic_nonce="c"*64))
        self.target=r.env.checksum(self.eb)
        self.raw=r.bundle(self.b,self.lb)

    def verify(self, raw, **kwargs):
        return r.verify(kwargs.get("ea",self.ea),kwargs.get("eb",self.eb),
                        kwargs.get("a",self.a),kwargs.get("la",self.la),raw,
                        kwargs.get("target",self.target),kwargs.get("pin",self.pin))
    def test_valid(self):
        self.assertEqual(self.verify(self.raw),"RECOVERED_LINKED_SYNTHETIC_FLOOR_AND_LEDGER_ONLY")
    def test_missing(self):
        self.assertEqual(self.verify(None),"HOLD_FLOOR_PREIMAGE_UNAVAILABLE")
    def test_old_bundle(self):
        self.assertEqual(self.verify(r.bundle(self.a,self.la)),"HOLD_FLOOR_COMMITMENT")
    def test_tampered_floor(self):
        self.assertTrue(self.verify(r.bundle(self.b.replace(self.new["head"].encode(),b"0"*64,1),self.lb)).startswith("HOLD_"))
    def test_tampered_ledger(self):
        self.assertTrue(self.verify(r.bundle(self.b,self.lb+b"x")).startswith("HOLD_"))
    def test_truncated_ledger(self):
        self.assertTrue(self.verify(r.bundle(self.b,self.la)).startswith("HOLD_"))
    def test_wrong_first_pin(self):
        self.assertEqual(self.verify(self.raw,a=self.b),"HOLD_FIRST_FLOOR_PIN")
    def test_old_envelope(self):
        self.assertEqual(self.verify(self.raw,eb=self.ea),"HOLD_ENVELOPE_LINK")
    def test_wrong_prefix(self):
        self.assertTrue(self.verify(self.raw,la=self.la+b"x").startswith("HOLD_"))
    def test_noncanonical_bundle(self):
        self.assertTrue(self.verify(self.raw+b" ").startswith("HOLD_"))
    def test_duplicate_bundle_field(self):
        raw=self.raw.replace(b'"profile":',b'"profile":"duplicate","profile":',1)
        self.assertTrue(self.verify(raw).startswith("HOLD_"))
    def test_wrong_scope_even_if_recommitted(self):
        new=copy.deepcopy(self.new);new["scope"]["epoch"]="OTHER"
        eb=r.env.canonical(dict(r.env.parse(self.eb),floor_commitment_sha256=r.commitment(new)))
        self.assertTrue(self.verify(r.bundle(r.r10.canonical(new)+b"\n",self.lb),eb=eb,target=r.env.checksum(eb)).startswith("HOLD_"))
    def test_same_count_fork(self):
        w,o=sample("aba")
        fork=observed_rows(w,o,events=["SYNTHETIC-C","SYNTHETIC-D"])
        floor=r.floor_record(fork,4)
        self.assertEqual(self.verify(r.bundle(r.r10.canonical(floor)+b"\n",r.ledger(fork))),"HOLD_FLOOR_COMMITMENT")
    def test_recommitted_fork_of_old_prefix(self):
        w,o=sample("visible_pr")
        fork=observed_rows(w,o,events=["SYNTHETIC-C","SYNTHETIC-D"])
        floor=r.floor_record(fork,4)
        eb=r.env.canonical(dict(r.env.parse(self.eb),floor_commitment_sha256=r.commitment(floor)))
        self.assertTrue(self.verify(r.bundle(r.r10.canonical(floor)+b"\n",r.ledger(fork)),eb=eb,target=r.env.checksum(eb)).startswith("HOLD_"))
    def test_event_signature_and_digest(self):
        pin=r.commitment(self.new)
        event=r.event_for(self.raw,pin)
        self.assertEqual(r.extract(event,pin),self.raw)
        self.assertIsNone(r.extract(event,r.commitment(self.old)))
        self.assertIsNone(r.extract(dict(event,content=event["content"]+"x"),pin))
    def test_wrong_count_even_if_envelope_signed(self):
        eb=r.env.canonical(dict(r.env.parse(self.eb),record_count=5))
        self.assertEqual(self.verify(self.raw,eb=eb,target=r.env.checksum(eb)),"HOLD_FLOOR_SCOPE_OR_SEQUENCE")

if __name__=="__main__":
    unittest.main()
