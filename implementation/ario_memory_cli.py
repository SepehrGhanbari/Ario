"""Opt-in research interface; existing M0 ario_cli.py is deliberately unchanged."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

def _ascii_decimal_or_none(text):
    # argparse's int() accepts " 5000", "+5000", "5_000" and non-ASCII digits.
    if isinstance(text, int):
        return text
    if not (isinstance(text, str) and text.isascii() and text.isdigit()):
        return None
    significant = text.lstrip("0") or "0"
    # The maximum permitted value is 10000. Avoid unbounded int conversion.
    return int(significant) if len(significant) <= 5 else None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Ario opt-in cognitive memory research CLI (no M0 authority)."
    )
    parser.add_argument(
        "--ledger",
        help="Input JSONL ledger",
    )
    parser.add_argument(
        "--memory-conflicts",
        "--conflict-report",
        dest="memory_conflicts",
        action="store_true",
        help="Generate and display an epistemic contestation and memory conflict audit report",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format for conflict report (default: markdown)",
    )
    parser.add_argument(
        "--output",
        help="Optional file path to export the report to",
    )
    parser.add_argument(
        "--memory-max-events",
        type=str,
        default=4096,
        metavar="N",
        help="Explicit event ceiling for --memory-conflicts (default 4096; max 10000)",
    )
    parser.add_argument(
        "--inspect-ledger",
        action="store_true",
        help="Perform a read-only crash integrity inspection of the specified --ledger file",
    )
    parser.add_argument(
        "--bridge-agent-ledger",
        action="store_true",
        help="Audit untrusted agent JSONL into recorded-only cognitive memory; do not activate intentions",
    )
    args = parser.parse_args(argv)
    if sum((args.memory_conflicts, args.inspect_ledger, args.bridge_agent_ledger)) != 1:
        parser.error('choose exactly one research operation')
    if args.output and (Path(args.output).exists() or Path(args.output).is_symlink()):
        print(json.dumps({'error': 'HOLD_OUTPUT_EXISTS', 'detail': 'Use a new report path; input and previous records are never replaced.'}), file=sys.stderr)
        return 2

    # 1. Handle memory conflict reporting
    if args.memory_conflicts:
        if not args.ledger:
            print(json.dumps({
                "error": "MISSING_REQUIRED_ARGUMENT",
                "detail": "--ledger path is required for --memory-conflicts",
            }, ensure_ascii=False, sort_keys=True), file=sys.stderr)
            return 2
        max_events = _ascii_decimal_or_none(args.memory_max_events)
        if max_events is None or not 1 <= max_events <= 10000:
            print(json.dumps({
                "error": "INVALID_MEMORY_MAX_EVENTS",
                "detail": "--memory-max-events must be an integer from 1 to 10000",
            }, ensure_ascii=False, sort_keys=True), file=sys.stderr)
            return 2
        try:
            from core.memory_consolidation import ConsolidationEngine
            engine = ConsolidationEngine(max_batch_events=max_events)
            ledger_path = Path(args.ledger)
            if not ledger_path.exists():
                print(json.dumps({
                    "error": "LEDGER_NOT_FOUND",
                    "detail": f"Ledger file does not exist: {ledger_path}",
                }, ensure_ascii=False, sort_keys=True), file=sys.stderr)
                return 2

            engine.ingest_ledger_file(ledger_path)
            report = engine.generate_contestation_report()

            if args.output:
                out_path = Path(args.output)
                # Exclusive creation protects input and existing reports even after the preflight.
                rendered = json.dumps(report.to_dict(), indent=2, ensure_ascii=False) if args.format == 'json' else report.to_markdown()
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with out_path.open('x', encoding='utf-8') as output:
                    output.write(rendered)

            if args.format == "json":
                print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
            else:
                print(report.to_markdown())
            return 0
        except Exception as exc:
            print(json.dumps({
                "error": "MEMORY_CONFLICT_AUDIT_FAILED",
                "detail": str(exc),
            }, ensure_ascii=False, sort_keys=True), file=sys.stderr)
            return 2

    # 2. Handle read-only ledger crash inspection
    if args.inspect_ledger:
        if not args.ledger:
            print(json.dumps({
                "error": "MISSING_REQUIRED_ARGUMENT",
                "detail": "--ledger path is required for --inspect-ledger",
            }, ensure_ascii=False, sort_keys=True), file=sys.stderr)
            return 2
        from core.memory_consolidation import ConsolidationEngine
        report = ConsolidationEngine.inspect_ledger_integrity(Path(args.ledger))
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        return 0 if report.is_clean else 1

    # 3. Handle agent ledger bridge to cognitive memory
    if args.bridge_agent_ledger:
        if not args.ledger:
            print(json.dumps({
                "error": "MISSING_REQUIRED_ARGUMENT",
                "detail": "--ledger path is required for --bridge-agent-ledger",
            }, ensure_ascii=False, sort_keys=True), file=sys.stderr)
            return 2
        from core.ledger_memory_bridge import EpistemicLedgerBridge, BridgeError
        try:
            bridge = EpistemicLedgerBridge()
            summary = bridge.ingest_agent_ledger(Path(args.ledger))
            res_dict = summary.to_dict()
            if args.format == "json":
                out_str = json.dumps(res_dict, indent=2, ensure_ascii=False)
            else:
                out_str = (
                    f"# Epistemic Ledger Memory Bridge Audit\n\n"
                    f"- **Ledger Path:** `{res_dict['ledger_path']}`\n"
                    f"- **Ledger SHA-256:** `{res_dict['ledger_sha256']}`\n"
                    f"- **Total Events Read:** {res_dict['total_events_read']}\n"
                    f"- **Steps Observed:** {res_dict['steps_observed']}\n"
                    f"- **Nodes Consolidated:** {res_dict['nodes_consolidated']}\n"
                    f"- **Contested Nodes:** {res_dict['contested_nodes_count']}\n"
                    f"- **Reported Task Finishes (Unverified):** {res_dict['reported_task_finishes_count']}\n"
                    f"- **Triggered Intentions:** {res_dict['triggered_intentions_count']}\n"
                )
            if args.output:
                with Path(args.output).open("x", encoding="utf-8") as output:
                    output.write(out_str)
            print(out_str)
            return 0
        except (BridgeError, OSError, ValueError) as exc:
            print(json.dumps({
                "error": "BRIDGE_INGESTION_FAILED",
                "detail": str(exc),
            }, ensure_ascii=False, sort_keys=True), file=sys.stderr)
            return 2


    return 2

if __name__ == '__main__':
    raise SystemExit(main())
