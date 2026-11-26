#!/usr/bin/env python3
"""Browser-level smoke for the #104 static bilingual teaching page.

Research/demo only; no secrets, user data, network fixtures or trust admission.
Uses a preinstalled Chrome/Chromium headless browser. FAILS if no browser.
This is not a screen-reader, security penetration test, or production release.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SOURCE = ROOT / "docs/ario-explainer-demo-2026-11-08/index.html"
SOURCE = Path(os.environ.get("ARIO_DEMO_SOURCE", str(_DEFAULT_SOURCE)))
if not SOURCE.is_absolute():
    SOURCE = ROOT / SOURCE
JS = r"""
(() => {
  let checks = 0;
  const ck = (condition, label) => {
    if (!condition) throw new Error(label);
    checks++;
  };
  const byId = id => document.getElementById(id);
  const options = () => Array.from(document.querySelectorAll("#scen-list > .scen"));
  try {
    ck(document.documentElement.lang === "fa" && document.documentElement.dir === "rtl", "fa-rtl");
    ck(options().length === 5, "five-fa-scenarios");
    ck(options().every(x => x.querySelectorAll(".opts button").length === 3), "choice-buttons");
    ck(byId("banner").textContent.includes("SYNTHETIC"), "fictional-banner");
    ck(!document.querySelector("form, input, textarea"), "no-user-upload");
    ck(document.querySelectorAll("script[src],link[href^='http']").length === 0, "no-external-assets");
    const feedback = options()[0].querySelector(".feedback");
    options()[0].querySelector(".opts button:nth-child(2)").click();
    ck(feedback.textContent.includes("درست"), "fa-feedback-updated");
    ck(options()[0].querySelector('.opts button:nth-child(2)').getAttribute("aria-pressed") === "true", "choice-aria-pressed");
    byId("langBtn").click();
    ck(document.documentElement.lang === "en" && document.documentElement.dir === "ltr", "en-ltr");
    ck(options().length === 5 && options()[3].textContent.includes("hash"), "five-en-scenarios");
    ck(options()[4].textContent.includes("fine"), "respectful-human-case");
    ck(options()[0].querySelector('.opts button:nth-child(2)').getAttribute("aria-pressed") === "true", "choice-persist-language");
    const oldEntry = "Permission: the assistant may send emails.";
    const newEntry = "Permission: prepare drafts only.";
    const revision = () => byId("rev-view");
    const entries = () => Array.from(revision().querySelectorAll(".log-entry"));
    const revised = () => entries().length === 2 &&
      entries()[0].classList.contains("struck") &&
      entries()[0].textContent.includes(oldEntry) &&
      entries()[1].classList.contains("new") &&
      entries()[1].textContent.includes(newEntry) &&
      entries()[1].textContent.includes("REVISED") &&
      byId("revEraseBtn").getAttribute("aria-pressed") === "false" &&
      byId("revReviseBtn").getAttribute("aria-pressed") === "true" &&
      byId("rev-status").getAttribute("role") === "status" &&
      byId("rev-status").getAttribute("aria-live") === "polite" &&
      byId("rev-status").getAttribute("aria-atomic") === "true" &&
      byId("rev-status").textContent === "Teaching revision view: the previous record and correction are both retained.";
    ck(revised(), "initial-revision-preserved");
    byId("revEraseBtn").focus();
    byId("revEraseBtn").click();
    ck(entries().length === 1 &&
      entries()[0].classList.contains("new") &&
      entries()[0].textContent.includes(newEntry) &&
      !revision().textContent.includes(oldEntry) &&
      !revision().querySelector(".struck") &&
      revision().textContent.includes("The trail was erased.") &&
      byId("revEraseBtn").getAttribute("aria-pressed") === "true" &&
      byId("revReviseBtn").getAttribute("aria-pressed") === "false" &&
      byId("rev-status").textContent === "Teaching erase view: the previous record is hidden in this view." &&
      document.activeElement === byId("revEraseBtn"), "erase-view");
    byId("revReviseBtn").focus();
    byId("revReviseBtn").click();
    ck(revised() && document.activeElement === byId("revReviseBtn"), "revision-preserved");
    byId("evidenceDisputedBtn").click();
    ck(byId("evidence-output").textContent.includes("CONTESTED"), "disputed-mode");
    ck(byId("evidenceDisputedBtn").getAttribute("aria-pressed") === "true", "disputed-aria");
    byId("evidenceAcceptedBtn").click();
    ck(byId("evidence-output").textContent.includes("CONTRADICTED"), "accepted-mode");
    const required = ["langBtn", "revEraseBtn", "revReviseBtn", "evidenceAcceptedBtn", "evidenceDisputedBtn"];
    ck(required.every(id => byId(id).tagName === "BUTTON"), "native-keyboard-controls");
    ck(!!document.querySelector('#evidence-output[aria-live="polite"]'), "status-announcement");
    byId("langBtn").click();
    ck(document.documentElement.lang === "fa" && options().length === 5 &&
      byId("rev-status").textContent === "نمایش آموزشی اصلاح: سابقهٔ قبلی و اصلاح جدید هر دو حفظ شده‌اند.", "return-fa");
    ck(performance.getEntriesByType("resource").length === 0, "no-auto-network-resources");
    const marker = document.createElement("pre");
    marker.id = "ario-browser-smoke";
    marker.textContent = "ARIO_DEMO_BROWSER_PASS:" + checks;
    document.body.appendChild(marker);
  } catch (exc) {
    const marker = document.createElement("pre");
    marker.id = "ario-browser-smoke";
    marker.textContent = "ARIO_DEMO_BROWSER_FAIL:" + String(exc && exc.message);
    document.body.appendChild(marker);
  }
})();
"""


class _ResultMarker(HTMLParser):
    """Read a real, unique pre element, not script source or comments."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.count = 0
        self.active = False
        self.closed = False
        self.invalid = False
        self.parts = []
        self.inert = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "template", "noscript"):
            self.inert.append(tag)
        if self.active:
            self.invalid = True
        if self.inert:
            return
        ids = [v for k, v in attrs if k == "id"]
        if "ario-browser-smoke" in ids:
            self.count += 1
            if tag != "pre" or len(ids) != 1 or self.active:
                self.invalid = True
            else:
                self.active = True

    def handle_endtag(self, tag):
        if self.inert:
            if tag == self.inert[-1]:
                self.inert.pop()
            return
        if self.active:
            if tag == "pre":
                self.active = False
                self.closed = True
            else:
                self.invalid = True

    def handle_data(self, data):
        if self.active and not self.inert:
            self.parts.append(data)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.active:
            self.invalid = True
        self.handle_endtag(tag)


