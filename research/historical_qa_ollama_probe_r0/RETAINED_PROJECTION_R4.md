# RIO-01 R4 — existing external retained reference, synthetic memory projection

RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE

This is a bridge experiment to existing R22.22B/F (#380), exact source
ebec6c0f83bda5003b06b4579454fbaf8ca23f90. Reuse public external paste
https://paste.rs/m18dx (GET only) and two previously verified public synthetic
receipt archives (GitHub artifact IDs 15047051021 and 15045299282). The R22.22F
official Sigsum verifier run 45826658118 previously verified four archived
proofs; R4 verifies exact archived ZIP and external kit byte pins and semantic
transition, not signatures anew. The external kit already contains the
retained ledger SHA256; the local memory fixtures are deterministic new
projections of the existing seq6 and seq8 ledger bytes, NOT new externally
published memory commitments. Exact-byte mapping is conditional on this
version of the projection program.

The actual metadata worker is called with an independently selected derived
pin. A disposable local publisher directory is restored by two os.replace
calls: archive and local pin. Local-only verification accepts the stale
valid fixture (RED); external-reference comparator must reject it.
Absent, changed, or old external reference must HOLD, without fallback to
local pin. Unknown extension must HOLD. An exact current fixture remains
metadata-only, even with a wrong local pin.

No independent custody proof: paste is outside the simulated local rollback
set, but availability/administrator ownership is not attested. GitHub hosts
this verifier and both archived evidence ZIPs; its administrator can replace
the verifier and expected external hash. No generic signature verification,
global latest, independent verifier host, root compromise resistance, real
memory admission, display bridge or Windows ACL result. No publication,
new keys, network service, real archive, model, active memory or merge.
