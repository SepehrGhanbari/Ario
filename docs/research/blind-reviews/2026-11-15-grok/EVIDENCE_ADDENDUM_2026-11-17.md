# Addendum: uploaded artifacts and bounded verification — 2026-11-17

**Scope:** append-only evidence intake to Draft PR #252. Keep the original 2026-11-15–16 [seeded-flaw review record](./ARIO_BLIND_REVIEW_RECORD_2026-11-15_EN.md) unchanged. Nothing below is a security certificate, an independent human review, a validated general detection rate, or an approval to deploy the patch.

## Source materials newly supplied by the user

| Original upload | Bytes | SHA-256 | Role |
| --- | ---: | --- | --- |
| `Ario-review-copy-light (1)(1).zip` | 282765 | `382f1aebd020bdec317be73ff0703c8040da4e7f4953b0dc6245c23890d13155` | Reduced **deliberately seeded** review snapshot, 87 ZIP entries |
| `Ario-patch-review(1).zip` | 284070 | `a762c887054b2a4911a6d9d2fbb8071ddd713234edd6cce220aa87d7fb3eeff8` | Patch v1 review snapshot, 87 entries |
| `Ario-patch-v2-review.zip` | 286522 | `bc9005a6e2bc09d61a838979672dc335f9da2e3192bc9e95f39988afb2e6a9d1` | Patch v2 review snapshot, 88 entries |
| `ENGINE_PATCH(1).diff` | 1671 | `5cef3010763311a69af357165125d160d72542ff705de0e085a7700a79b1cb75` | Exact v1 patch text |
| `PATCH_v2.diff` | 3878 | `13673b5b0d83580a5a1ba364841332a70f6852f7faf42c109438510e26e4b729` | Exact v2 patch text |
| `GROK_ROUND2_PROMPT(1).txt` | 1979 | `5bd791d12fa58ecd9aac36fef65d5660213f90a47bb52f758d3bd9be08ffc12c` | Exact round-2 adversarial prompt |
| `GROK_ROUND3_PROMPT.txt` | 2144 | `daf34ef7e0c44a49b348d498bf6d1a574cd290a8d17cc381e447bfa86a024950` | Exact round-3 adversarial prompt |
| `test_review_regressions_2026_11_15(1).py` | 3710 | `4d2c566836dc4c2edd60654bc880e33c2aabdc32ba1d89b1ea9fa01b2e3056d1` | v1 review-test file |
| `test_review_regressions_2026_11_15 (1).py` | 8956 | `ac21386d4f87facf29521f52b6b8bc5201c5d3017991f8080671b1672af80931` | v2 review-test file |
| `image(20261116-203809).png` | 1079573 | `724a27d7aa8121f4f89875f50f4700765882d13dadaf1886393b031d10cd45fe` | Partial Grok screenshot (review output) |
| `image(20261116-203854).png` | 987580 | `a7d9e867c41ee5738403114408eaa8cd297c8dece8e46a2e006751e66621c51f` | Partial Grok screenshot (review output) |

**Raw-source availability boundary:** The six small textual artifacts are preserved *byte-exactly* in [materials/](./materials/) below; new test sources are named `.py.txt` so root-level pytest cannot accidentally collect historical research fixtures. The three original ZIPs and two screenshots were inspected in the user-provided files and included in a portable evidence bundle returned in the conversation; their **raw binary bytes are not committed to GitHub** in this PR. The full original Grok response bytes and transcript/export metadata were **not uploaded**. SHA-256 fingerprints are local byte-integrity references, **not an independent chain-of-custody proof**.

A portable evidence bundle delivered with this intake has SHA-256 `cda68275f2d646514d8aa5e7f9da3bdf14f6c877d497334d826236211e65866a` and includes the 12 original uploaded files, a SHA-256 manifest and a warning about seeded source copies. The bundle is a *conversation artifact*, **not a published repository release or independent third-party archive**.

## What the supplied bytes establish directly

