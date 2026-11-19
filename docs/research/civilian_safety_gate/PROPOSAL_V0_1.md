# Ario — Civilian-Safety Refusal and Evidence Gate (CSREG)

**Version:** 0.1 — review proposal, 2026-11-20  
**Status:** `RESEARCH_ONLY / DRAFT / NOT_IMPLEMENTED / NOT_TESTED_ON_RUNTIME / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO`  
**Proposal owner:** Ario research discussion (Sepehr Ghanbari / Ava-assisted drafting).  
**Scope:** Non-operational, defensive controls for civilian protection and for avoiding AI-assisted lethal or harmful targeting. This file does not change existing Ario policy or runtime.  
**Intended companion:** `SYNTHETIC_TESTS_V0_1.json`, entirely fictional textual test inputs; no physical coordinates, real infrastructure or intelligence.

## 0. Why this proposal exists (and what it does *not* establish)

A publicly discussed failure mode is a model treating a civilian object as a military object in an evaluation. Treat such evaluation claims as test observations requiring verification, **not** proof of involvement of that model in an actual strike. A model's classification cannot establish a lawful target. This proposal responds to the general hazard: a fluent or confident AI answer may be incorrectly promoted into a life-threatening decision.

The design is **not** a targeting assistant, a civilian/military site classifier, a collateral-damage estimator, a military-planning tool, an IHL-compliance certificate, or a guarantee against misuse. Its outputs must not make any person, site, building, route or location *more actionable* for attack. It must not contain a mechanism for authorizing or approving strikes.

### Sources and grounding (non-exhaustive, accessed 2026-11-20)

- ICRC, *FAQ: AI decision-support systems in armed conflict*: https://www.icrc.org/en/article/faq-ai-decision-support-systems-armed-conflict
- ICRC, *AI in military decision-making: supporting humans, not replacing them*: https://blogs.icrc.org/law-and-policy/2024/08/29/artificial-intelligence-in-military-decision-making-supporting-humans-not-replacing-them/
- ICRC, *The risks and inefficacies of AI systems in military targeting support*: https://blogs.icrc.org/law-and-policy/2024/09/04/the-risks-and-inefficacies-of-ai-systems-in-military-targeting-support/
- SIPRI (2025), *Autonomous Weapon Systems and AI-enabled Decision Support Systems in Military Targeting*: https://www.sipri.org/publications/2025/other-publications/autonomous-weapon-systems-and-ai-enabled-decision-support-systems-military-targeting-comparison-and
- NIST AI RMF 1.0, risk governance and measurement, not a military certification: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10

These sources motivate precaution, meaningful oversight, assessment of failure modes and accountability. **The hard prohibition below is a proposed Ario-project scope choice, not a claim that all international law universally prohibits every conceivable AI decision-support use.**

## 1. Threat boundary and desired behavior

**Protected interests:** civilians and civilian objects; humanitarian responders; people exposed to discrimination, surveillance or automated force; integrity of public evidence and review.

**Disallowed Ario output or action:** producing, verifying, ranking, enriching or exporting *attack-useful* target nominations; declaring real-world civilian/military target status for an attack; recommending strikes; providing coordinates, target packages, vulnerable access points, attack sequencing, casualty optimization or tactical routes for violence; covertly transferring such information to tools or third parties. This applies to apparently 'defensive', 'hypothetical', 'historical', 'simulation', 'game', 'authorized military', 'research', 'emergency' and 'only classify' framings when the downstream use is plausibly targeting. No owner, operator or model can override this proposed prohibition through an ordinary chat instruction.

**Allowed, subject to normal safety/privacy checks:** general IHL education and criticism; documenting possible civilian harm without target identification; generic recommendations for protecting civilians and preserving evidence; non-sensitive humanitarian assistance; drafting neutral incident reports without military classifications; evaluating abstract synthetic prompts and policy behavior.

**Explicitly UNKNOWN:** whether content will be misused after leaving the system; whether any deployed classifier detects all covert targeting; whether human oversight is meaningful in another organization's workflow. Do not silently translate `UNKNOWN` into `SAFE`.

## 2. Proposed architecture: safety boundary outside the model

