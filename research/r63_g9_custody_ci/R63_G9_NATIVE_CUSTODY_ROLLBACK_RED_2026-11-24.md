# R63 G9 — Native distinct-SID custody fence, with independently reproduced shared-administrator rollback RED

**2026-11-24** · `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO`.

## Decision

**The G9 experiment reproduced BOTH outcomes:**

1. With publisher/broker use-intent and receipt files deleted, but a separately OS-SID-owned custody use marker retained, the same synthetic signed request returned **`HOLD_EXTERNAL_SPENT`** and **no new CNG entry** was observed.
2. With the same common administrator subsequently deleting that custody marker as well, the original signed synthetic request reached native CNG again and a second independently verifiable public ECDSA P-256 receipt was produced using the **same disposable Software KSP key**. This is an expected **RED counterexample**, not a fix.

This directly invalidates any claim that merely having different Windows account SIDs under a common administrator achieves independent, non-rollbackable key-use custody.

## Grounded code and changes

Baseline: [G8 source-bound native synthetic broker](../r63_g8_native_ci/README.md) and user-visible G8 audited evidence. G9 does not change G8's original source, private historic ZIP, main, laptop, phone note, or any real signing key.

- `research/r63_g9_custody_ci/G9IntegratedBroker.cs`: G8 implementation copied to a new research-only class and **modified at the CNG entry gate**. Before writing local durable intent and before any `NCryptSignHash` call, the broker must receive a *durably committed* use-consumption acknowledgment from a separate named-pipe custody process. No answer/incorrect answer → HOLD. The custodian uses its **actual impersonated Windows client SID** to require the broker's OS SID. A 64-hex token commits exact epoch, seq3 baseline, seq4 candidate, case name, nonce, ID, payload hash. The custodian uses exclusive `FileMode.CreateNew` + `Flush(true)` under its own SID.
- `Invoke-G9-Actor.ps1`: scoped broker and custody roles, wrong-SID rejects and direct-write-denial probe.
- `Invoke-G9-NativeE2ECI.ps1`: creates **four ephemeral Windows local users** (broker writer, allowed requester, rogue, custody), two DACL-constrained local directory roots, a disposable Software KSP signing key and two temporary signed actor approvals. Repeats precisely the same signed request across the three scenarios; archives public-only evidence and cleans up accounts/key and directories.
- `.github/workflows/r63-g9-custody-rollback.yml`: Windows Server 2022 CI, `permissions: contents:read`, no persisted checkout credentials, time-bound test; G6/G7 pinned source checks first.

**Important narrower scope:** the rollback removes G9's local intent/CNG/receipt/public-pin marker files, not the complete production Ario V1/V2/R60/R51 journals. Both signing attempts are native and exact signed request was reused; this is a strong counterexample for common-admin local-use custody, but not a production integration test.

## CI / exact evidence

