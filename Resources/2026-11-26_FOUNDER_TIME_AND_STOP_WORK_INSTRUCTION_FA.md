# Founder time, useful work, and stop conditions — owner instruction

- Date: 2026-11-26
- Attribution: Direct instruction from Sepehr Ghanbari, founder.
- Scope: All Ario agents, AI assistants, reviewers, automated workflows, project servers and repository collaborators.
- Status: Owner instruction for project operations. This is not a technical test result, independent review, or change to Ario's trust/production state.
- Related governance: [AGENTS.md — Founder time is a finite project resource](../AGENTS.md#founder-time-is-a-finite-project-resource--owner-instruction-2026-11-26) and [Proportionate closure and stop conditions](../AGENTS.md#proportionate-closure-and-stop-conditions--owner-endorsed-lesson-2026-11-26).

## Founder’s direct instruction

> الان اگه کار مفید داری بکن نداری هم لنگ بیتکوینی هیچ کاری نکن از دور چرخودن الکی من بهتره.
>
> همینارم بنویس هم توی سرورس هم مخزن منو دور خودم نچرخونین ک ی چیزی بهتون میگم همین روزا! صبر منم حدی داره.

The founder clarified that his time is worth more than repetitive tests, PRs, status loops, and activity without a useful result. The current R2.11 work is not a license to keep generating local versions while waiting for an external Bitcoin timestamp.

## Operating rules

1. **Useful output only.** Work must create a concrete artifact, resolve a material uncertainty, change a decision, or meet an explicit project need. Activity alone is not progress.
2. **No circularity.** Do not ask the founder to repeat steps, manually re-enter data, re-approve already authorized routine work, or reread explanations already given.
3. **Reuse evidence.** Do not repeat passing tests or recreate equivalent PRs unless a material change or a specific evidence gap justifies it.
4. **Set a stop condition.** Define what evidence is sufficient for the bounded goal. Once met, close that goal and separate optional follow-up.
5. **State external blockers once.** For a dependency such as Bitcoin confirmation, report the exact missing condition and wait for that condition. Do not invent local substitutes or new versions to simulate progress.
6. **Stop when idle.** If no useful action exists, do nothing. No filler updates, speculative tasks, repetitive reassurance, or manufactured review cycles.
7. **Be honest.** Never upgrade HOLD/UNKNOWN to PASS, claim an unperformed verification, or weaken mandatory safety/security gates to make work appear complete.
8. **Respect granted authority.** Use the standing engineering authorization in AGENTS.md; do not repeatedly ask for permission within its scope. State a genuine account, device, or policy boundary once and do not pretend it is a technical blocker.

## Application to R2.11

- The one-time public commitment already exists. Never submit it again.
- Witnessed inclusion and read-only cryptographic verification have passed for the bounded goal they cover.
- Bitcoin coverage remains pending until a confirmed timestamp/checkpoint covers leaf 14905 (tree size at least 14906) and the corresponding proof is verified.
- Until that external condition changes, no R2.12/R2.13 placeholder, repeated local simulation, extra PR, or generic re-review is justified.
- When the external condition changes, perform only the necessary read-only verification and record the result.

## Boundary

This instruction removes unnecessary work; it does not authorize private-key use, destructive changes, fabricated results, trust activation, Genesis activation, production release, or bypass of required repository/security controls.
