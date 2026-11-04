# Ario — Inclusive Compute Participation: Demand-First, Non-Paid Research Plan v0.1

**Status:** RESEARCH_DESIGN_ONLY / NOT_EXECUTED / NOT_AN_OPERATING_ECONOMY  
**Date:** 2026-11-04  
**Related:** [#94](https://github.com/SepehrGhanbari/Ario/issues/94) (incentive-first adoption research); [#139](https://github.com/SepehrGhanbari/Ario/pull/139) (mission, third-party and evidence safeguards; separate review scope).

## Provenance and boundary

This proposal distills owner-stated design constraints from privately retained conversations and public issue context; **the private transcripts are not published or independently authenticated here**. The design is a hypothesis, not evidence of user demand, service quality, device feasibility, independent reward validation, legal eligibility, or actual financial benefit. This document neither supersedes #94's incentive-feasibility research nor approves payments, tokens, a decentralized network, governance changes, or production.

## What must remain true

1. **Access without ownership.** Core access to Ario must not depend on buying, owning, or contributing hardware.
2. **No pay for possession.** GPU count, idle uptime, installed clients, fake tasks, or nominal device identities must not by themselves guarantee greater income or rewards.
3. **High capability only when useful.** Faster GPUs may potentially earn more *only when fulfilling genuinely requested, independently checked services*, with higher value or volume actually justified by demand. More hardware is not evidence of more useful service.
4. **Real entry for weaker devices.** Low-end GPUs, CPUs, and opt-in phones should have access to eligible, meaningful work; do not equate “can register” with “can deliver useful tasks at acceptable net cost.”
5. **No guaranteed yield.** No fixed salary, passive mining-like return, token value, minimum revenue, or prediction of profit is promised.
6. **Owner-first device safety.** Participation is optional, interruptible, revocable, and subject to local user-configured temperature, battery, network, charging, energy-cost, and time limits. A coordinator cannot override a local stop. Missing sensor support must be disclosed; potentially unsafe workloads are ineligible, rather than silently ignoring the stop.
7. **Demand and service before money.** Begin with a bounded non-paid service trial, measuring real requested work, quality, energy, latency, and inclusion. Price and reward scenarios are later *simulations* until separately approved.
8. **Privacy and mission beyond participants.** Prefer aggregate and privacy-minimized observation. Measure effects on people who do not own devices or use Ario separately; absence of sampled nonusers is **UNKNOWN**, not proof of satisfaction or zero harm.

## Bounded research stages (no launch authorization)

| Stage | Proposed activity | Evidence needed | Forbidden inference |
|---|---|---|---|
| T0: offline synthetic | Opt-in local benchmarks of narrowly specified, low-risk/verifiable tasks on low-end, ordinary and high-end devices; collect nonidentifying thermal, cost, latency, correctness and interruption aggregates | Task-level reproducible fixtures, explicit device limitations, user-controlled stop verified, failures retained | T0 demand, profit, earning entitlement or readiness for live distribution |
| T1: non-paid genuine-demand pilot | Only with separate, scoped participant permission, match a bounded set of genuine user requests to volunteer devices; compare against a non-distributed baseline | Actual requests vs accepted/validated/user-accepted deliveries, retries, unserved needs, net device costs, and opt-out events | A simulated request is demand; a provider's accepted task implies payment eligibility |
| T2: analysis and adversarial simulation | Model useful-work allocation, fair opportunity queues, validation costs, Sybil/collusion resistance, concentration and budget exhaustion from T0/T1 observations | Preregistered positive/negative controls, sensitivity ranges, comparable device classes and honest uncertainty | Simulated credits, tokens or cash imply real funding, rights, legal compliance or owner approval |
| T3: decision gate (not granted here) | Independently review evidence and proposed incentive instruments; separately decide whether even a limited paid experiment is warranted | Source- and task-grounded evidence, appeal and cost mechanisms, security/privacy/legal review, risk limits, explicit fresh authorization | Passing research tests constitutes a permission for production or financial operation |

**Precondition:** No persistent background worker, real-user content ingestion, inbound network service, wallet, cloud key, production account, or externally exposed task broker in T0. T1 is **not authorized by this document**.

## Explicitly falsifiable comparisons

Preregister task categories, eligibility constraints, observation horizon and thresholds **before** any trial (none are invented here). Compare:

- **A: naive fastest-GPU matching** versus **B: demand-matched allocation with a bounded fair-opportunity queue**, holding workload, total legitimate demand and verification requirements fixed.
- **Quality-adjusted useful service**: user-requested work that was actually delivered and validated, excluding synthetic, duplicate, collusive and self-requested fake jobs. Treat independent validation limits as explicit.
- **Inclusive opportunity, not equal hardware returns**: eligible task offers, completed useful work, opt-outs, net energy/thermal cost and successful participation by low-end/CPU/phone class. Report cases where a class is technically eligible but reliably cannot finish.
- **Mission checks**: compare service access with and without donated compute for people unable to contribute hardware, including offline/nonpaying users where ethically observable. Do not collect identifiable poverty, disability or location information solely to improve a score.

The allocation hypothesis fails if the apparent fairness gain comes from useless work, unverified identities, thermal harm, concealed costs, exclusion of unobserved users, or task-quality loss outside preregistered limits. If demand or ground truth cannot be established, state **UNKNOWN** rather than projecting revenue.

## Adversarial fixtures (PROPOSED / NOT_EXECUTED)

| ID | Counterexample | Failure signal to measure |
|---|---|---|
| EC-T01 | One actor represents 100 nominal devices | Allocation gain attributable to duplicate identities rather than independently useful work |
| EC-T02 | Requester and supplier collude to fabricate a completed service | False validated deliveries and reward claims |
| EC-T03 | Expensive GPU wins through speed but returns lower-quality work | Quality-adjusted useful delivery decreases |
| EC-T04 | Phone repeatedly reaches temperature/battery stop | Local stop ignored, override attempted, or device silently penalized for safe exit |
| EC-T05 | Nonusers and offline owners are missing from the sampled denominator | False universal success or absence-of-harm claim |
| EC-T06 | Verification costs exceed user value of completed tasks | Negative net benefit despite apparent task throughput |
| EC-T07 | A large owner controls the scheduler and thousands of nodes | Allocation or future reward concentration masked by node count |
| EC-T08 | Connectivity drops during task and duplicate retry occurs | Duplicate payment-like claims or fabricated success (simulation only) |
| EC-T09 | The evaluator returns UNKNOWN on every sample | False “good epistemics” score from missed fully evidenced positive controls |
| EC-T10 | Hardware and local sensor APIs cannot verify thermal boundaries | Unjustified claim of safe phone/low-end participation |

## Reporting and admission limits

Report separately **observed**, **derived**, **self-reported**, **not measured**, **unknown**, and **proposed** outcomes; label validation of task output separately from independent source provenance. Publish any synthetic fixture and test scripts only after their own code and privacy review; do not count proposed tests as run. Avoid centralizing full user prompts, hardware fingerprints or personal identities. Establish a contest/appeal path before any real reward system.

**Decision:** No production compute economy, payout, minting, real insurance, financial account access, or network activation without independently reviewed demand, service correctness, device safety, economics, anti-abuse evidence, privacy controls and explicit founder authorization. The research plan does not modify security, signer, trust, Genesis, governance, M0/N1 or evidence admission. **OWNER_SIGNER=HOLD; GENESIS/PRODUCTION=NO_GO.**

## Independent CodeRabbit review requested

Please challenge (1) whether the task-value proxy can be gamed by self-demand, (2) how to falsify meaningful low-end opportunity without fake quotas, (3) privacy-preserving Sybil/collusion defense, (4) hard-stop claims when sensors are unavailable, (5) false mission success from unobserved nonusers, and (6) whether the step from non-paid pilot to any financial trial is clearly unauthorized here. Prefer concrete negative controls, expose assumptions and contradictions with #94; **do not infer activation or real-world evidence from this text**.
