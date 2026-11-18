# R04 OpenTimestamps — second live recheck (2026-11-18)

**Environment:** newly created disposable Vercel sandbox, Python 3.14.4, `opentimestamps-client==0.8.0`. Outbound network restricted to official package registries and three listed calendar domains. No real Ario memory, private key or Bitcoin Core node.

Original JSON SHA256 `c37da68d045da9c85a90dc679857c017ed0bbd1454e51d9033ef9a48e799a68a`, 613 bytes. Original binary OTS SHA256 `5b7fc36d470560adbc8fd4620436451ea43ea0578bf50e7ca6104ce0280c3bf6`, 549 bytes. Both matched after reconstruction from [the previous issue comment](https://github.com/SepehrGhanbari/Ario/issues/280#issuecomment-6990276287).

The following three real commands were executed against **the old original receipt**, without requesting a new stamp:

```text
ots info synthetic_checkpoint_r04.json.ots
=> Alice, Bob, Finney all PendingAttestation

ots upgrade -n --timeout 20 synthetic_checkpoint_r04.json.ots
=> Pending confirmation in Bitcoin blockchain (all 3 calendars)
=> Failed! Timestamp not complete
=> UPGRADE_DRYRUN_EXIT=1

ots verify --timeout 15 -f synthetic_checkpoint_r04.json synthetic_checkpoint_r04.json.ots
=> Pending confirmation in Bitcoin blockchain (all 3 calendars)
=> VERIFY_EXIT=1
```

**Observed verdict: `PENDING_BITCOIN / NO_FINAL_BLOCK_PROOF / NO_INDEPENDENT_FLOOR`.** This is a fresh result as of this execution, not a permanent claim. The `ots info` parser is a format check; it cannot establish that the history was honest, complete or latest. No authoritative time, administrator independence or Bitcoin confirmation was established.
