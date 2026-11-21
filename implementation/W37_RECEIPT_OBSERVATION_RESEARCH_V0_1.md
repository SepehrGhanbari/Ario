# W37: Read-only receipt and ledger observation — prospective research integration

**Status:** RESEARCH_ONLY / PROPOSED / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO.

## Source and version boundary

- Candidate based on the public W35 synthetic checkpoint's actual Sigsum test-policy proof, and the original W36 pinned verifier and W37 scratch observer.
- The two **unchanged** Ario ledger modules must be imported from the repository's active `implementation/` installation, not from bundled duplicates:
  - `implementation/ledger_observation_adapter.py` (checked Git blob `39d16808ff7ebe976633c64fd2e3f30fc96ba2e3` at `main` `dcc9064da5e0f11e41d2048d3be1226777efe42b`)
  - `implementation/ledger_audit_bridge.py` (checked Git blob `f0ca882926ac4c3ed19cde5624070274ce095a43` at that commit).
- The library `research/w36_pinned_sigsum_v0_1.py` checks **only the exact W35 public byte image** against immutable SHA-256 pins, an Ed25519 key, a test-policy log, inclusion path and test-policy cosignatures. It does **not** verify new Sigsum objects, live freshness, full history or production custody.
- Five static fixtures are public/synthetic. **No private key** is included.

## Exact interface

From `implementation/` with pinned `cryptography` installed:

```shell
python -B -m research.w37_receipt_observation_v0_1 tests/fixtures/w37_w35_public/sample_events.jsonl --receipt-dir tests/fixtures/w37_w35_public
python -B -m pytest -q tests/test_w37_receipt_observation_v0_1.py
```

The CLI emits exactly one JSON result. Exit **0** means both read-only structural checks completed and matched the provided synthetic bytes; it means **neither successful external-event authentication nor permission to act**. Exit **2** means at least one input is UNKNOWN/REJECTED, including missing local ledger or malformed proof. Treat the structured `use_disposition` as authoritative for action; for this entire research profile it is always `SUSPENDED` and `may_use` is always false.

## Required invariants

1. `receipt_status=VERIFIED_SYNTHETIC_INCLUSION` states only that the supplied public synthetic checkpoint was included under the specified pinned policy. External-freshness/current-head checks remain `NOT_CHECKED`.
2. `ario_observation_status=OBSERVED` and `ario_bridge_status=OBSERVED` state current local-ledger byte consistency. They do not authenticate who emitted those bytes or that events happened outside the lab.
3. The W35 signed checkpoint and the W37 sample JSONL are different artifacts. Their digests are unequal and `cross_artifact_binding` remains `NOT_ESTABLISHED`, regardless of a caller-supplied claim. Hash equality *alone* would not establish an authorized semantic link.
4. Always `use_disposition=SUSPENDED`, `may_use=false`, `evidence_admission=NOT_EVALUATED`, `historical_event_truth=UNKNOWN`, `m0_evidence_created=false`, `audit_engine_called=false`, `signer_authority=NONE`, `trust_activation=NO_GO`, `genesis=NO_GO`, `production=NO_GO`.
5. No private keys, writes to the Ario event ledger, network calls, real memory, M0 `Evidence`/`Assessment` instantiation, or automatic trust/admission.
6. `claimed_external_bind` is intentionally **ignored** and reported as such, not parsed as an authorization.

## Source tests and test-environment boundary

- New prospective tests: 28 pre-existing W37 controls, plus source import pin, CLI positive, CLI missing-input negative, CLI corrupt-proof negative: **32 W37 focused controls**.
- Separate W36 baseline: **44 checks** and **300/300** single-bit proof mutations rejected (pinned test profile).
- Independent scratch combined run against *archival* Ario implementation source (14 Nov 2026) plus exact-blob current versions of the two observed modules: report exact counts from run log; this is **not** the full current `main` suite with this candidate installed.
- The original full-current `main` CI is linked separately; it did **not** include this new candidate.
- Any final GitHub PR must receive explicit path-scoped owner authorization and a **fresh source-pinned full CI run including the candidate**. Passing archival tests never authorizes merge.

## Held questions

- A verified W35 receipt does **not** attest the W37 ledger, its inventory completeness, temporal authenticity or history custody.
- W36 policy/file pins apply to a **single public synthetic test receipt**, not all future receipts. No generic Sigsum verifier is claimed.
- No real external high-water verifier, complete incident registry, or application-layer use authority is created.

**Disposition:** research PR review can proceed once authorized; core memory/identity/trust changes and merge remain NO_GO.
