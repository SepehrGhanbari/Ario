# External review proposal — 8 November 2026

**Status of this file:** proposal only. It does not change the M0 runtime, rename any verdict, archive any document, or narrow an existing claim by itself. Nothing here is an official Ario release. Merge only after independent comment.

**وضعیت این فایل:** فقط پیشنهاد است. رفتار M0، نام حکم‌ها، جای سندها و ادعاهای فعلی را عوض نمی‌کند. انتشار رسمی نیست. ادغام فقط بعد از نقد مستقل.

This note records five changes discussed as a way to keep the public claim no wider than what the tests actually break.

Revision note, 8 November 2026, after review comments on PR #161: section 2 no longer offers `unittest discover` as the suite. The commands below are copied from `docs/REPRODUCE_M0.md`. This commit still does not execute them or pin an output hash.

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

Already documented in `docs/REPRODUCE_M0.md`. That file is the authority for the commands. Do not replace it with `python -m unittest discover`; the repository tests are pytest tests, and discover will not collect them. Pins named there include Python 3.13, `pytest==9.1.1`, and `cryptography==46.0.4`.

First follow the environment setup in `docs/REPRODUCE_M0.md`, including its pinned dependencies. The commands below use the virtual-environment interpreter defined there: `$PYTHON` on Linux/macOS and `$python` in Windows PowerShell. Do not substitute a system-wide interpreter.

Demo, from the repository root on Linux/macOS:

```bash
"$PYTHON" -B implementation/m0_reproducibility_demo.py
```

Demo, from the repository root on Windows PowerShell:

```powershell
& $python -B implementation/m0_reproducibility_demo.py
```

Regression, from `implementation/` on Linux/macOS:

```bash
"$PYTHON" -B -m pytest -p no:cacheprovider -q tests
```

Windows full suite, also from `implementation/`, because parameterized ids need the extra plugin:

```powershell
& $python -B -m pytest -p no:cacheprovider -p tests.test_m0_reproducibility_demo -q tests
```

A later commit, not this one, should paste the exact stdout or a hash of the demo result for one named Git HEAD, after the command has actually been run. Exit 0 in one environment is not artifact truth.

If someone other than the author cannot get that output, auditability is still a claim rather than a property.

## 3. Three public "try to break this" cases

These are proposed issue bodies, not issues opened by this pull request. Comment here if the cases are wrong, too weak, or already covered.

1. **Schema boundary.** Supply one JSON audit request that the schema rejects but a careful reader thinks must be accepted, and one that the schema accepts but must be rejected. The interesting result is a disagreement about the boundary, not a green test.
2. **Ledger prefix.** Freeze one shared JSONL prefix and two different tails, such that both complete files are valid ledgers (valid newline-terminated event envelopes, within the adapter's bounds). Record the exact Git HEAD and observation-adapter version. Run `observe_ledger` on each frozen file and record each returned `status`, whole-ledger `sha256`, and every `observations[].record_sha256` with its line number; an `UNKNOWN` response is not a successful observation. Independently compute SHA-256 of each complete file's raw bytes and of each raw line (including its newline), and compare them to the adapter's outputs for both the common prefix and the divergent tails. Record discrepancies rather than inferring custody or authenticity: a matching prefix neither proves either tail nor establishes historical truth.
3. **Structural success, false content.** Construct an input on which the structural audit completes while the artifacts' content is false by the fixture's own declaration. Record the exact status string the engine returns, and separately record that the fixture declared the content false. Do not expect a structural checker to discover the falsehood. The finding, if any, is that the status string can be read as a truth judgment.

Until someone who did not write the tests attempts these, there is no external review. Stars and the author's own regression suite do not substitute for that.

## 4. Documents should follow a failing test

Proposed rule for later, not applied in this branch:

- An executable invariant enters `main` only when a corresponding test already fails without the behavior it describes. A philosophical or normative note has no machine oracle; it does not become "noncompliant" for lacking one. It stays labeled as argument, not as an enforced contract.
- Successive dialogue-protocol drafts (`V0_2` through `V0_2_4` and similar) keep one current file. Superseded drafts move only in a separate reviewed change that preserves the original bytes, the old path in the history, and the SHA. Revision is not erasure.
- `docs/ai-readable-snapshots/Ario_READ.txt` (about 2.8 MB) and the long engineering log stay out of the default reading path. A release asset is a better place than the main tree. This pull request does not move them.

## 5. Keep the authoritative core narrow

`ario_cli` plus `core/audit_engine` are the only paths this proposal would call citable. Agent, planner, and workflow stay labeled non-authorizing and stay out of the primary demo until they are not.

Naming suggestion, deliberately **not** implemented here: if a result token can be mistaken for "the claim is true," prefer a token such as `STRUCTURAL_MATCH`. Renaming is a behavior change and needs its own tests and its own pull request. Modules whose docstrings say they must not grant admission should not return a word that looks like a verdict.

Witness comparisons against an oracle supplied or controlled by the same laboratory controller do not measure independence. A later experiment may claim to *test* independence only if its method documents who independently controls the source observations **and** the reference oracle, what prevents the author from modifying either, and how separate custody and failure/compromise are checked. A second repository, person, or signature alone does not establish those conditions. If independent source-and-oracle control cannot be shown, the experiment title **and** method must explicitly say `independence NOT MEASURED`. The failure mode to avoid is strong independence wording resting on a shared-control laboratory assumption.

## What this pull request asks reviewers to do

- Say which row of the table over-claims or under-claims.
- Say whether the three break-cases are the right ones.
- Do not treat a merge of this file as acceptance of the renaming, the archive move, or a new official status. Those stay separate changes.

## چه چیزی عمداً انجام نشده است

- هیچ فایل پایتون عوض نشده.
- `README.md` عوض نشده.
- سندی حذف یا جابه‌جا نشده.
- ایشوی جدید باز نشده.
- دستورها اینجا اجرا نشده‌اند و هش خروجی ثبت نشده.
- `main` دست نخورده.
