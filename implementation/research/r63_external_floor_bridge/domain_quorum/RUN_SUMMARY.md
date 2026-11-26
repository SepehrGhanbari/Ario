# R63 domain quorum test run

Command: `python -m unittest -v test_domain_quorum.py`

Result: `Ran 50 tests ... OK` (exit code 0).

The suite covers receipt binding and freshness gates, failure-domain collapse across operator/corporate group, administration, key custody and state backup, read/write intersection in every required class, and weighted-quorum analysis. It includes the published Markovian 4-of-7 example after conservative corporate grouping.

The model is synthetic and consumes pre-verified receipt flags. It does not perform cryptographic verification or prove any real operator's administrative independence or persistence. The Markovian recovery-floor behavior is a live operational claim not yet source-verified against the published witness code. A research inquiry was sent, but no R63 log was enrolled or published.

Exact Git blob SHA-1:
- domain_quorum.py: 64aaef787c002ff23fa0648168da6103eb4bf88f
- test_domain_quorum.py: 3daf2e5ed3d3ad3df30ef7c8f0613604f02eb1fc
- README.md: 62eb7e2c2f465b457ca60cfe660c3b8d396148ae

Exact SHA-256:
- domain_quorum.py: 85b339c20557ebfa367d80a2f7ba577f0319013223544a94da919ed917fff1ba
- test_domain_quorum.py: 55fe58b9f55c5e3ada5127a512220b78459c69d265817b0cec719012586b12c6
- README.md: 382d89aa2c2aa5fd7bedfd12c8781e52d1d60c25736dac8fb30eac66366e071c

Startup note: the Python tool emitted an unrelated spreadsheet-runtime warmup warning before the tests; the test runner itself completed with exit code 0.
