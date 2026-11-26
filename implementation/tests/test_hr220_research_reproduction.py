"""Run #220's existing synthetic research controls in standard regression CI."""
from pathlib import Path
import subprocess
import sys


def test_human_revision_research_suite():
    root = Path(__file__).resolve().parents[2]
    research = root / "research" / "human_revision_v02_20261122"
    completed = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "-v", "test_reference.py"],
        cwd=research,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Ran 9 tests" in completed.stderr, completed.stdout + completed.stderr
