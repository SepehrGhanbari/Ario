# R63 V10 — synthetic CI journal model

**RESEARCH_ONLY**. This source is an independently authored model of the published V9 V2 append-order chain and R60 nonce-sorted content commitments. It is **NOT** the private/frozen V9 native implementation.

Tests require V1 disk order == V2 disk order == RPC memory and compare the R60 content digest independently. Validation re-reads bytes to detect some within-validation changes. No atomic snapshot, cross-process lock, independently held anchor, or actual signer is provided.

The TCP child process really exits after fsync of a synthetic V2 journal and before the synthetic V1 append/ACK; it is **NOT** a CNG signer or native Windows broker. The 2/8/16 concurrent TCP clients exercise a toy locked Python counter only. Two negative controls intentionally demonstrate that a coherent local rollback can pass and deletion after final validation remains unprotected. Passing these tests must NEVER be described as a successful antirollback or native exactly-once proof.

Run: `python -B -m unittest discover -s research/r63_v10_ci -p 'test_*.py' -v`

`GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO / NATIVE_R63_V10=NOT_EXECUTED / INDEPENDENT_CUSTODY=NOT_ESTABLISHED / A_GOV=NOT_ESTABLISHED / USE_COMPLETENESS=NOT_ESTABLISHED`
