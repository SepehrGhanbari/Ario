# Ario R1.4 — bounded final verification

Exact candidate SHA-256: `fac354c46e8fc8ce68edf6202980aa974ab3f0319cfe0e8272b5c688330b432b`.

Review the two transport changes in `PATCH_R13_to_R14.diff`. Reconstruct from `input/ario_github_crosscheck_v0_3.py` and compare exact bytes. Preserve historical tests and inputs. The correction reads exactly the validated Content-Length (including equal combined values) and requests identity content encoding; nonidentity responses are intentionally UNKNOWN, not a checksum mismatch. Gzip decoding is not in scope. Check these bounded guarantees and actual regressions rather than requiring arbitrary expansion of the research threat model.

Rerun on Windows and Linux, verify real HTTPS for the exact candidate, and if accessible check the three official published assets. Use read-only requests. Separately report unmodified historical tests, adapted tests, new controls and skips. Verify that invalid/truncated responses remain UNKNOWN and identity registry/file digest mismatches remain REJECTED. A passing live check is byte consistency, not independent publisher identity. Return PASS / REVISE / HOLD with actual evidence and limitations. No automatic merge, real keys, trust activation, production or historical edits.

## Reproduction (from extracted package root)

```
python -I -B tests/test_r14_http.py
python -I -B tests/test_r13_falsifiers.py
python -I -B tests/run_mutations_r14.py
python -I -B candidate/ario_github_crosscheck_v0_4.py --file fixtures/retrieved-ario-manifest.json --asset ario-manifest.json
```

For the original R1.3 RED, set `ARIO_TEST_TARGET` to the absolute path of `input/ario_github_crosscheck_v0_3.py` and run `test_r14_http.py` (expected nonzero). For the 50 adapted tests, enter `testbench-ported`:

```
python -I -B -c 'import sys,unittest;sys.path.insert(0,".");s=unittest.defaultTestLoader.loadTestsFromNames(["test_crosscheck_v0_2","test_adversarial_r1_v0_2","test_adversarial_extended_v0_2","r12_independent_controls"]);r=unittest.TextTestRunner(verbosity=2).run(s);sys.exit(not r.wasSuccessful())'
python -I -B http_controls_ported.py .
```

For the byte-original R1 suite, enter `historical-r1` and use the same unittest command without `r12_independent_controls`; old expectations intentionally remain visible and are not evidence of a passing historical suite. The candidate source is copied under historical import names; those are not different implementations. On Linux the 50 adapted and 20 preserved R1.3 tests and all 24 HTTP controls passed. Fresh live attempt returned UNKNOWN. The previous reviewer's live success on R1.3 is reported, not claimed for this candidate.
