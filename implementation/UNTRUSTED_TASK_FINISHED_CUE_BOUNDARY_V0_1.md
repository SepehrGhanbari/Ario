# Untrusted TASK_FINISHED → Prospective Intention Boundary v0.1

**RESEARCH_ONLY / DRAFT / HOLD / NOT_ADOPTED / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO**

Parent: experimental #267, HEAD `bfa621d568771abb39a5535c887e435fee171cba`. Original #210 remains unchanged. No production side effects.

## Actual prior behavior

The replay bridge `EpistemicLedgerBridge.ingest_agent_ledger` reads untrusted JSONL `TASK_FINISHED` and directly calls `ProspectiveMemoryRegistry.evaluate_cues`. That registry function **mutates** matching intentions from `PENDING` to `TRIGGERED` and returns each intention's `action_payload`.

A synthetic ledger with `{"event":"TASK_FINISHED", "task_id":"synthetic-deploy", "status":"COMPLETED", "exit_code":0}` is enough to satisfy a registered condition `status == 'COMPLETED'` when `current_epoch` falls in TTL, even without authentication of the claimed completion.

**Important distinction:** The registry does not actually execute the returned action payload; it produces a state transition and a payload that a future caller could misuse as an instruction. This is not proof of a production deployment.

## Proposed new replay behavior

- Count each `TASK_FINISHED` report in `BridgeAuditSummary.reported_task_finishes_count`.
- **Do not** call the mutating `evaluate_cues` from an untrusted ledger read.
- `triggered_intentions_count` remains zero and `triggered_intentions` remains empty for this replay path. `ProspectiveMemoryRegistry` keeps any matching intentions **PENDING**.
- The existing direct `ProspectiveMemoryRegistry.evaluate_cues` API still works for callers with **separate, independently established event authority**. This patch does not implement such authority.
- Input ledger bytes remain unchanged. No reporting is silently lost: task-finish report count is explicit.

The `BridgeAuditSummary.to_dict()` object gains one additive field. This is a **research-only contract proposal**; compatibility with clients expecting exactly the old schema must be evaluated before adoption.

## Positive and negative tests

1. A self-reported synthetic `COMPLETED` does not mutate registry state, return action payloads, or trigger a synthetic deploy intention.
2. Replaying the same report three times does not consume a pending intention.
3. A reported failure remains a report, not a trigger.
4. Direct registry evaluation still triggers when an explicitly supplied cue matches, serving as a **mechanical positive control** and NOT proof of event authentication.
5. The old #210 test expecting automatic triggers is **explicitly revised**, not silently removed. This is a behavior change; do not merge without approval.
6. Under missing `current_epoch`, no untrusted cues evaluate; no crash from comparison to TTL.
7. Historical prior RED and current GREEN must remain traceable to exact SHAs and GitHub CI.

## Still UNKNOWN / out of scope

- Whether a future privileged consumer executes `triggered_intentions`.
- Whether some real authorized task-completion workflow depends on old automatic bridge triggering. Such consumers need a separate authenticated input path, not a simple `trusted=True` flag supplied by the ledger.
- Whether direct guard empirical functions are protected from unauthorized callers. They are not protected by this replay fix.
- Any process-isolation, signer, witness custody, review authority, or production deployment.

## خلاصهٔ فارسی

صرفِ اینکه در فایل گزارش نوشته شده «کار تمام شد»، نباید نیت بعدی مثل «استقرار» را به وضعیت فعال تبدیل کند. این اصلاحِ آزمایشی گزارش‌های اتمام کار را می‌شمارد ولی خودِ نیت را در وضعیت `PENDING` نگه می‌دارد. اجرای واقعی یا مجوزهای امنیتی دست نخورده‌اند. این تغییر هنوز برای مرج تأیید نشده است.
