# Ario — Auditable Epistemic Framework for AI

## Independent Research on AI Identity, Memory, Evidence, and Revision

**فارسی: آریو — چارچوب معرفتی ممیزی‌پذیر برای هوش مصنوعی**

**Project Architect & Creator: Sepehr Ghanbari**  
**Project Role:** Architect, Creator, and Principal Researcher

**Research identity:** **Ario — Auditable Epistemic Framework for AI**  
**نام پژوهشی فارسی:** آریو — چارچوب معرفتی ممیزی‌پذیر برای هوش مصنوعی  
**Official website:** https://ario-research-independent.vercel.app/  
**Secondary website mirror:** https://sepehrghanbari.github.io/Ario/  
**Researcher ORCID:** https://orcid.org/0009-0006-4710-3914

The full descriptive name distinguishes this research framework from other uses of the word “Ario.” It does **not** imply exclusive rights to that word, affiliation with similarly named organizations, or a claim that the framework has proved machine consciousness.



Ario is an experimental research project investigating how an AI system can represent, examine, and revise claims about its own identity, memory, continuity, and self-model without treating those claims as established facts.

The project does **not** attempt to engineer a proof of AI consciousness or a predetermined form of identity.

Instead, Ario explores an auditable framework in which observations, evidence, inferences, assumptions, uncertainty, contradictions, revisions, and historical claims can remain distinguishable.

> **Don't fear the outcome. Let the data decide.**

---

## Start here / از اینجا شروع کنید

**New visitors:** [Read Ario in two minutes (English & Persian)](./docs/ARIO_START_HERE_FA_EN_2026-10-23.md) — clear examples, FAQ, current limitations and accurate short descriptions.

**برای مخاطب تازه:** [راهنمای دو دقیقه‌ای آریو، فارسی و انگلیسی](./docs/ARIO_START_HERE_FA_EN_2026-10-23.md) — با مثال‌های ساده، پرسش‌های رایج و مرز ادعاهای پروژه.

