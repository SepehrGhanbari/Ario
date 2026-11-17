"""Standalone bounded JSON primitive tests; no CLI/admission coupling.

This test file is additive and synthetic. The 4096-decimal-digit threshold is
copied from #248 as a *candidate* value, not an owner-approved contract.
Do not merge this Draft until real-ledger compatibility and threshold choice
are resolved. Input size remains a caller-owned budget.
"""
import json
import sys
import unittest

from bounded_json import (
    JSONDepthExceeded,
    JSONValueLimitExceeded,
    MAX_JSON_DEPTH,
    MAX_JSON_INTEGER_DIGITS,
    loads_bounded,
    nesting_exceeds,
)


class BoundedJsonPrimitiveTests(unittest.TestCase):
    def test_depth_limit_exact_boundary(self):
        inner = "[" * (MAX_JSON_DEPTH - 1) + "0" + "]" * (MAX_JSON_DEPTH - 1)
        ok = '{"payload":' + inner + "}"
        self.assertIsNone(nesting_exceeds(ok))
        self.assertIsInstance(loads_bounded(ok), dict)

        too_deep = '{"payload":' + "[" * MAX_JSON_DEPTH + "0" + "]" * MAX_JSON_DEPTH + "}"
        with self.assertRaises(JSONDepthExceeded) as caught:
            loads_bounded(too_deep)
        self.assertIsInstance(caught.exception, json.JSONDecodeError)
        self.assertGreater(caught.exception.pos, 0)

    def test_deep_input_rejected_before_runtime_recursion(self):
        raw = "[" * 12000 + "0" + "]" * 12000
        with self.assertRaises(JSONDepthExceeded):
            loads_bounded(raw)

    def test_escaped_brackets_in_strings_not_depth(self):
        noisy = '[{' * 200 + '\\"' + '}]' * 200
        raw = json.dumps({"payload": noisy})
        self.assertEqual(loads_bounded(raw), {"payload": noisy})
        self.assertIsNone(nesting_exceeds(raw))

    def test_decimal_integer_bound_at_candidate_4096(self):
        candidate = "9" * MAX_JSON_INTEGER_DIGITS
        self.assertIsInstance(loads_bounded(candidate), int)
        for raw in ("9" * (MAX_JSON_INTEGER_DIGITS + 1),
                    "-" + "9" * (MAX_JSON_INTEGER_DIGITS + 1)):
            with self.subTest(negative=raw.startswith("-")):
                with self.assertRaises(JSONValueLimitExceeded) as caught:
                    loads_bounded(raw)
                self.assertIn("integer digit limit", str(caught.exception))

    def test_4300_digits_currently_rejected_by_candidate(self):
        # Explicitly pin the policy difference with historical JSON parsing:
        # 4300 may be accepted by an unmodified CPython default decoder.
        with self.assertRaises(JSONValueLimitExceeded):
            loads_bounded("9" * 4300)

    def test_custom_integer_hook_cannot_bypass_limit(self):
        self.assertEqual(loads_bounded('{"n": 12}', parse_int=str), {"n": "12"})
        with self.assertRaises(JSONValueLimitExceeded):
            loads_bounded("9" * (MAX_JSON_INTEGER_DIGITS + 1), parse_int=str)

    def test_value_error_from_hook_maps_to_decoder_error(self):
        def refuse(_):
            raise ValueError("synthetic callback refusal")
        with self.assertRaises(JSONValueLimitExceeded):
            loads_bounded("123", parse_int=refuse)

    def test_digits_inside_json_string_are_not_integer_tokens(self):
        raw = "9" * 5000
        self.assertEqual(loads_bounded(json.dumps(raw)), raw)

    def test_malformed_json_preserves_original_decoder_error(self):
        with self.assertRaises(json.JSONDecodeError) as caught:
            loads_bounded('{"a": }')
        self.assertNotIsInstance(caught.exception, JSONValueLimitExceeded)
        self.assertGreater(caught.exception.pos, 0)

    @unittest.skipUnless(
        hasattr(sys, "set_int_max_str_digits") and hasattr(sys, "get_int_max_str_digits"),
        "interpreter has no configurable integer conversion limit",
    )
    def test_integer_limit_independent_of_interpreter_setting(self):
        original = sys.get_int_max_str_digits()
        try:
            sys.set_int_max_str_digits(0)
            self.assertIsInstance(loads_bounded("9" * 4096), int)
            with self.assertRaises(JSONValueLimitExceeded):
                loads_bounded("9" * 5000)
        finally:
            sys.set_int_max_str_digits(original)


if __name__ == "__main__":
    unittest.main()
