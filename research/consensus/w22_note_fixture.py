#!/usr/bin/env python3
"""W22: creates PUBLIC ONLY synthetic C2SP signed-note checkpoints (research).

Private keys are ephemeral in RAM and never serialized or sent to any external API.
Underlying 8 synthetic event bytes are copied from the already published W20 lab.
This is NOT a public Ario origin registration and NOT a witness cosignature.
"""
from __future__ import annotations
import base64
import hashlib
import json
import sys
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

ORIGIN = 'ario-w22-research.invalid/synthetic-log'


def raw_event(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def lh(b):
    return hashlib.sha256(b'\x00' + b).digest()


def nh(a, b):
    return hashlib.sha256(b'\x01' + a + b).digest()


def mth(leaves):
    if len(leaves) == 0:
        return hashlib.sha256(b'').digest()
    if len(leaves) == 1:
        return lh(leaves[0])
    split = 1 << ((len(leaves) - 1).bit_length() - 1)
    return nh(mth(leaves[:split]), mth(leaves[split:]))


def signed_note(key, name, size, root):
    """C2SP tlog-checkpoint + C2SP signed-note/Ed25519 0x01 layout."""
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    key_id = hashlib.sha256(name.encode() + b'\x0a\x01' + pub).digest()[:4]
    text = (name + '\n' + str(size) + '\n' + base64.b64encode(root).decode() + '\n').encode()
    sig_bytes = key_id + key.sign(text)
    note = text + b'\n' + ('— ' + name + ' ' + base64.b64encode(sig_bytes).decode() + '\n').encode()
    vkey = name + '+' + key_id.hex() + '+' + base64.b64encode(b'\x01'+pub).decode()
    return note.decode(), vkey


def make_fixture(original):
    assert original['schema'] == 'ARIO_W20_NATIVE_LOG_LAB_FIXTURE_V1'
    assert original['events_are_synthetic_public_only'] is True
    events = original['events']
    assert len(events) == 8 and all(e['action_authority'] == 'NONE' for e in events)
    raw = [raw_event(e) for e in events]
    assert mth(raw[:3]).hex() == original['old_checkpoint']['body']['root_sha256']
    assert mth(raw).hex() == original['new_checkpoint']['body']['root_sha256']
    key = Ed25519PrivateKey.generate()
    previous, vkey = signed_note(key, ORIGIN, 3, mth(raw[:3]))
    current, same_vkey = signed_note(key, ORIGIN, 8, mth(raw))
    assert vkey == same_vkey
    altered = list(events)
    altered[-1] = {**altered[-1], 'payload_sha256': 'f' * 64}
    fork_bytes = [raw_event(e) for e in altered]
    fork, _ = signed_note(key, ORIGIN, 8, mth(fork_bytes))
    assert fork != current
    return {
       'schema': 'ARIO_W22_SIGNED_NOTE_TILE_LAB_V1',
       'origin': ORIGIN,
       'public_vkey_for_synthetic_demo_only': vkey,
       'previous_checkpoint': previous,
       'current_checkpoint': current,
       'same_signer_fork_checkpoint': fork,
       'events': events,
       'fork_events': altered,
       'declared_prev_size': 3,
       'declared_current_size': 8,
       'actual_ario_log_witnessed': False,
       'private_key_exported': False,
       'human_approval_established': False,
       'source_truth': 'UNKNOWN',
       'action_authority': 'NONE'
    }


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: python w22_note_fixture.py W20_PUBLIC_FIXTURE.json W22_OUTPUT.json')
    fixture=make_fixture(json.loads(Path(sys.argv[1]).read_text('utf8')))
    Path(sys.argv[2]).write_text(json.dumps(fixture,indent=2,sort_keys=True,ensure_ascii=False)+'\n', encoding='utf8')
    print('W22_PUBLIC_NOTE_FIXTURE_CREATED, EPHEMERAL_PRIVATE_KEY_DISCARDED, ACTUAL_WITNESS=NONE')


if __name__ == '__main__':
    main()
