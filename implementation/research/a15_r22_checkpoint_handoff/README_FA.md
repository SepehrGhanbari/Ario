# A15 v0.10 — Exact cosigned checkpoint handoff (RESEARCH_ONLY / HOLD)

This version is read-only. It does not submit leaves, sign, publish, alter relay state, or change a retained floor.

It captures the exact HTTP response bytes returned by the Sigsum TEST client's get-tree-head request, parses and verifies the cosigned tree head under the pinned log/witness policy, and saves:
- exact cosigned checkpoint response bytes;
- consistency proofs from retained floors 281653 and 281670 to the captured head;
- the three pinned A15 leaf records and their inclusion proofs against that same head;
- a manifest with per-file SHA-256 digests and explicit unknown/NO_GO boundaries.

The same verifier then reopens the saved bytes and independently re-verifies signatures, cosignature quorum, consistency proofs, leaf signatures, and inclusion proofs. A separate negative audit mutates one signature, one consistency path, one inclusion path, and one leaf checksum while updating the file digest in the manifest; each must still be rejected cryptographically.

Run in Linux/WSL with Go 1.25 and network access:
```sh
go test -count=1 ./...
go run . capture ./out
go run . verify ./out
python3 negative_audit.py ./out .
```

The bundle is a historical checkpoint handoff, not proof of global latest, trusted time, independent administration, independent custody, local fsync, or production authority. Runner clock is explicitly unattested. Keep the ZIP and its outer SHA-256 pin on separately controlled media. No real keys; no trust activation; no production; no merge.


The GitHub Actions read-only verifier is exercised by the stacked draft review workflow; no publication or signing step is included.
