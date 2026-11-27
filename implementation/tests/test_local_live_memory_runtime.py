"""Offline integration of the live adapter with the checked-out cognitive core."""
import importlib.util
import json
from pathlib import Path

from core.memory_consolidation import ConsolidationEngine, ledger_line_digests
from core.source_monitoring import SourceMonitoringGuard
from core.legacy_v153_historical_view import _decode_record
from core.working_memory import WorkingMemoryBuffer
from core.prospective_memory import ProspectiveMemoryRegistry

_PATH = Path(__file__).resolve().parents[1] / "local_live_memory" / "ario_live.py"
_spec = importlib.util.spec_from_file_location("local_live_memory_v07", _PATH)
live = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(live)


def _row(i, user, reply):
    return dict(record_version="15.3", record_id=f"fixture-{i}",
                user=user, ario=reply,
                user_sha256=live.sha(user.encode()),
                ario_sha256=live.sha(reply.encode()),
                event_sha256=live.sha((user + "\n" + reply).encode()))


def test_live_working_focus_uses_checked_out_core(tmp_path):
    archive = tmp_path / "archive.jsonl"
    rows = [_row(i, f"Remember that bicycle detail number {i} is recorded.",
                 "Acknowledged") for i in range(6)]
    raw = "".join(json.dumps(r) + "\n" for r in rows).encode()
    archive.write_bytes(raw)
    memory = live.ChatMemory(archive, ConsolidationEngine, SourceMonitoringGuard,
                             _decode_record, ledger_line_digests)
    assert memory.refresh() == 6
    candidates = memory.recall("bicycle detail")
    assert len(candidates) == 4
    selected = live.working_focus(memory, candidates, WorkingMemoryBuffer)
    assert len(selected) == 4
    assert {r["record_id"] for r in selected} == {r["record_id"] for r in candidates}
    assert archive.read_bytes() == raw
    assert all(r["veracity"] == "REPORTED_UNVERIFIED" for r in selected)


def test_live_prospective_reload_and_single_trigger(tmp_path):
    path = tmp_path / "prospective.json"
    first = live.ChatProspective(path, ProspectiveMemoryRegistry, clock=lambda: 1000)
    assert "PENDING" in first.handle("/remind-when comet-73 | review the fixture")
    iid = first.load().get_pending_intentions()[0].intention_id
    later = live.ChatProspective(path, ProspectiveMemoryRegistry, clock=lambda: 1001)
    assert "No pending" in later.handle("/cue unrelated")
    assert later.load().get_pending_intentions()[0].intention_id == iid
    response = later.handle("/cue comet-73")
    assert iid in response and "review the fixture" in response
    assert not later.load().get_pending_intentions()
    assert "No pending" in later.handle("/cue comet-73")


def test_live_prospective_cancel_and_expiry(tmp_path):
    path = tmp_path / "prospective.json"
    pm = live.ChatProspective(path, ProspectiveMemoryRegistry, clock=lambda: 1000)
    pm.handle("/remind-when cancel-cue | cancelled fixture")
    iid = pm.load().get_pending_intentions()[0].intention_id
    assert "Cancelled" in pm.handle("/cancel-intention " + iid)
    assert "No pending" in pm.handle("/cue cancel-cue")
    pm.handle("/remind-when expire-cue | expired fixture")
    later = live.ChatProspective(path, ProspectiveMemoryRegistry,
                                 clock=lambda: 1000 + live.PROSPECTIVE_TTL)
    assert "No pending" in later.handle("/cue expire-cue")
    assert "EXPIRED" in later.handle("/intentions")
