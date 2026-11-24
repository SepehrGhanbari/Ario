# R22.11 — content-addressed recovery of R22.10 synthetic envelope

**RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.**

Parent #356 at 814f69d546d41bb1e30ceac252d215df64d049bc. Prior live Sigsum TEST discovery: [run 45453396739](https://github.com/SepehrGhanbari/Ario/actions/runs/45453396739). Final parent PR checks (Implementation Regression, Published TXT Restore Security, Ario Repo Self Audit Research) all SUCCESS.

## Actual provider round trip (2026-11-24)
Re-downloaded original three public artifact ZIPs 14949671120, 14948912790, 14947504418; SHA256 matched prior record, ZIP CRC checks passed. Extracted only the explicitly public synthetic second envelope and uploaded the exact 515 bytes under the discovered double-SHA256 address in a new private Google Drive lab folder. Listing that folder, exact name equality, one match, no pagination or warnings, then raw materialization to a separate recovery directory returned 515 bytes. Standard Google Drive connector upload attempts failed on the file-reference interface; direct Drive search with exact name returned no results; mounted Drive upload/list/materialize succeeded. No sharing changes. File identifiers omitted from public report.

- Address SHA256(SHA256(raw).digest()): a0ac8945297132b7c869c79b7d08f4b303ee49599112269428013fc83bde3905
- Single SHA256(raw): 501069de56a2f7296cdb61a0ea26845af4666f6bdd3b7e8f3c5a7d5b16e66a5e
- Recovered bytes equal original bytes (cmp), same scope, predecessor bound to first exact bytes, record_count 2 -> 4. Local simulated old state checksum unchanged.
- Actual lookup/materialization by address was orchestrated through connector calls, not embedded in the Python verifier. The caller knew the prior discovery report, and the original second artifact remained accessible to the experiment operator; this is a provider round trip, not a new blinded publication or physically isolated recovery.

## Executable local controls
Run from this directory: `python recovery.py fixtures/first.json fixtures/discovery.jsonl fixtures/recovered.json`. Fixtures are archived public synthetic bytes from the earlier run and this readback, not a live store. Source SHA256 tested locally: 5cb9d7a816271caae2ef1f857e6c3e0c2bc05f8e47fa5e41a393e99cf8d017eb.

16/16 local cases PASS: actual recovered candidate; missing; tampered; old replay at new address; invalid address; oversize; wrong scope; wrong predecessor; non-advancing count; authority claim; boolean count; duplicate JSON key; noncanonical JSON; invalid JSON; incomplete discovery; wrong first binding. Semantic negative controls use recomputed hypothetical candidate checksums; no forged external signatures or external mutations. No real deletion or replacement on Drive. Recovered disposition RECOVERED_LINKED_CANDIDATE_RESEARCH_ONLY; all authority flags remain NO_GO.

## Limits and next experiment
The verifier assumes an authenticated R22.10 discovery result from its caller. It does not independently reverify signatures/Merkle evidence or authenticate a serialized report; malformed report inputs can abort rather than yield structured HOLD. It supports exactly two leaves, not arbitrary chains. A replay of an older internally consistent discovery+object pair is not detectable without independently retained latest floor; stale-head replay remains RED/NOT_ESTABLISHED. The store may delete or replace content; tampering is detectable relative to known expected checksum, availability is not guaranteed. Separate providers do not establish distinct administrative control. No public unauthenticated recovery, real disk restore, global freshness, floor truth, completeness or independent custody demonstrated. Next: separate admin storage/read-only recovery, real disposable-object deletion and replacement, signed-head replay tests, and authenticated discovery-to-recovery handoff. No merge or admission.
