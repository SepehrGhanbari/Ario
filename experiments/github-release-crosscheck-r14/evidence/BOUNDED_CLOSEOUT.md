# Ario GitHub release cross-check — R1.4 bounded closeout

Date: 2026-11-24
Disposition: PASS_BOUNDED / RESEARCH_ONLY / READY_FOR_SEPARATE_OWNER_ADMISSION
Related draft: https://github.com/SepehrGhanbari/Ario/pull/323

## Evidence and identity
Reviewed the user-supplied Windows final-validation log. This is review of recorded execution, not an independently repeated Windows run or an authenticated attestation of the log.
- Log SHA-256: `332a106fb61372392eaeaa58cc8e05253a0de5fe8730c8dc7407489ae5797e8b`
- Reported review ZIP SHA-256: `b94abb906995f807515b968e816dd0a4661c265d59e696277c3fda723ce78491`
- Exact reported candidate SHA-256: `fac354c46e8fc8ce68edf6202980aa974ab3f0319cfe0e8272b5c688330b432b`
- Package manifest: 37/37 entries verified in recorded run.
- Windows 10 build 19045; CPython 3.13.16 AMD64; OpenSSL 3.5.9.
- Source commit: `05ba5c960aaea96fc6bb80504b53b4d47e7d42f5`
- Publication commit: `4731c912ba4b34b302843dd37067822ffb699ba7`
- Registry SHA-256: `33df4395bffc0ab261af333d84e48b080fdff3d10852de2522bc61e19515ae6f`
- Registry URL: https://raw.githubusercontent.com/SepehrGhanbari/Ario/4731c912ba4b34b302843dd37067822ffb699ba7/releases/ai-readable-full-2026-11-11-05ba5c9/checksums.json

## Recorded acceptance results
| Asset | Bytes | SHA-256 | Result |
|---|---:|---|---|
| ario-full.zip | 6524694 | d11269dc593f9cbb70e7d622a8acc31d0fe36d292a935225aca6b8f98d5c5d51 | MATCH, exit 0 |
| ario-full.txt | 17751878 | 86aafca0e20fb356bdee14c05815d017b3212ef68afed8757fa16f1a1b746af6 | MATCH, exit 0 |
| ario-manifest.json | 63205 | f86fb10ef3eb71dd6e3c348b3f0c9b42c88b3837ae889918c33d8f5d62fe11d8 | MATCH, exit 0 |

All three CLI reports state GITHUB_RELEASE_BYTES_MATCH / HTTPS_GITHUB. The same-size modified-file negative control returned REJECTED / FILE_SHA256_MISMATCH / exit 2 (expected). The harness recorded zero for the negative-control assertion, not for the rejected verifier invocation.

| Suite | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| R1.4 controls | 15 | 0 | 0 | 1 |
| R1.3 controls | 18 | 0 | 0 | 2 |
| Adapted suite | 47 | 0 | 0 | 3 |
| HTTP controls | 24 | 0 | 0 | 0 |
| Byte-original historical suite (diagnostic) | 23 | 3 | 4 | 2 |

Both distinct R1.4 mutants detected. All specified acceptance gates exited successfully. These are suite counts, not a claim of distinct independent tests.

## Historical suite disposition
The three failures assert superseded provenance labels. Three errors arise from obsolete synthetic responses without headers; the fourth attempts a custom release on the default live route, which the newer contract intentionally rejects. These are recorded, not relabelled as passes. Adapted suites cover the revised contract. The six skips across the three current unittest suites concern POSIX-specific checks and symlink creation permissions. Prior Linux test results were reported in earlier R1.4 work; not rerun in this closeout.

## Decision and limits
Close the bounded R1.4 engineering-validation cycle without adding functionality or another review round absent a material new finding. The recorded evidence meets the agreed acceptance criteria for checking exact local bytes against the fixed GitHub publication through the verifier's pinned registry. Unsupported content encodings and ambiguous framing intentionally yield UNKNOWN. This does not establish independent publisher identity, independent pin custody, DOI asset equivalence, scientific truth, all filesystem races/reparse points, or subsequent use of a mutable pathname. The 15 DOI references are bibliography only. No Genesis, signer, trust activation, production, release or automatic merge authorized. No repository changes performed in this closeout. GitHub admission and any merge are separate owner decisions; preserve historical artifacts.
