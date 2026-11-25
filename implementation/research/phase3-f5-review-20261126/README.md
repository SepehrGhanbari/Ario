# Phase 3 review follow-up (research only)

Related: Issue #280. This branch is not main, a production deployment, or a trust activation.

Pinned source archives are the Phase 3-A and Phase 3-B attachments identified in #280 and verified by CodeRabbit. SHA-256: A 86453b9d30c29ee2d2b6da720c02bf66110f4e79cf211ca1d5346accece9cfe4; B d0520351365d1dc6ef693d00d290de4f8f6b296d37feb3c129b1ced1ff4ebd98. Do not change originals.

Reproduction in separate extracted source roots:
- A: apply phase3-A.patch and journal-review.patch using patch -p1; copy review_guard.py into source root.
- B: apply phase3-B.patch, F5-gateway.patch, B-review.patch, journal-review.patch, and B-tests.patch in that order, using patch -p1; copy review_guard.py, test_f5_lag.py, test_review_guards.py into source root.
- A: python -B -m unittest -q test_protocol test_phase2 test_phase3
- B: python -B -m unittest -q test_protocol test_phase2 test_phase3 test_f5_lag test_review_guards

Actual local Linux Python 3.13.5 results: A 60/60, B 70/70. Previous applicable regression suites 3/3 each. New test_review_guards on prior B candidate: 4 tests, 3 failures (metadata export, missing message proof, wrong witness identity), 1 pass (injected recovery interruption). All 4 pass on new B. Separate direct probe on prior B: non-extending longer history returned QUORUM_FINALIZED; altered journal metadata was exported despite verify=False. These are local executions, not CI or third-party reproduction.

Changes: reconstruct message head from records and check metadata in one SQLite read snapshot for export; refuse finalization without a message proof, validate extension against retained modeled floor, reject witness state identity mismatch, distinguish lag from conflict and missing evidence. F1 recovery transaction failure tested; F2 same-process race and F4 payload absence tests still pass. Existing B tests explicitly use the new proof argument and expect UNAVAILABLE after restart with no retained modeled certificates.

Fault bounds for 4/10/100 witnesses: f=1/3/33, q=3/7/67. Fixed roster only. No real signature, authenticated enrollment, remote nonce freshness, durable certificate recovery, independent observer custody, safe churn, production consensus, or complete capture is established. A self-consistent full chain is not independently authenticated; all-state rollback remains outside the model. F3's journal export fix does not make the full gateway capture bundle export atomic; F2 does not establish cross-process/transport exactly-once. Receiver deduplication is required for retry; no distributed delivery guarantee. F6 executable identity and transcript scope remain open. No real messages or keys.

RESEARCH_ONLY / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO.
