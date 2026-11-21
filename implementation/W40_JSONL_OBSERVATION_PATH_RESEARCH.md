# W40 — JSONL observation read boundary hardening

**Research-only.** Work is deliberately separate from W39's Windows ancestor-path probe.

## Exact source contract and problem
At original main `3d2e17374359eb28778fbd74ec520215c0bb2a6b`, `implementation/ledger_observation_adapter.py` (blob `5d3082570fbbbf9ea62b17030c21eac53a11a26b`) first checked `target.is_symlink()` then called `target.open("rb")`. That separation is a check/open symlink race; on Windows, the separate native W38 guard still has unresolved ordinary-ancestor substitution races.

## Patch scope
Reuse the **already merged** `research.w38_receipt_fd_guard.read_bounded_regular` for one bounded acquisition of the nominated JSONL file, then parse using `io.BytesIO`. The 8 MiB max, 64 KiB max line, 5000-event cap, envelopes, UTF-8 and JSON depth constraints, event record hashes, manifest schema and bridge are unchanged. No mutation of the ledger, manifest or an authority source is permitted.

On POSIX, W38's descriptor-relative O_NOFOLLOW directory walk removes the demonstrated symlink substitution between predicate and open. The copy in memory prevents *later pathname replacement* from changing the bytes being parsed, but does **not** establish an atomic disk snapshot under a simultaneous in-place write. On Windows this reuses native W38's limited leaf no-follow checks; W39 separately probes the ancestor race. A successful JSONL manifest remains a statement about locally observed bytes, not authenticated event truth.

## Synthetic adversarial tests
- Normal exact bytes and digest, two events, zero filesystem mutation
- Missing file and direct symlink refusal
- POSIX deterministic parent and leaf symlink swaps injected **at** os.open
- Limit, malformed/incomplete/empty JSONL, bridged stale-manifest rejection
- Single bounded read and no second Path.open

Actual new suite and full Linux/Windows CI outcomes must be attached to the PR. POSIX-only tests are skipped on Windows, not misreported as a platform security proof.

## Explicit retained boundaries
`UNKNOWN` is valid. `OBSERVED` is **not** Evidence, Assessment, fresh history, external custody, a monotonic external floor, rollback protection, trust or signer authorization. W40 does not amend `ledger_audit_bridge.py`, core memory, Genesis, `M0` or rulesets. In-place concurrent updates, Windows ancestor replacement, hardlink provenance and platform-specific file sharing remain **NOT_PROVEN_CLOSED**.

A scientific/research-only merge can be considered after source review and exact-head CI; no automatic promotion of the data as truth or production permission.
