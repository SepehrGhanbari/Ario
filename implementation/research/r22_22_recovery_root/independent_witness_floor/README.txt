R22.22I — external independent witness cosignature quorum (read-only, TEST_ONLY)

The first live run of the official sigsum-test2-2025 built-in 4-of-5 policy did not meet its grouped quorum; preserve this as NOT_MET. The live log did return two cryptographically valid cosignatures from two non-Glasklar test operators: remora.n621.de (Florian Larysch) and witness.stagemole.eu (Grégoire Détrez). A custom external-only 2-of-4 policy over the four external public keys in sigsum-go v0.14.1 is used for this bounded research check; Glasklar is excluded. It requires two distinct external signatures on the exact same cosigned tree head.

Live evidence from run 45836342538:
- cosigned head size 282811
- root 7f5a1fbf808e3a63652c0817a568c50b9965af19d4fd0faf98fe426166b90ff7
- external valid cosigners: remora.n621.de and witness.stagemole.eu
- built-in test2 4-of-5: NOT_MET
- both witnesses' get-tree-size endpoints returned HTTP 404 in the attempted readback. The current check therefore relies on their cryptographically verified signed cosignatures and the documented witness protocol, not a separate state readback.

The next live run pins this exact externally cosigned head as the retained floor, verifies consistency to the current head, and rejects rollback below the floor or same-size root substitution.

Boundaries:
- This is a TEST witness network and a custom research policy, not production custody. Test operators can reset their test state.
- Witnesses retain/check monotonic tree-head state, not the underlying Ario files or all log leaves. Cosignatures show these operators accepted this exact checkpoint; they do not prove data availability.
- Remora explicitly warns that its test instance runs on a VM, has no HSM or redundancy, and should not be relied on alone. This policy requires two operators, not one.
- Global latest remains UNKNOWN. No new publication, POST, key, DNS change, account, payment, trust activation, production, or merge.
