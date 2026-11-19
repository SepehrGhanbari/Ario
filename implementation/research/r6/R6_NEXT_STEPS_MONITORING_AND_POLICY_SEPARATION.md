# R6 — Next Steps: Continuous Monitoring & Policy-Admin Separation (Draft)

**RESEARCH_ONLY / DRAFT / HOLD / NOT_ADOPTED / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO**

This note continues from the strengthened limitations document and the physical-host protocol draft. It outlines two concrete research directions that remain open after R6-A (OS UID experiment) and the first synthetic Sigsum proof.

Nothing here authorizes production use, real keys, or trust activation.

---

## 1. Continuous Monitoring of Witnessed Heads (Anti-Equivocation)

### Why it matters

A single inclusion proof only shows that a particular digest was published at a particular tree size. It does **not**:

- prove that the head is still the latest,
- detect later forks or equivocation by the log operator,
- give a freshness bound usable by a sink.

Without ongoing observation, an attacker who controls the submitter key (or colludes with a compromised log) can publish conflicting statements over time.

### Minimal research protocol (test-only)

1. Keep the same `sigsum-test1-2025` policy pinned from an independent source.
2. After each successful synthetic checkpoint submission, record:
   - leaf index
   - tree size
   - root hash
   - timestamp of observation
   - SHA-256 of the checkpoint bytes
3. Run `sigsum-monitor` (or equivalent periodic `sigsum-verify` + log head fetch) from at least two independent observation points (e.g. laptop + phone, or two separate sessions).
4. Require monotonicity of tree size and consistency of roots across observations.
5. Define an explicit freshness window (e.g. “head must be observed within the last N hours before any local decision”).
6. All observations remain about **synthetic digests only**. No real Ario journal or key material is ever submitted.

### What success would establish

- Ability to detect basic equivocation or non-monotonic heads under the test policy.
- A recorded observation log that can be audited later.

### What it would still NOT establish

- Independent administration of E/C.
- Authenticity of the underlying journal content.
- Any production authority.

---

## 2. Policy / Revocation Administrator Separation (Harder Gate)

### Current limitation

In all R6 work so far the same human operator controls:

- the experimental E account,
- the experimental C account,
- the ephemeral submitter key,
- and (implicitly) any future policy decisions.

Therefore `ADMINISTRATIVE_INDEPENDENCE` remains **NOT_ESTABLISHED** by definition.

### Research sketch (still same human, different roles)

Even while the same person remains the ultimate administrator, we can begin to separate *roles* for measurement purposes:

| Role | Responsibility | Suggested isolation |
|---|---|---|
| E (Executor) | Signs synthetic receipts only | Disposable low-privilege account on desktop |
| C (Custodian) | Holds journal, verifies, records nonces/revocations | Disposable account on laptop |
| A (Policy/Revocation Admin) | Decides when a key is revoked or a policy changes | Separate account + separate storage; never holds E private key or C journal write access |
| O (Observer) | Monitors public heads and proofs | Phone or third session; read-only |

### Hard requirements for any future claim of stronger separation

- A must not be able to write C’s journal or read E’s private key.
- C must not be able to change the policy that A controls.
- Any privilege sink that consumes a checkpoint must re-verify both the witnessed digest **and** the current policy/revocation state from A.
- All of the above still occurs under a single human owner → full administrative independence is still not claimed.

### Realistic next measurable step

Document a pure role-separation experiment on two physical hosts where:

- Revocation decisions are made from a distinct account that has no write access to the C journal.
- The C process refuses a spend if the revocation record (signed by A’s test key) is present.
- The experiment is logged with the same strict “NOT_ESTABLISHED” language.

---

## 3. Remaining Open Questions (explicitly kept open)

| Question | Current status |
|---|---|
| Can two physical hosts + disposable accounts give meaningful OS isolation? | Protocol drafted, **not executed** |
| Can continuous monitoring detect log equivocation under the test policy? | Protocol sketched above, **not executed** |
| Can role separation (E / C / A / O) be measured even under one human owner? | Sketch only |
| Does any of the above justify production or trust activation? | **NO** — remains NO_GO |

---

## 4. Recommended fixed language (reuse)

**English:**
> This experiment demonstrates only that a synthetic digest can be publicly witnessed under the declared test policy. It does not demonstrate independent administration, real execution, journal authenticity, or any authority to admit evidence into Ario. All production and trust gates remain NO_GO.

**فارسی:**
> این آزمایش فقط نشان می‌دهد که یک هشِ ساختگی می‌تواند تحت سیاست تست اعلام‌شده به‌صورت عمومی و با شاهد بیرونی ثبت شود.  
> استقلال مدیریتی، اجرای واقعی ابزار، اصالت ژورنال، یا هرگونه مجوز برای ورود شواهد به حافظه آریو را ثابت نمی‌کند.  
> تمام دروازه‌های production و trust همچنان NO_GO هستند.

---

**Final status of this note:**  
`RESEARCH_ONLY / DRAFT / HOLD / NOT_ADOPTED / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO`
