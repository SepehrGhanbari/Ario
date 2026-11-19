# W1 remote RED → GREEN receipt — 17 November 2026

**Status:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NO PRODUCTION AUTHORITY.

## Initial remote failure (not hidden)

- https://github.com/SepehrGhanbari/Ario/actions/runs/44157654647
- Ubuntu Python 3.11 and 3.13: SUCCESS.
- Windows 2022 Python 3.11 and 3.13: FAILURE at source loader with `SOURCE_SIZE_MISMATCH`; zero tests executed on Windows.
- A Windows checkout LF→CRLF conversion was the supported hypothesis; no exact byte-count was logged, so this is not presented as forensic proof.
- Source-byte pin correctly refused the unexpected image.

## Minimal correction

In `.github/workflows/w1-provenance-research.yml` before `actions/checkout@v4`:

```sh
git config --global core.autocrlf false
```

Commit: `6efa093f75ee9601758308f403cb1886179ac72e`. No modification to TB-003 evaluator, source pin, tests, fixture oracle, signer, trust or main.

## Real remote rerun

- https://github.com/SepehrGhanbari/Ario/actions/runs/44157917211
- Ubuntu Python 3.11 **SUCCESS**
- Ubuntu Python 3.13 **SUCCESS**
- Windows 2022 Python 3.11 **SUCCESS**
- Windows 2022 Python 3.13 **SUCCESS**

All four jobs run the same fifteen **author-built development tests**; the 192 graph-order permutations are NOT independent adversarial samples. Success is not proof of real custodian independence, input authenticity, or general security. Repository-wide regression, reviewer sign-off and other external checks are separately gated. No merge or trust activation authorized.