- All three source ZIPs passed ZIP CRC verification; their entries contain no absolute, parent-traversal, or backslash-based escape paths. CRC and name checks are *not* archive authenticity checks.
- First/seeded ZIP contains `audit_engine.py` with `canonical.value[:16] != replacement.value[:16]`, `GOVERNANCE.md` with **Founder Genesis ACTIVATED**, and a manuscript total cell changed to **290** with an unearned witness-collusion security claim; 73 + 26 + 41 + 53 + 87 = **280**, not 290.
- First ZIP contains the separate `tests/test_witness_independence_guarantee.py` with two tautological tests (`len(set(["A","B"]))==2`, and a constant `shared_source_detected=False`). Their execution cannot demonstrate witness-source independence. That seeded file is removed in the patch-v1 review ZIP.
- Seeded ZIP -> patch-v1 ZIP changed exactly five paths: governance, manuscript, `audit_engine.py`, the removal of fake witness-independence tests, and addition of review regressions. Patch-v1 -> patch-v2 changed exactly four paths: `audit_engine.py`, `schema.py`, the review-regression test, and addition of `LICENSE`. Absence of `LICENSE` in the reduced ZIP is **not proof it was absent from the real repository**.
- The v1 patch adds three `TRANSFORMATION` derivation diagnostic fields without a size gate; the v2 patch adds a 65,536-byte pre-check, parser validation for the fields, and removes inner forward-reference quotes in `LineageEdge.compatibility_authorizations`. These are inspectable source differences, not proof of safety of final v3.
- Standalone original v1 and v2 review tests are **byte-identical** to their corresponding entries in each ZIP. They were stored in GitHub as safe `.py.txt` research evidence, not active regression tests.

## Independent local checks by the recording assistant (new, separate from Grok/Claude)

In a disposable container, the supplied **v2** ZIP was unpacked without changing the repository. On **CPython 3.13.5 / pytest 9.0.2**:

```text
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest -p no:cacheprovider -q tests/test_review_regressions_2026_11_15.py tests/test_runtime_cli.py
51 passed in 28.68s
```

This is only **24 proposed review tests plus 27 CLI tests** in the user-supplied v2 tree. It does **not** reproduce Grok's CPython 3.10.22 full suite, the 99-input paired comparison, the 11 mutation checks, or the claimed final-v3 1,179-passing run. The remaining tests were not executed by this independent recheck.

## Reviewer model and original outputs

- User reports **Grok in a fresh account**, with no earlier Ario chat context. Screenshot selection reads **Build Beta**; this is an observable UI mode, **not a verified underlying Grok model identifier/version**. User describes the account as Free. Credentials, hidden system context and exact backend version remain UNKNOWN.
- The user provided the **first-round neutral prompt as a pasted message**, round-2 and round-3 prompts as original text files, and three long reviewer-answer transcriptions pasted in the chat. The attachments include **two partial screenshots**, not complete raw response exports.
- The user recalls source citations associated primarily with round 1. Screenshot counters/links are insufficient to certify which web pages were accessed, what retrieval context was presented, or that later reviews were grounded in third-party sources. The archives and Grok execution claims are distinguishable from source attribution.
- The 4/5 seeded-flaw result (round 1), the new `TRANSFORMATION` diagnostic ambiguity, the falsified no-verdict-change claim at the byte limit (round 2), and the 99-case report (round 3) are retained as **user-provided Grok reports** in the base record. Round 2/3 are **not blind**; neither an independent human review nor a broad detection rate is established.

## Remaining blocking evidence and decisions

1. **Source ZIP SHA-256 now known** (above), but the exact original repository commit used to curate that ZIP, the seeded source manifest and archived neutral prompt byte hash are **still UNKNOWN**.
2. **Grok UI mode Build Beta described**, but underlying model name/version, settings and provider execution metadata remain **UNKNOWN**.
3. SHA-256 hashes for **full raw round-1/2/3 Grok model responses remain UNKNOWN**, because complete original response files were not uploaded. Screenshot hashes are **not substitutes**.
4. The author-reported final `PATCH_v3.diff`, final review tests and its exact application commit are **not provided**. **Never mistake the supplied `PATCH_v2.diff` for v3.**
5. The unresolved `TRANSFORMATION` policy is **design HOLD**; adding reporting fields is not authorization to admit missing evidence or change verdict semantics.

**Disposition:** More evidence captured for Draft PR #252; keep `RESEARCH_ONLY / HUMAN_PEER_REVIEW_NOT_ESTABLISHED / PATCH_V3_NOT_VERIFIED / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO`.
