"""Automated verification of Working Memory Benchmark invariants."""

from benchmarks.benchmark_working_memory import run_benchmark


def test_benchmark_invariants():
    metrics = run_benchmark(event_count=100, capacity=4)

    assert metrics["capacity_invariant_held"] == 1.0
    assert metrics["max_active_observed"] <= 4.0
    assert metrics["active_at_end"] <= 4.0
    assert metrics["total_evictions"] > 0
    assert metrics["consolidated_to_ltm"] > 0
    assert metrics["decayed_forgotten"] > 0
    assert metrics["avg_latency_per_step_us"] < 2000.0  # Must be faster than 2ms per step
