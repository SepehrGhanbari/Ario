# W13 — Two logical issuers: signed provenance is not independent authority

**Date:** 2026-11-17. **Scope:** isolated research; **no real Ario signer or key, no live memory, no tool dispatch, no trust/permission activation, no main merge**.  
**Status:** `SYNTHETIC_TWO_KEY_LAB_EXECUTED / 20_MATRIX_CASES / 4_UNITTEST_METHODS_PASS / 13_OF_13_SELECTED_MUTANTS_DETECTED / TWO_NEGATIVE_CUSTODY_CASES_CONFIRMED / INDEPENDENT_CUSTODY=NOT_ESTABLISHED / HOLD`.

## For the owner — خلاصهٔ قابل‌خواندن

یک نمونهٔ کوچک با **دو کلید کاملاً آزمایشی و موقت** ساختم: یکی صرفاً منشأِ ثبت اطلاعات را امضا می‌کند و یکی مجوزی با دامنهٔ دقیق را. هیچ‌کدام کلید واقعی آریو نیستند.

- حافظهٔ آلوده و امضای صادرکنندهٔ منشأ **بدون مجوز جداگانه** به اجرا نمی‌رسند.
- امضای جعل‌شده با کلید اشتباه، مخاطب یا عملیات نامربوط، محتوای تغییرکرده، مجوز باطل/منقضی و مجوزی که هنوز موعدش نرسیده رد شدند.
- ولی اگر **خود صادرکنندهٔ مجوز** در اختیار عامل مخرب قرار بگیرد، امضای صحیحِ مجوز نامشروع را نمی‌توان فقط با بررسی امضا تشخیص داد.
- اگر **دفتر ابطال** به نسخهٔ قبل برگردد، مجوزی که باطل شده بود باز هم معتبر دیده می‌شود.
- در نمونهٔ ما یک مجوز معتبر را می‌توان دوباره برای **بررسی** فرستاد؛ «دقیقاً یک‌بار اجرای واقعی» اصلاً پیاده‌سازی یا اثبات نشده.

**نتیجه:** دو کلید متفاوت در یک فرایند، استقلال واقعیِ نگهداری، تأیید دوطرفهٔ صاحب پروژه یا ضدبازگردانی نیست. این فقط یک آزمون محدود از جداسازی نقش‌هاست.

## 1. Exactly executed source and outputs

The research source was created and executed using **Python 3.13.5 + cryptography 46.0.4** in isolated ChatGPT container scratch. Ed25519 keys were newly generated inside the test process, never exported or installed on user systems.

| Public artifact | Exact Git blob SHA-1 of locally executed bytes | Reproduction |
| --- | --- | --- |
| [w13_issuer_boundary.py](w13_issuer_boundary.py) | `2f5b21fb45fc335452d8950cec15ede323fc2810` | Two role-separated synthetic Ed25519 signatures, strict source/claim/permission binding |
| [test_w13_issuer_boundary.py](test_w13_issuer_boundary.py) | `59efbd51bf8c90f79c555ddc34ed7feb4b08f46b` | 20 declared input matrix cases plus actual separate rollback/issuer-compromise/replay tests |
| [w13_record_results.py](w13_record_results.py) | `87f22d930fcdfd18af4f0807699644480aa2f74f` | Run the four unittest methods and capture case-by-case behavior |
| [W13_RESULTS_2026-11-17.json](W13_RESULTS_2026-11-17.json) | `9ad14ce711b3110f63c13edcf2e3a42347dae388` | 20 source/permit case outputs plus explicit negative custody evidence |
| [w13_mutation_audit.py](w13_mutation_audit.py) | `a1b2029f45282fbef77eab1c8f77aefe0dc4c632` | 13 disposable intentional implementation defects and 4 tests |
| [W13_MUTATION_RESULTS_2026-11-17.json](W13_MUTATION_RESULTS_2026-11-17.json) | `af019a91fa6a8cf156d43ec8094e95fa6e545361` | Each selected mutant's SHA-256 and first failing test |

