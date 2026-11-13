# ARIO Red-Team Research — TB-003, 13 November 2026

**Status:** EXPLORATORY / reproduced observations / **contract-semantics not yet adjudicated**.  
**Provenance:** AI-assisted skeptical review requested by the project founder; not independent human peer review. Not preregistered.  
**Authority:** Research documentation only; no trusted witnesses, signing, evidence admission, release or production integration.  
**Root discussion:** [Research critique #195](https://github.com/SepehrGhanbari/Ario/issues/195); existing [TB-003 identity-alias hypothesis #129](https://github.com/SepehrGhanbari/Ario/issues/129).

## Fixed subject and preservation

- Evaluator: [`implementation/witness_provenance_experiment.py`](https://github.com/SepehrGhanbari/Ario/blob/972a4199e5c52e1bdab559be623949c7d7a24b69/implementation/witness_provenance_experiment.py)
- Commit: `972a4199e5c52e1bdab559be623949c7d7a24b69` (main at inspection).
- Raw evaluator SHA-256: `71912958bad6db97218ac630cadee6c34c04b286aec99b3f7cda071f8d79f567`
- Git blob SHA-1: `4faf010d73219af63c254097e9c135da68d60078`
- Execution: read-only Windows Python 3.13.14; pinned source fetched and executed in memory with `-B`; no local checkout changes, keys or tokens.
- All inputs are **synthetic**. `LAB` origin and completeness declarations are scenario fixtures, **not authenticated histories**.
- Reproduce: `python -B Resources/REDTEAM_2026-11-13_TB003/reproduce.py`; offline: `python -B .../reproduce.py --file implementation/witness_provenance_experiment.py` **on the pinned commit**, or another file with the exact SHA-256. Script checks source hashes before running.
- The `observations.json` in this folder is a compact transcription of 17 observed outputs and their controls. The executable fixture is the ground truth for reproduction. Original earlier 11-case report is preserved outside this PR in the research conversation as Finding 001; this PR does **not** overwrite that history.

## Finding RT-001 — custody/transfer interpretation

**Question:** Can `LAB_CONDITIONALLY_SEPARATE` remain positive after a later, scenario-declared transfer to a custodian marked compromised, when `HELD_BY` still names the original custodian?

**Reproduced:** yes. Baseline direct custody and P1→P3 `TRANSFERRED_TO` (seq=2) both yield `LAB_CHAIN_PRESENT` for artifact A and `LAB_CONDITIONALLY_SEPARATE`, even if P3 is marked compromised. When `HELD_BY` is changed to P3 and P3 is compromised, `COMPROMISED_BY_SCENARIO` is reported instead. Missing required transfer to a newly declared holder yields `UNKNOWN`.

**Mechanism:** `_custody_for` returns `DIRECT_LAB_CUSTODY` when the capture custodian equals declared holder; the support path omits off-path noncyclic transfers. `evaluate_provenance` builds relevant custody/compromise actors from those selected support paths. See [evaluator L284–339](https://github.com/SepehrGhanbari/Ario/blob/972a4199e5c52e1bdab559be623949c7d7a24b69/implementation/witness_provenance_experiment.py#L284-L339) and [L447–497](https://github.com/SepehrGhanbari/Ario/blob/972a4199e5c52e1bdab559be623949c7d7a24b69/implementation/witness_provenance_experiment.py#L447-L497).

**Strong counterevidence:** an [existing explicit regression test](https://github.com/SepehrGhanbari/Ario/blob/972a4199e5c52e1bdab559be623949c7d7a24b69/implementation/tests/test_witness_provenance_experiment.py#L612-L625) deliberately permits short acyclic off-path transfers in direct-custody cases. Therefore this is **not yet a proved regression**. If the public API intentionally models *existence of a particular historical custody path*, the code may conform. If it is intended to certify *current or exhaustive custody*, the label can be overread. Review must choose the semantics **before** changing code.

## Finding RT-002 — distributed SOURCE identity alias ancestry (existing #129)

**Question:** If `P1` and `P2` denote the same declared SOURCE `object_identity=X`, and `P2 DERIVED_FROM R`, should ancestry through that alias also apply to `P1`?

**Reproduced:** A reaches P1(X). B reaches Q(Y)→R(Z). Separately P2(X)→R(Z). Current evaluator reports `LAB_CONDITIONALLY_DISTINCT`. With the ancestry edge attached directly to P1 rather than aliased P2, it reports `COMMON_SOURCE_DETECTED`. If B directly reaches P2(X), it also reports `COMMON_SOURCE_DETECTED`. Reversing record order does not change the alias result. Marking ancestry self-declared or omitting completeness yields `UNKNOWN`.

**Mechanism:** `_source_set` traverses `DERIVED_FROM` edges by distinct `node_id`, then collapses only *reached* SOURCE nodes to `object_identity`. See [L342–354](https://github.com/SepehrGhanbari/Ario/blob/972a4199e5c52e1bdab559be623949c7d7a24b69/implementation/witness_provenance_experiment.py#L342-L354). This **executes and corroborates the earlier unexecuted diagnostic in #129**, but only the output is settled.

**Semantic caveat:** The existing contract says equal object identities count as one source; it does not unambiguously say an equal ID entails shared complete transitive ancestry of immutable source versions. Only under that stronger, **prospectively adopted** semantics would the distinct verdict be a false positive. This is not claimed to be a live source-forgery exploit.

## Controls and non-findings

- Common control is detected: `COMMON_CONTROL_DETECTED`.
- Exact same direct source identity is detected: `COMMON_SOURCE_DETECTED`.
- Missing transfer to a declared holder returns `UNKNOWN`.
- Incomplete surface declarations and untrusted ancestry do not yield affirmative source independence.
- Every evaluated report retains `evidence_admission=NOT_EVALUATED`. For custody cases, `production_custody_authenticity=NOT_ESTABLISHED`.
- No claim about a human custodian, physical source, live system, or AI consciousness can be inferred.

## Adversarial review acceptance protocol (PROPOSED, NOT RUN)

1. **Predefine semantics:** Is `HELD_BY` current, time-bounded, or existential? Are all valid transfer branches in-scope? Does SOURCE `object_identity` name an immutable version with shared ancestry or merely a declared label?
2. **Freeze labels & blind cases:** Independent researcher creates new fixtures unseen by implementers; counterbalance order and prevent label leakage.
3. **Controls:** connected/disconnected aliases; same/different versions; compromised on/off support path; valid transfer and missing transfer; lab versus candidate provenance; complete/incomplete graph.
4. **Primary failure metric:** rate of *unqualified affirmative verdicts* on fixtures adjudicated as not justifying them under frozen semantics. Report numerator/denominator, confidence interval, false-negative rate, abstentions, runtime, and baseline performance.
5. **Avoid outcome-switching:** preserve this exploratory output, announce any protocol changes before inspecting new results, and retain negative or inconclusive findings without editing this snapshot.
6. **Review gate:** no production bridge, trust activation, signer, governance or existing contract changes from this research-only PR. A later code PR requires separate authority, scope and regression tests.

### فارسی — خلاصه

این بسته دو خروجی واقعی و قابل‌تکرار نشان می‌دهد: (۱) تأیید مشروط جدایی مدیریتی با وجود انتقال خارج از مسیر منتخب و نگهدارندهٔ به‌خطر‌افتاده در سناریو؛ (۲) تفاوت نتیجهٔ استقلال منشأ وقتی یک وابستگی اجدادی به نام دومِ همان هویت منبع متصل است. **اما هنوز ثابت نشده که رفتارها قرارداد رسمی را نقض کرده‌اند.** این پرونده برای نقد مستقل است، نه اثبات هک یا مجوز اصلاح امنیتی.

**Preservation rule:** historical reports and original tests stay intact; this new record may be superseded through an **additional versioned entry**, never silent rewrite.