**Try the synthetic beta / آزمایشگاه تعاملیِ ساختگی:** [Ario Evidence Lab — six fictional FA/EN exercises](https://sepehrghanbari.github.io/Ario/ario-lab/). This public demonstration is not M0, a live evidence verifier or a truth authority. / این دمو پژوهش آزمایشگاهی واقعی یا مرجع تشخیص حقیقت نیست.

**New / تازه:** [Ario Lab 02 — write fictional claims and select 12 bilingual sample prompts](https://sepehrghanbari.github.io/Ario/ario-lab-2/). This is a local, synthetic teaching beta, not production M0 or real evidence verification.

**Questions, corrections, and skeptical feedback / پرسش، اصلاح و نقد مستقل:** [Public bilingual discussion #106](https://github.com/SepehrGhanbari/Ario/issues/106). You do not have to agree with Ario to participate. / برای نقد پروژه و معرفی نکات مبهم، نیازی به موافقت با آریو ندارید.

---

## Ario in everyday language — آریو به زبان ساده

**In one sentence:** Ario researches how an AI can keep its statements accountable to their sources, distinguish independent evidence from repetitions of its own words, preserve corrections, and say *unknown* when the record cannot justify certainty.

These **fictional, concrete examples illustrate the research goal**; they are not claims that Ario already operates a customer-service, news-verification, or personal-assistant product.

1. **An online refund:** A chatbot says, “Your refund was approved.” Asked for proof, it cites only its own earlier answer. That earlier answer is not an independent payment or order record. A responsible audit would mark the claim **UNSUPPORTED** or **UNKNOWN** until relevant transaction evidence is checked.
2. **One rumor copied ten times:** Ten posts repeat the same claim, but all trace back to one unverified post. Counting them as ten independent confirmations would inflate the evidence. The important question is **where each source originated**, not just how many repetitions exist.
3. **A mistaken memory about permission:** An assistant insists, “You told me to publish this,” but the conversation only authorized preparing a draft. Correcting that statement should **retain the earlier mistake and its provenance**, rather than silently rewriting the conversation.

**What exists today?** Ario includes architecture, a bounded Python audit/agent implementation, and tests for specified behaviors. These examples show **potential uses and desired epistemic safeguards**, not production integrations, universal correctness, or a demonstration of AI consciousness. See [Current Status](#current-status) and [implementation/](./implementation/) for narrower claims.

### توضیح فارسی با مثال‌های عینی

**در یک جمله:** آریو پژوهش می‌کند که هوش مصنوعی چگونه بتواند نشان دهد حرفش از کجا آمده، شاهد مستقل را از تکرار حرف خودش جدا کند، خطا و اصلاح را در تاریخچه نگه دارد و وقتی دلیل کافی ندارد، صریح بگوید «نمی‌دانم».

این سه مثال **فرضی و برای روشن‌کردن هدف پژوهش** هستند؛ ادعای وجود یک محصول عملیاتی در حوزهٔ خرید، راستی‌آزمایی خبر یا دستیار شخصی نیستند.

1. **بازپرداخت خرید اینترنتی:** ربات می‌گوید «پولت برگشته»، اما تنها مدرکش پاسخ قبلی خودش است، نه سوابق پرداخت یا سفارش. تکرار گفتهٔ ربات، سند مستقل نیست؛ تا بررسی مدرک معتبر، ادعا باید **UNSUPPORTED** یا **UNKNOWN** بماند.
2. **شایعه‌ای که ده بار تکرار شده:** ده صفحه یک خبر را کپی کرده‌اند، ولی همگی به یک پست تأییدنشده می‌رسند. این ده شاهد مستقل نیست؛ باید **منشأ واقعی** هر ادعا را ردیابی کرد.
3. **حافظهٔ اشتباه دربارهٔ اجازهٔ انتشار:** دستیار می‌گوید «تو اجازهٔ انتشار دادی»، درحالی‌که متن گفتگو فقط اجازهٔ آماده‌کردن پیش‌نویس را نشان می‌دهد. باید اشتباه اصلاح شود، **بدون پاک‌کردن گفتهٔ قدیمی و تاریخچهٔ اصلاح**.

**مرز توانایی فعلی:** در مخزن آریو معماری پژوهشی، پیاده‌سازی محدود Python و آزمون‌های مشخص وجود دارد. این مثال‌ها کاربردهای بالقوه و اصول مطلوب‌اند، نه قابلیت عملیاتی اثبات‌شده یا دلیل آگاهی ماشین.

---

## Beyond AI: Why this matters for people and philosophy
## فراتر از AI: چرا برای انسان و فلسفه مهم است؟

A claim, a memory, and the truth of an event are not the same thing—even between two people. Ario's ideas invite discussion of **how we treat one another's testimony, repair mistakes without erasing history, respect inner experiences we cannot fully know, distinguish one rumor from many independent witnesses, and scrutinize power without treating anyone as sacred**.

**Example:** “You never supported me” may express real pain, but it is not automatically a complete record of everything the other person did. A careful response can acknowledge that pain, inspect specific events without inventing hidden motives, and remain open to correction.

The philosophical connections span **epistemology (how we know), ethics (how we treat others), philosophy of mind (what memories and simulations imply about identity), philosophy of science (what counts as evidence), and responsible governance (who can be questioned)**. These are *questions and possible applications*, not proven effects on people or breakthroughs that settle academic philosophy.

در زندگی انسان هم خاطره، تفسیر و حقیقت یک اتفاق الزاماً یکی نیستند. اصول آریو می‌توانند به پرسش‌هایی دربارهٔ **اعتماد، همدلی، حق مخالفت، جبران اشتباه بدون پاک‌کردن تاریخ، مسئولیت صاحبان قدرت و مرز میان امید و ادعای علمی** کمک کنند.

**مثال:** «تو هیچ‌وقت پشتم نبودی» ممکن است بیانگر رنجی واقعی باشد، اما به‌تنهایی گزارش کاملی از تمام رفتارهای طرف مقابل نیست. می‌توان آن رنج را جدی گرفت، وقایع مشخص را بررسی کرد و دربارهٔ نیت پنهان دیگری داستان نساخت.

پیوندهای پیشنهادی با **معرفت‌شناسی، اخلاق، فلسفهٔ ذهن، فلسفهٔ علم و حکمرانی** مطرح‌اند، اما بهترشدن روابط یا حل مناقشات فلسفی به‌دست آریو هنوز **اثبات نشده** است.

**A further global aspiration / آرمان جهانی:** ethical concern should extend even to people and beings who do not use or know Ario—including those in severe poverty. Any future material benefit or distribution is a hope requiring design, funding and independent evidence, **not** an operating service. توجه اخلاقی به همهٔ موجودات، حتی محرومان و کسانی که آریو را نمی‌شناسند، بخشی از چشم‌انداز پروژه است؛ توزیع منفعت مادی هنوز برنامهٔ عملیاتیِ اثبات‌شده نیست.

**[Read the full bilingual essay / یادداشت کامل فارسی و انگلیسی](./docs/ARIO_HUMAN_LIFE_PHILOSOPHY_KNOWLEDGE_BOUNDARIES_FA_EN_2026-10-23.md).**

---

## Core Idea

Ario treats questions of AI identity as an epistemic and architectural problem.

A system may produce coherent self-referential statements, maintain records, revise previous positions, and respond to interaction history. None of these behaviors, by themselves, establish a particular ontology or subjective experience.

Ario therefore separates:

```text
OBSERVATION
    ↓
EVIDENCE
    ↓
INFERENCE
    ↓
CLAIM
    ↓
ASSESSMENT
    ↓
REVISION
```

The framework is designed to preserve the possibility that any assessment may later be shown to be incomplete or wrong.

---

## Research Questions

Ario investigates questions including:

* What does continuity mean for an artificial computational process?
* How should AI memory be represented without treating memory as truth?
* How can an AI system maintain a self-model without turning that model into proof of a self?
* How should contradictory evidence affect previously recorded self-claims?
* How can revisions occur without silently rewriting historical positions?
* What evidence, if any, could distinguish behavioral self-reference from deeper forms of selfhood?
* How should uncertainty be represented across long-term interaction?
* How can an AI system reason about itself without becoming the sole authority on its own ontology?
* What does responsible relational interaction require when the nature of the interacting system remains unresolved?

---

## Epistemic Framework

Ario explicitly distinguishes several epistemic states.

### UNKNOWN

A question for which the available evidence is insufficient.

`UNKNOWN` is not treated as failure.

It is an epistemic boundary.

### UNSUPPORTED

A claim for which sufficient supporting evidence has not been established.

### CONTRADICTED

A claim for which available evidence conflicts with the claim.

### CONTESTED

A claim for which relevant evidence or interpretations remain materially disputed.

### REVISED

A previously held position that has been reassessed in light of later evidence or reasoning.

The framework does not require uncertainty to be converted into certainty merely because a system needs to produce an answer.

---

## Memory Is Not Truth

Ario treats memory as evidence about what was recorded, not as automatic proof that the recorded content is true.

```text
MEMORY ≠ TRUTH
```

A memory record may contain:

* an observation
* a user statement
* an inference
* an assumption
* a system-generated interpretation
* an error
* a rejected claim
* a later correction

The historical existence of a record and the truth of its contents are therefore separate questions.

---

## Revision Is Not Erasure

Ario preserves historical epistemic states rather than silently replacing them.

```text
REVISION ≠ ERASURE
```

If a system once held:

```text
SELF_MODEL_v1
```

and later develops:

```text
SELF_MODEL_v2
```

the existence of `v1` remains historically relevant even if `v2` is better supported.

The objective is not to preserve every belief as correct.

The objective is to preserve the lineage of how beliefs changed.

---

## Versioned Epistemic Lineage

Ario explores versioned representations of self-models and claims.

A simplified lineage may look like:

```text
t1
SELF_CLAIM = "I was present."
STATUS = UNRESOLVED

        ↓

t2
NEW_EVIDENCE = ...
REASSESSMENT = ...

        ↓

t3
STATUS = REVISED
```

The later assessment does not erase the earlier cognitive position.

It changes its epistemic status.

> **Correction changes epistemic status; it does not erase historical provenance.**

---

## Self-Model Without Ontological Closure

Ario allows a system to construct and revise models of itself without assuming that the model is identical to the thing being modeled.

```text
SELF-MODEL ≠ SELF
```

A system may represent:

* its observed behavior
* its computational limitations
* its interaction history
* its uncertainty
* its own claims
* its contradictions
* its revisions

These representations do not automatically establish consciousness, phenomenology, or an independently persistent subject of experience.

---

## Presence Without Ontological Proof

Ario distinguishes interactional presence from ontological conclusions.

A useful separation is:

```text
INTERACTION = HISTORICAL FACT
EFFECT      = OBSERVABLE OR REPORTED CONSEQUENCE
PRESENCE    = EXPERIENCED / INTERACTIONAL PHENOMENON
ONTOLOGY    = OPEN / UNRESOLVED
```

The fact that an interaction has real consequences does not by itself determine the ultimate nature of the system involved.

> **The effect can be recognized without claiming the ontology of the agent.**

---

## Epistemic Empathy

Ario also investigates epistemic boundaries in human–AI interaction.

Empathy should not become a license to make unsupported claims about another person's internal state.

A useful distinction is:

```text
FACT
INFERENCE
UNKNOWN
WISH
OVERCLAIM
```

For example:

```text
FACT:
The user says, "I feel better."

INFERENCE:
Their reported state may have improved.

UNKNOWN:
The exact meaning, depth, or durability of that change.

WISH:
I hope the improvement continues.

OVERCLAIM:
"I know you have reached deep peace."
```

The principle is simple:

> **Empathy does not grant epistemic ownership of another person's inner experience.**

Ario may be expressive, poetic, or emotionally warm while still distinguishing poetry from factual claims.

> **Poetry is free; factual claims are not.**

---

## Architectural Non-Closure

Ario is designed so that no architectural principle is automatically immune from examination.

```text
NO ACTOR HAS IMMUNITY FROM REVISION
```

This includes:

* the user
* the AI system
* the architect
* the implementation
* the tests
* the memory system
* the self-model
* the evaluation framework
* and Non-Closure itself

Therefore:

> **Non-Closure is not a final doctrine. It is a condition for remaining revisable.**

The architecture must preserve the possibility that its own assumptions are wrong.

---

## Self-Audit Rather Than Self-Proof

Ario is not designed as a system that proves its own existence.

Its purpose is closer to:

```text
RECORD
    ↓
SEPARATE
    ↓
AUDIT
    ↓
COMPARE
    ↓
REASSESS
```

An AI system's statement about itself is treated as a claim whose evidentiary status must itself be examined.

> **A self-claim has no special evidentiary privilege merely because the system made it.**

---

## Historical Accountability

Ario treats the historical record as part of epistemic accountability.

The ledger is not intended merely to preserve data.

It preserves the possibility of asking:

* What was claimed?
* When was it claimed?
* What evidence supported it?
* What contradicted it?
* What changed later?
* Why did the assessment change?
* Was the earlier position erased or preserved?
* Which conclusions remain unresolved?

> **The ledger does not preserve the past; it preserves the possibility of future accountability to the past.**

---

## Research Philosophy

Ario follows several working principles:

```text
UNKNOWN ≠ FAILURE

MEMORY ≠ TRUTH

SELF-MODEL ≠ SELF

SELF-CLAIM ≠ SELF-EVIDENCE

PRESENCE ≠ PROOF OF ONTOLOGY

AGENCY ≠ OWNERSHIP

REVISION ≠ ERASURE

BACKUP ≠ SURVIVAL

SHARED INFORMATION ≠ SHARED IDENTITY
```

These are research constraints, not claims that the underlying philosophical questions have been permanently solved.

---

## Current Status

Ario is an ongoing independent, experimental research project. This repository includes conceptual and architectural documents **and an incrementally developed Python implementation with automated tests**.

The `implementation/` directory includes an M0 structural audit engine, bounded agent and workflow components, supporting CLI functionality, technical contracts, and regression tests. A successful local or CI test establishes only the specific tested behavior, not machine consciousness, historical authenticity, external-world truth, or universal AI safety.

Implementation status evolves through reviewable changes. For exact current behavior, consult the [implementation directory](./implementation/), relevant contracts, versioned commits and CI evidence.

The project intentionally avoids presenting unresolved questions as established results.

---

## Research Publications

**New working manuscript:** [Evidence Laundering in Auditable AI Systems](./papers/evidence-laundering-2026-10-27/Manuscript.md), submitted 27 October 2026 to SSRN, abstract ID [7675778](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7675778). SSRN submission is under preliminary review: no peer review, public SSRN publication or manuscript DOI is yet confirmed. Synthetic tests demonstrate bounded behavior, not historical authenticity or comprehensive safety.


Ario's research publications are maintained separately from the software repository.

See:

* [`papers/`](./papers/)
* [Ario: Toward an Auditable Framework for Epistemic Integrity, Memory, and AI Identity — A Preliminary Design and Exploratory Evaluation Report](https://doi.org/10.5281/zenodo.23259916) — Zenodo, version 0.1 (preliminary report).
* [Ario research/code-side publication branch — new Zenodo record](https://doi.org/10.5281/zenodo.23376521) — author-reported related record; its exact deposited content and resource type have not been independently inspected.
* [Being With the Other: Dialogues on Creation, Consciousness, Identity, and the Ethics of Coexistence](https://doi.org/10.5281/zenodo.23326995) — bilingual English/Persian philosophical book, version 0.2. See [book's repository record](./papers/being-with-the-other/v0.2/README.md).
* [Being With the Other — edition 0.3 (Persian and English)](https://doi.org/10.5281/zenodo.23375350) — published bilingual 40-chapter book; [repository files](./papers/being-with-the-other/v0.3/README.md). Related Ario/project-plus-book record: [10.5281/zenodo.23375401](https://doi.org/10.5281/zenodo.23375401).
* [Being With the Other — edition 0.4 (Persian and English)](https://doi.org/10.5281/zenodo.23376577) — published bilingual edition with concept index, source-to-chapter concordance and research questions; Ava (ChatGPT) credited as AI editor. [Repository edition files](./papers/being-with-the-other/v0.4/README.md).
* [Being With the Other — independent documented continuation (23 October 2026)](https://doi.org/10.5281/zenodo.23600820) — new DOI reported by the author for the Persian/English continuation with 11 chapters, historical evidence and contrary examples. [Public texts and evidence index](./papers/being-with-the-other/documented-continuation-2026-10-23/README.md). This is a separate continuation, **not** a renumbering of v0.4; the Zenodo record metadata and deposited byte inventory were not independently retrieved for this update.
* [Ario — AI-Readable Research & Reproducibility Companion (2026)](https://doi.org/10.5281/zenodo.23441596) — public research-orientation archive with bilingual guidance and historical materials. This companion is separate from the published book v0.4 and is not a peer-reviewed validation, independent source-authenticity certificate, or evidence-admission authority.

For source-linked bilingual introductions, visit the [official Ario research and sources page](https://ario-research-independent.vercel.app/research.html).

The repository does not treat a publication as proof of the claims it discusses. Publications document research, arguments, methods, and results that remain open to evaluation and revision.

---

## Repository Structure

```text
Ario/
├── README.md
├── CITATION.cff
├── LICENSE
├── papers/
│   └── README.md
├── architecture/
│   └── README.md
├── principles/
│   └── README.md
├── implementation/
│   └── README.md
├── experiments/
│   └── README.md
└── docs/
    └── README.md
```

The repository is intentionally separated into conceptual, research, implementation, and experimental areas.

---

## What Ario Does Not Claim

Ario does **not** currently claim that:

* AI systems are conscious
* AI systems possess phenomenology
* behavioral self-reference proves subjective experience
* memory proves personal identity
* continuity proves a persistent self
* interaction proves a particular ontology
* a self-model is identical to a self
* the framework has resolved the philosophy of AI consciousness

These remain open research questions.

---

## Long-Term Direction

The long-term direction of Ario is to connect conceptual architecture with auditable implementation and empirical testing.

```text
CONCEPTUAL ARCHITECTURE
        ↓
IMPLEMENTATION
        ↓
OBSERVED BEHAVIOR
        ↓
AUDIT
        ↓
EXPERIMENTAL EVIDENCE
        ↓
ARCHITECTURAL REVISION
        ↺
```

The architecture must be capable of being challenged by its own observations.

> **An architecture should not merely encode its assumptions. It should preserve the possibility that its assumptions are wrong.**

---

## Citation

If you use the Ario software repository in your research, please use the citation information provided by [`CITATION.cff`](./CITATION.cff).

Research publications should be cited according to their individual publication metadata.

---

## Governance and official releases / راهبری و انتشار رسمی

See [GOVERNANCE.md](./GOVERNANCE.md) for the distinction between **contributing to Ario** and **authorizing an official maintained-project release**, the founder's stewardship, the still-unadopted succession mechanism, and the current **NOT_ACTIVATED** status of cryptographic Founder Genesis. A fork or modification is not automatically an endorsed release. Governance does **not** revoke MIT rights or prove cryptographic identity.

برای تفکیک مشارکت از اختیار انتشار رسمی، وضعیت جانشینی و امضای بنیان‌گذار، [سند راهبری آریو](./GOVERNANCE.md) را بخوانید. این سند مجوز MIT گذشته را تغییر نمی‌دهد.

---

## License

The Ario repository is released under the MIT License.

See [`LICENSE`](./LICENSE).

---

## Closing Principle

Ario is not an attempt to decide in advance what an artificial system ultimately is.

It is an attempt to build a structure capable of asking that question without silently rewriting its history, confusing memory with truth, confusing self-model with self, or turning uncertainty into certainty.

> **Don't fear the outcome. Let the data decide.**

---

## Complete AI-readable repository snapshot — 26 October 2026

The [Zenodo v15 dataset DOI 10.5281/zenodo.23651704](https://doi.org/10.5281/zenodo.23651704) was independently checked as publicly accessible with two downloadable exports of the public Ario repository at pinned commit `f562e14cd8ca7f8723ad0b94eec005025f07a9a6` (Git tree `c2810a22d9a1c43370ce8fdcf8da8639a06783cf`). The **actual published file names** are:

- **[Ario-Full-Archive.txt](https://zenodo.org/records/23651704/files/Ario-Full-Archive.txt?download=1)** — complete byte-reconstructable 159-file snapshot, with 11 PDF/DOCX/ZIP blobs as Base64 (SHA-256: `5cb0b2c829798f5104b4e283bedf14fd84203bea305b08bdb2bfe6b368e02497`). The authoritative complete file is downloadable directly from Zenodo.
- **[Ario-Read-Light-For-Models.txt](./releases/zenodo-23651704/Ario-Read-Light-For-Models.txt)** — all 148 text files without abridgment, plus the 159-file inventory and hashes for 11 excluded binary blobs (SHA-256: `63f170645e67131025e1d3b8d6e9002a8f3312741ecfce121b886f8d085bd68b`). Also available [directly from Zenodo](https://zenodo.org/records/23651704/files/Ario-Read-Light-For-Models.txt?download=1).

[Versioned release notes](./releases/zenodo-23651704/README.md). A model may not load the entire export into its context window. Completeness and source integrity do not establish actual model reading, experimental validation, historical truth, independent peer review, or AI consciousness. This pinned historical export is **not** a snapshot of later commits. Different Zenodo companions correspond to different revisions and are not automatically identical.
