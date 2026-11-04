# Ario TB-003 — Post-holder custody semantics: decision proposal v0.2

**Date:** 2026-11-05  
**Status:** RESEARCH_PROPOSAL_ONLY / NOT_ADOPTED  
**Scope:** synthetic LAB provenance. No live attestation, custody authority, signer, or M0 admission.  
**Source baseline:** PR #130 at `22f3378abbcdcf521db2b731b77ff2d3c26bbc56`; corrective draft PR #147. This file does **not** modify the frozen v0.1 contract.

## The question the previous contract did not answer

The v0.1 contract defines `HELD_BY: ARTIFACT -> CUSTODIAN` and requires a path from the capture custodian to the declared holder, but gives `HELD_BY` no event sequence, snapshot timestamp or validity interval. It does **not** specify whether a later `TRANSFERRED_TO(holder, T)` belongs to the evaluated custody period. A laboratory trace with `HELD_BY(A,H)` and later `H -> T` can therefore mean different things.

## Three materially different candidate interpretations

A. **Historical holder at a specified observation point.** `HELD_BY(A,H)` is a past assertion. Require an observation sequence/interval in a future schema; compromise after the observation can be irrelevant if an explicit boundary is authenticated (in LAB, asserted), but not inferred from a missing field.

B. **Current/latest holder.** `HELD_BY(A,H)` must be consistent with all later declared custody edges at a specified evaluation sequence. If H transfers to T and no return is shown, `HELD_BY(A,H)` is stale or contradictory. Future validation must constrain branch fanout, ordering, missing transfers and incomplete histories. This changes many existing tests and cannot be slipped into a minor fix.

C. **Nominated proof endpoint only.** `HELD_BY(A,H)` is the endpoint for *selected-path proof*, but subsequent strictly sequenced same-artifact transfers remain in the data. Whether their recipient's compromise affects administrative separation is a **separate explicit relevance rule**; ending the evidence path at H is not itself permission to ignore downstream actors.

**None is adopted by this file.** Until an authorized contract decision, implementation draft #147 returns `UNKNOWN / POST_HOLDER_COMPROMISE_RELEVANCE_UNRESOLVED` for a known compromised post-holder custodian reachable by eligible same-artifact transfers. A benign extra transfer alone remains a bounded positive laboratory case, not real-world proof.

## Required independent decisions before integration

1. What observation sequence, if any, does `HELD_BY` assert? Does missing time necessarily imply `UNKNOWN` or merely a nominated path?
2. Does administration cover the capture-to-holder selected path, the holder's continued descendants, or a defined time window?
3. Must a compromise interval overlap a transfer/holding window? How to treat an interval that ends **before** downstream receipt, starts **after** downstream transfer, or has an open end?
4. If common administration or the same storage object is independently established, those positive dependence findings must outrank post-holder `UNKNOWN`; preserve existing result precedence.
5. What happens with ambiguous parallel transfers, convergent sequences, unsupported origins, external/scope claims, and real-world missing events?

## Executable characterization (not contract approval)

Targeted synthetic tests in PR #147 include:
- post-holder compromised H->T and H->T1->T2: `UNKNOWN` in administrative separation, custody status unchanged;
- benign post-holder transfers, unrelated artifact links and disconnected compromised nodes: preserve conditional LAB result;
- common shared storage with post-holder uncertainty: `COMMON_CONTROL_DETECTED` outranks `UNKNOWN`;
- a compromised nominated holder: `COMPROMISED_BY_SCENARIO` outranks downstream uncertainty;
- compromise interval ending before T receives and interval spanning T receipt: **both** currently yield `UNKNOWN`, explicitly *not* a claim that time intervals overlap;
- a disconnected compromise interval: must not taint nominated witness.

These are observable expectations for the **research candidate**. Passing test results do not select A/B/C or prove that any external custodian is legitimate.

## Approval gates

The existing v0.1 contract must not be silently revised. A future change must have an explicit owner-scoped decision, versioned contract with fully specified time semantics, dedicated RED/GREEN controls and opposing reviewer analysis. #130 and #147 remain `HOLD`; `OWNER_SIGNER=HOLD`; `GENESIS/PRODUCTION=NO_GO`; `M0_ADMISSION=NOT_EVALUATED`.
