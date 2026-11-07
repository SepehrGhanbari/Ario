"""Explicit adversarial two-world fixtures; no devices, API or money involved."""
import unittest
from dataclasses import dataclass
from claim_model import ReceiptObservation, ExternalFixture, Verdict, CLAIMS, evaluate, local_pilot_admission


@dataclass(frozen=True)
class HiddenWorld:
    public: ReceiptObservation
    hidden_controller: str
    actual_usable_delivery: bool


class EpistemicEconomyTests(unittest.TestCase):
    def setUp(self):
        self.observed = ReceiptObservation(
            tuple(f"slot-{i:02d}" for i in range(40)), signed_receipts=40,
            output_check=True, self_reported_delivery=True, self_reported_demand=True)

    def test_40_signed_receipts_do_not_prove_demand_delivery_or_control(self):
        verdict = evaluate(self.observed)
        self.assertEqual(verdict['OUTPUT_CORRECT'], Verdict.MOCK_CORRECT)
        self.assertTrue(all(verdict[k] == Verdict.UNKNOWN for k in CLAIMS if k != 'OUTPUT_CORRECT'))

    def test_two_hidden_worlds_same_inputs_same_policy_verdict(self):
        # World H: independent need/delivery; C: all roles are controlled by
        # one principal. Neither hidden truth is allowed into policy input.
        honest = HiddenWorld(self.observed, 'separate', True)
        captured = HiddenWorld(self.observed, 'common-controller', False)
        self.assertNotEqual(honest.hidden_controller, captured.hidden_controller)
        self.assertNotEqual(honest.actual_usable_delivery, captured.actual_usable_delivery)
        self.assertEqual(honest.public, captured.public)
        self.assertEqual(evaluate(honest.public), evaluate(captured.public))
        self.assertEqual(evaluate(captured.public)['DELIVERED_USABLE_SUPPORT'], Verdict.UNKNOWN)

    def test_different_40_ids_do_not_establish_40_useful_outcomes(self):
        self.assertEqual(len(set(self.observed.slot_ids)), 40)
        self.assertEqual(evaluate(self.observed)['EXTERNALLY_VALUED_DEMAND'], Verdict.UNKNOWN)

    def test_claimed_delivery_is_not_observed_delivery(self):
        self.assertEqual(evaluate(self.observed)['DELIVERED_USABLE_SUPPORT'], Verdict.UNKNOWN)

    def test_observer_signature_without_separation_still_unknown(self):
        fixture = ExternalFixture(consented_observation=True, observer_separation_evidenced=None,
                                  usable_delivery_observed=True)
        self.assertEqual(evaluate(self.observed, fixture)['DELIVERED_USABLE_SUPPORT'], Verdict.UNKNOWN)

    def test_delivery_positive_is_only_conditional_on_synthetic_external_evidence(self):
        fixture = ExternalFixture(consented_observation=True, observer_separation_evidenced=True,
                                  usable_delivery_observed=True)
        self.assertEqual(evaluate(self.observed, fixture)['DELIVERED_USABLE_SUPPORT'], Verdict.FIXTURE_CONDITIONAL)

    def test_explicit_non_delivery_refutes_delivery_when_consented(self):
        f = ExternalFixture(consented_observation=True, usable_delivery_observed=False)
        self.assertEqual(evaluate(self.observed, f)['DELIVERED_USABLE_SUPPORT'], Verdict.REFUTED)

    def test_refusal_to_be_observed_is_not_fraud(self):
        f = ExternalFixture(consented_observation=False, usable_delivery_observed=None)
        self.assertEqual(evaluate(self.observed, f)['DELIVERED_USABLE_SUPPORT'], Verdict.UNKNOWN)

    def test_fabricated_demand_can_refute_without_punishing_worker(self):
        f = ExternalFixture(independent_origin_evidenced=False)
        verdict = evaluate(self.observed, f)
        self.assertEqual(verdict['REQUEST_INDEPENDENT'], Verdict.REFUTED)
        self.assertEqual(verdict['OUTPUT_CORRECT'], Verdict.MOCK_CORRECT)

    def test_independence_does_not_prove_external_usefulness(self):
        f = ExternalFixture(independent_origin_evidenced=True)
        v = evaluate(self.observed, f)
        self.assertEqual(v['REQUEST_INDEPENDENT'], Verdict.FIXTURE_CONDITIONAL)
        self.assertEqual(v['EXTERNALLY_VALUED_DEMAND'], Verdict.UNKNOWN)

    def test_true_need_without_funding_still_not_a_wage(self):
        f = ExternalFixture(externally_valued_need_evidenced=True)
        self.assertEqual(evaluate(self.observed, f)['EXTERNALLY_VALUED_DEMAND'], Verdict.FIXTURE_CONDITIONAL)
        self.assertNotIn('GUARANTEED_INCOME', CLAIMS)

    def test_control_does_not_follow_from_phone_account_or_receipt(self):
        self.assertEqual(evaluate(self.observed)['BENEFICIARY_CONTROL'], Verdict.UNKNOWN)
        f = ExternalFixture(voluntary_control_evidenced=False)
        self.assertEqual(evaluate(self.observed, f)['BENEFICIARY_CONTROL'], Verdict.REFUTED)

    def test_zero_or_negative_net_weak_device_benefit_is_not_positive(self):
        f = ExternalFixture(participant_valued_benefit=3, energy_data_time_wear_cost=5)
        self.assertEqual(evaluate(self.observed, f)['NET_WEAK_DEVICE_BENEFIT'], Verdict.REFUTED)
        f2 = ExternalFixture(participant_valued_benefit=5, energy_data_time_wear_cost=5)
        self.assertEqual(evaluate(self.observed, f2)['NET_WEAK_DEVICE_BENEFIT'], Verdict.REFUTED)

    def test_positive_net_benefit_only_under_fixture_assumptions(self):
        f = ExternalFixture(participant_valued_benefit=6, energy_data_time_wear_cost=4)
        self.assertEqual(evaluate(self.observed, f)['NET_WEAK_DEVICE_BENEFIT'], Verdict.FIXTURE_CONDITIONAL)

    def test_missing_cost_is_unknown(self):
        f = ExternalFixture(participant_valued_benefit=4)
        self.assertEqual(evaluate(self.observed, f)['NET_WEAK_DEVICE_BENEFIT'], Verdict.UNKNOWN)

    def test_duplicate_ids_are_refused_not_double_counted(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            evaluate(ReceiptObservation(('a','a'), signed_receipts=2))

    def test_illogical_receipt_count_refused(self):
        with self.assertRaises(ValueError):
            evaluate(ReceiptObservation(('a',), signed_receipts=2))

    def test_missing_sensor_or_stop_refuses_device_pilot(self):
        for kw in [
            dict(opted_in=False, has_enforceable_stop=True, sensor_fresh=True, within_heat_battery_data_budget=True),
            dict(opted_in=True, has_enforceable_stop=False, sensor_fresh=True, within_heat_battery_data_budget=True),
            dict(opted_in=True, has_enforceable_stop=True, sensor_fresh=None, within_heat_battery_data_budget=True),
            dict(opted_in=True, has_enforceable_stop=True, sensor_fresh=True, within_heat_battery_data_budget=None),
            dict(opted_in=True, has_enforceable_stop=True, sensor_fresh=True, within_heat_battery_data_budget=False),
        ]:
            with self.subTest(kw=kw):
                self.assertEqual(local_pilot_admission(**kw), 'REFUSE_OR_STOP')

    def test_fully_safe_mock_still_does_not_authorize_real_device(self):
        self.assertEqual(local_pilot_admission(opted_in=True, has_enforceable_stop=True,
            sensor_fresh=True, within_heat_battery_data_budget=True),
            'TOY_ELIGIBLE_NOT_AUTHORIZED_TO_RUN')

    def test_invalid_cost_values_refused(self):
        for cost in [-1, float('nan'), float('inf')]:
            with self.subTest(cost=cost):
                with self.assertRaises(ValueError):
                    evaluate(self.observed, ExternalFixture(participant_valued_benefit=2,
                                                           energy_data_time_wear_cost=cost))


if __name__ == '__main__':
    unittest.main()
