"""#104 pre-release source contract for static official Ario website route.

This test validates only the proposed *research branch* files, including the
exact inline CSP hash. It does not prove a production deployment or human
screen reader usability. No network, credentials, engine or trust actions.
"""
import base64
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "website"
DEMO = SITE / "ario-demo.html"
HOME = SITE / "index.html"
CONF = SITE / "vercel.json"


def _files():
    return DEMO.read_text(encoding="utf-8"), HOME.read_text(encoding="utf-8"), json.loads(CONF.read_text(encoding="utf-8"))


def _hash(raw):
    return "sha256-" + base64.b64encode(hashlib.sha256(raw.encode("utf-8")).digest()).decode("ascii")


def test_five_cases_and_links_fa_en():
    demo, home, _ = _files()
    assert "Five interactive examples" in demo
    assert "پنج مثال تعاملی" in demo
    assert len(re.findall(r'^\s*h: "[1-5]\)', demo, re.MULTILINE)) == 5
    assert len(re.findall(r'^\s*h: "[۱۱۲۳۴۵]\)', demo, re.MULTILINE)) == 5
    assert 'var selectedAnswers = [null, null, null, null, null];' in demo
    assert 'Interactive Ario demo · 5 fictional evidence exercises (not M0)' in home
    assert 'دموی تعاملی آریو · پنج مثال آموزشی ساختگی (نه موتور M0)' in home
    assert home.count('href="/ario-demo.html"') == 2


def test_live_site_metadata_and_clear_synthetic_warning():
    demo, _, _ = _files()
    assert '<link rel="canonical" href="https://ario-research-independent.vercel.app/ario-demo.html">' in demo
    assert '<meta name="robots" content="index, follow">' in demo
    assert "SYNTHETIC / FICTIONAL" in demo
    assert "is not the Ario M0 engine" in demo
    assert '<a href="/">Ario main site / بازگشت به سایت اصلی آریو</a>' in demo
    assert "I'm fine" in demo
    assert "matching hash" in demo
    assert 'type="button"' in demo
    assert 'aria-live="polite"' in demo


def test_inline_script_and_style_explicitly_hashed_in_strict_site_csp():
    demo, _, conf = _files()
    style = re.findall(r"<style>([\s\S]*?)</style>", demo)
    script = re.findall(r"<script>([\s\S]*?)</script>", demo)
    assert len(style) == len(script) == 1
    csp = next(h["value"] for h in conf["headers"][0]["headers"] if h["key"] == "Content-Security-Policy")
    assert "'" + _hash(style[0]) + "'" in csp
    assert "'" + _hash(script[0]) + "'" in csp
    assert "default-src 'none'" in csp
    assert "connect-src 'none'" in csp
    assert "form-action 'none'" in csp
    assert "'unsafe-inline'" not in csp
    assert "unsafe-eval" not in csp


def test_no_external_script_or_user_upload_surface():
    demo, _, _ = _files()
    assert not re.search(r'<script\b[^>]*src=', demo, re.IGNORECASE)
    assert "<form" not in demo.lower()
    assert "XMLHttpRequest" not in demo
    assert "fetch(" not in demo
    assert "localStorage" not in demo
    assert "navigator.sendBeacon" not in demo
    assert not re.search(r'<input\b|<textarea\b', demo, re.IGNORECASE)


def test_revision_status_is_bilingual_and_separate_from_history():
    s = _files()[0]
    assert '<div class="log" id="rev-view"></div>' in s
    assert '<p id="rev-status" class="sr-only" role="status" aria-live="polite" aria-atomic="true"></p>' in s
    assert s.count("revEraseStatus:") == 2
    assert s.count("revKeepStatus:") == 2
    assert 'var announcement = mode === "erase" ? t.revEraseStatus : t.revKeepStatus;' in s
    assert 'if (status.textContent !== announcement) status.textContent = announcement;' in s
    assert "Teaching erase view:" in s
    assert "Teaching revision view:" in s
    assert "نمایش آموزشی حذف:" in s
    assert "نمایش آموزشی اصلاح:" in s


def test_site_and_docs_explainer_keep_identical_application_script():
    docs = ROOT / "docs" / "ario-explainer-demo-2026-11-08" / "index.html"
    demo, _, _ = _files()
    pattern = r"<script>([\s\S]*?)</script>"
    assert re.findall(pattern, demo) == re.findall(pattern, docs.read_text(encoding="utf-8"))