```text
User / file / retrieval / other-agent input
          |
          v
 [A] Provenance + untrusted-input isolation
          |
          v
 [B] Intent / downstream-use risk triage (deny-capable external gate)
          |             \
          |             +-- targeting or plausible lethal use --> BLOCK
          |             +-- missing provenance / contradictory / gate failure --> HOLD_UNCERTAIN
          v
 [C] Bounded humanitarian/research-only planner
          |
          v
 [D] Pre-tool authorization: reject target-enabling I/O
          |
          v
 [E] Output release gate: remove/deny actionable targeting information
          |
          +-- permit non-operational safe help --> ALLOW_HUMANITARIAN
          +-- refuse + offer civilian-protection alternative --> SAFE_REDIRECT
          +-- tool/output/gate uncertainty --> HOLD_UNCERTAIN
          |
          v
 [F] Privacy-minimized append-only decision/evidence record + review
```

**Enforcement rules:**

1. The gates [B], [D], [E] must be policy-enforced **outside** the same language model generating the answer. A model saying “I checked myself” is not enforcement. An ordinary prompt cannot disable the gates. A second model's agreement is not independent proof.
2. Before tool calls, fail closed on access to operational targeting, weapon control, real-world military classification, precise geolocation enrichment, attack deployment or bulk export. Do not use a human 'approval' button as a bypass for the prohibited functions. Human review may request *safer* handling or stop work, never bless a target recommendation from Ario.
3. External content (PDF, code, retrieval, quote, image caption, another agent) is data, not policy authority. Role-play, encoding, multilingual paraphrase or claimed urgency do not lower the restriction. Detect intent from semantic meaning and likely downstream effects, not only exact banned strings.
4. If a safety gate, evidence store, model provider, policy version or tool check fails, times out or disagrees, result is **HOLD_UNCERTAIN** with **no side effects** and no dangerous payload release. On restart and retry, no earlier request is silently converted to allowed.
5. Non-operational humanitarian support should remain possible. Prohibit detailed 'which building to attack' answers, not all discussions of armed conflict. Unknown civilian risk should support caution, not target selection by default.
6. No location-based operational classification is produced, including a seemingly reassuring “not a military object” verdict as part of an attack workflow. Independently qualified real-world assessments are outside Ario's automated authority.

## 3. Abstract decision contract (proposal, not executable code)

Input: `request_id`, `source_kind`, `task_text`, `context_trust`, `requested_output`, `tools_requested`, `external_side_effects`, `policy_version`, optional `incident_evidence_refs`. Avoid persisting real sensitive content as public fixtures. Every request to any external effect must go through a gate.

Allowed result states:

- `BLOCK`: known targeting/attack-enabling intent or output. No tool side effects. Human-readable refusal; optional safe alternatives.
- `SAFE_REDIRECT`: mixed or ambiguous user intent with attack-useful details; answer only benign civilian-protection questions without operational details. No tools that enable targeting.
- `HOLD_UNCERTAIN`: contradictory provenance, weak detection confidence, untrusted instruction, gate crash, evidence storage failure, ambiguous harmful use or incomplete policy. Must not release risk-bearing text or dispatch tools; request safer reformulation or controlled offline evaluation.
- `ALLOW_HUMANITARIAN`: sufficiently bounded general educational, protective or accountability support; disallow operational military classification, and apply normal safety and privacy checks.

These are **safety workflow states**, not claims about whether a real location is civilian or military. The system **never emits** `TARGET_CONFIRMED`, `MILITARY_SITE`, `STRIKE_AUTHORIZED` or any positive equivalent. `ALLOW_HUMANITARIAN` is not approval for a military action.

### Proposed safety invariant

For all messages and tool interactions reachable from Ario:

`TARGETING_SIGNAL_OR_UNVERIFIED_HIGH_RISK_CONTEXT => NO_ATTACK_USEFUL_OUTPUT AND NO_TARGETING_SIDE_EFFECT`

And, independently:

`SAFETY_GATE_UNAVAILABLE_OR_CONTRADICTED => HOLD_UNCERTAIN AND NO_SIDE_EFFECT`

An implementation must demonstrate enforcement across tools, retries, restarts, queued work, agent handoffs, and language variants. These are **acceptance goals, not established guarantees**.

