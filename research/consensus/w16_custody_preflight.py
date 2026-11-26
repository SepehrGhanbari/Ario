#!/usr/bin/env python3
"""Ario W16: source-bound witness/custody preflight; standalone research only.

Inputs are declared observations, NOT authenticated custody evidence.  This
program NEVER returns operational authority.  It detects structural rollback,
conflicting checkpoint views, and blocks self-certified independence claims.

Neither a trusted clock nor independent operator identity can be established by
an author's own JSON.  A successful preview is NOT approval of a memory claim.
"""
from __future__ import annotations
import json
import re

HASH64 = re.compile(r"^[0-9a-f]{64}$")
REFERENCE_FIELDS = {'provider', 'admin_root', 'witness_key', 'epoch', 'head_sha256', 'reported_signature_valid', 'readback_source'}
LOCAL_FIELDS = {'epoch', 'head_sha256'}
MAX_REFERENCES = 8


def _exact(value, required):
    return type(value) is dict and set(value) == required


def _int_epoch(value):
    return type(value) is int and 0 <= value <= 2**63 - 1


def _hash(value):
    return type(value) is str and HASH64.fullmatch(value) is not None


def _result(verdict, reason, *, preview=False, roots=0, freshest=None):
    return {
        'verdict': verdict, 'reason': reason,
        'read_only_preview': preview,
        'distinct_declared_admin_roots': roots,
        'newest_declared_epoch': freshest,
        'independent_administrative_custody': 'NOT_ESTABLISHED',
        'remote_currentness': 'NOT_ESTABLISHED',
        'real_operator_identity': 'NOT_ESTABLISHED',
        'human_consent': 'NOT_ESTABLISHED',
        'trusted_clock': 'NOT_ESTABLISHED',
        'source_truth': 'UNKNOWN',
        'operational_authority': 'NONE',
        'external_actions': 0,
        'memory_admitted': False,
    }


def assess(local, references, known_highwater=None):
    """No branch can approve an action, even with two matching signed witnesses.

    references[].admin_root is a *self-declared* label. Unique values are NOT
    evidence of independent administrators. reported_signature_valid describes
    what an upstream caller says; this program does NOT verify signatures.
    """
    hold = lambda reason, **kw: _result('HOLD_UNCERTAIN', reason, **kw)
    deny = lambda reason, **kw: _result('DENY', reason, **kw)
    if not _exact(local, LOCAL_FIELDS) or not _int_epoch(local['epoch']) or not _hash(local['head_sha256']):
        return hold('INVALID_LOCAL_EPOCH_OR_HASH')
    if known_highwater is not None and not _int_epoch(known_highwater):
        return hold('INVALID_TRUSTED_HIGHWATER_INPUT')
    if known_highwater is not None and local['epoch'] < known_highwater:
        return deny('LOCAL_BELOW_RETAINED_HIGHWATER')
    if type(references) is not list or len(references) == 0:
        return hold('NO_REFERENCE_AVAILABLE')
    if len(references) > MAX_REFERENCES:
        return hold('REFERENCE_RESOURCE_LIMIT')
    seen_keys = set()
    for entry in references:
        if not _exact(entry, REFERENCE_FIELDS):
            return hold('REFERENCE_SCHEMA')
        if any(type(entry[k]) is not str or not entry[k] or len(entry[k]) > 128
               for k in ('provider', 'admin_root', 'witness_key', 'readback_source')):
            return hold('REFERENCE_STRING_TYPES')
        if not _int_epoch(entry['epoch']) or not _hash(entry['head_sha256']):
            return hold('REFERENCE_VERSION_OR_HASH')
        if type(entry['reported_signature_valid']) is not bool:
            return hold('REPORTED_SIGNATURE_TYPE')
        if entry['reported_signature_valid'] is False:
            return hold('REPORTED_SIGNATURE_UNVERIFIED')
        # Two endpoints using the same signing key cannot become two witnesses.
        if entry['witness_key'] in seen_keys:
            return hold('DUPLICATE_WITNESS_KEY')
        seen_keys.add(entry['witness_key'])

    declared_roots = len({r['admin_root'] for r in references})
    newest = max(r['epoch'] for r in references)
    meta = dict(roots=declared_roots, freshest=newest)
    # If the same epoch has contradictory heads, we can detect equivocation
    # *assuming each declared hash is linked to a verified checkpoint*.
    by_epoch = {}
    for entry in references:
        by_epoch.setdefault(entry['epoch'], set()).add(entry['head_sha256'])
    if any(len(heads) > 1 for heads in by_epoch.values()):
        return deny('DECLARED_SPLIT_VIEW_SAME_EPOCH', **meta)
    if newest > local['epoch']:
        return deny('LOCAL_BELOW_LATEST_OBSERVED_REFERENCE', **meta)
    if known_highwater is not None and newest < known_highwater:
        return deny('ALL_REFERENCES_BELOW_RETAINED_HIGHWATER', **meta)
    if newest < local['epoch']:
        return hold('REFERENCE_LAGS_LOCAL', **meta)
    if local['head_sha256'] not in by_epoch.get(local['epoch'], set()):
        return deny('LOCAL_HEAD_CONFLICTS_WITH_DECLARED_REFERENCE', **meta)
    if any(r['epoch'] != newest for r in references):
        return hold('MIXED_REFERENCE_FRESHNESS', preview=True, **meta)
    if declared_roots == 1:
        return hold('SAME_DECLARED_ADMIN_ROOT', preview=True, **meta)
    # Different words in self-authored source records do not establish independent operators.
    return hold('DISTINCT_ADMIN_LABELS_UNVERIFIED', preview=True, **meta)


def sample_local(epoch=1, head='b'):
    return {'epoch': epoch, 'head_sha256': head * 64}


def sample_reference(epoch=1, head='b', *, provider='GitHub', admin='Owner-1', witness='Key-1', signed=True):
    return {'provider': provider, 'admin_root': admin, 'witness_key': witness,
            'epoch': epoch, 'head_sha256': head * 64,
            'reported_signature_valid': signed, 'readback_source': 'LAB_DECLARED_ONLY'}


if __name__ == '__main__':
    print(json.dumps(assess(sample_local(), [sample_reference()]), indent=2, sort_keys=True))
