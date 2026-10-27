# Evidence Laundering in Auditable AI Systems: A Reproducible Case Study of Source Dependence, Integrity Checks, and Bounded Authorization

**Sepehr Ghanbari**  
Independent Researcher, Ario Project (no institutional affiliation claimed)  
Correspondence: sepehrqanbari@gmail.com  
ORCID: https://orcid.org/0009-0006-4710-3914  
**Working paper / preprint manuscript · 27 October 2026 · Not peer reviewed**

## Abstract

An artificial system can pass local structural checks while relying on records whose origin, independence, or authority is uncertain. We examine this gap through a reproducible, bounded case study of Ario, an open-source research implementation that separates checkpoint integrity, witness agreement, provenance control, and authorization. The study uses a fixed, AI-readable source snapshot attributed to Git commit `f562e14cd8ca7f8723ad0b94eec005025f07a9a6`. We extracted 148 text files and checked each file's SHA-256 and Git blob SHA-1 against the included manifest; all 148 matched their *supplied* digests. We then ran five targeted Python test modules covering checkpoint-prefix comparison, synthetic witness comparison, witness-provenance modeling, and two versions of compromise-and-recovery assessment: 280 tests passed in a single combined run under Python 3.13.5 and pytest 9.0.2. These results reproduce bounded program behavior for supplied synthetic inputs; they do not independently authenticate the original Git history, establish real custody independence, validate historical events, or confer operational authorization. We present a cross-experiment failure taxonomy and a claim-to-evidence interpretation matrix to explain why matching hashes, agreeing witnesses, and successful tests cannot be composed into stronger, unsupported historical or ontological conclusions. The principal contribution is a documented reproduction and critical interpretation of these narrowly defined checks, not a proof of comprehensive AI safety.

**Keywords:** artificial intelligence; evidence provenance; source dependence; epistemic integrity; audit logs; witness independence; reproducibility; authorization; adversarial testing; uncertainty.

**AI-use disclosure (also supplied for SSRN abstract metadata):** Generative AI (OpenAI GPT-6, October 2026) assisted in drafting, organizing, and language editing this manuscript and in executing the stated local extraction and test commands. It is not an author. The named author is responsible for reviewing the manuscript, interpreting the evidence, verifying references, and approving submission.

## 1. Introduction

Many AI-enabled workflows produce records that look evidentially strong: hash-linked event histories, repeated or summarized observations, multiple witnesses, stable test results, and formally shaped authorization decisions. Yet these records answer different questions. A hash proves correspondence to bytes under a specified digest computation, not that those bytes were honestly collected. Two reports can agree because they share the same origin or controller. A successful regression suite establishes observed behavior over its exercised fixtures, not that an implementation is secure in production. An authorization-like data field is not itself an authorized action.

This paper studies a concrete engineering question: **under what bounded circumstances does an audit detect a disagreement between an altered local account and retained references, and which stronger claims remain unsupported even when every local check succeeds?** The case is Ario, a public repository focused on inspectable epistemic claims, evidence ancestry, historical representation, and bounded agency [1, 2]. The central distinction is not whether an AI has an enduring identity, but whether an auditor avoids promoting one type of evidence into another without a justified warrant.

The present contribution is deliberately narrower than a new general framework. It reports a reproducible execution of existing source-identified tests, documents a cryptographic inventory check over source payloads, relates failure modes across several modules, and identifies where positive technical verdicts must stop. It does not claim a comparative benchmark against other systems, a human-subject study, a novel cryptographic primitive, or an independently assessed security guarantee.

## 2. Related work and conceptual boundary

The W3C PROV data model distinguishes entities, activities, and agents, supporting explicit descriptions of derivation and attribution [3]. Provenance *representation*, however, does not by itself prove that a claimed source is independent or genuine. Certificate Transparency illustrates a complementary lesson: append-only structures and cryptographic inclusion/consistency proofs support specified log properties, while distributed observation and split-view resistance require additional assumptions [4]. Ario's own documentation repeatedly treats this separation as a constraint on admissible conclusions [1, 2].

