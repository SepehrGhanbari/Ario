"""Operator-side pin tool for the separated-role research verifier.

Run this from OUTSIDE the candidate repository, then keep the resulting trust
root file outside that repository too. The pin records the exact bytes of the
verifier sources and policy that the verifier will later insist on::

    python -m research.trusted_merge_verifier.pin \
        --verifier-dir <pinned copy> --out <path>/trust_root.json

The pin is a research artifact. A common administrator can rewrite it together
with the verifier, so it is byte integrity, not independent custody.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .trust import POLICY_SCHEMA, TRUST_SCHEMA, load_policy, load_trust_root


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(verifier_dir: Path, pinned_at: str) -> dict:
    directory = verifier_dir.resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("verifier directory is not a directory")
    sources = sorted(path.name for path in directory.glob("*.py") if path.is_file())
    if not sources:
        raise ValueError("verifier directory has no python sources")
    policy = load_policy(directory, {"policy_file": "policy.json", "policy_sha256": "0" * 64})
    if policy["schema"] != POLICY_SCHEMA:
        raise ValueError("unexpected policy schema")
    return {
        "schema": TRUST_SCHEMA,
        "policy_file": "policy.json",
        "policy_sha256": _digest(directory / "policy.json"),
        "verifier_sha256": {name: _digest(directory / name) for name in sources},
        "pinned_at": pinned_at,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verifier-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--pinned-at", default="2026-11-25T00:00:00Z")
    args = parser.parse_args(argv)
    root = build(args.verifier_dir, args.pinned_at)
    args.out.write_text(json.dumps(root, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    load_trust_root(args.out)  # round-trip structural check
    return 0


if __name__ == "__main__":
    sys.exit(main())
