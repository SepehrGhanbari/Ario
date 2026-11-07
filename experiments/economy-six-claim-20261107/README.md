# Read first — Ario six-claim economy **research-only** lab

**Status:** `RESEARCH_HOLD` · **Owner signer:** `HOLD` · **Genesis / production:** `NO_GO` · **Merge approval:** `NOT_ESTABLISHED`.

This directory is a deterministic, side-effect-free **mock experiment**. It does not perform device work, contact the network, pay anyone, enroll a participant, verify identity, authenticate a requester, or grant economic rights. No earnings are guaranteed by GPU/CPU/phone ownership.

## Read this before older contract paragraphs

The historical section “Added bounded contracts from CodeRabbit #94” of [CONTRACT.md](CONTRACT.md) discusses `compare_mock_opportunity`. **That legacy name and any causal opportunity/fairness inference are SUPERSEDED** by the later *Methodological corrigendum v0.2* in that same file. The current public function `classify_mock_completion_delta` returns **descriptive synthetic count changes only**, not opportunity, equity, entitlement, employment, demand or welfare.

`CompletionCountDelta.NO_DROP` is **not** evidence of fairness. An unchanged completion count is consistent with an unseen eligible worker being excluded, a user opting out, changing demand, or unequal opportunity. `ScenarioAssumptions` are caller-selected fiction, never authenticated evidence; a nonempty string pretending to be a signature is not an independent witness. `MOCK_CORRECT` refers only to an invented output-check result; no real-world `GREEN`, trust activation or payout exists.

Validation is **separate**: `project_reported_receipts` rejects non-exact integer `slot_count` values (including `bool`), counts outside 0–1,000, and malformed mock namespaces. `evaluate` rejects non-exact integer `signed_receipts` (including `bool`), negative values and counts exceeding the **supplied slot-ID list length**; it does not authenticate or validate the projector namespace. Present cost/benefit values are individually validated even when their counterpart is missing. These checks reject internally inconsistent synthetic inputs; they prove nothing about real receipt authorship, actual utility, local device safety, supply/demand or privacy.

**Optional telemetry** must not be conflated with mandatory, *local* thermal/battery STOP. A device that declines optional detailed data upload is not fraudulent or disqualified from non-work assistance. A safe, consented workload, a verified requester need, a beneficiary's real-valued support, and a sustainable funding model are separate claims; none is established by this lab.

## Auditable bounded checks

Run from this directory:

```console
python -m unittest -v test_claim_model
```

- [Windows-neutral synthetic lab at commit `dc9bb2a`](https://github.com/SepehrGhanbari/Ario/actions/runs/42374604475): **39 Python stdlib tests passed**, including new malformed projector-count fixtures.
- [Implementation Regression at `dc9bb2a`](https://github.com/SepehrGhanbari/Ario/actions/runs/42374604466): **SUCCESS**.
- [PR #152](https://github.com/SepehrGhanbari/Ario/pull/152) is still **unmerged**. CodeRabbit's previous exact-head review at `5df4ff1` identified the projector type gap corrected in `dc9bb2a`. Independent verification of later source and GitHub's required approval rules must be performed separately.
- Read [Issue #94](https://github.com/SepehrGhanbari/Ario/issues/94) for peer challenges about offline devices, network partitions, optional telemetry and hidden self-reinforcing forecasts. Those discussions are research proposals, not operator policy.

A green unit test, signed mock receipt, source-code commit SHA or resolved review thread is never a substitute for independent evidence or the protected branch's required Code Owner review. Historical claims and prior RED evidence remain in Git/GitHub history; this read-first file is an additive supersession pointer, not an erasure.
