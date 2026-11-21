"""Tests for ARIO-TB-UCD v0.1 (synthetic undeclared-copy dependence probe).

Several tests pin *negative* results (known limitations) on purpose.
A future improvement that changes them should update them knowingly,
not silently.
"""
from dataclasses import replace

from core.audit_engine import AuditEngine, AuditInput
from core.schema import Evidence, IndependenceStatus, Reference, Timestamp
from undeclared_copy_dependence_probe import (
    DEFAULT_WORLDS,
    ScreenConfig,
    dependence_screen,
    downgrade_only,
    generate_world,
    m0_inflation_flag,
    run_trial,
    summarize,
)

COPIER, NULL, NULL_HIGH, WEAK = DEFAULT_WORLDS
SEEDS = range(20)


def test_world_generation_is_deterministic():
    assert generate_world(COPIER, 3) == generate_world(COPIER, 3)
    assert generate_world(COPIER, 3) != generate_world(COPIER, 4)


def test_screen_never_reads_ground_truth():
    world = generate_world(COPIER, 1)
    poisoned = replace(world, truth=tuple("F0" for _ in world.truth))
    assert dependence_screen(world) == dependence_screen(poisoned)


def test_signal_is_labelled_as_not_evidence():
    assert dependence_screen(generate_world(COPIER, 0)).signal_kind == (
        "INFERRED_DEPENDENCE_SIGNAL_NOT_EVIDENCE"
    )


def test_downgrade_only_never_promotes_or_rewrites():
    screen = dependence_screen(generate_world(COPIER, 0))
    flagged = {s for pair in screen.flagged_pairs for s in pair}
    assert flagged
    declared = {
        "O": IndependenceStatus.INDEPENDENT,
        "C1": IndependenceStatus.UNKNOWN,
        "C2": IndependenceStatus.DEPENDENT,
        "C3": IndependenceStatus.INDEPENDENT,
        "I1": IndependenceStatus.INDEPENDENT,
        "I2": IndependenceStatus.UNKNOWN,
        "I3": IndependenceStatus.DEPENDENT,
    }
    after = downgrade_only(declared, screen)
    for source, before in declared.items():
        if before != IndependenceStatus.INDEPENDENT:
            assert after[source] == before
        elif source in flagged:
            assert after[source] == IndependenceStatus.UNKNOWN
        else:
            assert after[source] == IndependenceStatus.INDEPENDENT
    assert all(
        not (declared[s] != IndependenceStatus.INDEPENDENT
             and after[s] == IndependenceStatus.INDEPENDENT)
        for s in declared
    )


def test_m0_boundary_undeclared_copying_is_not_visible_to_m0():
    """Observation of M0's declared-lineage boundary; not a defect claim."""
    for seed in range(5):
        world = generate_world(COPIER, seed)
        declared = {s: IndependenceStatus.INDEPENDENT for s in world.claims}
        assert m0_inflation_flag(world, 0, declared) is False


def test_m0_control_flags_inflation_when_shared_root_is_declared():
    shared = Reference("OBS-SHARED-ROOT", "SYNTHETIC_SOURCE_CLAIM")
    evidence = tuple(
        Evidence(
            evidence_id=f"EV-{s}",
            observation_refs=(shared,),
            evidence_level="OBSERVATION",
            independence_status=IndependenceStatus.INDEPENDENT,
            derivation_reference=Reference(f"DER-{s}", "SYNTHETIC"),
            scope="UCD control",
        )
        for s in ("O", "C1")
    )
    result = AuditEngine().audit(
        AuditInput(evidence=evidence),
        rule_versions=("M0-1.0",),
        configuration_id="UCD-control",
        execution_timestamp=Timestamp("UCD-control"),
        audit_id="UCD-control",
    )
    assert "EVIDENCE_INFLATION" in result.violations


def test_copier_majority_screen_recovers_accuracy_without_false_positives():
    trials = [run_trial(COPIER, s) for s in SEEDS]
    naive = sum(t.naive_accuracy for t in trials) / len(trials)
    screened = sum(t.screened_accuracy for t in trials) / len(trials)
    assert screened - naive >= 0.15
    assert all(t.false_positive_pairs == 0 for t in trials)
    assert all(t.true_positive_pairs == t.true_dependent_pairs for t in trials)
    assert all(set(t.downgraded_sources) == {"O", "C1", "C2", "C3"} for t in trials)


def test_null_world_without_copiers_flags_nothing():
    assert all(run_trial(NULL, s).flagged_pairs == 0 for s in SEEDS)


def test_known_limitation_high_accuracy_independents_are_misread_as_copying():
    """Pinned negative result: agreement-excess confuses 'all accurate' with copying."""
    trials = [run_trial(NULL_HIGH, s) for s in SEEDS]
    assert all(t.false_positive_pairs > 0 for t in trials)
    naive = sum(t.naive_accuracy for t in trials) / len(trials)
    screened = sum(t.screened_accuracy for t in trials) / len(trials)
    assert screened < naive - 0.2


def test_known_limitation_weak_copying_is_mostly_missed():
    trials = [run_trial(WEAK, s) for s in SEEDS]
    recall = sum(t.true_positive_pairs for t in trials) / sum(
        t.true_dependent_pairs for t in trials
    )
    assert recall < 0.1


def test_higher_accuracy_prior_removes_high_accuracy_false_positives_on_this_world():
    """Prior choice is an explicit trade-off, not a neutral default."""
    config = ScreenConfig(max_plausible_accuracy=0.95, margin=0.05)
    assert all(run_trial(NULL_HIGH, s, config).false_positive_pairs == 0 for s in range(5))
    recalls = [run_trial(COPIER, s, config) for s in range(5)]
    assert all(t.true_positive_pairs < t.true_dependent_pairs for t in recalls)


def test_summary_rows_cover_all_worlds():
    rows = summarize(range(3))
    assert [r["world"] for r in rows] == [w.name for w in DEFAULT_WORLDS]
