# Ario Live Memory v0.7 — local execution adapter

This is the byte-identical adapter exercised on Windows by the founder on 2026-11-27 (Git blob c35aafb358879b89bd93d4cc6de00dcbfba180b1). It is an opt-in local execution path, not trust activation, a production release, or a new memory engine.

## Run

An existing compatible V15.4.7/V16.1 controller is required. Supply its local path explicitly; private user files and the original local controllers are not published in this PR.

From the repository root, with local Ollama already running:

```powershell
py -3 implementation/local_live_memory/ario_live.py --install-core --original "C:\path\to\ario_original_lineage.py" --mode active --port 11600 --model qwen2.5:3b --max-predict 128 --timeout 180
```

The installer obtains seven public upstream modules from the exact pinned commit ba4fa6e0e83d48a340322b439072d1c7cad710d9 and checks their Git blob IDs. Subsequent runs can omit --install-core. --check runs startup smoke tests and read-only archive replay without invoking Ollama. --repo requires the exact pinned files, not a moving main checkout. The latest main working_memory.py has a different blob; compatibility of that newer source is tested separately rather than silently changing the tested pin.

The launcher integrates the existing ConsolidationEngine, SourceMonitoringGuard, WorkingMemoryBuffer and ProspectiveMemoryRegistry. Working memory is a query-scoped focus of at most four recorded reports; no automatic LTM flush or cross-turn buffer persistence. The original controller continues to own the archive and specialized routes. Prospective memory accepts explicit commands only: /remind-when CUE | reminder text, /cue CUE, /intentions, /cancel-intention INT-ID. Cues are user reports, not independently verified observations. Reminders are chat-only, expire after seven days by default, and use a separate local journal. No background scheduler or external action. Single active process per journal; journal and archive writes are not one transaction. Local checksums do not prove independent authenticity or rollback protection.

## Observed local results (founder-supplied terminal output, 2026-11-27)

- Pinned replay/retrieval and working/prospective startup smoke tests reported PASS.
- Real Qwen 2.5 3B served via loopback port 11600 received a query with working memory 4/4, empirical ratio 0.00 and UNGROUNDED_HYPOTHESIS; returned the correct current and prior test values.
- A reminder was registered, the chat process exited and restarted, and an explicit cue returned the same intention ID and reminder text. The pending count then returned to zero.
- Earlier in the session, direct source attribution recovered original user record identifiers without asking the model to invent an origin.
- Local adapter package regression suite: 72 tests passed (doubles/mocks and adapter contracts); startup on the user's machine exercised the actual pinned core. These are bounded observations, not proof of universal correctness. No private conversation archive, journal, screenshot or user-specific record identifiers are included.

The tests added to the repository exercise the adapter with the checked-out core, without requiring the original controller or Ollama. Preserve all prior history; no production, signing, Genesis, or trust authority is changed.
