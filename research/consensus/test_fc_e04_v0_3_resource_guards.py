#!/usr/bin/env python3
"""FC-E04 v0.2: negative resource-boundary regression (synthetic, read-only)."""
import hashlib
import json
import unittest
from unittest.mock import patch

import fc_e04_readonly_comparator_v0_3 as fc


class ResourceGuards(unittest.TestCase):
    def _unknown(self, raw, reason, expect_digest):
        actual = fc.evaluate_image(raw)
        self.assertEqual(actual['final']['status'], 'UNKNOWN')
        self.assertEqual(actual['final']['reason'], reason)
        self.assertEqual(actual['image_sha256'], expect_digest)
        self.assertEqual(actual['world_truth'], 'UNKNOWN')
        self.assertEqual(actual['source_custody'], 'NOT_ESTABLISHED')
        self.assertFalse(actual['memory_admitted'])
        self.assertEqual(actual['action_authority'], 'NONE')
        return actual

    def test_01_oversize_never_full_hashes_on_failure(self):
        raw = b'x' * (fc.MAX_BYTES + 1)
        with patch.object(fc, '_sha', side_effect=AssertionError('FULL_HASH_ON_REFUSAL')):
            self._unknown(raw, 'IMAGE_TYPE_OR_BYTE_LIMIT', None)

    def test_02_oversize_recognition_never_full_hashes(self):
        raw = b'X' * (fc.MAX_BYTES + 1)
        with patch.object(fc, '_sha', side_effect=AssertionError('FULL_HASH_ON_REFUSAL')):
            rec = fc.recognize_image(raw)
        self.assertEqual(rec['status'], 'UNKNOWN')
        self.assertEqual(rec['reason'], 'IMAGE_TYPE_OR_BYTE_LIMIT')
        self.assertIsNone(rec['image_sha256'])

    def test_03_huge_input_does_not_masquerade_as_prefix_sha(self):
        raw = b'A' * 2_000_000
        observed = self._unknown(raw, 'IMAGE_TYPE_OR_BYTE_LIMIT', None)
        self.assertIsNone(observed['image_sha256'])
        self.assertNotEqual(observed['image_sha256'], hashlib.sha256(raw[:fc.MAX_BYTES]).hexdigest())

    def test_04_nonbytes_is_no_digest(self):
        self._unknown(bytearray(b'{}'), 'IMAGE_TYPE_OR_BYTE_LIMIT', None)

    def test_05_integer_129_digits_refused_before_conversion(self):
        raw = b'{"schema":"bad","number":' + b'9'*129 + b'}'
        self._unknown(raw, 'JSON_INTEGER_DIGIT_LIMIT', hashlib.sha256(raw).hexdigest())

    def test_06_negative_integer_129_digits_refused(self):
        raw = b'{"schema":"bad","number":-' + b'9'*129 + b'}'
        self._unknown(raw, 'JSON_INTEGER_DIGIT_LIMIT', hashlib.sha256(raw).hexdigest())

    def test_07_integer_128_digits_passes_numeric_limit_not_schema(self):
        raw = b'{"schema":"bad","number":' + b'9'*128 + b'}'
        self._unknown(raw, 'IMAGE_SCHEMA', hashlib.sha256(raw).hexdigest())

    def test_08_huge_integer_5000_digits_refused_deterministically(self):
        raw = b'{"schema":"bad","number":' + b'1'*5000 + b'}'
        self._unknown(raw, 'JSON_INTEGER_DIGIT_LIMIT', hashlib.sha256(raw).hexdigest())

    def test_09_number_brackets_inside_string_do_not_count(self):
        x = b'{"schema":"bad","txt":"' + b'['*65 + b'"}'
        self._unknown(x, 'IMAGE_SCHEMA', hashlib.sha256(x).hexdigest())

    def test_10_bounded_w9_unchanged_blob(self):
        from pathlib import Path
        p=Path(fc.__file__).with_name('w9_bounded_receipt_contract.py')
        bs=p.read_bytes()
        h=hashlib.sha1(b'blob '+str(len(bs)).encode()+b'\0'+bs).hexdigest()
        self.assertEqual(h, fc.W9_BLOB_SHA1)
        self.assertLess(len(bs),fc.MAX_W9_SOURCE_BYTES)

    def test_11_bounded_small_malformed_bytes_hash_is_exact(self):
        raw=b'not-json'
        self._unknown(raw, 'INVALID_JSON_OR_UNICODE', hashlib.sha256(raw).hexdigest())

    def test_12_quoted_digits_not_numeric_token(self):
        raw=b'{"schema":"bad","number":"'+b'9'*5000+b'"}'
        self._unknown(raw, 'IMAGE_SCHEMA', hashlib.sha256(raw).hexdigest())

if __name__ == '__main__':
    unittest.main()
