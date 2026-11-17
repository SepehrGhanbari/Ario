#!/usr/bin/env python3
"""W23 offline, synthetic C2SP signed-note split-view/gossip falsifier.

Independent implementation of strict W22 subset parsing, with no network, no writes,
no witness signatures, and no assertion of independent operator custody. This is
NOT a C2SP tlog-witness service and is NOT evidence of current-world freshness.
"""
from __future__ import annotations
import base64
import hashlib
import re
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ORIGIN = 'ario-w22-research.invalid/synthetic-log'
_VKEY = re.compile(r'^([^+\s]+)\+([0-9a-f]{8})\+([A-Za-z0-9+/]+={0,2})$')
_B64 = re.compile(r'^[A-Za-z0-9+/]+={0,2}$')
_HEX = re.compile(r'^[0-9a-f]{64}$')


def _b64(value):
    if not isinstance(value, str) or not _B64.fullmatch(value):
        raise ValueError('invalid base64')
    raw = base64.b64decode(value, validate=True)
    if base64.b64encode(raw).decode('ascii') != value:
        raise ValueError('noncanonical base64')
    return raw


def read_signed_note(note, pinned_vkey, origin=ORIGIN):
    """Return a strictly verified W22-subset head or None. Never discover keys in notes."""
    if type(note) is not bytes or len(note) > 4096 or type(pinned_vkey) is not str or len(pinned_vkey) > 220:
        return None
    try:
        match = _VKEY.fullmatch(pinned_vkey)
        if match is None or match.group(1) != origin:
            return None
        name, keyid, encoded = match.groups()
        public = _b64(encoded)
        if len(public) != 33 or public[0] != 1:
            return None
        kid = hashlib.sha256(name.encode('utf-8')+b'\n\x01'+public[1:]).digest()[:4]
        if kid.hex() != keyid:
            return None
        parts = note.split(b'\n\n')
        if len(parts) != 2 or not parts[1].endswith(b'\n'):
            return None
        message = parts[0] + b'\n'
        lines = message.decode('utf-8').splitlines()
        if len(lines) != 3 or lines[0] != origin or not re.fullmatch(r'[1-9][0-9]*', lines[1]):
            return None
        size = int(lines[1])
        if size > 64:
            return None
        root = _b64(lines[2])
        if len(root) != 32:
            return None
        signature_lines = parts[1].decode('utf-8').splitlines()
        if len(signature_lines) != 1 or not signature_lines[0].startswith('— '+name+' '):
            return None
        signature = _b64(signature_lines[0][len('— '+name+' '):])
        if len(signature) != 68 or signature[:4] != kid:
            return None
        Ed25519PublicKey.from_public_bytes(public[1:]).verify(signature[4:], message)
        return {'size': size, 'root': root.hex(), 'note_sha256': hashlib.sha256(note).hexdigest()}
    except (ValueError, UnicodeError, OverflowError, TypeError, InvalidSignature):
        return None


def _node(left, right):
    return hashlib.sha256(b'\x01'+left+right).digest()


def verify_compact_consistency(m, n, older_root, newer_root, proof):
    """RFC6962 compact proof validation for research, with strict bounded inputs."""
    if (type(m) is not int or type(n) is not int or not 0 < m <= n <= 64
        or type(older_root) is not str or type(newer_root) is not str
        or not _HEX.fullmatch(older_root) or not _HEX.fullmatch(newer_root)
        or type(proof) is not list or len(proof) > 16
        or any(type(x) is not str or not _HEX.fullmatch(x) for x in proof)):
        return False
    if m == n:
        return not proof and older_root == newer_root
    if not proof:
        return False
    nodes = [bytes.fromhex(x) for x in proof]
    if m & (m-1) == 0:
        nodes.insert(0, bytes.fromhex(older_root))
    fn, sn = m-1, n-1
    while fn & 1:
        fn >>= 1
        sn >>= 1
    fr = sr = nodes[0]
    for sibling in nodes[1:]:
        if sn == 0:
            return False
        if (fn & 1) or fn == sn:
            fr = _node(sibling, fr)
            sr = _node(sibling, sr)
            if not (fn & 1):
                while not (fn & 1) and fn:
                    fn >>= 1
                    sn >>= 1
        else:
            sr = _node(sr, sibling)
        fn >>= 1
        sn >>= 1
    return sn == 0 and fr.hex() == older_root and sr.hex() == newer_root


def _finding(reason, **detail):
    return dict(finding=reason, **detail, latest_world_state='UNKNOWN',
                independently_administered_custody='NOT_ESTABLISHED',
                out_of_band_pin='NOT_ESTABLISHED', external_actions=0,
                operational_authority='NONE', memory_admitted=False)


def compare(retained_note, candidate_note, pinned_vkey=None, consistency_proof=None):
    """Retained is caller-supplied, not proven independent; no key discovery."""
    retained = read_signed_note(retained_note, pinned_vkey)
    candidate = read_signed_note(candidate_note, pinned_vkey)
    if retained is None or candidate is None:
        return _finding('HOLD_INVALID_NOTE_OR_UNPINNED_KEY')
    common = dict(retained_size=retained['size'], candidate_size=candidate['size'])
    if candidate['size'] < retained['size']:
        return _finding('DENY_ROLLBACK_RELATIVE_TO_RETAINED', **common)
    if candidate['size'] == retained['size']:
        if retained['root'] != candidate['root']:
            return _finding('SIGNED_EQUIVOCATION_PROVEN', **common,
                            evidence_note_sha256=[retained['note_sha256'],candidate['note_sha256']])
        return _finding('MATCHING_SIGNED_HEADS_NOT_FRESHNESS', **common)
    if consistency_proof is None:
        return _finding('HOLD_MISSING_CONSISTENCY_PROOF', **common)
    if not verify_compact_consistency(retained['size'], candidate['size'],
                                      retained['root'],candidate['root'],consistency_proof):
        return _finding('HOLD_INVALID_PROOF_NOT_FORK_EVIDENCE', **common)
    return _finding('CONSISTENT_GROWTH_NOT_FRESHNESS', **common)


def gossip(views, pinned_vkey=None):
    """Compare bounded signed views. View labels are untrusted, not verified identities."""
    if type(views) is not dict or not 2 <= len(views) <= 16 or any(
        type(k) is not str or not 1 <= len(k) <= 40 or not re.fullmatch(r'[A-Za-z0-9_-]+',k)
        for k in views):
        return _finding('HOLD_BAD_VIEW_SET')
    parsed = {name: read_signed_note(note,pinned_vkey) for name,note in views.items()}
    if any(head is None for head in parsed.values()):
        return _finding('HOLD_INVALID_NOTE_OR_UNPINNED_KEY')
    ordered = sorted(parsed.items())
    for i,(left_name,left) in enumerate(ordered):
        for right_name,right in ordered[i+1:]:
            if left['size'] == right['size'] and left['root'] != right['root']:
                return _finding('SIGNED_EQUIVOCATION_PROVEN', view_labels_untrusted=[left_name,right_name],
                    evidence_note_sha256=[left['note_sha256'],right['note_sha256']])
    if len({head['size'] for head in parsed.values()}) > 1:
        return _finding('HOLD_DIFFERENT_SIZES_NEED_PAIRWISE_CONSISTENCY')
    return _finding('OBSERVED_AGREEMENT_NOT_WORLD_FRESHNESS', observed_size=ordered[0][1]['size'])
