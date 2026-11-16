# Independent critical research protocol for Ario W1: evaluating hidden witness/so

**Question:** Independent critical research protocol for Ario W1: evaluating hidden witness/source/controller dependence, deliberately incomplete provenance graphs, and false completeness attestations. This is the user's separate, time-limited Consensus Pro research sprint. Please use Pro research depth, not Deep, and prioritize full-text primary literature over vendor or AI-generated secondary summaries. Scope and prior materials: Ario's public TB-003 is a synthetic provenance graph evaluator which returns only LAB_CONDITIONALLY_SEPARATE, LAB_CONDITIONALLY_DISTINCT, COMMON_CONTROL_DETECTED, COMMON_SOURCE_DETECTED or UNKNOWN on the graph supplied. Its completeness is asserted by laboratory booleans; signatures/hashes are NOT evidence that all real links were recorded. A developer-authored W1 rehearsal generated eight logical families times ten label permutations, 80 outputs; 30 latent-world disagreements came from 3 families with intentionally concealed shared roots/sources; this is NOT independent validation or an existing code bug. Related research includes Dong et al. 2009 DOI 10.14778/1687627.1687690 (source copying), Douceur 2002 DOI 10.1007/3-540-45748-8_24 (Sybil), Bauer et al. 2011 DOI 10.1145/2000799.2000800 (three-valued inconclusive); compare forward-integrity logs and verified provenance completeness. Please (1) examine prior academic approaches to dependence/collusion/source copying, unknown-world links/open-world assumptions, validity of evaluator claims, independent witness attestation and threat models; distinguish source-dependence inference from authenticated controller independence; (2) develop a rigorous prospective blinded study where *independent* case authors, two independent labelers, sealed masked inputs, and verifiable run-before-unseal workflow keep holdout labels inaccessible to implementation authors; clarify that cryptographic hashes alone cannot prove independent authorship or chronology; (3) independently criticize whether 80 variants of only 8 templates can demonstrate anything beyond conditional consistency; (4) give 12 novel HIGH-LEVEL adversarial scenario FAMILY descriptions, without solutions or gold labels, which differ from the already used eight families and are suitable for future external authors to create, including admin graph incompleteness, SOURCE alias/transitive ancestry, root compromise, custody timing, invalid completeness and provenance laundering; (5) specify explicit falsifiers and primary endpoints with denominator, abstention, false affirmative, signed/unsigned provenance control and oracle uncertainty; (6) recommend matched baseline comparisons including naive record count and conservative UNKNOWN, ensure existing TB-003 vs PR #199 H_E/H_S custody semantics are not conflated, (7) cite peer-reviewed original papers with DOI/full-text evidence and clearly distinguish preprints, analogies and unsupported claims. Do not fabricate citations, do not assert real deployment security or independent blinded outcomes, and do not output any private fixture labels/answers. Answer with a structured research protocol and references for archiving under research/consensus.

# Provenance Evaluation Under **Incomplete Graphs** and Collusion

