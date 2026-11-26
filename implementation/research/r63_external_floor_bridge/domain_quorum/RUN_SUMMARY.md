# R63 domain quorum test run

Command: `python -m unittest -v test_domain_quorum.py`

Result: `Ran 50 tests ... OK` (exit code 0).

The suite covers receipt binding and freshness gates, failure-domain collapse across operator/corporate group, administration, key custody and state backup, read/write intersection in every required class, and weighted-quorum analysis. It includes the published Markovian 4-of-7 example after conservative corporate grouping.

The model is synthetic and consumes pre-verified receipt flags. It does not perform cryptographic verification or prove any real operator's administrative independence or persistence. The weighted profile function analyzes only the supplied domain mapping.

Exact Git blob SHA-1:
- domain_quorum.py: 64aaef787c002ff23fa0648168da6103eb4bf88f
- test_domain_quorum.py: 3daf2e5ed3d3ad3df30ef7c8f0613604f02eb1fc
- README.md: 5dbe299841f7d00cff34a2b1b2ea513c74049a9b

Exact SHA-256:
- domain_quorum.py: 85b339c20557ebfa367d80a2f7ba577f0319013223544a94da919ed917fff1ba
- test_domain_quorum.py: 55fe58b9f55c5e3ada5127a512220b78459c69d265817b0cec719012586b12c6
- README.md: 73db810ed2d65c7a41fb0b8ca4b498cea78d772bd06b5496dc2509dd6d6bece0

Startup note: the Python tool emitted an unrelated spreadsheet-runtime warmup warning before the tests; the test runner itself completed with exit code 0.
