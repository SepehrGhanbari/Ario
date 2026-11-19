# Referee report: "Independence Is Not Multiplicity" (Zenodo 10.5281/zenodo.24041161)

Reviewer: Claude (AI model, Sonnet 5.5). Date: 2026-11-17. Assignment A.
Status: `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE`. **This is an AI review. It is not independent human peer review, and it is not independent of the project's AI tooling** (the same model family wrote and attacked other Ario patches this week).

## 0. What I read, what I did not, and what I had already seen

- **Read in full:** the published preprint text (`papers/zenodo-published-research/24041161/Independence_Is_Not_Multiplicity_Extracted_Text.txt`, SHA-256 `1108f6905ad95e60694eb8b3b5cc8a1ea6b2a67c3f6e396c9019cb741c691287`, 8 pages, from the 2026-11-15 repository archive), and its `SOURCE_PROVENANCE.json`. Line numbers below refer to this extracted text, not to the PDF layout.
- **Ran:** the repository's provenance engine (`implementation/witness_provenance_experiment.py`) and its test file from the same archive (a later tree than the paper's pinned commit `f562e14`), plus three small probes written by me.
- **Could not read:** the three research-branch files (brief, source-preservation register, adversarial supplement draft) and PR #242; those URLs are outside my network allowlist. Anything that depends on them is marked UNKNOWN. I also did not have the author's `reproduce_study.py`, `scenario_results.*` or `SHA256SUMS.txt`, and did not check the three Git blob IDs against GitHub.
- **Disclosure about the requested pre-results step.** I had already read this preprint, including its results, earlier in this same session, before the context was compacted. The counterarguments in section 1 are therefore **post-hoc reconstructions, not pre-registered**. They were written down before I re-read the text and before I ran the probes, but not before I had seen the results once.

Tags: **VERIFIED** (checked in the text or by running code; method stated), **HYPOTHESIS** (plausible, not tested), **UNKNOWN** (could not be checked).

## 1. Counterarguments formulated before this re-read (post-hoc, see section 0)

1. **The 4/16 versus 16/16 contrast is entailed by construction, so it is not an experiment.** If the baseline looks at storage identity only and 14 of 16 scenarios vary something else, the outcome is fixed before any run.
2. **The wrapper's 16/16 is circular for the same reason from the other side.** Scenarios are mutations of the engine's own fixture constructor; labels come from the same mutations; the gate reads the same fields.
3. **The engine cannot detect what the title is about.** A hidden shared source or controller that the case author did not declare produces the same report as true independence. A completeness flag and its origin label are inputs, not observations.
4. (added) A trivial constant classifier may beat the declared baseline, which would show the baseline is not a meaningful null.

All four are confirmed in section 3.

## 2. Summary of the submission

Using a pinned Ario snapshot, the paper compares (a) a storage-object-identity rule and (b) a three-outcome gate wrapped around `evaluate_provenance()` on 16 hand-built synthetic cases with author-declared labels (2 CONDITIONAL, 7 DEPENDENT, 7 UNKNOWN). Reported: baseline 4/16, gate 16/16, 12 "unsupported conditional endorsements" versus 0. It also reports 280 passing tests from five existing modules, 148/148 internal hash matches and 3/3 Git blob matches against GitHub. The claims are heavily hedged in the body. The thesis ("multiplicity of records is not independence of evidence roots") is correct and worth stating. My concerns are about what the experiment supports and where the abstract and conclusion outrun the body.

Recommendation: **major revision.** As an empirical comparison the result carries no information. As a worked demonstration of decision boundaries and of the cost of equating storage distinctness with independence, it is useful if reframed.

## 3. Prioritized findings

### F1 (major, VERIFIED): the baseline's 4/16 is a logical consequence of the design
Evidence in the paper itself:
- Baseline (§4.3, lines 145-150) returns CONDITIONAL for distinct storage objects, DEPENDENT for the same object, UNKNOWN for duplicated or unresolvable artifacts. It reads nothing else.
- Scenario table (§4.4, lines 175-191): of the 14 non-CONDITIONAL scenarios, only S05 (aliased storage) and S16 (artifact presented twice) vary storage identity. The other twelve (S02-S04, S06-S14) vary administrator, source, backup, control root, inventory, graph origin or custody record, none of which the baseline reads.
- So the baseline must return CONDITIONAL on those twelve. 2 (S01, S15) + S05 + S16 = 4. The result can be derived from the table without running anything.

Consequence: "agreed with four of sixteen" and "twelve unsupported endorsements" (abstract lines 30-32; §9 lines 312-314 "incorrectly endorsed twelve of fourteen") report the number of scenarios the author built to vary other fields. They are not measurements of a rule.