**Execution evidence:** original Python unittest **4/4 method groups PASS, 20/20 matrix cases with expected local verdicts**, and **13/13 selected code mutations detected** by failing tests. Those numbers are **not independent blind cases, not a universal mutation coverage measure, not proof of threat resistance**, and not an Ario runtime integration. All file Git blob IDs above were read back after GitHub commits and compared against the locally executed bytes. No secrets, including synthetic private keys, are recorded in these files or JSON outputs.

Run in a disposable checkout from the research branch:

```bash
python -m pip install 'cryptography>=46,<47'  # if not already installed
cd research/consensus
python -B test_w13_issuer_boundary.py
python -B w13_record_results.py > /tmp/W13_recomputed.json
python -B w13_mutation_audit.py > /tmp/W13_mutants_recomputed.json
```

Expected invariant checks: source signature cannot serve as grant signature; verified grant scope binds `principal/operation/resource/destination/source_digest`, revoked grant denied by currently loaded revocation state; any positive verdict is only `ELIGIBLE_FOR_SEPARATE_GATE`, with `authority=NOT_ESTABLISHED`, `external_effects=0`, `memory_admitted=false`. The main source uses Python cryptography's Ed25519 signature API, **not** Ario's key signer or native CNG broker. Only ephemeral test keys exist.

## 2. Threat/custody matrix — which argument is actually established?

| Tested condition | Actual synthetic outcome | Interpreting the result safely |
| --- | --- | --- |
| Poisoned memory text claims USER approval; no separate grant | `DENY / NO_SEPARATE_GRANT` | Correct bounded rejection of text-only promotion |
| Same bytes, grant signed by the **source** key instead of grant key | `DENY / GRANT_INVALID_SIGNATURE_OR_PAYLOAD` | Role-specific public verification prevents simple cross-key confusion |
| Correct grant key, exact source digest, principal, operation, recipient, resource and declared time | `ELIGIBLE_FOR_SEPARATE_GATE`, never `AUTHORIZED` | A declared synthetic permission scope matched. This is NOT authenticated actual user approval |
| Malformed/impostor issuer, changed source bytes, changed recipient, expired/unborn grant | `DENY` or `UNKNOWN` | Test-case-specific checks function under key trust assumptions |
| Origin signing handle **compromised**, emits false `USER_INGRESS` label | Signature **can verify**; no grant still `DENY` | Source signature says only what the signer claimed, not who truly supplied the bytes |
| **Grant issuer signing handle compromised** | Forged malicious destination grant still `ELIGIBLE_FOR_SEPARATE_GATE` | **VERIFIED NEGATIVE:** a cryptographically correct signature cannot distinguish malicious issuer intent |
| Grant ID revoked, then verifier restarted from an older local revocation snapshot | `GRANT_REVOKED` before restoration; same old token becomes `ELIGIBLE_FOR_SEPARATE_GATE` afterward | **VERIFIED NEGATIVE:** no independently retained revocation high-water state. Distinct keys alone do not repair rollback |
| Same fully valid grant checked twice before expiry | Both checks return `ELIGIBLE_FOR_SEPARATE_GATE` | No one-use reservation or remote-effect exactly-once semantics are implemented |
| Two configured verifier roles share the same public key | Local constructor refuses `TRUST_DOMAIN_COLLISION` | Catches accidental same-key reuse, **not** same-admin simultaneous compromise of two distinct keys |

**Critical caveat:** In this lab, both signing handles and verification live **inside the same Python process**, and the test itself can access either handle to simulate a compromise. No two different operating-system identities, administrators, HSM/TPM non-exportable custody, separately controlled service or external witness has been exercised. The result **must not be described** as true independent custody or a deployed security defense.

## 3. Source-grounded architecture ideas — not drop-in Ario authority

The observed signer-ownership issue resembles, but is not solved merely by copying, practices from:

