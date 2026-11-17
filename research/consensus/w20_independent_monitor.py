#!/usr/bin/env python3
"""W20 read-only verifier for CT-style compact proofs; independent of generator.

No generator imports. No I/O or network in verification path. Use only a
TRUSTED externally obtained log public key. Checkpoint signatures prove solely
possession of a key; this does not prove independent custody or actual consent.
"""
from __future__ import annotations
import hashlib
import json
import re
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

DOMAIN = 'ARIO_W20_SYNTHETIC_CHECKPOINT_ED25519_V1'
ORIGIN = 'ario-w20-synthetic.test.invalid/research-log-v1'
H64 = re.compile(r'^[0-9a-f]{64}$')
MAX_PROOF = 16
MAX_SIZE = 64


def node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b'\x01' + left + right).digest()


def hash_leaf(data: bytes) -> bytes:
    return hashlib.sha256(b'\x00' + data).digest()


def _decode_hashes(proof) -> list[bytes] | None:
    if not isinstance(proof, list) or len(proof) > MAX_PROOF:
        return None
    if any(type(h) is not str or H64.fullmatch(h) is None for h in proof):
        return None
    return [bytes.fromhex(h) for h in proof]


def verify_inclusion(event_bytes: bytes, index: int, size: int, expected_root: str, proof: list[str]) -> bool:
    """RFC9162 §2.1.3-style, independent of inclusion proof construction."""
    if (type(event_bytes) is not bytes or type(index) is not int or type(size) is not int
            or not (0 <= index < size <= MAX_SIZE) or type(expected_root) is not str
            or not H64.fullmatch(expected_root)):
        return False
    path = _decode_hashes(proof)
    if path is None:
        return False
    fn, sn = index, size - 1
    acc = hash_leaf(event_bytes)
    for sibling in path:
        if sn == 0:
            return False
        if (fn & 1) or fn == sn:
            acc = node(sibling, acc)
            if not fn & 1:
                while not fn & 1 and fn != 0:
                    fn >>= 1
                    sn >>= 1
        else:
            acc = node(acc, sibling)
        fn >>= 1
        sn >>= 1
    return sn == 0 and acc.hex() == expected_root


def verify_consistency(old_size: int, new_size: int, old_root: str, new_root: str, proof: list[str]) -> bool:
    """Compact RFC9162 §2.1.4.2-like verifier; no access to old or new leaves."""
    if (type(old_size) is not int or type(new_size) is not int
            or not 0 < old_size <= new_size <= MAX_SIZE
            or type(old_root) is not str or type(new_root) is not str
            or H64.fullmatch(old_root) is None or H64.fullmatch(new_root) is None):
        return False
    path = _decode_hashes(proof)
    if path is None:
        return False
    if old_size == new_size:
        return len(path) == 0 and old_root == new_root
    if not path:
        return False
    if old_size & (old_size - 1) == 0:
        path = [bytes.fromhex(old_root)] + path
    fn, sn = old_size - 1, new_size - 1
    while fn & 1:
        fn >>= 1
        sn >>= 1
    fr = sr = path[0]
    for sibling in path[1:]:
        if sn == 0:
            return False
        if (fn & 1) or fn == sn:
            fr = node(sibling, fr)
            sr = node(sibling, sr)
            if not (fn & 1):
                while not (fn & 1) and fn != 0:
                    fn >>= 1
                    sn >>= 1
        else:
            sr = node(sr, sibling)
        fn >>= 1
        sn >>= 1
    return sn == 0 and fr.hex() == old_root and sr.hex() == new_root


def _check_head(head, pinned_public_key: str, expected_origin: str):
    if (type(pinned_public_key) is not str or H64.fullmatch(pinned_public_key) is None
            or type(expected_origin) is not str or not expected_origin):
        return None
    if (type(head) is not dict or set(head) != {'domain', 'body', 'signature'}
            or head['domain'] != DOMAIN or type(head['body']) is not dict
            or type(head['signature']) is not str or len(head['signature']) != 128):
        return None
    body = head['body']
    if (set(body) != {'schema', 'origin', 'size', 'root_sha256', 'version'}
            or body['schema'] != 'ARIO_W20_SYNTHETIC_CHECKPOINT_V1'
            or body['origin'] != expected_origin or body['version'] != 1
            or type(body['size']) is not int or not (0 < body['size'] <= MAX_SIZE)
            or type(body['root_sha256']) is not str or H64.fullmatch(body['root_sha256']) is None):
        return None
    signed_bytes = json.dumps({'domain': DOMAIN, 'body': body}, sort_keys=True,
                              ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf8')
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pinned_public_key)).verify(
            bytes.fromhex(head['signature']), signed_bytes)
    except (InvalidSignature, ValueError, TypeError):
        return None
    return body


def result(verdict: str, reason: str):
    return {
        'verdict': verdict, 'reason': reason,
        'real_ario_log_witnessed': 'NOT_ESTABLISHED',
        'cross_admin_key_custody': 'NOT_ESTABLISHED',
        'freshest_world_checkpoint': 'UNKNOWN',
        'source_truth': 'UNKNOWN',
        'human_approval': 'NOT_ESTABLISHED',
        'operational_authority': 'NONE',
        'memory_admitted': False,
        'external_effects': 0,
    }