### F2 (major, VERIFIED, partly conceded by the authors): the gate's 16/16 is circular and largely duplicates existing tests
- Scenarios are "controlled edits to the pinned repository's own synthetic fixture constructor" (§4.4, lines 170-171); labels are assigned by the same process (§3 lines 115-117; §4.3 lines 166-168); the gate is a wrapper over the same engine (lines 151-165). §6 line 260 concedes: "The fact that the bounded wrapper agrees with every label is not a surprise."
- The repository's own test file already asserts these classes. In my archive, `tests/test_witness_provenance_experiment.py` holds 58 tests: `tp01..tp26` (26) plus 15 `test_extra_*` (= 41, matching the manuscript's "provenance (41)") plus 17 `test_issue129_*` added later (= 58). This resolves the "41 versus 58" drift: it is the later `issue129` additions, not an error in the paper. Examples of correspondence (my mapping, to be confirmed against the unseen `reproduce_study.py`): S01~tp05 (separate lab control), S02~tp01 (one administrator), S05~tp02 (alias storage), S06~tp03 (shared restore backup), S07~tp04 (override root), S09~tp06 (absent admin inventory), S12~tp09 (candidate-supplied graph), S14~tp12 (missing transfer record), S15~tp08 (self-certified witness), S16~tp21 (one artifact duplicated).
- Fairness note: the authors do disclose circularity (lines 166-168, 260-261, 271-274). The problem is that the abstract and conclusion present 16/16 as "the" result anyway (abstract lines 32-33; §9). Disclosure in the body does not change what a reader takes from the abstract.

### F3 (major, VERIFIED by running the engine): completeness and its origin are declared inputs, so hidden dependencies are invisible
I built three inputs from the test file's own `baseline()` fixture and ran `evaluate_provenance`:
- World A: the fixture as written (separate by declaration).
- World B: a world in which both captures really derive from one source and one administrator, but the case author omitted that from the graph and labelled completeness as LAB-origin. This is **byte-identical input to A** (`A == B` is `True`), so the report is identical (`LAB_CONDITIONALLY_SEPARATE`, `LAB_CONDITIONALLY_DISTINCT`, `LAB_DISTINCT_OBJECTS`, custody `LAB_CHAIN_PRESENT` x2, `LAB_BEFORE_MUTATION`).
- World C: the same graph with only `completeness_origin` changed from LAB to CANDIDATE: source and administrative separation become `UNKNOWN`.

What this shows: the verdict is a function of the declared graph and a **self-applied origin label**. A party that supplies its own graph and labels it LAB obtains CONDITIONAL; honest labelling is what produces UNKNOWN. §6 lines 250-259 says S12 "shows that even an internally coherent graph cannot establish its own independence when supplied by the candidate". What the code shows is narrower: the engine honors the label it is given. §7 lines 279-282 ("Missing a dependency may cause a positive lab classification") states the limit correctly, but it is placed after a discussion that reads as if the gate handles falsely complete graphs. It handles *declared* incompleteness (known unknowns) and cannot handle *undeclared* incompleteness (unknown unknowns), which is the case the title is about.

On the user's question whether the non-identifiability counterexamples support the claims: the paper contains no formal non-identifiability statement. The A/B pair above is a minimal one (two worlds, one observation). It supports the weak claim "declared graphs do not identify independence". It does not support any claim that the gate establishes independence. The supplement draft (item 3) was unreadable, so any counterexample stated there is UNKNOWN to me.

### F4 (major, VERIFIED arithmetic): the baseline is weaker than constant classifiers
The study has 2 CONDITIONAL, 7 DEPENDENT and 7 UNKNOWN cases. A classifier that always answers UNKNOWN agrees with the label on 7/16 and makes **zero** unsupported conditional endorsements. That beats the declared baseline (4/16, 12 endorsements) on both reported metrics. So (a) the baseline is not a reasonable null, and (b) the headline metric "unsupported CONDITIONAL endorsements" is satisfied trivially by a rule that never says anything is separate. With only two positive cases, missed positives (CONDITIONAL called UNKNOWN) cannot be estimated. The paper itself says (§8) missed detections, false rejections and UNKNOWN decisions should be reported separately; the present results do not.

### F5 (major, VERIFIED text): "independently" in the abstract contradicts §4.1 and §7
Abstract lines 34-35: "independently matched three source-file Git blob identifiers against a fixed GitHub commit". §4.1 lines 128-131: the check used "the connected GitHub repository" (the author's own repository, through the author's tooling) against a snapshot the author's project produced. §7 lines 292-294 correctly requires "actors and systems not controlled by this project" for independent replication. The check is an external-to-the-export spot check, not independent. Likewise the 280-test and 148-file results were produced by the author's AI-assisted workflow, i.e. one party re-running its own code. UNKNOWN: whether any third party has re-run it.

