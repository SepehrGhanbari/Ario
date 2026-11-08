# External review proposal — 8 November 2026

**Status of this file:** proposal only. It does not change the M0 runtime, rename any verdict, archive any document, or narrow an existing claim by itself. Nothing here is an official Ario release. Merge only after independent comment.

**وضعیت این فایل:** فقط پیشنهاد است. رفتار M0، نام حکم‌ها، جای سندها و ادعاهای فعلی را عوض نمی‌کند. انتشار رسمی نیست. ادغام فقط بعد از نقد مستقل.

This note records five changes discussed as a way to keep the public claim no wider than what the tests actually break.

---

## 1. A status table that only lists what a test can fail

Suggested placement, if accepted later: near the top of `README.md`, above the everyday-language examples. Wording below is a draft, not a replacement of the current "What Ario Does Not Claim" section.

| Capability | What current code does | What it does not establish |
|---|---|---|
| M0 JSON audit (`implementation/ario_cli.py`, `implementation/core/audit_engine.py`) | Parses a typed request and runs a deterministic structural audit. A successful process exit means the request was parsed and the audit ran. | That the verdict is true, that content is authentic, or that a PASS-like result is a truth judgment. |
| Ledger observation (`ledger_observation_adapter.py`, `ledger_audit_bridge.py`) | Reads nominated ledger bytes and compares a manifest to a fresh bounded read. | Historical truth, custody, or that the bytes were not chosen by the same party that wrote the claim. |
| Candidate dossier / admission preflight | Describes what current ledger bytes report, or screens an envelope for some explicit contradictions. Docstrings already say these paths do not grant admission. | Evidence admission, reviewer authority, or an authorized recommendation. |
| Witness, checkpoint, and ethics-dispatch experiments | Laboratory comparisons against a caller-supplied oracle or a local state model. Several modules state that they have no network, signer, clock, or M0 authority. | Independent historical witness, signer identity, or a real provider request. |
| Ava dialogue records | Preserved transcripts and notes. | A controlled experiment or a result about identity or consciousness. |

Persian gloss: موفقیت اجرا یعنی درستی محتوا نیست. مشاهدهٔ لجر یعنی صحت تاریخی نیست. آزمایش سنتتیک استقلال شاهد را اندازه نمی‌گیرد.

Any sentence that cannot sit in this table should stay out of the first screen of the README.

## 2. One reproduction path

Already documented in `docs/REPRODUCE_M0.md`. The proposal is to make this the only "start here if you want to check the code" path, and to pin the expected output next to it:

```bash
python -B implementation/m0_reproducibility_demo.py
python -m unittest discover -s implementation/tests
```

Target environment already stated by the demo module: Python 3.13, run from the repository root. A future commit, not this one, should paste the exact stdout or a hash of the demo result so a stranger can see a mismatch without asking the author.

If someone other than the author cannot get that output, auditability is still a claim rather than a property.

## 3. Three public "try to break this" cases

These are proposed issue bodies, not issues opened by this pull request. Comment here if the cases are wrong, too weak, or already covered.

1. **Schema boundary.** Supply one JSON audit request that the schema rejects but a careful reader thinks must be accepted, and one that the schema accepts but must be rejected. The interesting result is a disagreement about the boundary, not a green test.
2. **Ledger prefix.** Two JSONL ledgers share an identical prefix and diverge afterward. State what the observation adapter is allowed to say about each, and what it must not say about the shared prefix.
3. **Structural success, false content.** Construct an input on which the structural audit completes while the artifacts' content is false by the fixture's own declaration. The expected public wording is that completion is not truth. If the current result string can be read as a truth judgment, that is the finding.

Until someone who did not write the tests attempts these, there is no external review. Stars and the author's own regression suite do not substitute for that.

## 4. Documents should follow a failing test

Proposed rule for later, not applied in this branch:

- A new contract enters `main` only when a corresponding test already fails without the behavior it describes.
- Successive dialogue-protocol drafts (`V0_2` through `V0_2_4` and similar) keep one current file; superseded drafts move to an archive path in a separate, reviewed change.
- `docs/ai-readable-snapshots/Ario_READ.txt` (about 2.8 MB) and the long engineering log stay out of the default reading path. A release asset is a better place than the main tree. This pull request does not move them.

## 5. Keep the authoritative core narrow

`ario_cli` plus `core/audit_engine` are the only paths this proposal would call citable. Agent, planner, and workflow stay labeled non-authorizing and stay out of the primary demo until they are not.

Naming suggestion, deliberately **not** implemented here: if a result token can be mistaken for "the claim is true," prefer a token such as `STRUCTURAL_MATCH`. Renaming is a behavior change and needs its own tests and its own pull request. Modules whose docstrings say they must not grant admission should not return a word that looks like a verdict.

Witness comparisons against an oracle supplied by the same laboratory controller do not measure independence. Either a later experiment uses a witness outside the author's process (second repository, second person, separate signature), or the experiment title says, in the same sentence as the method, that independence is not what is being measured. The middle state — strong wording, laboratory assumption — is the failure mode this note is trying to keep visible.

## What this pull request asks reviewers to do

- Say which row of the table over-claims or under-claims.
- Say whether the three break-cases are the right ones.
- Do not treat a merge of this file as acceptance of the renaming, the archive move, or a new official status. Those stay separate changes.

## چه چیزی عمداً انجام نشده است

- هیچ فایل پایتون عوض نشده.
- `README.md` عوض نشده.
- سندی حذف یا جابه‌جا نشده.
- ایشوی جدید باز نشده.
- `main` دست نخورده.
