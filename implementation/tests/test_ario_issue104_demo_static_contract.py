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
