"""R16.1 proposed regressions for #315 + R16 patch + R16.1 addendum.

RESEARCH_ONLY. No true security, publisher-custody or durability claim.
Place in implementation/tests/ ONLY after owner approval.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.memory_consolidation import ConsolidationEngine, ConsolidationError
from core.working_memory import WorkingMemoryBuffer
from core.source_monitoring import SourceAttribution, SourceType, VeracityState


HERE = Path(__file__).resolve().parents[1]


def _make_ledger(path, count):
    with path.open('w', encoding='utf-8', newline='\n') as f:
        for i in range(count):
            f.write(json.dumps({'concept': f'c{i%50}', 'assertion': f'a{i}'}) + '\n')


def _run_cli(ledger, *options):
    return subprocess.run(
        [sys.executable, str(HERE/'ario_memory_cli.py'), '--memory-conflicts',
         '--ledger', str(ledger), '--format', 'json', *options],
        text=True, capture_output=True, cwd=str(HERE), check=False,
    )


def test_r16_1_large_cli_requires_explicit_ceiling(tmp_path):
    ledger = tmp_path/'5000.jsonl'
    _make_ledger(ledger, 5000)
    default = _run_cli(ledger)
    assert default.returncode == 2
    assert 'HOLD_BATCH_TOO_LARGE' in default.stderr

    requested = _run_cli(ledger, '--memory-max-events', '5000')
    assert requested.returncode == 0, requested.stderr
    assert json.loads(requested.stdout)['total_nodes'] == 5000


def test_r16_1_cli_rejects_out_of_policy_limits(tmp_path):
    ledger = tmp_path/'one.jsonl'
    _make_ledger(ledger, 1)
    for candidate in ('0', '-1', '10001'):
        result = _run_cli(ledger, '--memory-max-events', candidate)
        assert result.returncode == 2
        assert json.loads(result.stderr)['error'] == 'INVALID_MEMORY_MAX_EVENTS'


def test_r16_1_long_physical_line_rejected_before_ingestion(tmp_path):
    ledger = tmp_path/'long.jsonl'
    ledger.write_bytes(b'{"concept":"c","assertion":"a"}' + b' ' * 1_048_577 + b'\n')
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError, match='HOLD_LEDGER_LINE_TOO_LARGE'):
        engine.ingest_ledger_file(ledger)
    assert not engine.nodes
    assert not engine.known_ledger_hashes


def test_r16_1_valid_prefix_then_oversized_line_is_not_committed(tmp_path):
    ledger = tmp_path/'prefix.jsonl'
    ledger.write_bytes(b'{"concept":"ok","assertion":"first"}\n' +
                       b'{"concept":"huge","assertion":"' + b'x' * 1_048_577 + b'"}\n')
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError, match='HOLD_LEDGER_LINE_TOO_LARGE'):
        engine.ingest_ledger_file(ledger)
    assert engine.nodes == {}


def _hyp(ident):
    return SourceAttribution(
        attribution_id=ident, assertion=f'claim {ident}',
        source_type=SourceType.INTERNAL_HYPOTHESIS,
        veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
        created_at='2026-01-01T00:00:00+00:00',
    )


@pytest.mark.xfail(strict=True, reason='DESIGN_HOLD: flush_to_long_term remains partial on second LTM failure')
def test_r16_1_flush_should_be_transactional_design_hold():
    class FailOnSecond(ConsolidationEngine):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def ingest_event_stream(self, events):
            self.calls += 1
            if self.calls == 2:
                raise ConsolidationError('synthetic second-save failure')
            return super().ingest_event_stream(events)

    engine = FailOnSecond()
    wm = WorkingMemoryBuffer(consolidation_engine=engine)
    wm.ingest('first', 'claim first', _hyp('first'))
    wm.ingest('second', 'claim second', _hyp('second'))
    with pytest.raises(ConsolidationError, match='synthetic second-save failure'):
        wm.flush_to_long_term()
    # Future atomic contract: neither a partial LTM write nor a partial WM
    # consolidation acknowledgement should survive the failed flush.
    assert engine.nodes == {}


def test_r16_1_total_ledger_byte_budget_before_ingestion(tmp_path):
    ledger = tmp_path/'too_big.jsonl'
    with ledger.open('wb') as f:
        f.write(b'{"concept":"c","assertion":"a"}\n')
        f.truncate(64 * 1024 * 1024 + 1)
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError, match='HOLD_LEDGER_BYTES_TOO_LARGE'):
        engine.ingest_ledger_file(ledger)
    assert not engine.nodes


def test_r16_1_exact_line_budget_accepted(tmp_path):
    ledger = tmp_path/'exact_line.jsonl'
    content = b'{"concept":"ok","assertion":"within max line"}'
    data = content + b' ' * (1_048_576 - len(content) - 1) + b'\n'
    assert len(data) == 1_048_576
    ledger.write_bytes(data)
    engine = ConsolidationEngine()
    assert engine.ingest_ledger_file(ledger) == 1
    assert len(engine.nodes) == 1
