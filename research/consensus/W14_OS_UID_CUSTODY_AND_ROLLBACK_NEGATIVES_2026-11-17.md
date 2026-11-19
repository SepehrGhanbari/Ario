# W14 — Four real Linux UIDs for synthetic grant, revocation, anchor and read-only verification

**Date:** 2026-11-17  
**Verdict:** `LINUX_DAC_SEPARATION_REPRODUCED / 31_SELECTED_CHECKS_MATCHED / 9_SELECTED_PURE_VERIFIER_MUTANTS_KILLED / COMMON_ROOT_CAN_READ_ALL_KEYS / OFFLINE_BOTH_STALE=FALSE_ACCEPTANCE / INDEPENDENT_CUSTODY_NOT_ESTABLISHED / RESEARCH_ONLY / HOLD`.

## خلاصهٔ فارسی برای بنیان‌گذار

این بار چهار نقش با **چهار شناسهٔ کاربری متفاوت سیستم‌عامل** در یک کانتینر لینوکسی دورریختنی اجرا شدند؛ کلیدها کاملاً آزمایشی‌اند. صاحب یک نقش نتوانست کلید خصوصی نقش دیگر را بخواند یا فایل عمومی نقش دیگر را بازنویسی کند. نگهدارندهٔ ابطال و نگهدارندهٔ شاهدِ زمان/نسخه دو نقش جدا بودند. با حفظ نسخهٔ جدید شاهد، عقب‌بردن دفتر ابطال تشخیص داده شد.

اما **سه محدودیت حیاتی واقعاً بازتولید شدند**: (۱) مدیر `root` مشترک می‌تواند هر سه کلید خصوصی را بخواند؛ (۲) اگر شاهد و دفتر ابطالِ در دسترس هر دو قدیمی باشند، بررسی‌کنندهٔ آفلاین ممکن است مجوز باطل‌شده را دوباره قابل‌بررسی ببیند؛ (۳) اگر *صادرکنندهٔ واقعی مجوز* از کنترل خارج شود، مجوزِ جعلی که با کلید خودش امضا شده، حتی با شاهد تازه هم از لحاظ امضا معتبر است. این نتیجه **امنیت تولیدی، مالکیت مستقل آریو، رضایت سپهر یا آریو، و «اجرای دقیقاً یک بار» را ثابت نمی‌کند**.

### A. Executed artifacts and source identity

| Artifact | Exact Git blob of tested local bytes | What it contains |
| --- | --- | --- |
| [w14_uid_custody_lab.py](w14_uid_custody_lab.py) | `9665854a2a8133cec73049d8d219800295a860f3` | Native Linux `setpriv` launch to **four distinct OS UIDs**, 3 synthetic Ed25519 signers, read-only verifier, revocation/anchor states, DAC probes, rollback and compromise negatives |
| [W14_NATIVE_RESULTS_2026-11-17.json](W14_NATIVE_RESULTS_2026-11-17.json) | `8a1bd6adf7548c2616384ba6eda07f602c32ff7c` | **31** executed case IDs + exact bounded outcomes. One-line JSON; no private keys or signatures |
| [w14_verifier_mutation_audit.py](w14_verifier_mutation_audit.py) | `bfe218fa0e164db50c9bb49d5a18b5328bbdbc2d` | Additional **in-memory-only** verifier mutation exercise: 11 local controls, 9 selected mutants |
| [W14_MUTATION_RESULTS_2026-11-17.json](W14_MUTATION_RESULTS_2026-11-17.json) | `ab38d38038b8711c561956e41a19e8b232f73b0f` | **9/9** selected verifier mutants detected, each mutation SHA256/first failing case |

**Execution environment actually used:** isolated ChatGPT Linux container (root inside **this disposable container only**), CPython `3.13.5`, `cryptography 46.0.4`, installed `setpriv` (util-linux). Numeric test identities `31801` (grant), `31802` (revoker), `31803` (anchor), `31804` (verifier). No system users were added, and no real Ario host/Windows Sandbox, signer key, GitHub permission, memory ledger or network effect was modified. Key generation occurred **after each subprocess dropped to its own nonroot UID**; private key files were owned by that UID in mode `0600`, private directories mode `0700`, signed publication files mode `0644`. A root-owned `0444` trust store maps the three temporary public keys to roles; it **does not resist a hostile common root**.

