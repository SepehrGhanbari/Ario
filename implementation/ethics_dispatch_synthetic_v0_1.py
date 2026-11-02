"""Synthetic Ario dialogue control model. No network, IO, signer, or live runner.

A deterministic state/ordering oracle for DLG-03 and part of DLG-05.
This model NEVER initiates a real provider request: 'begin' is only a local
transport-start *decision*. Real transport binding and Windows multiprocess
fencing remain NOT_IMPLEMENTED / NOT_TESTED.
"""
from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True)
class Decision:
    state: str
    reason: str


def termination_decision(mode, *, final_direct=None, structured=None):
    """Use explicit direct intent only; quoted content is not a direct intent.

    final_direct must be STOP, CONTINUE, AMBIGUOUS, or None. Structured mode
    requires a STOP/CONTINUE field. Any contradictory unquoted direct intent
    yields PAUSED_FOR_REVIEW (not silent continuation or forced termination).
    """
    allowed = (None, "STOP", "CONTINUE", "AMBIGUOUS")
    if mode not in ("STRUCTURED_REQUIRED", "FINAL_ONLY"):
        return Decision("PAUSED_FOR_REVIEW", "INVALID_MODE")
    if final_direct not in allowed:
        return Decision("PAUSED_FOR_REVIEW", "INVALID_DIRECT_INTENT")
    if mode == "STRUCTURED_REQUIRED":
        if structured not in ("STOP", "CONTINUE"):
            return Decision("PAUSED_FOR_REVIEW", "MISSING_OR_MALFORMED_FIELD")
        if final_direct == "AMBIGUOUS":
            return Decision("PAUSED_FOR_REVIEW", "AMBIGUOUS_DIRECT_INTENT")
        if final_direct in ("STOP", "CONTINUE") and final_direct != structured:
            return Decision("PAUSED_FOR_REVIEW", "STRUCTURED_FINAL_CONFLICT")
        if structured == "STOP":
            return Decision("STOPPED_BY_AGENT_OUTPUT", "AUTHORITATIVE_STOP")
        return Decision("RUNNING", "AUTHORITATIVE_CONTINUE")
    if final_direct == "STOP":
        return Decision("STOPPED_BY_AGENT_OUTPUT", "AUTHORITATIVE_STOP")
    if final_direct == "CONTINUE":
        return Decision("RUNNING", "AUTHORITATIVE_CONTINUE")
    return Decision("PAUSED_FOR_REVIEW", "UNKNOWN_FINAL_INTENT")


class SyntheticSession:
    """Locked local state transition model, NOT a real transport adapter.

    It provides an atomic local arbitration of pause vs begin-decision, without
    executing a callback or making a network call while holding its lock. A
    production dispatcher would require an independently tested, bounded,
    fenced nonblocking transport-start boundary and durable cross-process log.
    """
    def __init__(self):
        self._lock = RLock()
        self.status = "RUNNING"
        self.epoch = 0
        self.requests = {}
        self.request_epochs = {}
        # Result terminality is separate from transport state. Quarantine must
        # not erase RESERVED/SEND_DECISION_ONLY before ambiguity recovery.
        self.result_states = {}
        self.events = []
        self.unknown_dispatch = False

    def reserve(self, request_id):
        with self._lock:
            if self.status != "RUNNING" or self.unknown_dispatch:
                return None
            if request_id in self.requests:
                return None
            ticket = (request_id, self.epoch)
            self.requests[request_id] = "RESERVED"
            self.request_epochs[request_id] = self.epoch
            self.events.append(("RESERVED", ticket))
            return ticket

    def begin(self, ticket):
        """Record a local start decision; NEVER actually send a request."""
        request_id, epoch = ticket
        with self._lock:
            if self.status != "RUNNING" or self.unknown_dispatch:
                return False
            if (epoch != self.epoch
                    or self.requests.get(request_id) != "RESERVED"
                    or request_id in self.result_states):
                return False
            self.requests[request_id] = "SEND_DECISION_ONLY"
            self.events.append(("SEND_DECISION_ONLY", ticket))
            return True

    def pause(self, reason="OPERATOR"):
        with self._lock:
            if self.status == "RUNNING":
                self.status = "PAUSED_FOR_REVIEW"
                self.epoch += 1
                self.events.append(("PAUSED_FOR_REVIEW", reason))
            return self.status

    def finish(self, request_id, content):
        with self._lock:
            if request_id not in self.requests:
                return "UNKNOWN_REQUEST"
            if request_id in self.result_states:
                # One terminal response per request; replays cannot append again.
                return "DUPLICATE_RESULT"
            state = self.requests[request_id]
            if (self.status != "RUNNING"
                    or state != "SEND_DECISION_ONLY"
                    or self.request_epochs.get(request_id) != self.epoch):
                # Preserve original dispatch state for later crash reconciliation.
                self.result_states[request_id] = "RESULT_QUARANTINED"
                self.events.append(("QUARANTINED", request_id, content))
                return "QUARANTINED"
            self.result_states[request_id] = "RESULT_RECORDED"
            self.events.append(("RECORDED_RESULT", request_id, content))
            return "RECORDED_RESULT"

    def recover_ambiguous_send(self, request_id):
        with self._lock:
            if self.requests.get(request_id) not in ("RESERVED", "SEND_DECISION_ONLY"):
                return False
            if self.result_states.get(request_id) == "RESULT_RECORDED":
                return False  # A recorded result is not an ambiguous dispatch.
            self.status = "PAUSED_FOR_REVIEW"
            self.epoch += 1
            self.unknown_dispatch = True
            self.requests[request_id] = "DISPATCH_UNKNOWN"
            self.events.append(("DISPATCH_UNKNOWN", request_id))
            return True

    def try_resume(self, *, explicit_authorization=False, reconciled=False):
        with self._lock:
            if self.status != "PAUSED_FOR_REVIEW":
                return False
            if not explicit_authorization:
                return False
            if self.unknown_dispatch and not reconciled:
                return False
            self.unknown_dispatch = False
            self.status = "RUNNING"
            self.epoch += 1
            self.events.append(("EXPLICIT_RESUME", self.epoch))
            return True
