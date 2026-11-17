# Ario — Declared Authority History / Anti-Rollback Research v0.1

**DRAFT / RESEARCH_ONLY / HOLD / NOT_ADOPTED / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO**

## Source and explicitly limited goal

This is a new **read-only**, bounded, deterministic history-comparison experiment, stacked on unmerged Draft #269 (the synthetic Ed25519 receipt metadata lab). No production signer, owner key, real Ario key, real witness, service identity, privileged sink or memory engine is touched. Only three paths are added: `authority_history_readonly_lab.py`, `tests/test_authority_history_readonly_lab.py` and this document.

The experiment accepts **caller-supplied** canonical JSONL history, a purported externally pinned latest record SHA-256, an optional prior-sequence floor and its SHA-256, a requested key ID and declared policy SHA-256, and a nonce to query.

The history is ordered and hash-linked, with domain-separated per-record digest, contiguous sequence and canonical bytes. Its three **synthetic** event types are `KEY_ENROLLED`, `KEY_REVOKED` and `NONCE_SPENT`. There is no private-key operation in the module. A key that has been revoked cannot be re-enrolled, and a spent nonce cannot be repeated. The historical floor helps detect rollback or a rewritten prefix **only when its digest truly comes from an independent custodian**; here that condition is **not proven**.

### Structural tests and falsifiers

- A canonical, correctly linked synthetic history can be marked `REVIEWABLE_ONLY` but **NEVER** trusted or authorized.
- Duplicate nonce spending, invalid revocation, re-enrollment after revocation, sequence gaps, changed hash links, unexpected fields, noncanonical JSON or invalid primitive types are refused.
- A declared revoked key and a declared spent nonce are detected.
- A history shorter than a caller-provided prior floor, or a conflicting stored floor digest, is detected.
- Rewriting the ledger and **also updating both the history head and alleged external anchor** can appear internally consistent; this is a deliberate falsifier of any claim that self-hashing proves independent history.
- A malformed event kind supplied as a list or dictionary previously caused an unhandled `TypeError` in the new prototype; test-first RED and a strict string-type guard are preserved in successive Git commits.

### Non-authority contract

Every output always contains:
- `custody_independence=NOT_ESTABLISHED`
- `policy_origin_authenticated=false`
- `revocation_source_authenticated=false`
- `nonce_history_durability=NOT_ESTABLISHED`
- `authority_granted=false`
- `memory_write_allowed=false`
- `evidence_admission_allowed=false`
- `signing_allowed=false`
- `trust_activation_allowed=false`

These are **descriptive read-only flags**, not a new enforcement mechanism. No external production actor is bound to the policy ID. An apparently authentic hash chain cannot tell if a caller deleted an old revocation or invented a fresh genesis plus updated matching anchor. The code performs **no persistent append-only journal, fsync, lock, anti-fork consensus, independent OS/process custody, clock verification or crypto signature validation of history records**.

### Actual independence threshold before any use

1. **Independent source of authority:** pin the authorized public key and allowed policy version from a separately administered identity or precommitted immutable genesis path. Do not take its checksum from the same agent supplying the ledger.
2. **Durable anti-rollback state:** a separately held high-water mark and head digest from an independent observer. Need real persistence, crash/compromise-window evidence and revoked-identity recovery.
3. **Real revocation authority:** the same signer being revoked must not control the historical revocation record and the supposed external floor.
4. **Independent receipt custody:** cross-check key identity/expiry and nonce against actual receipts produced by an authorized executor; the synthetic journal proves no execution.
5. **Sink authorization:** any change to source monitoring, cognitive memory, tool execution or signer/trust requires mandatory external verification and separate governance. An internal `REVIEWABLE_ONLY` or `VERIFIED_EMPIRICAL` label is not a capability.
6. Test independently administered controls on separate principals/devices with concrete evidence before changing the NO_GO verdict. Two synthetic identities, multiple same-user signatures and a single GitHub Actions runner are **not independent witnesses**.

This version is a candidate *format/logic probe* only; it does not fix direct in-process `record_empirical_observation` self-attestation or activate `ProspectiveMemoryRegistry`. All earlier RED evidence and historical status records remain untouched.

## خلاصهٔ فارسی

ممیز می‌تواند بفهمد آیا دفتر فرضیِ ثبت کلید، ابطال و مصرف رسید از نظر ترتیب و هش خودش سازگار است یا نه. اگر یک نسخهٔ قدیمی از تاریخچه ارائه شود و مرجع قبلاً مستقل «حداقل شماره و هش» را نگه داشته باشد، می‌توان عقب‌گرد را تشخیص داد. اما **در این آزمایش خودِ درخواست‌دهنده شماره و هش مرجع را هم می‌دهد**؛ پس می‌تواند دفتر تازه‌ای بسازد که ظاهراً سالم باشد. بنابراین سازگاری دفتر به معنی اعتماد یا شاهد مستقل نیست و هیچ مجوز امنیتی صادر نمی‌شود.


## R5 independent reviews: verified distinctions and unresolved policy choices

Several independent reviews had different levels of access: one ran a local
74-case source-based suite on a different Python/cryptography version; a
separate `r5_counterexamples.py` is explicitly **only a reviewer-authored
reference model**, not a run of the repository implementation. A third review
was primarily architectural, without exact 2026 PR source. Their VERIFIED
labels are **not interchangeable**.

**Actual source-backed checks added to this PR:**
- A terminally revoked, otherwise known key now returns
  `DECLARED_KEY_REVOKED` *even if the caller's requested policy pin differs*.
  This is reporting precedence only, not a new source authentication or
  authorization decision. A previous RED test captured the wrong reason.
- `floor_sequence` and `floor_sha256` are a **pair**: the same-length
  replacement of a floor-pinned revocation with a different event produces
  `EXTERNAL_FLOOR_MISMATCH`. An independently retained floor **stale at the
  enrollment event**, however, does **not** detect revocation later omitted
  from the caller-controlled history. A floor is a prefix check, **not
  proof that the observed head is current**. No trusted freshness bound or
  independent high-water storage exists in this lab.
- `KEY_REVOKED` is terminal for the exact `key_id` in this v0.1
  research format. Re-enrolling even under another policy hash is rejected.
  Whether a future authorized reinstatement should use a new identity or
  an explicit versioned append-only reinstatement event requires a separate
  governance decision; never silently resurrect or erase a revoked record.
- **Nonce scope is GLOBAL across all key IDs in this experimental format**.
  A nonce spent under key A also rejects a receipt query under key B; a
  second spend by key B is `DUPLICATE_NONCE_SPEND`. This conservative
  existing behavior is now explicitly tested; it may prevent independent
  issuers from choosing the same nonce. Changing to per-key would require
  a versioned security contract and proof that the signed receipt binds
  the key identity. Do not silently change the existing semantics.
- JSON `nonce` is a bounded **string** under this actual schema. A
  recommendation to use `isinstance(nonce, int)` was based on a different
  model and **does not apply** to this code.
- **Concurrency and fork detection remain unsolved:** two independent
  consumers can inspect the same pre-spend snapshot and each get
  `REVIEWABLE_ONLY`. An actual compare-and-append primitive, independently
  retained high-water head and cross-view monitoring are required before
  claiming replay prevention. The laboratory performs neither.

None of the above grants memory admission, tool execution, signing or trust.
**REVIEWABLE_ONLY != AUTHORIZED; CLAIM != PROOF; MEMORY != TRUTH.**
