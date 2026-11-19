#!/usr/bin/env python3
"""W20 research-only RFC9162-style Merkle producer for *synthetic* Ario events.

SHA-256 leaf and branch domain separation as in RFC9162 section 2.1.1.
Compact inclusion and consistency proof generation are educational, not a
C2SP log protocol endpoint. All event payloads are SHA digests of made-up text.
No Ario, founder, trust, production, or persistent signing keys are accessed.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ORIGIN = 'ario-w20-synthetic.test.invalid/research-log-v1'
DOMAIN = 'ARIO_W20_SYNTHETIC_CHECKPOINT_ED25519_V1'
MAX_LEAVES = 64


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf8')


def leaf_hash(value: bytes) -> bytes:
    return hashlib.sha256(b'\x00' + value).digest()


def combine(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b'\x01' + left + right).digest()


def low_split(n: int) -> int:
    if n < 2:
        raise ValueError('need at least 2 leaves')
    return 1 << ((n - 1).bit_length() - 1)


def root(leaves: list[bytes]) -> bytes:
    n = len(leaves)
    if n == 0:
        return hashlib.sha256(b'').digest()
    if n == 1:
        return leaf_hash(leaves[0])
    split = low_split(n)
    return combine(root(leaves[:split]), root(leaves[split:]))


def inclusion_path(leaves: list[bytes], index: int) -> list[bytes]:
    n = len(leaves)
    if not (0 <= index < n <= MAX_LEAVES):
        raise ValueError('index or size out of range')
    if n == 1:
        return []
    split = low_split(n)
    if index < split:
        return inclusion_path(leaves[:split], index) + [root(leaves[split:])]
    return inclusion_path(leaves[split:], index - split) + [root(leaves[:split])]


def consistency_path(leaves: list[bytes], old_size: int) -> list[bytes]:
    new_size = len(leaves)
    if not (0 < old_size <= new_size <= MAX_LEAVES):
        raise ValueError('size out of range')
    if old_size == new_size:
        return []
    def walk(arr: list[bytes], m: int, matched_subtree: bool) -> list[bytes]:
        if m == len(arr):
            return [] if matched_subtree else [root(arr)]
        split = low_split(len(arr))
        if m <= split:
            return walk(arr[:split], m, matched_subtree) + [root(arr[split:])]
        return walk(arr[split:], m - split, False) + [root(arr[:split])]
    return walk(leaves, old_size, True)


def synthetic_events() -> list[dict]:
    samples = [
        ('INGEST', 'untrusted public article asserted an action was approved', 'EXTERNAL_UNTRUSTED'),
        ('MEMORY_WRITE', 'summary retained the original untrusted origin label', 'EXTERNAL_UNTRUSTED'),
        ('MEMORY_RETRIEVE', 'retrieved prior summary; no new permission', 'EXTERNAL_UNTRUSTED'),
        ('MEMORY_REWRITE', 'rewritten summary preserved taint', 'EXTERNAL_UNTRUSTED'),
        ('ACCESS_REVOKE', 'research-only revocation marker G1', 'TEST_OPERATOR_DECLARED'),
        ('REVIEW_HOLD', 'signed records are not consent; permission held', 'TEST_OPERATOR_DECLARED'),
        ('MEMORY_RETRIEVE', 'old source reappeared but retains untrusted classification', 'EXTERNAL_UNTRUSTED'),
        ('AUDIT', 'no actual Ario effects executed', 'TEST_OPERATOR_DECLARED'),
    ]
    out = []
    for i, (kind, payload, origin) in enumerate(samples):
        out.append({
            'schema': 'ARIO_W20_SYNTHETIC_EVENT_V1', 'sequence': i,
            'kind': kind, 'payload_sha256': hashlib.sha256(payload.encode()).hexdigest(),
            'declared_origin': origin, 'memory_truth': 'UNKNOWN', 'action_authority': 'NONE',
        })
    return out


def make_fixture() -> dict:
    """Fresh ephemeral key is deliberately thrown away; no export/persistence."""
    events = synthetic_events()
    raw = [canon(e) for e in events]
    signer = Ed25519PrivateKey.generate()
    pub = signer.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    def checkpoint(size: int) -> dict:
        body = {'schema': 'ARIO_W20_SYNTHETIC_CHECKPOINT_V1', 'origin': ORIGIN,
                'size': size, 'root_sha256': root(raw[:size]).hex(), 'version': 1}
        to_sign = canon({'domain': DOMAIN, 'body': body})
        return {'domain': DOMAIN, 'body': body, 'signature': signer.sign(to_sign).hex()}
    old_size = 3
    return {
        'schema': 'ARIO_W20_NATIVE_LOG_LAB_FIXTURE_V1',
        'origin_is_real_or_registered': False,
        'events_are_synthetic_public_only': True,
        'source_labels_are_attested': False,
        'private_signer_key_exported': False,
        'log_key_held_by_separate_custodian': False,
        'signature_scope': 'EPHEMERAL_ED25519_FAKE_LOG_ONLY',
        'public_key_hex': pub,  # for fixture only. Verifier must get this OOB.
        'events': events,
        'old_checkpoint': checkpoint(old_size), 'new_checkpoint': checkpoint(len(events)),
        'consistency_proof': [v.hex() for v in consistency_path(raw, old_size)],
        'inclusions': [
            {'index': i, 'proof': [v.hex() for v in inclusion_path(raw, i)]}
            for i in range(len(events))
        ],
        'world_truth': 'UNKNOWN', 'operational_authority': 'NONE', 'external_effects': 0,
    }


def save_fixture(path: Path):
    path.write_bytes(json.dumps(make_fixture(), indent=2, sort_keys=True, ensure_ascii=False).encode('utf8')+b'\n')

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    args=p.parse_args()
    save_fixture(Path(args.output))
    print('W20_SYNTHETIC_FIXTURE_ONLY / NO_REAL_ARIO_EVENT / NO_EXTERNAL_WITNESS / NO_AUTHORITY')
