"""Comparative Benchmark: Eviction Policies vs Ario Cognitive Working Memory.

Evaluates four eviction policies under distinct cognitive operational scenarios:
1. FIFO (First In, First Out)
2. LRU (Least Recently Used)
3. RANDOM (Uniform random replacement)
4. ARIO_COGNITIVE (WorkingMemoryBuffer: Salience + Provenance Protection + Adaptive Decay)

Scenarios:
- Scenario 1: Standard Balanced Cognitive Stream
- Scenario 2: Epistemic Flooding (Adversarial High-Frequency Noise Bursts)
- Scenario 3: Evidence Competition (Contradiction Pressure & Conflicting Claims)
- Scenario 4: Temporal Longevity (Extended Horizon with Temporal Decay & Rehearsal)

Metrics evaluated:
- Active Empirical Count: Ground-truth empirical observations actively maintained in WM.
- Total Empirical Preserved: Empirical observations preserved in active WM or safely consolidated into LTM.
- Empirical Preservation Rate: Ratio of unique ingested empirical observations preserved.
- Noise Filtering Rate: Ratio of transient sensory noise discarded without corrupting long-term memory.
- Active Attentional Quality: Average salience of chunks residing in active working memory.
- Strict Cowan Compliance: Max active chunks <= K (default 4).
"""

from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
import json
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.memory_consolidation import ConsolidationEngine
from core.source_monitoring import (
    SourceAttribution,
    SourceType,
    VeracityState,
    EmpiricalProvenance,
)
from core.working_memory import WorkingMemoryBuffer, ChunkState