Research on consistency-based hallucination detection, such as SelfCheckGPT, exploits agreement and disagreement among generations as useful statistical signals [5]. Such signals address a different task from authenticated historical evidence. In the adversarial setting considered here, consistency among outputs can arise from shared input, circular derivation, or the replacement of both the candidate and its supposed corroboration. Consequently, **repetition and agreement are observations; independence and truth are separate claims that need separate support**.

## 3. Materials, questions, and reproducibility protocol

### 3.1 Source material and scope

The primary material was `Ario_READ.txt`, the AI-readable textual export associated with Ario's public research archive [1, 2]. It identifies a 159-file repository tree at commit `f562e14cd8ca7f8723ad0b94eec005025f07a9a6`, including 148 verbatim UTF-8 source/text files and an inventory of 11 non-text files whose binary contents are **not** contained in the readable export. The 159-file *byte-reconstructable* edition is a separate artifact described in the archival record [2].

This analysis used the 148 text entries, not the omitted 11 binary payloads. The available export was obtained from the author's archived material rather than independently downloaded from GitHub during this run. Its SHA-256, as processed locally for this reproduction, was `63f170645e67131025e1d3b8d6e9002a8f3312741ecfce121b886f8d085bd68b` (2,857,981 bytes). This fingerprint identifies **the examined local text export**; it is not a cryptographic attestation by GitHub, Zenodo, or a third party.

### 3.2 Research questions

**RQ1 — Integrity:** What does rechecking the digest metadata of a text repository snapshot establish, and what does it leave unresolved?

**RQ2 — Conflict:** Can test scenarios distinguish an internally coherent rewritten chain from its disagreement with a separately supplied frozen checkpoint?

**RQ3 — Dependence:** Can synthetic multiple-witness and provenance-graph checks preserve the difference between agreement, separately modeled custody, common control, and historical event truth?

**RQ4 — Authority:** Do the tested comparison and recovery reports refrain from becoming automatic evidence admission, identity authentication, or human authorization?

### 3.3 Extraction and test procedure

A byte-oriented parser read each `BEGIN_FILE` record's declared `ORIGINAL_BYTES`, extracted the exact payload length, checked SHA-256 over that payload, and separately checked Git blob SHA-1 using the standard `SHA1("blob " || decimal_length || NUL || payload)` construction. The resulting text files were written into a disposable analysis directory. No archived source file was edited in place. **148/148 extracted payloads matched both of the digests written in that same supplied export.** This verifies internal correspondence, not independence of the manifest from the payloads.

Tests were run from the extracted `implementation/` directory with CPython 3.13.5 and pytest 9.0.2 on a Linux analysis host. The execution was read-only with respect to the author's repository; temporary extraction and test processes were local to this analysis. Bytecode and pytest cache generation were disabled. The exact combined command was:

```
PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -p no:cacheprovider -q \
  tests/test_checkpoint_prefix_experiment.py \
  tests/test_independent_witness_experiment.py \
  tests/test_witness_provenance_experiment.py \
  tests/test_witness_compromise_recovery_experiment.py \
  tests/test_witness_compromise_recovery_experiment_v0_2.py
```

No live signer, two-host network, external identity registry, human approval endpoint, or physical witness was exercised. The reported result must be interpreted as a *single local deterministic-target test run*, not as a cross-host certification.

## 4. Experiment classes and threat model

The relevant Ario modules explicitly assume test-controller-selected contexts, symbolic identities, and retained reference objects. Attacker capabilities are *scenario inputs*, not detections of real compromise. We group their adversarial cases into five testable classes.

**A. Candidate rewrite with recomputed local hashes.** An adversary controls candidate ledger content and recomputes its local chain. A local-validity result can therefore coexist with a mismatch against a separately held test reference. The checkpoint experiment tests altered prefixes, declared scopes, descriptor mismatches, stale floors, and malformed or duplicated metadata [6].

**B. Witness agreement without guaranteed source independence.** Two controlled witness envelopes may report the same historical prefix. The witness experiment compares each against its own frozen fixture, while distinguishing metadata differences from actual historical-content conflicts. Common control or adversary control of both the witness and frozen reference invalidates the inference of independent attestation [7].

