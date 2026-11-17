# W21 independent security review handoff — Cloud/Claude/Codex/Grok or any unaffiliated reviewer

**Review target (exact fixed source):** repository `SepehrGhanbari/Ario`, branch `research/consensus-sprint-20261116`. The core hardened HTTP observer and tests are the Git blobs below; review their actual content, NOT merely an AI/CI summary:

- `research/consensus/w21_loopback_log_server.py`: `166829146235878c239d397a232f9b74f04f5afd`
- `research/consensus/w21_http_observer.py`: `b97db30fd880fc8ec71d96936b87a2284cc38d8d`
- `research/consensus/test_w21_http_monitor.py`: `32ad0d92c6d119e6018eac483008dab9190f100c`
- `research/consensus/W21_SIMULATED_RETAINED_HIGHWATER_2026-11-17.json`: `3100c1d5e144503d2da4569aea0f34fd5b611fc6`
- Merkle verifier: `research/consensus/w20_independent_monitor.py`: `e0e1132a19fe5774460ccea48ef055eb1787653e`
- Main result and trust boundaries: [W21 report](W21_LOOPBACK_HTTP_ORIGIN_AND_HIGHWATER_LIMITS_2026-11-17.md)
- Actual **hardened** execution: https://github.com/SepehrGhanbari/Ario/actions/runs/44163994803

## Reviewer mission — report only independently checked evidence

Please perform an **adversarial source audit**, not a generic positive review. **No secrets, no production Ario signer, no live memory, no external enrollment.** The existing code serves a *synthetic 8-leaf log* over local HTTP, not a production C2SP-compatible service.

**1. Find a counterexample that matters.** Independently author at least one malicious HTTP responder or altered public fixture. Try: signed-but-stale old+old views, frozen same-size checkpoint, inconsistencies between responses to `/checkpoint`, `/events` and `/consistency`, malformed query, duplicate JSON key, large response, 302/307 redirects to a different origin, a link-local or loopback SSRF attempt, changed event sequence, forged operator claim, wrong public key, and wrong origin.

**2. Independence and currentness.** W21's `W21_SIMULATED_RETAINED_HIGHWATER_2026-11-17.json` is a copy produced by **the same repository owner**. Propose an independently authenticated/custodied last-seen checkpoint, and show whether a publisher-controlled old+old response is detected *without* that anchor. Do not confuse two Python processes, two GitHub runners or two signatures with separate administrative domains.

**3. Crypto/protocol interop.** Recreate at least one inclusion and one append-only consistency proof using independent source/library references against [RFC 9162](https://www.rfc-editor.org/rfc/rfc9162.html) and compare results. The custom W20 JSON head signed with Ed25519 **is not** [C2SP tlog-checkpoint](https://c2sp.org/tlog-checkpoint@v1.1.0); no official witness `add-checkpoint` has been called. Do not claim compatibility with [C2SP tlog-witness v1.1.0](https://c2sp.org/tlog-witness@v1.1.0) or [C2SP tlog-tiles](https://c2sp.org/tlog-tiles@v1.0.0) without a real independent spec-level interoperability test.

**4. Effect/authority boundary.** Prove a response cannot silently become human consent, memory admission, truth or action authority. Verify `operational_authority=NONE`, `real_ario_log_witnessed=NOT_ESTABLISHED`, `freshest_world_checkpoint=UNKNOWN` in every result, including all benign positive test cases.

**5. Return exact evidence:** `claim | CONFIRMED/REFUTED/UNKNOWN | source commit/blob | actual command + output | independently authored negative fixture | severity & real-world prerequisites | minimal patch/hold decision`. Avoid rating green CI as independent audit. Keep negative/surviving cases in versioned append-only evidence, not rewritten history.

**Already established but NOT sufficient:** local 4/4 W21 Python test groups, GitHub 4/4 W21 + 6/6 W20 methods, 13 named HTTP matrix scenarios, one redirection canary test, same-repo public raw W20 immutable-commit snapshot. No actual independent human review or third-party administrative custody yet.

**Disposition:** `RESEARCH_ONLY / REVIEW_OPEN / NO_PR_MERGE / TRUST_ACTIVATION=NO_GO / GENESIS=NO_GO / PRODUCTION=NO_GO`. Return findings to [Issue #259](https://github.com/SepehrGhanbari/Ario/issues/259), coordinate actual native log witness prerequisites in [Issue #171](https://github.com/SepehrGhanbari/Ario/issues/171).
