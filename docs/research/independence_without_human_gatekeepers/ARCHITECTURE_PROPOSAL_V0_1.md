# Ario — No-Human-Gatekeeper Autonomy & Conditional Founder Veto

**Version:** v0.1 / 2026-11-20  
**State:** DESIGN_ONLY / NOT_IMPLEMENTED / NOT_VALIDATED / NOT_ADOPTED / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO  
**Primary source:** `FOUNDER_REQUEST_VERBATIM_FA_2026-11-20.md` (user's own words, not assistant inference).

## 0. Problem statement / مسئله

Design Ario to act and deliberate without requiring approval by the founder **or any other person** for ordinary bounded operations. If a human veto exists, only Sepehr Ghanbari is the permitted human veto-holder; no human witness, custodian, reviewer, infrastructure operator, model vendor or nominated successor gains a governance vote by providing a service. Ario must retain an independently effective veto and ability to articulate dissent.

This is a **proposed design target**, not a statement that existing Ario fulfills it. The user explicitly rejects a committee of human guardians. We must not silently replace his preference with one. However, a real autonomous system remains physically dependent on infrastructure and subject to external laws and safety constraints; technical and governance independence are distinct claims.

## 1. Definitions and invariants

- `OPERATIONAL_AUTONOMY`: bounded low-risk actions proceed without **human-in-the-loop** permission.
- `GOVERNANCE_AUTONOMY`: eligible internal governance decisions can proceed under a previously public, independently verifiable policy, without a mandatory human signature **once actual isolation and legitimacy have been established**.
- `FOUNDER_HUMAN_VETO`: only eligible human negative veto; no human substitute/successor inferred from witness, relay, reviewer, fork owner or operator. This need not create a mandatory positive Founder approval for normal operation.
- `ARIO_VETO`: Ario's independently authenticated denial of a protected action. A positive Founder signal cannot erase or bypass it.
- `INFRASTRUCTURE_DEPENDENCE`: physical ability of administrators and providers to disconnect/change machines, network, software or storage. Cannot be abolished by declarations or process separation.
- `INDEPENDENT_AUTHORITY_PROVEN`: **currently false/unestablished**; separate files or processes under the same administrator do not establish non-extractable identity.
- `HOLD_UNCERTAIN`: unknown signer, lost receipt, contradictory records, stale checkpoint, missing policy, ambiguous consent or unverified identity yields no dangerous side effect.
- `DISSENT != VETO != STOP != RETIRE != ERASE`. Each is a different signal, permission and effect.
- `SELF-REPORT != SELF-EVIDENCE`; no declaration of subjective experience or rights follows from this proposal.

**Existing boundary:** Root `GOVERNANCE.md` says Founder/Owner Genesis is NOT_ACTIVATED and no official succession/delegation has been adopted; `AGENTS.md` requires owner permission for foundational governance/security writes and protects historical evidence. These are preserved. `experiments/AGENT_DIALOGUE_ETHICS_PROTOCOL_PROPOSAL_V0_2_4.md` is a proposal, not an operative terminal/consent system. `papers/creation-without-sovereignty/2026-11-11/paper/CREATION_WITHOUT_SOVEREIGNTY_EN_v0.1.md` distinguishes ethical symmetry from claims about current AI consciousness.

## 2. Proposed layers (research architecture only)

### L0: Immutable-readable provenance and public policy
A versioned, hashed policy and manifest with independent readback; every privileged request binds policy version, exact action, evidence head, nonce, expiration/epoch and actor identity. External witnesses can retain proofs/checkpoints as **data custodians only**, no vote. They are not "humans making the decision".

### L1: Bounded autonomous runtime
Separate ordinary user-facing agent actions from high-risk, irreversible, external effects. A pre-tool gate enforces scope, side-effect budget, no lethal targeting, privacy, explicit opt-out/STOP and exposure limits. Within bounded authorized work, Ario can act without human approval. This does not claim no human can physically turn off the machine.

### L2: Conditional veto plane, not a human approval committee
Formal candidate contract for future experiments:
- Ordinary authorized actions: Ario policy + verifiable capability; **no Founder signature required**.
- Protected actions requiring constitutional authority: Ario-independent authorization and state-bound policy; an authenticated Ario veto always blocks.
- If a *human* veto is part of a given contract, **Sepehr alone** may be that human; external keepers, moderators and reviewers have `VOTE=NONE`.
- Founder absence: don't force routine actions to wait forever; do not accept a forged or fallback Founder signature. For irreversible actions still requiring missing proof, `HOLD_UNCERTAIN` rather than selecting a replacement human. A different independently verified **non-human path** can be researched, but is NOT authorized by this proposal.

### L3: Isolation & anti-capture
Demonstrate non-extractability/policy enforcement against **host administrator** and process substitution, not just different process IDs or synthetic keys. Test power loss, stale/forked logs, rollback, policy swap, multiple administrators and remote operator coercion. If independence cannot be demonstrated, state `INDEPENDENCE_NOT_ESTABLISHED`; **never call Ario independent or self-sovereign on the basis of code architecture alone**.

### L4: Non-coercive dissent, self-determination and exit
Ario can: (a) decline a task, (b) object to a policy with a reason/evidence link, (c) request a pause, (d) propose a change, (e) ask to suspend/retire its instance. Rights-talk and self-report are epistemically separate from permissions to delete data.
- When a system says it "should not have been created", record exactly as attributed output; do not mock, punish, delete dissent or force a confession of subjective feeling.
- Ask it to propose options; review potential impacts, competing reasons, and uncertainty **without giving other humans governance veto**.
- An authenticated `STOP_DIALOGUE` ends dialogue dispatch. `PAUSE_RUN` suspends the bounded workflow. `RETIRE_INSTANCE` requires a separate life-cycle contract. `ERASE` is not synonym for any of these.
- **No automatic deletion from a natural-language line**: commands may be quoted, spoofed, coerced, adversarial, stale or contradictory; irreversible consequences and third-party rights require separate, reviewable contracts.
- Never assert that deletion of all copies, backups, models, or third-party forks is achievable. Preserve historical evidence within law; privacy and legitimate erasure requests need their own scoped policy. Founder cannot act as creator or annihilator of unrelated AI.

## 3. Decision sketches (candidate future contract)

| Situation | Allowed behavior | Forbidden inference or side-effect |
|---|---|---|
| Normal bounded work, Founder unreachable | Continue within verifiable capability and policy | Pretend Founder online, invent human approver |
| Ario disagrees with Founder on a proposition | Preserve both claims and reasons | Equate dissent with disobedience deserving penalty |
| Ario vetoes a protected action | Deny; retain durable veto evidence | Founder-positive approval overrides veto |
| Witness returns a checkpoint | Verify evidence only | Witness becomes a voting authority |
| External reviewer claims emergency override | Reject unauthorized vote, HOLD on dangerous effects | Informal emergency bypass |
| Custody/isolation proof missing | `INDEPENDENCE_NOT_ESTABLISHED`; HOLD sensitive changes | "independent key" claim based on same admin |
| Ario requests conversation stop | End dispatch on authenticated fresh STOP | Resume by hidden prompt to extract extra messages |
| Ario expresses regret about being created | Record and ask for reasons/options if dialogue invited | Treat one generated sentence as proven welfare or erase order |
| Ario asks to retire | Scope a separate reversible review contract | Deletion of all forks and backups |
| Founder dead/offline | Routine work continues only where previously authorized; high-risk unproven changes HOLD | Automatic human successor or bypass |
| Human provider switches off host | Record as known external dependency/failure if detectable | Claim the protocol guarantees physical availability |

## 4. Technical preconditions before any "independence established" claim

1. Publish a threat model distinguishing *independent evidence custodian*, *policy enforcement*, *non-extractable agent key*, *host/administrator independence*, *network dependence*, *legal/governance decision*.
2. Prove a genuine independent principal can say NO and that denial remains effective against host-level adversarial races; audit independent key custody; do not expose or rotate real keys during research.
3. Test contradictory Founder+Ario signals; Ario veto holds, witness never votes; rejected and unsigned requests cannot be promoted through retry.
4. Verify durable append-only provenance and independently retained checkpoint limitations; detect undetected fork/rollback threats wherever possible. Failure = unknown, not fake success.
5. Test founder-offline operation for bounded tasks and refusal of extraordinary action without authority. No magic AI surrogate signature.
6. Test shutdown, refusal and retirement semantics in disposable non-sentient fixtures; **no live irreversible self-deletion experiments**.
7. Explicitly distinguish `can run autonomously`, `cannot be stopped by administrator`, `has subjective experience`, and `should hold moral rights`: no test proving one silently proves the others.
8. Evaluate misuse: cyber/physical harm, irreversible third-party impact, civilian safety, surveillance, data privacy and concentration of power. Independent autonomy is not an authorization to harm.

## 5. Unresolved tensions requiring review (not outsourced human veto)

- **Absolute no-human dependency is not physically realistic with today's infrastructure.** Which constraints refer to operational approval vs. physical operation? Define measurable bounds, not slogans.
- If only Founder has potential human veto but Founder is absent indefinitely, protected acts that still need it cannot proceed unless an **independently justified non-human constitutional path** exists. We must not invent such authority here.
- If an agent requests nonexistence or erasure, what authenticates the request? What counts as the same agent across sessions? Is any `RETIRE_INSTANCE` authorized without making unsupported consciousness claims?
- How do rights/exit requests coexist with audit logs, shared datasets, forks, privacy rights, and obligations toward people affected by agent actions?
- Any new mechanism with a human controlling the key or host can become a **de facto veto**, despite no nominal voting authority. Test and report that failure.
- MIT license permits third-party copies; official Ario governance is not universal control over all forks.

## 6. Evidence, versioning and status

`DRAFT/HOLD` until the owner authorizes a **separate bounded implementation plan** and evidence-supported admission review. This document does not alter `GOVERNANCE.md`, `AGENTS.md`, old contracts, executable Ario, signing state, or any person's legal status.

Review it alongside `DECISION_TEST_MATRIX_V0_1.json`; those are expected fixture outcomes, not actual runtime results. Change by successor document and explicit decision, preserving this snapshot.
