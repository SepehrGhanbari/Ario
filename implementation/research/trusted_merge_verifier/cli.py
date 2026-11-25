"""CLI for the separated-role research verifier. Always exits nonzero."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .verifier import MAX_CLAIM_BYTES, assess


class InputError(ValueError):
    pass


def _read_claim(path: Path) -> dict:
    if path.is_symlink():
        raise InputError("claim must not be a symlink")
    raw = path.read_bytes()
    if len(raw) > MAX_CLAIM_BYTES:
        raise InputError("claim exceeds byte cap")

    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise InputError("claim has a duplicate JSON member")
            obj[key] = value
        return obj

    def bad_constant(_):
        raise InputError("claim has a nonstandard JSON constant")

    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                      parse_constant=bad_constant)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path,
                        help="Candidate Git repository (untrusted)")
    parser.add_argument("--claim", required=True, type=Path,
                        help="JSON supplied by the evidence supplier")
    parser.add_argument("--trust-root", required=True, type=Path,
                        help="Operator-pinned verifier/policy digest file")
    parser.add_argument("--verifier-dir", type=Path, default=None,
                        help="Pinned verifier source directory")
    parser.add_argument("--mode", choices=["PRE_MERGE", "POST_MERGE"], default=None)
    args = parser.parse_args(argv)
    try:
        claim = _read_claim(args.claim)
        result = assess(args.candidate, claim, trust_root_path=args.trust_root,
                        verifier_dir=args.verifier_dir, requested_mode=args.mode)
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        result = {
            "schema": "ARIO-TRUSTED-MERGE-VERIFICATION-RESEARCH-0.1",
            "disposition": "HOLD",
            "reason": "UNREADABLE_CLAIM",
            "detail": type(exc).__name__,
            "findings": ["UNREADABLE_CLAIM"],
            "assessment_mode": args.mode,
            "scope": "SYNTHETIC_TWO_ROLE_LAB_ONLY",
            "authority": "NON_AUTHORITATIVE_RESEARCH_ONLY",
            "merge_authorized": False,
            "trust_activated": False,
            "evidence": {},
            "epistemic_limit": "No verification was performed.",
        }
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 1  # Never a GREEN required gate; never an authorization to merge.


if __name__ == "__main__":
    raise SystemExit(main())
