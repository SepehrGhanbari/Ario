"""Offline contract tests for R63 V10 tripwire candidate. NO native CNG."""
from __future__ import annotations
import copy
import json
import random
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import reference_oracle_from_previous_research as prior
from r63_v10_tripwire import compare_tripwire, parse_v1, TripwireHold


class V2OfflineAdapter:
    """Previous V10's offline model, not the original V9 spend_chain_v2."""
    @staticmethod
    def review(raw):
        seq, head, pairs = prior.review_v2(raw)
        return SimpleNamespace(seq=seq, head=head, pairs=tuple(tuple(x) for x in pairs))

    @staticmethod
    def snapshot(pairs):
        return prior.snap(pairs)


class TripwireTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ario-r63-v10-tripwire-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.v1 = self.root / "spend.jsonl"
        self.v2 = self.root / "spend-v2.jsonl"
        self.memory = [["e"*64,"1"*64], ["1"*64,"2"*64]]
        self.set_pairs(self.memory)

    def set_pairs(self,pairs):
        self.v1.write_bytes(prior.fmt_pairs(pairs))
        raw=b""
        for nonce,ident in pairs:
            raw=prior.append_v2(raw,nonce,ident)
        self.v2.write_bytes(raw)

    def gate(self, *, memory=None, before=None):
        return compare_tripwire(
            v1_path=self.v1,
            v2_path=self.v2,
            in_memory_pairs=self.memory if memory is None else memory,
            broker_before=prior.snap(self.memory) if before is None else before,
            canonical=prior.canon,
            digest=lambda x: prior.h(prior.canon(x)),
            spendv2=V2OfflineAdapter,
        )

    def assert_hold(self, code=None, **kw):
        with self.assertRaises(TripwireHold) as caught:
            self.gate(**kw)
        if code:self.assertIn(code,str(caught.exception))

    def test_valid_reversed_lexical_nonce_sequence(self):
        before_a,before_b=self.v1.read_bytes(),self.v2.read_bytes()
        state=self.gate()
        self.assertEqual(state.seq,2)
        self.assertEqual(before_a,self.v1.read_bytes())
        self.assertEqual(before_b,self.v2.read_bytes())
        # R60 sorted-content remains the same when append order changes.
        self.assertEqual(prior.snap(self.memory),prior.snap(list(reversed(self.memory))))
        reverse=b""
        for nonce,ident in reversed(self.memory):
            reverse=prior.append_v2(reverse,nonce,ident)
        self.assertNotEqual(state.head,V2OfflineAdapter.review(reverse).head)

    def test_initial_empty_is_consistent(self):
        self.set_pairs([])
        self.memory=[]
        self.assertEqual(self.gate().seq,0)

    def test_missing_v1(self):
        self.v1.unlink()
        self.assert_hold("MISSING_OR_UNREADABLE")

    def test_missing_v2(self):
        self.v2.unlink()
        self.assert_hold("MISSING_OR_UNREADABLE")

    def test_v1_truncated_to_one_valid_row(self):
        self.v1.write_bytes(self.v1.read_bytes().splitlines(keepends=True)[0])
        self.assert_hold("DIVERGENCE")

    def test_v1_truncated_partial_row(self):
        self.v1.write_bytes(self.v1.read_bytes()[:-2])
        self.assert_hold("PARTIAL_LAST_LINE")

    def test_v1_modified_canonical_row(self):
        wrong=[["a"*64,"1"*64],self.memory[1]]
        self.v1.write_bytes(prior.fmt_pairs(wrong))
        self.assert_hold("DIVERGENCE")

    def test_v1_noncanonical_space(self):
        self.v1.write_bytes(self.v1.read_bytes().replace(b',',b', ',1))
        self.assert_hold("NONCANONICAL")

    def test_v1_invalid_json(self):
        self.v1.write_bytes(b"!!\n")
        self.assert_hold("BAD_JSON")

    def test_v1_duplicate_nonce(self):
        pair=[self.memory[0][0],"9"*64]
        self.v1.write_bytes(prior.fmt_pairs(self.memory+[pair]))
        self.assert_hold("DUPLICATE")

    def test_v1_duplicate_id(self):
        pair=["7"*64,self.memory[0][1]]
        self.v1.write_bytes(prior.fmt_pairs(self.memory+[pair]))
        self.assert_hold("DUPLICATE")

    def test_v1_uppercase_hex(self):
        self.v1.write_bytes(prior.fmt_pairs([["E"*64,"1"*64],self.memory[1]]))
        self.assert_hold("BAD_NONCE_OR_ID")

    def test_v1_crlf(self):
        self.v1.write_bytes(self.v1.read_bytes().replace(b'\n',b'\r\n'))
        self.assert_hold("NONCANONICAL")

    def test_v1_empty_line(self):
        self.v1.write_bytes(self.v1.read_bytes()+b"\n")
        self.assert_hold("EMPTY_OR_OVERSIZED")

    def test_v1_row_limit(self):
        self.v1.write_bytes(b"x"*8193+b"\n")
        self.assert_hold("EMPTY_OR_OVERSIZED")

    def test_v1_total_limit(self):
        self.v1.write_bytes(b"X"*(2*1024*1024+1))
        self.assert_hold("JOURNAL_LIMIT_EXCEEDED")

    def test_v2_missing_chain_record(self):
        raw=self.v2.read_bytes()
        self.v2.write_bytes(raw.splitlines(keepends=True)[0])
        self.assert_hold("DIVERGENCE")

    def test_v2_corrupt_hash(self):
        obj=json.loads(self.v2.read_bytes().splitlines()[0])
        obj['hash']='f'*64
        lines=self.v2.read_bytes().splitlines()
        lines[0]=prior.canon(obj)
        self.v2.write_bytes(b'\n'.join(lines)+b'\n')
        self.assert_hold("V2_REVIEW_FAILED")

    def test_v2_extra_unsigned_append(self):
        raw=self.v2.read_bytes()
        self.v2.write_bytes(prior.append_v2(raw,"7"*64,"3"*64))
        self.assert_hold("DIVERGENCE")

    def test_in_memory_mismatch(self):
        self.assert_hold("DIVERGENCE",memory=list(reversed(self.memory)))

    def test_bad_broker_digest(self):
        self.assert_hold("R60_SORTED_CONTENT_MISMATCH",before="f"*64)

    def test_bad_broker_digest_shape(self):
        self.assert_hold("R60_BAD_BROKER_HASH",before="bad")

    def test_restore_local_with_old_snapshot_still_accepted(self):
        old_v1=self.v1.read_bytes()
        old_v2=self.v2.read_bytes()
        # Simulated same-admin coherent rollback; a read-only tripwire cannot
        # detect a whole local-domain replacement (nor claim that it does).
        newer=self.memory+[["7"*64,"3"*64]]
        self.set_pairs(newer)
        self.assertEqual(self.v1.read_bytes(),prior.fmt_pairs(newer))
        self.v1.write_bytes(old_v1)
        self.v2.write_bytes(old_v2)
        self.assertEqual(self.gate().seq,2)

    def test_no_rewrite_of_source_legacy_journal(self):
        old=self.v1.read_bytes()
        self.gate()
        self.assertEqual(self.v1.read_bytes(),old)

    def test_300_mutations_of_v1_bytes_do_not_pass(self):
        seed=632026
        randomizer=random.Random(seed)
        old=self.v1.read_bytes()
        for _ in range(300):
            changed=bytearray(old)
            i=randomizer.randrange(len(changed))
            changed[i]=changed[i]^randomizer.randrange(1,256)
            self.v1.write_bytes(changed)
            self.assert_hold()
        self.v1.write_bytes(old)
        self.assertEqual(self.gate().seq,2)

if __name__=='__main__':
    unittest.main(verbosity=2)
