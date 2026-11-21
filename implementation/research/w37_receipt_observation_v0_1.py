#!/usr/bin/env python3
"""W37 research-only bridge: original Ario ledger observer/bridge + W36 real receipt.

No M0 imports; no writes, remote calls, signing, issuance, trust activation or
binding W35's synthetic checkpoint to unrelated Ario ledger bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ledger_observation_adapter import observe_ledger
from ledger_audit_bridge import verify_observation_manifest
from research.w36_pinned_sigsum_v0_1 import (
    verify_bytes, PINNED_CHECKPOINT_SHA256, PINNED_PROOF_SHA256,
    PINNED_PUBKEY_SHA256, PINNED_POLICY_SHA256,
)

PROFILE = 'ARIO-W37-DUAL-OBSERVATION-RESEARCH/0.1'
# The *only* four public, synthetic Git text fixtures this profile accepts.
# Git for Windows may check out their LF bytes as CRLF. Never accept a
# transformed candidate unless LF restoration exactly matches the original
# externally pinned SHA-256. The cryptographic verifier still sees only the
# exact original signed byte image; no other text normalization is allowed.
PINNED_FILES = {
    'checkpoint': PINNED_CHECKPOINT_SHA256,
    'proof': PINNED_PROOF_SHA256,
    'pub': PINNED_PUBKEY_SHA256,
    'policy': PINNED_POLICY_SHA256,
}

FILES = {
    'checkpoint': ('checkpoint.PUBLIC_SYNTHETIC.json', 256*1024),
    'proof': ('checkpoint.PUBLIC_SYNTHETIC.json.proof', 64*1024),
    'pub': ('w35-lab-submitter.pub', 4096),
    'policy': ('sigsum-test1-2025.policy', 16*1024),
}


def read_bounded_regular(path: Path, max_bytes: int) -> bytes:
    # Deliberately fail closed for symlinks and oversized/unreadable input files.
    if path.is_symlink() or not path.is_file():
        raise ValueError('REFUSED_NON_REGULAR_OR_SYMLINK')
    with path.open('rb') as fp:
        data = fp.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError('INPUT_SIZE_LIMIT')
    return data


def restore_pinned_checkout_bytes(key: str, raw: bytes) -> tuple[bytes, bool]:
    """Recover Git-for-Windows CRLF only if resulting bytes match a fixed pin."""
    expected_sha256 = PINNED_FILES[key]
    if hashlib.sha256(raw).hexdigest() == expected_sha256:
        return raw, False
    if b'\r\n' in raw:
        restored = raw.replace(b'\r\n', b'\n')
        if hashlib.sha256(restored).hexdigest() == expected_sha256:
            return restored, True
    return raw, False  # Caller/verifier rejects any other mismatched bytes.


def observe_pair(ledger: str | Path, *, w36_inputs: str | Path,
                 supplied_manifest: dict | None = None,
                 claimed_external_bind: str | None = None) -> dict:
    """Only report two observations; never assert W35 attests Ario ledger events."""
    root = Path(w36_inputs)
    checkout_crlf_restored = []
    try:
        blobs = {}
        for key, (name, cap) in FILES.items():
            raw = read_bounded_regular(root / name, cap)
            blobs[key], restored = restore_pinned_checkout_bytes(key, raw)
            if restored:
                checkout_crlf_restored.append(key)
        receipt, details = verify_bytes(blobs['checkpoint'], blobs['proof'],
                                       blobs['pub'], blobs['policy'])
        receipt_status = receipt.receipt_status
        receipt_reason = receipt.reason
    except (OSError, ValueError, TypeError) as exc:
        blobs = {}
        details = {}
        receipt_status, receipt_reason = 'INVALID_OR_UNVERIFIED_RECEIPT', type(exc).__name__

    # Do not reuse a supplied manifest as a source of truth. Verify it via real bridge.
    manifest = observe_ledger(Path(ledger))
    selected = manifest if supplied_manifest is None else supplied_manifest
    verification = verify_observation_manifest(selected, Path(ledger))
    proof_digest = details.get('checkpoint_sha256')
    ledger_digest = manifest.get('sha256') if manifest.get('status') == 'OBSERVED' else None
    same_bytes = bool(proof_digest and ledger_digest and proof_digest == ledger_digest)
    verified = (receipt_status == 'VERIFIED_SYNTHETIC_INCLUSION'
                and manifest.get('status') == 'OBSERVED'
                and verification['status'] == 'OBSERVED')
    # Even hash equality would not prove any event truth or authoritative binding.
    return {
        'profile': PROFILE,
        'result': 'SEPARATE_VALID_OBSERVATIONS' if verified else 'UNKNOWN_OR_REJECTED_INPUT',
        'receipt_status': receipt_status,
        'receipt_reason': receipt_reason,
        'w35_fixture_git_checkout_crlf_restored': sorted(checkout_crlf_restored),
        'w35_checkpoint_sha256': proof_digest,
        'ario_ledger_sha256': ledger_digest,
        'ario_observation_status': manifest['status'],
        'ario_observation_count': manifest.get('event_count', 0),
        'ario_bridge_status': verification['status'],
        'ario_bridge_reason': verification.get('reason'),
        'artifact_byte_equality': same_bytes,
        'cross_artifact_binding': 'NOT_ESTABLISHED',
        'claimed_binding_ignored': claimed_external_bind is not None,
        'actual_ario_events_attested_by_w35': False,
        'independent_event_inventory': 'NOT_ESTABLISHED',
        'historical_event_truth': 'UNKNOWN',
        'snapshot_freshness': 'NOT_CHECKED',
        'temporal_assessment': 'NOT_EVALUATED',
        'evidence_admission': 'NOT_EVALUATED',
        'm0_evidence_created': False,
        'audit_engine_called': False,
        'use_disposition': 'SUSPENDED',
        'may_use': False,
        'signer_authority': 'NONE',
        'trust_activation': 'NO_GO',
        'genesis': 'NO_GO',
        'production': 'NO_GO',
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='W37: non-authorizing read-only research observations')
    parser.add_argument('ledger', help='Existing synthetic Ario-format events.jsonl')
    parser.add_argument('--receipt-dir', required=True, help='Folder with four pinned public W35 test artifacts')
    args = parser.parse_args(argv)
    result = observe_pair(args.ledger, w36_inputs=args.receipt_dir)
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    # This exit code reports only whether both observations were parsed/validated.
    # It NEVER implies evidence admission, historical authenticity or permission to act.
    return 0 if result['result'] == 'SEPARATE_VALID_OBSERVATIONS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
