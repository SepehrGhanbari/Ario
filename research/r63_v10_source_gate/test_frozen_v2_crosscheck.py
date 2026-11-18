"""Offline unit tests against the SHA256-pinned V9 spend_chain_v2.py source."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import spend_chain_v2 as v2
from v10_readonly_gate import GateHold, check_spend_gate, v1_pairs

EXPECTED_V2_SHA256="c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd"

class TripwireTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="r63-v10-ci-frozen-")
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.v1=self.root/"spend.jsonl"
        self.v2=self.root/"spend-v2.jsonl"
        self.pairs=[["e"*64,"1"*64],["1"*64,"2"*64]]
        self.write(self.pairs)

    def write(self,pairs):
        self.v1.write_bytes(b"".join(v2.canonical(x)+b"\n" for x in pairs))
        raw=b""
        for n,k in pairs:
            raw,status=v2.append(raw,n,k)
            self.assertEqual(status,"NEW_NEEDS_DURABLE_APPEND")
        self.v2.write_bytes(raw)

    def check(self,memory=None,digest=None,**kw):
        return check_spend_gate(self.v1,self.v2,
            self.pairs if memory is None else memory,
            v2.snapshot(self.pairs) if digest is None else digest,**kw)

    def test_exact_frozen_v2_sha256(self):
        self.assertEqual(hashlib.sha256(Path(v2.__file__).read_bytes()).hexdigest(),
                         EXPECTED_V2_SHA256)

    def test_clean(self):
        self.assertEqual(self.check().seq,2)

    def test_empty_present_journals(self):
        self.pairs=[]
        self.write([])
        self.assertEqual(self.check().seq,0)

    def test_absent_v1_even_empty_holds(self):
        self.pairs=[];self.write([]);self.v1.unlink()
        with self.assertRaises(GateHold):self.check()

    def test_absent_v2_even_empty_holds(self):
        self.pairs=[];self.write([]);self.v2.unlink()
        with self.assertRaises(GateHold):self.check()

    def test_v1_missing(self):
        self.v1.unlink()
        with self.assertRaises(GateHold):self.check()

    def test_v1_truncated(self):
        self.v1.write_bytes(self.v1.read_bytes()[:-1])
        with self.assertRaises(GateHold):self.check()

    def test_v1_cleared(self):
        self.v1.write_bytes(b"")
        with self.assertRaises(GateHold):self.check()

    def test_v1_noncanonical(self):
        self.v1.write_bytes(self.v1.read_bytes().replace(b",",b", ",1))
        with self.assertRaises(GateHold):self.check()

    def test_v1_duplicated(self):
        raw=self.v1.read_bytes()
        self.v1.write_bytes(raw+raw.splitlines()[0]+b"\n")
        with self.assertRaises(GateHold):self.check()

    def test_v1_same_content_reordered(self):
        self.v1.write_bytes(b"".join(v2.canonical(x)+b"\n" for x in reversed(self.pairs)))
        with self.assertRaises(GateHold):self.check()

    def test_v2_truncated(self):
        self.v2.write_bytes(self.v2.read_bytes()[:-1])
        with self.assertRaises(GateHold):self.check()

    def test_v2_extra_append(self):
        raw,_=v2.append(self.v2.read_bytes(),"b"*64,"3"*64)
        self.v2.write_bytes(raw)
        with self.assertRaises(GateHold):self.check()

    def test_v2_corrupt_event_hash(self):
        self.v2.write_bytes(self.v2.read_bytes().replace(b'"prev":"',b'"prev":"f',1))
        with self.assertRaises(GateHold):self.check()

    def test_stale_memory(self):
        with self.assertRaises(GateHold):self.check(memory=list(reversed(self.pairs)))

    def test_malformed_memory(self):
        with self.assertRaises(GateHold):self.check(memory=["garbage"])

    def test_stale_r60_digest(self):
        with self.assertRaises(GateHold):self.check(digest="f"*64)

    def test_prior_v2_read_mismatch(self):
        with self.assertRaises(GateHold):self.check(expected_prior_v2=b"")

    def test_inflight_v1_deletion(self):
        with self.assertRaises(GateHold):
            self.check(between_reads_hook=self.v1.unlink)

    def test_inflight_v2_deletion(self):
        with self.assertRaises(GateHold):
            self.check(between_reads_hook=self.v2.unlink)

    def test_expected_post_review_deletion_counterexample(self):
        self.check()
        self.v1.unlink()
        self.assertFalse(self.v1.exists())

    def test_expected_whole_local_rollback_counterexample(self):
        a,b=self.v1.read_bytes(),self.v2.read_bytes()
        self.write(self.pairs+[["b"*64,"3"*64]])
        anchor=v2.anchor(self.v2.read_bytes())
        self.v1.write_bytes(a);self.v2.write_bytes(b)
        self.assertEqual(self.check().seq,2)
        with self.assertRaises(v2.Hold):v2.review(self.v2.read_bytes(),external_anchor=anchor)

    def test_over_cap_v1(self):
        self.v1.write_bytes(b"a"*(2*1024*1024+1))
        with self.assertRaises(GateHold):self.check()

    def test_over_cap_v2(self):
        self.v2.write_bytes(b"a"*(2*1024*1024+1))
        with self.assertRaises(GateHold):self.check()

    def test_v1_parser_matches_frozen_canonical(self):
        self.assertEqual(v1_pairs(self.v1.read_bytes()),self.pairs)

if __name__=="__main__":
    unittest.main(verbosity=2)
