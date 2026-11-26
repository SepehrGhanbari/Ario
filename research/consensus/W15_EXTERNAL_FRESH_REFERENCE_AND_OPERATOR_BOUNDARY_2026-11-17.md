# W15 — Real GitHub-hosted fresh-reference lookup versus a locally restored revocation view

**Date:** 2026-11-17  
**Disposition:** `REMOTE_PROVIDER_READ_CONFIRMED / FIXTURE_BLOBS_PINNED / 4_UNITTEST_METHODS_PASS / OLD_PLUS_E1_DENIED / OLD_PLUS_OLD_STILL_LOOKS_ELIGIBLE / ACTUAL_SEPARATE_ADMINISTRATOR=NOT_ESTABLISHED / RESEARCH_ONLY / DRAFT_HOLD`.

## برای بنیان‌گذار — خلاصهٔ کوتاه فارسی

از W14 یک قدم واقعی جلو رفتیم: یک شاهدِ نسخه‌دار را **بیرون از کانتینر آزمایش در سرویس GitHub** گذاشتیم و با ابزار متصل به GitHub دوباره خواندیم. شناسهٔ Git Blob از GitHub با دادهٔ محلی بایت‌به‌بایت تطبیق داشت. در آزمایش با کلیدهای کاملاً ساختگی، ارائهٔ دفتر قدیمی E0 در مقابل شاهد جدید E1 باعث `DENY` شد. نسخهٔ جدید E1 هم نشان داد مجوز G1 قبلاً باطل شده است.

ولی اگر فقط **دفتر قدیمی E0 همراه شاهد قدیمی امضاشدهٔ E0** قابل‌دسترسی باشد، بررسی‌کننده به‌درستی نمی‌تواند بفهمد که نسخهٔ E1 وجود دارد؛ بنابراین تطبیق ساختاریِ نسخهٔ قدیمی را فقط `DECLARED_ELIGIBLE_FOR_SEPARATE_GATE` می‌نامد — **نه اجازهٔ واقعی**. بدون استعلام شاهد، `HOLD_UNCERTAIN` می‌دهد.

**تفاوت حیاتی:** GitHub از کانتینر ما جداست، ولی فایل‌های GitHub هنوز تحت اختیار **همان مالک مخزن** هستند؛ این آزمایش **دو مدیر مستقل، نگهداری غیرقابل‌پاک‌کردن، استقلال شاهد یا اصل رضایت سپهر و آریو** را ثابت نکرد.

## 1. Actual executed and independently read-back evidence

Source and unit test actually executed with **CPython 3.13.5, cryptography 46.0.4**, in an isolated research container:

| Artifact | Git Blob SHA-1, independently verified by GitHub readback | Role |
| --- | --- | --- |
| [w15_fresh_highwater_probe.py](w15_fresh_highwater_probe.py) | `9acc21953308a595a502801b6be1f703682722ae` | Versioned synthetic Ed25519 issuer, strict signed checkpoint comparison, missing reference → HOLD |
| [test_w15_fresh_highwater.py](test_w15_fresh_highwater.py) | `021862adec1395fa1dde2c2d150bf0668db2b429` | 4 unittest method groups; 10 labeled comparison cases plus signature/tamper/schema/JSON negative controls |
| [W15_SYNTHETIC_FIXTURE_2026-11-17.json](W15_SYNTHETIC_FIXTURE_2026-11-17.json) | `22f141ae808573c1a84d321b10eeaf10ceaa0937` | Public test keys, signed mock grant G1/G2, signed revocation heads E0/E1 and their anchors. **NO PRIVATE KEYS** |
| [W15_REMOTE_ANCHOR_E0_2026-11-17.json](W15_REMOTE_ANCHOR_E0_2026-11-17.json) | `38759bf53e40940141c673717545836a4c69b7b0` | Historical old signed witness checkpoint |
| [W15_REMOTE_ANCHOR_E1_2026-11-17.json](W15_REMOTE_ANCHOR_E1_2026-11-17.json) | `ae5dbc69867d8ad355002cb5c8bbf2badf17d9e2` | Later signed witness checkpoint, **actually re-fetched through the connected GitHub API** |
| [W15_REMOTE_REFERENCE_OBSERVATIONS_2026-11-17.json](W15_REMOTE_REFERENCE_OBSERVATIONS_2026-11-17.json) | `81dacceca88763305ad6b907c0440a730352c0e8` | Seven named before/after/failure scenarios actually evaluated, every output `operational_authority=NONE` |

