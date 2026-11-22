#!/usr/bin/env python3
"""Browser-level smoke for the #104 static bilingual teaching page.

Research/demo only; no secrets, user data, network fixtures or trust admission.
Uses a preinstalled Chrome/Chromium headless browser. FAILS if no browser.
This is not a screen-reader, security penetration test, or production release.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/ario-explainer-demo-2026-11-08/index.html"
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
    byId("revEraseBtn").click();
    ck(byId("rev-view").textContent.length > 30, "erase-view");
    byId("revReviseBtn").click();
    ck(byId("rev-view").textContent.includes("REVISED"), "revision-preserved");
    byId("evidenceDisputedBtn").click();
    ck(byId("evidence-output").textContent.includes("CONTESTED"), "disputed-mode");
    ck(byId("evidenceDisputedBtn").getAttribute("aria-pressed") === "true", "disputed-aria");
    byId("evidenceAcceptedBtn").click();
    ck(byId("evidence-output").textContent.includes("CONTRADICTED"), "accepted-mode");
    const required = ["langBtn", "revEraseBtn", "revReviseBtn", "evidenceAcceptedBtn", "evidenceDisputedBtn"];
    ck(required.every(id => byId(id).tagName === "BUTTON"), "native-keyboard-controls");
    ck(!!document.querySelector('#evidence-output[aria-live="polite"]'), "status-announcement");
    byId("langBtn").click();
    ck(document.documentElement.lang === "fa" && options().length === 5, "return-fa");
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
            matched = re.search(r"ARIO_DEMO_BROWSER_(PASS|FAIL):([^<\r\n]*)", result.stdout)
            if result.returncode != 0 or not matched or matched.group(1) != "PASS":
                print(f"ARIO_DEMO_BROWSER_FAIL:{name}:"
                      f"{matched.group(2) if matched else 'no-result'}")
                return 1
            print(f"ARIO_DEMO_BROWSER_PASS:{name}:{matched.group(2)}")
    print("ARIO_DEMO_BROWSER_RESULT:PASS_STATIC_LOCAL_ONLY_NOT_SCREEN_READER")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