### F6 (medium, VERIFIED text): published record carries unresolved draft statements and an availability inconsistency
- PDF title "A Reproducible Sixteen-Scenario Study of Witness Provenance in Audit Logs" versus Zenodo record title "A Synthetic Witness-Provenance Study within Ario's Auditable Epistemic Framework" (`SOURCE_PROVENANCE.json`).
- The text is labelled "Author-review manuscript" and contains to-dos addressed to the author: "must critically inspect, verify... before publication" (lines 43-45), "should confirm any additional competing interests before submission" (lines 322-323), funding "must reconfirm" (lines 324-325), "must verify all sources, outputs..." (lines 336-337).
- Abstract lines 36-38 promises "complete scenarios, source hashes, code, raw results". §Availability lines 331-334 says the supplement artifacts are "newly generated working files and should not be described as already deposited at an external DOI". If that is still true, the supplementary claims cannot be checked from the record. UNKNOWN: whether it has since been deposited.

### F7 (medium, VERIFIED for another module, UNKNOWN here): passing tests have limited evidential weight
In the seeded-flaw exercise this week, two silent weakenings in `core/audit_engine.py` (digest comparison on a 16-character prefix; transformation compared by id only) left the existing suite green, and two tautological tests were added without detection. That is VERIFIED for that module only. Whether the 280 tests are mutation-sensitive for the five modules used here is UNKNOWN. The paper cites 280 passing tests as part of its reproduction result (§5.1); a mutation run on `witness_provenance_experiment.py` would tell readers what "280 passed" means.

### F8 (medium, HYPOTHESIS): pinned-commit drift
The paper pins 25 October (`f562e14`); the tree I read contains 17 later `issue129` tests about compromised custodians, so the engine changed after the pin. Whether 16/16 still holds on the current engine is UNKNOWN. The paper says so (§7 lines 285-286); a rerun at the current commit would cost little.

### F9 (medium, VERIFIED/HYPOTHESIS): novelty and literature
The slogan has long antecedents in dependability engineering, and the paper does not cite them (see section 6). The claimed "principal new contribution" is the 16-case exercise (§1 lines 68-73), which F1 and F2 reduce to a demonstration. The novelty case therefore has to rest on the engineering artifact (an explicit three-valued gate that refuses to infer independence), and be compared with prior art on dependence handling.

### F10 (low, VERIFIED): internal consistency checks that passed
- 73 + 26 + 41 + 53 + 87 = 280. 
- Table 5.2 arithmetic: 2 + 6 + 6 = 14 CONDITIONAL outputs; 12 of them on non-CONDITIONAL labels; 2 + 1 + 1 = 4 agreements.
- Counts for the "seven DEPENDENT / seven UNKNOWN / two CONDITIONAL" split match the scenario table (S02-S08; S09-S14 plus S16; S01 and S15).
- Reference details I could check in search results or from familiarity (Buneman et al. 2001; Green et al. 2007; RFC 9162; NIST SP 800-53 Rev. 5 AU-9; National Academies 2019) are consistent. I did not re-verify every page range.

### F11 (low, HYPOTHESIS): terminology
The test file docstring says "Pre-registered TP-01..TP-26" while the preprint says the study "was not independently preregistered". Pre-registration by the author of tests the author later evaluates against is not independent pre-registration. Align the vocabulary.

## 4. Answers to the specific questions

1. **4/16 versus 16/16 and circularity.** Circular on both sides (F1, F2). The numbers describe how the cases were built.
2. **Is the baseline unfairly weak?** Yes, and by more than the paper says: it loses to an always-UNKNOWN classifier (F4). The paper's own words ("pedagogical", "not a fair representation of state of the art") are accurate, but the abstract and §9 still count its failures.
3. **Hidden dependencies and falsely complete graphs.** Not detectable by this method; shown by running the engine (F3). Declared incompleteness is handled; undeclared incompleteness is not.
4. **Independent evidence roots versus multiple reports.** The paper states the distinction well in prose. The experiment models roots only as nodes the author declared; it does not test whether roots can be recovered from reports. That would need data in which the true roots are hidden from the evaluator and known only to an adjudicator.
5. **Do the non-identifiability counterexamples support the claims?** The minimal pair in F3 supports "declared graphs do not identify independence". It does not support "the gate establishes it". The supplement's own counterexamples are UNKNOWN to me.
6. **Reproducibility versus independent validation.** Accurately distinguished in §2, §7 and the conclusion; contradicted by the abstract's "independently" (F5). Everything reported was run by the author's workflow.