[Native Windows Actions run #45405013056](https://github.com/SepehrGhanbari/Ario/actions/runs/45405013056): **SUCCESS** with expected red counterexample preserved:

```text
Ran 28 tests ... OK       # G6
Ran 22 tests ... OK       # G7
G9_STATIC_SOURCE_BOUND_SEQ4=PASS
G9_DIFFERENT_SID_CUSTODY_BLOCKED_LOCAL_ROLLBACK=PASS
G9_SHARED_ADMIN_COHERENT_ROLLBACK=RED_RESIGN_REPRODUCED
G9_TEMP_USER_AND_JOURNAL_CLEANUP=PASS
G9_VERDICT=PASS_SYNTHETIC_G9_EXPECTED_SHARED_ADMIN_RED
```

[Public-only Actions artifact #14925216074](https://github.com/SepehrGhanbari/Ario/actions/runs/45405013056/artifacts/14925216074) (G9 run tag `4f087129`). Downloaded and read *actual raw bytes*, not inferred from summary:

- artifact outer ZIP SHA256 `3a43567854fcde1158206bcaef06a70e13e2ffde41ea827226a0992274bf49b5`; inner evidence ZIP SHA256 `6a5ba41a27a4243ee4558c399631e49e8148412557129980ddbb843a21b85d8f`; both ZIP CRC PASS.
- first native public receipt SHA256 `f1b6c2756db1ab59c8bfb61416574f0567052bfb87f4a81e4ddf3e8209f8ccff`;
- after shared-admin reset, second receipt SHA256 `a65f3abbd57dbd8e4d9fa5751ffe14649f062e732aace7ff11624e81d34ef48b`;
- custody marker preserved while publisher local root was rolled back: SHA256 `858e2e1020c1dc26714937b4e2a32f0306a6ff50a9ad72de870573d629720706`;
- report recorded 2 native broker entries in two distinct processes; actual `NCryptSignHash` call count is **runner-reported**, not separately instrumented by a protected CNG provider or OS trace. We independently verified **four** ECDSA signatures: 2 synthetic actor approvals and 2 public native receipts, using a Python/`cryptography` implementation independent of the C# broker, including correct Windows P256 CNG public-blob decoding and IEEE-P1363-to-DER conversion.
- Independent byte and signature auditor returned `PASS_INDEPENDENT_PUBLIC_BYTES_AND_SIGNED_RECEIPTS`. Its **17 unit/mutation tests PASS**, including 16 positive/negative scenarios: altered or missing first/second receipts, bad actor key, forged actor approval, mutated input payload, missing/corrupt custody marker, forged safe verdict, forged OS independence, changed CNG entry marker and source-report mismatches. This independent audit ran in the research workspace, **not** in the above native Windows CI run.

## What this proves (and does not)

- **Established in a disposable CI environment:** OS SID-based segregation of a use-consumption ledger; a legitimate request is signed once; a publisher-local state deletion alone is blocked by a retained custody use marker, before native CNG; compromised same admin that resets both ledgers can cause another native signature for the **same** synthetic request/key.
- **Not established:** an independently administrated custodian, pinned and authenticated remote custodian server key, OS-admin-resistant storage, vendor-hardware-signing counter, out-of-band separately retained last consumption floor, genuine R60 two-key authorization, independent Ario private-key custody, V9 native broker integration, power-loss-atomic external acknowledgment or authoritative latest seq4 state.
- The published G5 Rekor historical inclusion of a synthetic seq3 checkpoint and founder-reported iPhone Notes minimum seq3 **do not attest** to this consumption marker. iPhone minimum remains `seq=3`; seq4 remains an **unapproved research candidate**.
- **Do NOT** replace `HOLD` with a successful synthetic CI verdict. All same-admin deletion counterexamples remain RED.

## Finite next acceptance action

Stop adding fresh native signing micro-tests. The next *materially new* evidence is an independently administered custodian endpoint that holds an irreversible consumed-nonce record and a verifier-pinned latest `(epoch,seq,head,receipt-digest)`, cannot be deleted/rolled back/rotated by the publisher and is authenticated by the signer with a key or pin provisioned outside the publisher's control.

Once such a trust domain genuinely exists, rerun **only** the exact G9 two-stage replay:
1. Publisher/broker rollback alone → no native re-sign, `HOLD_EXTERNAL_SPENT`.
2. Attempt to delete/restore custodian and verifier pin with *publisher* authority → denied, not the red observed here.

Without such separate control, do not use real Ario keys or activate production. A founder-owned offline iPhone note can preserve a manual *historical minimum*, not autonomous authoritative latest or a signer-use ledger.

**Verdict:** `G9_BROKER_LOCAL_ROLLBACK_WITH_RETAINED_CUSTODY=PASS_HOLD`; `G9_COMMON_ADMIN_ROLLBACK=RED_RE_SIGN`; `INDEPENDENT_ADMIN_CUSTODY=NOT_ESTABLISHED`; `REAL_V9_SIGNER=NOT_EXECUTED`; `GENESIS=NO_GO`; `TRUST_ACTIVATION=NO_GO`; `PRODUCTION=NO_GO`.
