# W1 — Trae third-pass adjudication, independent checks and CI receipt (2026-11-18)

**State:** `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO`.  
**Reviewer report:** [Trae third pass, preserved verbatim](W1_TRAE_THIRD_PASS_REPORT_2026-11-18_VERBATIM.md) — uploaded source re-read **character-for-character** from GitHub; Git blob `9c35973e1b6e3effbb22869a97d7c9dd0c90ce93`. Reviewer AI agent: DeepSeek-V4.1-Flash; self-reported non-blind technical review, not independent human peer review.  
**Original review patch:** [verbatim 299-line diff](W1_TRAE_THIRD_PASS_ORIGINAL_PATCH_2026-11-18.patch), Git blob `71c8cc9c1e554c27fd3ec31b5deabfc9bbfb466e`. No reported `evidence/` log directory or `tools/` scripts arrived in this user upload: **NOT_RECEIVED**. This record does not pretend to reproduce that complete battery from those unavailable raw files.

## What the project actually verified

1. **Source pin and patch structure.** The 2 added Python files are exactly the proposed third-pass code; no engine or workflow modifications occur in the original patch. Independently parsed the new-file diff; source content committed and GitHub re-read equal to the diff:
   - [w1_custody_correlation_probe.py](w1_custody_correlation_probe.py), blob `d7d43c5f0f98cfc83e1ffaa2ea99741b77625f18`.
   - [w1_latent_graph_challenge_v0_1.py](w1_latent_graph_challenge_v0_1.py), blob `debc4da1007e6dfe7851c1b09b7b62767e74353c`.
   - In a **disposable local tree restored from the previous 12-file offline packet**, the frozen evaluator had 26,726 bytes and SHA-256 `71912958bad6db97218ac630cadee6c34c04b286aec99b3f7cda071f8d79f567`. `git apply --check` on the original Trae third-pass patch returned 0 before it was applied **locally**; this is evidence for this compatible tree, not a verbatim copy of Trae's claimed test environment.
2. **Local actual deterministic tests:** `python -B -m unittest discover -s research/consensus -p test_w1_adversarial_input_sensitivity_v1.py -q` → **15 OK**. `PYTHONPATH=research/consensus python -B -m unittest research/consensus/w1_custody_correlation_probe.py -v` → **6 tests, 5 ordinary OK, one expectedFailure**. `PYTHONPATH=research/consensus python -B -m unittest research/consensus/w1_latent_graph_challenge_v0_1.py -v` → **4 OK**. These tests used the original SHA-pinned engine and fabricated laboratory cases only.
3. **Local scaffold score (author-declared truth only):** the pinned policy on four matched latent scenarios recorded `HONEST n=4 falseEnd=0`, `DECLARED_INCOMPLETE n=4 falseEnd=0`, `UNDISCLOSED_OMISSION n=4 falseEnd=3`. Never-promote had zero false endorsements across variants while missing a constructed true positive; **not** population accuracy or independently authenticated truth.
4. **M9 off-by-one replay:** changing `elif any(c >= case.mutation_sequence for c in captures):` to `>` in a **transient in-memory module only** changes equality at mutation=2 from `NOT_BEFORE_MUTATION / UNKNOWN` to `LAB_BEFORE_MUTATION / CONDITIONAL`. Frozen core remains untouched.
5. **Five-policy dispute independently checked:** storage status among 16 W1-DEV fixtures is **14× `LAB_DISTINCT_OBJECTS`, 2× `UNKNOWN`**. Exhaustively enumerated the **nine** storage-axis-only mappings (three possible outputs per observed status); **zero** reproduces Claude's previously reported exact row `(6/16 agreement, 11 false endorsements, 0 misses, 1 UNKNOWN)`. This supports Trae's numerical objection. Other four rows in Trae's report are **reviewer-reported**, not a newly created independent oracle. We must not use that disputed storage row as a verified paper result.

## Additional counterexample to the *new* custody-correlation proposal — OPEN

The proposed `_custodian_ids` function aggregates **all** LAB `TRANSFERRED_TO` endpoints linked to each artifact, whether or not those edges are reachable along the uniquely accepted sequential custody route. This is deliberately a coarse over-approximation and not a new TB-003 engine capability.

