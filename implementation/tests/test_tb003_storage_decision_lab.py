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


    def test_actual_v01_evaluator_retains_shared_storage_with_incomplete_control(self):
        # Load the repository's frozen LAB fixtures, not a fabricated result.
        import importlib.util
        from dataclasses import replace
        from pathlib import Path
        path = Path(__file__).with_name("test_witness_provenance_experiment.py")
        spec = importlib.util.spec_from_file_location("_tb003_existing_lab_fixtures", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        fixtures = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixtures)
        case = fixtures.replace_node(fixtures.baseline(), "store-b",
                                     object_identity="DISK-A")
        case = replace(case, complete_control_surface=False)
        original = fixtures.check(case)
        self.assertEqual(original.storage_separation.status, "SAME_STORAGE_OBJECT")
        self.assertEqual(original.administrative_separation.status, "UNKNOWN")
        decision = inspect_separation(
            administrative_status=original.administrative_separation.status,
            storage_status=original.storage_separation.status)
        self.assertEqual(decision.proposed_inference,
                         "BLOCK_SEPARATION_KNOWN_SHARED_STORAGE")
        self.assertEqual(original.production_custody_authenticity, "NOT_ESTABLISHED")

    def test_actual_v01_evaluator_complete_storage_alias_control(self):
        import importlib.util
        from pathlib import Path
        path = Path(__file__).with_name("test_witness_provenance_experiment.py")
        spec = importlib.util.spec_from_file_location("_tb003_existing_control_fixture", path)
        fixtures = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixtures)
        case = fixtures.replace_node(fixtures.baseline(), "store-b",
                                     object_identity="DISK-A")
        result = fixtures.check(case)
        self.assertEqual(result.storage_separation.status, "SAME_STORAGE_OBJECT")
        self.assertEqual(result.administrative_separation.status, "COMMON_CONTROL_DETECTED")
        decision = inspect_separation(
            administrative_status=result.administrative_separation.status,
            storage_status=result.storage_separation.status)
        self.assertEqual(decision.proposed_inference,
                         "BLOCK_SEPARATION_KNOWN_SHARED_STORAGE")


if __name__ == "__main__":
    unittest.main()