def _make_empirical(i: int, concept: str) -> Tuple[str, str, SourceAttribution, float]:
    prov = EmpiricalProvenance(
        tool="net_sensor",
        target="endpoint",
        exit_code=0,
        execution_lock_sha256="e" * 64,
        stdout_sha256="f" * 64,
        recorded_at=datetime.now(timezone.utc).isoformat(),
    )
    attr = SourceAttribution(
        attribution_id=f"emp_{i}",
        source_type=SourceType.EMPIRICAL_OBSERVATION,
        assertion=f"Verified empirical condition {i}",
        veracity_state=VeracityState.VERIFIED_EMPIRICAL,
        provenance=prov,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    return (concept, f"Verified empirical condition {i}", attr, 0.85)


def _make_testimony(i: int, concept: str) -> Tuple[str, str, SourceAttribution, float]:
    attr = SourceAttribution(
        attribution_id=f"ext_{i}",
        source_type=SourceType.EXTERNAL_TESTIMONY,
        assertion=f"Peer testimony claim {i}",
        veracity_state=VeracityState.EXTERNAL_ASSERTION,
        provenance=None,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    return (concept, f"Peer testimony claim {i}", attr, 0.50)


def _make_hypothesis(i: int, concept: str) -> Tuple[str, str, SourceAttribution, float]:
    attr = SourceAttribution(
        attribution_id=f"hyp_{i}",
        source_type=SourceType.INTERNAL_HYPOTHESIS,
        assertion=f"Speculative hypothesis {i}",
        veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
        provenance=None,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    return (concept, f"Speculative hypothesis {i}", attr, 0.30)


def _make_noise(i: int) -> Tuple[str, str, SourceAttribution, float]:
    attr = SourceAttribution(
        attribution_id=f"noise_{i}",
        source_type=SourceType.INTERNAL_HYPOTHESIS,
        assertion=f"Transient background flicker {i}",
        veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
        provenance=None,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    return ("transient_noise", f"Transient background flicker {i}", attr, 0.05)


def generate_scenario_stream(scenario: str, n_events: int = 150, seed: int = 42) -> List[Tuple[str, str, SourceAttribution, float]]:
    rng = random.Random(seed)
    stream = []

    if scenario == "STANDARD_BALANCED":
        # 35% empirical, 30% testimony, 20% hypothesis, 15% noise
        for i in range(n_events):
            r = rng.random()
            if r < 0.35:
                stream.append(_make_empirical(i, f"endpoint_{i % 5}"))
            elif r < 0.65:
                stream.append(_make_testimony(i, f"peer_{i % 4}"))
            elif r < 0.85:
                stream.append(_make_hypothesis(i, f"concept_{i % 3}"))
            else:
                stream.append(_make_noise(i))

    elif scenario == "EPISTEMIC_FLOODING":
        # 70% sensory noise burst, 15% empirical, 15% testimony
        for i in range(n_events):
            r = rng.random()
            if r < 0.70:
                stream.append(_make_noise(i))
            elif r < 0.85:
                stream.append(_make_empirical(i, f"core_service_{i % 3}"))
            else:
                stream.append(_make_testimony(i, f"peer_{i % 3}"))

    elif scenario == "EVIDENCE_COMPETITION":
        # 50% high-salience empirical facts vs 50% unverified claims/hypotheses sharing 3 concepts
        for i in range(n_events):
            target_concept = f"shared_target_{i % 3}"
            if rng.random() < 0.50:
                stream.append(_make_empirical(i, target_concept))
            else:
                if rng.random() < 0.50:
                    stream.append(_make_testimony(i, target_concept))
                else:
                    stream.append(_make_hypothesis(i, target_concept))

    elif scenario == "TEMPORAL_LONGEVITY":
        # Extended operational stream with rehearsal and decay over 10 concepts
        for i in range(n_events):
            r = rng.random()
            if r < 0.30:
                stream.append(_make_empirical(i, f"long_state_{i % 4}"))
            elif r < 0.60:
                stream.append(_make_testimony(i, f"peer_state_{i % 4}"))
            elif r < 0.80:
                stream.append(_make_hypothesis(i, f"hypo_state_{i % 3}"))
            else:
                stream.append(_make_noise(i))

    else:
        raise ValueError(f"Unknown scenario: {scenario}")

    return stream


class BaselineFIFOBuffer:
    def __init__(self, capacity: int = 4):
        self.capacity = capacity
        self.active: List[Tuple[str, str, SourceAttribution, float]] = []
        self.evictions: List[Tuple[str, str, SourceAttribution, float]] = []

    def ingest(self, concept, assertion, attr, salience):
        if len(self.active) >= self.capacity:
            victim = self.active.pop(0)
            self.evictions.append(victim)
        self.active.append((concept, assertion, attr, salience))


class BaselineLRUBuffer:
    def __init__(self, capacity: int = 4):
        self.capacity = capacity
        self.active: Dict[str, Tuple[str, str, SourceAttribution, float, int]] = {}
        self.evictions: List[Tuple[str, str, SourceAttribution, float]] = []
        self.tick = 0

    def ingest(self, concept, assertion, attr, salience):
        self.tick += 1
        key = f"{concept}:{assertion}"
        if key in self.active:
            old = self.active[key]
            self.active[key] = (old[0], old[1], old[2], salience, self.tick)
            return

        if len(self.active) >= self.capacity:
            oldest_key = min(self.active.keys(), key=lambda k: self.active[k][4])
            victim = self.active.pop(oldest_key)
            self.evictions.append((victim[0], victim[1], victim[2], victim[3]))

        self.active[key] = (concept, assertion, attr, salience, self.tick)


class BaselineRandomBuffer:
    def __init__(self, capacity: int = 4, seed: int = 42):
        self.capacity = capacity
        self.active: List[Tuple[str, str, SourceAttribution, float]] = []
        self.evictions: List[Tuple[str, str, SourceAttribution, float]] = []
        self.rng = random.Random(seed)

    def ingest(self, concept, assertion, attr, salience):
        if len(self.active) >= self.capacity:
            idx = self.rng.randint(0, len(self.active) - 1)
            victim = self.active.pop(idx)
            self.evictions.append(victim)
        self.active.append((concept, assertion, attr, salience))


def evaluate_scenario(scenario: str, n_events: int = 200, capacity: int = 4, seed: int = 42) -> Dict[str, Dict[str, Any]]:
    stream = generate_scenario_stream(scenario=scenario, n_events=n_events, seed=seed)
    empirical_total = len({item[1] for item in stream if item[2].veracity_state == VeracityState.VERIFIED_EMPIRICAL})
    empirical_assertions = {item[1] for item in stream if item[2].veracity_state == VeracityState.VERIFIED_EMPIRICAL}
    noise_assertions = {item[1] for item in stream if item[3] <= 0.10}
    noise_total = len(noise_assertions)

    # 1. FIFO Simulation
    fifo = BaselineFIFOBuffer(capacity=capacity)
    for c, a, attr, sal in stream:
        fifo.ingest(c, a, attr, sal)

    fifo_active_empirical = sum(1 for item in fifo.active if item[2].veracity_state == VeracityState.VERIFIED_EMPIRICAL)
    fifo_avg_salience = sum(item[3] for item in fifo.active) / len(fifo.active) if fifo.active else 0.0
    fifo_active_noise = {item[1] for item in fifo.active if item[1] in noise_assertions}
    fifo_noise_filter = (noise_total - len(fifo_active_noise)) / noise_total if noise_total else None

    # 2. LRU Simulation
    lru = BaselineLRUBuffer(capacity=capacity)
    for c, a, attr, sal in stream:
        lru.ingest(c, a, attr, sal)

    lru_active_empirical = sum(1 for item in lru.active.values() if item[2].veracity_state == VeracityState.VERIFIED_EMPIRICAL)
    lru_avg_salience = sum(item[3] for item in lru.active.values()) / len(lru.active) if lru.active else 0.0
    lru_active_noise = {item[1] for item in lru.active.values() if item[1] in noise_assertions}
    lru_noise_filter = (noise_total - len(lru_active_noise)) / noise_total if noise_total else None

    # 3. RANDOM Simulation
    rnd = BaselineRandomBuffer(capacity=capacity, seed=seed)
    for c, a, attr, sal in stream:
        rnd.ingest(c, a, attr, sal)

    rnd_active_empirical = sum(1 for item in rnd.active if item[2].veracity_state == VeracityState.VERIFIED_EMPIRICAL)
    rnd_avg_salience = sum(item[3] for item in rnd.active) / len(rnd.active) if rnd.active else 0.0
    rnd_active_noise = {item[1] for item in rnd.active if item[1] in noise_assertions}
    rnd_noise_filter = (noise_total - len(rnd_active_noise)) / noise_total if noise_total else None

    # 4. ARIO Cognitive Working Memory Buffer
    engine = ConsolidationEngine()
    ario = WorkingMemoryBuffer(capacity=capacity, consolidation_engine=engine)
    step_tick_freq = 5 if scenario != "TEMPORAL_LONGEVITY" else 3

    for step, (c, a, attr, sal) in enumerate(stream):
        ario.ingest(c, a, attr, salience=sal, step=step)
        if step % step_tick_freq == 0:
            ario.step_tick(step=step)

    ario_active_empirical = sum(1 for chunk in ario.active_chunks if chunk.source_attribution.veracity_state == VeracityState.VERIFIED_EMPIRICAL)
    ario_avg_salience = sum(c.salience for c in ario.active_chunks) / len(ario.active_chunks) if ario.active_chunks else 0.0

    # Compare unique exact assertions against actual active memory and actual LTM nodes.
    # This avoids crediting unrelated nodes merely because they share a concept prefix.
    ario_active_empirical_assertions = {
        chunk.assertion for chunk in ario.active_chunks
        if chunk.source_attribution.veracity_state == VeracityState.VERIFIED_EMPIRICAL
    }
    ltm_assertions = {node.assertion for node in engine.nodes.values()}
    ario_ltm_empirical_assertions = empirical_assertions & ltm_assertions
    ario_empirical_preserved_assertions = ario_active_empirical_assertions | ario_ltm_empirical_assertions
    ario_empirical_preserved = len(ario_empirical_preserved_assertions)

    ario_active_noise = {chunk.assertion for chunk in ario.active_chunks if chunk.assertion in noise_assertions}
    ario_ltm_noise = noise_assertions & ltm_assertions
    ario_noise_filter = (noise_total - len(ario_active_noise | ario_ltm_noise)) / noise_total if noise_total else None

    return {
        "FIFO": {
            "active_empirical_chunks": fifo_active_empirical,
            "total_empirical_preserved": fifo_active_empirical,
            "empirical_preservation_rate": round(fifo_active_empirical / max(1, empirical_total), 3),
            "avg_active_salience": round(fifo_avg_salience, 3),
            "empirical_facts_in_ltm": 0,
            "noise_facts_in_ltm": 0,
            "noise_rejection_rate": round(fifo_noise_filter, 3) if fifo_noise_filter is not None else None,
            "cowan_capacity_held": len(fifo.active) <= capacity,
        },
        "LRU": {
            "active_empirical_chunks": lru_active_empirical,
            "total_empirical_preserved": lru_active_empirical,
            "empirical_preservation_rate": round(lru_active_empirical / max(1, empirical_total), 3),
            "avg_active_salience": round(lru_avg_salience, 3),
            "empirical_facts_in_ltm": 0,
            "noise_facts_in_ltm": 0,
            "noise_rejection_rate": round(lru_noise_filter, 3) if lru_noise_filter is not None else None,
            "cowan_capacity_held": len(lru.active) <= capacity,
        },
        "RANDOM": {
            "active_empirical_chunks": rnd_active_empirical,
            "total_empirical_preserved": rnd_active_empirical,
            "empirical_preservation_rate": round(rnd_active_empirical / max(1, empirical_total), 3),
            "avg_active_salience": round(rnd_avg_salience, 3),
            "empirical_facts_in_ltm": 0,
            "noise_facts_in_ltm": 0,
            "noise_rejection_rate": round(rnd_noise_filter, 3) if rnd_noise_filter is not None else None,
            "cowan_capacity_held": len(rnd.active) <= capacity,
        },
        "ARIO_COGNITIVE": {
            "active_empirical_chunks": ario_active_empirical,
            "total_empirical_preserved": min(empirical_total, ario_empirical_preserved),
            "empirical_preservation_rate": round(min(1.0, ario_empirical_preserved / max(1, empirical_total)), 3),
            "avg_active_salience": round(ario_avg_salience, 3),
            "noise_rejection_rate": round(ario_noise_filter, 3) if ario_noise_filter is not None else None,
            "empirical_facts_in_ltm": len(ario_ltm_empirical_assertions),
            "noise_facts_in_ltm": len(ario_ltm_noise),
            "cowan_capacity_held": ario.active_count <= capacity,
        },
    }


def run_all_scenarios(n_events: int = 200, capacity: int = 4, seed: int = 42) -> Dict[str, Any]:
    scenarios = [
        "STANDARD_BALANCED",
        "EPISTEMIC_FLOODING",
        "EVIDENCE_COMPETITION",
        "TEMPORAL_LONGEVITY",
    ]
    results = {}
    for sc in scenarios:
        count = 350 if sc == "TEMPORAL_LONGEVITY" else n_events
        results[sc] = evaluate_scenario(sc, n_events=count, capacity=capacity, seed=seed)
    return results


def format_markdown_report(results: Dict[str, Any]) -> str:
    md = []
    md.append("# Cognitive Memory Benchmark: Policy Comparison Report\n")
    md.append("Comparative evaluation of Ario Cowan Cognitive Working Memory against FIFO, LRU, and Random baselines.\n")

    scenario_titles = {
        "STANDARD_BALANCED": "Scenario 1: Standard Balanced Stream (35% empirical, 30% testimony, 20% hypothesis, 15% noise)",
        "EPISTEMIC_FLOODING": "Scenario 2: Epistemic Flooding (70% sensory noise burst vs critical empirical signals)",
        "EVIDENCE_COMPETITION": "Scenario 3: Evidence Competition (50% empirical vs 50% unverified claims sharing concepts)",
        "TEMPORAL_LONGEVITY": "Scenario 4: Temporal Longevity (Extended horizon with temporal decay)",
    }

    for sc, res in results.items():
        title = scenario_titles.get(sc, sc)
        md.append(f"### {title}\n")
        md.append("| Metric | FIFO | LRU | RANDOM | ARIO (Cowan) |")
        md.append("| :--- | :---: | :---: | :---: | :---: |")
        metrics = [
            ("Empirical Preservation Rate", "empirical_preservation_rate", "{:.1%}"),
            ("Total Empirical Preserved", "total_empirical_preserved", "{:d}"),
            ("Active Empirical in WM", "active_empirical_chunks", "{:d}"),
            ("Empirical nodes in LTM", "empirical_facts_in_ltm", "{:d}"),
            ("Noise Rejection Rate", "noise_rejection_rate", "{:.1%}"),
            ("Average Active Salience", "avg_active_salience", "{:.3f}"),
            ("Cowan Capacity <= 4 Held", "cowan_capacity_held", "{}"),
        ]
        for label, key, fmt in metrics:
            row = [f"| {label}"]
            for pol in ["FIFO", "LRU", "RANDOM", "ARIO_COGNITIVE"]:
                val = res[pol].get(key, 0)
                if fmt == "{:.1%}":
                    formatted = "N/A" if val is None else f"{val * 100:.1f}%"
                elif fmt == "{:d}":
                    formatted = str(int(val))
                elif fmt == "{:.3f}":
                    formatted = f"{val:.3f}"
                else:
                    formatted = "PASS" if val else "FAIL"
                row.append(f" {formatted} ")
            row.append("|")
            md.append("|".join(row))
        md.append("\n")

    md.append("### Interpretation Limits\n")
    md.append("These are deterministic synthetic simulations, not empirical evidence about human cognition or production effectiveness. FIFO/LRU/Random are active-buffer-only baselines; Ario's preservation metric also counts an exact assertion only when a corresponding node is present in its LTM. The stores therefore have different capabilities, and results must not be presented as an apples-to-apples claim of policy superiority. Noise rejection means the unique synthetic noise assertion is absent from both active and modeled long-term stores at the end; `N/A` means the scenario generated no noise. Results are exploratory and seed-dependent.\n")

    return "\n".join(md)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ario Policy Comparison Benchmark")
    parser.add_argument("--events", type=int, default=200, help="Number of incoming events")
    parser.add_argument("--capacity", type=int, default=4, help="Capacity bound (Cowan limit)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default="", help="Path to write JSON output")
    parser.add_argument("--markdown", type=str, default="", help="Path to write Markdown report")
    args = parser.parse_args()

    results = run_all_scenarios(n_events=args.events, capacity=args.capacity, seed=args.seed)

    print("=" * 76)
    print("  ARIO COGNITIVE MEMORY BENCHMARK: MULTI-SCENARIO POLICY COMPARISON")
    print("=" * 76)
    for sc, res in results.items():
        print(f"\n--- {sc} ---")
        print(f"{'Metric':<28} | {'FIFO':<8} | {'LRU':<8} | {'RANDOM':<8} | {'ARIO (Cowan)':<12}")
        print("-" * 72)
        for m in ["empirical_preservation_rate", "total_empirical_preserved", "active_empirical_chunks", "noise_rejection_rate", "avg_active_salience"]:
            f_v = res["FIFO"][m]
            l_v = res["LRU"][m]
            r_v = res["RANDOM"][m]
            a_v = res["ARIO_COGNITIVE"][m]
            if "rate" in m:
                def pct(v): return "N/A" if v is None else f"{v*100:5.1f}%"
                print(f"{m:<28} | {pct(f_v):>8} | {pct(l_v):>8} | {pct(r_v):>8} | {pct(a_v):>12}")
            else:
                print(f"{m:<28} | {f_v:8} | {l_v:8} | {r_v:8} | {a_v:12}")

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved scenario results JSON to {args.output}")

    if args.markdown:
        md_text = format_markdown_report(results)
        os.makedirs(os.path.dirname(os.path.abspath(args.markdown)), exist_ok=True)
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(md_text)
        print(f"Saved scenario report Markdown to {args.markdown}")
