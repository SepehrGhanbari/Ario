# R63 direct witness reference comparison — 2026-11-25

RESEARCH_ONLY / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE. Continuation of #369, previous record 89cbbfd9c8217475b6d74e81082dd8257b611b96.

Actual read-only GET via TinyFish, ttl=0 (origin cache possible), no log-mediated witness read. Origin SHA256 eea2eb8af49836d7eeedbc0390f53632f45e051c71f7fc453b724d23d7d29640. Geomys monitoring prefix documented at https://navigli.sunlight.geomys.org/; Markovian key and endpoints retrieved from https://witness.markovianprotocol.com/about. Exact target paths below.

| Source | Size | Root (hex) | Signed UTC |
|---|---:|---|---|
| Prior independently verified log head |281650|b9338e3dc8eef6cbf24b0371d7c22c5c4853baf3f8c60565cc5d37d558dfcacf|2026-11-25 16:16:46|
| Markovian |281665|3980068d9f6d953b314be593c6faebf1c700130d77278876f6250feefe701a88|2026-11-25 17:00:02|
| Geomys |281668|9c7044a6046a110de263e507f9b461028baf82c526ac711fb162360732949f20|2026-11-25 17:12:36|

Python Ed25519 independently checked both log signatures, both witness cosignatures, exact origin and key IDs. Actual log consistency paths 281650->281665 and 281665->281668 verified against these roots. Different sizes are compatible, not equivocation. Geomys additional ML-DSA signature not checked. Notes normalized from extracted lines, not exact raw HTTP byte archives.

Five cryptographic negatives rejected (modified size, wrong witness, wrong origin, truncated consistency, same-size different root). Six policy cases passed: old log and lower witness HOLD against observed higher reference; higher match REVIEW_ONLY; single-source omission can conceal newer head (residual RED); no sources HOLD; same-size conflict model HOLD. No live fork or service outage induced. No nonce-bound read, fresh trusted clock, administrative audit, or absolute latestness. Both direct witnesses outside original 2-of-3 policy, advisory only. SmartIT/RGDD/Remora/Mullvad monitor path returned 404; Nisse timeout; IPng path redirected to operator about page. These do not prove service unavailability.

Owner package Ario_R63_Direct_Witness_Comparison.zip SHA256 aa2f1c94f52f13d348db5e77f25a7d2c90257e9c9176bd1998979d5ecd8e6d97, manifest and ZIP CRC checked; contains offline verifier, normalized signed notes, consistency paths and RUN.log. Package not committed here. Evidence below records the normalized Ed25519 note fields and proofs for durable review.

## Public observations

Geomys: https://witness.navigli.skylight.geomys.org/eea2eb8af49836d7eeedbc0390f53632f45e051c71f7fc453b724d23d7d29640/checkpoint

```
sigsum.org/v1/tree/4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d
281668
nHBEpgRqEQ3iY+UH+bRhAouvgsUmrHEfsWI2BzKUnyA=

— sigsum.org/v1/tree/4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d d4YpsT5yNHolQDQEKAwiz6tMgP5m/I/g6vxzhtH0h+29ilOGWnVTzSlBeYD6ww1eFpME/MgpQFDv4Amj8P4OPGitAAI=
— witness.navigli.sunlight.geomys.org o+AP4gAAAABrBxcE51m/CxGbPomgGnsuwKvT0xFePPEOelZDumj7yBUhAQv/xRcmiv4wulkkT5CfBQAWFLkG48kjKKmefV4FxRmiCg==
```

Markovian: https://witness.markovianprotocol.com/eea2eb8af49836d7eeedbc0390f53632f45e051c71f7fc453b724d23d7d29640/checkpoint

```
sigsum.org/v1/tree/4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d
281665
OYAGjZ9tlTsxS+WTxvrr8ccAEw13J4h29iUP7v5wGog=

— sigsum.org/v1/tree/4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d d4YpsR227T1keo7WRNXJyRw8FimWvnB/MZxRKCPpey9M2T2J4MlIWkzuLIZcF6ICUKTxliqjccwwmYBEbeXOQ0QjhAc=
— markovianprotocol.com/witness QbiCfwAAAABrBxQSCGh9PZbK6nrbVTZvQ3QlMJxw5GhtoA+RZKdEosVvRNw3TrPiw9sZ/r4YnW1aXp2GdMePON8N3iwoRWhHYlyaAg==
```

Public keys (vkey):
```
witness.navigli.sunlight.geomys.org+a3e00fe2+BNy/co4C1Hn1p+INwJrfUlgz7W55dSZReusH/GhUhJ/G
markovianprotocol.com/witness+41b8827f+BJKLl8rBYM0oUxSaWh9rjTldTprEpYj/SWVIGgacA9XC
```

Consistency path 281650 -> 281665:
```
7670276e1d8eba288fbd8db85f3d0d88c6e77136446731079fd50a05921674ed
d77f7582065940763f996f3f7a3924c3dea0addb770a997d9005a13ef5e8f0aa
ee6e8bdce27784bf86b98c1dbb6f013a93bcc6f4b9bb333ba66d63affdab27ce
b34f4c749e5b868e08c6f2aba251433521d5e45c285686a4ce6cb3f100888b46
5d7e919aa1b708b32c3ee9727d4ad91a7a1a9b61e36a888c22d32eb8fd734a7b
0d9c8572517970c83a8badc9a7104d3fbee017245adf7a71fe4cef566eeb7ef6
12f956af65ae4127d5a4b0ed5be70c1d971dededc7242d55b7907a552caded01
124a77d338c0c63bfc5a07db1f76420f14bb0c0bc6236dc60c92a80be7491956
3ca4fc8037a26123860ed4bdf0146ad64902dd8ddefc749e3638b8deead2eca7
9f08ed43a5f9cfda6ddc96965e7793c57a154e1624a7c239e3309efb4644dabc
ed692e645805ff21bd2e71d2cfb0ebecba7c9f75be664e981c3215f08cae5081
```
Consistency path 281665 -> 281668:
```
12f956af65ae4127d5a4b0ed5be70c1d971dededc7242d55b7907a552caded01
36727ab185067f71dc71fa54afb0b3461218127efe4b82351284e7f97aa618f6
f293a615d1d707783ca5111b948a4d0bb08b0c692727d260ec8cc1160695e7df
71d8aff2f20844cb16cdc5637eb1fdaa5cd04ecaca98915ff745ee75ed9db384
124a77d338c0c63bfc5a07db1f76420f14bb0c0bc6236dc60c92a80be7491956
3ca4fc8037a26123860ed4bdf0146ad64902dd8ddefc749e3638b8deead2eca7
9f08ed43a5f9cfda6ddc96965e7793c57a154e1624a7c239e3309efb4644dabc
ed692e645805ff21bd2e71d2cfb0ebecba7c9f75be664e981c3215f08cae5081
```

Decision: BOUNDED_DIRECT_WITNESS_READ_PASS; JOINT_ROLLBACK_NOT_CLOSED; GENESIS NO_GO. Next: establish independently available quorum with explicitly pinned operator/retention/freshness policy, fail closed on partial response; do not add authority or replace existing Sigsum test policy automatically.
