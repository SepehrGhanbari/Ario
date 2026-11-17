# Consumer-side authority boundary for claim-support proposals — V0.1 (research)

**RESEARCH_ONLY / PROPOSED / DRAFT / HOLD / NOT ADOPTED / NO MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO**

**Parent source pin:** Draft PR #260 head `7751ee50b14bef9db0e8423ddc195beb35551147`. Read-only claim-support contract: `implementation/CLAIM_SUPPORT_READONLY_CONTRACT_V0_1.md`. Governance: Issue #216. No historical claim, core memory, signer or registry modification.

## Hypothesis and counterexample

The sidecar `inspect_claim_support` can correctly return `REVIEWABLE_ONLY` when an unauthenticated proposer merely *declares* `SUPPORTS`. A **hypothetical, unsafe consumer** that implements `accept = (review_status == "REVIEWABLE_ONLY")` silently converts review eligibility into epistemic or authorization authority. This is a code-level counterexample / *future consumer risk*, NOT a verified current production exploit or a claim that such an adapter exists.

## Experiment

`implementation/claim_support_consumer_boundary_lab.py` implements `inspect_consumer_boundary(report)`, a separate, pure, non-authoritative projection. It accepts only an exact v0.1 report schema with fixed non-authority invariants. A well-shaped `REVIEWABLE_ONLY / UNAUTHENTICATED_SUPPORT_PROPOSAL` with zero authenticated independent sources becomes **`MANUAL_REVIEW_CANDIDATE_ONLY`**. Every output always sets:

- `epistemic_verdict=NOT_ASSESSED`
- `evidence_admission_allowed=false`
- `tool_execution_allowed=false`
- `memory_write_allowed=false`
- `signing_allowed=false`
- `trust_activation_allowed=false`
- `contract_adoption=NOT_ADOPTED`

Malformed or unknown input produces `NO_CANDIDATE`, without original claim text, source identifiers, hashes, or credentials. No original report is rewritten. Positive candidate discovery is preserved, but there is **no positive evidence-admission mechanism**.

## Falsifiers / required RED-GREEN properties

1. `REVIEWABLE_ONLY` is NEVER sufficient for admission, memory write, signing, tool execution or trust activation. The naive hypothetical consumer would make this mistake; the projection must not.
2. `UNKNOWN`, unrelated, contradictory, malformed, extra-field, wrong contract, and old `ACCEPTED` / `VERIFIED_EMPIRICAL` status inputs cannot grant admission.
3. Forged `source_authenticity`, `claim_assessment`, `reviewer_authorization`, `contract_adoption` or `independent_support_count>0` cannot authorize an action.
4. Boolean `True` cannot masquerade as an integer count; non-negative and maximum receipt bounds must apply.
5. Real `inspect_claim_support` output for a valid synthetic positive still yields only an inert queue candidate.
6. Caller-owned reports and existing `SourceMonitoringGuard` history remain value-for-value unchanged; no arbitrary inputs are echoed.
7. A new review/adapter version must not silently infer promotion from this projection. Demonstrate an actual authorized binding with integration tests *before* adoption; the existing tests alone cannot guarantee this.

The tests are in `implementation/tests/test_claim_support_consumer_boundary_lab.py`. The original #260 code and pre-existing files are untouched in this stacked branch.

## Independent research inputs

- Linfeng Fan et al., **The Granularity Mismatch in Agent Security: Argument-Level Provenance Solves Enforcement and Isolates the LLM Reasoning Bottleneck** (PACT, arXiv:2605.11039, 2026): trust decisions should bind origins to *specific authority-bearing arguments*, not to a whole tool response. https://arxiv.org/abs/2605.11039
- Faruk and Taylan Alpay, **AgentSecBench: Measuring Prompt Injection, Privacy Leakage, and Tool-Use Integrity in LLM Agents** (arXiv:2605.26269, 2026): separate policy enforcement from prompt/metadata annotations; preserve benign utility controls. https://arxiv.org/abs/2605.26269
- Debenedetti et al., **AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents** (NeurIPS 2024): realistic tool-agent security needs adversarial and benign tasks. https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html
- Vercel AI SDK tools/MCP documentation: `inputSchema` / `outputSchema` validate *structure*, not authentication, authority or truth. A typed tool output still requires a separate authorization check in its consumer. https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling

**Cautions:** PACT's oracle-provenance results are not evidence that Ario has independently authenticated provenance; scientific articles are motivation for test design, not certification of this code. Synthetic tests cannot prove provenance custody, semantic entailment, real deployment noninterference, or correct use by bypassing callers. This projection MUST NOT be integrated into production or cited as proof that downstream consumers are already safe. Independent exact-HEAD review remains a blocker.

**Memory != Truth; Claim != Proof; Revision != Erasure; UNKNOWN is valid.**
