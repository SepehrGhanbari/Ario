R22.22I — external independent witness cosignature quorum (read-only, TEST_ONLY)

The first live run of the official sigsum-test2-2025 built-in 4-of-5 policy did not meet its grouped quorum; preserve this as NOT_MET. The live log did return two cryptographically valid cosignatures from two non-Glasklar test operators: remora.n621.de (Florian Larysch) and witness.stagemole.eu (Grégoire Détrez). A custom external-only 2-of-4 policy over the four external public keys in sigsum-go v0.14.1 is used for this bounded research check; Glasklar is excluded. It requires two distinct external signatures on the exact same cosigned tree head.

Live evidence from run 45836342538:
- cosigned head size 282811
- root 7f5a1fbf808e3a63652c0817a568c50b9965af19d4fd0faf98fe426166b90ff7
- external valid cosigners: remora.n621.de and witness.stagemole.eu
- built-in test2 4-of-5: NOT_MET
- both witnesses' get-tree-size endpoints returned HTTP 404 in the attempted readback. The Remora /status page is the independent state readback; Stagemole contributes the second independently operated test-witness signature.

The Remora public /status page was also fetched independently. It lists the same log key at size 282811 and base64 root f1ofv4COOmNlLAgXpWjFC5llrxnU/Q+vmP5CYWa5D/c=, which decodes to the exact hex root above. R22.22I now parses this status page and requires an exact size+root match to the signed head. This is a separate readback from Remora's own stored state, outside GitHub and the publisher. Stagemole is identified by its own /about page as a Mullvad-operated test witness; its cosignature is verified, but it does not expose a matching /status or get-tree-size readback.

Boundaries:
- This is a TEST witness network and a custom research policy, not production custody. Test operators can reset their test state.
- Witnesses retain/check monotonic tree-head state, not the underlying Ario files or all log leaves. Cosignatures show these operators accepted this exact checkpoint; they do not prove data availability.
- Remora explicitly warns that its test instance runs on a VM, has no HSM or redundancy, and should not be relied on alone. Stagemole is a Mullvad-operated test witness, not a second production custodian.
- Global latest remains UNKNOWN. No new publication, POST, key, DNS change, account, payment, trust activation, production, or merge.