def executed_check_count(stdout: str) -> int | None:
    parser = _ResultMarker()
    try:
        parser.feed(stdout)
        parser.close()
    except (ValueError, AssertionError):
        return None
    if (parser.count != 1 or parser.active or not parser.closed or
            parser.invalid):
        return None
    matched = re.fullmatch(r"ARIO_DEMO_BROWSER_PASS:([0-9]{1,3})",
                           "".join(parser.parts).strip())
    if matched is None:
        return None
    count = int(matched.group(1))
    return count if count == 22 else None


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    if source.count("</body>") != 1:
        print("ARIO_DEMO_BROWSER_HOLD:unexpected-source-structure")
        return 2
    browser = next(
        (path for name in ("google-chrome", "chromium", "chromium-browser", "chrome")
         if (path := shutil.which(name))), None
    )
    if browser is None:
        print("ARIO_DEMO_BROWSER_HOLD:no-browser-installed")
        return 2
    with tempfile.TemporaryDirectory(prefix="ario-demo-browser-") as temporary:
        test_file = Path(temporary) / "index.html"
        test_file.write_text(
            source.replace("</body>", f"<script>{JS}</script>\n</body>"),
            encoding="utf-8",
        )
        for name, size in (("mobile", "390,844"), ("desktop", "1280,800")):
            cmd = [
                browser, "--headless", "--no-sandbox", "--disable-gpu",
                "--disable-dev-shm-usage", "--disable-background-networking",
                "--no-first-run", "--no-default-browser-check",
                "--virtual-time-budget=1700", f"--window-size={size}",
                "--dump-dom", test_file.as_uri(),
            ]
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True,
                    timeout=35, check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                print(f"ARIO_DEMO_BROWSER_HOLD:{name}:execution-error")
                return 2
            # Require the actual DOM element emitted by the EXECUTED script.
            # A loose regex for PASS can match the JavaScript source text
            # printed by --dump-dom and falsely report success.
            checks = executed_check_count(result.stdout)
            if result.returncode != 0 or checks is None:
                print(f"ARIO_DEMO_BROWSER_FAIL:{name}:"
                      "NONZERO_EXIT_OR_INVALID_EXECUTED_MARKER")
                return 1
            print(f"ARIO_DEMO_BROWSER_PASS:{name}:{checks}")
    print("ARIO_DEMO_BROWSER_RESULT:PASS_STATIC_LOCAL_ONLY_NOT_SCREEN_READER")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
