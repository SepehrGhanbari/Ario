# RIO-01 R3 — Linux two-UID metadata-only lab

RESEARCH_ONLY / SYNTHETIC_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE

Run only in the disposable PR #351 Ubuntu CI runner. Root creates a temporary
vault with a 0700 directory and 0600 synthetic JSONL file owned by numeric
UID/GID 61001. Consumer UID/GID 61002 has no supplementary groups and zero
effective capabilities. No persistent users are created. Root copies only
the three actual historical reader/preview/IPC modules into read-only staged
code. The child uses Python -I -B. Root is a trusted test orchestrator.

Falsifiers: owner can read; consumer can read a public control but cannot
open private source for reading or writing, rename/unlink it, write the
root-owned retained digest or overwrite worker code. The root relay accepts
only a fixed metadata lookup shape, chooses the archive path/pin itself, and
rejects raw-quote and caller-supplied-pin requests. Actual worker returns
metadata only. Owner can replace its own source with another internally valid
record; retained original SHA256 must reject it. Deliberate unsafe root
re-pin must accept the changed file, proving the trust assumption matters.

This is a Linux DAC observation, NOT independent custody or a hardened
service. Root controls both identities, code and reference; same-root
compromise, rollback of the root-held pin, kernel exploits, side channels,
authenticated persistent IPC, query privacy, display no-reentry, Windows
ACLs and actual live Ario are NOT_ESTABLISHED/NOT_RUN. The relay runs in the
trusted orchestration script, not a remotely exposed service; its response
is inspected by the coordinator, not delivered to a long-running consumer.
No private archive or real model is read. All fixture files are temporary.
