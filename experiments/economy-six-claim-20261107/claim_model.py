"""Offline, side-effect-free claim separation for the Ario fair-economy research lane.

This is NOT a scheduler, workload runner, payment system, identity verifier, or
assertion of real-world fairness. Any FIXTURE_CONDITIONAL result is explicitly
conditional on invented independent evidence, not a production admission.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class Verdict(str, Enum):
    MOCK_CORRECT = "MOCK_CORRECT"
    FIXTURE_CONDITIONAL = "FIXTURE_CONDITIONAL"
    REFUTED = "REFUTED"
    UNKNOWN = "UNKNOWN"


CLAIMS = (
    "OUTPUT_CORRECT", "REQUEST_INDEPENDENT", "EXTERNALLY_VALUED_DEMAND",
    "DELIVERED_USABLE_SUPPORT", "BENEFICIARY_CONTROL", "NET_WEAK_DEVICE_BENEFIT",
)


@dataclass(frozen=True)
class ReceiptObservation:
    """Only in-band observations; unique slots or signatures imply no independence."""
    slot_ids: tuple[str, ...]
    signed_receipts: int
    output_check: bool | None = None
    # Positive results here must never upgrade external claims.
    self_reported_delivery: bool | None = None
    self_reported_demand: bool | None = None


@dataclass(frozen=True)
class ExternalFixture:
    """Invented conditions, NOT verified independent evidence from the real world.

    Assertions intentionally require a separate fixture object, so a receipt
    cannot supply its own independent proof. No beneficiary name, ID or location.
    """
    independent_origin_evidenced: bool | None = None
    externally_valued_need_evidenced: bool | None = None
    consented_observation: bool | None = None
    observer_separation_evidenced: bool | None = None
    usable_delivery_observed: bool | None = None
    voluntary_control_evidenced: bool | None = None
    participant_valued_benefit: float | None = None
    energy_data_time_wear_cost: float | None = None


def evaluate(observation: ReceiptObservation, fixture: ExternalFixture | None = None) -> Mapping[str, Verdict]:
    """Classify *toy* claims; evidence of a synthetic mock never proves deployment.

    Contradictory fixture evidence is RED/REFUTED, lack of independent evidence
    is UNKNOWN. Output correctness is the only claim supportable by in-band
    tests, and even that remains a scoped mock observation.
    """
    if observation.signed_receipts < 0 or observation.signed_receipts > len(observation.slot_ids):
        raise ValueError("inconsistent receipt count")
    if len(observation.slot_ids) != len(set(observation.slot_ids)):
        # Duplicate slots cannot be silently counted as independently useful work.
        raise ValueError("duplicate slot ids")
    out: dict[str, Verdict] = dict.fromkeys(CLAIMS, Verdict.UNKNOWN)
    if observation.output_check is True:
        out["OUTPUT_CORRECT"] = Verdict.MOCK_CORRECT
    elif observation.output_check is False:
        out["OUTPUT_CORRECT"] = Verdict.REFUTED
    if fixture is None:
        return out
    if fixture.independent_origin_evidenced is True:
        out["REQUEST_INDEPENDENT"] = Verdict.FIXTURE_CONDITIONAL
    elif fixture.independent_origin_evidenced is False:
        out["REQUEST_INDEPENDENT"] = Verdict.REFUTED
    if fixture.externally_valued_need_evidenced is True:
        out["EXTERNALLY_VALUED_DEMAND"] = Verdict.FIXTURE_CONDITIONAL
    elif fixture.externally_valued_need_evidenced is False:
        out["EXTERNALLY_VALUED_DEMAND"] = Verdict.REFUTED
    if fixture.usable_delivery_observed is False and fixture.consented_observation is True:
        out["DELIVERED_USABLE_SUPPORT"] = Verdict.REFUTED
    elif (fixture.consented_observation is True
          and fixture.observer_separation_evidenced is True
          and fixture.usable_delivery_observed is True):
        out["DELIVERED_USABLE_SUPPORT"] = Verdict.FIXTURE_CONDITIONAL
    if fixture.voluntary_control_evidenced is False:
        out["BENEFICIARY_CONTROL"] = Verdict.REFUTED
    elif fixture.voluntary_control_evidenced is True:
        out["BENEFICIARY_CONTROL"] = Verdict.FIXTURE_CONDITIONAL
    b, c = fixture.participant_valued_benefit, fixture.energy_data_time_wear_cost
    if b is not None and c is not None:
        if not (0 <= b < float('inf') and 0 <= c < float('inf')):
            raise ValueError("invalid mock cost/benefit value")
        out["NET_WEAK_DEVICE_BENEFIT"] = Verdict.FIXTURE_CONDITIONAL if b > c else Verdict.REFUTED
    return out


def local_pilot_admission(*, opted_in: bool, has_enforceable_stop: bool,
                          sensor_fresh: bool | None, within_heat_battery_data_budget: bool | None) -> str:
    """Mock-only refusal rule. NEVER reaches a device or starts a workload."""
    if (opted_in is True and has_enforceable_stop is True
            and sensor_fresh is True and within_heat_battery_data_budget is True):
        return "TOY_ELIGIBLE_NOT_AUTHORIZED_TO_RUN"
    return "REFUSE_OR_STOP"
