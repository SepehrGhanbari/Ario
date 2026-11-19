# W27 — Independent Witness Network readiness (UNSENT / NO CONTACT)

**Ario research date: 2026-11-18**  
**Status: RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NO_ENROLLMENT / NO_PUBLIC_SUBMISSION / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO**

## خلاصهٔ فارسی

این فایل بستهٔ آماده‌سازی ورود احتمالی یک *لاگ کاملاً مصنوعی و مجزا از آریو اصلی* به Witness Network است؛ **درخواست ارسال نشده** و هیچ اپراتور/شاهد خارجی به آریو متصل نشده است. اصل مسئلهٔ W24 تا W26 روشن شد: چند فایل، چند فرایند، چند حساب، یا چند ماشین زیر یک مدیر، «نگهدارندهٔ مستقل» نمی‌سازند.

در W27 یک تأییدکنندهٔ آفلاین برای امضای Ed25519 شاهد در فرمت C2SP ساخته شد؛ در عین حال هر نتیجهٔ موفق رمزنگاری هم به HOLD ختم می‌شود، چون ادعاهای منبع کلید، مدیریت مستقل و تازه‌بودن وضعیت جهان هنوز اثبات نشده‌اند.

## Official sources checked

- C2SP witness protocol v1.1.0: https://c2sp.org/tlog-witness@v1.1.0 ; POST add-checkpoint, independent log verification, atomic persisted state before response; optional GET monitoring-prefix/<origin SHA256 hex>/checkpoint. Monitoring may lag for up to one hour by design. There is **no requirement of client authentication** beyond the signed checkpoint.
- C2SP cosignature v1.1.0: https://c2sp.org/tlog-cosignature@v1.1.0 ; signed checkpoint content and timestamp. Ed25519 cosignatures use cosignature/v1 message domain, timestamp and root. Distinct witness key is not a proof of distinct administrator.
- C2SP checkpoint v1.1.0: https://c2sp.org/tlog-checkpoint@v1.1.0 ; key type 0x01 for Ed25519 log, 0x04 for Ed25519 cosigner. New deployments SHOULD consider ML-DSA-44; this W27 audit handles **only the Ed25519 W22 subset**, not ML-DSA-44 or arbitrary note extensions.
- Witness Network: https://witness-network.org/ ; **experimental / work in progress**.
- Participation instructions: https://witness-network.org/participate/ ; ask maintainers via participate (at) lists.witness-network.org. Maintainers recommend human-to-human communication and may ignore requests from AI agents. **This document is a draft, not a sent message or enrollment.**
- Log list syntax: https://github.com/transparency-dev/witness-network/blob/main/log-list-format.md . Required line fields include logs/v0, vkey, qpd and contact; optional origin.

## Gate register — evidence needed before ANY external contact or enrollment

| Gate | Required evidence | Current state |
| --- | --- | --- |
| E0 | Only synthetic, nonpersonal and non-Ario-key log payloads | PLANNED, not deployed |
| E1 | Stable, globally unique synthetic log origin (NOT the .invalid W22 fixture as if public) | MISSING |
| E2 | Separate public vkey of a **real synthetic log for this experiment** (private key managed solely for that disposable log) | MISSING |
| E3 | Actual append-only log service and RFC6962 consistency support externally testable | NOT_ESTABLISHED |
| E4 | Expected add-checkpoint requests per day, bounded load | UNDECIDED |
| E5 | Public contact details the founder consents to disclose | UNDECIDED |
| E6 | Selection of testing/staging list: testing preferred for short-lived dev experiments | DECISION_NOT_SUBMITTED |
| E7 | Candidate witness about page with vkey (0x04 or supported newer algorithm), monitored contact and endpoints | NOT_SELECTED |
| E8 | Out-of-band witness key retrieval from a source independently authenticated by the verifier | NOT_ESTABLISHED |
| E9 | Independent administrative control of historical state from claimant, including rollback/revocation handling | NOT_ESTABLISHED |
| E10 | Signed cosignature and monitor retrieval independently compared against retained head | NOT_RUN |
| E11 | Explicit founder approval of irreversible external data submission and privacy scope | NOT_GRANTED |
| E12 | Witness Network maintainer review / enrollment / log-list acceptance | NOT_REQUESTED |
| E13 | Governance authority/Genesis/Ario veto changes | FORBIDDEN IN THIS EXPERIMENT |

