#!/usr/bin/env python3
"""W22 strict signed-note verifier + bounded loopback tlog-tiles *subset* monitor.

No imports from W22 producer/server. Earlier Ed25519 note and vkey must be
passed separately. Same-repository files are NOT independently pinned in fact.
This does not implement C2SP add-checkpoint or a public witness deployment.
"""
from __future__ import annotations
import base64
import binascii
import hashlib
import json
import re
import struct
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from w20_independent_monitor import verify_consistency  # only RFC compact proof logic

ORIGIN = 'ario-w22-research.invalid/synthetic-log'
MAX_NOTE = 4096
MAX_TILE = 2048
MAX_ENTRIES = 16384
MAX_PROOF = 4096
MAX_SIZE = 64
VKEY_RE = re.compile(r'^([^+\s]+)\+([0-9a-f]{8})\+([A-Za-z0-9+/]+={0,2})$')
B64_RE = re.compile(r'^[A-Za-z0-9+/]+={0,2}$')


def b64(s):
    if not B64_RE.fullmatch(s):
        raise ValueError('invalid base64 grammar')
    raw=base64.b64decode(s,validate=True)
    if base64.b64encode(raw).decode()!=s:
        raise ValueError('noncanonical base64')
    return raw


def verify_note(data:bytes,vkey:str,expected_origin=ORIGIN):
    """Only C2SP single Ed25519 log signature; refuses extensions and other types.

    More restrictive lab profile than general signed-note multiple-signer spec.
    Unknown cosignatures are intentionally unsupported, NOT interpreted as trust.
    """
    if type(data) is not bytes or len(data)>MAX_NOTE or type(vkey) is not str or len(vkey)>220:
        return None
    try:
        key=VKEY_RE.fullmatch(vkey)
        if key is None or key.group(1)!=expected_origin:
            return None
        name,keyid,payload=key.groups()
        k=b64(payload)
        if len(k)!=33 or k[0]!=1:
            return None
        raw_pub=k[1:]
        expected_id=hashlib.sha256(name.encode()+b'\n\x01'+raw_pub).digest()[:4]
        if bytes.fromhex(keyid)!=expected_id:
            return None
        chunks=data.split(b'\n\n')
        if len(chunks)!=2 or not chunks[1].endswith(b'\n'):
            return None
        note_text=chunks[0]+b'\n'
        head=note_text.decode('utf8').splitlines()
        if len(head)!=3 or head[0]!=expected_origin:
            return None
        if not re.fullmatch(r'0|[1-9][0-9]*',head[1]):
            return None
        size=int(head[1])
        if size<1 or size>MAX_SIZE:
            return None
        root=b64(head[2])
        if len(root)!=32:
            return None
        line=chunks[1].decode('utf8').splitlines()
        if len(line)!=1 or not line[0].startswith('— '+name+' '):
            return None
        signature=b64(line[0][len('— '+name+' '):])
        if len(signature)!=68 or signature[:4]!=expected_id:
            return None
        Ed25519PublicKey.from_public_bytes(raw_pub).verify(signature[4:], note_text)
        return {'origin':head[0], 'size':size, 'root':root.hex(), 'note_sha256':hashlib.sha256(data).hexdigest()}
    except (UnicodeDecodeError, ValueError, InvalidSignature, TypeError, OverflowError, binascii.Error):
        return None


def node(a,b):
    return hashlib.sha256(b'\x01'+a+b).digest()


def root_from_leaves(digests):
    if len(digests)==0:
        return hashlib.sha256(b'').digest()
    if len(digests)==1:
        return digests[0]
    pivot=1<<((len(digests)-1).bit_length()-1)
    return node(root_from_leaves(digests[:pivot]),root_from_leaves(digests[pivot:]))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args):
        return None

# Never honor HTTP_PROXY/ALL_PROXY or a malicious empty NO_PROXY for this loopback lab.
_OPENER=build_opener(ProxyHandler({}), NoRedirect)


def fetch(base,path,content_type,limit):
    req=Request(base+path,method='GET',headers={'Accept-Encoding':'identity','Cache-Control':'no-store'})
    with _OPENER.open(req,timeout=2) as response:
        if response.status!=200 or response.headers.get_content_type()!=content_type:
            raise ValueError('BAD_HTTP_STATUS_OR_TYPE')
        if response.headers.get('Content-Encoding') not in (None,'identity'):
            raise ValueError('UNSUPPORTED_ENCODING')
        val=response.read(limit+1)
        if len(val)>limit:
            raise ValueError('EXCESSIVE_RESPONSE_SIZE')
        return val


def allowed_base(base):
    try:
        p=urlsplit(base)
        return (p.scheme=='http' and p.hostname=='127.0.0.1'
                and p.port is not None and 1 <= p.port <= 65535
                and p.username is None and p.password is None
                and p.path in ('','/') and not p.query and not p.fragment)
    except (TypeError,ValueError):
        return False


def result(status,reason,preview=False):
    return {'verdict':status,'reason':reason,'read_only_preview':preview,
            'external_actions':0,'operational_authority':'NONE',
            'source_truth':'UNKNOWN','real_ario_log_witnessed':'NOT_ESTABLISHED',
            'real_operator_custody':'NOT_ESTABLISHED', 'latest_world_state':'UNKNOWN',
            'independently_retained_prior':'NOT_ESTABLISHED',
            'memory_admitted':False}