**C. Provenance laundering through shared causes.** Two storage locations may restore from one backup, be writable by one administrator, or derive from the same source. The provenance graph contains explicit tests for such links, unknown inventories, cycles, self-issued claims, and copied prior audit reports. A complete laboratory graph can support conditional separation *in the model*; an incomplete or candidate-issued one cannot certify independence [8].

**D. Compromise and recovery narratives.** A favorable previous report may be replayed or edited, or a synthetic recovery history may omit critical ancestors. Recovery assessment v0.2 tightens prior-evaluation identification and controller-declared head binding, but explicitly lacks an externally retained trust root [9].

**E. Promotion beyond the tested property.** A validator or witness diagnostic may be represented as if it were new admissible evidence, proof of a person's identity, or authority to execute an action. The relevant project documents deliberately classify these as `NOT_EVALUATED`, `NOT_ESTABLISHED`, `UNKNOWN`, or equivalent non-authorizing outcomes [6-9].

## 5. Results

### 5.1 Reproduction summary

| Targeted module in pinned text snapshot | Test cases in combined run | Observation |
|---|---:|---|
| Checkpoint-prefix experiment | 73 | Included in passing combined execution |
| Independent historical witness experiment | 26 | Included in passing combined execution |
| Witness-provenance experiment | 41 | Included in passing combined execution |
| Compromise/recovery experiment v0.1 | 53 | Included in passing combined execution |
| Compromise/recovery experiment v0.2 | 87 | Included in passing combined execution |
| **Total** | **280** | **280 passed; 1.37 seconds; one combined execution** |

The table reports pytest's collected passing tests, not the number of distinct threat models, attacks, real-world environments, or independently authenticated witnesses. The test modules themselves are authored fixtures and can miss faults outside their assertions. A later attempt to execute the modules individually did not produce a complete five-module standalone result before the execution window ended; therefore the combined execution, rather than unverified per-module repeatability, is the central reproduction claim. Four of the five modules did emit standalone pass summaries in that follow-up; the fifth has no completed standalone verdict in this record.

### 5.2 Claim-to-evidence interpretation matrix

| Observed result | Supported inference | Inference **not** established |
|---|---|---|
| 148 payload digest matches | Bytes correspond to hashes listed in the same export | Independent authenticity of the original repository |
| Internally valid candidate chain | Candidate satisfies the local hash/link rule | Original events occurred as described |
| Frozen checkpoint mismatch | Candidate differs from the supplied retained reference | Which historical party is honest |
| Two synthetic witness commitments agree | Equivalent controlled commitments under defined scope | Real custody independence or true events |
| Provenance graph reports conditional separation | Disjointness under its explicitly complete supplied graph | Complete inventory of real-world administrative control |
| Recovery chain accepted under named lab head | Specified case-binding checks hold in the fixture | Untampered external trust anchor or legal authority |
| 280 targeted tests pass | Checked assertions held for this run | Comprehensive security, deployed reliability, or AI identity |

### 5.3 Interpretive findings

**F1 — Source self-consistency is not source authentication.** RQ1 received an internally positive result: all 148 extracted UTF-8 files matched their supplied size and digest metadata. Since the payload and digests arrived together, a controller able to replace both could preserve the same structural property. Independent comparison with an externally retained, previously authenticated commitment was not performed here.

**F2 — Local validity and historical correspondence are independent axes.** In RQ2, the prescribed negative scenarios distinguish a rewritten candidate chain from a frozen checkpoint. This is a meaningful *conditional discrepancy detector*. It cannot decide which account is historically true if the reference itself is untrusted, colluding, or retrospectively replaced.

**F3 — Correlated witnesses must not be counted as independent corroboration.** RQ3's synthetic witness and provenance cases make one subtle distinction explicit: disagreement of serialized witness metadata does not necessarily imply different historical bytes, while agreement of historical bytes does not necessarily imply independent collection. A common backup or administrator can collapse apparently plural testimony into one source of control. Missing provenance edges remain epistemically unknown rather than being treated as proof of separation.