Reproducible synthetic negative: starting from `w.build_case(p)`, add just one unrelated but type-valid transfer:
```python
e = p.Edge("unused-b", "origin-a", "holder-b", "TRANSFERRED_TO",
           p.LAB, "FROZEN:unused-b", subject_artifact_ref="artifact-b", sequence=9)
case = w.change_graph(sep, edges=sep.graph.edges + (e,))
```
- Both per-witness custody reports still return `LAB_CHAIN_PRESENT`; the pinned evaluator still returns `CONDITIONAL`.
- Yet the proposed standalone `custody_axis` moves from `NO_COMMON_CUSTODY_IN_DECLARED_GRAPH` to `COMMON_CUSTODY_DETECTED` with `("origin-a",)`. The extra origin-a edge is **not reachable from artifact-b's capture custodian origin-b**. Thus a `COMMON_CUSTODY_DETECTED` label from a union-of-declared-edge-endpoints does **not necessarily prove shared custodians along the selected valid chains**.
- [test_w1_custody_axis_counterexample_v0_1.py](test_w1_custody_axis_counterexample_v0_1.py) adds **2 ordinary positive controls and 1 explicit expectedFailure** for this design gap. No change to frozen evaluator, no authority promotion. Do not claim F3 solved. The eventual reviewed spec could select accepted paths before intersecting custodians, or name this metric as *potential shared declared endpoint*, and must test precision/recall.
- This new counterexample is distinct from Trae's observed shared-middle/initial/final custody gap: it demonstrates a **false positive of the proposed correlation implementation**, not an observed production attack.

## New GitHub-hosted CI evidence

To ensure each new unit-test command can **individually fail the job**, updated only the draft research W1 workflow `.github/workflows/w1-provenance-research.yml` with triggers for both new modules and the counterexample test and **three separate steps**; retained the original pinned source, cross-platform checks, 15 W1 cases, and existing 5 focused boundary tests.

**[GitHub Actions run 44290509475](https://github.com/SepehrGhanbari/Ario/actions/runs/44290509475)** from commit `210f42b1a0af41944b3dd963c12887d7942abb79`: **4/4 W1 jobs SUCCESS** on Windows 2022/Linux (Python 3.11/3.13). Retrieved actual Windows and Linux job logs, not just summary: each shows
- 15 existing W1 tests;
- 5 W1 focused boundary controls, **one expected failure** for unfixed shared-custodian F3;
- 6 custody-correlation tests, **one expected failure** for frozen evaluator not exposing that correlation axis;
- 4 masked latent-graph scaffold tests;
- 3 new counterexample tests, **one expected failure** for unreachable extra edge.
The two inspected OS logs show the corresponding `OK (expected failures=1)` lines. The other two job *step success* summaries and job conclusions were checked through GitHub API; individual log lines for those two were not independently quoted. **Three expected failures per job remain unfixed**, not three passing security properties.

An earlier run [44290400496](https://github.com/SepehrGhanbari/Ario/actions/runs/44290400496) already reported W1 success before the final workflow step separation. Implementation Regression was reported successful on the immediately preceding research commit; do not infer the latest project-wide regression conclusion without querying its exact SHA.

## Scientific and operational boundaries

- Historical R5NOV-16 and new W1-DEV-16 are separate sets; historical evaluator blob `b49b5fa6489a97a31a7056bf2fd8b1c6f2c03139` (23,876 bytes) is **not** the same as current `4faf010d...` (26,726 bytes), although Trae reports agreement on W1-DEV-16.
- The `16/16` development expectation score counts **three known hidden-dependency non-detections as matches**. In any new manuscript, identify comparison as co-designed developer boundary tests, not field accuracy. A policy trade-off between endorsement and abstention can be stated but its real-world prevalence is UNKNOWN.
- No independent latent ground-truth adjudication, sealed holdout, physical or administrative witness independence, human peer review, real keys, production trust or legal authorization was established.
- This work is supplementary research on a DRAFT branch only; the previously submitted journal-facing first article and its rights/fees correspondence remain unchanged. No merge, signer edit, trust activation, main alteration or journal manuscript substitution.

**Final disposition:** `TRAe_3RD_REPORT_ARCHIVED / TWO_SCAFFOLDS_REPLAYED / NEW_AXIS_FALSE_POSITIVE_XFAIL / CI_SCOPE_PASS / SCIENCE_REVISION_REQUIRED / HOLD / NO_MERGE`.
