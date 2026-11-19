#!/usr/bin/env python3
"""FC-E04 v0.3: bounded, read-only declared-lineage recognition/adjudication lab.

This is NOT a trusted provenance system, truth validator, memory admission gate,
agent runtime, or production Ario component. It reads one immutable byte image,
checks W9's narrow self-reported predicate and a separate declared-ancestry graph,
and refuses to convert declared root counts into independent evidence.
"""
from __future__ import annotations

import hashlib
import types
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = 'ario.lab.fc_e04.v0.3'
RECOGNITION_SCHEMA = 'ario.lab.fc_e04.recognition.v0.3'
MAX_BYTES = 65536
MAX_DEPTH = 16
MAX_RECORDS = 8
MAX_INTEGER_DIGITS = 128
MAX_W9_SOURCE_BYTES = 16384
ID = re.compile(r'[A-Za-z0-9_.:-]{1,64}\Z', re.ASCII)
W9_BLOB_SHA1 = 'f795065ce06d88c2ca017270f5036eb028029220'
W9_SHA256 = 'bd515b470fd51186f6e44f5320dd69fa73a1bce325b12301b9b276163d5e33d3'


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _bounded_sha(raw: Any) -> str | None:
    """No full hashing of refused oversized/non-bytes inputs.

    None is an explicit no-digest result, not a hash of an empty substitute
    or a prefix hash that could be misread as the image's byte identity.
    """
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        return None
    return _sha(raw)


class _IntegerLimit(ValueError):
    pass


def _bounded_int(token: str) -> int:
    digits = token[1:] if token.startswith('-') else token
    if len(digits) > MAX_INTEGER_DIGITS:
        raise _IntegerLimit('JSON_INTEGER_DIGIT_LIMIT')
    return int(token)


def _unknown(raw: bytes, reason: str, w9: dict | None = None) -> dict:
    return {
        'schema': SCHEMA, 'image_sha256': _bounded_sha(raw),
        'recognition': {'status': 'UNKNOWN', 'reason': reason},
        'w9_relation': w9['declared_relation'] if w9 else 'NOT_CHECKED',
        'final': {'status': 'UNKNOWN', 'reason': reason,
                  'declared_root_count': None, 'illustrative_occurrence_count': None},
        'source_custody': 'NOT_ESTABLISHED', 'independent_corroboration': 'UNKNOWN',
        'world_truth': 'UNKNOWN', 'assessment': 'NOT_ASSESSED',
        'memory_admitted': False, 'action_authority': 'NONE',
    }


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict:
    obj: dict = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError('DUPLICATE_JSON_KEY')
        obj[k] = v
    return obj


def _bad_number(_value: str) -> None:
    raise ValueError('NON_INTEGER_NUMBER')


def _depth(raw: bytes) -> int:
    """Conservatively bound JSON nesting before json.loads; ignore quoted braces."""
    depth = 0
    high = 0
    quote = False
    escape = False
    for b in raw:
        if quote:
            if escape:
                escape = False
            elif b == 92:
                escape = True
            elif b == 34:
                quote = False
        elif b == 34:
            quote = True
        elif b in (91, 123):
            depth += 1
            high = max(high, depth)
            if high > MAX_DEPTH:
                raise ValueError('JSON_DEPTH_LIMIT')
        elif b in (93, 125):
            depth -= 1
            if depth < 0:
                raise ValueError('JSON_BRACKETS_INVALID')
    if quote or depth != 0:
        raise ValueError('JSON_FRAMING_INVALID')
    return high