**F4 — Technical checks do not grant authority.** RQ4's relevant artifacts are comparison reports and bounded recovery diagnostics. The executed tests exercise restrictions within those local interfaces; neither the reports nor a passing test result should be used as an automatically admitted identity, human-authorization, or continuity fact. The architecture's non-authorizing boundary is a contract under test, not a universal theorem about all integrations.

## 6. Why evidence laundering is a composition failure

Evidence laundering occurs when a derived representation is treated as possessing stronger evidential status than its inputs justify. Consider a synthetic unsupported claim `C0`, a summary `S(C0)`, a repeated witness statement `W(S(C0))`, and an audit record `A(W)`. If every artifact is derived through the same controller, then the *number* of artifacts increases while the number of independent origins does not. A naive system may count each item as a fresh source and increase confidence; a provenance-aware system instead asks whether any distinct evidentiary ancestor exists.

The point is operational, not metaphysical. A hash commitment is valuable once a trusted reference and boundary of control are specified. Multiple observers are valuable once their independence is justified. Regression tests are valuable for guarding the exercised properties. A weakness arises when these tools are silently composed across incompatible claim types:

- `valid_hash_chain` is upgraded to `authentic_history`;
- `two_matching_witnesses` is upgraded to `independent_corroboration`;
- `provenance_graph_pass` is upgraded to `actual_independent_custody`;
- `test_pass` is upgraded to `authorized_release`;
- `stored_memory` is upgraded to `true_claim` or `persistent_self`.

The examined source and its documentation explicitly avoid these promotions. The strongest defensible positive result remains conditional on scope, fixture selection, controller honesty, and completeness. There is no evidence here that a model's verbal certainty or a system's self-description can substitute for those prerequisites.

## 7. Threats to validity and negative evidence

**Construct validity.** The tests model hand-selected synthetic cases. Terms such as `LAB_BEFORE_MUTATION` and `CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON` are labels assigned under stipulated premises, not measurements of real time, physical custody, or authenticated identity. Code-level correctness at one interface does not imply end-to-end enforcement by downstream consumers.

**Internal validity.** The 148 source-file hash checks rely on digest fields carried by the same export; a forged pair could pass. No contemporaneous trusted external head, independent Git clone audit, or cross-organizational custody chain was established. The omitted 11 binary files were not reconstructed or evaluated in this experiment.

**Execution validity.** The central 280-test result is one passing combined run on one Linux host under one Python/pytest configuration. The incomplete later isolated rerun must not be silently represented as a second complete successful experiment. Independent physical-host and Windows reproduction of *this exact selected snapshot and command* were not performed for this paper. No timing performance claims follow from the 1.37-second run.

**External validity.** Simulated actors are not proof of real-world adversarial resilience. This reproduction did not evaluate live cryptographic signing, revocation, arbitrary Byzantine behavior, network partitions, coordinated third-party witnesses, deployment privilege boundaries, or the behavior of a current large language model. Outcomes are not evidence of machine consciousness, persistent personal identity, continuity across backups, or institutional safety.

**Selection and publication bias.** The targets were five selected public regression modules, not a randomly sampled benchmark. The research repository includes additional tests and historical reports, including open defects and previously recorded negative/expected-failure results [9]. They were not subsumed into the 280-test denominator. No comparison with a no-audit baseline or alternative provenance systems was run.

## 8. Implications and future tests

The case suggests a practical audit discipline: label every positive status with its actual predicate, the scope and origin of its reference, and the operations it **does not** authorize. Evidence admission, custody independence, and human approval should remain independent gates with recorded external grounds where those grounds are needed. More copies of one claim should not substitute for an independently held record. An explicitly unresolved result is preferable to unsupported elevation of authority.

A stronger empirical follow-up would preregister a blinded matrix of adversary capabilities and externally retained anchors; run the same fixtures on independently provisioned hosts; measure false-positive and false-negative rates for provenance conflict detection; test lossy, multi-hop derivations; and independently evaluate downstream clients for unauthorized status promotion. A valid comparison would include a specified unaudited baseline and compare performance with both misses and incorrect rejections, rather than treating the passing of the system's own unit tests as a scientific estimate of efficacy.

