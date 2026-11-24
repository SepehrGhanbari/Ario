# Ario release byte cross-check R1.4

**PASS_BOUNDED / RESEARCH_ONLY.** No production, signer, trust activation, release replacement, or automatic merge.

Exact verifier: [`candidate/ario_github_crosscheck_v0_4.py`](candidate/ario_github_crosscheck_v0_4.py), SHA-256 `fac354c46e8fc8ce68edf6202980aa974ab3f0319cfe0e8272b5c688330b432b`.
This is a read-only check of a local asset against the pinned checksum registry from the fixed GitHub publication commit, not independent publisher identity, independent pin custody, DOI equivalence, or truth of content. The original historical publication is unchanged. Use only a separately obtained trusted verifier; do not execute received archive contents. Unsupported content encoding or inconsistent HTTP framing returns UNKNOWN.

See [bounded closeout](evidence/BOUNDED_CLOSEOUT.md), [public Windows execution log](evidence/R14_WINDOWS_FINAL_RESULTS.public.txt), [original evidence hashes](evidence/ORIGINAL_EVIDENCE_HASHES.json), [R1.4 review report](REPORT_FA.md) and [test instructions](REVIEWER_HANDOFF_EN.md). The original Windows log remains preserved separately; the public copy redacts its local scratch path. Embedded historical ZIPs are not republished in this directory; their hashes and original inventory are retained. `SHA256_MANIFEST.json` covers this public directory excluding itself. The byte-original historical suite is diagnostic, not a green acceptance gate.

Example, Python >=3.10 (no third-party dependencies):
```sh
python -I -B candidate/ario_github_crosscheck_v0_4.py --file /path/to/ario-full.zip --asset ario-full.zip
python -I -B tests/test_r14_http.py
python -I -B tests/test_r13_falsifiers.py
python -I -B tests/run_mutations_r14.py
```

Exit codes: 0 = matching bytes, 2 = rejected, 3 = unknown. Successful local hash results do not guarantee later use of a mutable pathname. The adapted and historical harnesses retain original import filenames; all four candidate copies in the test layout are byte-identical. The previous R1.3 input under `input/` is retained separately for RED reproduction.
