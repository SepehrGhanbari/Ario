# ARIO — Four-Paper Research Intake and Evidence Review

**Date:** 2026-11-10  
**Status:** `RESEARCH_ONLY / LITERATURE_INTAKE / NOT_IMPLEMENTED / NOT_VALIDATED / NO_TRUST_ACTIVATION`  
**Project:** [SepehrGhanbari/Ario](https://github.com/SepehrGhanbari/Ario)  
**Purpose:** document the four-paper research intake and its *testable* implications, while distinguishing reported paper findings from Ario's own evidence and leaving memory, identity, security and governance contracts unchanged.

> **Research boundary.** Findings in cited papers are findings of their authors under their reported conditions. They are **not** evidence that Ario implements, matches, inherits, or has independently validated the published methods. This document creates no authorization to modify Ario's trust boundaries or governance. An existing principle is not necessarily an implemented behavior. `UNKNOWN` remains a valid outcome.

## 0. Source inventory and integrity

The original resource intake reports retaining the four user-supplied PDF byte streams **outside this GitHub repository**. The PDFs are **not included** in this branch. The listed SHA-256 values are transcribed from that earlier intake and were **not recomputed or independently verified for this GitHub publication**; they concern local file identity only, not the scientific correctness or authenticity of the papers.

| Ref | Original PDF | Source / version as printed | SHA-256 |
|---|---|---|---|
| S1 | `2605.12978v2.pdf` | Dylan Zhang et al., *Useful Memories Become Faulty When Continuously Updated by LLMs*, arXiv:2605.12978v2, 29 Aug 2026, **78 pages** | `625564a6dcf7fa672cfaca5e004e7a19caeaf43a5a02a2b66ac12cb142867770` |
| S2 | `2605.11039v1.pdf` | Linfeng Fan et al., *The Granularity Mismatch in Agent Security: Argument-Level Provenance Solves Enforcement and Isolates the LLM Reasoning Bottleneck*, arXiv:2605.11039v1, 11 May 2026, **24 pages** | `b1653aacb1786f364116517a6c3c4f254978d20578ae28ee971d0029aaf02309` |
| S3 | `2605.15343v1.pdf` | Joshua C. Yang et al., *Belief Engine: Configurable and Inspectable Stance Dynamics in Multi-Agent LLM Deliberation*, arXiv:2605.15343v1, May 2026, **21 pages** | `882e454780117d7240258ba82354cac84ac6c3f274df28b71dd6d3e11f4b6c0a` |
| S4 | `2602.20064v2.pdf` | Zac Garby, Andrew D. Gordon, David Sands, *The LLMbda Calculus: AI Agents, Conversations, and Information Flow*, arXiv:2602.20064v2, 10 Jul 2026, **63 pages** | `7214cc6201da593047f04bbf7b18e9764215952fc21567813b667cf71f37f1a2` |

Canonical discovery links: [S1](https://arxiv.org/abs/2605.12978), [S2](https://arxiv.org/abs/2605.11039), [S3](https://arxiv.org/abs/2605.15343), [S4](https://arxiv.org/abs/2602.20064). The research status/publication history beyond the uploaded version has not been independently established in this intake.

## 1. Key findings, with reproducible pointers to the PDFs

### S1 — Agent memory consolidation may be destructive

**Authors' reported result (pp. 1–3, figures 1–2):** repeated LLM-generated rewriting of condensed memory can degrade performance even when it starts from useful episodes or ground-truth solutions. In a **selected 19-problem ARC-AGI slice**, GPT-5.4 solved all chosen problems without memory; under repeated *stream* consolidation, accuracy on those same problems fell to **52.6% by round 10**, while the static consolidation control retained **94.7%** in the reported setup. This is a bounded study on chosen tasks, not an estimate of all agent-memory deployments. The paper compares episodic-only retention, consolidation schedules, and different rewrite operations.

**Important ablation (paper Table 5, around p. 12):** on the authors' ARC-AGI Stream condition at step 400, in-place rewriting scored **43.2**, append-only with previous store visible **50.0**, append-plus-delete **64.0**, append-only with prior store hidden **70.0**, and raw trajectories **76.6**. These are the study's outcome numbers; they must not be quoted as Ario test results.

**Authors' limitations and nuanced message:** raw episode retention is a safer default *in their tested settings*, not a complete long-term memory solution; unbounded raw history is costly, and useful generalization still requires controlled abstraction. Three described failure modes include incorrect grouping of experiences, dropping applicability conditions from lessons, and overfitting to near-duplicate examples.

**Ario correspondence:** reinforces the research importance of `MEMORY ≠ TRUTH`, `REVISION ≠ ERASURE`, retaining original episodes, and treating summaries as derived objects with provenance. These principles **already exist** in Ario's README/contracts; the paper does **not** establish they have been fully implemented or are performance-optimal.

**Proposed *new* experiment rather than duplicated principle:** compare memory architectures on the *same* held-out tasks with original records preserved in every experimental arm for independent auditing. Measure when derived summaries become misleading, which update operation caused the change, and what retention/cost tradeoff is incurred. See `ARIO_FOUR_PAPER_PILOT_DESIGN_2026-11-10.md`.

### S2 — Provenance should be checked at the tool-argument level

**Authors' mechanism (pp. 1–5):** PACT (`Provenance-Aware Capability Contracts`) assigns different semantic roles and trust requirements to individual tool arguments. A webpage may legitimately influence `send_email.body`, but not necessarily `send_email.recipient`. A whole-call allow/block policy cannot express this distinction. PACT tracks provenance across replanning and performs a role-specific check at the sensitive sink. Its roles include authority-bearing targets, commands and credentials, plus content and selection roles; policy precision spans L0–L3.

**Authors' measured results (abstract, evaluation and conclusion):** under idealized/oracle provenance, they report 100% utility/security in their controlled mixed-trust diagnostics. In an AgentDojo configuration with selected stronger models, reported security is 100%, with **38.1–46.4%** benign utility. Crucially, the authors also report **87.1%** automatic tool-role inference and **77.4%** provenance-inference accuracy on 20 real MCP tools: automatic inference remains a practical weak point. Broad safety benchmarks also expose out-of-scope attacks.

**Explicit limits (paper §3.1 and Appendix limitations):** structural argument binding does not solve malicious content inside an otherwise permitted `content` field, dangerous tool selection using trusted constants, or correctness of incorrectly inferred source labels. Oracle assumptions are stronger than deployment conditions.

**Ario correspondence:** a candidate independent *tool-boundary constraint* atop existing authorization and evidence firewalls; not a reason to replace the existing review-evidence gates or relax `NO_GO` around signer, key activation, native IO or other protected operations. Before any candidate implementation, require separately approved contract schemas, an explicit trusted-source model, and adversarial tests demonstrating the difference between **payload data** and **authority-bearing parameters**.

**Nontrivial candidate cases:** email: external text as body but user-specified recipient; shell tool: documentation quote cannot become executable command; GitHub: code-review comment cannot set merge target/ref/approval; file tool: retrieved PDF cannot dictate output or deletion path; browser: external page cannot silently alter the authorized domain. Track provenance through intermediate summaries and retries, not just first-hop tool outputs.

### S3 — Model stance changes should be accounted for, not mistaken for convictions

**Authors' mechanism (pp. 1–4):** Belief Engine (BE) converts dialogue statements into candidate structured arguments, separates *active* and *archived* records, applies an explicit log-odds-style update with **evidence uptake `u`** and **prior anchoring `a`**, and conditions response generation on a scalar **stance** in `[-1,1]`. The authors say 'belief' is an **operational simulation variable**, not evidence of a human-like mind or inner conviction. Their design is for experimental deliberative simulations, not proof of stable personal identity.

**Authors' evaluation:** a controlled set of generated-agent parameter sweeps and replay against **2,495 quality-filtered DEBATE trajectories**. They report **96.9% polarity accuracy** for clean single-argument inputs (their controlled diagnostic), while highlighting differing profiles for evidence-aligned movers, evidence-opposed movers and stable participants. No one globally fixed `(u,a)` reproduces all heterogeneous human trajectories.

**Limits / methodological caution:** argument extraction, judgments of evidence, prompt effects and retrieval omissions can all confound the apparent source of stance change. A numerical score should never be promoted to truth, agency, identity, authentic intention, or commitment. BE cannot by itself explain causal motivation of a real or synthetic participant if key evidence lies outside the extraction stream.

**Ario correspondence:** useful *experimental lens* for A14/A15-type multi-agent dialogue: log the exact prompt, accepted/rejected evidence and provenance, update rule, abstentions, and changes in stance. **Do not** adopt BE's scalar stance as Ario's epistemic truth or cross-IRG composite score. The multi-Ava history, requests to exit, identity questions, and rights cannot be made into a single inferred score. Any change to core identity/continuity contracts requires explicit owner approval and independent review.

### S4 — Information-flow enforcement needs a complete boundary and explicit downgrades

**Authors' formal result (pp. 1–4; implementation and conclusion §§6–9):** LLMbda is a lambda-calculus-based model of conversations, program generation, fork/clear, and dynamically labelled information flow. The Lean mechanization claims termination-insensitive probabilistic noninterference (`TIPNI`), including an insulated variant; endorsement/reclassification is an explicit construct. The formal guarantee is about a **specified calculus and trusted tool policy**, not arbitrary host environments or any unmodelled external tool API.

**Authors' experimental report:** on the AgentDojo banking test, the paper reports two attacker successes among **1,296** attacked runs; the authors attribute these to over-permissive endorsement paths. Their trusted programming language design retains a need for safe source labels and checks at all sensitive sinks.

**Key failure pattern:** even where a monitor propagates labels inside an interpreter, an untracked host-side retry loop or other outside wrapper can create an information-flow channel. A security claim is only as broad as the *full* execution boundary covered by the proof. Likewise, blanket reclassification of an untrusted value can launder it past later checks.

**Ario correspondence:** treat this as a reference for a future *review-only formal threat model* of agent wrappers, error/retry handlers and provenance declassification; it does not endow Ario with a Lean proof or authorize installing a new runtime. If a prototype is built, scope verification to explicit boundaries and document external assumptions.

## 2. What Ario already has versus what is still proposed

**Read-only repository material inspected on 2026-11-10, pinned to main commit `e6ab569fec79d192a83a121f834af23e93397674` (documentation inspection only; not a runtime verification):** [`AGENTS.md`](https://github.com/SepehrGhanbari/Ario/blob/e6ab569fec79d192a83a121f834af23e93397674/AGENTS.md), [`principles/README.md`](https://github.com/SepehrGhanbari/Ario/blob/e6ab569fec79d192a83a121f834af23e93397674/principles/README.md), [`implementation/README.md`](https://github.com/SepehrGhanbari/Ario/blob/e6ab569fec79d192a83a121f834af23e93397674/implementation/README.md), and [`architecture/CROSS-IRG_INTEGRITY_V1.md`](https://github.com/SepehrGhanbari/Ario/blob/e6ab569fec79d192a83a121f834af23e93397674/architecture/CROSS-IRG_INTEGRITY_V1.md).

**Observed in those documents:** stored representations are not automatically true; memory/claim/evidence/status must remain distinct; original records should not be silently rewritten; independent evidence counts are not equivalent to record counts; composition does not automatically imply stronger truth/identity status; review and governance controls require authorization. One architectural contract is explicitly historical and marked **NOT IMPLEMENTED**, and must not be retroactively upgraded by citing newer experiments.

**Not verified as part of this intake:** current end-to-end runtime coverage, security of all wrapper/retry paths, automatic provenance inference accuracy in Ario, empirical memory consolidation performance, causal explanations of A14/A15 model responses, or correctness of any unreviewed PR. No production execution or trust activation occurred.

## 3. Integration candidates ordered by safety and research utility

| Priority | Candidate | Status in this intake | Why | Gate before implementation |
|---|---|---|---|---|
| P1 | Preserve raw episodes; treat summaries as versioned derived artifacts with source links | `RESEARCH_PROPOSAL` | direct test of S1 and Ario memory principles | reproducible, bounded test dataset; benchmark vs raw and rewrite baselines; cost measurements |
| P1 | Per-argument provenance/authority contracts for tool calls | `SECURITY_RESEARCH_ONLY` | S2: defend mixed-trust workflows without blocking all data | authorized scope; role dictionary; conservative trust labels; no signer/IO changes; red-team negative cases |
| P2 | Stance-change evidence ledger for synthetic dialogues | `RESEARCH_PROPOSAL` | S3: distinguish evidence uptake, anchoring and context shifts | consent/privacy boundaries; no identity inference; prompt exactness; multiple baselines |
| P2 | Explicit audit of label propagation, retries and endorsement | `FORMAL_RESEARCH_ONLY` | S4: find gaps outside monitors | trusted computing boundary; proof obligations; sandbox only; no implicit trust escalation |

**Do not silently adopt:** direct code from the papers (licensing not checked), model weights/dependencies, large new runtime frameworks, automatic trust promotion, fixed persona/identity scores, permanent signing keys, external-network execution, or changes to core governance.

## 4. Concrete questions for a future external peer review

1. S1 memory authors: How to select consolidation triggers and evaluate the tradeoff between episode fidelity, transfer, retrieval overhead and context budget under a preregistered test split?
2. S2 PACT authors: How to ground semantic argument roles and multi-hop provenance when a tool's schema is ambiguous and intermediate outputs are generated by LLMs?
3. S3 BE authors: How to avoid confusing a policy-imposed stance trajectory with actual evidence-responsive revision when extractor errors, role drift and selection of active evidence are possible?
4. S4 LLMbda authors: How can a formal guarantee be composed with host retry loops, external IO adapters and human approval transitions without assuming the very boundary one wishes to validate?

## 5. Scientific claims and publication discipline

- Existing Ario tests, if any, remain bounded local synthetic experiments. Citing four other studies does not independently replicate their methods, validate Ario's code, or establish useful scientific novelty.
- The PACT/Lambda calculus authors report their own performance/proofs, not ours. Reuse only with attribution and correct license review.
- Respect `UNKNOWN`; record failure and false positives as first-class results. Missing external observations or source metadata may justify abstention.
- Neither a conversation trace nor a numerical stance score proves selfhood, consciousness, continuity or transferred obligations.
- Future manuscripts must cite the authors directly and distinguish conceptual extension, implemented mechanism, and tested result. The earlier resources-only intake did not submit a scientific article; this branch proposes two research notes, not a tested implementation or scientific-paper submission.

## 6. Preservation manifest

The original resources-only intake retained **four source PDFs and two research-only notes** in separate research resources. This documentation-only GitHub proposal includes the **two Markdown notes, not the PDFs**. The uploaded originals remain preserved separately; this edition only clarifies the publication context. The branch changes no existing historical archive, `main`, implementation code, governance, keys, workflows, or trust state. Future updates should be new dated notes or explicitly versioned derivatives, not silent rewriting of source papers or prior decisions.

**Next artifact:** [`ARIO_FOUR_PAPER_PILOT_DESIGN_2026-11-10.md`](ARIO_FOUR_PAPER_PILOT_DESIGN_2026-11-10.md).
