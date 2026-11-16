## What changed / چه چیزی عوض شد
<!-- Describe the exact diff and affected paths; link the issue or claim. -->

## Why / چرا
<!-- State the observed defect or hypothesis, not just the proposed fix. -->

## Claims touched / ادعاهای تحت تأثیر
- [ ] No research/paper/runtime claim changed
- [ ] Claims changed: file, exact line/quote, and evidence

## Scope and reproducibility / محدوده و بازتولید
- Head SHA / commit:
- New, changed, or removed paths:
- Python version / OS / dependency version:
- [ ] The entire `implementation/tests/` directory was executed in an isolated, secret-free environment
- [ ] Full suite NOT run — reason and exact subset:
- Commands and result counts (passed / failed / skipped / subtests):

## Tests and falsifiers / آزمون نقض
- [ ] A realistic faulty mutation turns at least one relevant new test RED (paste the mutation and observed failure)
- [ ] New tests have no tautological assertions; identify the independently observed outcome
- [ ] Not applicable (docs only), or explain why:

## Verdict / آیا PASS/FAIL/UNKNOWN تغییر می‌کند؟
- [ ] No — paired original/candidate evidence and tested bounds:
- [ ] Yes — exact contract decision, approval and regression evidence:
- [ ] UNKNOWN / NOT_EVALUATED — what blocks a supported conclusion:

## Independent review and evidence provenance
- Reviewer name/model and version, if known:
- [ ] No independent approval claimed merely from a model comment, CI, or author-run mutation check
- [ ] No Founder/Genesis signer activation, trust promotion or security guarantee claimed without separate authority

## Not covered / چه چیزی بررسی نشد؟
<!-- Required prose: untouched modules, OSes, models, threat assumptions, inputs, or missing tests. Write UNKNOWN/NOT_RUN explicitly. -->

## Preservation / حفظ سابقه
- [ ] Existing evidence/history kept; REVISION ≠ ERASURE
- [ ] Scope and backup/rollback recorded where applicable

---
Automated reviewers: **COMMENT ONLY**, never approve, push, merge, or close. Read [REVIEWER_INSTRUCTIONS.md](../REVIEWER_INSTRUCTIONS.md). Permissions must be limited independently of this prose.
