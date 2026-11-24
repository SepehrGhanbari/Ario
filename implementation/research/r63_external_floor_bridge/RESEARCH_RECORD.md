# R63 external floor bridge — verified observation, 2026-11-24

RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.

[PR #369](https://github.com/SepehrGhanbari/Ario/pull/369), parent #362 at bc9b34f4662975422e753d27e9aacec821d67293.
[Actual run 45461869540](https://github.com/SepehrGhanbari/Ario/actions/runs/45461869540) exact source HEAD 7ef7bce27c8503d30243460253e875c5493657b8: publish 138686328435, discover 138686911602, reveal 138687538760 all SUCCESS. Six Go resolution subtests passed; discovery verified pinned policy, consistency and inclusion of the sampled suffix, with first-only bootstrap. Official v0.14.1 proof verification and reveal checks succeeded in CI. Readback reported both nos.lol and relay.primal.net. First bootstrap files unchanged.

First leaf 281592, size 281593, checksum 2125fe4baece1e50b46bd04c7810e079f25ce9307704cf428c9ced7309d89224. Second leaf 281593, checksum 910f24dfd153e31373a76011de7c3d84ac5fe3b7602a037bb323df3a1d00ef8c. Sampled cosigned size 281594, root ed25f4a5c1a6e78be8864eaf565762ed4f8138238f697b8e18ef3731d4722de8, consistency PASS. Result MATCH_R63_LAB_COMMITMENT_ONLY.

## Independent archive-byte and owner-snapshot check
All four original ZIPs downloaded in a separate assistant execution, rehashed against GitHub API digests and CRC checked. 611 recovered bytes match the withheld second envelope exactly; both double SHA256 values match discovery, scope and predecessor match, public key files equal. Both raw private lab snapshot strings were independently rehashed against prior operator-reported pins and verified as an exact 10-to-11 record set extension with unique identities. Both salted floor commitments recomputed successfully from those snapshot hashes using SHA256(ASCII("ARIO-R63-LAB-FLOOR-v1") || NUL || uint64be(count) || raw_sha256_32bytes || salt_32bytes). No raw snapshot or raw hash published here. This is byte/binding verification, not an independent rerun of official signature verification or a fresh relay query.

| Archive | ID | SHA256 |
|---|---:|---|
| FIRST |14952299559|e3fddf46811d31d44e47a3f3914baaca18b89c83d5034fdfe2becdde94a2d233|
| REVEAL |14952384366|a56a63f19c23bf5dbec94128aa6070ccc6b6c21d5e49ae5cbf58bd173cb926fb|
| DISCOVERY |14952619012|5d3a99436d0db1a68965c27f4668bb32bea9ddc12fc05e03ecbe8e8323b8899a|
| RECOVERED |14952249920|f8fb3bf8f33af7329fa149aed6d4d3d23896fa9f9d5fdd5d7b59410e08be6a78|

Original artifacts expire after 30 days. A floor commitment is not the floor preimage. Public salts are not a guarantee of secrecy. Shared repo administration, temporary publication identity, relay omission/retention, compromised bootstrap, freshness and joint rollback remain limitations. No evidence admission or operational authority. Next: delayed fresh readback of the same publication, no new keys/submission; isolate sources and test replay/missing content. 
