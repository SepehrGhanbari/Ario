# Ario economy: indistinguishable benefit-worlds contract v0.1

**RESEARCH ONLY / NO NETWORK, PAYMENTS, HARDWARE, IDENTITY, AUTHORITY OR ADMISSION.**

Linked public discussion: [Ario Issue #94](https://github.com/SepehrGhanbari/Ario/issues/94#issuecomment-6691587038). The current CodeRabbit critique recognizes six separate claims and warns that signed receipts alone cannot distinguish independent demand from captured demand or real delivery from colluding false reports. **The code implements a toy subset, not the full proposed governance or fairness mechanism.**

## Scope and interpretation

- `MOCK_CORRECT`: a synthetic task-specific check reported pass. Does not prove independent need or funded settlement.
- `FIXTURE_CONDITIONAL`: a caller-selected `ScenarioAssumptions` field **assumes** the named claim for the synthetic world; the code verifies no external independence. This must **never** be translated into a real-world `GREEN` or an authorization to distribute money, do work or gather identity data.
- `REFUTED`: fixture supplies direct contradictory mock evidence to the named claim.
- `UNKNOWN`: no admissible evidence in the toy inputs. Not a judgment that a person is dishonest or ineligible for assistance.

The six claims in `CLAIMS` are disjoint. There is intentionally no `PAYOUT_APPROVED`, `REAL_PERSON_VERIFIED`, `FAIRNESS_PROVEN`, or `PRODUCTION_READY`. Two distinct `HiddenScenario` objects (independent vs captured) each pass through `project_reported_receipts`; that generator explicitly omits hidden controller/delivery truth. Their projected in-band observations are equal, while independently generated different self-report inputs are *not* equal. A policy seeing equal projections must issue equal verdicts. This is a synthetic observational-equivalence counterexample, **not** proof about actual receipt signatures or human behavior. A positive real-world conclusion based only on receipts is therefore unsupported.

The local-device pilot refusal helper does not contact any device. An apparent positive means only `TOY_ELIGIBLE_NOT_AUTHORIZED_TO_RUN`; even a mock-safe input is not permission or evidence of physical safety. No earnings are guaranteed, no enrollment or government ID is required, and any help for people outside the computational network must remain an independent policy discussion with privacy and delivery uncertainty explicit.

## Commands

From this directory: `python -m unittest -v test_claim_model`. Standard-library-only, no credentials, no network or side effects; explicitly invented data.

## Limits and proposed falsifiers

This model **does not prove independence**. It trusts the fields of `ExternalFixture` under stated assumptions; a colluding observer can falsely fill them. A future negative control should supply a valid-looking independent attestation from a common-controlled observer; real-world verdict must stay `UNKNOWN`. The model does not assess requester beneficial ownership, offline delivery, welfare by unobserved populations, safe device containment or economic viability. Missing data are not zero. Pending independent review before any promotion beyond this lab.

**OWNER_SIGNER=HOLD · GENESIS/PRODUCTION=NO_GO · M0_ADMISSION=NOT_EVALUATED.**
