"""Standalone bounded JSON primitive tests; no CLI/admission coupling.

This test file is additive and synthetic. The depth-64 and 4096-digit
ceilings already exist on main after PR #298. These tests constrain only
the default integer hook's interpreter-cap behavior, not production authority.
Input size remains a caller-owned budget.
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

    def test_explicit_none_int_hook_is_still_bounded(self):
        # json.loads(parse_int=None) normally selects the interpreter default.
        with self.assertRaises(JSONValueLimitExceeded):
            loads_bounded("9" * 5000, parse_int=None)

    @unittest.skipUnless(
        hasattr(sys, "set_int_max_str_digits") and hasattr(sys, "get_int_max_str_digits"),
        "interpreter has no configurable integer conversion limit",
    )
    def test_lowered_runtime_digit_cap_does_not_reject_within_candidate_bound(self):
        original = sys.get_int_max_str_digits()
        try:
            # CPython minimum nonzero limit is 640 decimal digits.
            sys.set_int_max_str_digits(640)
            self.assertIsInstance(loads_bounded("9" * 700), int)
            self.assertIsInstance(loads_bounded("9" * MAX_JSON_INTEGER_DIGITS), int)
            with self.assertRaises(JSONValueLimitExceeded):
                loads_bounded("9" * (MAX_JSON_INTEGER_DIGITS + 1))
        finally:
            sys.set_int_max_str_digits(original)

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



    @unittest.skipUnless(
        hasattr(sys, "set_int_max_str_digits") and hasattr(sys, "get_int_max_str_digits"),
        "interpreter has no configurable integer conversion limit",
    )
    def test_explicit_builtin_int_hook_is_stable_at_lowered_cap(self):
        previous = sys.get_int_max_str_digits()
        try:
            sys.set_int_max_str_digits(640)
            self.assertIsInstance(loads_bounded("8" * 700, parse_int=int), int)
            self.assertIsInstance(loads_bounded("-" + "8" * 4096, parse_int=int), int)
            with self.assertRaises(JSONValueLimitExceeded):
                loads_bounded("8" * 4097, parse_int=int)
        finally:
            sys.set_int_max_str_digits(previous)


    @unittest.skipUnless(
        hasattr(sys, "set_int_max_str_digits") and hasattr(sys, "get_int_max_str_digits"),
        "interpreter has no configurable integer conversion limit",
    )
    def test_lock_inspection_rejects_impossible_700_digit_pid_as_unknown(self):
        """Read-only CLI must never attempt to JSON-emit a huge int lock PID."""
        import io
        import tempfile
        from contextlib import redirect_stdout
        from pathlib import Path
        import ario_agent

        with tempfile.TemporaryDirectory(prefix="ario-int-pid-boundary-") as temp:
            ledger = Path(temp) / "synthetic.jsonl"
            lock = ledger.with_name(ledger.name + ".lock")
            initial = ('{"pid":' + '9' * 700 +
                       ',"task_id":"T","started_at":"2026-01-01T00:00:00Z"}').encode()
            lock.write_bytes(initial)
            prior = sys.get_int_max_str_digits()
            try:
                sys.set_int_max_str_digits(640)
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = ario_agent.main([
                        "--inspect-lock", "--ledger", str(ledger)
                    ])
                report = json.loads(output.getvalue())
                self.assertEqual(exit_code, 2)
                self.assertEqual(report["status"], "UNKNOWN")
                self.assertNotIn("lock_record", report)
                self.assertFalse(report["write_performed"])
                self.assertFalse(report["automatic_removal"])
            finally:
                sys.set_int_max_str_digits(prior)
            self.assertEqual(lock.read_bytes(), initial)
            self.assertFalse(ledger.exists())

    def test_lock_inspection_pid_range_and_no_mutation(self):
        """The lock contains an operating-system PID, never arbitrary JSON int."""
        import tempfile
        from pathlib import Path
        import ario_agent

        with tempfile.TemporaryDirectory(prefix="ario-pid-range-") as temp:
            ledger = Path(temp) / "synthetic.jsonl"
            lock = ledger.with_name(ledger.name + ".lock")
            for raw_pid, expected in (
                ("1", "LOCK_PRESENT"),
                ("4294967295", "LOCK_PRESENT"),
                ("4294967296", "UNKNOWN"),
                ("-1", "UNKNOWN"),
            ):
                lock.write_text(
                    '{"pid":' + raw_pid +
                    ',"task_id":"T","started_at":"t"}',
                    encoding="utf-8",
                )
                original = lock.read_bytes()
                report = ario_agent.inspect_execution_lock(ledger)
                self.assertEqual(report["status"], expected, raw_pid)
                self.assertEqual(report["write_performed"], False)
                self.assertEqual(report["automatic_removal"], False)
                self.assertEqual(lock.read_bytes(), original)

@unittest.skipUnless(hasattr(sys, "set_int_max_str_digits"), "requires a configurable digit limit")
class AgentIntegerOutputTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(sys.set_int_max_str_digits, sys.get_int_max_str_digits())
        sys.set_int_max_str_digits(640)

    def test_line_positions_are_checked_during_task_validation(self):
        from ario_agent import AgentRequestError, parse_task

        first_too_large = 10 ** 640
        for field in ("start_line", "expected_next_start_line"):
            action = {"step_id": "s", "tool": "read_text", "path": "example"}
            if field == "expected_next_start_line":
                action["expected_truncated"] = False
            task = {"task_id": "t", "goal": "read", "actions": [action]}
            with self.subTest(field=field):
                action[field] = first_too_large - 1
                self.assertEqual(parse_task(task)["actions"][0][field], first_too_large - 1)
                action[field] = first_too_large
                with self.assertRaisesRegex(AgentRequestError, field + " exceeds"):
                    parse_task(task)

    def test_nested_output_values_follow_the_encoder_limit(self):
        from ario_agent import _integers_fit_json_output

        boundary = 10 ** 640
        self.assertTrue(_integers_fit_json_output({"values": [1 - boundary, "9" * 700]}))
        self.assertFalse(_integers_fit_json_output({"values": [-boundary]}))
        sys.set_int_max_str_digits(0)
        self.assertTrue(_integers_fit_json_output({"values": [-boundary]}))

    def test_report_refusal_returns_one_unknown_without_writing(self):
        import io
        import tempfile
        from contextlib import redirect_stdout
        from pathlib import Path
        from unittest.mock import patch
        import ario_agent

        with tempfile.TemporaryDirectory() as temp:
            ledger = Path(temp) / "events.jsonl"
            original = b'{"event":"TASK_STARTED","task_id":"t","goal":"read"}\n'
            ledger.write_bytes(original)
            output = io.StringIO()
            with patch.object(ario_agent, "_integers_fit_json_output", return_value=False), redirect_stdout(output):
                code = ario_agent.main(["--inspect-task-id", "t", "--ledger", str(ledger)])
            report = json.loads(output.getvalue())
            self.assertEqual((code, report["status"], report["event_count"]), (2, "UNKNOWN", 1))
            self.assertFalse(report["automatic_resume"])
            self.assertFalse(report["write_performed"])
            self.assertEqual(ledger.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
