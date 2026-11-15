"""Pure-stdlib tests for the research-only, non-integrated snapshot comparator.

Run: python -m unittest -v test_ario_same_snapshot_comparator.py
The test doubles do NOT replace later verification against pinned actual source.
"""
import hashlib
import io
import json
import types
import unittest
from pathlib import Path
from ario_same_snapshot_comparator import compare_snapshot


def observed_fake(path):
    import hashlib
    target = Path(path)
    with target.open("rb") as stream:
        raw = stream.read()
    if b"BROKEN" in raw:
        return {"status": "UNKNOWN"}
    return {"status": "OBSERVED", "sha256": hashlib.sha256(raw).hexdigest(),
            "event_count": raw.count(b"\n"), "source": str(target.absolute()),
            "observations": [{"goal": "PRIVATE"}]}


def strict_fake(raw):
    if b"BROKEN" in raw or b"STRICT_ONLY" in raw:
        return {"status": "UNKNOWN", "reason_code": "SCHEMA_REJECTED",
                "eligible_records": 0, "file_sha256": None}
    return {"status": "OBSERVED", "eligible_records": raw.count(b"\n"),
            "file_sha256": hashlib.sha256(raw).hexdigest()}


class ComparatorTests(unittest.TestCase):
    def setUp(self):
        self.legacy = types.SimpleNamespace(observe_ledger=observed_fake)
        self.strict = types.SimpleNamespace(inspect_jsonl_bytes=strict_fake)
        self.raw = b'{"event":"TASK_STARTED"}\n'

    def call(self, raw=None, **kw):
        return compare_snapshot(self.raw if raw is None else raw,
                                legacy_observer_module=self.legacy,
                                strict_lab_module=self.strict, **kw)

    def test_agree_observed_and_no_original_module_monkeypatch(self):
        original = observed_fake.__globals__.get("Path")
        a = self.call()
        self.assertEqual(a["comparison"], "AGREE_OBSERVED")
        self.assertIsNone(a["snapshot_sha256"])
        self.assertEqual(a["legacy_record_count"], 1)
        self.assertEqual(observed_fake.__globals__.get("Path"), original)

    def test_optin_digest(self):
        a = self.call(include_digest=True)
        self.assertEqual(a["snapshot_sha256"], hashlib.sha256(self.raw).hexdigest())

    def test_agree_unknown(self):
        self.assertEqual(self.call(b"BROKEN\n")["comparison"], "AGREE_UNKNOWN")

    def test_disagree_without_content_disclosure(self):
        a = self.call(b"STRICT_ONLY\n")
        self.assertEqual(a["comparison"], "DISAGREE")
        self.assertEqual(a["candidate_reason_code"], "SCHEMA_REJECTED")
        self.assertNotIn("PRIVATE", json.dumps(a))
        self.assertNotIn("STRICT_ONLY", json.dumps(a))

    def test_reject_oversize_before_running_any_parser(self):
        a = self.call(b"x" * 16, max_snapshot_bytes=8)
        self.assertEqual(a["comparison"], "UNKNOWN_COMPARISON")
        self.assertEqual(a["reason_code"], "SNAPSHOT_SIZE_LIMIT")
        self.assertIsNone(a["legacy_status"])

    def test_reject_empty(self):
        a = self.call(b"")
        self.assertEqual(a["reason_code"], "EMPTY_SNAPSHOT")

    def test_non_bytes(self):
        with self.assertRaises(TypeError):
            self.call(bytearray(b"x\n"))

    def test_bad_limit_and_digest_flag(self):
        with self.assertRaises(ValueError):
            self.call(max_snapshot_bytes=0)
        with self.assertRaises(TypeError):
            self.call(include_digest=1)

    def test_bad_parser_data_is_unknown(self):
        self.strict.inspect_jsonl_bytes=lambda raw: {"status":"OBSERVED", "eligible_records":1,
                                                      "file_sha256":"0"*64}
        a = self.call()
        self.assertEqual(a["comparison"], "UNKNOWN_COMPARISON")
        self.assertEqual(a["reason_code"], "ACCEPTED_DIGEST_OR_COUNT_MISMATCH")

    def test_exception_no_leak(self):
        def failing(_raw):
            raise RuntimeError("private goal content")
        self.strict.inspect_jsonl_bytes=failing
        a = self.call()
        self.assertEqual(a["reason_code"], "COMPARATOR_EXECUTION_ERROR")
        self.assertNotIn("private goal", json.dumps(a))


if __name__ == "__main__":
    unittest.main()
