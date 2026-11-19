# R6 — Strengthened Limitations, Physical Protocol Draft & Evidence Consistency Notes

**RESEARCH_ONLY / DRAFT / HOLD / NOT_ADOPTED / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO**

This note consolidates four documentation improvements requested for PR #273:

1. Stronger, more formal statement of what a successful Sigsum proof does and does **not** establish.
2. A concrete, executable draft of the next physical two-host experiment (R6-B).
3. Consistency check between current evidence records and claims in the PR body / workflows.
4. Clearer bilingual limitation language.

Nothing in this file changes any code, workflow, key, or production path. It is pure research documentation.

---

## 1. What a successful R6-C Sigsum proof actually establishes vs. what it does not

### Established (under the pinned `sigsum-test1-2025` policy)

- The exact bytes of a **caller-supplied synthetic checkpoint** were hashed and submitted to the external Sigsum TEST log.
- An inclusion proof was obtained that satisfies the policy’s declared 2-of-3 external witness quorum.
- Offline `sigsum-verify` succeeded on the original bytes and failed after a one-byte tamper.
- The public test key, policy text, proof, and checkpoint hashes are recorded and independently checkable for the lifetime of the artifact.

### Explicitly NOT established (and must never be claimed)

| Claim | Status | Reason |
|---|---|---|
| The digest corresponds to a real C journal that was independently controlled | **NOT_ESTABLISHED** | The checkpoint only *quotes* a previously reported hash; the journal bytes themselves were never the signed input. |
| The submitter key is independent of the operator who controls C | **NOT_ESTABLISHED** | The ephemeral key was generated inside the same workflow that produced the synthetic claim. |
| Any real tool execution, receipt admission, or memory write occurred | **NOT_ESTABLISHED** | All authority flags remain false; the input is synthetic by design. |
| Administrative independence of E and C | **NOT_ESTABLISHED** | Same operator / same administrative domain (GitHub runner or future single-user hosts). |
| Freshness / non-equivocation of the high-water mark over time | **NOT_ESTABLISHED** | A single inclusion proof does not monitor subsequent heads; continuous monitoring + multiple observations are required. |
| Resistance to rollback or fork by the local custodian | **NOT_ESTABLISHED** | Local journal remains under C’s control; Sigsum only anchors a public statement about a digest. |
| Any production trust, signer, Ruleset, or memory activation | **NO_GO** | Explicitly forbidden by design and by all authority flags. |

**Core epistemic rule for this experiment:**  
Witnessed *publication of a digest* ≠ authentication of the *meaning or origin* of that digest.  
Anyone who controls the submitter key can publish any other digest under the same key. The witness quorum constrains the log operator, not the honesty of the submitter about what the bytes represent.

---

## 2. Stage R6-B — Two physical hosts (NOT YET EXECUTED)

**Status:** Protocol draft only. Requires explicit owner authorization before any host is touched.

### Preconditions (must be recorded before any command)

- Desktop = experimental E only (disposable low-privilege account, synthetic Ed25519 key only).
- Laptop  = experimental C only (separate disposable account, separate journal directory, mode 0700, no access to real Ario keys or production paths).
- Phone   = pure observer (receives only public proof + previous SHA; no private material).
- All real Ario private keys, signer material, trust state, and production directories remain completely untouched.
- Both hosts still share the same human administrator → `ADMINISTRATIVE_INDEPENDENCE = NOT_ESTABLISHED` by definition. The experiment measures physical separation + OS isolation, nothing more.

### Exact sequence (manual, logged)

1. Create disposable OS accounts and directories on each host. Record UID/GID, ownership, and permission bits.
2. Generate synthetic E keypair on desktop only. Copy *only* the public key to laptop C.
3. Run the same positive/negative tests as R6-A (EACCES both directions, single nonce spend, concurrent race, revocation, clock skew, unpinned key).
4. After a successful C spend, compute the exact post-fsync journal head SHA-256 on laptop.
5. Create a new *synthetic* public checkpoint file that contains only that head SHA + sequence + explicit flags (`evidence_admission_allowed=false`, etc.). Never include raw journal lines or private data.
6. Submit that checkpoint with a *fresh* ephemeral test key to the same `sigsum-test1-2025` policy from a machine that is not the C host (or from C under strict observation).
7. Obtain proof, verify offline on a third observation point (phone or separate session), record all hashes and timestamps.
8. Retain at least two independent observations of successive heads to begin checking monotonicity.

### Hard stops

- Any real Ario key path appears in any command → abort.
- Any authority flag is set to true → abort and mark contaminated.
- Root/admin on either host can still override both → record explicitly as `ADMINISTRATIVE_INDEPENDENCE: NOT_ESTABLISHED`.

---

## 3. Evidence consistency check (2026-11-18)

### Good / consistent points

- All documents and workflow logs correctly repeat `ADMINISTRATIVE_INDEPENDENCE: NOT_ESTABLISHED`, `PRODUCTION=NO_GO`, and `TRUST_ACTIVATION=NO_GO`.
- The public artifact contains only non-secret files; the ephemeral private test key was never uploaded.
- Offline verification + one-byte tamper failure are both recorded.
- The checkpoint is correctly described as a *quoted claim* from a prior CI run, not a fresh independent extraction of a C journal.

### Minor points that benefit from clarification (not contradictions)

- Run ID references should be centralized in one table (see below) so readers do not have to cross-check multiple places.
- The role-identity lab (R6-A) is Linux-only; Windows results mentioned in the PR body belong to the earlier implementation regression suite, not to the two-UID experiment itself.
- The proof contains more cosignature records than the policy requires (2-of-3). The authoritative check remains the policy’s quorum, not the raw number of cosignatures present.

### Canonical run reference table (to be maintained)

| Purpose | Run ID | Notes |
|---|---|---|
| R6-A OS custody (final green) | 44176378100 | Two UIDs, EACCES, concurrent nonce, revocation |
| Implementation regression (Linux+Windows) | 44176378090 | Existing code; not the new UID experiment |
| R6-C Sigsum public proof | 44175613003 | Synthetic checkpoint only |
| Earlier R6-A partial | 44173643104 / 44173655606 | Historical; digest quoted in synthetic checkpoint |

---

## 4. Clearer bilingual limitation language (recommended fixed wording)

**English (concise, for every R6 document):**

> This experiment demonstrates only that a synthetic digest can be publicly witnessed under the declared test policy. It does not demonstrate independent administration, real execution, journal authenticity, or any authority to admit evidence into Ario. All production and trust gates remain NO_GO.

**فارسی (روشن و ثابت):**

> این آزمایش فقط نشان می‌دهد که یک هشِ ساختگی می‌تواند تحت سیاست تست اعلام‌شده به‌صورت عمومی و با شاهد بیرونی ثبت شود.  
> استقلال مدیریتی، اجرای واقعی ابزار، اصالت ژورنال، یا هرگونه مجوز برای ورود شواهد به حافظه آریو را ثابت نمی‌کند.  
> تمام دروازه‌های production و trust همچنان NO_GO هستند.

---

**Final status of this note itself:**  
`RESEARCH_ONLY / DRAFT / HOLD / NOT_ADOPTED / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO`
