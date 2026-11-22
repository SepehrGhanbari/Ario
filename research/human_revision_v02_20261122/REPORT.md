# Issue #220 research slice — audit record, 2026-11-22

**Scope:** Exactly five ADDITIVE files in this directory on a separate draft branch. No edits to `implementation/`, existing PR #226, original memory contracts, AGENTS, signer or main. Synthetic only.

**Prior art already in repository:** [#220](https://github.com/SepehrGhanbari/Ario/issues/220), [#210](https://github.com/SepehrGhanbari/Ario/issues/210), [Draft #226](https://github.com/SepehrGhanbari/Ario/pull/226). The prior helper classifies a correction for review but does not project separate historical/system/correction/permission/withdrawal/dispute layers. This is a deliberately separate, experimental **gap test**, not a duplicate implementation or a memory migration.

**Public test plan:** 9 visible synthetic HR01–HR09 scenarios, history immutability, late-model-summary non-override, unknown authority, repeated ID, withdrawal. Cases and labels authored together; **not blind**, **not independently adjudicated**. Test execution and CI statuses must be appended after verified runs; no PASS is asserted in this initial source record.

**RED condition (conceptual, not an old-contract defect):** any automatic reuse after withdrawal, person correction overwritten by model summary, accepted third-party impersonation, stale correction silently applied, or historical statement silently erased. **GREEN means only passing these synthetic predicates** and cannot establish verified human identity, legal compliance or persistent cache invalidation.

**Open integration gate:** independent review against #210 RECORDED/ACCEPTED and PR #226, then explicit owner authorization before any modification to core memory or data processing. No human identifier, actual preference or private transcript is included.

## 2026-11-22 append-only negative and correction record

- **Original source bytes verified:** GitHub source blob `6497f03fc59e2de28ee40c2a851a2a69b84a5f2b` equals `git hash-object` on the isolated local copy.
- **Executed RED (before correction):** invented sequence `statement -> model interpretation T1 -> use permission for T1 -> correction to T2` returned `REVIEWABLE / CURRENT_REF_ONLY / CORR-T2`. It wrongly carried an old interpretation's permission to a new one. This is a defect in the *new v0.2 research projector*, not in PR #226 or Ario runtime.
- **Executed GREEN (isolated local Python, after targeted fix):** four explicitly chosen controls passed: prior permission then correction => WITHHOLD; correction then new permission => CURRENT_REF_ONLY; prior permission then new model interpretation => WITHHOLD; explicit withdrawal => DENY. These are researcher-authored controls, not an independent study.
- Added two corpus-adjacent unittest regression cases to this Draft PR; **full unittest corpus execution and GitHub-hosted execution not yet claimed**. Repository `implementation-regression.yml` runs tests under `implementation/tests/` and does not automatically invoke these separate research-directory tests.
- Permission now invalidates whenever an interpretation ref changes; withdrawal still denies. No real authentication, privacy-policy decision, memory integration, or trust authority was introduced.
