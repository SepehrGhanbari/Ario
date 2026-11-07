# Ario economy: indistinguishable benefit-worlds contract v0.1

**RESEARCH ONLY / NO NETWORK, PAYMENTS, HARDWARE, IDENTITY, AUTHORITY OR ADMISSION.**

Linked public discussion: [Ario Issue #94](https://github.com/SepehrGhanbari/Ario/issues/94#issuecomment-6691587038). The current CodeRabbit critique recognizes six separate claims and warns that signed receipts alone cannot distinguish independent demand from captured demand or real delivery from colluding false reports. **The code implements a toy subset, not the full proposed governance or fairness mechanism.**

## Scope and interpretation

- `MOCK_CORRECT`: a synthetic task-specific check reported pass. Does not prove independent need or funded settlement.
- `FIXTURE_CONDITIONAL`: a caller-selected `ScenarioAssumptions` field **assumes** the named claim for the synthetic world; the code verifies no external independence. This must **never** be translated into a real-world `GREEN` or an authorization to distribute money, do work or gather identity data.
- `REFUTED`: fixture supplies direct contradictory mock evidence to the named claim.
- `UNKNOWN`: no admissible evidence in the toy inputs. Not a judgment that a person is dishonest or ineligible for assistance.

The six claims in `CLAIMS` are disjoint. There is intentionally no `PAYOUT_APPROVED`, `REAL_PERSON_VERIFIED`, `FAIRNESS_PROVEN`, or `PRODUCTION_READY`. Two distinct `HiddenScenario` objects (independent vs captured) each pass through `project_reported_receipts`; that generator explicitly omits hidden controller/delivery truth. Their projected in-band observations are equal, while independently generated different self-report inputs are *not* equal. A policy seeing equal projections must issue equal verdicts. This is a synthetic observational-equivalence counterexample, **not** proof about actual receipt signatures or human behavior. A positive real-world conclusion based only on receipts is therefore unsupported.

The local-device pilot refusal helper does not contact any device. An apparent positive means only `TOY_ELIGIBLE_NOT_AUTHORIZED_TO_RUN`; even a mock-safe input is not permission or evidence of physical safety. No earnings are guaranteed, no enrollment or government ID is required, and any help for people outside the computational network must remain an independent policy discussion with privacy and delivery uncertainty explicit.

## Commands

From this directory: `python -m unittest -v test_claim_model`. Standard-library-only, no credentials, no network or side effects; explicitly invented data.

## Limits and proposed falsifiers

This model **does not prove independence**. It trusts the fields of `ScenarioAssumptions` under stated assumptions; a colluding observer can falsely fill them. A future negative control should supply a valid-looking independent attestation from a common-controlled observer; real-world verdict must stay `UNKNOWN`. The model does not assess requester beneficial ownership, offline delivery, welfare by unobserved populations, safe device containment or economic viability. Missing data are not zero. Pending independent review before any promotion beyond this lab.

**OWNER_SIGNER=HOLD · GENESIS/PRODUCTION=NO_GO · M0_ADMISSION=NOT_EVALUATED.**

## Added bounded contracts from CodeRabbit #94 (2026-11-07)

- **Optional telemetry must not govern route access.** `mock_support_route` ignores `telemetry_opt_in` entirely. A route offer and queue rank are not evidence that a person actually received aid. A refusal of observation never implies fraud, zero welfare, or grounds to deny aid.
- **Baseline-relative opportunity is not net device benefit.** `compare_mock_opportunity` can refute preservation of a weak device's completed tasks if aggregate service stays unchanged and the device loses a completion. If the baseline is unavailable or total service falls, it returns `UNKNOWN`; a non-loss remains only `FIXTURE_CONDITIONAL`, not a fairness guarantee. Detailed participant energy costs not shared must leave `NET_WEAK_DEVICE_BENEFIT=UNKNOWN`.
- These are pure synthetic comparators, **not** a route operator or a scheduler; no private personal data, money, enrollment, hardware or network requests are used. The independently consented pilot remains unapproved.

Follow-up review: https://github.com/SepehrGhanbari/Ario/issues/94#issuecomment-6704471710 .

## Methodological corrigendum v0.2 — 2026-11-07 (append-only)

Prior public research HEAD: `15bbc06a3e56b30df8da36c10aaa7e3f842cb40e`. Its `compare_mock_opportunity` function used **completed-job counts alone** to emit `REFUTED` or `FIXTURE_CONDITIONAL` for purported opportunity preservation. The previous “baseline-relative opportunity” description above is **superseded for causal/fairness interpretation**; the historical file remains available at the pinned parent commit, not rewritten.

Current narrow replacement `classify_mock_completion_delta` reports **only synthetic descriptive count changes**: `NO_DROP`, `WEAK_DROP`, `TOTAL_DROP`, `BOTH_DROP`, or `UNKNOWN`. It validates exact integer, nonnegative counts and refuses malformed present fields even if another field is missing. It intentionally does **not** return the separate `Verdict` fairness/claim enum. `WEAK_DROP` is neither proof of discriminatory scheduling nor evidence that a worker has done failed work; `NO_DROP` is not a real-world GREEN. The misleading function name was removed rather than retained as a would-be fairness oracle.

The same 1→0 weak-device completion drop and 10→10 total completions could reflect exclusion, independent demand falling 20→10, changed task mix, loss of eligible weak-device time, safety STOP, or voluntary opt-out. The toy has no independent denominator, verified task-value comparison, coercion/consent proof, or net energy cost measurement. **All such causal opportunity and real welfare claims remain UNKNOWN**, and no earned wage is justified by hardware ownership or invented shadow tasks. The four label cases are a syntax-level regression matrix, not empirical user outcomes. Optional telemetry refusal must not reduce access to non-work assistance.

Peer-review provenance: CodeRabbit [demand-vs-completion critique](https://github.com/SepehrGhanbari/Ario/pull/152#issuecomment-6704625556); Ava [bounded peer-discussion question](https://github.com/SepehrGhanbari/Ario/pull/152#issuecomment-6704838187). Gemini and Claude peer model responses were unverified reasoning over supplied excerpts, **not independent repository attestations**. All real-work, payout, signer/trust, Genesis and production gates remain HOLD / NO_GO. This corrigendum does not approve a merge.

### Corrigendum v0.2.1 — partial-pair consistency

Additional fail-closed detail after peer review: validate each present weak/total completion pair before returning `UNKNOWN` for other missing fields. Thus missing baseline weak count does not excuse an impossible candidate pair (weak 5, total 4), and vice versa. This is a **synthetic schema** requirement only; it does not establish comparable periods, active device eligibility or independent demand. Parent research commit: `d905dd675876bc20eed04bbb6d5ce9539e9c7fee`. No prior test or evidence record is erased.


### Corrigendum v0.2.2 — strict evaluator slot IDs (2026-11-07; candidate only)

Following CodeRabbit's scoped suggestion in PR #152 issuecomment-6709694151, the local candidate explicitly validates every observation slot ID **before** duplicate detection. Each ID must be a nonempty hashable string (including Unicode and hashable `str` subclasses); malformed IDs cause `ValueError("invalid slot id")`, not accidental acceptance or leaked `TypeError`. Exact string equality remains unchanged; no trimming or Unicode normalization is performed. An empty slot tuple with zero signed receipts is valid. This evaluator contract intentionally does **not** import the projector's ASCII namespace constraint. No real identity, device service, fairness, payment or authority is established. RED and GREEN must be independently reported; branch-protection approval remains separate and HOLD/NO_GO remain unchanged.
