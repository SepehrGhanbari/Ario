# W1 GitHub Actions actual RED → GREEN receipt — 17 November 2026

**Context:** Research-only, no operational trust, no production authority. This receipt documents actual CI job outcomes rather than treating a local test as a remote pass.

## Initial remote failure (RED)

- GitHub run: https://github.com/SepehrGhanbari/Ario/actions/runs/44157654647
- On the first research workflow at branch HEAD `16ed001b13b999a313548d80874ca934b9a749b9`, Linux (`ubuntu-latest`) Python 3.11 and 3.13 jobs passed.
- Windows (`windows-2022`) Python 3.11 and 3.13 jobs **failed before any unittest executed**: `ValueError: SOURCE_SIZE_MISMATCH` in `load_pinned_engine()`.
- The observed error is consistent with Windows Git checkout converting line endings before raw-byte pin validation. The exact checked-out byte-count was not printed, so this cause is a supported hypothesis, not a direct forensic observation. The test correctly refused to execute an unrecognized image.

## Narrow correction

- In `.github/workflows/w1-provenance-research.yml` added one step **before** `actions/checkout@v4`:

```sh
git config --global core.autocrlf false
```

- Research workflow commit: `6efa093f75ee9601758308f403cb1886179ac72e`.
- No production code, signer, main branch, research oracle, test expectations, or source pin was changed.

## Repeated remote execution (GREEN)

- GitHub run: https://github.com/SepehrGhanbari/Ario/actions/runs/44157917211
- Ubuntu Python 3.11: **SUCCESS**
- Ubuntu Python 3.13: **SUCCESS**
- Windows 2022 Python 3.11: **SUCCESS**
- Windows 2022 Python 3.13: **SUCCESS**

**Interpretation:** All four CI jobs execute the same 15 development tests, verifying that the pinned engine source can be admitted identically on the listed runner environments with checkout configured to preserve Git blob bytes. This does not establish independent witness authenticity, protocol security, or peer-reviewed empirical validity.

**Separate gates:** Repository-wide regression and Vercel deployment/status checks are separate jobs. Success of this targeted research workflow is *not* an assertion that all PR checks are green, ready to merge, or releaseable.