**Composite readiness verdict: NOT_READY_TO_CONTACT / HOLD.** An email draft is not approval to send it.

## Private-by-default candidate selection rubric

1. Operator **identity**: distinguish legal/administrative operator from website, cloud account, owner email, machine, proxy or witness public key.
2. Key provenance: independently retrieve a public-key fingerprint via a pre-trusted channel, record exact origin, timestamp, operator and the path used; never blindly accept the key supplied with the response being verified.
3. Retention: demand operator-maintained high-water and policy for crash, restore, revocation/rotation, stale checkpoints, lost responses, recovery, unavailability and monitoring readbacks.
4. Counterexamples: two different URL domains can still share one admin; two witnesses with distinct keys can be held by one admin; a good signature from a same-admin key does **not** pass separation; matching checkpoint roots do not prove global freshness; missing logs remain unknowable.
5. Monitoring endpoint: compare signed/cosigned checkpoint from a genuine watcher with an independently retained earlier checkpoint; prove consistency where claimed, never infer completeness or absence of hidden forks.
6. Enrollment and privacy: only a dedicated disposable public synthetic log; no original Ario keys, production memory, private research notes, personal archives or identifying account records.
7. Independence label remains NOT_ESTABLISHED until independent authority, independent key custody and independently retained/available high-water are observed; do not self-approve via a Boolean in JSON.
8. Separate human communication if chosen: official Witness Network says maintainers may ignore AI-origin requests; don't automate unsolicited contact.

## Future log-list entry template (DO NOT PUBLISH)

    logs/v0
    vkey <NEW_PUBLIC_SYNTHETIC_LOG_VKEY_NOT_YET_CREATED>
    origin <NEW_PUBLIC_SYNTHETIC_LOG_ORIGIN_UNDECIDED>
    qpd <INTEGER_TO_BE_MEASURED_AND_APPROVED>
    contact <PUBLIC_CONTACT_FOUNDERS_CHOICE>

This is a **non-valid placeholder template**, not a real list entry. Use no live/public production identifier.

## Unsent draft, for future review only

Subject: Request to discuss a synthetic testing-list transparency log (Ario research; NOT SENT)

Hello Witness Network maintainers,

We are studying C2SP checkpoint consistency and independent witness custody. We are considering a separate, strictly synthetic and public test transparency log for the testing list; no personal records, production Ario memory, governance keys, or real authority would be involved.

Origin: <NOT_DECIDED>
Public log vkey: <NOT_GENERATED>
Rate (add-checkpoint requests/day): <NOT_MEASURED>
Public contact: <NOT_APPROVED>
Expected lifetime and purpose: short-lived, reproducible consistency and monitoring research (subject to confirmation).
Requested list: testing, subject to your review.

We would like to understand the operator-independence, retained-checkpoint and out-of-band witness-key practices before deciding whether to request enrollment. Please treat this as a future draft only.

Regards,
<CONTACT_NOT_APPROVED>

**Do not send. Do not treat preparatory prose as third-party acceptance or custody evidence.**

## Audit code constraints

The separately committed W27 audit accepts a caller-supplied note and purported pinned witness key, verifies C2SP Ed25519 note cosignature in W22's strict no-extension subset, checks signature timestamp against an explicit evaluation clock, and always reports HOLD and INDEPENDENT_OPERATOR_CUSTODY=NOT_ESTABLISHED. It performs **no network access, filesystem I/O, public key discovery, signing, C2SP POST, external enrollment, governance authorization or memory admission**. Cryptographic correctness alone is insufficient for W27's broader objective.

**Do not merge as a security feature. RESEARCH_ONLY / NO_EXTERNAL_CONTACT / HOLD / PRODUCTION=NO_GO.**
