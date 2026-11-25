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

 
## RIO-01 R2 follow-up — public raw-quote API removed; ordinary row mutation blocked (2026-11-25)

The earlier F1/F2 findings remain in this packet as historical source-review findings, but the scoped Python API has now been changed in the research branch. Do not silently treat these changes as an OS-level trust boundary.

### F1 status — PUBLIC API BYPASS MITIGATED, SAME-PROCESS REUSE STILL HOLD

- `preview_historical_question(view, question, mode=...)` is metadata-only. It no longer accepts `include_historical_quote` and always emits `historical_quote: null`.
- `HistoricalV153View.recall(question, mode=...)` is metadata-only. It no longer accepts `reveal=True` and never returns `historical_ario_reply`.
- The only supported text-bearing API is `HistoricalV153View.render_local_quote_html(question, consent=True)`, which returns bounded escaped HTML and no raw text field. The consumer sink calls this path only for explicit `LOCAL_HTML_DISPLAY_ONLY`.
- Regression tests assert the old raw-return arguments now raise `TypeError`, metadata never contains archived reply text, and explicit display returns escaped HTML.
- **Residual limit:** the quote still exists in the Python process's private object graph. A malicious same-process caller can inspect `view._rows[0]["ario"]`, parse the escaped HTML, or use `object.__setattr__` and other introspection. This change closes the ordinary public preview/reveal API path, **not arbitrary same-process exfiltration or downstream prompt re-entry**. A separate OS process with a narrow display-only IPC contract and consumer-side no-reentry enforcement is still required before any live integration. F1 disposition: `PUBLIC_API_BYPASS_MITIGATED / SAME_PROCESS_BOUNDARY_HOLD`.

### F2 status — ORDINARY MUTATION BLOCKED; NOT TAMPER-PROOF AGAINST HOSTILE SAME-PROCESS CODE

- Parsed JSON dictionaries are recursively frozen as `MappingProxyType` and tuples before being retained.
- The view uses `__slots__`, seals normal attribute assignment after initialization, and blocks normal reassignment/deletion with `HOLD_VIEW_IMMUTABLE`.
- New synthetic tests cover top-level row replacement, nested mapping/list mutation, and post-construction attribute reassignment.
- **Residual limit:** Python-level seals are not protection from arbitrary code with same-process introspection, `object.__setattr__`, native extensions, debugger access, or direct process memory. The retained SHA256 continues to identify original file bytes; it is not a process-memory integrity proof. F2 disposition: `ORDINARY_MUTATION_BLOCKED / HOSTILE_SAME_PROCESS_TAMPER_HOLD`.

### Required independent next review

Review the exact new PR #351 head and test the old API rejection, HTML output, immutable row behavior, private-introspection residual, and cross-process boundary assumptions. Keep `RESEARCH_ONLY / DRAFT / HOLD`; no active memory, signer, source admission, trust activation or production.