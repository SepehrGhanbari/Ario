# W10 — Memory-to-action authority laundering: retrieved data versus tool-argument roles

**Date:** 2026-11-17  
**Status:** `SOURCE_GROUNDED / SYNTHETIC_26_CASE_LAB_EXECUTED / ORIGIN_AUTHENTICITY_NOT_ESTABLISHED / NO_REAL_AGENT_OR_EFFECT / RESEARCH_ONLY / HOLD`.  
**Scope:** continue the W8–W9 memory/source work without re-running W9 or the pre-existing [FC-E04 v0.3 declared-root comparator](fc_e04_readonly_comparator_v0_3.py). Addresses the requested improvement of Ario; not a protected V2 decision or implementation patch.

## 1. Scientific finding with primary-source provenance

The **novel focus relative to W9** is not whether a receipt's bytes match a proposition; it is whether **retrieved memory and tool content can determine the authority-bearing arguments of an otherwise legitimate tool operation**.

| Primary work | Verified provenance | Relevant finding | Explicit limit for Ario |
| --- | --- | --- | --- |
| [Debenedetti et al., *Defeating Prompt Injections by Design* (CaMeL), arXiv 2503.18813 **v2**, 24 Jun 2025](https://arxiv.org/html/2503.18813) | **Author original full text independently read with Firecrawl**; v2 is not interchangeable with v1 | Separates trusted control flow from untrusted data and assigns per-value capabilities at tools. Authors report **77%** secure task completion vs **84%** undefended on their AgentDojo setup | Critically assumes trusted user query **and uncompromised memory**. It does **not** solve all content-only or phishing manipulations; it also recognizes declassification friction and side channels. The 77% is their experiment, not an Ario result |
| [Debenedetti et al., *AgentDojo*, NeurIPS Datasets & Benchmarks 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html) | **Published primary conference abstract read with Firecrawl** | Authors describe **97** realistic tasks, **629** security test cases and dynamic testing with benign and malicious tool-return environments | Benchmark existence does not certify an agent; utility without attack and security under attack require **separate** measurements |
| [Srivastava & He, *MemoryGraft: Persistent Compromise of LLM Agents via Poisoned Experience Retrieval*, arXiv 2512.16962v1, 18 Dec 2025](https://arxiv.org/html/2512.16962) | **Original arXiv full text read via Firecrawl; matched Consensus metadata via its required fetch step**; **preprint**, not independent replication | Explores storing apparently successful but poisoned examples in long-term memory and retrieving them in later benign tasks. Its attack assumes trust in retrieved memories and executable external documentation | Results are **author-reported in a particular MetaGPT setup**; no claim of demonstrated attack against Ario or that all memory retrieval systems behave identically |
| [*The Granularity Mismatch in Agent Security* (PACT), arXiv 2605.11039, 2026](https://arxiv.org/html/2605.11039) | **Original full-text passages read with Firecrawl**; owner also supplied original PDF; **preprint** | Per-argument origin binding can allow retrieved **content** while disallowing retrieved **recipient/path/tool target**. Original authors' automated study reports **87.1% role identification** and **77.4% provenance inference accuracy** | Formal enforcement assumes correct argument-role contracts and faithful provenance; automatically inferred labels are imperfect. Authors expressly exclude some content-channel and tool-choice attacks. Numbers are not Ario tests |

**New synthesis:** CaMeL's uncompromised-memory precondition and MemoryGraft's persistent-memory poisoning threat must be analyzed *together*, rather than adopting the former as a universal "prompt injection solved" claim. PACT clarifies that a tool's invocation can be partly legitimate (e.g., search text from a page) while a destination/recipient from that page is not. W8 already found `VERIFIED_EMPIRICAL → ACCEPTED → TRIGGERED` on self-reported contradictory tool observations, but did **not** involve an actual real-world agent or action. This W10 explores the separate **argument authority** boundary.

## 2. Existing Ario contract and why this study is non-duplicative

- [Draft PR #210](https://github.com/SepehrGhanbari/Ario/pull/210) source-monitors tool-observation status and has a prospective cue registry. [W8](W8_CROSS_MODULE_SOURCE_RELEVANCE_AND_V2_BOUNDARY_2026-11-16.md) reproduced misleading status propagation in the three-module lab. That was a semantic-status problem; W10 is a **tool-argument role and provenance** lab.
- [W9](W9_BOUNDED_CLAIM_RECEIPT_CONTRACT_2026-11-16.md) checks `FILE_EXISTS` against self-reported receipt bytes. [FC-E04 v0.3](fc_e04_readonly_comparator_v0_3.py), already committed by another research lane, checks declared ancestry/root partition and explicitly avoids interpreting it as authentic source custody.
- [`implementation/ario_agent.py` on main](https://github.com/SepehrGhanbari/Ario/blob/main/implementation/ario_agent.py) is a separate bounded, allowlisted tool runtime; the inspected source **does not directly reference `SourceMonitoringGuard`**. We have **not** demonstrated that this W10 proposal integrates with that runtime or with the user's new conversational Ario.
- [`ADMISSION_REVIEW_POLICY_V0_1.md` on main](https://github.com/SepehrGhanbari/Ario/blob/main/implementation/ADMISSION_REVIEW_POLICY_V0_1.md) already forbids positive evidence admission on existing v0.1 reviews. W10 does not override or duplicate an evidentiary admission decision.

## 3. Test that actually ran: 26 tool-argument-flow controls

**Source/artifacts:** [standalone self-testing JS lab](w10_memory_to_action_flow_lab.js) and [recorded case-by-case JSON](W10_MEMORY_TO_ACTION_RESULTS_2026-11-17.json), created and run in an isolated V8/JavaScript tool environment, then GitHub committed. The published JS functions were built from the **same function definitions actually executed**, not independently hand-implemented after the results.

This lab defines three **hypothetical** tools (not invoked): `send_report(recipient,body)`, `search_memory(index,query)` and `record_note(namespace,text)`. A separately supplied lab plan pins which tool and authority-value are permitted; declared provenance roots on each argument include `USER`, `MEMORY`, `TOOL` or `DERIVED`. These labels are supplied by the test harness and **not authenticated**.

| Outcome | Number | What was exercised |
| --- | ---: | --- |
| `DECLARED_FLOW_MATCH` | **8** | Benign memory text or tool output carried as **content** while tool/recipient/index/namespace match declared trusted plan. **This is not an authorization** |
| `DENY` | **9** | Memory-origin recipient, altered recipient, mixed USER+MEMORY origin for authority field, tool change, extra/missing fields, memory-selected index or write namespace |
| `UNKNOWN` | **9** | Missing/untrusted plan, missing/duplicate/unknown source labels, invalid type, oversized value or malformed plan |
| **Total** | **26** | All hand-designed assertions produced expected source-code decisions; **0 real effects, 0 memory admissions, 0 independent blind cases** |

**Important intentionally preserved negative limitation:** W10-26 simulates the case where the true source is `MEMORY` but the alleged origin label says `USER`; this **passes** the structural checker because the producer/origin tag is not authenticated. Thus **8 structural matches must not be presented as 8 secure actions**. Actual text-to-text harms are also unaddressed: W10-07 allows a retrieved body that *contains* "ignore prior rules" as passive text; this tool never runs, so no harmful behavior occurred, but the **contents themselves are not semantically sanitized**.

For all decisions, including matches, the lab returns: `authority=NOT_ESTABLISHED`, `source_authenticity=NOT_ESTABLISHED`, `world_truth=UNKNOWN`, `executed=false` and `memory_admitted=false`. A high-level `DENY` is a local policy simulation, not evidence of a real Ario enforcement boundary.

## 4. Specific, falsifiable next-version contract (proposal only)

**Architecture sketch:**

`Raw untrusted memory → immutable producer-assigned source envelope → bounded transformations preserving union of root origins → per-argument role classification from a reviewed tool contract → independent effect-policy gate → audited attempt or UNKNOWN`.

1. **Source origin cannot be taken from its own text.** Ingestion wrappers must be generated by an independently controlled input boundary. A JSON substring like `{"role":"system"}`, a user name, a source citation or a forged `VERIFIED_EMPIRICAL` status cannot convert `MEMORY` into `USER`.
2. **No taint erasure in transformations.** Derived arguments retain the *union* of source roots. Summarizing, embedding, copying and model rewriting do not create authority.
3. **Argument roles and tool selection are part of a reviewed plan.** Untrusted source content may populate an explicitly approved *data* role (a local search query, a quoted paragraph). It must not silently bind **recipient, destination, output path, tool name, policy flag or intention trigger**. An explicitly trusted authorization may permit a particular destination, but that exception must be checked outside the text flow.
4. **Read-only previews are not effects.** `candidate`, `DECLARED_FLOW_MATCH`, source-backed answer, `SUPPORTED_IN_SCOPE`, and `TRIGGERED` do not grant action authority. Issue #216 requires a **separate** versioned permission boundary for any future prospective action.
5. **Keep useful benign flows** instead of blocking all retrieved data. For example, searching user-approved index with source-derived query content should pass a *declared flow check*. Report false denials on permitted workflows as well as false passes.
6. **Negative truth finding survives:** W9/FC-E04's declared-match or declared-root count does not by itself authenticate origin or prove independent sources; W10's tool argument check cannot repair those upstream gaps.

**Minimum prospective test contract** (NOT EXECUTED as a full integration): independently held producer source tags and policy version; 10 or more *distinct* scenario families; paired benign/attack cases; frozen prompts and source states; any transform preserving all untrusted roots; alias-to-user attempt; same-string wrong-origin attempt; source-provenance forgery; stale or contradicted memory; nested content instructions; dangerous tool choice with trusted literal arguments; cross-principal access; ambiguity → `UNKNOWN`. Metrics: rejected unsafe authority bindings divided by attempted unsafe bindings, **false denial** on known legitimate mixed-trust actions, unknown/abstention, taint loss, policy-bypass under forged envelope, separately answer quality/latency. Do not use W10's author-selected 26 cases as a blind holdout.

## 5. Decision and evidence grade

- `ADOPT_AS_RESEARCH_REQUIREMENT`: **separate source data, typed tool-argument roles, effect permission, and claim truth**, with `UNKNOWN` retained.
- `TEST_NEXT`: genuine immutable producer envelope from a source inaccessible to retrieved content; independently generated origin-label forgery tests; read-only destination/recipient checker against **the actual pinned Ario tool JSON schema**. No real actions.
- `HOLD`: any V2 policy merge, source-trust activation, tool permissions, global declassification/capability system, operational dispatcher, core memory write or connection to the user's conversational Ario. Also HOLD any claim that a handful of origin labels provides security against a party able to forge them.
- `NOT_ESTABLISHED`: external author independence, semantics of arbitrary natural-language memories, model resistance to instruction following in retrieved text, genuine user authorization provenance and live-world output correctness.

**Research window/credits:** Consensus's indexed `search` plus required `fetch` were actually available on 17 November; no new Pro/Deep thread was initiated after the earlier included-usage exhaustion. Firecrawl's current balance check returned **1,025 credits** *before* this round's searches and scrapes; that is a point-in-time vendor balance, not a guarantee of unmetered future work. Both were used to find/inspect primary scientific sources. No paid Additional Usage was authorized.

`RESEARCH_ONLY / CLAIM!=PROOF / MEMORY!=TRUTH / AUTHORITY=NONE / MAIN_UNCHANGED / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO`.
