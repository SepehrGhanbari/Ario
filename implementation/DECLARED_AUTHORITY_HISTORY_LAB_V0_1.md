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