**GitHub commits actually created:** public fixture `6176045f`, old remote checkpoint `2875ec70`, new remote checkpoint `d7f20a6e`. All three documents are appended in the **existing research branch**. No production trust root or signer is involved. Exact file SHA-256 for the new GitHub E1 witness: `011ff81c9bd0317c02292c3f7fbeb69435955698fc83567eedb7c3b87a828ae0`, matched local bytes. **This remote read establishes GitHub was serving those bytes when asked, NOT an unforgeable statement that E1 is currently the final epoch.** There could already be an E2 held elsewhere or a branch owner could publish E0 again.

**Reproduction scope:** 4 unittest method groups **PASS** under CPython 3.13.5. Separate main script CLI was run against local copies with `--local E0 --remote E1` → `DENY/PRESENTED_STATE_BELOW_REMOTE_REFERENCE`; `--local E0 --remote E0` → `DECLARED_ELIGIBLE_FOR_SEPARATE_GATE`; `--local E1 --remote E1` → `DENY/REVOKED_BY_PRESENTED_HEAD`. The Python script intentionally has **no network access**; a caller must obtain and hash-verify the actual GitHub remote file out of band. It is a bounded signed-data comparator, not a deployed GitHub client with authenticated freshness policy.

## 2. Seven executed scenario outcomes and false-acceptance counterexample

| Scenario | Actually observed verdict | What that establishes |
| --- | --- | --- |
| Local E0, remotely fetched/pinned E1, G1 | `DENY / PRESENTED_STATE_BELOW_REMOTE_REFERENCE` | *Given the current E1 packet*, the old local state is stale |
| Local E0, old **signed** E0 reference, G1 | `DECLARED_ELIGIBLE_FOR_SEPARATE_GATE` | **Negative result:** mutually old but individually authentic versions conceal later revocation |
| Local E1, current E1 reference, revoked G1 | `DENY / REVOKED_BY_PRESENTED_HEAD` | A correctly presented newer head denies revoked grant |
| Local E1, E1 reference, non-revoked G2 | `DECLARED_ELIGIBLE_FOR_SEPARATE_GATE` | Bounded positive control; **not authorization or actual user consent** |
| Local E0, reference unavailable | `HOLD_UNCERTAIN / REMOTE_REFERENCE_UNAVAILABLE` | Offline/no lookup must not silently declare secure |
| Local E1, reference reports only E0 | `HOLD_UNCERTAIN / REMOTE_REFERENCE_BEHIND_PRESENTED_STATE` | No unsupported assertion of latest from a lagging remote |
| Local E0, remote E0, but retained trusted local high-water `epoch>=1` | `DENY / REMOTE_BELOW_PREVIOUSLY_SEEN_EPOCH` | Anti-rollback works if prior high-water memory survives and cannot be forged/reverted |

Every row also returns `operational_authority=NONE`, `real_user_approval=NOT_ESTABLISHED`, `external_actions=0`, `remote_reference_independent_custody=NOT_ESTABLISHED` and `remote_currentness_guaranteed=false`.

**A signature identifies a signer's public key, not that the associated metadata is the newest in the world.** Historical E0 remains a cryptographically valid old snapshot. TUF clients maintain trusted version/freshness checks and reject rollback/freeze under defined assumptions; a GitHub blob hash does **not** add a trusted currentness guarantee. The W15 comparison deliberately preserves the failure and does not call the E0 result `SUPPORTED` or `AUTHORIZED`.

## 3. Scientific and standards grounding (exact original URLs)

