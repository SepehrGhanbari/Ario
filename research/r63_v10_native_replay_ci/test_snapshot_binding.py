"""R63 synthetic signed-receipt payload/current-journal binding tests."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from prepare_public_payload import prepare
from verify_durable_snapshot import verify,Hold
sys.path.insert(0,str(HERE.parent/"r63_v10_source_gate"))
import spend_chain_v2 as v2

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="r63_current_snapshot_")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"fixture"
        prepare(self.root)

    def test_positive_current_snapshot(self):
        result=verify(self.root)
        self.assertEqual(result["v2_event_count"],2)

    def test_v1_missing(self):
        (self.root/"v1.jsonl").unlink()
        with self.assertRaises(Hold):verify(self.root)

    def test_v2_missing(self):
        (self.root/"v2.jsonl").unlink()
        with self.assertRaises(Hold):verify(self.root)

    def test_v1_partial_last_line(self):
        p=self.root/"v1.jsonl";p.write_bytes(p.read_bytes()[:-1])
        with self.assertRaises(Hold):verify(self.root)

    def test_v2_partial_last_line(self):
        p=self.root/"v2.jsonl";p.write_bytes(p.read_bytes()[:-1])
        with self.assertRaises(Hold):verify(self.root)

    def test_v1_reordered(self):
        p=self.root/"v1.jsonl";p.write_bytes(b"\n".join(reversed(p.read_bytes().splitlines()))+b"\n")
        with self.assertRaises(Hold):verify(self.root)

    def test_corrupt_v2_hash(self):
        p=self.root/"v2.jsonl";p.write_bytes(p.read_bytes().replace(b'"prev":"',b'"prev":"f',1))
        with self.assertRaises(Hold):verify(self.root)

    def test_new_v2_reservation_requires_new_signed_snapshot(self):
        p=self.root/"v2.jsonl"
        next_raw,kind=v2.append(p.read_bytes(),"c"*64,"3"*64)
        self.assertEqual(kind,"NEW_NEEDS_DURABLE_APPEND")
        p.write_bytes(next_raw)
        with self.assertRaises(Hold):verify(self.root)

    def test_metadata_event_head_wrong(self):
        p=self.root/"metadata.json";obj=json.loads(p.read_text())
        obj["v2_head"]="f"*64
        p.write_text(json.dumps(obj),encoding="utf-8")
        with self.assertRaises(Hold):verify(self.root)

    def test_metadata_nonce_wrong(self):
        p=self.root/"metadata.json";obj=json.loads(p.read_text())
        obj["nonce"]="f"*64
        p.write_text(json.dumps(obj),encoding="utf-8")
        with self.assertRaises(Hold):verify(self.root)

    def test_payload_mutated(self):
        p=self.root/"payload.bin";b=bytearray(p.read_bytes());b[-1]^=1;p.write_bytes(b)
        with self.assertRaises(Hold):verify(self.root)

    def test_metadata_canonical_terminal_lf_required(self):
        p=self.root/"metadata.json"
        p.write_bytes(p.read_bytes()[:-1])
        with self.assertRaises(Hold):verify(self.root)

    def test_missing_metadata(self):
        (self.root/"metadata.json").unlink()
        with self.assertRaises(Hold):verify(self.root)

    def test_post_check_modification_not_prevented(self):
        verify(self.root)
        (self.root/"v1.jsonl").unlink()
        self.assertFalse((self.root/"v1.jsonl").exists())

    def test_coherent_local_rollback_is_accepted_expected_counterexample(self):
        names=("v1.jsonl","v2.jsonl","payload.bin","metadata.json")
        old={n:(self.root/n).read_bytes() for n in names}
        # Move forward on disk, then roll back ALL same-admin files together.
        p=self.root/"v2.jsonl"
        new,kind=v2.append(p.read_bytes(),"c"*64,"3"*64)
        self.assertEqual(kind,"NEW_NEEDS_DURABLE_APPEND")
        p.write_bytes(new)
        with self.assertRaises(Hold):verify(self.root)
        for n,raw in old.items(): (self.root/n).write_bytes(raw)
        self.assertEqual(verify(self.root)["v2_event_count"],2)
        # Passing this test proves the lack of external rollback protection.

if __name__=="__main__":unittest.main(verbosity=2)
