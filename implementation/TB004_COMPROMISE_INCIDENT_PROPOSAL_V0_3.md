# TB-004 compromise incident boundaries — v0.3 proposal

**Status: PROPOSED / DRAFT / HOLD. Semantics are not adopted.**  
**Date:** 2026-11-10  
**Observed baseline:** `e6ab569fec79d192a83a121f834af23e93397674`

This document records a reproducible ambiguity in the synthetic compromise model and proposes prospective controls. It changes no v0.1/v0.2 runtime, tests, frozen evidence, evaluation history, admission authority, or trust state. The filename is a proposal version, not an implemented TB-004 profile.

## Observed behavior and its limit

A confirmed epoch compromise window `[5,30]` leaves capture at sequence `10` and external retention at `12` unresolved; the current evaluator returns `SUSPENDED`. Adding a confirmed compromise of the controlling root with window `[20,25]` changes the result to `CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON`. Both observations are available before evaluation at `70`.

This behavior was **OBSERVED by execution** in both existing modules at the baseline. The v0.2 implementation [collects relevant observations across target kinds](https://github.com/SepehrGhanbari/Ario/blob/e6ab569fec79d192a83a121f834af23e93397674/implementation/witness_compromise_recovery_experiment_v0_2.py#L488-L496), [intersects all their onset bounds](https://github.com/SepehrGhanbari/Ario/blob/e6ab569fec79d192a83a121f834af23e93397674/implementation/witness_compromise_recovery_experiment_v0_2.py#L518-L524), and [uses the resulting lower bound for affirmative historical use](https://github.com/SepehrGhanbari/Ario/blob/e6ab569fec79d192a83a121f834af23e93397674/implementation/witness_compromise_recovery_experiment_v0_2.py#L632-L643).

**INFERRED concern, contingent on incident semantics:** an epoch compromise and a root compromise can be distinct incidents. A later root incident cannot establish that the earlier epoch incident began later. Under that interpretation, intersecting their windows discards an earlier plausible compromise and promotes the artifact without justification.

**UNKNOWN:** whether the intended contract restricts every relevant observation to the same compromise-onset variable. The [v0.1 contract](WITNESS_COMPROMISE_RECOVERY_EXPERIMENT_V0_1.md) describes epoch, witness, and control-root targets and onset bounds, but provides no incident identity or explicit cross-target shared-onset binding. The [v0.2 contract](WITNESS_COMPROMISE_RECOVERY_EXPERIMENT_V0_2.md) inherits those compromise rules. This proposal does not present disputed semantics as an already adopted runtime requirement.

The current affirmative label remains a conditional synthetic comparison result. No real evidence admission, historical truth, authenticated custody, or production safety was observed.

## Minimal executable counterexample

Save the following snippet as a temporary `.py` file **outside the repository checkout**, then execute it **from the repository root** with `python -B /absolute/path/to/tb004_repro.py` (quote the script path if it contains spaces). Python's `-B` option disables `.pyc`/`__pycache__` writes during these imports. The snippet exercises both existing versions without intentionally modifying their inputs or source:

```python
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import importlib
import json
import sys

sys.path.insert(0, str(Path("implementation").resolve()))
for module in (
    "witness_compromise_recovery_experiment",
    "witness_compromise_recovery_experiment_v0_2",
):
    m = importlib.import_module(module)
    scope = "LAB:SCOPE"
    digest = sha256(b"synthetic checkpoint").hexdigest()
    epoch = m.WitnessEpoch("EP", "W", scope, "ROOT", 0)
    artifact = m.HistoricalArtifact("ART", "W", "EP", scope, 10, digest)
    pin = m.FrozenReference(
        "REF", "ART", digest, 12, "EXTERNAL-ROOT",
        "LAB_CONDITIONALLY_SEPARATE", True, m.LAB, "PIN",
    )
    epoch_observation = m.CompromiseObservation(
        "EPOCH-INCIDENT", "EPOCH", "EP", "CONFIRMED_WINDOW",
        40, 5, 30, m.LAB, "EPOCH-SUPPORT",
    )
    root_observation = m.CompromiseObservation(
        "ROOT-INCIDENT", "CONTROL_ROOT", "ROOT", "CONFIRMED_WINDOW",
        45, 20, 25, m.LAB, "ROOT-SUPPORT",
    )
    original = m.RecoveryCase(
        scope, (epoch,), (artifact,), (pin,),
        (epoch_observation,), (), (), (), "ART", 70, True, m.LAB,
    )
    first = m.evaluate_recovery(original)
    second = m.evaluate_recovery(replace(
        original, observations=(epoch_observation, root_observation),
    ))
    assert first.evidentiary_usability.status == "SUSPENDED"
    assert second.evidentiary_usability.status == (
        "CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON"
    )
    print(json.dumps({
        "module": module,
        "epoch_only": first.evidentiary_usability.status,
        "additional_root_observation": second.evidentiary_usability.status,
    }, sort_keys=True))
```

The assertions document current behavior. They are not proposed acceptance expectations for a future version.

## Decision required before implementation

Choose and freeze one contract prospectively:

1. **Restrict the model to one onset variable.** Declare that all relevant observations constrain exactly the same onset. Reject or preserve uncertainty for observations without an explicit shared-onset binding, including cross-target observations. Merely sharing an attacker, witness, or investigation does not establish equal onset.
2. **Represent multiple incidents.** Bind every observation to an incident and an onset variable. Intersect bounds only within a valid shared-onset group. Keep separate incidents separate, including multiple incidents against one target. Require pre-compromise reliance to precede every relevant incident; an unresolved incident association cannot support affirmative use.

For either choice, binding remains a supplied LAB premise. It authenticates no real incident. Refutations must remain scoped to their referenced observations, and existing confirmed-compromise conflict handling must not silently restore an epoch.

For grouped intervals, within one shared-onset group the lower bound may be `max(lower_bounds)` and the upper bound `min(upper_bounds)`. Across independent relevant incidents, capture and retention must be strictly earlier than each incident's lower bound. A missing necessary lower bound prevents that proof. Distinct incidents with disjoint windows are not contradictory merely because their windows do not overlap.

## Prospective acceptance matrix

These are proposed controls, not retroactive oracle labels or claims that the current implementations pass them.

| Input distinction | Proposed expected outcome |
|---|---|
| Epoch window `[5,30]`; capture `10`, retention `12` | Unresolved pre-compromise relation; use remains suspended |
| Add a distinct relevant root incident `[20,25]` | No promotion; retain the epoch's earlier plausible compromise |
| Two observations explicitly constrain one onset, `[5,30]` and `[20,25]` | Intersection `[20,25]` permitted; conditional use requires all other existing gates |
| Two targets share an alleged incident but lack a shared-onset binding | Preserve uncertainty; do not assume identical onset |
| One onset has disjoint windows `[5,10]` and `[20,25]` | Explicit contradictory-evidence finding; no affirmative use |
| Distinct incidents have those disjoint windows | Preserve both incidents; do not invent a contradiction or ignore the earlier one |
| Relevant incident has unknown lower bound | No pre-compromise proof or affirmative use |
| Observation concerns an unrelated witness/root | Preserve target scope; do not change this artifact's result |
| Observation/incident groups are reordered | Identical semantic result and deterministic reporting |
| Add a separate adverse relevant incident without refining an existing onset | Must not promote usability |
| Controller compromised, inventory incomplete, or required pin unavailable | Existing nonpositive gates remain in force |
| Refutation targets one observation | Preserve other incidents and original history; no silent confirmed-state erasure |

A future implementation should test the entire result dependency: incident grouping, interval reasoning, retained-reference eligibility, usability, and the new evaluation's evidence binding. A shared status or a changed evaluation digest alone is insufficient.

## Validation and unperformed work

The code block above was executed against the pinned baseline and reproduced the promotion in both modules. Markdown's relative contract references resolve to existing tracked files. No current regression expectation was changed.

No future incident schema, runtime repair, new benchmark score, cryptographic verifier, independent witness, or production safety claim is implemented here. Adoption, implementation, independent review, and exact-head validation remain future work.
