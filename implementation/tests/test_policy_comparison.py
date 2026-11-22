"""Smoke tests for synthetic, multi-scenario working-memory comparisons."""

from benchmarks.policy_comparison import evaluate_scenario, run_all_scenarios


def test_all_scenarios_report_bounded_and_bounded_metrics():
    results = run_all_scenarios(n_events=80, capacity=4, seed=7)
    assert set(results) == {
        "STANDARD_BALANCED",
        "EPISTEMIC_FLOODING",
        "EVIDENCE_COMPETITION",
        "TEMPORAL_LONGEVITY",
    }
    for scenario in results.values():
        assert set(scenario) == {"FIFO", "LRU", "RANDOM", "ARIO_COGNITIVE"}
        for policy in scenario.values():
            assert policy["cowan_capacity_held"] is True
            assert 0 <= policy["empirical_preservation_rate"] <= 1
            assert 0 <= policy["avg_active_salience"] <= 1
            rate = policy["noise_rejection_rate"]
            assert rate is None or 0 <= rate <= 1


def test_scenario_with_no_noise_reports_not_applicable():
    results = evaluate_scenario("EVIDENCE_COMPETITION", n_events=60, capacity=4, seed=19)
    assert all(policy["noise_rejection_rate"] is None for policy in results.values())


def test_policy_results_reproduce_for_same_seed():
    first = run_all_scenarios(n_events=60, capacity=4, seed=123)
    second = run_all_scenarios(n_events=60, capacity=4, seed=123)
    assert first == second
