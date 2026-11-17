# Direct CNG P-256 CI probe

This is a **single disposable Software KSP ECDSA-P256 key** used on a fresh, GitHub-hosted Windows 2022 VM. The script directly invokes NCryptSignHash one time, checks its returned length, independently validates the signature with a public-only ECDsa verifier, checks a mutated digest is rejected and tests deletion using CngKey.Exists. It never serializes or uploads a private key.

Counts describe **only this independent CI process**, not the R63 signer service or a system-wide CNG audit. No two-actor synthetic grants, witness custody, recovery, RPC server, crash injection or broker exactly-once semantics are exercised. Do not mislabel this as native R63 V10 acceptance.

`RESEARCH_ONLY / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO / R63_SIGNER_SERVICE=NOT_EXECUTED / INDEPENDENT_CUSTODY=NOT_ESTABLISHED`
