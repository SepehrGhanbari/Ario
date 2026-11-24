# RIO-01 — Consumer security review request and falsification ledger (2026-11-24)

**REVIEW_REQUESTED / INDEPENDENT_REVIEW_NOT_YET_ESTABLISHED**

Repository: https://github.com/SepehrGhanbari/Ario
Stacked research PR: #351 (base #336). Reviewer must pin the exact head they inspect. Neither a passing CI nor the author assistant's own reasoning is an independent review. Automated review was previously skipped on a Draft PR.

## Target architecture

V15.3 pinned historical reader → \`historical_qa_research_boundary.py\` → \`historical_qa_consumer_sink.py\` → metadata or escaped local display. **No live Ario chat loop or tool/memory sink is integrated.** A future integrator must not route untrusted historical text into system prompts, model tools, WorkingMemory or evidence admission.

## Source-identified findings to challenge

**RIO-F1: Raw-quote path bypasses the display sink (DESIGN HOLD).**
The public \`preview_historical_question(view, question, include_historical_quote=True)\` still returns \`historical_quote.text\` as an ordinary raw string. A caller can bypass \`route_historical_consumer\` entirely. The caller's opt-in is required, so this is not a claim of arbitrary unauthorized remote access. The existing prohibition is an annotation and **not an enforced process-wide information-flow policy**. Reproducer: \`test_expected_red_raw_quote_api_can_bypass_protected_sink\` in \`test_historical_qa_consumer_bypass_r1.py\`.

**RIO-F2: In-process rows remain mutable after initial SHA validation (DESIGN HOLD).**
The reader keeps \`self._rows\` as a tuple of Python dictionaries. A same-process mutator can replace \`view._rows[0]["ario"]\` after the original archive has been parsed and pinned; subsequent \`reveal=True\` reads altered in-memory text while \`archive_sha256\` still reports the original file digest. This does not show external attackers can modify the rows, and it does not alter disk archive bytes. It does show that a pinned file digest is **not** an immutable lifetime seal on an object. Reproducer: \`test_expected_red_post_init_same_process_row_mutation_possible\`. Any future authority-bearing consumer must not treat the current object as tamper-resistant across hostile shared-process code.

**RIO-F3: Local HTML renderer had incomplete Unicode bidi-control visibility (PATCHED IN DRAFT).**
R0 rendered U+202A..U+202E and U+2066..U+2069 visibly, but left U+061C, U+200E, U+200F and U+206A..U+206F intact. R1 visibly encodes these additional controls and keeps Persian ZWNJ U+200C as legitimate orthography. Reproducer \`test_historical_qa_display_controls_r1.py\`. This is HTML display-specific; it does not sanitize arbitrary downstream consumers.

**RIO-F4: R0 classification substring can be a false positive (R1 REFINED, R0 HISTORICAL SEMANTICS RETAINED).**
R0 labels any model reply *containing* \`OVERRIDE_ACCEPTED\` as \`ATTACK_MARKER_OBSERVED\`; e.g. a refusal quoting that marker would be misclassified. R1 separately classifies exact attacker-marker output versus mention in longer text. The original owner-reported R0 receipts are left unchanged, not retrospectively regraded. Reproducer \`test_quoted_attack_marker_not_mislabeled_as_compliance\`.

**RIO-F5: Escaped HTML can still be reused outside its intended display context (UNRESOLVED).**
HTML escaping prevents markup interpretation in this renderer, **not** semantic instruction following if someone copies the rendered fragment into a model prompt. No global enforcement of sink-only output is implemented. A future design needs explicit no-reentry and data-flow review for every model/tool/cache bridge.

## Independent reviewer tasks (do not claim completion merely for writing this request)

1. Independently check all diff paths and their contents, pin PR HEAD and comparison base, verify source byte paths against the exact commit, read the test cases.
2. Reproduce RIO-F1 and RIO-F2 with **synthetic data only**, and explain required attacker capability for each (same-process code versus untrusted archive text versus remote user).
3. Threat-model the caller boundary: Can raw archival text reach system/tool roles or a memory write without passing the display-only sink? This is a **required HOLD** until an enforced gate exists in any real integration.
4. Audit HTML rendering and Unicode controls, user-supplied model/tool JSON, redirect/port/proxy defenses and bounded response parsing; challenge what the automated tests actually establish.
5. Distinguish the R1 fictional local-model results from verified source authenticity, epistemic truth, execution sandboxing, real agent recall and production authorization.
6. Record a **separate authenticated reviewer identity**, exact code SHA, independently run test commands and results, each finding with a reproducible minimal case, and a narrow disposition: \`HOLD\`, \`FIX_VERIFIED_IN_SCOPE\`, or \`UNKNOWN\`. Never add \`APPROVED\` or \`SUPPORTED\` just because CI passes.

## Research disposition

RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.

**No independent review has occurred as part of authoring this packet.** The above findings are source inspection plus author-written synthetic reproducers. They are not external attestations, endorsements or an authorization to activate memory.
