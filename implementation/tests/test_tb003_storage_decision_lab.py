"""Diagnostic tests, independent of original TB-003 v0.1 evaluator contract."""
import unittest

from tb003_storage_decision_lab import inspect_separation


class TB003StorageOverlayTests(unittest.TestCase):
    def test_shared_storage_and_unknown_admin_are_both_visible(self):
        r = inspect_separation(administrative_status="UNKNOWN",
                               storage_status="SAME_STORAGE_OBJECT")
        self.assertEqual(r.storage_status, "SAME_STORAGE_OBJECT")
        self.assertEqual(r.administrative_status, "UNKNOWN")
        self.assertEqual(r.proposed_inference, "BLOCK_SEPARATION_KNOWN_SHARED_STORAGE")

    def test_shared_storage_overrides_inconsistent_positive_admin_only_in_overlay(self):
        r = inspect_separation(administrative_status="LAB_CONDITIONALLY_SEPARATE",
                               storage_status="SAME_STORAGE_OBJECT")
        self.assertEqual(r.proposed_inference, "BLOCK_SEPARATION_KNOWN_SHARED_STORAGE")

    def test_common_control_detected_blocks_independence(self):
        r = inspect_separation(administrative_status="COMMON_CONTROL_DETECTED",
                               storage_status="LAB_DISTINCT_OBJECTS")
        self.assertEqual(r.proposed_inference, "BLOCK_SEPARATION_KNOWN_CONTROL_OR_COMPROMISE")

    def test_explicit_compromise_blocks_independence(self):
        r = inspect_separation(administrative_status="COMPROMISED_BY_SCENARIO",
                               storage_status="LAB_DISTINCT_OBJECTS")
        self.assertEqual(r.proposed_inference, "BLOCK_SEPARATION_KNOWN_CONTROL_OR_COMPROMISE")

    def test_unknown_admin_with_distinct_store_still_blocks(self):
        r = inspect_separation(administrative_status="UNKNOWN",
                               storage_status="LAB_DISTINCT_OBJECTS")
        self.assertEqual(r.proposed_inference, "BLOCK_SEPARATION_UNKNOWN")

    def test_clean_lab_model_never_grants_production_authority(self):
        r = inspect_separation(administrative_status="LAB_CONDITIONALLY_SEPARATE",
                               storage_status="LAB_DISTINCT_OBJECTS")
        self.assertEqual(r.proposed_inference, "LAB_CONDITIONAL_ONLY_NEVER_PRODUCTION_AUTHORITY")
        self.assertEqual(r.m0_admission, "NOT_EVALUATED")
        self.assertEqual(r.production_authentication, "NOT_ESTABLISHED")

    def test_unknown_new_labels_fail_closed(self):
        r = inspect_separation(administrative_status="NEW_LABEL", storage_status="NEW_STORAGE")
        self.assertEqual(r.proposed_inference, "BLOCK_SEPARATION_UNKNOWN")


if __name__ == "__main__":
    unittest.main()