## 9. Conclusion

A locally consistent chain, a matching pair of synthetic witnesses, a complete-looking provenance graph, and a successful test run can all be genuine observations without establishing what happened in the world. In the pinned Ario snapshot examined here, the 148 text-payload checks and a 280-test targeted combined run reproduced the system's constrained handling of these categories under synthetic assumptions. The important result is not generalized safety; it is a documented separation of **structural correctness**, **conditional reference correspondence**, **provenance dependence**, and **authorization**. Bridging those categories requires evidence that this study has not supplied. The remaining uncertainty is part of the result.

## Declarations

**Author contribution:** Sepehr Ghanbari is the sole named author and originator of the Ario research project. This manuscript is an AI-assisted editorial synthesis and local reproduction intended for the author's verification before public submission. No AI system is named as a co-author.

**Funding and interests:** No funding source, grant award, or competing-interest declaration is asserted on the basis of the materials examined here. The corresponding author should confirm the final declarations before submission.

**Ethics:** Only existing source material and synthetic fixtures were analyzed in this reproduction; no human participants or identifiable private research-subject data were involved in the reported tests.

**Data and code availability:** Public project repository: https://github.com/SepehrGhanbari/Ario . Associated repository-snapshot archival record: https://doi.org/10.5281/zenodo.23651704 . The exact `Ario_READ.txt` source material is a text-only subset of the complete 159-file snapshot and is separately identified in Section 3. Test files and principal documentation paths are listed below for targeted examination. No SSRN identifier has yet been assigned to this manuscript.

**AI-use disclosure:** OpenAI GPT-6 assisted with drafting, synthesis, formatting, and code-assisted local test execution. The author is responsible for verifying all claims, disclosing the use of AI to SSRN, and deciding whether and where to submit this preprint.

## References

[1] Ghanbari, S. (2026). *Ario*, open-source research repository. https://github.com/SepehrGhanbari/Ario . Examined snapshot: commit `f562e14cd8ca7f8723ad0b94eec005025f07a9a6` (25 October 2026), as identified by the archived readable export.

[2] Ghanbari, S. (2026). *Ario: Complete Verifiable GitHub Repository Snapshot and AI-Readable Text Edition*. Zenodo. https://doi.org/10.5281/zenodo.23651704 . Related primary archival material; no independent external authenticity claim is made in this paper.

[3] Moreau, L., and Missier, P. (eds.) (2013). *PROV-DM: The PROV Data Model*. W3C Recommendation. https://www.w3.org/TR/prov-dm/ .

[4] Laurie, B., Messeri, E., and Stradling, R. (2021). *Certificate Transparency Version 2.0*. RFC 9162. https://www.rfc-editor.org/rfc/rfc9162.html .

[5] Manakul, P., Liusie, A., and Gales, M. (2023). *SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models*. EMNLP, 9004-9017. https://doi.org/10.18653/v1/2023.emnlp-main.557 .

[6] Ghanbari, S. (2026). *Checkpoint Prefix Experiment v0.1* and `implementation/tests/test_checkpoint_prefix_experiment.py`. In [1], paths `implementation/CHECKPOINT_PREFIX_EXPERIMENT_V0_1.md` and corresponding test module.

[7] Ghanbari, S. (2026). *Independent Historical Witness Experiment v0.1* and `implementation/tests/test_independent_witness_experiment.py`. In [1], corresponding documentation and test module.

[8] Ghanbari, S. (2026). *Witness Provenance Experiment v0.1* and `implementation/tests/test_witness_provenance_experiment.py`. In [1], corresponding documentation and test module.

[9] Ghanbari, S. (2026). *Witness Compromise and Recovery Experiments v0.1 and v0.2*; `implementation/tests/test_witness_compromise_recovery_experiment.py` and `implementation/tests/test_witness_compromise_recovery_experiment_v0_2.py`. In [1], corresponding documentation and test modules.