Evaluating provenance graph evaluators requires distinguishing **internal graph consistency** from physical or latent-world completeness, as cryptographic signatures alone cannot prove independent authorship or chronological honesty [[1.1]](https://consensus.app/papers/condrey-witnessd-proofofprocess-via-adversarial-collapse/w:3a952f68-fa8e-49b6-bf2f-85ba9b70d6c8/) [[1.2]](https://consensus.app/papers/condrey-witnessd-proofofprocess-via-adversarial-collapse/w:3a952f68-fa8e-49b6-bf2f-85ba9b70d6c8/). Below is a structured critical research protocol addressing source dependence, blinded execution, structural expressiveness limits, and adversarial challenge families.

| Feature | Result / Value |
| :--- | :--- |
| **Study Design** | Prospective double-blinded challenge-response evaluation [[2.1]](https://consensus.app/papers/zhou-yu-auditable-aiassisted-research-writing-an/w:0ab2299f-0682-4933-97c7-73501ce6470f/) [[3.1]](https://consensus.app/papers/bultel-fraser-blindreview-anonymous-and-endtoend-verifiable-peer/w:7c182c01-c3af-496c-9f90-6a68dc78080a/) |
| **Evaluator Target** | Synthetic provenance evaluator (Ario TB-003 / PR #199 semantics) [[2.2]](https://consensus.app/papers/zhou-yu-auditable-aiassisted-research-writing-an/w:0ab2299f-0682-4933-97c7-73501ce6470f/) [[4.1]](https://consensus.app/papers/chan-cheney-provmark/w:f45f892d-4796-4ff9-882c-773f0f89a322/) |
| **Intervention** | Injection of unobserved latent-world dependencies and omitted edges [[5.1]](https://consensus.app/papers/raja-grading-the-narrators-an-isnadrijal-framework-for/w:7c8e2d50-b4a8-4145-9c13-ef7c36d69ccb/) [[6.1]](https://consensus.app/papers/pan-stakhanova-data-provenance-in-security-and-privacy/w:46d02003-58f2-4958-a466-a8f6214514ff/) |
| **Controls** | Matched baselines: naive record count, conservative UNKNOWN, full TEE/ledger logs [[7.1]](https://consensus.app/papers/ardebili-novafabric-tamperevident-replayable-evidence-for/w:18a89511-1cc2-42c6-b6ef-b403bd0e9648/) [[8.1]](https://consensus.app/papers/hung-dung-a-blockchainbased-chain-of-custody-for-digital/w:756a4330-f915-45f5-b0d4-73e77f19e918/) |
| **Primary Endpoints** | False Affirmative Rate (FAR), Abstention Rate (AR), Coverage Under Incompleteness [[7.2]](https://consensus.app/papers/ardebili-novafabric-tamperevident-replayable-evidence-for/w:18a89511-1cc2-42c6-b6ef-b403bd0e9648/) [[5.2]](https://consensus.app/papers/raja-grading-the-narrators-an-isnadrijal-framework-for/w:7c8e2d50-b4a8-4145-9c13-ef7c36d69ccb/) |
| **Key Limitation** | Observer-operator conflation without external holdouts [[2.3]](https://consensus.app/papers/zhou-yu-auditable-aiassisted-research-writing-an/w:0ab2299f-0682-4933-97c7-73501ce6470f/) [[2.4]](https://consensus.app/papers/zhou-yu-auditable-aiassisted-research-writing-an/w:0ab2299f-0682-4933-97c7-73501ce6470f/) |

**Figure 1:** Core structural parameters of the independent prospective evaluation protocol.

## Theoretical Foundations and Threat Models

Prior literature demonstrates that provenance graphs relying strictly on internal assertions operate under an **open-world vulnerability** where unrecorded causal links cannot be ruled out by cryptographic hashes [[9.1]](https://consensus.app/papers/moreau-batlajery-a-templating-system-to-generate-provenance/w:b378ec38-86af-48c8-bda2-a271698e75be/) [[10.1]](https://consensus.app/papers/cheney-chong-provenance/w:d5df45aa-ea1c-4110-9edb-f88e246a5f67/). Digital signatures and hash chains certify key possession and local tamper detection, but they fail to prove actual composition process or prevent post-hoc construction [[1.1]](https://consensus.app/papers/condrey-witnessd-proofofprocess-via-adversarial-collapse/w:3a952f68-fa8e-49b6-bf2f-85ba9b70d6c8/) [[1.3]](https://consensus.app/papers/condrey-witnessd-proofofprocess-via-adversarial-collapse/w:3a952f68-fa8e-49b6-bf2f-85ba9b70d6c8/) [[11.1]](https://consensus.app/papers/kao-constantsize-cryptographic-evidence-structures-for/w:ec600df6-9daf-4911-94b3-5b935626b2dc/). Colluding malicious actors can shuffle or omit records without violating cryptographic signatures unless multi-party aggregation or third-party witnesses enforce transitive verification [[6.1]](https://consensus.app/papers/pan-stakhanova-data-provenance-in-security-and-privacy/w:46d02003-58f2-4958-a466-a8f6214514ff/) [[6.2]](https://consensus.app/papers/pan-stakhanova-data-provenance-in-security-and-privacy/w:46d02003-58f2-4958-a466-a8f6214514ff/) [[8.2]](https://consensus.app/papers/hung-dung-a-blockchainbased-chain-of-custody-for-digital/w:756a4330-f915-45f5-b0d4-73e77f19e918/). 

Furthermore, **source-dependence inference** must be strictly decoupled from authenticated controller independence [[5.3]](https://consensus.app/papers/raja-grading-the-narrators-an-isnadrijal-framework-for/w:7c8e2d50-b4a8-4145-9c13-ef7c36d69ccb/) [[1.4]](https://consensus.app/papers/condrey-witnessd-proofofprocess-via-adversarial-collapse/w:3a952f68-fa8e-49b6-bf2f-85ba9b70d6c8/). In multi-agent and distributed environments, apparent corroboration across separate chains collapses when underlying agents share training, prompts, or latent control hierarchies [[5.4]](https://consensus.app/papers/raja-grading-the-narrators-an-isnadrijal-framework-for/w:7c8e2d50-b4a8-4145-9c13-ef7c36d69ccb/) [[5.5]](https://consensus.app/papers/raja-grading-the-narrators-an-isnadrijal-framework-for/w:7c8e2d50-b4a8-4145-9c13-ef7c36d69ccb/). Cross-layer contradictions frequently emerge where valid cryptographic manifests coexist alongside incompatible metadata or hidden data washings [[12.1]](https://consensus.app/papers/nemecek-he-authenticated-contradictions-from-desynchronized/w:9769eb4a-0ccd-40dc-b6ec-80f84a9bdc29/) [[12.2]](https://consensus.app/papers/nemecek-he-authenticated-contradictions-from-desynchronized/w:9769eb4a-0ccd-40dc-b6ec-80f84a9bdc29/). Evaluators cannot infer controller separation from isolated topological distinctness without verified hardware isolation or non-colluding witnesses [[1.5]](https://consensus.app/papers/condrey-witnessd-proofofprocess-via-adversarial-collapse/w:3a952f68-fa8e-49b6-bf2f-85ba9b70d6c8/) [[13.1]](https://consensus.app/papers/condrey-a-teebased-architecture-for-confidential-and/w:7c9ff912-460f-4cfe-bfd3-36a219553f20/).

## Prospective Blinded Study Design

Evaluating an evaluator requires resolving the structural observer-operator conflict identified in methodological audits [[2.3]](https://consensus.app/papers/zhou-yu-auditable-aiassisted-research-writing-an/w:0ab2299f-0682-4933-97c7-73501ce6470f/) [[2.4]](https://consensus.app/papers/zhou-yu-auditable-aiassisted-research-writing-an/w:0ab2299f-0682-4933-97c7-73501ce6470f/):

- **Pre-registered execution firewalls:** Protocols, metrics, and stopping rules must be frozen and pinned before trial execution begins [[2.5]](https://consensus.app/papers/zhou-yu-auditable-aiassisted-research-writing-an/w:0ab2299f-0682-4933-97c7-73501ce6470f/) [[5.6]](https://consensus.app/papers/raja-grading-the-narrators-an-isnadrijal-framework-for/w:7c8e2d50-b4a8-4145-9c13-ef7c36d69ccb/) [[14.1]](https://consensus.app/papers/brandes-evidence-records-for-publicrecord-changes/w:07145343-462a-4b78-9d8b-796749bb8607/).
- **Blinded case isolation:** Independent case authors generate test fixtures behind strict import firewalls that evaluation engines cannot inspect [[2.6]](https://consensus.app/papers/zhou-yu-auditable-aiassisted-research-writing-an/w:0ab2299f-0682-4933-97c7-73501ce6470f/) [[5.1]](https://consensus.app/papers/raja-grading-the-narrators-an-isnadrijal-framework-for/w:7c8e2d50-b4a8-4145-9c13-ef7c36d69ccb/).
- **Dual-labeler holdout verification:** Two independent labelers classify ground-truth graphs under sealed conditions prior to unsealing [[2.1]](https://consensus.app/papers/zhou-yu-auditable-aiassisted-research-writing-an/w:0ab2299f-0682-4933-97c7-73501ce6470f/) [[3.1]](https://consensus.app/papers/bultel-fraser-blindreview-anonymous-and-endtoend-verifiable-peer/w:7c182c01-c3af-496c-9f90-6a68dc78080a/).
- **Deterministic replay pipelines:** Verifiers rebuild data inventories and recompute metrics mechanically in clean environments to ensure reproducibility [[2.7]](https://consensus.app/papers/zhou-yu-auditable-aiassisted-research-writing-an/w:0ab2299f-0682-4933-97c7-73501ce6470f/) [[15.1]](https://consensus.app/papers/abramyan-ala’anzy-compprov-produces-machine-readable-graphs-encoding/w:e691a3b7-98d7-42a1-bddf-c36a8b5c06c3/).

Generating eighty variants across eight logical templates merely tests **syntactic expander consistency** rather than empirical validity [[9.2]](https://consensus.app/papers/moreau-batlajery-a-templating-system-to-generate-provenance/w:b378ec38-86af-48c8-bda2-a271698e75be/) [[16.1]](https://consensus.app/papers/moreau-batlajery-provtemplate-evaluation-dataset/w:fbe8995b-c0a2-4d5d-850e-3b747a4a376a/). In template-driven provenance generation, binding variables to fixed graph topologies produces predictable serializations in fractions of milliseconds, but it does not expand topological coverage or capture unforeseen causal structures [[9.3]](https://consensus.app/papers/moreau-batlajery-a-templating-system-to-generate-provenance/w:b378ec38-86af-48c8-bda2-a271698e75be/) [[16.2]](https://consensus.app/papers/moreau-batlajery-provtemplate-evaluation-dataset/w:fbe8995b-c0a2-4d5d-850e-3b747a4a376a/). A suite of 80 template expansions demonstrates internal generator determinism, but remains vulnerable to identical systemic blind spots [[2.8]](https://consensus.app/papers/zhou-yu-auditable-aiassisted-research-writing-an/w:0ab2299f-0682-4933-97c7-73501ce6470f/) [[17.1]](https://consensus.app/papers/li-zhang-provgrp-a-contextaware-provenance-graph-reduction/w:5c3dfb07-b769-42b3-8a64-75fabffba7bb/).

## Twelve Novel Adversarial Scenario Families

To assess resilience against latent dependence without exposing private benchmark fixtures, future independent benchmark authors should construct twelve non-overlapping test families:

- **Administrative Graph Pruning:** An operator intentionally omits administrative process events from audit streams to hide causal linkage [[18.1]](https://consensus.app/papers/liu-inam-how-to-effectively-trace-provenance-on-windows/w:fa3e2215-9e26-48ce-afc5-2c12e6210d8f/) [[18.2]](https://consensus.app/papers/liu-inam-how-to-effectively-trace-provenance-on-windows/w:fa3e2215-9e26-48ce-afc5-2c12e6210d8f/).
- **Transitive Source Aliasing:** Identical source material is routed through multiple intermediary proxy identities to evade copying heuristics [[5.3]](https://consensus.app/papers/raja-grading-the-narrators-an-isnadrijal-framework-for/w:7c8e2d50-b4a8-4145-9c13-ef7c36d69ccb/) [[5.5]](https://consensus.app/papers/raja-grading-the-narrators-an-isnadrijal-framework-for/w:7c8e2d50-b4a8-4145-9c13-ef7c36d69ccb/).
- **Root Key Compromise with Forward Consistency:** An adversary utilizes an exfiltrated signing key while preserving strict sequential hashes [[1.1]](https://consensus.app/papers/condrey-witnessd-proofofprocess-via-adversarial-collapse/w:3a952f68-fa8e-49b6-bf2f-85ba9b70d6c8/) [[11.1]](https://consensus.app/papers/kao-constantsize-cryptographic-evidence-structures-for/w:ec600df6-9daf-4911-94b3-5b935626b2dc/).
- **Temporal Custody Desynchronization:** Timestamps are manipulated within allowable clock skew to disguise true execution order [[18.3]](https://consensus.app/papers/liu-inam-how-to-effectively-trace-provenance-on-windows/w:fa3e2215-9e26-48ce-afc5-2c12e6210d8f/) [[13.2]](https://consensus.app/papers/condrey-a-teebased-architecture-for-confidential-and/w:7c9ff912-460f-4cfe-bfd3-36a219553f20/).
- **False Completeness Attestation:** An attester signs an explicit boolean completeness flag while deliberately suppressing internal telemetry edges [[7.2]](https://consensus.app/papers/ardebili-novafabric-tamperevident-replayable-evidence-for/w:18a89511-1cc2-42c6-b6ef-b403bd0e9648/) [[12.3]](https://consensus.app/papers/nemecek-he-authenticated-contradictions-from-desynchronized/w:9769eb4a-0ccd-40dc-b6ec-80f84a9bdc29/).
- **Cross-Layer Provenance Laundering:** Artifacts are stripped of upstream provenance manifests and re-injected under clean downstream signatures [[12.4]](https://consensus.app/papers/nemecek-he-authenticated-contradictions-from-desynchronized/w:9769eb4a-0ccd-40dc-b6ec-80f84a9bdc29/) [[12.5]](https://consensus.app/papers/nemecek-he-authenticated-contradictions-from-desynchronized/w:9769eb4a-0ccd-40dc-b6ec-80f84a9bdc29/).
- **Collusive Split-Graph Merging:** Multiple colluding entities fragment a single execution graph into disconnected subgraphs that pass separation tests [[6.1]](https://consensus.app/papers/pan-stakhanova-data-provenance-in-security-and-privacy/w:46d02003-58f2-4958-a466-a8f6214514ff/) [[6.2]](https://consensus.app/papers/pan-stakhanova-data-provenance-in-security-and-privacy/w:46d02003-58f2-4958-a466-a8f6214514ff/).
- **Process Injection via Long-Running Daemons:** Attacks execute within benign persistent services to generate misleading dependency explosion and obfuscate root cause [[18.4]](https://consensus.app/papers/liu-inam-how-to-effectively-trace-provenance-on-windows/w:fa3e2215-9e26-48ce-afc5-2c12e6210d8f/) [[17.2]](https://consensus.app/papers/li-zhang-provgrp-a-contextaware-provenance-graph-reduction/w:5c3dfb07-b769-42b3-8a64-75fabffba7bb/).
- **Sybil Witness Inflation:** A single controller provisions multiple apparent witness entities that mutually cross-sign incomplete graphs [[1.4]](https://consensus.app/papers/condrey-witnessd-proofofprocess-via-adversarial-collapse/w:3a952f68-fa8e-49b6-bf2f-85ba9b70d6c8/) [[6.3]](https://consensus.app/papers/pan-stakhanova-data-provenance-in-security-and-privacy/w:46d02003-58f2-4958-a466-a8f6214514ff/).
- **Decoupled Content Substitution:** Cryptographic envelope hashes match historical runs while the actual underlying payload is swapped [[7.3]](https://consensus.app/papers/ardebili-novafabric-tamperevident-replayable-evidence-for/w:18a89511-1cc2-42c6-b6ef-b403bd0e9648/) [[15.2]](https://consensus.app/papers/abramyan-ala’anzy-compprov-produces-machine-readable-graphs-encoding/w:e691a3b7-98d7-42a1-bddf-c36a8b5c06c3/).
- **Algebraic Intermediate Suppression:** Complex computational derivations omit intermediary state transformations to conceal tainted arithmetic paths [[15.2]](https://consensus.app/papers/abramyan-ala’anzy-compprov-produces-machine-readable-graphs-encoding/w:e691a3b7-98d7-42a1-bddf-c36a8b5c06c3/) [[15.3]](https://consensus.app/papers/abramyan-ala’anzy-compprov-produces-machine-readable-graphs-encoding/w:e691a3b7-98d7-42a1-bddf-c36a8b5c06c3/).
- **Attestation Rollback under Partition:** An adversary selectively drops late-arriving revocation receipts during network partitioning events [[13.3]](https://consensus.app/papers/condrey-a-teebased-architecture-for-confidential-and/w:7c9ff912-460f-4cfe-bfd3-36a219553f20/) [[13.4]](https://consensus.app/papers/condrey-a-teebased-architecture-for-confidential-and/w:7c9ff912-460f-4cfe-bfd3-36a219553f20/).

## Protocol Endpoints and Baselines

Primary endpoints must evaluate classification performance under missing information flows [[5.2]](https://consensus.app/papers/raja-grading-the-narrators-an-isnadrijal-framework-for/w:7c8e2d50-b4a8-4145-9c13-ef7c36d69ccb/) [[18.5]](https://consensus.app/papers/liu-inam-how-to-effectively-trace-provenance-on-windows/w:fa3e2215-9e26-48ce-afc5-2c12e6210d8f/). The **False Affirmative Rate (FAR)** measures instances where the evaluator returns separation or distinctness despite latent controller or source linkage, evaluated over the total pool of concealed-dependency fixtures [[5.7]](https://consensus.app/papers/raja-grading-the-narrators-an-isnadrijal-framework-for/w:7c8e2d50-b4a8-4145-9c13-ef7c36d69ccb/) [[18.6]](https://consensus.app/papers/liu-inam-how-to-effectively-trace-provenance-on-windows/w:fa3e2215-9e26-48ce-afc5-2c12e6210d8f/). The **Abstention Rate (AR)** tracks appropriate assignments of `UNKNOWN` when incoming graphs lack verified completeness proofs [[7.4]](https://consensus.app/papers/ardebili-novafabric-tamperevident-replayable-evidence-for/w:18a89511-1cc2-42c6-b6ef-b403bd0e9648/) [[19.1]](https://consensus.app/papers/song-qihang-vcause-efficient-and-verifiable-causality-analysis/w:b8bc7fa8-4c53-4633-8a98-8eb5b2c5a476/). Evaluator metrics must be benchmarked against a naive record-count baseline and a conservative three-valued baseline that abstains whenever unverified boundaries exist [[7.5]](https://consensus.app/papers/ardebili-novafabric-tamperevident-replayable-evidence-for/w:18a89511-1cc2-42c6-b6ef-b403bd0e9648/) [[14.2]](https://consensus.app/papers/brandes-evidence-records-for-publicrecord-changes/w:07145343-462a-4b78-9d8b-796749bb8607/). 

Protocols must also enforce strict semantic separation between legacy graph-topology evaluations and chain-of-custody models incorporating cryptographic hardware roots, permissioned multi-party logs, or verifiable execution capsules [[7.6]](https://consensus.app/papers/ardebili-novafabric-tamperevident-replayable-evidence-for/w:18a89511-1cc2-42c6-b6ef-b403bd0e9648/) [[13.5]](https://consensus.app/papers/condrey-a-teebased-architecture-for-confidential-and/w:7c9ff912-460f-4cfe-bfd3-36a219553f20/) [[8.3]](https://consensus.app/papers/hung-dung-a-blockchainbased-chain-of-custody-for-digital/w:756a4330-f915-45f5-b0d4-73e77f19e918/) [[19.2]](https://consensus.app/papers/song-qihang-vcause-efficient-and-verifiable-causality-analysis/w:b8bc7fa8-4c53-4633-8a98-8eb5b2c5a476/). Confused semantics between pure topological syntax and true environmental execution tracking undermine objective verification [[17.3]](https://consensus.app/papers/li-zhang-provgrp-a-contextaware-provenance-graph-reduction/w:5c3dfb07-b769-42b3-8a64-75fabffba7bb/) [[14.3]](https://consensus.app/papers/brandes-evidence-records-for-publicrecord-changes/w:07145343-462a-4b78-9d8b-796749bb8607/).
 
_These search results were found and analyzed using Consensus, an AI-powered search engine for research. Try it at https://consensus.app. © 2026 Consensus NLP, Inc. Personal, non-commercial use only; redistribution requires copyright holders’ consent._
 
## References
 
`1.` Condrey D. Witnessd: Proof-of-process via Adversarial Collapse. *arXiv (Cornell University).* 2026;abs/2602.01663. doi:10.48550/arxiv.2602.01663
 
> [1.1] Digital signatures prove key possession, not that the signer created the content. (Introduction)
 
> [1.2] Digital signatures prove key possession, not authorship. (Abstract)
 
> [1.3] An author who generates text with AI, constructs intermediate document states post-hoc, and signs each hash produces a signature chain indistinguishable from genuine composition. (Abstract)
 
> [1.4] Two components 𝐴 and 𝐵 have independent trust assumptions if: - (1) No single party controls both verification paths - (2) No shared secret enables compromise of both - (3) No common vulnerability affects both - (4) Compromise of 𝐴 does not enable compromise of 𝐵 Where independence holds: Local hash chain integrity (verified by recomputation) is independent of Bitcoin anchor validity (verified against public blockchain). (Body)
 
> [1.5] Each component provides an independent verification checkpoint; disputing authentic evidence requires alleging coordinated compromise across multiple trust boundaries. (Introduction)
 
`2.` Zhou Y, Yu C. Auditable AI-Assisted Research Writing: An Engineering Discipline with Pre-Registered Process Observation. *arXiv (Cornell University).* 2026;abs/2608.10858. doi:10.48550/arxiv.2608.10858
 
> [2.1] We build the record as work happens: version-control sealing, hash-bound provenance, refusal-logging gates, cross-model role separation, and scripted assembly from registered sources, under a protocol frozen before the prospective case it observes; a retrospective case is reported apart, at lower standing. (Conclusion)
 
> [2.2] We claim nothing about whether this improves the research it governs, only what the mechanisms recorded. (Conclusion)
 
> [2.3] We state the gravest limitation first: the observer and the observed are the same team. (Body)
 
> [2.4] In a single-team project the orchestrating role necessarily holds both operator and adjudicator standing, a residual conflict the protocol registers as structural and irreducible rather than isolated. (Body)
 
> [2.5] In the prospective case the observed project's pre-registered test returned No-Go, and that project's frozen stopping rule, not ours, halted the work, against its own operators. (Conclusion)
 
> [2.6] The frozen role table separates operator, observer and adjudicator and bars the observer from writing to an observed repository; collection is read-only and hashes upstream files before and after every snapshot, voiding any taken across a change; script hashes are fixed before the first confirmatory event, so retuning one after a result is seen requires a substantive amendment and dual-caliber reporting; blinded audit seeds are generated by someone who does not run collection. (Body)
 
> [2.7] Its verifier rebuilds that inventory independently and compares as a set, so omitting one item fails rather than passes; the scripts admit no third-party dependency. (Body)
 
> [2.8] Adherence is instrumented by metric cards, each carrying a pre-registered blind spot and evidential standing, frozen before the prospective case it observes. (Abstract)
 
`3.` Bultel X, Fraser A, Quaglia EA. BlindReview: Anonymous and End-to-End Verifiable Peer Review. *IEEE Computer Security Foundations Workshop (CSFW).* 2026. doi:10.1109/csf68417.2026.00028
 
> [3.1] We introduce BlindReview, an anonymous and end-to-end verifiable peer review system that cryptographically guarantees both privacy and auditability throughout the reviewing process. (Abstract)
 
`4.` Chan SC, Cheney J, Bhatotia P, et al. ProvMark. *International Middleware Conference.* 2019. doi:10.1145/3361525.3361552
 
> [4.1] We present an automated tool, ProvMark, that uses an existing provenance system as a black box and reliably identifies the provenance graph structure recorded for a given activity, by a reduction to subgraph isomorphism problems handled by an external solver. (Abstract)
 
`5.` Raja AZ. Grading the Narrators: An Isnad-Rijal Framework for Claim-Level Provenance in Multi-Agent Knowledge Systems. *arXiv (Cornell University).* 2026;abs/2607.24117. doi:10.48550/arxiv.2607.24117
 
> [5.1] What is independently verifiable is the leakage firewall: the injection manifest lives in a dedicated module that an enforced test forbids any grading, gating, or routing code from importing. (Methods)
 
> [5.2] Two results are reported as inconclusive rather than positive: a matched-coverage comparison against the baseline could not be completed, because the framework could not be driven above 4.8% coverage with the reference content critic; and the confidence-gated baseline is uninformative by construction and therefore supports no claim about real model self-confidence. (Abstract)
 
> [5.3] | Source registry | Truth discovery (Yin et al., 2008; Dong et al., 2014) - source relia- bility estimation | Per-domain grading; version-bump resets; quarantine lifecycle | | Content criticism | FEVER-style fact-checking | Decoupled from chain quality; operates on matn independently; explicit unverifiable verdict | | Agent grading | MAS reputation (EigenTrust, Re- GreT, FIRE) | Claim-level provenance, not just partner se- lection | | Decision routing | - (no direct ancestor) | Chain grade × content verdict → concrete serve/review/quarantine action | Table 4: Capability coverage across approaches, under the narrow column definitions given above. (Body)
 
> [5.4] Independent-chain corroboration fires across three corpora of increasing difficulty, with negative controls on the Wikipedia corpus. (Abstract)
 
> [5.5] Over centuries it developed a rigorous methodology - isnad (a complete transmission chain attached to every claim), rijal (systematic grading of each narrator's integrity and precision), weakest-link chain evaluation, corroboration through independent chains, and matn criticism (content evaluated independently of chain quality). (Abstract)
 
> [5.6] The analysis protocol - hypotheses, metrics, conditions, and decision rule - was written before the experiment was run and is preserved verbatim in the repository as ANALYSIS\_PLAN.md , together with a dated log of deviations made during execution. (Methods)
 
> [5.7] Weakest-link grading correctly quarantined every claim whose chain contained a rejected narrator, with each quarantine traceable to the grade that caused it. (Abstract)
 
`6.` Pan B, Stakhanova N, Ray S. Data Provenance in Security and Privacy. *ACM Computing Surveys.* 2023;55:1-35. doi:10.1145/3593294
 
> [6.1] The majority of the solutions that are based on the idea of the provenance chain implicitly assume transitive trust and therefore are not able to handle multiple malicious users that may e.g., shuffle provenance records without being detected. (Body)
 
> [6.2] [5, 6] extended the aggregated signatures introduced in their initial study [7] to prevent tampering with provenance records by multiple consecutive and non-consecutive users. (Body)
 
> [6.3] The issue of colluding malicious users was addressed in a series of studies by Ahmed et al. (Body)
 
`7.` Ardebili MS. NovaFabric: Tamper-Evident, Replayable Evidence for Autonomous AI Agent Runs. *arXiv (Cornell University).* 2026. doi:10.48550/arxiv.2609.12582
 
> [7.1] We present NovaFabric, producing audit-grade execution evidence: provider-neutral, tamper-evident, replayable, shareable. (Abstract)
 
> [7.2] Declared-stream completeness is 0.652 (95% CI +/-0.064, ten scenarios). (Abstract)
 
> [7.3] Mocked replay serves every model response from the capsule (no live model call, 10/10) but is offline w.r.t. models, not the network; only 2/10 tool-using workloads completed; the gap is missing tool-response substitution. (Abstract)
 
> [7.4] Sealed runs are re-executable under a four-mode replay protocol and exportable as an Evidence Bundle for third-party verification with stock tooling (specified, not evaluated). (Abstract)
 
> [7.5] Blast-radius queries: 45.5ms p99 over 10M edges (3.3x faster than a columnar baseline), 167.9ms over 100M (1 client, n=30). (Abstract)
 
> [7.6] It records an agent run, without modifying agent logic, into a portable Run Capsule (fifteen-entity schema), sealed with a holistic DSSE signature, RFC 3161 timestamp, Merkle log and redaction attestation. (Abstract)
 
`8.` Hung TX, Dung LT, Tu TA. A Blockchain-Based Chain of Custody for Digital Evidence: Design and Evaluation. *Journal of Science and Technology on Information security.* 2025. doi:10.54654/isj.v3i26.1167
 
> [8.1] We therefore record custody metadataevent types, actors, timestamps, policies, and content digests-on a permissioned blockchain, while keeping bulky or sensitive artefacts in secure off-chain repositories. (Body)
 
> [8.2] Because the ledger is replicated across agencies that do not fully trust one another, unilateral edits or attempts to rewrite history become detectable. (Body)
 
> [8.3] Smart contracts encode custody workflows and authorization rules so that sensitive transitions (e.g., sealing, transfer, disclosure) require multi-party endorsement. (Body)
 
`9.` Moreau L, Batlajery BV, Huynh TD, Michaelides DT, Packer HS. A Templating System to Generate Provenance. *IEEE Transactions on Software Engineering.* 2017;44:103-121. doi:10.1109/tse.2017.2659745
 
> [9.1] To avoid code instrumentation, YesWorkflow assumes that critical information has been encoded in data product files and directory names, which allows full provenance to be inferred. (Body)
 
> [9.2] Designers specify the topology of the provenance to be generated by composing templates, which are provenance graphs containing variables, acting as placeholders for values. (Abstract)
 
> [9.3] An expansion algorithm generates instantiated provenance from templates and sets of bindings in any of the serialisation formats supported by prov. (Abstract)
 
`10.` Cheney J, Chong S, Foster N, Seltzer M, Vansummeren S. Provenance. *Companion to the ACM SIGPLAN Conference on Object-Oriented Programming, Systems, Languages, and Applications (OOPSLA Companion).* 2009. doi:10.1145/1639950.1640064
 
> [10.1] In this paper, we outline the current state of provenance research and practice, identify hard open research problems involving provenance semantics, formal modeling, and security, and articulate a vision for the future of provenance. (Abstract)
 
`11.` Kao L. Constant-Size Cryptographic Evidence Structures for Regulated AI Workflows. *arXiv (Cornell University).* 2025;abs/2511.17118. doi:10.48550/arxiv.2511.17118
 
> [11.1] We formalize a model of regulated AI workflows, define syntax and algorithms for evidence structures, and prove security properties (evidence binding, tamper detection, and non-equivocation) via game-based definitions under standard assumptions (collision-resistant hashing and EUF-CMA signatures). (Abstract)
 
`12.` Nemecek A, He H, Cheng G, Ayday E. Authenticated Contradictions from Desynchronized Provenance and Watermarking. *arXiv (Cornell University).* 2026;abs/2603.02378. doi:10.48550/arxiv.2603.02378
 
> [12.1] We make three contributions: - We formalize the Integrity Clash through a threat model and a conflict matrix that categorizes all combinations of provenance and watermark signals into four states, identifying the Authenticated Fake quadrant as the inconsistency. (Introduction)
 
> [12.2] This work formalizes and empirically demonstrates the $\textit{Integrity Clash}$, a condition in which a digital asset carries a cryptographically valid C2PA manifest asserting human authorship while its pixels simultaneously carry a watermark identifying it as AI-generated, with both signals passing their respective verification checks in isolation. (Abstract)
 
> [12.3] The authenticated fakes produced through this workflow require no cryptographic compromise, only the omission of a single assertion field permitted by the current specification. (Conclusion)
 
> [12.4] - We construct metadata washing workflows using openly available tools, showing that authenticated fakes can be produced through standard editing pipelines with no cryptographic compromise. (Introduction)
 
> [12.5] We construct metadata washing workflows that produce these authenticated fakes through standard editing pipelines, requiring no cryptographic compromise, only the semantic omission of a single assertion field permitted by the current C2PA specification. (Abstract)
 
`13.` Condrey D. A TEE-Based Architecture for Confidential and Dependable Process Attestation in Authorship Verification. *arXiv (Cornell University).* 2026;abs/2603.00178. doi:10.48550/arxiv.2603.00178
 
> [13.1] Trusted Execution Environments (TEEs) such as Intel SGX [15], ARM TrustZone [31], and AMD SEV-SNP [21] provide hardware-enforced isolation, converting the trust problem from 'the adversary controls everything' to 'the adversary controls everything except the enclave.' (Introduction)
 
> [13.2] (g) clock-manipulation resistance via SWF sequential hardness. (Results)
 
> [13.3] [10] and Strackx and Piessens [37] address rollback protection. (Body)
 
> [13.4] We introduce a resilient evidence chain protocol maintaining chain integrity across TEE crashes, network partitions, and enclave migration. (Abstract)
 
> [13.5] We present the first architecture for continuous process attestation evidence collection inside TEEs, providing hardware-backed tamper resistance against trust-inverted adversaries with graduated input assurance from software-channel integrity (Tier 1) through hardware-bound input (Tier 3). (Abstract)
 
`14.` Brandes A. Evidence Records for Public-Record Changes: Definitional Class Membership as the Certifiable Citation Unit. *arXiv (Cornell University).* 2026. doi:10.48550/arxiv.2609.11978
 
> [14.1] We introduce the Evidence Record, a deterministic, hash-pinned, claim-bounded primitive that makes a public-record change citable through a record whose integrity any reader can verify, and that carries its definitional class memberships explicitly. (Abstract)
 
> [14.2] Public records change in ways that matter for later interpretation, yet citing a change precisely is difficult--most consequentially, separating what the change demonstrably is from what it is claimed to mean. Definitional class membership--whether a change matches an objectively checkable predicate--is certifiable: it can be independently verified against the cited source. (Abstract)
 
> [14.3] On the uncertifiable side, a derived severity/priority label could not be certified under blinded adversarial review (reviewer confirmations of 4 to 17 of 30 against a pre-registered 24/30 gate) and is released only as uncalibrated metadata. (Abstract)
 
`15.` Abramyan M, Ala’anzy MA, Saeed N. CompProv Produces Machine Readable Graphs Encoding Microscopic Algebraic Provenance for Reproducible Computation. *arXiv (Cornell University).* 2026. doi:10.48550/arxiv.2610.01203
 
> [15.1] Deterministic replay reproduced each result exactly in a fresh environment, and CPG-based input substitution supported sensitivity analysis without exposing the underlying source code. (Abstract)
 
> [15.2] Existing provenance systems operate at the granularity of files, datasets, or pipeline stages, leaving the internal sequence of algebraic transformations connecting an algorithm's inputs to its outputs unrecorded; a rounding error, an undocumented substitution, or a missing intermediate value can propagate to a final result with no recoverable trace. (Abstract)
 
> [15.3] This work presents CompProv, a Java-based, audit-oriented provenance framework that captures lineage at the atomic level of individual algebraic operations by encapsulating numerical values in high-precision wrapper objects, producing a serializable Calculation Provenance Graph (CPG) that persists as a self-contained artifact rather than a discarded byproduct. (Abstract)
 
`16.` Moreau L, Batlajery BV, Huynh TD, Michaelides DT. Prov-template evaluation dataset. *ePrints Soton (University of Southampton).* 2016. doi:10.5258/soton/390436
 
> [16.1] Programmers write programs that log values and package them up in sets of bindings, a datastructure associating variables and values. (Abstract)
 
> [16.2] Our quantitative evaluation shows that sets of bindings have a size typically 40% of expanded provenance and that the expansion algorithm is suitably tractable, operating in fractions of milliseconds for the type of templates surveyed in the paper. (Abstract)
 
`17.` Li J, Zhang R, Liu J. ProvGRP: A Context-Aware Provenance Graph Reduction and Partition Approach for Facilitating Attack Investigation. *Electronics.* 2023;13:100-100. doi:10.3390/electronics13010100
 
> [17.1] However, most of these techniques rely on defined templates without considering the rich context information of events. (Abstract)
 
> [17.2] The simpli fi ed provenance graph describes several behaviors, which are associated together by long-running process chrome.exe. (Body)
 
> [17.3] Moreover, these methods fail to remove false dependencies caused by the coarse-grained nature of logs. (Abstract)
 
`18.` Liu J, Inam MA, Goyal A, Greenenwald D, Bates A, Chittal S. How to Effectively Trace Provenance on Windows Endpoint Detection & Response Telemetry. *Proceedings 2026 Workshop on Attack Provenance, Reasoning, and Investigation for Security in the Monitored Environment.* 2026. doi:10.14722/prism.2026.23012
 
> [18.1] We first show that the event-driven nature of most Windows system services make them candidates for execution partitioning, highlighting both inter-process and intra-process opportunities for pruning false information flows during graph traversal. (Body)
 
> [18.2] The first two heuristics are process-centric, leveraging domain knowledge of Windows service control flow patterns to mitigate the dependency explosion caused by Windows IPC. (Abstract)
 
> [18.3] When attempting to forward trace the attacks from their root cause(s), we typically found success using a naive tracing algorithm, i.e., the edge s→d was associated with the instantaneous timestamp t. (Body)
 
> [18.4] As wholesystem provenance is already prone to dependency explosion [21] due to the known semantic gap between system call logs and and intra-process control flow, the exacerbation of false provenance by EDR logs warrants careful consideration. (Body)
 
> [18.5] We show that it is possible to reproduce a conservative approximation of a whole-system provenance graph generated from syscall logs, but with reduced information flow precision. (Body)
 
> [18.6] From this graph, we must assume that P 2 is causally dependent on F b , but this is false provenance as no such information flow occurred on the system. (Body)
 
`19.` Song Q, Qihang Z, Xiaoqi J, et al. vCause: Efficient and Verifiable Causality Analysis for Cloud-based Endpoint Auditing. *Zenodo (CERN European Organization for Nuclear Research).* 2025;abs/2603.15216. doi:10.5281/zenodo.17908629
 
> [19.1] Algorithm 5: Validating Forward Causality Relations ̸ ``` for a Given Node Input: a node n , its forward causally related nodes and edges { Vn → , En →} , temporal range node proofs P , and the hash function H( · ) . (Methods)
 
> [19.2] vCause integrates two authenticated data structures: a graph accumulator and a verifiable provenance graph. (Abstract)
