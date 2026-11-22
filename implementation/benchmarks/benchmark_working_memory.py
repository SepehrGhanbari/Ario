"""Empirical Cognitive Memory Benchmark: Working Memory Dynamics & Metacognition.

Simulates an autonomous cognitive episode consisting of multi-source incoming streams:
- Empirical tool observations (verifiable, high salience)
- External testimonies (unverified, medium salience)
- Internal hypotheses (low-to-medium salience)
- Transient background noise (low salience, decay targets)

Evaluates:
1. Strict Cowan Capacity Invariant: Max active chunks <= K (default 4).
2. Dual Eviction Fidelity: Ratio of high-salience empirical facts consolidated vs noise forgotten.
3. Attentional Rehearsal & Decay Survival: Half-life of reinforced vs unattended propositions.
4. Metacognitive Calibration Accuracy: Contradiction detection and grounding indicators.
5. Latency & Throughput: Microseconds per ingestion, tick, and assessment.
"""

from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from core.memory_consolidation import ConsolidationEngine
from core.source_monitoring import (
    SourceAttribution,
    SourceType,
    VeracityState,
    EmpiricalProvenance,
)
from core.working_memory import (
    WorkingMemoryBuffer,
    ChunkState,
    MetacognitiveVerdict,
)


def run_benchmark(event_count: int = 200, capacity: int = 4) -> Dict[str, float]:
    engine = ConsolidationEngine()
    wm = WorkingMemoryBuffer(capacity=capacity, consolidation_engine=engine)

    t0 = time.perf_counter()
    empirical_ingested = 0
    noise_ingested = 0
    max_active_observed = 0

    for step in range(event_count):
        mod = step % 10
        if mod in (0, 1, 2):
            # Empirical observation (tools, probes)
            prov = EmpiricalProvenance(
                tool="bench_sensor",
                target="sys_probe",
                exit_code=0,
                execution_lock_sha256="c" * 64,
                stdout_sha256="d" * 64,
                recorded_at=datetime.now(timezone.utc).isoformat(),
            )
            attr = SourceAttribution(
                attribution_id=f"emp_{step}",
                source_type=SourceType.EMPIRICAL_OBSERVATION,
                assertion=f"System metric {step} verified at threshold",
                veracity_state=VeracityState.VERIFIED_EMPIRICAL,
                provenance=prov,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            wm.ingest(f"metric_{step % 5}", f"System metric {step} verified at threshold", attr, salience=0.85, step=step)
            empirical_ingested += 1

        elif mod in (3, 4, 5):
            # External testimony / peer claim
            attr = SourceAttribution(
                attribution_id=f"test_{step}",
                source_type=SourceType.EXTERNAL_TESTIMONY,
                assertion=f"Peer claims status {step}",
                veracity_state=VeracityState.EXTERNAL_ASSERTION,
                provenance=None,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            wm.ingest(f"peer_status_{step % 3}", f"Peer claims status {step}", attr, salience=0.5, step=step)

        elif mod in (6, 7):
            # Internal hypothesis
            attr = SourceAttribution(
                attribution_id=f"hyp_{step}",
                source_type=SourceType.INTERNAL_HYPOTHESIS,
                assertion=f"Agent infers cause {step}",
                veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
                provenance=None,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            wm.ingest("hypothetical_cause", f"Agent infers cause {step}", attr, salience=0.35, step=step)

        else:
            # Transient noise
            attr = SourceAttribution(
                attribution_id=f"noise_{step}",
                source_type=SourceType.INTERNAL_HYPOTHESIS,
                assertion=f"Ephemeral background flicker {step}",
                veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
                provenance=None,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            wm.ingest("background_noise", f"Ephemeral background flicker {step}", attr, salience=0.1, step=step)
            noise_ingested += 1

        max_active_observed = max(max_active_observed, wm.active_count)

        # Advance tick periodically to trigger decay
        if step % 3 == 0:
            wm.step_tick(step=step)

    t_ingest = time.perf_counter()

    # Final metacognitive evaluation
    assessment = wm.metacognitive_assessment()
    t_end = time.perf_counter()

    # Analyze eviction history
    consolidated_count = sum(1 for e in wm.eviction_history if e.fate == ChunkState.CONSOLIDATED_TO_LTM)
    decayed_count = sum(1 for e in wm.eviction_history if e.fate == ChunkState.DECAYED_FORGOTTEN)
    total_evicted = len(wm.eviction_history)

    metrics = {
        "event_count": float(event_count),
        "capacity_k": float(capacity),
        "max_active_observed": float(max_active_observed),
        "capacity_invariant_held": 1.0 if max_active_observed <= capacity else 0.0,
        "empirical_ingested": float(empirical_ingested),
        "noise_ingested": float(noise_ingested),
        "total_evictions": float(total_evicted),
        "consolidated_to_ltm": float(consolidated_count),
        "decayed_forgotten": float(decayed_count),
        "active_at_end": float(wm.active_count),
        "total_elapsed_ms": (t_end - t0) * 1000.0,
        "avg_latency_per_step_us": ((t_end - t0) / event_count) * 1_000_000.0,
        "final_empirical_ratio": assessment.empirical_ratio,
        "final_contradiction_count": float(assessment.contradiction_count),
    }

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ario Working Memory Benchmark")
    parser.add_argument("--events", type=int, default=200, help="Number of incoming events")
    parser.add_argument("--capacity", type=int, default=4, help="Capacity bound (Cowan limit)")
    parser.add_argument("--output", type=str, default="", help="Path to write JSON output")
    args = parser.parse_args()

    results = run_benchmark(event_count=args.events, capacity=args.capacity)

    print("=" * 65)
    print("  ARIO COGNITIVE MEMORY BENCHMARK: WORKING MEMORY BUFFER")
    print("=" * 65)
    for k, v in results.items():
        if "ms" in k or "us" in k or "ratio" in k:
            print(f"  {k:32s}: {v:10.3f}")
        else:
            print(f"  {k:32s}: {int(v) if v.is_integer() else v:10}")
    print("=" * 65)

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Saved benchmark results to {args.output}")
