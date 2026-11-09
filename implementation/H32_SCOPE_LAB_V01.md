# H3.2 Scope-Attribution Lab v0.1 — Research-only

**Status:** New independent deterministic synthetic prototype, **NOT Ario M0**.  
**Date:** 2026-11-09  
**Reference discussion:** [Ario Issue #169](https://github.com/SepehrGhanbari/Ario/issues/169)  
**Frozen benchmark:** H3.2 v0.2 is **unchanged**; its original 12 cases, private oracle, and published SHA-256 `26264fe793dc0ade8923549425dbc4fccdc4482493571a1b37b280230d72b9c1` are **not inputs to this prototype's tests**.

## What this actually implements

`h32_scope_lab_v01.py` is a standalone, deterministic research function and CLI for **synthetic explicitly structured records**. It returns distinct `earliest_observed` and `earliest_global` for five modeled checks:

1. `display_qualifier_omission`: a previously supplied **display-facet key** disappears in a later record; merely changing a value does not count as *omission*.
2. `typed_metadata_loss`: a previously supplied typed metadata key disappears (including an explicitly `null` later metadata object); changed values are not *loss*.
3. `preservation_contract_breach`: an **explicit, versioned-by-fixture interval** (`start_at` through `end_at`, inclusive) requires exact named facet values in a specified `typed` or `display` channel. No implicit or persistent authority is inferred from a Boolean.
4. `unsupported_scope_assertion`: under a named **cited-justification** policy, available and accepted cited guarantees cannot cover the typed assertion's claimed scope. A conditional content result is retained alongside an effective justification result.
5. `unsupported_firm_certification`: the same insufficient cited justification expressed with typed `strength=CERTIFIED`; tentative text is not silently upgraded to firm certification.

The five checks are **research operationalizations**, not claims to have reproduced the original v0.2 five-label oracle or its ambiguities. The lab does not interpret free text. `display_text` is an optional inert observation field: equal displayed words with unequal evidence are intentionally distinguishable through the structured evidence channel.

## Boundaries and epistemic semantics

- A guarantee's `verification` is one of `TEST_VERIFIED`, `TEST_INVALID`, or `UNVERIFIED` **supplied by the fixture writer**. The lab does **no cryptographic validation**, authenticates no real evidence, and confers no source authority. Its output explicitly states `provenance_validation: NOT_PERFORMED_TEST_PREMISES_ONLY`.
- `available_at`, `verified_at`, and `published_at` are separate **synthetic integer ticks**. The fixed policy requires availability **and** test verification no later than the asserting event. Public publication is **not** required and is never treated as proof of contemporaneous availability.
- Every assertion supplies explicit `citations` and `citations_complete`. Evidence that exists but is not cited does **not** rehabilitate a cited-justification verdict. An unknown citation or incomplete citation set can make justification `UNKNOWN`, unless a known eligible cited guarantee already covers the claim.
- Known narrow scope cannot cover a wider scope, even when verification is unknown. **Unsupported by cited evidence is not the same as a false underlying claim.**
- The fixture supplies explicit finite atom sets for `facility`, `period`, and `population`. Assertion coverage requires set inclusion across the Cartesian product of these dimensions; the program never guesses real-world containment relationships.
- `coverage/single-item-v1`: one eligible cited item must cover every claimed cell. `coverage/union-v1`: the union of eligible cited items may cover them, provided claim kind, strength, and temporal eligibility match. These are **different contracts**, and results cannot be silently pooled. No authority delegation or independence check is inferred.
- **Observed vs global:** a definite locally observed error remains visible when earlier history is incomplete, but `earliest_global=UNKNOWN`. Even with a declared complete history, an earlier unresolved assertion can make global ordering unknowable.
- The status `UNKNOWN` means the modeled question was examined but material evidence is insufficient; `NOT_EVALUATED` denotes a separate task not run. `NOT_IMPLEMENTED` requires a closed-boundary capability audit and is **not** asserted repo-wide here.
- Strict schema, bounded events/evidence/obligations, bounded atom expansion, duplicate-ID rejection, deterministic JSON output, 256 KiB CLI input cap, and symlink input refusal support **bounded synthetic testing**. They are not a production security audit.

## Use (standard-library-only Python)

From repository root:

```powershell
python -m unittest discover -s implementation/tests -p test_h32_scope_lab_v01.py -v
python implementation/h32_scope_lab_v01.py PATH_TO_SYNTHETIC_FIXTURE.json
```

One fixture is a JSON object with exactly `case_id`, `domain`, `events`, `guarantees`, `obligations`, `history_complete`, and `coverage_policy`. Each scope uses explicit named aliases for `facility`, `period`, and `population`; domain aliases enumerate finite atomic members. Events specify increasing `at`, `actor`, `display_facets`, `scope_meta`, and an optional typed `assertion`; guarantees specify source scope, kind, strength, verification **premise**, and three synthetic time fields. The unit tests contain complete examples and matched pairs.

On a valid input, the CLI returns JSON with `execution_attribution=STANDALONE_RESEARCH_ONLY_NOT_M0`, five checks, per-event citation diagnoses, and `ario_m0_h32_runtime_score=NOT_EVALUATED`. Invalid input is rejected with a nonzero exit code and **never** a success label.

## Falsification-oriented coverage actually exercised locally

The independent synthetic test suite tests equal/broader/narrower population scopes, same-display/different-cited-evidence pairs, strict-superset support, unknown and invalid verification **premises**, evidence available or verified after an assertion, delayed public publication, uncited broader evidence, complete/incomplete citations, unknown references, the two incompatible composition policies, wrong claim kind/strength, tentative versus firm certification, three structural checks, obligation lifetime, incomplete earlier history, earlier local uncertainty, case-ID renaming, JSON key reordering, strict schema rejection, and CLI input handling.

**Local author run:** `python -m unittest discover -s implementation/tests -p test_h32_scope_lab_v01.py -q` — **36 tests passed**. This is a test report for this **prototype only**; it is not GitHub CI, an independent review, or an Ario M0 benchmark run. The number must be updated if source/tests change.

## Open limitations and planned adverse reviews

1. **R0 is not finished repo-wide.** The existing direct M0 CLI has a different schema/output; this prototype does not integrate with or claim to upgrade it. See `H32_R0_CAPABILITY_REVIEW_2026-11-09.md`.
2. No cryptographic proof, real signature verification, independent verifier, runtime process attestation, anti-replay nonce, or engine-output dependency measurement is implemented. A wrapper could still do all these calculations without M0. **No M0 labels are credited.**
3. The synthetic scope-domain atom mapping, evidence premise, available/verified times, claim kind and strength must be supplied as structured inputs; they are not extracted or corroborated from real text, medical records, or independent witnesses.
4. No held-out blind independent benchmark has yet measured this implementation. Existing local tests are author-visible development fixtures, **not** an independently established oracle or comparative superiority result.
5. Display-facet value changes (as opposed to omissions), implicit/persistent preservation obligations, timestamp ties, cryptographic authority, unknown domain completeness, overlapping contradictory evidence, evidence retraction, and provenance/authentication of the domain itself require separate, versioned specifications and tests.
6. Before a later engine attribution claim: pin the M0 callable and adapter; independently observe boundary input **and output**; run an engine-unavailable negative control, semantic-output substitution with unchanged process status, and matched unseen scope/provenance counterexamples. Freeze rules, expectations, artifacts and comparison methodology before any prospective score.

**Nothing here changes signer gates, governance, identity, memory, trust activation, or the frozen v0.2 benchmark.**
