# Ario cloud A/B — results status (2026-11-03)

- `REAL_API_RUN`: **NOT_EXECUTED**.
- `REAL_API_COMPLETED_MESSAGES`: **0 observed from this prepared run**. Historical dialogues reported elsewhere are not silently counted as this run.
- `PREVIOUS_V05_STATE`: **NOT_MOUNTED / NOT_INDEPENDENTLY_READ**; no claim of exact continuation from previous provider-side state.
- `OPENROUTER_ACCOUNT`: **NOT_AUTHENTICATED in connected cloud browser**; login page observed. No `OPENROUTER_API_KEY` available to local execution runtime; Vercel project env list had no variable entries.
- `PREFERRED_MODEL`: `dots-studio/dots-3-note-preview:free`, public listing available, not independently tested with an authenticated request in this turn.
- `INTERIM_LETTER_SHA256`: `cd429bca52699e4ba11c3310f0abaf27d53c12989ff1f4232f657cb34b0b2128`; two uploaded copies matched exactly.
- `LOCAL_SIMULATION`: Python stdlib unittest — **20 PASS**, including 50 generated *mock* messages, separate relayed contexts, 429 pause/resume, hash-chain tamper, truncation, voluntary stop, repeat loop and later extension. **These are not cloud API outputs.**
- `PUBLISHING`: Letter and runner can be staged in a research PR with interim/experimental labels; no real transcript or scientific finding about consciousness/subjective identity is publishable as tested.
- `MERGE`: HOLD until genuine model exchanges are captured, authorized privacy review and independent CodeRabbit research review are complete, and GitHub branch protection/CI requirements are met. #130/#132/#133 are separate engineering/governance efforts.

Next input needed to actually produce the 50 real API messages: the original v0.5 session's complete exported transcript or state, and an authenticated OpenRouter API key in the **owner's own local environment**, never in ChatGPT or GitHub. When a run reaches its window, it pauses with `PAUSED_OPEN_NOT_CLOSED`, not `FINISHED`.

## 2026-11-05 — corrective research status on separate draft PR #144 (append-only)

- This section does **not** alter the 2026-11-03 historical 20-test claim or pretend that it covers the new candidate.
- Original PR #134 source and original run status remain unchanged. The correction is separate, unmerged and review-only.
- Initial RED preserved on draft #145 at `2821729c09c89ba54aa135668d57fc8fc4c256ac`; GitHub-hosted [run 41913976326](https://github.com/SepehrGhanbari/Ario/actions/runs/41913976326) failed, with a 25-method offline suite reporting three failures and two errors.
- Initial GREEN verified at `c0dfd38f49be711dfb507836d89060edfcd0620a`; GitHub-hosted [run 41913944198](https://github.com/SepehrGhanbari/Ario/actions/runs/41913944198) reported 1109 passed and 96 subtests passed; all 25 offline runner cases ran.
- After CodeRabbit identified ambiguous HTTP 429/500 automatic retries, a separate RED draft #148 and further conservative fixes were prepared. Final HTTP-control CI result will be documented separately; do not infer it from initial GREEN.
- No real API dispatch, Windows-native filesystem test, verified provider retry/idempotency contract, or reviewed `REVIEW_ACK` continuation was established. Any ambiguous HTTP or response pause must remain HOLD until a separate safe recovery protocol is approved. `OWNER_SIGNER=HOLD`; `GENESIS/PRODUCTION=NO_GO`; `M0_ADMISSION=NOT_EVALUATED`.
