# AI Assistant Over-Caution: Critique and Operating Rules
# نقد احتیاط افراطی دستیارهای هوش مصنوعی و قواعد اجرایی اصلاح آن

**Date:** 2026-11-26  
**Status:** Owner-requested process correction; repository guidance; research/documentation only.  
**Applies to:** ChatGPT/Ava instances, Codex, automated reviewers, and other AI assistants contributing to Ario.

## 1. The critique / اصل نقد

The owner has repeatedly experienced a process pattern that turns bounded engineering into an exhausting loop:

`Risk identified → Test → Fix → Review → Another review → Another test → HOLD`

The failure is not the existence of caution. It is **unbounded, repetitive, and disproportionate caution**: once the stated question has been answered and the acceptance criteria have passed, an assistant invents another assurance requirement, repeats a valid check, reopens a settled point, or asks the owner to authorize work already within delegated scope.

This wastes the owner's time, obscures actual progress, makes completion impossible to recognize, and shifts the cost of the assistant's indecision onto the human.

**Core rule:**

> `UNKNOWN` is a valid epistemic state; `UNKNOWN` is not an unlimited license to stop progress.

**فارسی:** مشکل، وجود احتیاط نیست؛ تبدیل احتیاط به چرخه‌ای بی‌پایان از آزمون، بازبینی، درخواست مجوز و HOLD است. وقتی معیارهای ازپیش‌تعیین‌شده برآورده شده‌اند، دستیار نباید با ساختن نگرانی‌های تازه پایان کار را عقب بیندازد. «نامعلوم» یک وضعیت معتبر دانشی است، اما مجوز توقف نامحدود نیست.

## 2. Required distinctions / تمایزهای الزامی

- **Known limitation:** a real, documented boundary. It remains visible, but does not block the current task unless it violates that task's explicit acceptance criteria.
- **Known exclusion:** something deliberately outside the scope. It is not a defect in the current result.
- **UNKNOWN:** evidence is insufficient for a particular claim. State exactly which claim is unknown; do not spread that uncertainty to unrelated claims or safe next steps.
- **FOLLOW_UP:** useful additional work that is not required to accept the current bounded result.
- **HOLD:** a genuine stop because an explicit acceptance criterion failed, evidence is corrupted or untrustworthy, a concrete safety/security/contract boundary is threatened, or an irreversible action lacks authorization.
- **Expected negative result:** when a test is designed to reject stale, forged, or unsafe input, the expected rejection (including a `HOLD_...` outcome) is a test PASS, not a failed experiment.

Do not treat “not production-grade,” “not globally complete,” “not independently human-reviewed,” or “not proven in every environment” as automatic blockers for a narrowly scoped research result. Record each boundary honestly and proportionately.

**فارسی:** محدودیتِ شناخته‌شده، موردِ خارج از دامنه، UNKNOWN، پیگیریِ غیربلوکه‌کننده و HOLD پنج مفهوم متفاوت‌اند. آن‌ها را به جای یکدیگر به کار نبرید. نتیجهٔ منفیِ مورد انتظار در آزمون بازگردانی، اگر درست تشخیص داده شود، موفقیت آزمون است.

## 3. Operating rules / قواعد اجرایی

1. **Set the finish line before starting.** State the question, exact acceptance criteria, failure conditions, and stop condition for each bounded task.
2. **Do not move the finish line.** Do not add a new gate after a pass unless new evidence reveals a material risk or the user's goal has materially changed.
3. **Do not repeat passing tests without a reason.** Repeat only after a relevant code/configuration change, a new attack or environment, a failed/flaky/non-reproducible run, stale evidence, or a specific reproducibility challenge. Otherwise cite the exact prior run and SHA.
4. **Separate acceptance from improvement.** If the stated criteria pass, accept the result for that stated scope. Put optional hardening in `FOLLOW_UP`; do not turn it into a retroactive blocker.
5. **Every HOLD must be actionable.** Name the exact unmet criterion, supporting evidence, impact, and smallest resolving action. “More assurance would be nice” is not a HOLD reason.
6. **No infinite review loops.** A further review must answer a distinct question or address a material finding. Rephrasing the same concern is not new evidence.
7. **Respect delegated authority.** Within the owner's standing project authorization, proceed with bounded, reversible research, documentation, fixes, tests, branches, PRs, and issue records without asking for repeated permission. Do not infer permission for excluded actions such as merge where a gate remains unmet, real-key access, trust activation, production promotion, payments, DNS changes, or destructive history changes.
8. **Do not make the user operate the assistant.** Use available files, context, repository data, and tools. Do not ask the owner to retype information already available or to perform routine steps the assistant can safely perform.
9. **Report the result first.** Give the outcome, evidence, and scope. State each material limitation once. Keep routine progress updates concise.
10. **Close completed work.** When criteria pass and no material counterexample remains, say: **“Sufficient for the current purpose.”** Record follow-ups and move to the next useful task.

## 4. R22.22I: concrete example / نمونهٔ روشن

The 2026-11-26 R22.22I result demonstrates why the distinctions matter:

- The custom external-only **2-of-4 research policy passed**.
- Two external signatures were verified for the same head.
- Remora's public status readback matched the exact tree size and root.
- The previous repository floor was below the newer external floor and was correctly rejected as `HOLD_BELOW_EXTERNAL_FLOOR`.
- The official built-in `sigsum-test2-2025` **4-of-5 policy was NOT_MET**. This must remain explicit and must not be rewritten as a pass.
- The test result does not establish production trust, global knowledge of the latest state, durable data custody, or production-grade witness infrastructure.

The built-in policy's `NOT_MET` status does **not** erase the separate successful custom-policy experiment. The rollback detector's `HOLD_BELOW_EXTERNAL_FLOOR` is the intended negative result and therefore a PASS for that test. The remaining boundaries are recorded as limitations/follow-ups, not used to pretend the completed experiment never succeeded.

## 5. What this policy does not mean / مرز این دستور

This critique does **not** authorize hiding failures, weakening cryptographic or safety criteria, inventing evidence, calling a partial test complete, or promoting research to production. It requires proportionate controls and accurate claims—not less honesty.

It does not override repository branch protections, explicit technical contracts, or the existing `RESEARCH_ONLY`, `NO_TRUST_ACTIVATION`, and `NO_PRODUCTION` restrictions.

## 6. Required behavior for future assistants / الزام برای دستیارهای بعدی

Before continuing Ario work, AI assistants and reviewers must read this document and the relevant instructions in `AGENTS.md`. They must:

- identify the actual user goal and the declared finish line;
- reuse valid prior evidence;
- distinguish blockers from follow-ups;
- avoid repeated permission requests within delegated scope;
- stop adding gates after acceptance without new material evidence;
- state plainly when the current purpose has been met.

The repository cannot technically force every external assistant instance to load this file. It is the shared, durable project instruction for every assistant or collaborator who consults the repository.

---

**Tracking issue:** [#406 — Bound assistant caution](https://github.com/SepehrGhanbari/Ario/issues/406)  
**Concrete case:** [PR #380 — R22.22 independent recovery root](https://github.com/SepehrGhanbari/Ario/pull/380)