## 5. Recommended corrections

### Abstract (replace the results sentences)
Suggested wording: "We examine, in a pinned open-source audit-provenance implementation, how an evidence-independence verdict changes when a rule reads only storage identity versus when it also reads declared source, control, completeness and custody fields, on sixteen synthetic cases whose labels were assigned by the authors. Because the cases vary exactly the fields the richer rule reads, the outcomes follow from the construction (storage-only: 4/16; three-outcome gate: 16/16) and are reported as a demonstration of decision boundaries, not as a measurement. A constant UNKNOWN rule would agree with 7/16. The gate evaluates declared graphs; it cannot detect dependencies the graph omits, and its completeness label is self-declared. We also re-ran, with the same workflow that produced the code, 280 existing tests and matched three file hashes to the project's own repository; this is reproducibility by the originating party, not independent replication."

### Methods
1. State up front that outcomes are entailed by which fields each rule reads, and give a table "field read by rule" × "scenario varies it".
2. Add baselines: constant-UNKNOWN, constant-DEPENDENT, storage + administrator rule, and a randomly labelled rule, scored on all of agreement, unsupported endorsements, missed positives and UNKNOWN rate.
3. Describe `completeness_origin` as an input and test the self-labelling case (world A versus C above).
4. Run the study at the current commit as well as the pinned one.
5. Add a mutation-sensitivity check for the five test modules.
6. Have scenarios and labels written by someone who has not seen the gate, with labels withheld from whoever writes the wrapper.

### Discussion
Rewrite §6 lines 250-259: replace "S12 shows that even an internally coherent graph cannot establish its own independence" with a statement that the engine returns UNKNOWN when the graph's origin is labelled as the candidate and CONDITIONAL when it is labelled otherwise, and that the label is not authenticated. Add a short subsection on undeclared dependencies (the A/B pair).

### Limitations (add)
Outcomes entailed by design; baseline below constant classifiers; two positive cases; self-declared completeness/origin; no hidden-dependency scenarios; same-party execution; engine has changed since the pin; passing tests not shown to be mutation-sensitive.

### Record hygiene
Remove "author-review" to-dos or resolve them; align the PDF and Zenodo titles; state whether the supplement is deposited and with which identifier; state the exact repository tree for the 41-versus-58 count.

## 6. References to consider (status of my verification)

- Knight, J. C., & Leveson, N. G. (1986). An experimental evaluation of the assumption of independence in multiversion programming. *IEEE Trans. Software Engineering* 12(1), 96-109. Independently developed versions failed together more often than independence predicts. **Existence confirmed in search results today; not re-read.** Directly relevant as the classical experiment on independence-by-multiplicity.
- Douceur, J. R. (2002). The Sybil Attack. IPTPS 2002. **Existence confirmed in search results.** Multiple identities without a trusted root of distinctness.
- Haeberlen, A., Kouznetsov, P., & Druschel, P. (2007). PeerReview: Practical accountability for distributed systems. SOSP 2007. **Existence confirmed.** Witness-based accountability with evidence of misbehavior.
- From my own knowledge, **not re-verified today; check before citing:** Pearl (1988), *Probabilistic Reasoning in Intelligent Systems* (double counting of correlated evidence); Ladha (1992), Condorcet jury theorem with correlated votes, *AJPS* 36(3); Schneier & Kelsey (1999), secure audit logs, *ACM TISSEC* 2(2); Crosby & Wallach (2009), tamper-evident logging, USENIX Security; Malkhi & Reiter (1998), Byzantine quorum systems, *Distributed Computing* 11; Chuat et al. (2015), gossip for Certificate Transparency; common-cause failure and beta-factor models in functional-safety standards (for example IEC 61508). **HYPOTHESIS** that these are close enough prior art to require discussion.

## 7. What would change my assessment

- A set of scenarios and labels produced by an independent author, with hidden shared roots known only to an adjudicator, evaluated against several baselines (F1-F4).
- A mutation result for the five test modules (F7).
- A rerun at the current commit (F8).
- Reading the unavailable supplement draft and research-branch files; I would revise F3 and answer 5 accordingly.

## 8. Limits of this review

AI review; same model family as other Ario tooling; one pass; extracted text only (not the rendered PDF, so figures and formulas could differ); my engine tree is later than the paper's pinned commit; I did not run the author's scripts or check the GitHub blob IDs. Findings F1, F4, F5, F6, F10 rest on the text; F2's test counts and F3 rest on running code in my archive; everything else is a hypothesis or UNKNOWN as marked.