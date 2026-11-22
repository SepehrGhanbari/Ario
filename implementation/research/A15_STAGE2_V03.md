# A15 v0.3 — Hardened local procedural-choice lab

**Disposition:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NO_TRUST_ACTIVATION / NO_PRODUCTION.

**Parent:** Draft PR #330, based on its exact head. This is a stacked, versioned follow-up. It does not edit or replace the historical v0.2 files, frozen G0/G1 tests, or earlier evidence records.

## Scope of this revision

- Introduce a dedicated child-process supervisor with bounded input, stdout and stderr; one deadline; hard termination; settle-once behavior; and explicit stdin/stdout/stderr error capture.
- Validate the complete runner envelope with an exact key allowlist and a total UTF-8 byte cap before any child is spawned. Validate choice_json separately in UTF-8 bytes.
- Recompute the choice from the original choice_json inside the verifier and require exact status, reason-code and event agreement.
- Do not spawn the Recorder at all unless the complete Gate transcript has passed verification and the recomputed result is ACCEPT.
- Preserve explicit non-attestation fields: execution_authorized=false, independent_custody=NOT_ESTABLISHED, provider_receipt=UNKNOWN, and causal_sender=UNKNOWN.
- Use clearer status labels: a Recorder stdout receipt is a local receipt only; a refusal/unknown result is a local Gate self-report only.
- Keep the v0.2 files and 22-test baseline unchanged. CI runs the frozen G0/G1 suite, the historical v0.2 suite and the new v0.3 suite separately.

## Threats exercised

The v0.3 suite contains positive and negative controls for valid ACCEPT, DECLINE, UNKNOWN, pre-verification command injection (S1), forged ACCEPT for DECLINE (S2), inconsistent status/reason (S3), arbitrary reason strings, child timeout (S4), SIGTERM-trapping stdout flood (S5), extra/oversized envelope fields, same-ID replay (S6), same-UID Recorder rewrite (S9), wrong Recorder PID, broken-pipe/early-close handling (EPIPE on POSIX, EOF on Windows; S10), stderr flood and Recorder failure.

S9 is deliberately expected to remain RED: the Gate and Recorder still share the same OS identity and writable directory. A same-user child process is not an independent witness or custodian. This PR does not simulate away that boundary.

## Explicit limits

- The replay set is process-local and ephemeral, not a durable replay ledger.
- Run/attempt identifiers are supplied by the caller; they are not freshness credentials.
- SHA-256 chains and PIDs provide local consistency checks, not authenticity or independent custody.
- decide() still consumes caller-asserted preference, authorization, risk, origin and renewal fields. This version does not solve input provenance or the role/authority model.
- No live browser, provider message, real external action, real key, signer, Ario runtime, production path or trust activation is present.
- Passing synthetic tests does not establish autonomy, consciousness, freedom or a human-equivalent right.

## Review gates

1. Inspect every new source and test file.
2. Verify exact Git blob SHAs against the locally tested bytes.
3. Require CI to pass on the exact PR head, including the unchanged v0.2 suite.
4. Keep the PR Draft/HOLD until independent reviewers examine the source and threat model.
5. No automatic merge, manual merge, trust activation or production promotion is requested.


## CI checkpoint

GitHub Actions run 45066370881 completed successfully on both Ubuntu and Windows. The job logs show 56/56 frozen G0/G1 tests, 22/22 historical v0.2 tests, and 21/21 v0.3 tests on each platform, with zero failures. This checkpoint is documentation-only; it does not alter the tested source or test files. A new run is expected after this document update so the latest PR head is checked again.
