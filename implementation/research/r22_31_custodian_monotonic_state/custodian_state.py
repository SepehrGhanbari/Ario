#!/usr/bin/env python3
"""Default custodian entrypoint: require a pinned verifier-signed TPM receipt."""
from __future__ import annotations

import sys
from pathlib import Path

RESEARCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_DIR / "r22_33_attested_transition"))

from attested_custodian import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
