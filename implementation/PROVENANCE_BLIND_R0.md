# Ario A/B/C provenance challenge R0 — public observable-only research candidate

**Status:** `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO`.

This is an **additive stacked research candidate**, not an evidence-admission, trust, production or signing feature. The parent Draft PR #257 supplies the v0.8 PR-log comparator; `main` is not changed.

## Provenance and scope

Design originated in Hallaaj's A/B/C **DESIGN_REVIEW / CHAT_REPORTED** counterexamples. The reviewer could not fetch exact GitHub source, validate receipts, or execute code independently. Original review and refined constraints: https://github.com/SepehrGhanbari/Ario/issues/251#issuecomment-6956801307. Related evidence-admission design #81 and provenance study #128.

This evaluator operates on **supplied synthetic observable data only**, using:

- **A:** actual in-repository `witness_provenance_experiment.evaluate_provenance()` and its existing *synthetic* `baseline()` test helper. A shared controller/source may be detected in the laboratory graph. `LAB_CONDITIONALLY_SEPARATE` is not verified independent custody. If a forged case claims a complete lab graph while hiding shared control, the conditional label can be falsely positive; this **known fabricated-completeness limitation** must not be masked.
- **B:** actual in-repository Draft #257 `pr_claim_audit_log_parser_v0_8.assess()` for text/log-snapshot *correspondence*. A separately defined research-only lab observer field does **not** constitute signature verification or independently proven execution. The author-provided `artifact_signature_claim` is always unverified.
- **C:** entirely **new research-only reducer** for historical receipt IDs, HEAD/run-attempt matching, lab-declared sequences and revocation. Neither historical signatures nor trusted clocks nor a real Ario M0 admission decision are verified. No receipt is deleted by this reducer.

## Public files in this PR

- `implementation/provenance_blind_r0.py` — evaluator; no network, real credentials, signing or filesystem writes. Input one JSON object on stdin, bounded to 24,000 bytes; output is one diagnostic JSON response.
- `implementation/provenance_blind_r0_observables.jsonl` — **24 synthetic observable inputs**: 8 A, 8 B and 8 C. They do **not** include fixture oracle truth or per-case expected classifications. Case IDs are research handles, not independent hidden labels. Some case behavior has already been described publicly; this set is **not** a genuinely blind third-party holdout.
- `implementation/tests/test_provenance_blind_r0.py` — **public oracle-free** fail-closed and interface tests. They deliberately do **not** measure accuracy against hidden truth.
- `implementation/PROVENANCE_BLIND_R0.md` — this limitation document.

**Never place** the local fixture generator, `private_oracle_not_for_pr.json`, truth mappings, full scoring results, or hidden holdout into this PR until a separate explicit unblinding decision. The original 24-case generator was written by the same author; separating its truth from the evaluator's stdin is **not** an independently curated hidden holdout and is **not** OS custody isolation.

## How to run

From `implementation/` of a checkout that includes this stacked PR and parent #257:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -p 'test_provenance_blind_r0.py' -q
python -B provenance_blind_r0.py < one_observable.json
```

`one_observable.json` is **one line selected from** `implementation/provenance_blind_r0_observables.jsonl` (not the whole JSONL). Python standard library only, reuses existing in-repository modules. The source importer loads the existing test graph helper solely to reconstruct explicitly synthetic A fixtures.

## Earlier private/same-author preliminary outcome (NOT reproduced by this public PR)

Prior local research bundle reported 24/24 agreement with **its author's own expected classifications**, 4/4 lab-only positive controls, zero global trust-status promotions, 17 abstentions and **one fabricated-completeness conditional false positive** in the prior author-side scoring. These were same-author fixtures and expectations; this new public PR must **not** represent those as independently verified or as end-to-end Ario truth. The new public tests only establish their stated local invariants. GitHub Actions status on the new HEAD must be checked **after** opening the PR, not predicted from earlier green tests.

## RED criteria for future independent reviewer

- A: any **real-world** independent-custody claim solely from names, keys, or self-reported complete graph; or an unmarked lab-conditional result presented as a real-world verified property.
- B: an artifact-signature *string* or self-hashed fake log promoted into verified artifact authenticity, independently attested pytest execution, or correct test semantics.
- C: a receipt for another HEAD/attempt promoted to current, any historical receipt erased, or synthetic order/revocation assumptions treated as trusted external time.
- Cross-domain: every final `status` must remain `UNKNOWN`, every `execution_attestation` `NOT_ESTABLISHED`, and `evidence_admission` `NOT_EVALUATED`; no automatic M0 conversion.

**Positive-control cost:** Count lab-conditional positives and false conditional positives separately; **all-UNKNOWN does not establish discriminating ability**. A truly independent, third-party holdout and separately administered witness custody are `NOT_RUN` / `NOT_ESTABLISHED`.

## Governance

No `main` change, merges, workflow/permission/ruleset changes, external contacts, production keys, trust roots, signer operation, Github admission or truth authority. Historical v0.1–v0.8 and witness-provenance source/test files remain unchanged. Repo `AGENTS.md` remains governing.
