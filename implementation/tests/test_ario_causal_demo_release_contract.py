from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML_PATH = ROOT / "website" / "ario-causal-demo.html"
INDEX_PATH = ROOT / "website" / "index.html"
VERCEL_PATH = ROOT / "website" / "vercel.json"
NODE_TEST_PATH = ROOT / "implementation" / "tests" / "test_ario_causal_demo_runtime.js"


def _inline_blocks(tag: str, html: str) -> list[str]:
    return re.findall(rf"<{tag}\b[^>]*>([\s\S]*?)</{tag}>", html, flags=re.IGNORECASE)


def _csp_value() -> str:
    config = json.loads(VERCEL_PATH.read_text(encoding="utf-8"))
    for header in config["headers"]:
        for item in header["headers"]:
            if item["key"].lower() == "content-security-policy":
                return item["value"]
    raise AssertionError("Content-Security-Policy header is missing")


def test_exact_inline_style_and_script_hashes_are_allowlisted() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    csp = _csp_value()
    style_blocks = _inline_blocks("style", html)
    script_blocks = _inline_blocks("script", html)
    assert style_blocks and script_blocks
    for block in style_blocks:
        digest = base64.b64encode(hashlib.sha256(block.strip().encode("utf-8")).digest()).decode("ascii")
        assert f"sha256-{digest}" in csp, f"style hash is not allowlisted: {digest}"
    for block in script_blocks:
        digest = base64.b64encode(hashlib.sha256(block.strip().encode("utf-8")).digest()).decode("ascii")
        assert f"sha256-{digest}" in csp, f"script hash is not allowlisted: {digest}"


def test_strict_csp_has_no_inline_style_or_event_handler_attributes() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    assert re.search(r"\sstyle\s*=", html, flags=re.IGNORECASE) is None
    assert re.search(r"\son[a-z]+\s*=", html, flags=re.IGNORECASE) is None
    assert "unsafe-inline" not in _csp_value()


def test_synthetic_scope_is_explicit_and_no_live_operations_are_claimed() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    assert "no file is read" in html
    assert "no tool is run" in html
    assert "no hash is computed" in html
    assert "no memory is written" in html
    assert "دموی آموزشی کاملاً ساختگی است" in html
    assert "هیچ فایلی خوانده" in html
    assert "fixtureRef" in html
    assert "SYNTHETIC_FIXTURE_N" in html
    assert "file_fingerprint" not in html
    assert "sha256=" not in html


def test_homepage_labels_the_page_as_a_synthetic_dependency_demo() -> None:
    index = INDEX_PATH.read_text(encoding="utf-8")
    assert "Synthetic evidence dependency demo (Issue #208)" in index
    assert "دموی ساختگی گراف وابستگی شواهد" in index


def test_scenario_runtime_and_keyboard_controls() -> None:
    node = shutil.which("node")
    assert node, "Node.js is required for the synthetic scenario runtime test"
    result = subprocess.run(
        [node, "--test", str(NODE_TEST_PATH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
