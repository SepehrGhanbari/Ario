# First-generation dual-approval signer lab

**Research-only, disposable simulated TPM, synthetic keys; never a real Ario signer.** Retains the bounded demonstrated result from #415 at source 29e75c1a2cdb47ec5eedff2dabc3bb494b8095a5, [CI run 45856611263](https://github.com/SepehrGhanbari/Ario/actions/runs/45856611263). Exact source files and their Go dependency modules are preserved; all source blobs are byte-identical. The original four-job experiment included two separate custody checks; those are not part of this extraction and are not prerequisites for this bounded lab.

The retained integrated job uses swtpm, synthetic Founder and Ario Ed25519 approval signatures, veto, three durable witness reservations, distinct Linux UIDs, receipt verification, retries and seven SIGKILL points. The boundary job intentionally reproduces TPM command-path counterexamples. A successful boundary job means counterexamples were observed, not that the counterexamples are fixed. The first-generation integrated job does not show a winning competing request in the observed run, so liveness is not established.

## Reproduce

Use only a disposable Ubuntu GitHub Actions runner using the dedicated workflow. It installs swtpm and tpm2-tools; the harness runs with root to create isolated synthetic UIDs/directories. Do not execute on the founder's signer or a real TPM host. The workflow uses explicit software-TPM sockets and no real keys. It does not upload secrets, publish checkpoints or modify Ario runtime. No scheduled execution.

## Limits / stop

Same root controls the fixture; no independent administration or hardware custody, no continuous multi-generation signer, no physical exactly-once guarantee, no Genesis, trust activation or production. The successful bounded lab is preserved in main as research, not as operational authority and not as acceptance of #415's full stacked branch. No new experiments are necessary for this bounded retention.
