# ARIO INTEGRITY GATE V1 (research candidate)

Independent, explicitly invoked acquisition/restore entrypoint, not a Git hook and not a modification of Ario's existing runtime. Obtain this package and its pins through a separately trusted channel. All historical publication assets and the merged R1.4 and coverage helper bytes remain unchanged. The source pin for the current checkout is `89ef7ba466db2e7a267ee7780df348ee9e5920e6`, tree `7b1566d33a52b5bb609976f94501bc63f69d2a09`, 473 files / 96,396,968 bytes, as read from the repository connector. The historical source pin is `05ba5c960aaea96fc6bb80504b53b4d47e7d42f5`, tree `8a9429d396c09fe17682a61dd91cb43672d3cb79`, 204 files / 16,183,258 bytes. The original publication generator at `4731c912ba4b34b302843dd37067822ffb699ba7` has three ZIP metadata entries and a short TXT footer. The candidate uses those exact historical formats only after matching the whole archive SHA-256 and pinned manifest; this is not a general-purpose untrusted TXT parser.

Python 3.10+ and Git for clone modes. In a separately trusted package directory:

```
python -I -B scripts/ario_integrity_gate.py clone --output-parent .
python -I -B scripts/ario_integrity_gate.py startup-probe --output-parent .
python -I -B scripts/ario_integrity_gate.py download-restore --output-parent .
python -I -B scripts/ario_integrity_gate.py restore --input /path/to/ario-full.txt --output-parent .
python -I -B scripts/ario_integrity_gate.py import --input /path/to/ario-full.zip --output-parent .
python -I -B scripts/ario_integrity_gate.py check --directory /path/to/checkout --commit 89ef7ba466db2e7a267ee7780df348ee9e5920e6
python -I -B scripts/ario_integrity_gate.py doi-check --directory /path/to/records --record 24136175
```

Windows: `RUN_INTEGRITY_GATE.cmd` presents the menu and creates a unique JSON report. Clone creates a fresh directory with Git global/system configuration, hooks, submodules, and interactive credentials disabled; it compares the raw worktree with the exact GitHub commit, and never invokes downloaded programs. Only the explicit `startup-probe` additionally runs the pinned official CLI on a fixed synthetic empty request after full verification. It expects epistemic UNKNOWN, not PASS, and supplies no ledger. This is **not** a sandbox or proof that verified code is safe. No general first-start enforcement, private memory access, arbitrary execution command, or changes to existing CLI entrypoints. A direct invocation of those old entrypoints is outside the gate. No automatic execution when using normal clone or download.

Archive import reads bounded regular bytes, checks the exact historical size and SHA-256, requires R1.4's live result on a private staged copy, and uses the originally checked immutable bytes for materialization. Restore verifies the pinned manifest, exact expected source member set, each SHA-256 and Git blob ID; the restored worktree is subsequently compared to the pinned source tree over HTTPS. Metadata scripts are neither extracted nor executed. Only regular source entries supported, no overwrites, no link creation. An interrupted or failed-cleanup stage may remain; do not consume it. DOI check is read-only and covers only the chosen allowlisted record, with all listed files and no extra immediate entries in that record directory. The startup probe is not run for DOI or archive modes.

The trusted OS, runtime, Git executable and path, trusted verifier, TLS trust store and non-hostile parent directories are environmental assumptions; no hostile-local-administrator, general concurrent-modification, atomic-snapshot, Git history/mode, cryptographic identity, independent pin custody, or freshness claim. Git fetch disk consumption not globally bounded, network blocking-operation timeouts are not global deadlines. No production or signing. Exit 0 is bounded preparation or synthetic startup success, 2 rejected, 3 unknown. A successful result does not authorize other execution.

New focused Linux tests: 28/28 (synthetic fixtures and mocked external dependencies). Prior accepted suite rerun: 41/41 (11+25+5). Direct live check returned UNKNOWN, Windows and complete live startup/restore not validated. See logs. Proposed repository admission, requiring scoped owner approval: `scripts/ario_integrity_gate.py`, `scripts/test_ario_integrity_gate.py`, `RUN_INTEGRITY_GATE.cmd`, `docs/ARIO_INTEGRITY_GATE_V1.md` and new evidence under `docs/integrity-gate-v1-evidence/`, append-only root README and ENGINEERING_LOG.md. Existing helpers are not replaced. No repository write occurred.

RESEARCH_ONLY / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE

## Admission and subsequent live Windows evidence

See [bounded closeout](integrity-gate-v1-evidence/README.md). Both explicit startup-probe (473/473) and download-restore ZIP (204/204) succeeded in owner-supplied Windows reports. The earlier live UNKNOWN is retained. The `import` command stages verified archive bytes only; `restore` extracts verified source members. Use `restore` for a local ZIP or TXT if restoration is desired. The fixed startup pin remains the tested pre-admission commit, not the new main. No blanket runtime enforcement or new signature authority.

## Explicit verified runtime audit (non-memory integration)

The original fixed 473-file startup probe and release pins remain unchanged. The new `runtime-audit` operation selects the separate exact merged runtime commit `f158695b60bd2c10061531f6cc56e2ed12db1ca0`, tree `c5c374fce05e0bbc17193ae00dffc67525ed201b`, 636 regular tracked blobs / 97,610,980 bytes, as enumerated from GitHub. From a separately trusted copy of the gate:

```powershell
python -I -B scripts/ario_integrity_gate.py runtime-audit --input request.json --output-parent .
```

Windows menu option 7 uses the same operation. The gate reads an explicit M0 JSON request (up to 20,000 bytes), retains its exact SHA-256, prepares a fresh isolated-directory checkout of the fixed pin, checks its complete raw tracked-byte coverage, and invokes only the existing deterministic `implementation/ario_cli.py` with a private copy of the request. No caller-selected script, arbitrary command, ledger, memory, signer or model execution. An unavailable or mismatched checkout never starts the audit. No automatic launch on clone/download. Output distinguishes preparation/execution success (`MATCH_RUNTIME_AUDIT_COMPLETED`, exit 0) from M0's own PASS/FAIL/UNKNOWN result; even FAIL or UNKNOWN can be a correctly completed audit. Invalid input/read or failed execution is rejected or unknown; an unfinished stage is not accepted. The fixed pin is not a moving main and must not be interpreted as signed, latest, independently trusted or production-authorized. The same environmental assumptions as V1 apply, including no hostile-local-OS sandbox guarantee. The new mode uses the existing checked helper bytes without changing their pins.
