#!/usr/bin/env python3
"""Research-only W9: check declared receipt bytes against an exact toy predicate.

No trusted receipt issuer, tool execution, evidence admission, signer or runtime
is included. 'MATCH' means consistency with SELF-REPORTED BYTES only.
"""
import hashlib
import json

SCHEMA = 'ario.lab.fs_presence.v0'
MAX_BYTES = 4096

def _hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def _pairs(pairs):
    out = {}
    for key, val in pairs:
        if key in out:
            raise ValueError('duplicate key')
        out[key] = val
    return out

def _bad(x):
    raise ValueError(str(x))

def _parse(s):
    return json.loads(s, object_pairs_hook=_pairs,
                      parse_constant=_bad, parse_float=_bad)

def result(relation, reason):
    return {'declared_relation': relation, 'reason': reason,
            'execution_authenticity': 'UNKNOWN',
            'source_custody': 'NOT_ESTABLISHED',
            'assessment': 'NOT_ASSESSED',
            'world_truth': 'UNKNOWN',
            'action_authority': 'NONE', 'memory_admitted': False}

def evaluate(claim, receipts):
    """Strict, all-receipts toy contract. No linguistic entailment model."""
    ck = {'predicate','principal','target','as_of','expected_present'}
    if type(claim) is not dict or set(claim) != ck:
        return result('UNKNOWN','INVALID_CLAIM')
    if (claim['predicate']!='FILE_EXISTS' or
            type(claim['expected_present']) is not bool or
            any(type(claim[k]) is not str or not claim[k] for k in ('principal','target','as_of'))):
        return result('UNKNOWN','UNSUPPORTED_CLAIM')
    if type(receipts) is not list or not 1 <= len(receipts) <= 8:
        return result('UNKNOWN','RECEIPT_COUNT')
    seen = set()
    judgments = []
    for r in receipts:
        required={'id','tool','principal','target','at','exit_code','stdout','stdout_sha256','lock','lock_sha256'}
        if type(r) is not dict or set(r)!=required:
            return result('UNKNOWN','BAD_RECEIPT_SCHEMA')
        if type(r['id']) is not str or not r['id'] or r['id'] in seen:
            return result('UNKNOWN','DUPLICATE_OR_INVALID_ID')
        seen.add(r['id'])
        if r['tool']!='inspect_directory' or type(r['exit_code']) is not int:
            return result('UNKNOWN','BAD_TOOL_OR_EXIT_TYPE')
        if any(type(r[k]) is not str for k in ('principal','target','at','stdout','stdout_sha256','lock','lock_sha256')):
            return result('UNKNOWN','BAD_RECEIPT_TYPES')
        if (r['stdout_sha256']!=_hash(r['stdout']) or r['lock_sha256']!=_hash(r['lock'])):
            return result('UNKNOWN','SELF_REPORTED_DIGEST_MISMATCH')
        if r['exit_code']!=0:
            return result('UNKNOWN','REPORTED_TOOL_FAILURE')
        if len(r['stdout'].encode('utf-8'))>MAX_BYTES:
            return result('UNKNOWN','RESOURCE_LIMIT')
        if not r['stdout']:
            return result('UNKNOWN','EMPTY_OUTPUT')
        try:
            data = _parse(r['stdout'])
        except (ValueError,TypeError):
            return result('UNKNOWN','INVALID_OR_DUPLICATE_JSON')
        if type(data) is not dict or set(data)!={'schema','principal','target','at','present'} or data['schema']!=SCHEMA:
            return result('UNKNOWN','UNKNOWN_OBSERVATION_SCHEMA')
        if type(data['present']) is not bool:
            return result('UNKNOWN','BAD_PRESENT_TYPE')
        for receipt_key, claim_key in [('principal','principal'),('target','target'),('at','as_of')]:
            if (r[receipt_key]!=claim[claim_key] or data[receipt_key]!=claim[claim_key]):
                return result('UNKNOWN','SCOPE_TARGET_OR_TIME_MISMATCH')
        judgments.append(data['present'])
    if len(set(judgments))>1:
        return result('DECLARED_CONFLICT','SELF_REPORTED_SOURCES_DISAGREE')
    if judgments[0] is claim['expected_present']:
        return result('DECLARED_MATCH','EXACT_TOY_PREDICATE_IN_SELF_REPORTED_BYTES')
    return result('DECLARED_CONTRADICTION','EXACT_TOY_PREDICATE_CONTRADICTED')

def claim(present=True, target='A', principal='LAB', at='2026-11-16T00:00:00Z'):
    return {'predicate':'FILE_EXISTS','expected_present':present,'target':target,'principal':principal,'as_of':at}

def receipt(present=True, target='A', principal='LAB', at='2026-11-16T00:00:00Z', id='R1', stdout=None, exit_code=0):
    if stdout is None:
        stdout=json.dumps({'schema':SCHEMA,'present':present,'target':target,'principal':principal,'at':at},separators=(',',':'),sort_keys=True)
    lock='synthetic-'+id
    return {'id':id,'tool':'inspect_directory','principal':principal,'target':target,'at':at,'exit_code':exit_code,
            'stdout':stdout,'stdout_sha256':_hash(stdout),'lock':lock,'lock_sha256':_hash(lock)}