- [The Update Framework specification](https://theupdateframework.github.io/specification/latest/): versioned signed metadata, trusted key mapping, rollback/freeze protection **with retained trusted client state and freshness checks**. It does not guarantee operator independence for Ario.
- [RFC 9162 Certificate Transparency v2](https://www.rfc-editor.org/rfc/rfc9162.html): signed tree heads and consistency proofs within a real Merkle-log protocol. W15 merely uses a **linear sequence of signed toy anchor records**; it is not a Merkle CT implementation and does not demonstrate a gossip network or independent monitors.

Both original sources were re-checked on 17 Nov. Neither standard establishes that the repo owner cannot rewrite W15, that private key identities are independently operated, or that a user actually agreed to any task.

## 4. Explicit truth table of operational independence

| Claim | W14 | W15 | Status |
| --- | --- | --- | --- |
| Different unprivileged Linux UIDs cannot trivially read each other's test key file | Reproduced in disposable container | Not retested | `DAC_ONLY` |
| A **separate network/provider** can serve a public signed witness outside local root process | Not tested | **Actual GitHub connector fetch and blob verification** | `REMOTE_HOST_SEPARATION_ONLY` |
| Source local root cannot edit or delete the external reference | Not established | **No — same repo owner controls GitHub path; locally independent admin not attested** | `NOT_ESTABLISHED` |
| A remote E1 contradicts a locally rolled-back E0 | Bounded local two-UID witness control | Reproduced with fetched GitHub packet | `SYNTHETIC_REPRODUCED` |
| Currentness of the **latest** E2+ is independently guaranteed | Not established | Not established | `UNKNOWN` |
| Shared owner cannot restore both accessible reference and local state | W14 counterexample | W15 E0/E0 negative | `UNPROVEN_AND_NEGATIVE_TEST` |
| Independent actual human approval and recipient authorization | Not established | Not established | `NO_GO` |
| Global exactly-once external effect | Not established | No effect is invoked | `NO_GO` |

The test creator generated all three ephemeral signers in a **single process** and chose E0/E1 fixture timelines. GitHub hosts the published *public blobs*, but **no actual second independent writer or trusted timestamp service was enrolled**. We do not claim to have completed the "two independently administered environments" requirement.

## 5. Independent reviewer checklist, already tracked in #259

- [ ] **Repeat on a separate checkout**: fetch both named anchors from GitHub via the authenticated API, record exact blob SHA, execute `python -B test_w15_fresh_highwater.py` and compare all seven scenario verdicts.
- [ ] **Real separate operator**: enroll an independently controlled witness/custodian who **cannot be administered, deleted or overwritten by the research-repo owner**, and has a separately authenticated public-key pin. The existing GitHub file **does not count**.
- [ ] **Freshness and freeze**: define the exact lookup authority, maximum permitted staleness, clock source, retained high-water monotonic counter, and behavior when the latest reference cannot be authenticated. Test E2 that GitHub does not display, malicious E0 republish, partial propagation and split view.
- [ ] **Negative under common root/owner**: let the same admin rewind local state and replace both Github visible paths; show that old signatures remain valid and the verifier without a surviving reference **cannot know**. Preserve failure as data; do not erase it or upgrade trust labels.
- [ ] **Positive compatibility**: non-revoked G2 with genuinely current authorized scope should remain eligible only for a **different action authority gate**, while G1 correctly remains denied.
- [ ] **Human/source authority**: explain why the signer keys and public-key registry are mapped to trusted principals; a real source of independently approved user intent must not be inferred from mere tokens or GitHub workflow success.
- [ ] **Integration gate**: map the current main runtime and draft #210/#216 contracts; if W15 is not called by the actual system, report `NOT_IMPLEMENTED`. No live signer or memory tests permitted under this PR.

**Reproduce using the exact published files (requires Python3 + `cryptography`):**

```bash
cd research/consensus
python -B test_w15_fresh_highwater.py
python w15_fresh_highwater_probe.py --fixture W15_SYNTHETIC_FIXTURE_2026-11-17.json --local E0 --remote W15_REMOTE_ANCHOR_E1_2026-11-17.json
python w15_fresh_highwater_probe.py --fixture W15_SYNTHETIC_FIXTURE_2026-11-17.json --local E0 --remote W15_REMOTE_ANCHOR_E0_2026-11-17.json
python w15_fresh_highwater_probe.py --fixture W15_SYNTHETIC_FIXTURE_2026-11-17.json --local E0
```

A real reviewer should fetch the remote file anew instead of merely trusting a checked-out copy. This repository does **not** contain a live credentialed GitHub fetcher by design. A green CI run does not prove the research program is integrated or independently audited.

**Research decisions:** `ADOPT_AS_SOURCE_BOUNDED_NEGATIVE_EVIDENCE` old+old and missing remote; `TEST_NEXT` independently administered witness and out-of-band key trust; `HOLD` real anti-rollback security claim, production, trusted owner signer, permission/consent, #216 migration and any main merge.

`MEMORY!=TRUTH; SIGNED!=CURRENT; TWO_REMOTE_COPIES!=INDEPENDENT_CUSTODY; UNKNOWN_VALID; NO_AUTO_MEMORY / NO_SIGNER / TRUST_ACTIVATION=NO_GO`.
