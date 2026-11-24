"""R22.11 research-only; report is assumed verified by R22.10, not a trust token."""
import hashlib, json, re, sys
from pathlib import Path

def digest(raw):
    return hashlib.sha256(hashlib.sha256(raw).digest()).hexdigest()

def pairs(items):
    out = {}
    for k, v in items:
        if k in out:
            raise ValueError('duplicate key')
        out[k] = v
    return out

def parse(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 4096:
        raise ValueError('size')
    x = json.loads(raw.decode('ascii'), object_pairs_hook=pairs)
    if type(x) is not dict or set(x) != set('authoritative floor_commitment_sha256 historical_event_truth previous_checksum production profile record_count scope synthetic synthetic_nonce trust_activation'.split()):
        raise ValueError('schema')
    if (x['profile'] != 'ARIO-R22.10-PUBLIC-SYNTHETIC-FLOOR-v1' or x['synthetic'] is not True or x['authoritative'] is not False or x['historical_event_truth'] != 'UNKNOWN' or x['production'] != 'NO_GO' or x['trust_activation'] != 'NO_GO' or type(x['record_count']) is not int or not 0 < x['record_count'] <= 2**63-1):
        raise ValueError('policy')
    for k, n in [('scope',48),('floor_commitment_sha256',64),('synthetic_nonce',64)]:
        if type(x[k]) is not str or not re.fullmatch('[0-9a-f]{'+str(n)+'}', x[k]):
            raise ValueError('format')
    p = x['previous_checksum']
    if type(p) is not str or not (p == 'GENESIS' or re.fullmatch('[0-9a-f]{64}', p)):
        raise ValueError('previous')
    if raw != encode(x):
        raise ValueError('canonical')
    return x

def encode(x):
    return (json.dumps(x, sort_keys=True, separators=(',', ':'))+'\n').encode('ascii')

def recover(first, expected, raw):
    # expected is a checksum from a previously authenticated matching-key leaf.
    if type(expected) is not str or not re.fullmatch('[0-9a-f]{64}', expected):
        return 'HOLD_BAD_CHECKSUM'
    if raw is None:
        return 'HOLD_UNAVAILABLE'
    if type(raw) is not bytes or not 0 < len(raw) <= 4096:
        return 'HOLD_SIZE'
    if digest(raw) != expected:
        return 'HOLD_HASH_MISMATCH'
    try:
        a, b = parse(first), parse(raw)
    except (ValueError, TypeError, RecursionError):
        return 'HOLD_SCHEMA_OR_POLICY'
    if b['scope'] != a['scope']:
        return 'HOLD_SCOPE'
    if b['previous_checksum'] != digest(first):
        return 'HOLD_PREDECESSOR'
    if b['record_count'] <= a['record_count']:
        return 'HOLD_NON_ADVANCING'
    return 'RECOVERED_LINKED_CANDIDATE_RESEARCH_ONLY'

def candidate(report, first):
    # Input report must be authenticated by the caller; this checks only shape/binding.
    m = report['matching_signed_leaves']
    if (report['disposition'] != 'HOLD_OPAQUE_NEW_SIGNED_COMMITMENT' or report['complete_sampled_suffix'] is not True or len(m) != 2 or m[0]['checksum'] != digest(first) or type(m[0]['index']) is not int or type(m[1]['index']) is not int or m[1]['index'] <= m[0]['index'] or m[1]['checksum'] == m[0]['checksum']):
        raise ValueError('HOLD_DISCOVERY_BINDING')
    return m[1]['checksum']

def run(first, report, recovered):
    expected = candidate(report, first)
    good = 'RECOVERED_LINKED_CANDIDATE_RESEARCH_ONLY'
    x = parse(recovered)
    cases = [('actual_readback',expected,recovered,good),('missing',expected,None,'HOLD_UNAVAILABLE'),('tampered',expected,recovered+b' ','HOLD_HASH_MISMATCH'),('old_replay',expected,first,'HOLD_HASH_MISMATCH'),('bad_address','bad',recovered,'HOLD_BAD_CHECKSUM'),('oversize',expected,b'x'*4097,'HOLD_SIZE')]
    for name, edits, status in [('wrong_scope',{'scope':'0'*48},'HOLD_SCOPE'),('wrong_previous',{'previous_checksum':'0'*64},'HOLD_PREDECESSOR'),('nonadvancing',{'record_count':parse(first)['record_count']},'HOLD_NON_ADVANCING'),('authority',{'authoritative':True},'HOLD_SCHEMA_OR_POLICY'),('bool_count',{'record_count':True},'HOLD_SCHEMA_OR_POLICY')]:
        raw = encode(dict(x, **edits)); cases.append((name,digest(raw),raw,status))
    for name, raw in [('duplicate',recovered.replace(b'{',b'{"synthetic":true,',1)),('noncanonical',recovered+b' '),('invalid_json',b'{')]:
        cases.append((name,digest(raw),raw,'HOLD_SCHEMA_OR_POLICY'))
    for name, h, raw, status in cases:
        got = recover(first,h,raw)
        if got != status:
            raise AssertionError((name,got,status))
        print(name,got,'PASS')
    for name, edits in [('incomplete',{'complete_sampled_suffix':False}),('wrong_first',{'matching_signed_leaves':[{'index':1,'checksum':'0'*64}, {'index':2,'checksum':expected}]})]:
        try:
            candidate(dict(report,**edits),first)
        except ValueError:
            print(name,'HOLD_DISCOVERY_BINDING PASS')
        else:
            raise AssertionError(name)
    print('16/16 PASS; record_count=',x['record_count'],'; global_latest=NOT_ESTABLISHED; trust_activation=NO_GO; production=NO_GO',sep='')

if __name__ == '__main__':
    first = Path(sys.argv[1]).read_bytes()
    report = json.loads(Path(sys.argv[2]).read_text().splitlines()[-1])
    recovered = Path(sys.argv[3]).read_bytes()
    run(first,report,recovered)
