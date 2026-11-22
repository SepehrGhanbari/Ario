"""R21 A source-derived failure vocabulary contract (no network, no secrets).

Walk the actual reader source using AST to compare explicitly-emitted reason
literals with the validator allowlist in BOTH directions. This is a lexical
regression guard, NOT complete dynamic reachability or trusted provenance.
"""
import ast
import re
from pathlib import Path

from research import guard_v2_manual_report as validator

IMPL = Path(__file__).resolve().parents[1]
RESEARCH = IMPL / "research"
READ_GRAPH = RESEARCH / "guard_v2_review_graph.py"
READ_MANUAL = RESEARCH / "guard_v2_trusted_manual.py"
READ_REST = IMPL / "ario_repo_self_audit.py"
TOKEN = re.compile(r"[A-Z0-9_]{3,}\Z")


def _call_name(node):
    if isinstance(node.func, ast.Name):
        return node.func.id
    return getattr(node.func, "attr", "")


def _literals(node):
    return {n.value for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and TOKEN.fullmatch(n.value)}


def _tree(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _emitted(graph_tree, manual_tree):
    reasons = set()
    for t in (graph_tree, manual_tree):
        for n in ast.walk(t):
            if isinstance(n, ast.Call):
                name = _call_name(n)
                if name == "require" and len(n.args) >= 2:
                    reasons.update(_literals(n.args[1]))
                elif name in ("ReviewGraphUnknown", "_hold") and n.args:
                    reasons.update(_literals(n.args[0]))
            if isinstance(n, ast.Assign):
                if any(isinstance(target, ast.Subscript)
                       and isinstance(target.slice, ast.Constant)
                       and target.slice.value == "reason" for target in n.targets):
                    reasons.update(_literals(n.value))
    reasons.difference_update(validator.SUCCESS_REASONS)
    reasons.difference_update({"GRAPHQL_HTTP_", "GRAPH_"})
    return reasons


def _rest_get_json_reasons(rest_tree):
    cls = next(n for n in rest_tree.body
               if isinstance(n, ast.ClassDef) and n.name == "GitHubReadOnly")
    reasons, prefixes = set(), set()
    for n in ast.walk(cls):
        if not isinstance(n, ast.Call):
            continue
        name = _call_name(n)
        if name == "ReadUnknown" and n.args:
            val = n.args[0]
            if isinstance(val, ast.Constant):
                reasons.add(val.value)
            elif isinstance(val, ast.BinOp) and isinstance(val.left, ast.Constant):
                prefixes.add(val.left.value)
        if name == "_object" and len(n.args) == 2 and isinstance(n.args[1], ast.Constant):
            reasons.add("INVALID_" + n.args[1].value)
    return reasons, prefixes, {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}


def test_graph_and_manual_reasons_exactly_match_source_ast():
    expected = _emitted(_tree(READ_GRAPH), _tree(READ_MANUAL))
    actual = set(validator.GRAPH_REASON_LITERALS) | set(validator.MANUAL_REASON_LITERALS)
    assert actual == expected, {
        "accepted_but_unemitted": sorted(actual - expected),
        "emitted_but_rejected": sorted(expected - actual),
    }


def test_rest_failure_reasons_exactly_match_get_json_ast():
    expected, prefixes, functions = _rest_get_json_reasons(_tree(READ_REST))
    assert set(validator.REST_REASON_LITERALS) == expected
    assert prefixes == {"GITHUB_HTTP_"}
    assert functions == {"__init__", "get_json"}


def test_reader_rest_calls_remain_bound_to_narrow_reachable_api():
    t = _tree(READ_MANUAL)
    names = {f"{n.value.id}.{n.attr}" for n in ast.walk(t)
             if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
             and n.value.id == "rest"}
    assert names == {"rest.API", "rest.GitHubReadOnly", "rest.ReadUnknown"}


def test_added_graph_reason_would_trigger_drift_failure():
    graph = _tree(READ_GRAPH)
    fake = ast.parse('require(False, "NEW_GRAPH_FAILURE_REASON")').body[0]
    graph.body.append(fake)
    changed = _emitted(graph, _tree(READ_MANUAL))
    allowed = set(validator.GRAPH_REASON_LITERALS) | set(validator.MANUAL_REASON_LITERALS)
    assert "NEW_GRAPH_FAILURE_REASON" in (changed - allowed)


def test_extra_allowlist_reason_would_trigger_drift_failure():
    actual = set(validator.GRAPH_REASON_LITERALS) | set(validator.MANUAL_REASON_LITERALS)
    expected = _emitted(_tree(READ_GRAPH), _tree(READ_MANUAL))
    assert "DECISION_APPROVED_BY_USER" in (actual | {"DECISION_APPROVED_BY_USER"}) - expected
