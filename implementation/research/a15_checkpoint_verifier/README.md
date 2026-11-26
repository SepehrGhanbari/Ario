# A15 archived checkpoint verifier (synthetic TEST research)

Extracted from closed, unmerged #389, corrective source commit cbcc7426aaa9bd39f0852afb5771db0d18392bed. The original live run [45855828021](https://github.com/SepehrGhanbari/Ario/actions/runs/45855828021) verified Remora and Stagemole cosignatures on both archived checkpoints and the live head, checkpoint/event/leaf binding and the Merkle extension. The adverse AI review and correction remain recorded in #389. This utility is deliberately separated from the experimental Broker, publisher, relay and #380 stack.

## Use

From this directory, with Go 1.25, Python 3.13, coincurve 21.0.0 and official Sigsum verifier v0.14.1:
```sh
python -m pip install coincurve==21.0.0
go install sigsum.org/sigsum-go/cmd/sigsum-verify@v0.14.1
go mod tidy
go test -v .
go run . --first-zip ../../tests/fixtures/a15_r22_run_45823494521/A15-FIRST-ONLY.zip --second-zip ../../tests/fixtures/a15_r22_run_45823494521/A15-SECOND-REVEAL-SYNTHETIC.zip
```
Put the Go bin directory on PATH. The default verifies the exact pinned synthetic archives, actual external cosignatures, inclusion and checkpoint bindings, without querying external services. Dependencies may need fetching. Optional `--live --evidence-dir NEW_DIRECTORY` also queries Sigsum TEST and Remora and verifies consistency paths, saving signed head and unsigned status; do not schedule or treat this as a production prerequisite. It will fail closed if the test service is unavailable.

Historical floor 282813 is a coordinate pin; its historical signatures were not retained. No independent payload custody, global latestness, trusted time, operator admission, operational signer, Genesis, or production trust is established. No operational integrations. Do not use real data or keys. This is an accepted bounded research utility, not acceptance of the closed custody research proposal. Original fixtures remain byte-identical and retain their SHA-256 pins.

Sources: live.py blob b040a4921aff134b50b5c809d3b8e004a885fe8b, adapter blob 4ada57ce833f1194bfccb64ad008eaf2be430bd2, bridge main.go blob b8f27f1d7a01d93a07a7b94a4b1832558184708a. Only the verifier functions/constants were extracted from the first two; no publishing, Broker, database, or relay transport code is included. Offline exit is explicit and does not claim live consistency.