def _parse(raw: bytes) -> dict:
    if type(raw) is not bytes or not raw or len(raw) > MAX_BYTES:
        raise ValueError('IMAGE_TYPE_OR_BYTE_LIMIT')
    _depth(raw)
    try:
        txt = raw.decode('utf-8', 'strict')
        obj = json.loads(txt, object_pairs_hook=_no_duplicates,
                         parse_constant=_bad_number, parse_float=_bad_number,
                         parse_int=_bounded_int)
    except _IntegerLimit as exc:
        raise ValueError('JSON_INTEGER_DIGIT_LIMIT') from exc
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise ValueError('INVALID_JSON_OR_UNICODE') from exc
    if type(obj) is not dict or set(obj) != {'schema', 'claim', 'receipts', 'lineage'} or obj['schema'] != SCHEMA:
        raise ValueError('IMAGE_SCHEMA')
    if type(obj['receipts']) is not list or not 1 <= len(obj['receipts']) <= MAX_RECORDS:
        raise ValueError('RECEIPT_COUNT')
    if type(obj['lineage']) is not list or len(obj['lineage']) != len(obj['receipts']):
        raise ValueError('LINEAGE_MISSING_OR_COUNT')
    # Unpaired JSON escaped surrogates must not enter W9's UTF-8 hash paths.
    try:
        json.dumps(obj, ensure_ascii=False).encode('utf-8', 'strict')
    except UnicodeError as exc:
        raise ValueError('INVALID_UNICODE_SCALAR') from exc
    return obj


def _valid_id(value: Any) -> bool:
    return type(value) is str and ID.fullmatch(value) is not None


def _recognize(obj: dict, image_hash: str) -> dict:
    receipts = obj['receipts']
    identifiers = []
    for r in receipts:
        if type(r) is not dict or not _valid_id(r.get('id')):
            raise ValueError('RECEIPT_ID_INVALID')
        identifiers.append(r['id'])
    if len(set(identifiers)) != len(identifiers):
        raise ValueError('RECEIPT_IDS_REPEATED')
    entries = {}
    for item in obj['lineage']:
        if type(item) is not dict or set(item) != {'receipt_id', 'root_id', 'parents'}:
            raise ValueError('LINEAGE_SCHEMA')
        rid = item['receipt_id']
        if not _valid_id(rid) or rid in entries:
            raise ValueError('LINEAGE_DUPLICATE_OR_ID')
        root = item['root_id']
        parents = item['parents']
        if type(parents) is not list or len(parents) > MAX_RECORDS or not all(_valid_id(p) for p in parents):
            raise ValueError('LINEAGE_PARENTS_INVALID')
        if len(parents) != len(set(parents)):
            raise ValueError('LINEAGE_DUPLICATE_PARENT')
        # A primitive has exactly one declared root. A derivation has parents only.
        if (root is None) == (not parents):
            raise ValueError('LINEAGE_ROOT_PARENT_EXCLUSIVE')
        if root is not None and not _valid_id(root):
            raise ValueError('LINEAGE_ROOT_INVALID')
        entries[rid] = (root, parents)
    if set(entries) != set(identifiers):
        raise ValueError('LINEAGE_RECEIPT_SET_MISMATCH')
    seen, visiting = {}, set()
    def roots(rid: str) -> frozenset[str]:
        if rid in visiting:
            raise ValueError('LINEAGE_CYCLE')
        if rid in seen:
            return seen[rid]
        if rid not in entries:
            raise ValueError('LINEAGE_MISSING_PARENT')
        visiting.add(rid)
        root, parents = entries[rid]
        if root is not None:
            result = frozenset([root])
        else:
            result = frozenset().union(*(roots(p) for p in parents))
        visiting.remove(rid)
        seen[rid] = result
        return result
    root_sets = {rid: sorted(roots(rid)) for rid in sorted(identifiers)}
    all_roots = sorted(set().union(*(set(x) for x in root_sets.values())))
    return {'schema': RECOGNITION_SCHEMA, 'image_sha256': image_hash,
            'status': 'DECLARED_LINEAGE_RESOLVED', 'root_sets': root_sets,
            'declared_primitive_roots': all_roots,
            'declared_root_count': len(all_roots),
            'source_custody': 'NOT_ESTABLISHED'}


def _load_w9() -> Any:
    """Verify and execute the SAME bounded local W9 bytes; no second path read.

    Avoid a check-then-import TOCTOU gap: importlib's loader otherwise opens
    the file again after verifying its hash. No sys.modules or cache writes.
    Local byte identity is NOT source authenticity, custody or truth.
    """
    path = Path(__file__).resolve().with_name('w9_bounded_receipt_contract.py')
    with path.open('rb') as fh:
        raw = fh.read(MAX_W9_SOURCE_BYTES + 1)
    if len(raw) > MAX_W9_SOURCE_BYTES:
        raise ValueError('W9_SOURCE_BYTE_LIMIT')
    git_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if git_blob != W9_BLOB_SHA1 or hashlib.sha256(raw).hexdigest() != W9_SHA256:
        raise ValueError('W9_SOURCE_BLOB_MISMATCH')
    # Compilation and execution consume only the hash-verified byte object.
    # The verified file path is kept as a display label, NOT reopened.
    module = types.ModuleType('_fc_e04_pinned_w9')
    module.__file__ = str(path)
    code = compile(raw, str(path), 'exec', dont_inherit=True)
    exec(code, module.__dict__)
    return module