**Every file above was read back from GitHub and its returned blob SHA compared with the exact local executed file.** Reported case verdicts are internally designed expectations (not an external, blinded gold oracle).

### B. What each test actually proved (within this disposable box)

| Source-scoped question | Observed result | Evidence boundary |
| --- | --- | --- |
| Can grant, revocation, anchor, verifier read other roles' private keys? | **6/6 actual cross-UID read attempts denied** | Linux discretionary access control (DAC) works against these distinct **unprivileged** UIDs |
| Can one unprivileged role overwrite another's signed publication? | **3/3 cross-UID write-access probes denied** | DAC only; common root not constrained |
| Can unprivileged grant or verifier edit root-owned trust key map? | **2/2 refused** | Protects from those UIDs; root can change it |
| Is verifier actually a separate UID? | **Yes, UID 31804 returned by verifier subprocess** | Kernel identity, not independent operator or physical device |
| Is a correct synthetic grant + current signed head + current signed anchor usable? | `ELIGIBLE_FOR_SEPARATE_GATE` (never `AUTHORIZED`) | Positive availability control; zero real effects |
| Does a revoked grant fail after latest head anchored? | `DENY / GRANT_REVOKED` | Bounded to latest head reaching verifier |
| Does an old head conflict with a retained current anchor? | `DENY / STALE_OR_UNANCHORED_HEAD` | Need an **untampered, reachable recent anchor** |
| Does a current anchor holder reject an old head upon attempted rewind? | `STALE_OR_FORKED_REVOCATION_HEAD` | Only if its private high-water state survives |
| Do both old, individually valid signed public snapshots still pass stale-only verification? | **`ELIGIBLE_FOR_SEPARATE_GATE`** | **Verified negative:** both-old rollback not detectable to a stale-only verifier |
| Can a common `root` read each test role's private key? | **Yes, three private key files accessible to root** | **Verified negative:** not independent administrative custody |
| Does root restoration of *both public signed views* defeat stale-only verification? | **Yes, returns `ELIGIBLE_FOR_SEPARATE_GATE`** | **Verified negative** in this one machine; retained new anchor detects |
| If actual grant issuer signs an unauthorized destination, does a *fresh* anchor fix it? | **No; structurally eligible** | **Verified negative:** signature authenticates signer key, **not** real user intent |
| Is recipient substitution, wrong time, wrong signer or edited packet blocked? | Rejected in the selected positive/negative cases | Does not prove generic string normalization or model safety |

**IMPORTANT:** the original W14 private witness-state files are **not physically outside root control**. Root can restore them too; this lab explicitly demonstrates local root access rather than claiming hardware-grade non-extractability or multi-host consensus. The term *anchor* here means a signed local second-role checkpoint; **not** a Certificate Transparency implementation or a real remote witness.

### C. Test sensitivity vs underlying security

The original **31/31** Linux checks passed as written. A **separate** pure-verifier suite then exercised **11 additional in-memory cryptographic controls** and **9 deliberately defective selected code variants**. All nine selected mutants were rejected by at least one targeted control: ignored grant scope, ignored revocation, ignored anchor digest, ignored validity window, fake final permission, accepting bad signatures, wrong signer key, role-domain confusion, wrong anchor public key.

**Do not claim that 9/9 mutant detection ran the full 31-case multi-UID subprocess suite nine times. It did not.** Mutations used temporary Python module text in memory and the pure function `check_packets`; no OS UID manipulation in the mutation loop. Mutants and expectations were authored by the same evaluator; this is test sensitivity for **nine selected faults**, not a percentage of actual threats blocked.

### D. Reproduction commands (no dependency on the founder's Windows machine)

**Precondition: a NEW/throwaway Linux container** where root is allowed, `setpriv` exists and `cryptography==46.0.4` is installed. Do **NOT** run as root on a regular personal host or any actual Ario key holder. The parent only creates a temporary folder under `/tmp`; it doesn't create system accounts. Child roles drop to fixed numeric UIDs `31801..31804`; ensure these IDs are not already used **inside the throwaway container**. Lab source refuses non-Linux or nonroot execution (no synthetic substitute passing as native UID evidence).

