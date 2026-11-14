# Deferred proposal: verifiable, model-friendly reading shards (not activated)

**Recorded:** 15 November 2026  
**Status:** PROPOSED / HOLD — documentation only; no shards, scripts, publication or changes to existing releases are authorized by this record.  
**Scope:** public Ario research corpus, book, papers, experiments, tests and source; **not** a new model capability or scientific result.

## Why record this?

The verified release dated 14 November 2026 is a single AI-readable TXT plus an original-file ZIP, pinned to Git source commit `a39ac06e69c1b5115bca2016698556730bf920cd`. Its TXT has 230 complete original UTF-8 file bodies, including the selectable-text extractions of the English and Persian *Being With the Other* PDF editions, papers and public experiment/test files. The ZIP preserves original illustrated PDFs and other binary assets. See `releases/complete-research-2026-11-14-a39ac06e/` and DOI https://doi.org/10.5281/zenodo.24230572.

**Source completeness is not model ingestion.** When an assistant receives only a truncated portion of the large TXT, seeing the file index does not mean it has examined each file body. Do not falsely diagnose such truncation as missing source content; do not falsely claim a review.

### Recorded example: Gemini access report (user-supplied, not independently verified)

A Gemini interaction reported seeing the 230-path index and the full 145-page English book text layer, while receiving the Persian book text only through part of page 89/154 and not the full bodies of files 003–230 in that turn. This is **Gemini's self-report, not independently demonstrated reading or a persistent fact about its access in later turns**. Earlier attempts to give it a ZIP yielded a corrupt/garbled representation, while TXT exposed readable material. Other models/tools or later turns may have different access. The report is evidence of a *possible intake bottleneck*, not evidence that the public TXT or ZIP was defective.

## Current action — do not generate another corpus yet

1. Retain the immutable, dated TXT/ZIP and their SHA-256 manifests as the reference release.
2. Ask the reviewing model to state exactly which actual source text it accessed, with original path, chapter/page or section, and verifiable excerpts. Do not count the initial index as full access.
3. Continue the review in bounded batches or using supported file-range retrieval, if available to that model. Maintain an explicit progress ledger: `NOT_ACCESSED`, `PARTIALLY_ACCESSED`, `FULL_TEXT_ACCESSED`, `REVIEWED_WITH_EVIDENCE`. A self-reported status is not independent proof.
4. If access is truncated, use smaller direct excerpts or files and resume from the **last verified page/chapter/file boundary**; do not skip source material or fabricate analysis.
5. Distinguish *access verification*, *content comprehension*, *critical review*, and *independent experimental replication*; they are different claims.

## Possible future implementation — only after an explicit decision

Create a **derived reading edition** whose subdivisions are easy to inspect in tools with limited context windows. This is optional and **does not supersede or alter the original TXT/ZIP**.

- Book: separately navigable English and Persian chapter/page-range sections with genuine source page references; never assume a one-to-one chapter correspondence between languages from a partially parsed heading list. Verify chapter counts and boundaries against **both PDFs** before labeling.
- Research papers: each complete paper as a separate text file with DOI, edition, language and source-path metadata; keep source text verbatim and record extraction method.
- Experiments, test files and code: group by project and dependency without deleting unique historical evidence; retain the raw logs, protocols, negative results and contradictory observations, not just summaries.
- Every output shard: `source_commit`, `source_path`, source byte range/page range, total shards, ordered shard index, UTF-8 bytes, `SHA256` of original and shard, and extraction or transformation notes.
- Strict reproducibility: each original source text can be reconstructed byte-for-byte from ordered shards (or noncontiguous excerpts must be explicitly marked as such). Test complete source coverage, no gaps, overlaps or silent normalization, no accidental duplicate content, and stable links back to original files.
- Preserve original published PDFs separately for visual pages, figures and diagrams. The TXT has only selectable text, not the illustrations.
- Include an explicit per-shard index and a separate `READER_ACCESS_LEDGER` template for model self-reports, with exact source excerpts and uncertainty.
- Before any public replacement, compare old and new coverage manifests and publish a new *dated* release and new hashes, leaving historical archives untouched. No implied Zenodo revision or release automation at this stage.

## Acceptance criteria for a future work item

The work may be described as an improved *delivery format* only when tests show complete deterministic coverage of the chosen pinned corpus, reconstructability of its original text, original-byte hashes, immutable historical artifacts and no loss of independent research or experimental evidence. This does **not** prove any model has read or understood every shard.

## خلاصهٔ فارسی

این فقط ثبت یک ایده برای **آینده** است: اگر پنجرهٔ متن مدل‌ها برای آرشیو یکپارچهٔ آریو کافی نبود، بعدها کتاب را بر اساس فصل/صفحه، مقالات را به‌صورت مستقل و آزمایش‌ها را همراه مدارکشان در بسته‌های کوچک‌تر و هش‌دار تهیه کنیم. **فعلاً هیچ فایل اصلی تغییر یا تقسیم نمی‌شود.** گزارش جمینی در مورد دریافت متن، یک اظهار خودِ مدل است و به‌تنهایی نه اثبات مطالعهٔ کامل است و نه نشانهٔ ناقص‌بودن آرشیو. اصلِ آرشیو، شواهد تاریخی و نتیجه‌های منفی باید بدون حذف و بازنویسی باقی بمانند.