def observe(base,*,pinned_vkey=None,retained_prior=None,retained_highwater=None):
    if not allowed_base(base):return result('HOLD_UNCERTAIN','NON_LOOPBACK_URL')
    if pinned_vkey is None:return result('HOLD_UNCERTAIN','NO_OUT_OF_BAND_VKEY')
    if retained_prior is None:return result('HOLD_UNCERTAIN','NO_RETAINED_PRIOR')
    prior=verify_note(retained_prior,pinned_vkey)
    if prior is None:return result('HOLD_UNCERTAIN','PRIOR_SIGNATURE_INVALID')
    if retained_highwater is None:return result('HOLD_UNCERTAIN','NO_RETAINED_HIGHWATER')
    highwater=verify_note(retained_highwater,pinned_vkey)
    if highwater is None:return result('HOLD_UNCERTAIN','HIGHWATER_SIGNATURE_INVALID')
    if highwater['size']<prior['size']:
        return result('HOLD_UNCERTAIN','HIGHWATER_BELOW_PRIOR')
    if highwater['size']==prior['size'] and highwater['root']!=prior['root']:
        return result('DENY','PINNED_PRIOR_AND_HIGHWATER_FORK')
    try:
        port=urlsplit(base).port
        base=f'http://127.0.0.1:{port}'
        raw_note=fetch(base,'/checkpoint','text/plain',MAX_NOTE)
        candidate=verify_note(raw_note,pinned_vkey)
        if candidate is None:
            return result('DENY','CHECKPOINT_NOTE_SIGNATURE_OR_FORMAT_INVALID')
        n=candidate['size']
        if n<highwater['size']:
            return result('DENY','OLDER_THAN_RETAINED_HIGHWATER')
        if n==highwater['size'] and candidate['root']!=highwater['root']:
            return result('DENY','EQUIVOCATION_SAME_SIZE')
        if n<prior['size']:
            return result('DENY','OLDER_THAN_RETAINED_PRIOR')
        if n>highwater['size']:
            # Need consistency from *highwater*, not just from prior.
            # This toy only has 3->8 proof, and cannot silently promote others.
            if highwater['size']!=3 or n!=8:
                return result('HOLD_UNCERTAIN','UNSUPPORTED_HIGHWATER_TO_CANDIDATE_PATH')
        elif n>prior['size'] and highwater['size']!=n:
            return result('HOLD_UNCERTAIN','HIGHWATER_INCONSISTENT_WITH_CANDIDATE')

        tile=fetch(base,f'/tile/0/0.p/{n}','application/octet-stream',MAX_TILE)
        entries=fetch(base,f'/tile/entries/0.p/{n}','application/octet-stream',MAX_ENTRIES)
        if len(tile)!=32*n:
            return result('DENY','TILE_WIDTH_OR_HASH_SIZE_WRONG')
        hashes=[tile[j*32:(j+1)*32] for j in range(n)]
        raw=[]; offset=0
        for i in range(n):
            if offset+2>len(entries):return result('DENY','BUNDLE_TRUNCATED')
            sz=struct.unpack('>H',entries[offset:offset+2])[0];offset+=2
            if sz==0 or sz>2048 or offset+sz>len(entries):return result('DENY','BUNDLE_BAD_LENGTH')
            event=entries[offset:offset+sz];offset+=sz
            if hashlib.sha256(b'\x00'+event).digest()!=hashes[i]:
                return result('DENY','TILE_AND_ENTRY_HASH_DISAGREE')
            # Stronger *supplied* public research event semantics, still no real event completeness.
            try:
                obj=json.loads(event, object_pairs_hook=lambda p: strict_pairs(p))
            except (ValueError, UnicodeDecodeError, TypeError):
                return result('HOLD_UNCERTAIN','PUBLIC_EVENT_BAD_JSON')
            if (type(obj) is not dict or obj.get('schema')!='ARIO_W20_SYNTHETIC_EVENT_V1'
                or type(obj.get('sequence')) is not int or obj['sequence']!=i
                or obj.get('action_authority')!='NONE' or obj.get('memory_truth')!='UNKNOWN'
                or set(obj)!={'schema','sequence','kind','payload_sha256','declared_origin','memory_truth','action_authority'}):
                return result('HOLD_UNCERTAIN','NON_SYNTHETIC_OR_EXTRA_EVENT_FIELDS')
            raw.append(event)
        if offset!=len(entries):return result('DENY','BUNDLE_TRAILING_BYTES')
        if root_from_leaves(hashes).hex()!=candidate['root']:
            return result('DENY','TILE_ROOT_DOES_NOT_MATCH_SIGNED_CHECKPOINT')
        if n>prior['size']:
            cp=fetch(base,'/w22/consistency/3/8','application/json',MAX_PROOF)
            proof=json.loads(cp,object_pairs_hook=strict_pairs)
            if (type(proof) is not dict or set(proof)!={'schema','old_size','new_size','nodes'}
                or proof['schema']!='ARIO_W22_LOCAL_COMPACT_PATH_V1'
                or proof['old_size']!=prior['size'] or proof['new_size']!=n
                or not verify_consistency(prior['size'],n,prior['root'],candidate['root'],proof['nodes'])):
                return result('DENY','INVALID_LOCAL_COMPACT_CONSISTENCY_PROOF')
        return result('HISTORICAL_CONSISTENT','SIGNED_NOTE_AND_C2SP_PARTIAL_TILE_SUBSET_NOT_WORLD_FRESHNESS',True)
    except (OSError,ValueError,TypeError,UnicodeDecodeError,OverflowError,KeyError):
        return result('HOLD_UNCERTAIN','NETWORK_OR_WIRE_ERROR')


def strict_pairs(pairs):
    out={}
    for k,v in pairs:
        if k in out:raise ValueError('DUPLICATE_JSON_KEY')
        out[k]=v
    return out
