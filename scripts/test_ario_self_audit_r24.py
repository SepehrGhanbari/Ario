import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import ario_self_audit_r24 as r24

STAMP = "2026-11-24T18:31:33.7119771Z"


def make_log(expected, checkout=None, summary=None, extra_summary=None):
    checkout = checkout or r24.EXPECTED_CHECKOUT
    summary = summary or expected["summary"]
    lines = [
        f"{STAMP} Current runner version: '2.338.2'",
        f"{STAMP} ##[group]Operating System",
        f"{STAMP} {expected['os_marker']}",
        f"{STAMP} ##[endgroup]",
        f"{STAMP} Python {expected['python_marker']}",
        f"{STAMP} [command]git fetch --depth=1 origin +{checkout}:refs/remotes/pull/366/merge",
        f"{STAMP} [command]git log -1 --format=%H",
        f"{STAMP} {checkout}",
        f"{STAMP} ##[group]Run {expected['pytest_command']}",
        f"{STAMP} ##[command]{expected['pytest_command']}",
        f"{STAMP} {summary}",
    ]
    if extra_summary:
        lines.append(f"{STAMP} {extra_summary}")
    return ("\ufeff" + "\n".join(lines) + "\n").encode("utf-8")


class R24Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.expected = {}
        self.logs = {}
        for name, base in r24.EXPECTED.items():
            exp = dict(base)
            data = make_log(exp)
            exp["sha256"] = hashlib.sha256(data).hexdigest()
            exp["bytes"] = len(data)
            exp["timestamp_lines"] = len(data.decode("utf-8-sig").splitlines())
            exp["line_count"] = exp["timestamp_lines"] + 1
            self.expected[name] = exp
            self.logs[name] = data
        self.write_bundle()

    def report_obj(self):
        jobs = []
        for name, exp in self.expected.items():
            samples = []
            for i in (1, 2):
                samples.append({
                    "sample": i,
                    "reason": "LOG_RECEIVED",
                    "local_file": exp["files"][i - 1],
                    "sha256": exp["sha256"],
                    "bytes": exp["bytes"],
                    "checkout_text_present": True,
                    "body_diagnostic": {
                        "format": "TIMESTAMPED_TEXT", "utf8_bom": True,
                        "timestamp_lines": exp["timestamp_lines"], "line_count": exp["line_count"],
                    },
                    "events": [
                        {"stage": "API", "http_status": 302, "location_present": True},
                        {"stage": "STORAGE", "http_status": 200, "location_present": False},
                    ],
                })
            jobs.append({
                "job": name, "job_id": exp["job_id"], "samples": samples,
                "raw_body_correspondence": "MATCH_RAW_BYTES_AT_TWO_READS",
                "correspondence": "MATCH_RAW_BYTES_AT_TWO_READS",
            })
        return {
            "schema": r24.SCHEMA_IN, "repository": r24.REPO, "run_id": r24.RUN_ID,
            "expected_checkout": r24.EXPECTED_CHECKOUT, "authorization_used": True,
            "source_origin": "UNATTESTED_READER_RESPONSES",
            "execution_attestation": "NOT_ESTABLISHED", "merge_authorized": False,
            "memory_admission": False, "trust_activation": False, "status": "UNKNOWN", "jobs": jobs,
        }

    def write_bundle(self):
        for name, exp in self.expected.items():
            for i, filename in enumerate(exp["files"], 1):
                (self.root / filename).write_bytes(self.logs[name])
        (self.root / "LOG_TRANSPORT_REPORT.json").write_text(
            json.dumps(self.report_obj(), indent=2), encoding="utf-8"
        )

    def run_verify(self, expected=None):
        return r24.verify_directory(self.root, expected_map=expected or self.expected)

    def test_baseline_three_jobs_and_six_reads_pass_bounded(self):
        result = self.run_verify()
        self.assertEqual(result["status"], "PASS_BOUNDED")
        self.assertEqual(len(result["checks"]), 3)
        self.assertEqual(sum(x["samples"] for x in result["checks"]), 6)
        self.assertFalse(result["merge_authorized"])
        self.assertEqual(result["execution_attestation"], "NOT_ESTABLISHED")

    def test_one_byte_tamper_is_rejected_by_fixed_sha_pin(self):
        p = self.root / self.expected["m0-regression"]["files"][0]
        raw = bytearray(p.read_bytes()); raw[-2] ^= 1; p.write_bytes(raw)
        with self.assertRaisesRegex(r24.Rejected, "RAW_SHA256_MISMATCH"):
            self.run_verify()

    def test_report_cannot_repin_a_tampered_log(self):
        name = "m0-regression"
        exp = self.expected[name]
        filename = exp["files"][0]
        path = self.root / filename
        raw = bytearray(path.read_bytes()); raw[-2] ^= 1; raw = bytes(raw)
        path.write_bytes(raw)
        report = self.report_obj()
        job = next(x for x in report["jobs"] if x["job"] == name)
        sample = job["samples"][0]
        sample["sha256"] = hashlib.sha256(raw).hexdigest()
        sample["bytes"] = len(raw)
        (self.root / "LOG_TRANSPORT_REPORT.json").write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaisesRegex(r24.Rejected, "report digest/length differs from pinned observation"):
            self.run_verify()

    def test_wrong_commit_is_rejected_even_if_report_digest_is_recomputed(self):
        name = "m0-regression"
        wrong = "0" * 40
        data = make_log(self.expected[name], checkout=wrong)
        exp = dict(self.expected[name], sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                   timestamp_lines=len(data.decode("utf-8-sig").splitlines()),
                   line_count=len(data.decode("utf-8-sig").splitlines()) + 1)
        with self.assertRaisesRegex(r24.Rejected, "WRONG_OR_AMBIGUOUS_FETCH_CHECKOUT"):
            r24.inspect_log(data, exp)

    def test_fake_success_line_is_rejected_even_if_report_digest_is_recomputed(self):
        name = "m0-regression"
        fake = "999999 passed, 0 skipped, 0 warnings, 0 subtests passed in 0.01s"
        data = make_log(self.expected[name], extra_summary=fake)
        exp = dict(self.expected[name], sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                   timestamp_lines=len(data.decode("utf-8-sig").splitlines()),
                   line_count=len(data.decode("utf-8-sig").splitlines()) + 1)
        with self.assertRaisesRegex(r24.Rejected, "TEST_SUMMARY_MISSING_DUPLICATED_OR_FABRICATED"):
            r24.inspect_log(data, exp)

    def test_fabricated_success_replacing_expected_summary_is_rejected(self):
        name = "python-314-differential-advisory"
        fake = "1715 passed, 0 skipped, 0 warnings, 359 subtests passed in 14.14s"
        data = make_log(self.expected[name], summary=fake)
        exp = dict(self.expected[name], sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
        with self.assertRaisesRegex(r24.Rejected, "TEST_SUMMARY_MISSING_DUPLICATED_OR_FABRICATED"):
            r24.inspect_log(data, exp)

    def test_swapped_job_log_is_rejected_by_job_specific_pin(self):
        a = self.expected["m0-regression"]["files"][0]
        b = self.expected["python-314-differential-advisory"]["files"][0]
        (self.root / a).write_bytes((self.root / b).read_bytes())
        with self.assertRaisesRegex(r24.Rejected, "RAW_SHA256_MISMATCH"):
            self.run_verify()

    def test_wrong_job_id_binding_rejected(self):
        report = self.report_obj()
        report["jobs"][0]["job_id"] += 1
        (self.root / "LOG_TRANSPORT_REPORT.json").write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaisesRegex(r24.Rejected, "job id/name binding mismatch"):
            self.run_verify()

    def test_wrong_run_id_rejected(self):
        report = self.report_obj(); report["run_id"] += 1
        (self.root / "LOG_TRANSPORT_REPORT.json").write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaisesRegex(r24.Rejected, "report identity/safety field mismatch: run_id"):
            self.run_verify()

    def test_report_cannot_upgrade_execution_attestation(self):
        report = self.report_obj(); report["execution_attestation"] = "ESTABLISHED"
        (self.root / "LOG_TRANSPORT_REPORT.json").write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaisesRegex(r24.Rejected, "execution_attestation"):
            self.run_verify()

    def test_report_cannot_enable_merge_or_memory(self):
        for field in ("merge_authorized", "memory_admission", "trust_activation"):
            with self.subTest(field=field):
                report = self.report_obj(); report[field] = True
                (self.root / "LOG_TRANSPORT_REPORT.json").write_text(json.dumps(report), encoding="utf-8")
                with self.assertRaisesRegex(r24.Rejected, field):
                    self.run_verify()

    def test_duplicate_json_keys_rejected(self):
        (self.root / "LOG_TRANSPORT_REPORT.json").write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
        with self.assertRaisesRegex(r24.Rejected, "duplicate JSON key"):
            self.run_verify()

    def test_wrong_event_chain_rejected(self):
        report = self.report_obj(); report["jobs"][0]["samples"][0]["events"][1]["http_status"] = 302
        (self.root / "LOG_TRANSPORT_REPORT.json").write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaisesRegex(r24.Rejected, "storage response observation mismatch"):
            self.run_verify()

    def test_mismatched_two_samples_rejected(self):
        p = self.root / self.expected["windows-differential-advisory"]["files"][1]
        p.write_bytes(p.read_bytes() + b" ")
        with self.assertRaisesRegex(r24.Rejected, "RAW_BYTE_LENGTH_MISMATCH|RAW_SHA256_MISMATCH"):
            self.run_verify()

    def test_wrong_python_environment_rejected(self):
        name = "python-314-differential-advisory"
        data = make_log(dict(self.expected[name], python_marker="Python/3.13."))
        exp = dict(self.expected[name], sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                   timestamp_lines=len(data.decode("utf-8-sig").splitlines()),
                   line_count=len(data.decode("utf-8-sig").splitlines()) + 1)
        with self.assertRaisesRegex(r24.Rejected, "PYTHON_VERSION_MARKER_MISSING"):
            r24.inspect_log(data, exp)

    def test_missing_bom_rejected(self):
        name = "m0-regression"
        data = self.logs[name][3:]
        exp = dict(self.expected[name], sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
        with self.assertRaisesRegex(r24.Rejected, "EXPECTED_UTF8_BOM_MISSING"):
            r24.inspect_log(data, exp)

    def test_symlink_log_rejected_when_supported(self):
        name = "m0-regression"; filename = self.expected[name]["files"][0]
        p = self.root / filename; target = self.root / "target.log"
        target.write_bytes(p.read_bytes()); p.unlink()
        try:
            p.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable on this platform")
        with self.assertRaisesRegex(r24.Rejected, "not a regular file"):
            self.run_verify()

    def test_missing_log_returns_unknown(self):
        (self.root / self.expected["m0-regression"]["files"][0]).unlink()
        with self.assertRaisesRegex(r24.Unknown, "evidence file unavailable"):
            self.run_verify()

    def test_report_directory_symlink_rejected_when_supported(self):
        link = self.root.parent / (self.root.name + "-link")
        try:
            link.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("directory symlink creation unavailable")
        self.addCleanup(lambda: link.unlink(missing_ok=True))
        with self.assertRaisesRegex(r24.Rejected, "real directory"):
            r24.verify_directory(link, expected_map=self.expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
