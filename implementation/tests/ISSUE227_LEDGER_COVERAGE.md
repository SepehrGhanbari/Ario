# Issue #227 — bounded review candidate

Research-only. Legacy semantic identifiers and legacy trimmed event hashes remain unchanged. The opt-in report records both the legacy trimmed and raw-line SHA-256 for each completed nonblank line, without making the legacy hash an unambiguous inverse mapping. Duplicate raw representations are separate line entries. Reports contain linkable digests; do not export automatically. Keep original input bytes under existing retention policy; no new durable store is introduced.

The existing agent bridge already has a typed policy for goals and step reports and counts task finishes without triggering actions. The generic consolidator deliberately does not turn unmapped events into claims. The new report distinguishes newly ingested records, semantic-linking events, unmapped events, replay, and blank lines; semantic-linking counts events, not distinct graph nodes or truth. Success reports cover completed structurally valid batches only; errors do not emit a successful report. Blank lines retain legacy skip behavior; this is not a general parser equivalence claim.

Completed LF (including CRLF) is required for both generic ingestion and read-only integrity inspection; the agent bridge rejects incomplete tails before applying any prefix, using a bounded read of the same bytes. This does not establish source authentication, durable atomicity, or full bridge rollback for other error types. No evidence admission, task-completion inference, or trust activation. No history rewrite or numeric sidecar adoption.

Review the six targeted regression cases (three parameterized incomplete-tail controls), legacy tests, and Linux/Windows CI. No local test execution is claimed.