def evaluate(old, candidate, pinned_public_key=None, consistency=None, *, expected_origin=ORIGIN):
    """Pinned public key must be supplied separately, not accepted from fixture."""
    if pinned_public_key is None:
        return result('HOLD_UNCERTAIN', 'NO_OUT_OF_BAND_KEY_PIN')
    old_body = _check_head(old, pinned_public_key, expected_origin)
    next_body = _check_head(candidate, pinned_public_key, expected_origin)
    if old_body is None or next_body is None:
        return result('DENY', 'CHECKPOINT_SIGNATURE_OR_SCHEMA_INVALID')
    m, n = old_body['size'], next_body['size']
    if n < m:
        return result('DENY', 'LOCAL_TREE_SIZE_ROLLBACK')
    if n == m:
        if old_body['root_sha256'] != next_body['root_sha256']:
            return result('DENY', 'EQUIVOCATION_SAME_SIZE')
        return result('HISTORICAL_CONSISTENT', 'SAME_SIGNED_HEAD_NOT_FRESHNESS')
    if consistency is None:
        return result('HOLD_UNCERTAIN', 'MISSING_COMPACT_CONSISTENCY_PROOF')
    if not verify_consistency(m, n, old_body['root_sha256'], next_body['root_sha256'], consistency):
        return result('DENY', 'COMPACT_CONSISTENCY_PROOF_INVALID')
    return result('HISTORICAL_CONSISTENT', 'SIGNED_APPEND_ONLY_GROWTH_NOT_WORLD_FRESHNESS')


def valid_public_synthetic_event(event, expected_index: int) -> bool:
    """Public fixture admission guard: never print or upload payload strings."""
    if type(event) is not dict or set(event) != {
        'schema', 'sequence', 'kind', 'payload_sha256', 'declared_origin',
        'memory_truth', 'action_authority'
    }:
        return False
    if (event['schema'] != 'ARIO_W20_SYNTHETIC_EVENT_V1'
        or type(event['sequence']) is not int or event['sequence'] != expected_index
        or type(event['kind']) is not str or event['kind'] not in {
            'INGEST', 'MEMORY_WRITE', 'MEMORY_RETRIEVE', 'MEMORY_REWRITE',
            'ACCESS_REVOKE', 'REVIEW_HOLD', 'AUDIT'
        } or type(event['payload_sha256']) is not str
        or H64.fullmatch(event['payload_sha256']) is None
        or event['declared_origin'] not in {'EXTERNAL_UNTRUSTED', 'TEST_OPERATOR_DECLARED'}
        or event['memory_truth'] != 'UNKNOWN'
        or event['action_authority'] != 'NONE'):
        return False
    return True


def evaluate_bundle(bundle: dict, pinned_public_key: str | None, *, known_prior: dict | None = None):
    if type(bundle) is not dict or bundle.get('schema') != 'ARIO_W20_NATIVE_LOG_LAB_FIXTURE_V1':
        return result('HOLD_UNCERTAIN', 'INVALID_FIXTURE_SCHEMA')
    if pinned_public_key is None:
        return result('HOLD_UNCERTAIN', 'NO_OUT_OF_BAND_KEY_PIN')
    if known_prior is None:
        return result('HOLD_UNCERTAIN', 'NO_RETAINED_PRIOR_CHECKPOINT')
    old, new = bundle.get('old_checkpoint'), bundle.get('new_checkpoint')
    if old != known_prior:
        return result('DENY', 'DECLARED_OLD_HEAD_DIFFERS_FROM_TRUSTED')
    p = evaluate(known_prior, new, pinned_public_key, bundle.get('consistency_proof'))
    if p['verdict'] != 'HISTORICAL_CONSISTENT':
        return p
    try:
        body = new['body']
        events, inclusions = bundle['events'], bundle['inclusions']
        if (type(events) is not list or type(inclusions) is not list
            or len(events) != body['size'] or len(inclusions) != len(events)):
            return result('HOLD_UNCERTAIN', 'INCOMPLETE_FULL_HISTORY_EVIDENCE')
        # Require independently verifiable inclusion of EVERY available event,
        # not only selected positive leaves, to avoid a false full-history claim.
        seen = set()
        for item in inclusions:
            if type(item) is not dict or set(item) != {'index', 'proof'}:
                return result('HOLD_UNCERTAIN', 'INCLUSION_RECORD_SCHEMA')
            ix = item['index']
            if type(ix) is not int or not (0 <= ix < len(events)) or ix in seen:
                return result('HOLD_UNCERTAIN', 'DUPLICATE_OR_MISSING_INCLUSION')
            seen.add(ix)
            event = events[ix]
            if not valid_public_synthetic_event(event, ix):
                return result('HOLD_UNCERTAIN', 'NOT_A_PUBLIC_SYNTHETIC_EVENT')
            raw = json.dumps(event, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False).encode('utf8')
            if len(raw) > 1024:
                return result('HOLD_UNCERTAIN', 'SYNTHETIC_EVENT_TOO_LARGE')
            if not verify_inclusion(raw, ix, body['size'], body['root_sha256'], item['proof']):
                return result('DENY', 'EVENT_INCLUSION_INVALID')
        if seen != set(range(len(events))):
            return result('HOLD_UNCERTAIN', 'INCOMPLETE_FULL_HISTORY_EVIDENCE')
    except (KeyError, IndexError, TypeError, ValueError):
        return result('HOLD_UNCERTAIN', 'MALFORMED_PUBLIC_REPLAY_FIXTURE')
    return result('HISTORICAL_CONSISTENT', 'ALL_SUPPLIED_SYNTHETIC_LEAVES_INCLUDED_NOT_AUTHORITY')
