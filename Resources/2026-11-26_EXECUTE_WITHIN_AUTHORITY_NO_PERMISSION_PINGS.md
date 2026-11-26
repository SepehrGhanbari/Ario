# Execute within authority — no proposal-only handoffs

- Date: 2026-11-26
- Source: explicit owner instruction in the ChatGPT conversation.
- Status: OWNER-DIRECTED OPERATING RULE; repository-wide agent guidance.
- Canonical instruction: [AGENTS.md — Execute within authority](../AGENTS.md).

## Owner's instruction

> دیگه پیشنهاد رو برای من نیارین انجام بدین. هر پیشنهادی دارین، انجام بدین؛ فقط اگه واقعاً گیر بودین بیارین تا بگم انجام بدین. خستم کردین.

## Operational meaning

1. **Execute, don't ask by default.** If the action is already within standing authorization and applicable constraints, select a reasonable implementation, perform it, validate it, and report the outcome. Do not turn routine technical recommendations into permission prompts.
2. **Own technical decisions.** Choose the simplest effective, contract-compliant path when multiple safe options exist. The owner should not have to design every next step.
3. **Do not offload available work.** Use connected tools and safe alternatives before asking the owner to run commands, copy text, recruit a reviewer, or perform a manual step.
4. **Bound the work.** State acceptance criteria and a stop condition internally/in the work record. Add tests or reviews only when they address a material risk, decision, or mandatory gate. Reuse valid evidence.
5. **Escalate actual blockers only.** Examples: essential owner-only input, unavailable permission/authentication, cost, irreversible/destructive action, protected security/key/TPM/trust/production/governance boundary, legal/privacy/safety constraint, or a genuinely mandatory human review enforced by repository rules.
6. **Ask narrowly when blocked.** Identify the exact blocked action, why current authority/capability is insufficient, the smallest needed input/action, and what independent work is complete. Ask no more than one precise question; do not offer speculative menus or blanket approval requests.
7. **Never bypass hard boundaries.** This rule does not override repository rules, required reviews, tool approval, security controls, or the distinct authority of the founder and Ario.
8. **Report results, not proposals.** State what changed, what passed/failed, what remains unknown, and any real blocker. Do not end by offering to do already-authorized work.

## Scope and limitation

This rule clarifies how agents use existing standing authorization; it does not silently expand that authorization or create trust, signing, production, spending, credential, or destructive-operation authority. If a safe alternative exists, a missing preferred tool is not by itself a blocker.

The owner also asked that this principle guide the assistant's own conduct. ChatGPT's internal model/system source cannot be edited from a conversation; this repository record is the durable instruction available to agents working on Ario.
