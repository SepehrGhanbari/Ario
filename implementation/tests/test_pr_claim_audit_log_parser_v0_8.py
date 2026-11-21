"""Hallaaj v0.8 independent negative controls for version misattribution.

The first two tests preserve the old v0.7 RED behavior as evidence, but do not
change historic source. All v0.8 tests target conservative diagnostic outputs.
"""
from __future__ import annotations

import unittest

import pr_claim_audit as v01
import pr_claim_audit_log_parser_v0_7 as v07
import pr_claim_audit_log_parser_v0_8 as v08
from test_pr_claim_audit_log_parser_v0_7 import (
    CMD, SETUP, SUMMARY, make_log, claim_text, evidence,
)


class StrictVersionSourceTest(unittest.TestCase):
    def test_baseline_v07_forged_substring_was_false_match(self):
        log = make_log(setup='Some test deliberately prints: Python 3.13.18')
        self.assertEqual(v07.assess(claim_text(), evidence(log))['claim_correspondence'], 'MATCH')

    def test_v08_forged_substring_fail_closed(self):
        log = make_log(setup='Some test deliberately prints: Python 3.13.18')
        result = v08.assess(claim_text(), evidence(log))
        self.assertEqual(result['claim_correspondence'], 'UNKNOWN')
        self.assertIn('python version', result['reason'])
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertEqual(result['execution_attestation'], 'NOT_ESTABLISHED')

    def test_v07_unrelated_doc_line_false_conflict(self):
        log = make_log()+'\nDocumentation: Python 3.12.0 is EOL'
        self.assertEqual(v07.assess(claim_text(), evidence(log))['claim_correspondence'], 'UNKNOWN')

    def test_v08_unrelated_doc_line_ignored(self):
        log = make_log()+'\nDocumentation: Python 3.12.0 is EOL'
        out = v08.assess(claim_text(), evidence(log))
        self.assertEqual(out['claim_correspondence'], 'MATCH')
        self.assertEqual(out['status'], 'UNKNOWN')
        self.assertEqual(out['source_delivery'], 'UNVERIFIED')

    def test_v08_real_setup_python_line_accepted(self):
        parsed = v08.extract_log(make_log())
        self.assertEqual(parsed['python_version'], '3.13.18')
        self.assertEqual(parsed['passed'], 1253)
        self.assertEqual(parsed['skipped'], 2)
        self.assertEqual(parsed['subtests_passed'], 124)

    def test_v08_legacy_full_line_accepted(self):
        legacy = '2026-11-17T16:14:44.0Z Python 3.13.18'
        self.assertEqual(v08.extract_log(make_log(setup=legacy))['python_version'], '3.13.18')

    def test_v08_conflicting_authorized_full_lines_rejected(self):
        log=make_log()+'\nPython 3.12.0'
        out=v08.assess(claim_text(),evidence(log))
        self.assertEqual(out['claim_correspondence'], 'UNKNOWN')
        self.assertEqual(out['reason'], 'missing or conflicting python version in log')
        self.assertIsNone(out['binding'])

    def test_v08_same_version_multiple_authorized_formats_allowed(self):
        log=make_log()+'\nPython 3.13.18'
        self.assertEqual(v08.extract_log(log)['python_version'], '3.13.18')

    def test_v08_setup_marker_with_unrelated_version_does_not_conflict(self):
        for line in ('Release notes for Python 3.12.0',
                     'The test uses CPython (3.12.0) in its example',
                     'Some test deliberately prints: Python 3.12.0'):
            with self.subTest(line=line):
                self.assertEqual(v08.extract_log(make_log()+'\n'+line)['python_version'], '3.13.18')

    def test_v08_no_valid_version_line_downgrades(self):
        for line in ('Setup says Python 3.13.18',
                     'Successfully set up CPython (3.13.18) extra',
                     'CPython (3.13.18)',
                     'CPython 3.13.18',
                     'Python 3.13.18 (user-provided text)',
                     '   ',
                     'A Python 3.13.18'):
            with self.subTest(line=line):
                with self.assertRaisesRegex(v01.Invalid, 'python version'):
                    v08.extract_log(make_log(setup=line))

    def test_v08_ansi_and_timestamp_normalized_for_known_setup(self):
        setup = '2026-11-17T16:14:44.0507715Z \x1b[32mSuccessfully set up CPython (3.13.18)\x1b[0m'
        self.assertEqual(v08.extract_log(make_log(setup=setup))['python_version'], '3.13.18')

    def test_v08_unknown_summary_term_downgrades(self):
        log=make_log(summary=SUMMARY.replace('2 warnings','2 suspicious'))
        self.assertEqual(v08.assess(claim_text(),evidence(log))['claim_correspondence'],'UNKNOWN')

    def test_v08_duplicate_counter_key_is_rejected_even_when_same_value(self):
        log=make_log(summary=SUMMARY.replace('2 skipped','1253 passed, 2 skipped'))
        out=v08.assess(claim_text(),evidence(log))
        self.assertEqual(out['claim_correspondence'],'UNKNOWN')
        self.assertIn('duplicate',out['reason'])

    def test_v08_invalid_hash_remains_unknown(self):
        raw=make_log();ev=evidence(raw);ev['job_log_sha256']='0'*64
        out=v08.assess(claim_text(),ev)
        self.assertEqual(out['status'],'UNKNOWN')
        self.assertEqual(out['claim_correspondence'],'UNKNOWN')
        self.assertIn('digest mismatch',out['reason'])

    def test_v08_mismatching_claim_is_diagnostic_mismatch_only(self):
        out=v08.assess(claim_text(passed=1254),evidence())
        self.assertEqual(out['claim_correspondence'],'MISMATCH')
        self.assertEqual(out['differences'],['passed'])
        self.assertEqual(out['status'],'UNKNOWN')
        self.assertEqual(out['execution_attestation'],'NOT_ESTABLISHED')

    def test_v08_fabricated_complete_line_still_not_provenance(self):
        # A complete line can itself be printed by an attacker. This parser
        # deliberately cannot determine the *source* of such text.
        fake = make_log(setup='Python 3.13.18')
        result=v08.assess(claim_text(),evidence(fake))
        self.assertEqual(result['claim_correspondence'],'MATCH')
        self.assertEqual(result['status'],'UNKNOWN')
        self.assertEqual(result['source_delivery'],'UNVERIFIED')
        self.assertEqual(result['execution_attestation'],'NOT_ESTABLISHED')

    def test_v08_conflicting_setup_lines_downgrade(self):
        s = make_log()+'\nSuccessfully set up CPython (3.12.0)'
        with self.assertRaisesRegex(v01.Invalid,'conflicting python version'):
            v08.extract_log(s)

    def test_v08_duplicate_command_downgrades(self):
        with self.assertRaisesRegex(v01.Invalid,'exactly one pytest invocation'):
            v08.extract_log(make_log()+'\n'+CMD)


if __name__=='__main__':
    unittest.main()