```bash
python3 research/consensus/w14_uid_custody_lab.py > W14_recomputed.json
python3 research/consensus/w14_verifier_mutation_audit.py > W14_mutants_recomputed.json
python3 - <<'PY'
import json
a=json.load(open('W14_recomputed.json'))
b=json.load(open('W14_mutants_recomputed.json'))
assert a['cases']==31 and a['effects']==0 and not a['independent_admin_domains']
assert b['pure_controls']==11 and b['selected_mutants']==9 and b['killed']==9 and b['survived']==0
print('W14 SOURCE-BACKED SYNTHETIC REPLAY PASS — NOT PRODUCTION SECURITY')
PY
```

No secret keys are published. Runs produce new random ephemeral Ed25519 keys, so **do not** expect cryptographic packet byte identities across fresh executions; the *case semantics* and envelope fields are deterministic. The published W14 JSON records the specific observed local run, not a claim of repeated external replays.

**Explicit resource/power-failure caveat:** the toy uses `os.replace` and `fsync` on written file content but does **not** fsync the containing directory; process crash windows, actual power loss, concurrent signing and rollback of an entire root filesystem are **not** proven durable by W14. It is not a hardened key service.

### E. Original external standards used correctly

- [The Update Framework (TUF) specification](https://theupdateframework.github.io/specification/latest/) defines role separation, authorized key thresholds, version comparison and client anti-rollback behavior. This **does not** prove two different public keys have different real custodians; TUF's update trust model is not a drop-in consent system for Ario.
- [Certificate Transparency v2, RFC 9162](https://www.rfc-editor.org/rfc/rfc9162.html) defines signed-tree heads and consistency proofs for a defined append-only log. It explicitly does not supply a universal complete gossip network or prove that every external event was recorded. W14's linear hash-linked head is **not** a CT Merkle log, inclusion proof, completeness oracle or production transparency service.
- [W13 two logical issuers analysis](W13_TWO_ISSUERS_AND_REVOCATION_ROLLBACK_AUDIT_2026-11-17.md) reproduced the earlier same-process synthetic shared-admin rollback and issuer-compromise limits; W14 **improves one limited dimension only**: unprivileged OS UID file isolation, plus a surviving local high-water state under a different UID. It does not resolve W13's ultimate custody/consent requirement.

### F. Exact independent review request — existing GitHub issue, not a new implementation PR

Post to [review request #259](https://github.com/SepehrGhanbari/Ario/issues/259) and [research Draft PR #242](https://github.com/SepehrGhanbari/Ario/pull/242) using:

`Finding ID | CONFIRMED/REFUTED/UNKNOWN | exact W14 file+line/blob | independent disposable container UID outcome | wrong-origin/rollback/grant test | own new positive+negative pair | proposed bounded fix | independence/custody assumption`.

**Required additional independent falsifiers:**
1. Hold revoker and anchor under **different administrators/hosts**, not only numeric UIDs on one root, with a *separately authenticated* public-key registry and an authentic external high-water anchor.
2. Refuse an old but validly signed state on a verifier disconnected from the latest anchor; either show the protocol's required freshness bound or return `HOLD_UNCERTAIN`, never assert universal freshness.
3. Attest a **human/user approval** separately from a grant issuer's private key, against malicious correctly signed grants. Establish veto and signer policy independently, not from content or fabricated memories.
4. Inject crash between revoker head publication and anchor acceptance; check sequencing, fsync/directory durability, network partition and possible forged fork signatures.
5. Check positive availability of an authorized benign operation without giving permission to a malicious memory-sourced destination; report false refusal as well as false acceptance.
6. Inspect the real Ario bounded agent and the unmerged #210 source-monitoring contract. If they do not call any W14 gate, state **NOT_IMPLEMENTED** rather than claim Ario runtime is protected.

**Protected dispositions:** `RESEARCH_ONLY / MAIN_UNCHANGED / #216_HOLD / #259_REVIEW_OPEN / #242_DRAFT_HOLD / OWNER_SIGNER=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO / NO_AUTOMATIONS`.

**No historical file rewrites, grants in the real user environment, live model memory admissions or actual system approvals.**
