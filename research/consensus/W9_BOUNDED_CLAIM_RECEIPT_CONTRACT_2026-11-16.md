# W9 — Bounded claim-to-receipt relationship, without authenticating the receipt

**Date:** 2026-11-16  
**Disposition:** `RESEARCH_ONLY / SYNTHETIC_EXECUTED / CONSTRAINED_PREDICATE / NO_AUTHORITY / V2_NOT_ADOPTED / HOLD`  
**Scope:** Extend [W8's reproduced semantic-overpromotion gap](W8_CROSS_MODULE_SOURCE_RELEVANCE_AND_V2_BOUNDARY_2026-11-16.md) in [Draft memory PR #210](https://github.com/SepehrGhanbari/Ario/pull/210) and the still-protected [Issue #216](https://github.com/SepehrGhanbari/Ario/issues/216). **No core-code change, signer, host trust, live memory ingestion or merge.**

## 1. Scientific question and what we can currently test

W8 actually demonstrated that `exit_code=0` plus self-supplied SHA-256 can elevate a contradictory proposition (`Target A exists` despite `NOT_FOUND: Target A`) to `VERIFIED_EMPIRICAL`, then pass `require_verified=True`, become a consolidated `ACCEPTED` node and trigger a **synthetic** prospective cue. An error exit appropriately blocked that chain. The observed failure is an overly broad claim-to-evidence promotion policy; **not** cryptographic hash failure or proof of malicious access to a production system.

W9 therefore studies the narrower question:

> Can a typed, machine-readable **declared evidence relation** distinguish exact support, direct contradiction and out-of-scope/ambiguous inputs for *one specified claim family*, without falsely promoting the result to world truth or execution authority?

**We cannot solve arbitrary natural-language entailment by a JSON checker, and do not claim to.** W9's single permitted toy predicate is `FILE_EXISTS`. The receipt's claimed output must have the versioned `ario.lab.fs_presence.v0` schema with exact `present` boolean, `target`, `principal` and `at` fields. The claim must match those subject/scope/time fields byte-exactly. All fields are **self-reported laboratory strings**, not a real filesystem attestation. A populated hash field remains a self-consistency checksum, not an independent trust root.

## 2. Actually executed reproducible artifacts

- [Contract, pure Python stdlib](w9_bounded_receipt_contract.py) — **exact locally executed Git Blob** `f795065ce06d88c2ca017270f5036eb028029220`.
- [26 prewritten positive and negative controls](test_w9_bounded_receipt_contract.py) — exact locally executed Git Blob `8cd1804307ddc7c88c974903cf30499522dc54be`.
- [JSON of actual test-run outcomes](W9_BOUNDED_RECEIPT_RESULTS_2026-11-16.json) — exact locally produced Git Blob `ad9df9012197fb6c3e15cba55f857c7c7de5215f`.
- Execution: `python test_w9_bounded_receipt_contract.py` in the **isolated ChatGPT scratch container, Python 3.13**, exit `0`. 26 hand-designed assertions matched. No desktop host, installed Ario service, actual `inspect_directory` program or independent source ran. The previously used remote Windows device disconnected; this standalone experiment does **not** depend on it.
- Each published file was downloaded back through the GitHub connector and checked to have **exactly the same Git Blob SHA as the local tested file**; a successful upload is not presumed from merely calling the write action.

Summary of 26 deterministic controls:

| Observed declared relation | Count | Example |
| --- | ---: | --- |
| `DECLARED_MATCH` | 3 | `FILE_EXISTS=true`/declared `present=true`; also explicit `false/false` and two matching **non-independent** receipts |
| `DECLARED_CONTRADICTION` | 1 | Claim `FILE_EXISTS=true`, receipt declares `present=false` |
| `DECLARED_CONFLICT` | 1 | Two differently identified, same-scope self-reported receipts disagree |
| `UNKNOWN` | 21 | Cross-target/principal/time, duplicate ID, duplicate JSON key, nonfinite, wrong typed boolean, bad digests, empty/nonzero/oversized output, unsupported predicate, no receipts |

**26/26 is the test runner meeting its own anticipated labels, not scientific accuracy against a held-out gold oracle.** No independent source author, evaluator adversary, blinded set or real filesystem check was used.

## 3. The evidence ladder this prototype deliberately enforces

For *every* case, including positive `DECLARED_MATCH`, the output also says:

```json
{
  "execution_authenticity": "UNKNOWN",
  "source_custody": "NOT_ESTABLISHED",
  "assessment": "NOT_ASSESSED",
  "world_truth": "UNKNOWN",
  "action_authority": "NONE",
  "memory_admitted": false
}
```

A *positive byte relation* means only that the caller's offered content is internally consistent with a single typed proposition: it **does not** authenticate the operator, prove the real event happened, establish evidence independence, assess the true-world proposition, or approve future actions. Even two different `receipt_id` strings represent zero proven independent witness operators.

**Fair comparison to W8:** In actual #210 tests, a mismatched `NOT_FOUND`-versus-`FILE_EXISTS` was previously promoted and a downstream synthetic intention triggered. W9 explicitly emits `DECLARED_CONTRADICTION` for the comparable structured negative case, and never produces an assessment-positive status. This is a **conceptual, task-restricted contrast**, not a new, matched same-run A/B comparison of full #210 versus W9 on externally authored cases. Legacy #210 output and W9's new declared relation are **not the same type of verdict**.

## 4. Typed proposed sidecar boundary for #216 (not adopted)

Any future opt-in V2 should distinguish:

1. `capture_state` — source bytes and versioned digest: `RECORDED` means stored, not true.
2. `declared_relation` — typed claim-to-receipt relation: `DECLARED_MATCH`, `DECLARED_CONTRADICTION`, `DECLARED_CONFLICT`, `UNKNOWN`. For unspecified predicates return `UNKNOWN`.
3. `execution_authenticity` — separate, externally warranted tool/receipt origin; in W9 always `UNKNOWN`.
4. `assessment_state` — `NOT_ASSESSED` unless independent, approved evidence-assessment mechanism considers reliable provenance, semantic relevance, scope and counterevidence. **No implicit transition to `SUPPORTED_IN_SCOPE`**.
5. `action_authority` — remains `NONE` unless **another separately authorized boundary** grants an actual task/effect.

These proposed axes extend the already recommended **Option B: immutable V1 + opt-in V2 sidecar** from #216. No existing `ACCEPTED`, `VERIFIED_EMPIRICAL`, `SEM` IDs, `negates`, raw/trimmed line hash references or historical prospective predicates are rewritten, silently reinterpreted or dropped. Ambiguous ID/digest mapping stays `UNKNOWN`. Producer schema and consumer semantics must be versioned as a whole; changing one enum while a downstream cue still treats `status == 'ACCEPTED'` as permission would not resolve W8.

## 5. Additional technical caveats / falsifiers

- This test's `stdout_sha256` and `lock_sha256` are **self-issued**. They check accidental inconsistency, not a cryptographic attestation or proof of independent execution. An attacker controlling the receipt issuer can forge a consistent pair.
- `at` is an **untrusted string** matched byte-exactly. This demonstrates scope binding, not trusted clocks, time validity, Unicode canonicalization policy, filesystem path alias resolution, symlink identity or retention rules.
- The maximum of 4,096 UTF-8 bytes is enforced **after the input string already exists and a digest is computed**. It does not bound upstream allocation, parser CPU, caller resources or real filesystem traversal.
- The parser is strict about JSON duplicate keys, nonfinite constants, wrong boolean types and unknown schema, but **does not prove completeness of observed real-world events**.
- A two-receipt match is *not* a two-human witness finding; source diversity and authenticated custody are outside the lab.
- A general claimant may need temporal validity ranges, denial/permission scope, structured uncertainty and proposition-specific evidence predicates. Do not generalize a single file-existence toy to model beliefs, source monitoring broadly or fact truth.
- No live reading, patching or invocation of #210's core code occurred during W9, because its prior pinned source was already tested at W8 and the remote PC went offline. This avoids fabricating a new A/B run.

## 6. Decision and next research gate

**ADOPT for study:** distinguish `declared_relation` from `assessment` and `action_authority`; preserve positive controls so a future model is not vacuously safe by refusing everything; maintain `UNKNOWN` for out-of-contract inputs.

**TEST next:** a genuinely independent *producer/validator* pairing with immutable masked claims and sealed source facts held by an external custodian; challenge correct/false path aliasing, stale observations, wrong principal, compromised shared receipt issuer, and independently captured observation failures. Compare **false promotion and false rejection** separately against #210 and a transparent typed baseline.

**HOLD:** owner decision Option B, source trust/key custody, real-world memory assessment, any production patch, retrospective V1 status migration, runtime cue change and main merge. A code snippet, deterministic test suite or successful CI never confers protected owner approval.

**Scientific anchor:** Johnson, Hashtroudi & Lindsay (1993), *Source Monitoring*, DOI [10.1037/0033-2909.114.1.3](https://doi.org/10.1037/0033-2909.114.1.3) concerns fallible source attribution, **not** authentication by origin labels. The prior W2/W8 project findings and [#216 migration decision matrix](https://github.com/SepehrGhanbari/Ario/blob/c456f9886fdebe0aee0d529f554603dcf4c04384/implementation/MEMORY_V2_MIGRATION_DECISION_MATRIX_V0_1.md) remain the direct Ario engineering evidence; neither this scientific literature nor W9 establishes a production-safe AI source assessment.

`RESEARCH_ONLY / CI_NOT_AUTHORITY / OWNER_DECISION=HOLD / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO`.
