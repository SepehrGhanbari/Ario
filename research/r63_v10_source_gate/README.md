# R63 V10 — Frozen V9 V2 source crosscheck

Status: **RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO**.

The copied `spend_chain_v2.py` comes from the user's frozen V9 source-review ZIP and is SHA-256 pinned to:

`c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd`

The directory .gitattributes forces LF checkout because default Windows CRLF conversion initially caused the byte-identity test to fail. The initial Windows failure is preserved in [run 44303201149](https://github.com/SepehrGhanbari/Ario/actions/runs/44303201149). The correction is verified on Windows and Ubuntu in [run 44303352340](https://github.com/SepehrGhanbari/Ario/actions/runs/44303352340) (25/25 tests per OS).

## Direct source review (only the three files shared by the founder)

- `Input/guest_driver_r63_v9.py` (SHA256 `13b4526428322db3936e0dbfba36ab03925d3ecb0b6fdf0f0c7eb8090493af19`): `WitnessHandler.spend` reads and validates V2 against in-memory `parent.spends`, but does not reread current V1 disk bytes before spend ACK. Lines 177–203 concern the specific missing check.
- The witness TCP RPC server runs in a thread inside the same V9 driver process (`WitnessServer` around lines 219–228; server starts around 449).
- `Ario-R63-V9-Report.md` (SHA256 `ce6ad51416d4c6ea62a07322004066e978b0d060bf4bdd43f8ac61a75527cd84`) confirms the witnessed process crash was a **child append-writer**, not the parent RPC process.
- Full V9 driver is **not published to this branch**; the minimal `INTEGRATION_CANDIDATE.patch` is provided as source-anchored review material, **not applied to any native signer**. It applied cleanly and parsed with `ast.parse` against the founder-supplied V9 source locally, but it has not been native-tested.

## Invariants and limitations

The read-only candidate compares current V1 canonical append-order rows, V2 event-chain rows, RPC memory, and R60's **separately sorted** content digest. Both V1 and V2 must be *present* (empty only in an explicitly newly initialized disposable guest). Its final reread detects some in-validation drift, but is NOT atomic or a cross-process lock.

Two deliberate counterexamples remain: coherent rollback of all local state (without an independently retained anchor), and a change after the final reread. Treat their successful detection in tests as evidence of **known limitations**, not evidence of antirollback security.

The tested Python module uses only frozen V2 source, temporary files and no CNG, key use, network, account operations, or services. It is **not the real V9 native recovery test**. The native RPC-parent crash/recovery, stored receipt semantics, non-admin 2/8/16-client race and exact same-key `NCryptSignHash` counting remain **NOT_EXECUTED** in V10.

No main merge, no Rulesets change, no original V9 rewrite, no trust activation.

`NATIVE_R63_V10=NOT_EXECUTED / INDEPENDENT_CUSTODY=NOT_ESTABLISHED / USE_COMPLETENESS=NOT_ESTABLISHED`
