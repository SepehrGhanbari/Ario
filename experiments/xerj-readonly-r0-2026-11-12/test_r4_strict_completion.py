"""Research-only R4 deterministic tests of the exact, *locally proposed* parser patch.

No engine is run.  A complete synthetic response is *not* an authenticity attestation.
"""
import copy
import unittest
from ario_xerj_readonly import ArioRecord, parse_candidates

INDEX = "ario-r4-test"
LEDGER = {
    "e1": ArioRecord.from_text("e1", "Dana prefers yarn to pnpm", root_label="LAB_R1"),
    "e2": ArioRecord.from_text("e2", "Dana also likes Python", root_label="LAB_R1"),
    "e3": ArioRecord.from_text("e3", "Dana also likes Rust", root_label="LAB_R1"),
}


def wire(hits=True, **patch):
    res = {
        "timed_out": False,
        "_shards": {"total": 1, "successful": 1, "failed": 0, "skipped": 0},
        "hits": {
            "hits": [{"_id": "e1", "_index": INDEX, "_source": {"text": "FORGED"}}] if hits else [],
            "total": {"value": int(bool(hits)), "relation": "eq"},
        },
    }
    if isinstance(hits, dict):
        res["hits"] = hits
    for k, v in patch.items():
        res[k] = v
    return res


def run(resp, strict=True, k=2):
    return parse_candidates(resp, LEDGER, k=k, expected_index=INDEX,
                            require_completion_metadata=strict)


class R4StrictMetadataTests(unittest.TestCase):
    def test_successful_positive_one_shard(self):
        r = run(wire())
        self.assertEqual(r["status"], "CANDIDATES_ONLY")
        self.assertEqual([x["event_id"] for x in r["candidates"]], ["e1"])
        self.assertEqual(r["candidates"][0]["text"], LEDGER["e1"].text)

    def test_complete_empty_one_shard(self):
        self.assertEqual(run(wire(hits=False))["status"], "NO_HITS_UNKNOWN")

    def test_malformed_and_incomplete_responses_never_emit_candidates(self):
        scenarios = {
            "positive_zero_shards": wire(_shards={"total": 0, "successful": 0, "failed": 0, "skipped": 0}),
            "empty_zero_shards": wire(hits=False, _shards={"total": 0, "successful": 0, "failed": 0, "skipped": 0}),
            "skipped_shard": wire(_shards={"total": 2, "successful": 1, "failed": 0, "skipped": 1}),
            "terminated_early_true": wire(terminated_early=True),
            "terminated_early_string": wire(terminated_early="false"),
            "exact_total_zero_positive_hit": wire(hits={"hits": [{"_id":"e1", "_index":INDEX}], "total": {"value":0,"relation":"eq"}}),
            "integer_total_zero_positive_hit": wire(hits={"hits": [{"_id":"e1", "_index":INDEX}], "total":0}),
            "noninteger_total": wire(hits={"hits": [{"_id":"e1", "_index":INDEX}], "total":False}),
            "negative_total": wire(hits={"hits": [{"_id":"e1", "_index":INDEX}], "total":{"value":-1,"relation":"eq"}}),
            "invalid_relation": wire(hits={"hits": [{"_id":"e1", "_index":INDEX}], "total":{"value":1,"relation":"bogus"}}),
            "shard_boolean": wire(_shards={"total":True,"successful":1,"failed":0,"skipped":0}),
            "failed_shard": wire(_shards={"total":2,"successful":1,"failed":1,"skipped":0}),
            "missing_shard_metadata": {k:v for k,v in wire().items() if k != "_shards"},
            "unexpected_timeout": wire(timed_out=True),
            "foreign_index": wire(hits={"hits": [{"_id":"e1", "_index":"foreign"}], "total":1}),
        }
        for label, resp in scenarios.items():
            with self.subTest(name=label):
                result=run(resp)
                self.assertEqual(result["status"], "RETRIEVAL_INCOMPLETE")
                self.assertEqual(result["candidates"], [])
                self.assertEqual(result["distinct_root_labels"], [])
                self.assertFalse(result["answer_authorized"])

    def test_lower_bound_zero_with_positive_hit_is_inexact_in_strict_profile(self):
        r=wire(hits={"hits":[{"_id":"e1","_index":INDEX}],
                     "total":{"value":0,"relation":"gte"}})
        self.assertEqual(run(r)["status"], "RETRIEVAL_INCOMPLETE")
        # Legacy direct-fixture mode does not inspect completion metadata.
        self.assertEqual(run(r, strict=False)["status"], "CANDIDATES_ONLY")

    def test_total_missing_cannot_prove_complete_first_page(self):
        r=wire()
        del r["hits"]["total"]
        self.assertEqual(run(r)["status"], "RETRIEVAL_INCOMPLETE")
        self.assertEqual(run(r)["candidates"], [])

    def test_exact_first_page_positive_pairs(self):
        def hit(i): return {"_id":i,"_index":INDEX}
        for k, n, ids in ((3,2,["e1","e2"]),(3,5,["e1","e2","e3"]),
                          (3,0,[]),(3,3,["e1","e2","e3"])):
            with self.subTest(k=k,n=n):
                q=wire(hits={"hits":[hit(i) for i in ids],
                             "total":{"value":n,"relation":"eq"}})
                self.assertEqual(run(q,k=k)["status"],
                                 "CANDIDATES_ONLY" if ids else "NO_HITS_UNKNOWN")

    def test_exact_short_first_page_rejected_even_with_zero_hits(self):
        for k,n,ids in ((3,2,["e1"]),(3,2,[]),(3,5,["e1","e2"]),
                        (2,1,[]),(3,4,["e1","e2"])):
            with self.subTest(k=k,n=n,ids=ids):
                q=wire(hits={"hits":[{"_id":i,"_index":INDEX} for i in ids],
                             "total":{"value":n,"relation":"eq"}})
                x=run(q,k=k)
                self.assertEqual(x["status"],"RETRIEVAL_INCOMPLETE")
                self.assertEqual(x["candidates"],[])
                self.assertEqual(x["distinct_root_labels"],[])
                self.assertFalse(x["answer_authorized"])

    def test_wrong_total_shape_and_skipped_presence_fail_closed(self):
        for total in (-1,0,1,True,0.0,{"value":1,"relation":"gte"},
                      {"value":0,"relation":"gte"},
                      {"value":1,"relation":"bogus"}):
            with self.subTest(total=total):
                x=run(wire(hits={"hits":[{"_id":"e1","_index":INDEX}],"total":total}))
                self.assertEqual(x["status"],"RETRIEVAL_INCOMPLETE")
                self.assertEqual(x["candidates"],[])
        missing=wire()
        del missing["_shards"]["skipped"]
        self.assertEqual(run(missing)["status"],"RETRIEVAL_INCOMPLETE")

    def test_legacy_direct_parser_mode_kept_separate(self):
        r=wire(_shards={"total":0,"successful":0,"failed":0})
        self.assertEqual(run(r, strict=False)["status"], "CANDIDATES_ONLY")
        self.assertEqual(run(r, strict=True)["status"], "RETRIEVAL_INCOMPLETE")

    def test_non_authority_preserved(self):
        for resp in (wire(), wire(hits=False), wire(terminated_early=True)):
            x=run(resp)
            self.assertIs(x["answer_authorized"], False)
            self.assertIs(x["trust_activated"], False)
            self.assertEqual(x["source_independence"], "NOT_ESTABLISHED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
