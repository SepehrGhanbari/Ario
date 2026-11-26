# R63 domain quorum test run

Command: `python -m unittest -v test_domain_quorum.py`

Result: `Ran 47 tests ... OK` (exit code 0).

The test suite covers unique witness keys, corporate/operator/admin/key-custody/backup failure-domain collapse, unknown domain labels, proposal/policy/sequence binding, freshness, durability, continuity, readback, read/write quorum intersection in every required failure-domain class, and the Amagicom shared-parent example.

The model is synthetic and consumes pre-verified receipt flags. It does not perform cryptographic verification or prove any real operator's administrative independence or persistence.

Exact Git blob SHA-1:
- domain_quorum.py: cc4d2717a132d04e9cd8b63351238b6a6040e901
- test_domain_quorum.py: 79cf9b68377cf57b13162bb9d073f7a6dbd50e34
- README.md: eb87963eb05053f6d17d5cb1eccdc16dea75ded2

Exact SHA-256:
- domain_quorum.py: e9c14c475b3db6a376c7cdd3fad8d912239528be81f29ade5b74016b457483bf
- test_domain_quorum.py: 572aa02c13ce9259a8f2bb56aa0294f59224a6849093a2efc7671e3fb25885e9
- README.md: ba0b574107216f5938217b3a30aeba0f08792d9a2bbb39fa9fcbf83c9a2a0ffa

Startup note: the Python tool emitted an unrelated spreadsheet-runtime warmup warning before the tests; the test runner itself completed with exit code 0.
