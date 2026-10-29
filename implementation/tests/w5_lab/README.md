# Ario W5-v0.2 — Offline Payload Byte-Binding Negative Laboratory

**Date:** 2026-10-17  
**Upstream repository:** https://github.com/SepehrGhanbari/Ario  
**Observed `main` pinned head:** `5e70fae681a7d03574a12f2b42230e1ba0860be6`  
**Classification:** additive, isolated TEST-ONLY proposal for Issue #81; not incorporated in upstream.

## Purpose

Test whether a separately supplied byte payload matches an untrusted, caller-declared W1-style SHA-256 reference. Explicitly **do not** infer that the bytes, their supplier, their time, or their lineage are authentic.

The previously reported W1/W2 stale-digest limitation is real: M0 sees the *claimed digest*, not separately retrieved/authenticated report bytes. These offline tests do not integrate a payload retriever into M0 or grant any source, reviewer, identity, or evidence-admission authority.

## Contents

- `w5_payload_binding_lab.py`: small standard-library checker; returned statuses are `MATCHED_BYTES_ONLY`, `MISMATCH`, `MALFORMED`, `UNAVAILABLE`, `BOUNDED`; all authority fields remain `UNKNOWN` or `NOT_EVALUATED`.
- `test_w5_payload_binding_lab.py`: the **unchanged original** 30 collected W5 cases.
- `test_w5_adversarial_review.py`: **13** new negative and positive adversarial cases (8 named functions).
- `initial_red.log`: original checker + new tests (**5 failed, 38 passed**, exit 1, expected RED).
- `green_seed1.log`, `green_seed8675309.log`: corrected checker (**43 passed**, exit 0 under both seeds).
- `mutation_results.log`: removing digest check yielded **3 failed, 40 passed**; over-catching process-control errors yielded **4 failed, 39 passed**.
- `manifest_sha256.txt`: SHA-256 checksums for every packet file except the manifest itself.

## New issue and narrow test-lab fix

The original W5 checker converted certain supplier failures (`OSError`, `TimeoutError`, `RuntimeError`) into a conservative `UNAVAILABLE`, but not `ValueError`, `KeyError`, `IndexError`, `TypeError`, or Unicode decoding errors, which propagated as exceptions. Expected hostile supplier errors now return `UNAVAILABLE` through a bounded explicit exception tuple. `AssertionError`, `KeyboardInterrupt`, `SystemExit` and `GeneratorExit` **must not** be hidden as supplier unavailability. This is a local laboratory-interface resilience fix, **not** a claim that any upstream M0 vulnerability was fixed.

## Run locally

With Python 3.13 and pytest (original review used pytest 9.0.2) from the packet's root:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -p no:cacheprovider -q test_w5_payload_binding_lab.py test_w5_adversarial_review.py
```

The code also passes when staged under `implementation/tests/w5_lab/` and collected from an otherwise empty `implementation/` directory, but **the full upstream M0 regression suite was not executed here**. The main GitHub Actions suite previously reported 1,030 successful tests, but that is separate preexisting evidence and **not a prediction about integrating W5**.

## Reproduction boundaries

- `byte_supplier()` is injected and **untrusted**; even matching claimed digest + bytes may have been fabricated by a single actor. It is not an independently verified byte store.
- Exact raw byte serialization matters. JSON equivalence does not imply byte equivalence.
- A synchronous callback is **not** protected against indefinite blocking, huge allocations before returning, or malicious side effects. Treat it as trusted *test fixture code only*, not a safe boundary for arbitrary external plugins. Production requires process isolation, source authentication, resource budgets, custody and consent review.
- No live signatures, keys, third-party trust root, signed grant, RAC/ARP adapter, M0 admission, Claim truth or historic custody established.
- `MATCHED_BYTES_ONLY != AUTHENTIC_SOURCE != INDEPENDENT_CUSTODY != AUTHORIZED_REVIEW != ADMITTED_EVIDENCE != TRUE`.

## Scope for possible future GitHub PR (no writes made)

Add exactly **four new files** under `implementation/tests/w5_lab/`: this README and the three Python files. No edits to M0 core, schemas, existing tests, contracts, workflows, ledgers, AGENTS.md, or current canonical state. Before GitHub branch/PR creation, confirm exact head and obtain separate scoped approval under AGENTS.md. Run exact-head CI, review expected collection and pass counts, review source and test authority boundaries. Do not merge automatically or close #75/#81.
