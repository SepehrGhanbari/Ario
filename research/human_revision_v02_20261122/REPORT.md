# Issue #220 research slice — audit record, 2026-11-22

**Scope:** Exactly five ADDITIVE files in this directory on a separate draft branch. No edits to `implementation/`, existing PR #226, original memory contracts, AGENTS, signer or main. Synthetic only.

**Prior art already in repository:** [#220](https://github.com/SepehrGhanbari/Ario/issues/220), [#210](https://github.com/SepehrGhanbari/Ario/issues/210), [Draft #226](https://github.com/SepehrGhanbari/Ario/pull/226). The prior helper classifies a correction for review but does not project separate historical/system/correction/permission/withdrawal/dispute layers. This is a deliberately separate, experimental **gap test**, not a duplicate implementation or a memory migration.

**Public test plan:** 9 visible synthetic HR01–HR09 scenarios, history immutability, late-model-summary non-override, unknown authority, repeated ID, withdrawal. Cases and labels authored together; **not blind**, **not independently adjudicated**. Test execution and CI statuses must be appended after verified runs; no PASS is asserted in this initial source record.

**RED condition (conceptual, not an old-contract defect):** any automatic reuse after withdrawal, person correction overwritten by model summary, accepted third-party impersonation, stale correction silently applied, or historical statement silently erased. **GREEN means only passing these synthetic predicates** and cannot establish verified human identity, legal compliance or persistent cache invalidation.

**Open integration gate:** independent review against #210 RECORDED/ACCEPTED and PR #226, then explicit owner authorization before any modification to core memory or data processing. No human identifier, actual preference or private transcript is included.