def recognize_image(raw: bytes) -> dict:
    """Stage 1: read-only declared ancestry recognition, no claim admission."""
    try:
        obj = _parse(raw)
        return _recognize(obj, _sha(raw))
    except ValueError as exc:
        return {'schema': RECOGNITION_SCHEMA,
                'image_sha256': _bounded_sha(raw),
                'status': 'UNKNOWN', 'reason': str(exc),
                'source_custody': 'NOT_ESTABLISHED'}


def adjudicate_image(raw: bytes, recognition_receipt: dict) -> dict:
    """Stage 2: fail closed unless Stage 1's receipt matches these same bytes."""
    return evaluate_image(raw, recognition_override=recognition_receipt)


def evaluate_image(raw: bytes, recognition_override: dict | None = None) -> dict:
    """Recognition and final check recompute from the SAME input byte image.

    An override models a separately submitted recognition receipt and is
    strictly cross-checked with deterministic recomputation; no authority.
    """
    try:
        obj = _parse(raw)
    except ValueError as exc:
        return _unknown(raw, str(exc))
    digest = _sha(raw)
    try:
        recognized = _recognize(obj, digest)
    except ValueError as exc:
        return _unknown(raw, str(exc))
    if recognition_override is not None and (type(recognition_override) is not dict or recognition_override != recognized):
        return _unknown(raw, 'RECOGNITION_IMAGE_OR_CONTENT_MISMATCH')
    try:
        w9 = _load_w9()
        checked = w9.evaluate(obj['claim'], obj['receipts'])
    except (ValueError, TypeError, UnicodeError, OSError, RecursionError) as exc:
        # Deliberately don't expose raw exception text or user input.
        return _unknown(raw, 'PINNED_W9_UNAVAILABLE_OR_EXCEPTION')
    rel = checked['declared_relation']
    if rel != 'DECLARED_MATCH':
        out = _unknown(raw, 'W9_' + rel, checked)
        out['recognition'] = recognized
        return out
    return {
        'schema': SCHEMA, 'image_sha256': digest, 'recognition': recognized,
        'w9_relation': rel,
        'final': {
            'status': 'DECLARED_ROOT_PARTITION_ONLY',
            'reason': 'W9_DECLARED_MATCH_AND_DECLARED_LINEAGE_RESOLVED',
            'declared_root_count': recognized['declared_root_count'],
            'illustrative_occurrence_count': len(obj['receipts']),
        },
        'source_custody': 'NOT_ESTABLISHED', 'independent_corroboration': 'UNKNOWN',
        'world_truth': 'UNKNOWN', 'assessment': 'NOT_ASSESSED',
        'memory_admitted': False, 'action_authority': 'NONE',
    }


def make_image(claim: dict, receipts: list, lineage: list) -> bytes:
    """Test-only helper; not used by the evaluator itself."""
    return json.dumps({'schema': SCHEMA, 'claim': claim, 'receipts': receipts,
                       'lineage': lineage}, ensure_ascii=False,
                      sort_keys=True, separators=(',', ':')).encode('utf-8')


if __name__ == '__main__':
    # Only explicitly supplied immutable bytes; never read a user's real ledger.
    if len(sys.argv) != 2 or sys.argv[1] != '--self-demo':
        raise SystemExit('This research-only module has no file/network input CLI; use --self-demo or import evaluate_image(bytes)')
    w9 = _load_w9()
    r1, r2 = w9.receipt(id='R1'), w9.receipt(id='R2')
    example = make_image(w9.claim(), [r1, r2], [
        {'receipt_id':'R1','root_id':'ROOT_A','parents':[]},
        {'receipt_id':'R2','root_id':None,'parents':['R1']},
    ])
    print(json.dumps(evaluate_image(example), sort_keys=True, indent=2))
