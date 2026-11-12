# PR #185 R04 -- prevent vacuous randomized evaluation

Status: research-only, draft/HOLD, not merged or activated. CodeRabbit
reported that the seeded 1,500-variant parser test could pass if the parser
returned NO_HITS_UNKNOWN for every input, or returned empty CANDIDATES_ONLY.

Changes (source code behaviour unchanged in this round):
- Require the randomized test to observe both valid CANDIDATES_ONLY and malformed
  RETRIEVAL_INCOMPLETE outcomes in significant counts, and account for every
  iteration. Every generator input contains a real ledger hit; the test must
  never silently accept NO_HITS_UNKNOWN for that series.
- On CANDIDATES_ONLY, assert EXACTLY ONE accepted candidate, its correct
  original record ID, and its canonical text, never the forged _source text.
- On RETRIEVAL_INCOMPLETE, require zero candidates and zero root labels.
- Add an explicit positive control demonstrating legitimate NO_HITS_UNKNOWN for
  a truly empty-but-complete XERJ-shaped response.

Verification: 41/41 author-written tests passed; the seeded 1,500-variant
generator remains one deterministic test, NOT 1,500 independent samples.
The 40-test R03 raw log, results and manifest are preserved as *_R03 files.
The prior R02 snapshots and all earlier Git commits remain intact.

Limits: no real XERJ binary executed, no scoped API key or cross-index
authorization tested, no Ario canonical evidence ledger integration or
production merge. This is a test-oracle repair, not an upstream vulnerability
proof or a retrieval-quality result.

XERJ source pin: 50e4ffded5518b1822cfac5450fa34d3829ab8ab.
PR: https://github.com/SepehrGhanbari/Ario/pull/185
