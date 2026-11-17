# Ario — Synthetic Receipt Inspection Lab v0.1

**RESEARCH_ONLY / DRAFT / HOLD / NOT_ADOPTED / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO**

## Exact source and scope

Parent: proposed, **unmerged** #268 HEAD `a190d085b4f07fd9a106107fb37725c0a41eef9d`. This lab adds only:
- `implementation/receipt_verifier_readonly_lab.py`
- `implementation/tests/test_receipt_verifier_readonly_lab.py`
- this research contract

No existing runtime, memory engine, SourceMonitoringGuard, signer, Ruleset, journal, or trust state is changed. `inspect_receipt` is a **pure, stateless, read-only** byte checker; it does not sign, register public keys, mutate a replay ledger, or write any file. Unit tests create **ephemeral synthetic Ed25519 keys entirely in memory**, never any founder/Ario or production key. `cryptography==46.0.4` is already pinned in `implementation/requirements-research.txt`.

## Mechanism and bounded inputs

Inputs supplied to `inspect_receipt`:
1. Canonically encoded, bounded JSON **receipt envelope** containing a versioned payload and an Ed25519 signature over `b'ARIO-RESEARCH-EXECUTION-RECEIPT-V0.1\x00' + canonical_payload_bytes`.
   The suffix `\x00` in the Python bytes literal represents exactly **one NUL byte**, not the two literal backslash-and-`x` characters.
2. Canonical, bounded JSON **policy snapshot** with public key ID, raw Ed25519 public key, time interval, `revoked` flag, and a fixed `SYNTHETIC_RESEARCH_ONLY` purpose.
3. Caller-supplied expected **SHA-256 of the policy bytes**, expected request digest and result digest.
4. Caller-supplied, immutable `frozenset` of previously spent nonces (bounded to 1024), plus an integer inspection epoch.

Validation is fail-closed for duplicate JSON keys, noncanonical encodings, malformed or oversized inputs, unexpected fields, wrong primitive types (including `bool` as an integer), signatures from the wrong key, invalid signature, revoked/expired declared policy, replayed declared nonce, late event, or mismatched request/result bindings. No input is echoed unboundedly into the response.

If *all metadata checks* pass, the result is `inspection=REVIEWABLE_ONLY`, `signature_valid=true`, `policy_pin_matches=true`, `reason_code=SIGNED_METADATA_CHECKS_PASSED`.

**All outputs, positive and negative, always declare:**
- `custody_independence=NOT_ESTABLISHED`
- `executor_authorization=NOT_ESTABLISHED`
- `execution_reality=NOT_ESTABLISHED`
- `semantic_support=NOT_ASSESSED`
- `claim_truth=UNKNOWN`
- `evidence_admission_allowed=false`
- `memory_write_allowed=false`
- `tool_execution_allowed=false`
- `signing_allowed=false`
- `trust_activation_allowed=false`

These flags are part of the output **only**, not enforced at arbitrary downstream callers. No real consumer is wired to the checker.

## Critical limitation: the policy anchor can be invented by the caller

The lab controller supplies **both** the policy snapshot and its purported externally pinned SHA-256. A single attacker/controller can generate an Ed25519 keypair, issue their own policy snapshot, compute its hash, and create a perfectly valid signature. The lab intentionally shows that this remains **non-authoritative**. A signature proves only possession of the private key paired with the supplied public key, under the syntactic profile; it does NOT establish who owned that key, whether their policy identity was authorized, whether the tool actually executed, or whether the output proves any claim.

Likewise, the caller supplies the `spent_nonces` set. If the caller omits a previous nonce, the checker cannot discover the true prior use. The checker **does not implement durable replay protection**. Its input set must not be called an independent witness or a trusted ledger.

An elapsed-time check of a caller-supplied epoch is an arithmetic property, **not trusted time**. A signature with a legitimate synthetic key is not real execution attestation. More than one synthetic signature does not establish independent custody.

## Independent reviewer must try to falsify

- Replace the policy key AND matching pin to demonstrate metadata signature validity without authorization.
- Tamper with the request/result bytes, nonce, key ID, signature, canonical JSON, expiration and revocation state. Expected: not reviewable.
- Reuse a declared nonce; also explicitly test the false-negative of replay when `spent_nonces` is empty.
- Inject booleans for exit code and epoch; oversized fields and duplicate JSON keys; malformed, extra and noncanonical JSON.
- Show that no output can grant memory, evidence, tool, signer or trust authority in this module.
- Identify whether `cryptography` runtime failures or abnormal Python object types can crash an untrusted API boundary.
- Show no historical `ACCEPTED`, `SUPPORTED`, `VERIFIED_EMPIRICAL` or `TASK_FINISHED` path was silently connected to this lab.
- Require a **separately administered** key directory, revocation journal, nonce/receipt history, verified source of time, and privileged-sink validation **before** any real authority claim is contemplated.
- Distinguish this protocol smoke test from independently administered dual-process or dual-machine custody. GitHub Actions in one repository does **not** prove independence.

## Governance recommendation (#216)

This lab may become a *read-only preflight* for a future experiment, but not an admission gate. Security promotion needs proof of a separate executor identity, permission authority, custody, revocation, durable nonce and fork handling, source/semantic relevance, and enforcement at the consuming sink. Historical records are append-only; never rewrite legacy statuses. No real signing, producer enrollment or trust activation in this PR.

## خلاصهٔ فارسی

در این آزمایش، ممیز می‌تواند بگوید امضای یک «رسید آزمایشی» از نظر ریاضی درست است یا نه و آیا با مشخصاتِ اعلام‌شده تطابق دارد. اما **اثبات نمی‌کند ابزار واقعاً اجرا شده یا کلید متعلق به شاهد مستقلی بوده**؛ چون مشخصات کلید، فهرست ابطال و سابقهٔ رسیدها را خودِ درخواست‌دهنده می‌تواند بسازد. بنابراین حتی نتیجهٔ مثبت هم هیچ مجوزی به حافظه، ابزار یا امضاکننده نمی‌دهد. این کار فقط یک قطعهٔ قابل‌آزمایش برای طراحی شاهد مستقل در آینده است.
