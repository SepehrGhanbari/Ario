# Ario cloud A/B — results status (2026-11-03)

- `REAL_API_RUN`: **NOT_EXECUTED**.
- `REAL_API_COMPLETED_MESSAGES`: **0 observed from this prepared run**. Historical dialogues reported elsewhere are not silently counted as this run.
- `PREVIOUS_V05_STATE`: **NOT_MOUNTED / NOT_INDEPENDENTLY_READ**; no claim of exact continuation from previous provider-side state.
- `OPENROUTER_ACCOUNT`: **NOT_AUTHENTICATED in connected cloud browser**; login page observed. No `OPENROUTER_API_KEY` available to local execution runtime; Vercel project env list had no variable entries.
- `PREFERRED_MODEL`: `dots-studio/dots-3-note-preview:free`, public listing available, not independently tested with an authenticated request in this turn.
- `INTERIM_LETTER_SHA256`: `cd429bca52699e4ba11c3310f0abaf27d53c12989ff1f4232f657cb34b0b2128`; two uploaded copies matched exactly.
- `LOCAL_SIMULATION`: Python stdlib unittest — **17 PASS**, including 50 generated *mock* messages, separate relayed contexts, 429 pause/resume, hash-chain tamper, truncation, voluntary stop, repeat loop and later extension. **These are not cloud API outputs.**
- `PUBLISHING`: Letter and runner can be staged in a research PR with interim/experimental labels; no real transcript or scientific finding about consciousness/subjective identity is publishable as tested.
- `MERGE`: HOLD until genuine model exchanges are captured, authorized privacy review and independent CodeRabbit research review are complete, and GitHub branch protection/CI requirements are met. #130/#132/#133 are separate engineering/governance efforts.

Next input needed to actually produce the 50 real API messages: the original v0.5 session's complete exported transcript or state, and an authenticated OpenRouter API key in the **owner's own local environment**, never in ChatGPT or GitHub. When a run reaches its window, it pauses with `PAUSED_OPEN_NOT_CLOSED`, not `FINISHED`.
