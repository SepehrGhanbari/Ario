"""Issue #104 bilingual public explainer source contract (static, no browser attest).

These checks protect presence of the five fictional interactive cases, the
revision control and the separate opposing-evidence exercise. They do NOT
prove deployment, native accessibility, rendering or production safety.
"""
import re
from pathlib import Path

PAGE = (
    Path(__file__).resolve().parents[2]
    / "docs" / "ario-explainer-demo-2026-11-08" / "index.html"
)


def source():
    return PAGE.read_text(encoding="utf-8")


def test_five_synthetic_interactive_cases_in_both_languages():
    s = source()
    assert "پنج مثال تعاملی" in s
    assert "Five interactive examples" in s
    assert len(re.findall(r'^\s*h: "[۱۱۲۳۴۵]\)', s, re.MULTILINE)) == 5
    assert len(re.findall(r'^\s*h: "[1-5]\)', s, re.MULTILINE)) == 5
    assert "var selectedAnswers = [null, null, null, null, null];" in s


def test_no_false_authentication_from_hash_or_signed_looking_image():
    s = source()
    for fragment in ("matching hash", "UNKNOWN", "اصالت امضا", "هشِ درست"):
        assert fragment in s


def test_consent_and_human_relational_scenarios_are_fictional():
    s = source()
    assert 'I said prepare drafts only; not send.' in s
    assert "I'm fine" in s
    assert "mind-reading" in s
    assert "ذهن‌خوانی" in s


def test_existing_revision_and_disputed_evidence_modes_remain_present():
    s = source()
    for anchor in ("revEraseBtn", "revReviseBtn", "evidenceAcceptedBtn",
                   "evidenceDisputedBtn", "CONTESTED", "CONTRADICTED",
                   "REVISED", "UNSUPPORTED", "UNKNOWN"):
        assert anchor in s


def test_static_fictional_demo_keeps_source_and_trust_boundaries():
    s = source()
    assert '<html lang="fa" dir="rtl">' in s
    assert 'document.documentElement.dir' in s
    assert 'document.documentElement.lang' in s
    assert 'aria-live="polite"' in s
    assert "SYNTHETIC / FICTIONAL" in s
    assert "is not the Ario M0 engine" in s
    assert "textContent" in s
    assert "<form" not in s.lower()
    assert "fetch(" not in s
    assert "XMLHttpRequest" not in s
    assert "localStorage" not in s
    assert "navigator.sendBeacon" not in s


# Negative controls for browser transport, independent of a real browser.
import importlib.util
import subprocess
from unittest.mock import patch

SMOKE_PATH = PAGE.parents[2] / "implementation" / "research" / "ario_issue104_browser_smoke.py"
WORKFLOW = PAGE.parents[2] / ".github" / "workflows" / "ario-issue104-browser-smoke.yml"
SPEC = importlib.util.spec_from_file_location("issue104_smoke_under_test", SMOKE_PATH)
assert SPEC is not None and SPEC.loader is not None
SMOKE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SMOKE)
PASS = '<pre id="ario-browser-smoke">ARIO_DEMO_BROWSER_PASS:22</pre>'


def test_browser_marker_positive_and_negative_controls():
    assert SMOKE.executed_check_count(PASS) == 22
    invalid = [
        "",
        SMOKE.JS,
        "<script>const fake = '" + PASS + "';</script>",
        "<!--" + PASS + "-->",
        "<template>" + PASS + "</template>",
        PASS.replace("PASS:22", "FAIL:erase-view"),
        PASS.replace("PASS:22", "PASS:21"),
        PASS.replace("PASS:22", "PASS:999"),
        PASS + PASS,
        PASS.replace("</pre>", ""),
        PASS.replace("PASS:22", "<b>PASS:22</b>"),
        '<div id="ario-browser-smoke">ARIO_DEMO_BROWSER_PASS:22</div>',
    ]
    for output in invalid:
        assert SMOKE.executed_check_count(output) is None, output[:100]


def test_browser_missing_and_exit_fail_closed():
    with patch.object(SMOKE.shutil, "which", return_value=None):
        with patch.object(SMOKE.subprocess, "run") as run:
            assert SMOKE.main() == 2
            run.assert_not_called()
    for code, output, expected in [(1, PASS, 1), (0, "", 1),
                                    (0, SMOKE.JS, 1),
                                    (0, PASS.replace("PASS", "FAIL"), 1),
                                    (0, PASS, 0)]:
        with patch.object(SMOKE.shutil, "which", return_value="fake-browser"):
            with patch.object(SMOKE.subprocess, "run",
                              return_value=subprocess.CompletedProcess([], code, output, "")) as run:
                assert SMOKE.main() == expected
                assert run.call_count == (2 if expected == 0 else 1)
    with patch.object(SMOKE.shutil, "which", return_value="fake-browser"):
        with patch.object(SMOKE.subprocess, "run", side_effect=OSError):
            assert SMOKE.main() == 2


def test_repository_and_ref_guard_contract():
    # Structural test of the actual workflow expression, not Actions execution.
    text = WORKFLOW.read_text(encoding="utf-8")
    guards = re.findall(r"^    if: (.+)$", text, re.MULTILINE)
    assert guards == ["github.repository == 'SepehrGhanbari/Ario' && "
                      "github.ref == 'refs/heads/research/issue104-demo-completion-20261122'"]
    clauses = re.fullmatch(r"github\.repository == '([^']+)' && github\.ref == '([^']+)'",
                           guards[0])
    assert clauses is not None
    repo, ref = clauses.groups()
    for candidate_repo, candidate_ref, expected in [
        (repo, ref, True), ("Other/Ario", ref, False),
        (repo, "refs/heads/main", False), ("Other/Ario", "refs/heads/main", False),
    ]:
        assert ((candidate_repo == repo) and (candidate_ref == ref)) is expected
