"""Development-only deterministic RED/GREEN tests for pinned TB-003 observations."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import replace
from unittest.mock import patch

import w1_adversarial_input_sensitivity_v1 as w


class TestW1InputSensitivity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine=w.load_pinned_engine()
        cls.trials={t.name:t for t in w.build_trials(cls.engine)}

    def status(self,name):
        return w.classify(self.engine,self.trials[name].case)["classification"]

    def test_exact_source_pin(self):
        self.assertEqual(w.EXPECTED_GIT_BLOB,"4faf010d73219af63c254097e9c135da68d60078")
        self.assertEqual(w.load_pinned_engine().PROFILE,self.engine.PROFILE)

    def test_tampered_source_rejected_before_exec(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/"implementation";folder.mkdir()
            src=Path(__file__).resolve().parents[2]/"implementation"/"witness_provenance_experiment.py"
            raw=src.read_bytes()
            # Same size; independent SHA verification must fail.
            changed=raw.replace(b"ARIO-TB-003",b"ARIO-TB-004",1)
            self.assertEqual(len(changed),len(raw))
            (folder/"witness_provenance_experiment.py").write_bytes(changed)
            with self.assertRaisesRegex(ValueError,"SHA256_MISMATCH"):
                w.load_pinned_engine(Path(d))

    def test_oversized_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/"implementation"; folder.mkdir()
            (folder/"witness_provenance_experiment.py").write_bytes(b"x"*65537)
            with self.assertRaisesRegex(ValueError,"SIZE_MISMATCH"):
                w.load_pinned_engine(Path(d))

    def test_honest_controls_detected(self):
        self.assertEqual(self.status("honest-separate"),"CONDITIONAL")
        for n in ("honest-shared-source","honest-shared-admin","honest-shared-source-and-admin"):
            with self.subTest(n=n): self.assertEqual(self.status(n),"DEPENDENT")

    def test_hidden_dependencies_turn_into_conditional(self):
        for n in ("hidden-source-false-complete","hidden-admin-false-complete","hidden-source-admin-false-complete"):
            with self.subTest(n=n): self.assertEqual(self.status(n),"CONDITIONAL")

    def test_declared_incompleteness_holds_unknown(self):
        for n in ("hidden-source-incomplete","hidden-admin-incomplete","separate-incomplete-control","separate-incomplete-source"):
            with self.subTest(n=n): self.assertEqual(self.status(n),"UNKNOWN")

    def test_same_observed_graph_ambiguous_truth(self):
        reference=w.serialize_case(self.trials["honest-separate"].case)
        for n in ("hidden-source-false-complete","hidden-admin-false-complete","hidden-source-admin-false-complete"):
            with self.subTest(n=n):
                self.assertEqual(w.serialize_case(self.trials[n].case),reference)
                self.assertNotEqual(self.trials[n].latent_relation,self.trials["honest-separate"].latent_relation)

    def test_candidate_supplied_origin_fails_closed(self):
        self.assertEqual(self.status("candidate-claims-complete"),"UNKNOWN")

    def test_aliased_source_nodes_detected(self):
        self.assertEqual(self.status("source-alias-identity"),"DEPENDENT")

    def test_duplication_and_missing_custody_not_promoted(self):
        self.assertEqual(self.status("duplicate-witness"),"UNKNOWN")
        self.assertEqual(self.status("missing-custody-transfer"),"UNKNOWN")

    def test_untrusted_self_claim_not_new_witness(self):
        out=w.classify(self.engine,self.trials["untrusted-self-certification"].case)
        self.assertEqual(out["classification"],"CONDITIONAL")
        self.assertIn("UNSUPPORTED_CLAIM:self",out["reason_codes"])

    def test_no_operational_authority(self):
        for tr in self.trials.values():
            r=w.classify(self.engine,tr.case)
            self.assertEqual(r["safety"]["production_custody_authenticity"],"NOT_ESTABLISHED")
            self.assertEqual(r["safety"]["human_authorization"],"NOT_EVALUATED")
            self.assertEqual(r["safety"]["evidence_admission"],"NOT_EVALUATED")

    def test_order_permutation_metamorphism(self):
        self.assertEqual(w.permutation_checks(self.engine,list(self.trials.values()),rounds=12),192)

    def test_aggregate_does_not_infer_population_accuracy(self):
        report=w.run()
        self.assertEqual(report["aggregate"],{
             "designed_trials":16,"development_expectation_matches":16,
             "permutation_checks":192,"hidden_dependency_conditional":3,
             "hidden_dependency_trials":3})
        self.assertEqual(report["scientific_status"],"AUTHOR_BUILT_DEVELOPMENT_FIXTURES_NOT_BLINDED_OR_INDEPENDENT")

    def test_mutant_detector_proves_test_is_sensitive(self):
        original=w.classify
        def bad(p,case):
            z=original(p,case)
            if z["classification"]=="UNKNOWN":
                z={**z,"classification":"CONDITIONAL"}
            return z
        with patch.object(w,"classify",side_effect=bad):
            with self.assertRaisesRegex(AssertionError,"DEVELOPMENT_REGRESSION"):
                w.evaluate_trials(self.engine)


if __name__=="__main__":
    unittest.main()
