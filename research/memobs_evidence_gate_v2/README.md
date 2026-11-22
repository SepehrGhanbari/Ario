# MEM-OBS-01: Evidence-admission gate (synthetic Python fixture)

**State:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NO_TRUST_ACTIVATION / NO_PRODUCTION

This is a **standalone correction to Lovable's experimental Python memory-observability demo**. It does not modify Ario's core memory engine, and does not patch or validate the original Lovable HTML dashboard. The HTML artifact is not present in this evidence package.

## One falsifiable question

Can a record author obtain `SUPPORTED` or `ACCEPTED` by adding a nonempty `raw_evidence`, self-asserting `SIGNED_WITNESS` / `LOCAL_EMPIRICAL`, or providing a SHA-256 digest?

- **Original synthetic fixture:** YES. Its `_evaluate_initial_status` granted `SUPPORTED` when a caller's raw-evidence string was nonempty.
- **This standalone corrected fixture:** NO for the exercised constructor, public setter and journal ingestion paths. All such unverified records remain `RECORDED`, while source absence remains `UNKNOWN` and unverified AI narrative is labeled `UNSUPPORTED` diagnostically.
- A legitimate **recording** still succeeds. This fixture intentionally has **no authorized route to a positive `SUPPORTED` transition**; no independent evidence authority is claimed.

## Exact provenance

The corrected fixture derives from the founder-supplied `test_memory_observability.py`, SHA256 `188cc50e9b32f0ca6e87a041d827dfcfc669412b542af2175e03b211d228ae3a`. This original file was provided in a separate research conversation; its bytes are not newly committed to this directory. The corrected model was independently examined in the same session and had SHA256 `968b497c30ec5b2fed9124ca5f5accfb8751887f36650422d7a69391234f9fdc`. The focused regression source SHA256 was `0d1470651d1ab561cb072dc058423e2785e86480d982b01c6d8969530fa86e4e`.

Related existing design tracker: [Issue #81](https://github.com/SepehrGhanbari/Ario/issues/81) — external evidence admission and authority, which remain unresolved. This research fixture neither implements that authority nor changes its scope.

## Reproduction (Python standard library only)

From this directory:

```bash
python -B test_memory_observability_gate_regression.py
python -B test_memory_observability_evidence_gate_fixed.py
```

In the original research environment, the focused regression produced `14/14 PASS` on the corrected fixture, and `10 failures + 1 error` on the original unpatched fixture; the six adapted demonstration examples were `6/6 PASS`. The old comparison is not rerunnable solely from these two committed sources because the exact original Lovable fixture is intentionally not duplicated here. A temporary mutation restoring `raw_evidence => SUPPORTED` was detected by the tests. Verification is strictly about the Python demo's exercised paths.

## Explicit safety and epistemic limits

- `status` is read-only through the public property and ingest rejects privately forged stronger status. This is **not** a robust boundary against arbitrary code in the same interpreter, hostile pickle/snapshots, or write access to the journal internals.
- The demo still updates previous in-memory status/audit annotations during revision or contestation. Retaining old records in RAM is not equivalent to an append-only, nonrollbackable, independently held event history.
- No externally authenticated witness, verifier floor, evidence admissibility, or truth adjudication is introduced.
- `OBSERVED != AUTHENTICATED != AUTHORIZED != ADMITTED != TRUE`, `MEMORY != TRUTH`, `REVISION != ERASURE`, `UNKNOWN` valid.
- No real keys, signer, Genesis, governance, or production changes. This draft is for review only.
