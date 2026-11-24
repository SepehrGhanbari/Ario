# R22.6 — CI replay/ABA observation connected to existing witness prefix research

**DRAFT / HOLD / RESEARCH_ONLY.** PR #350 is stacked on #349 at `bb5acbcb46dbfd700e0d59a66aa05b9b7e363f53`. No real keys, deployment, automatic merge, trust activation or evidence admission.

## Existing mechanisms reused unchanged

- `implementation/checkpoint_prefix_experiment.py` (blob `a3aae40a43360c60bcaa8a4f34617be20ed9dd48`): fixed bounded two/four-record checkpoint comparison, symbolic descriptors, independently supplied oracle, prefix hash and known record-count floor.
- `implementation/independent_witness_experiment.py` (blob `8c7c34ca2c06da2535d2ebdde33c4ba4c2343a10`): two synthetic witness envelopes, frozen control anchors, discrepancy and conflict detection, explicit non-authentication.
- `implementation/tests/test_r22_5_replay_aba_boundary.py`: actual self-audit REST decoder through synthetic opener, identical transcripts for stable, ABA and replay histories.

The integration is an executable test harness, not a runtime adapter. It builds four records containing the digest of the fixed research scope, digest of the exact HTTP transcript plus observer output, and two synthetic event slots. The separate world model supplies events. Empty slots mean NO_EVENT_REPORTED, not proof no event occurred. Existing fixture builders seal the record chain and construct two witness-specific checkpoints, including parent checkpoint digest. Existing production and laboratory comparator implementations are not modified.

## Experiments

Fifteen cases cover retained checkpoint correspondence; ABA, final replay and full replay with identical HTTP transcript but different separately observed event history; older two-record checkpoint replay beneath retained four-record floor; deletion, replacement and reordering with recomputed local chain; same-count resealed fork; conflicting witnesses; missing witness; missing floor; cross-epoch replay; common-admin rollback; and events missed by both observers.

The prefix comparator's PASS can coexist with a mismatching known floor: an old two-record prefix may correspond perfectly while being below a known four-record checkpoint. The witness aggregate must reject this when the protected anchors are retained. A matching count alone is not sufficient: the retained checkpoint and exact prefix digest constrain the content. The two-witness model remains conditional on the assumed preservation of the control anchors.

## Intended negative controls (not claims of prevention)

A common administrator who can roll back both witnesses and their floor can present a coherent old checkpoint. The comparator can return CONDITIONAL_CORRESPONDENCE even though custody_independence is UNKNOWN. Similarly, an event that neither the REST observer nor the witness records produces indistinguishable evidence. The integration deliberately asserts these residuals rather than disguising them as detection successes.

The actual observer output is still UNKNOWN / no merge / no trust / no memory update. A witness report cannot establish historical event truth, production historical continuity, cryptographic authenticity or evidence admission. No claim that GitHub actually supplied replayed responses, nor that a real independent witness exists. No durable external storage, network delivery guarantee, authenticated event identity, atomic advancement or crash recovery implemented here.

## Next boundary

Connect this harness to a separately controlled retained (sequence, digest) floor only after reusing and examining the existing custody/floor-transfer experiments. A real witness must establish its coverage and protect its own state against rollback. Sequence advancement, cross-scope binding, crash/retry, gaps and replay across separate processes require further work. A missed event remains UNKNOWN even with a protected journal.

Tests: `implementation/tests/test_r22_6_ci_witness_prefix_integration.py`. Initial test commit `cced9a25f662c0a7800db2466626a0866953ee68`. CI results must be verified on the exact head; the report states the experimental design and intended assertions, not an unverified PASS count.
