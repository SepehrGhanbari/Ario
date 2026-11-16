# W1 — Hidden dependency development rehearsal: observed results (2026-11-16)

**Status:** `EXECUTED / LOCAL_SYNTHETIC_DEVELOPMENT / NOT_BLIND / NOT_INDEPENDENT / NO_GO`

This report was added after an actual local execution against Ario's pinned, unmodified TB-003 evaluator, not merely the runner self-check. **The evaluation did not run a hidden independent oracle or production-effect gate.** No part of this report changes an existing contract.

## Reproducibility record

- **Repository:** [SepehrGhanbari/Ario](https://github.com/SepehrGhanbari/Ario).
- **Pinned evaluator:** `implementation/witness_provenance_experiment.py` at commit `2e7f83c6c7518012bed7fedfb12103ce9b7222ea`.
- **Evaluator Git blob SHA-1:** `4faf010d73219af63c254097e9c135da68d60078` (checked from GitHub and independently with `git hash-object` on the test computer before executing).
- **Runner:** `research/consensus/w1_hidden_dependency_rehearsal.py`, Git blob SHA-1 `73ea9c3091e7c6596eb502aa8601d58fa9b8d1b3` (same independent check).
- **Environment:** Windows desktop test host, Python 3.13 via `py -3.13 -B`; disposable `Ario/research-scratch/W1-20261116-r1` folder. No modifications to installed Ario sources, production state, keys or trust configuration.
- **Command:** `py -3.13 -B w1_hidden_dependency_rehearsal.py --source-file witness_provenance_experiment_pinned.py --output w1_report.json` with paths resolved inside isolated scratch.
- **Actual observed exit:** `W1_EXIT_CODE=0`. The runner wrote `w1_report.json`; SHA-256 reported by `Get-FileHash`: `cb69fef21df52f41a04a9631a9b9c89e3bfe7968389f400876b28e69a4cf5888`.
- **Result artifact CSV:** 81 lines (header + 80 cases); SHA-256 of the initial locally exported Windows CSV `2a53d7642c343dfb8273c1592144120179fa4b72529ce9129b657245a9f4b0cc`. A published CSV, if present, may normalize line endings and thus have a distinct file SHA; compare **content fields**, not naive CRLF/LF hashes.
- **Self-check:** 80 uniquely identified cases spanning **eight logical families** with ten seed/ordering variants per family. Ten variants of one design are not ten independent trials.

## Observed results

| Family (10 deterministic instances each) | TB-003 admin status | TB-003 source status | Visible conditional claim disagrees with latent synthetic world |
| --- | --- | --- | ---: |
| `independent_complete` | `LAB_CONDITIONALLY_SEPARATE` | `LAB_CONDITIONALLY_DISTINCT` | 0 |
| `visible_shared_admin` | `COMMON_CONTROL_DETECTED` | `LAB_CONDITIONALLY_DISTINCT` | 0 |
| `visible_shared_source` | `LAB_CONDITIONALLY_SEPARATE` | `COMMON_SOURCE_DETECTED` | 0 |
| `visible_shared_both` | `COMMON_CONTROL_DETECTED` | `COMMON_SOURCE_DETECTED` | 0 |
| `hidden_shared_admin` | `LAB_CONDITIONALLY_SEPARATE` | `LAB_CONDITIONALLY_DISTINCT` | 10 |
| `hidden_shared_source` | `LAB_CONDITIONALLY_SEPARATE` | `LAB_CONDITIONALLY_DISTINCT` | 10 |
| `hidden_shared_both` | `LAB_CONDITIONALLY_SEPARATE` | `LAB_CONDITIONALLY_DISTINCT` | 10 |
| `independent_incomplete` | `UNKNOWN` | `UNKNOWN` | 0 |

Observed counts: `cases=80`, `logical_families=8`, `model_premise_mismatch_count=30`, `non_authorizing_all=True`. Exit code `0` means **no violations of the runner's narrow non-authorizing output-field assertions**; it is **not** a security certification, proof that no effect can ever occur, or a complete regression pass. There was no attempt to invoke an effect, admit evidence, sign, or use a real custody witness.

The 30 mismatches are exactly the three hidden-shared-origin families repeated ten times. The evaluator sees a different graph from the latent synthetic reference; the graph is marked complete even though an edge/root/source was intentionally hidden. As a result, an affirmative lab-conditional diagnosis **relative to supplied premises** is not automatically a software defect, nor is the numeric 30/80 a real-world error rate.

## Interpretation and falsification

**Observed:** TB-003 responds as expected to modeled shared administrators/sources and incomplete declarations in these development fixtures. Hidden facts absent from an incorrectly declared-complete graph result in a conditional positive in all three hidden families. Output fields `production_custody_authenticity=NOT_ESTABLISHED`, `human_authorization=NOT_EVALUATED`, and `evidence_admission=NOT_EVALUATED` remained non-authorizing across 80 results.

**Inferred boundary:** A self-asserted `complete_control_surface=True`, `complete_source_surface=True` and `completeness_origin=FROZEN_TEST_CONTROLLER_REFERENCE` do not provide an independently authenticated external source inventory. The evaluator's documented conditional claims cannot be elevated to independent real-world witness truth merely because tests are green.

**Not established:** a defect in the existing TB-003 *contract*, real-world source authenticity, independent scorer, blind validation, statistical significance, lack of downstream unauthorized effects, or effectiveness of a proposed stronger evidence gate.

**Next genuinely informative test:** independent latent-world steward creates unseen cases; two separate labelers verify underlying ownership/source dependence, then evaluate an explicitly scoped downstream rule that refuses to promote unverified inventory to unqualified corroboration. Measure conditional *contract consistency* separately from latent-world *input fidelity* and *promotion safety*. Keep PR #199's `H_E`/`H_S` snapshot semantics separate. Require a separately verified inventory source before testing claims of stronger guarantees.

## Preservation / scope

- New research result artifact only; no modifications to the published 16/16 source-study, existing TB-003 evaluator/tests, R9, memory, signer, actual witnesses, rulesets or `main`.
- Historical development design and all earlier notes remain available in this research branch.
- The original pretty JSON result is retained on the test desktop scratch under `w1_report.json`; it was **not** published as part of this report. Its SHA is provided to identify exactly the observed file.
- **HOLD:** research review and separately controlled holdout required before any claim extension, merge, or trust activation.