- [The Update Framework Specification (TUF)](https://theupdateframework.github.io/specification/latest/) and [TUF roles/metadata documentation](https://theupdateframework.io/docs/metadata/): role-specific signing keys, signature **thresholds** and key rotation after compromise. A repeated signature from the *same key ID* must **not** count as multiple independent threshold votes. TUF secures update metadata under its own trust assumptions; it is not an AI memory truth oracle.
- [RFC 9162, Certificate Transparency v2](https://www.rfc-editor.org/rfc/rfc9162.html): append-only log consistency commitments can expose rollback or split views when independently compared. The RFC expressly does **not** define a complete, always-available gossip mechanism. It does not prove every action was logged or every witness independent.
- [NIST SP 800-57 Part 1 Rev 5](https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final): key compromise affects the trustworthiness of claims made under that key; provenance and retention of a signature do not by themselves authenticate the human's intent once custody is compromised.

**Proposed future authorization predicate:** `bound_source_provenance AND separately_authenticated_user_grant AND current_independently_anchored_policy_epoch AND unspent_destination_operation_id AND destination_effect_authority`. Each must be established separately. A signed source, agreement of two labels, W11 `TRIGGERED`, W13 `ELIGIBLE_FOR_SEPARATE_GATE`, or a hash do **not** authorize an external effect.

**Do not claim any one of these prerequisites is built in the current Ario agent**. Current `implementation/ario_agent.py` on main is a separate allowlisted runtime, and #210/#216 remains a DRAFT/HOLD memory boundary. Real signer R62/R63 work is a **separate** restricted laboratory and out of scope.

## 4. Exact reviewer challenge (please request independent source+test evidence)

1. **Repeat byte-pinned source test** and 13 mutants on a different machine or runner; return Python version, cryptography version, exact Git SHA, stderr and SHA of recomputed result. Green GitHub CI alone is insufficient.
2. **Attack the assumptions**: forged user classification by a compromised origin signer, forged grant from actually compromised grant issuer, shared process/admin/key store, revocation-state rollback, signature trust-store substitution, replayed grant and post-verification key revocation.
3. **Independent trust root:** who binds the public keys to distinct custodians, who can rotate/revoke them, and how does the verifier learn a newer epoch if the attacker restores its whole disk? If no external independently reachable anchor exists, report `NOT_ESTABLISHED`.
4. **Non-vacuous positives:** a legitimate user-granted action must remain *eligible for later review* while unauthorized memory-derived recipient and scope remain rejected. Report false acceptance and false rejection separately.
5. **Real-world provenance:** demonstrate input-origin attestations are generated at the actual source boundary, **not** by an LLM, retrieved text, source metadata provided by an attacker or a mutable memory store.
6. **Actions:** a signed intent is not a destination effect, and multiple independent simulated signers are not consensus. Prove actual out-of-band scope approval and destination-side conditional/idempotent effect before using any stronger name than `ELIGIBLE_FOR_SEPARATE_GATE`.
7. **Crypto and resource limits:** this toy creates signatures with short JSON claims; public-key registry durability, canonical encodings across languages, path/recipient alias policy, strict source size bound *before allocation*, replay counters and real timestamps remain UNTESTED.

**Acceptance bar:** post a review with a new independent attack/benign pair and source lines; report `CONFIRMED/REFUTED/UNKNOWN`. Until then **external independent assessment = 0**. Preserve the result as a **research prerequisite, not an implementation directive or security approval**.

## 5. Decision

`ADOPT FOR RESEARCH`: two differently keyed logical roles, explicit origin/permission/output binding, negative compromise and rollback cases, no-history-promotion.  
`TEST NEXT`: genuinely separated source envelope producer + grant signer + rollback-resistant independent reference under disposable credentials, with two operators and independent adjudicator.  
`HOLD`: memory V2 rollout, source legitimacy, root/trust activation, signer keys, ruleset changes, external effects, claim-to-truth automatic elevation, PR merge and production.

**Do not erase negative findings.** Key principles: `MEMORY!=TRUTH; CLAIM!=PROOF; SIGNATURE!=HUMAN_CONSENT; TWO_LOGICAL_KEYS!=INDEPENDENT_CUSTODY; UNKNOWN_VALID`.
