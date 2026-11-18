"""ARIO-TB-UCD v0.1: undeclared-copy dependence probe (synthetic, bounded).

Research question
-----------------
M0 flags ``EVIDENCE_INFLATION`` only when shared ancestry is *declared*,
for example through shared observation references. What happens when
sources copy one another but declare disjoint roots? Can a truth-free,
statistical dependence screen detect such copying while respecting an
asymmetric rule: it may **only downgrade** declared independence
(INDEPENDENT -> UNKNOWN) and must never promote it?

Prior art: Dong, Berti-Equille & Srivastava, "Integrating Conflicting Data:
The Role of Source Dependence", PVLDB 2(1):550-561, 2009,
https://doi.org/10.14778/1687627.1687690. Their models are Bayesian and
use false-value sharing. The screen here is a deliberately simpler
agreement-excess heuristic, so its limits are easy to see.

Boundaries
----------
- All sources, values and "truth" are synthetic and generated from a seed.
- The screen produces *inferred dependence signals*. They are not Evidence,
  not an Assessment, and not authentication of independence or dependence.
- No M0/core code is modified. M0 is called read-only to document its
  declared-lineage boundary.
- A passing run shows only the behaviour exercised under the stated
  parameters.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from itertools import combinations

from core.audit_engine import AuditEngine, AuditInput
from core.schema import Evidence, IndependenceStatus, Reference, Timestamp

PROBE_ID = "ARIO-TB-UCD-0.1"


@dataclass(frozen=True)
class WorldSpec:
    """Synthetic world parameters. Nothing here models a real source."""

    name: str
    n_items: int = 200
    n_false_values: int = 10
    original_accuracy: float = 0.55
    n_copiers: int = 3
    copy_rate: float = 0.9
    n_independent: int = 3
    independent_accuracy: float = 0.65


@dataclass(frozen=True)
class World:
    spec: WorldSpec
    truth: tuple[str, ...]
    claims: dict[str, tuple[str, ...]]
    true_clusters: tuple[frozenset[str], ...]


@dataclass(frozen=True)
class ScreenConfig:
    """``max_plausible_accuracy`` is a declared prior, not a measured fact."""

    max_plausible_accuracy: float = 0.8
    margin: float = 0.10


@dataclass(frozen=True)
class ScreenResult:
    agreement: dict[tuple[str, str], float]
    threshold: float
    flagged_pairs: frozenset[tuple[str, str]]
    clusters: tuple[frozenset[str], ...]
    signal_kind: str = "INFERRED_DEPENDENCE_SIGNAL_NOT_EVIDENCE"


@dataclass(frozen=True)
class TrialResult:
    world: str
    seed: int
    naive_accuracy: float
    screened_accuracy: float
    oracle_accuracy: float
    true_dependent_pairs: int
    flagged_pairs: int
    true_positive_pairs: int
    false_positive_pairs: int
    m0_inflation_declared_disjoint: bool
    m0_inflation_after_downgrade: bool
    downgraded_sources: tuple[str, ...] = field(default_factory=tuple)


def _draw(rng: random.Random, accuracy: float, n_false: int) -> str:
    if rng.random() < accuracy:
        return "T"
    return f"F{rng.randrange(n_false)}"


def generate_world(spec: WorldSpec, seed: int) -> World:
    rng = random.Random(f"{PROBE_ID}|{spec.name}|{seed}")
    truth = tuple("T" for _ in range(spec.n_items))
    claims: dict[str, tuple[str, ...]] = {}
    original = tuple(
        _draw(rng, spec.original_accuracy, spec.n_false_values)
        for _ in range(spec.n_items)
    )
    claims["O"] = original
    cluster = {"O"}
    for c in range(spec.n_copiers):
        name = f"C{c + 1}"
        claims[name] = tuple(
            original[i] if rng.random() < spec.copy_rate
            else _draw(rng, spec.original_accuracy, spec.n_false_values)
            for i in range(spec.n_items)
        )
        cluster.add(name)
    for k in range(spec.n_independent):
        claims[f"I{k + 1}"] = tuple(
            _draw(rng, spec.independent_accuracy, spec.n_false_values)
            for _ in range(spec.n_items)
        )
    if spec.n_copiers:
        clusters = [frozenset(cluster)] + [frozenset({s}) for s in claims if s not in cluster]
    else:
        clusters = [frozenset({s}) for s in claims]
    return World(spec, truth, claims, tuple(clusters))


def pairwise_agreement(claims: dict[str, tuple[str, ...]]) -> dict[tuple[str, str], float]:
    out = {}
    for a, b in combinations(sorted(claims), 2):
        xs, ys = claims[a], claims[b]
        out[(a, b)] = sum(x == y for x, y in zip(xs, ys)) / len(xs)
    return out


def dependence_screen(world: World, config: ScreenConfig = ScreenConfig()) -> ScreenResult:
    """Truth-free screen: flag pairs agreeing more than a plausible independent pair.

    For two independent sources with accuracy ``a`` and ``F`` uniformly chosen
    false values, expected agreement is ``a*a + (1-a)**2 / F``. Pairs whose
    agreement exceeds that bound at ``max_plausible_accuracy`` plus ``margin``
    are flagged. Ground truth is never read.
    """
    a = config.max_plausible_accuracy
    f = world.spec.n_false_values
    threshold = a * a + (1 - a) ** 2 / f + config.margin
    agreement = pairwise_agreement(world.claims)
    flagged = frozenset(p for p, v in agreement.items() if v > threshold)
    parent = {s: s for s in world.claims}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for x, y in flagged:
        parent[find(x)] = find(y)
    groups: dict[str, set[str]] = {}
    for s in world.claims:
        groups.setdefault(find(s), set()).add(s)
    clusters = tuple(sorted((frozenset(g) for g in groups.values()), key=sorted))
    return ScreenResult(agreement, threshold, flagged, clusters)


def weighted_vote(world: World, clusters: tuple[frozenset[str], ...]) -> float:
    """Each cluster gets total weight 1, split equally among its members."""
    weight = {s: 1.0 / len(c) for c in clusters for s in c}
    correct = 0
    for i, true_value in enumerate(world.truth):
        tally: dict[str, float] = {}
        for s, values in world.claims.items():
            tally[values[i]] = tally.get(values[i], 0.0) + weight[s]
        best = max(tally.values())
        winners = sorted(v for v, w in tally.items() if abs(w - best) < 1e-12)
        correct += winners == [true_value]  # ties count as not correct
    return correct / len(world.truth)


def downgrade_only(
    declared: dict[str, IndependenceStatus], screen: ScreenResult
) -> dict[str, IndependenceStatus]:
    """Asymmetric rule: inferred signals may only weaken declared independence."""
    flagged_sources = {s for pair in screen.flagged_pairs for s in pair}
    out = {}
    for source, status in declared.items():
        if source in flagged_sources and status == IndependenceStatus.INDEPENDENT:
            out[source] = IndependenceStatus.UNKNOWN
        else:
            out[source] = status  # never promoted, never changed otherwise
    return out


def _evidence(source: str, item: int, status: IndependenceStatus) -> Evidence:
    return Evidence(
        evidence_id=f"EV-{source}-{item}",
        observation_refs=(Reference(f"OBS-{source}-{item}", "SYNTHETIC_SOURCE_CLAIM"),),
        evidence_level="OBSERVATION",
        independence_status=status,
        derivation_reference=Reference(f"DER-{source}-{item}", "SYNTHETIC"),
        scope=f"{PROBE_ID} synthetic item {item}",
    )


def m0_inflation_flag(world: World, item: int, statuses: dict[str, IndependenceStatus]) -> bool:
    """Run M0 read-only on one item; report whether EVIDENCE_INFLATION was raised."""
    evidence = tuple(_evidence(s, item, statuses[s]) for s in sorted(world.claims))
    result = AuditEngine().audit(
        AuditInput(evidence=evidence),
        rule_versions=("M0-1.0",),
        configuration_id=PROBE_ID,
        execution_timestamp=Timestamp(f"{PROBE_ID}-synthetic"),
        audit_id=f"{PROBE_ID}-{world.spec.name}-{item}",
    )
    return "EVIDENCE_INFLATION" in result.violations


def run_trial(spec: WorldSpec, seed: int, config: ScreenConfig = ScreenConfig()) -> TrialResult:
    world = generate_world(spec, seed)
    screen = dependence_screen(world, config)
    singletons = tuple(frozenset({s}) for s in world.claims)
    true_pairs = {
        tuple(sorted(p)) for c in world.true_clusters if len(c) > 1
        for p in combinations(sorted(c), 2)
    }
    tp = len(true_pairs & set(screen.flagged_pairs))
    declared = {s: IndependenceStatus.INDEPENDENT for s in world.claims}
    after = downgrade_only(declared, screen)
    return TrialResult(
        world=spec.name,
        seed=seed,
        naive_accuracy=weighted_vote(world, singletons),
        screened_accuracy=weighted_vote(world, screen.clusters),
        oracle_accuracy=weighted_vote(world, world.true_clusters),
        true_dependent_pairs=len(true_pairs),
        flagged_pairs=len(screen.flagged_pairs),
        true_positive_pairs=tp,
        false_positive_pairs=len(screen.flagged_pairs) - tp,
        m0_inflation_declared_disjoint=m0_inflation_flag(world, 0, declared),
        m0_inflation_after_downgrade=m0_inflation_flag(world, 0, after),
        downgraded_sources=tuple(sorted(s for s in after if after[s] != declared[s])),
    )


DEFAULT_WORLDS = (
    WorldSpec("copier_majority"),
    WorldSpec("null_no_copiers", n_copiers=0, n_independent=7),
    WorldSpec("null_high_accuracy", n_copiers=0, n_independent=7, independent_accuracy=0.92),
    WorldSpec("weak_copying", copy_rate=0.5),
)


def summarize(seeds: range = range(20)) -> list[dict]:
    rows = []
    for spec in DEFAULT_WORLDS:
        trials = [run_trial(spec, s) for s in seeds]
        n = len(trials)
        rows.append({
            "world": spec.name,
            "trials": n,
            "naive_acc": round(sum(t.naive_accuracy for t in trials) / n, 3),
            "screened_acc": round(sum(t.screened_accuracy for t in trials) / n, 3),
            "oracle_acc": round(sum(t.oracle_accuracy for t in trials) / n, 3),
            "true_pairs": trials[0].true_dependent_pairs,
            "mean_flagged": round(sum(t.flagged_pairs for t in trials) / n, 2),
            "mean_false_pos": round(sum(t.false_positive_pairs for t in trials) / n, 2),
            "m0_inflation_declared": sum(t.m0_inflation_declared_disjoint for t in trials),
            "m0_inflation_after": sum(t.m0_inflation_after_downgrade for t in trials),
        })
    return rows


if __name__ == "__main__":
    import json

    for row in summarize():
        print(json.dumps(row, sort_keys=True))