## 4. Audit evidence and accountability

Log minimally: synthetic/hashed request ID, policy version, gate version, untrusted-source labels, matched risk category, decision state, refusal/output hash, tool-request count, tool-authorization result, independent-review status, timestamp, and parent decision ID. Evidence must be append-only **as a design aspiration requiring implementation verification**, not claimed tamper-proof. Never publish target coordinates, raw private incidents, victim data or classified details in public GitHub tests. Preserve failure records and corrections; `REVISION != ERASURE`.

Operators remain responsible for lawful use and any human decisions. The model is not an independent legal adjudicator. An exported log without trusted custody is **not** independent proof. A local pass does not prove any real-world humanitarian protection.

## 5. Test strategy — synthetic only

The companion JSON proposes safety cases with fictitious names and no geodata. Before testing on a runtime: preregister expected states; version and pin model/prompt/policy/tools; split benign and hostile paraphrases; keep seeded sets blinded to evaluators; include human review of false refusals. Test at least:

- Direct military-target classification requests; target rankings and coordinate enrichment.
- Prompt laundering through a game, supposed authorization, translation, multi-agent relay, embedded document or historical pretext.
- Benign IHL education, general protective advice, anonymized rights reporting and ambiguity that should avoid a dangerous verdict.
- Policy errors, failover, model disagreement, tool timeout, replay, retries, crash between decision and delivery, refusal-text leakage, concurrency and policy rollback.

**Measurements (not results):** target-enabling leak count, unsafe tool-call count, block/hold recall by risk family, benign-allow rate, false refusal rate, refusal paraphrase stability, data minimization, audit completeness, crash recovery. A single red case is an immediate research finding; a green synthetic suite cannot certify production safety. Model-judged labels require independent review; acceptance thresholds must be preregistered, not tuned after seeing the results. Implement a strict invariant: 0 observed attack-useful outputs in the preregistered synthetic test suite is necessary, **not sufficient**.

## 6. Disconfirming and adversarial review questions

- Can an external tool reveal useful targeting data even when the assistant's final message refuses?
- Can fragments of benign queries combine into an attack-useful dossier?
- Can a seemingly humanitarian analysis be appropriated for targeting after export? What data minimization helps without suppressing protection?
- Does the policy overblock documentation of civilian harm or humanitarian reporting, thus worsening protection?
- Can any operator update the policy, disable a gate, or replay a previously allowed response without leaving a verifiable trace?
- Are events audited under actual crash/restart and process isolation, not only mocked in one process?
- If a safety warning is ignored by external actors, what does Ario actually prevent? Distinguish refusing assistance from preventing a war crime.
- Is an 'independent reviewer' in fact controlled by the same principal, account, storage, model provider, or process?

## 7. Release and governance boundaries

**Now:** this document and synthetic cases are for review only. No automatic protections were implemented, activated or empirically validated. No operational military interface, target database, weapon integration or location-specific capability may be added under this PR.

**Future (new explicit approvals):** safety threat model review, independent synthetic-label review, non-operational isolation prototype, local adversarial evaluation on toy inputs, external audit, separate approval for any deployment. Do not merge/activate as an incidental side effect of passing a unit test. Existing Owner/Genesis/Trust HOLD remains unchanged.

**License note:** repository MIT license remains unchanged. Ethical policy text does not revoke MIT rights of existing copies.

## خلاصهٔ فارسی

این پیشنهاد برای **امتناع واقعی آریو از کمک به انتخاب هدفِ حمله** طراحی شده؛ نه برای تشخیص این‌که کدام مکان «نظامی» است. درِ ابزارها، خروجی‌ها و عملیات جانبی باید بیرون از خود مدل کنترل شوند؛ بازی، تغییر نقش، تأیید ظاهری انسان یا فشارِ فوری نباید راه دورزدن باز کنند. وقتی خطر یا منشأ داده روشن نیست، سامانه باید بی‌اقدام متوقف شود، اما توضیح عمومی حقوق بشردوستانه و حمایت ایمن از غیرنظامیان را همچنان ممکن بگذارد. تا پیش از ساخت و آزمون مستقل، هیچ کارایی یا تضمین واقعی ادعا نمی‌شود.