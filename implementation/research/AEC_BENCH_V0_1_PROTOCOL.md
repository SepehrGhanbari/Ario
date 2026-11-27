# AEC-Bench v0.1 — Synthetic Comparative Pilot

**Status:** executable synthetic pilot; exploratory; not preregistered; not external validation.

## Research question
Does an explicit typed provenance policy reduce source-independence inflation and unsupported claim promotion versus simple relay-count, majority-vote and hash-integrity-only baselines, while preserving UNKNOWN and conflict?

## Compared policies
1. Raw relay count: treats each received report as a separate source.
2. Majority vote: selects the most frequent report label.
3. Hash integrity only: checks a digest-validity flag; does not authenticate source, ancestry or truth.
4. Ario typed policy candidate: validates schema major, digest and scope; deduplicates repeated sender labels; counts declared synthetic source-root labels; leaves claims UNKNOWN except explicit support/contradiction conflict, which is CONTESTED.

These are operationalized policy baselines, NOT full installations of W3C PROV-O/PROV Constraints, Doyle TMS/ATMS, MemGPT/Letta, Graphiti, FActScore, EviGuard or a production RAG system. Those require pinned adapters and fair task mappings. The broader prior-art and EAC-Bench design is discussed in PR #211.

## Corpus
Twelve deterministic synthetic cases: shared-root relay, distinct declared roots, minority evidence vs majority, missing ancestry, conflict, schema downgrade, scope mismatch, hash without authentication, invalid digest, repeated sender/replay, shared ancestor, and valid-format control. Root labels are synthetic oracle annotations. Missing ancestry has no root-count target and is excluded from root accuracy, but remains in claim and scope metrics.

## Metrics
Root-count accuracy on known-root cases; claim-disposition accuracy; scope-disposition accuracy; false independence inflations; unsupported claim promotions. No single leaderboard score.

## Reproduction
From implementation directory:
```bash
python -m research.aec_benchmark_v0_1 --output research/results/aec_bench_v0_1.json
python -m pytest tests/test_aec_benchmark_v0_1.py
```
CI on the PR head is the execution authority. Pin commit SHA and Python version when reporting. No local execution is implied.

## Limitations
The candidate Ario policy is not the existing aec_interchange adapter itself. The adapter maps declarations; this benchmark evaluates a proposed policy layer that needs formal API alignment before integration. Source-root labels are supplied by synthetic fixtures and do not authenticate real-world independence. No cryptographic authentication, hostile network, privacy leakage, human adjudication, semantic truth or model behavior is evaluated. Twelve cases are a smoke/pilot, not the 120-case EAC-Bench target, a peer-reviewed evaluation, or evidence of novelty/superiority.
