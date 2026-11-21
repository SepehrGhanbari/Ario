#!/usr/bin/env python3
"""W36 offline read-only Sigsum v2 proof validation; research-only, non-authorizing.

Uses cryptography Ed25519. Inputs are bytes; never writes, contacts a server, or
modifies the Ario repository. Strict version-2 format for this pinned W35 profile,
not a general replacement for the official sigsum-verify implementation.
"""
from __future__ import annotations
import base64
import binascii
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SHA = lambda x: hashlib.sha256(x).digest()
HEX = lambda x: hashlib.sha256(x).hexdigest()
# Explicit research pins. These must not be learned from a modified proof/policy.
PINNED_PROOF_SHA256 = "1bb2eb18c3e92fefe3a27f7e8a09412eb7870b2a33359c13e9530902fba54831"
PINNED_CHECKPOINT_SHA256 = "2202c78bf61138253e13d926733338fedd4b205520619bb6b5083ce9cacf8327"
PINNED_POLICY_SHA256 = "2dfadcc13f67f8be96e1453e1278621107709deda3e4410225fa7a38cc4585eb"
PINNED_PUBKEY_SHA256 = "e2c4ed77210f73c9f6694068fab9f4aef7ea3b4379add119d2c37115add2ce4e"
EXPECTED_SCOPE = "ARIO-W35-PUBLIC-SYNTHETIC-ONLY"
EXPECTED_SCHEMA = "ARIO-W35-SYNTHETIC-CHECKPOINT/0.1"

class CheckFailure(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def require(test: bool, code: str) -> None:
    if not test:
        raise CheckFailure(code)


def hexbytes(value: str, length: int, label: str) -> bytes:
    require(isinstance(value, str) and len(value) == 2 * length, f"MALFORMED_{label}")
    try:
        out = bytes.fromhex(value)
    except ValueError:
        raise CheckFailure(f"MALFORMED_{label}") from None
    require(len(out) == length, f"MALFORMED_{label}")
    return out


def verify_ed25519(public: bytes, signature: bytes, msg: bytes, label: str) -> None:
    try:
        Ed25519PublicKey.from_public_bytes(public).verify(signature, msg)
    except Exception as e:
        # The broad catch is local to crypto verification and maps backend-specific failures.
        raise CheckFailure(f"INVALID_{label}_SIGNATURE") from e


def json_no_duplicates(pairs: list[tuple[str, Any]]) -> dict:
    out = {}
    for k,v in pairs:
        if k in out:
            raise CheckFailure("DUPLICATE_CHECKPOINT_JSON_KEY")
        out[k] = v
    return out


def read_ssh_ed25519(data: bytes) -> bytes:
    try:
        fields = data.decode('ascii').strip().split()
        require(len(fields) >= 2 and fields[0] == 'ssh-ed25519', 'MALFORMED_SUBMITTER_KEY')
        b = base64.b64decode(fields[1], validate=True)
        def take(buf, at):
            require(at + 4 <= len(buf), 'MALFORMED_SUBMITTER_KEY')
            n = int.from_bytes(buf[at:at+4], 'big')
            require(n <= 128 and at + 4 + n <= len(buf), 'MALFORMED_SUBMITTER_KEY')
            return buf[at+4:at+4+n], at+4+n
        name, p = take(b,0)
        key, p = take(b,p)
        require(name == b'ssh-ed25519' and len(key) == 32 and p == len(b), 'MALFORMED_SUBMITTER_KEY')
        return key
    except (UnicodeError, binascii.Error, ValueError) as e:
        raise CheckFailure('MALFORMED_SUBMITTER_KEY') from e


def parse_policy(data: bytes) -> tuple[bytes, dict[str,bytes],int]:
    try:
        text = data.decode('ascii')
    except UnicodeError as e:
        raise CheckFailure('MALFORMED_POLICY') from e
    logs = []
    witnesses: dict[str, bytes] = {}
    groups = {}
    selected = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        parts=line.split()
        if parts[0] == 'log':
            require(len(parts) in (2,3), 'MALFORMED_POLICY')
            logs.append(hexbytes(parts[1],32,'POLICY_LOG_KEY'))
        elif parts[0] == 'witness':
            require(len(parts) == 3 and parts[1] not in witnesses, 'MALFORMED_POLICY')
            witnesses[parts[1]] = hexbytes(parts[2],32,'POLICY_WITNESS_KEY')
        elif parts[0] == 'group':
            require(len(parts) >= 4 and parts[1] not in groups, 'MALFORMED_POLICY')
            name=parts[1]
            require(parts[2].isdigit(), 'MALFORMED_POLICY')
            members=parts[3:]
            require(len(members)==len(set(members)) and all(m in witnesses for m in members),'MALFORMED_POLICY')
            count=int(parts[2]);require(1 <= count <= len(members),'MALFORMED_POLICY')
            groups[name]=(count, tuple(members))
        elif parts[0]=='quorum':
            require(len(parts)==2 and selected is None,'MALFORMED_POLICY')
            selected=parts[1]
        else:
            raise CheckFailure('UNKNOWN_POLICY_DIRECTIVE')
    require(len(logs)==1 and len(witnesses)>=2 and selected in groups,'MALFORMED_POLICY')
    count, members=groups[selected]
    return logs[0], {name:witnesses[name] for name in members}, count


def parse_proof(data: bytes):
    try:
        text=data.decode('ascii')
    except UnicodeError as e:
        raise CheckFailure('MALFORMED_PROOF') from e
    values = {}; cosigs=[]; audit=[]
    allowed={'version','log','leaf','size','root_hash','signature','leaf_index'}
    for line in text.splitlines():
        if not line: continue
        require(line.count('=') == 1, 'MALFORMED_PROOF_LINE')
        k,v=line.split('=',1)
        if k=='cosignature':
            parts=v.split()
            require(len(parts)==3 and parts[1].isdigit(), 'MALFORMED_COSIGNATURE')
            cosigs.append(parts)
        elif k=='node_hash': audit.append(hexbytes(v,32,'AUDIT_NODE'))
        else:
            require(k in allowed, 'UNKNOWN_PROOF_FIELD')
            require(k not in values,'DUPLICATE_PROOF_FIELD')
            values[k]=v
    require(set(values)==allowed, 'MISSING_PROOF_FIELD')
    require(values['version']=='2','UNSUPPORTED_PROOF_VERSION')
    return values,cosigs,audit


class UseDisposition(Enum):
    CONDITIONALLY_USABLE = 'CONDITIONALLY_USABLE'
    SUSPENDED = 'SUSPENDED'
    INSUFFICIENT_SUPPORT = 'INSUFFICIENT_SUPPORT'

@dataclass(frozen=True)
class EvidenceObservation:
    receipt_status: str
    reason: str
    source: str = 'SYNTHETIC_SIGSUM_TEST_PROOF'
    temporal_assessment: str = 'NOT_EVALUATED'
    use_disposition: UseDisposition = UseDisposition.SUSPENDED
    evidence_admission: str = 'NOT_EVALUATED'
    trust_activation: str = 'NO_GO'
    production: str = 'NO_GO'
    signer_authority: str = 'NONE'


def may_use_from_receipt(_: EvidenceObservation) -> bool:
    """This research adapter can never grant use, regardless of proof success."""
    return False


def verify_bytes(checkpoint: bytes, proof: bytes, pub: bytes, policy: bytes,
                 *, strict_proof_pin: bool = True) -> tuple[EvidenceObservation,dict]:
    """True cryptographic checks; failures are nonpositive, no IO."""
    data = {'checkpoint_sha256':HEX(checkpoint), 'proof_sha256':HEX(proof),
            'pubkey_file_sha256':HEX(pub), 'policy_sha256':HEX(policy),
            'quorum_met':False,'proof_valid':False,'pinned_policy':False,
            'leaf_signature':False,'log_signature':False,'merkle_inclusion':False,
            'witness_signatures':0,'witness_quorum':None,
            'scope_validated':False,'snapshot_freshness':'NOT_CHECKED',
            'historical_event_truth':'UNKNOWN','inventory_completeness':'NOT_ESTABLISHED',
            'ario_native_log':'NOT_ESTABLISHED'}
    try:
        if strict_proof_pin:
            require(HEX(proof)==PINNED_PROOF_SHA256, 'PROOF_BYTES_MISMATCH')
        require(HEX(policy)==PINNED_POLICY_SHA256, 'UNPINNED_POLICY')
        data['pinned_policy']=True
        require(HEX(pub)==PINNED_PUBKEY_SHA256,'SUBMITTER_KEY_FILE_MISMATCH')
        require(HEX(checkpoint)==PINNED_CHECKPOINT_SHA256,'CHECKPOINT_BYTES_MISMATCH')
        try:
            obj=json.loads(checkpoint.decode('utf-8'),object_pairs_hook=json_no_duplicates)
        except CheckFailure:
            raise
        except (UnicodeError,ValueError) as e:
            raise CheckFailure('MALFORMED_CHECKPOINT_JSON') from e
        require(isinstance(obj,dict) and obj.get('schema')==EXPECTED_SCHEMA and
                obj.get('scope')==EXPECTED_SCOPE and obj.get('production')=='NO_GO' and
                obj.get('trust_activation')=='NO_GO' and obj.get('authoritative') is False,
                'WRONG_CHECKPOINT_SCOPE_OR_PROFILE')
        require(isinstance(obj.get('records'),list) and all(isinstance(r,dict) and
                r.get('synthetic') is True and r.get('scope')==EXPECTED_SCOPE for r in obj['records']),
                'UNEXPECTED_NON_SYNTHETIC_RECORD')
        require(len(obj['records'])==obj.get('record_count'),'CHECKPOINT_RECORD_COUNT_MISMATCH')
        ids=[r.get('id') for r in obj['records']]
        require(all(isinstance(x,str) and x for x in ids) and len(ids)==len(set(ids)),
                'CHECKPOINT_DUPLICATE_RECORD_ID')
        data['scope_validated']=True
        log_key,witnesses,quorum = parse_policy(policy)
        data['witness_quorum']=quorum
        val,cosigs,audit=parse_proof(proof)
        require(hexbytes(val['log'],32,'LOG_ID')==SHA(log_key),'UNEXPECTED_LOG')
        signer_key=read_ssh_ed25519(pub)
        leaf_parts=val['leaf'].split()
        require(len(leaf_parts)==2, 'MALFORMED_LEAF')
        leaf_keyhash=hexbytes(leaf_parts[0],32,'LEAF_KEYHASH')
        require(leaf_keyhash==SHA(signer_key),'LEAF_SIGNER_MISMATCH')
        sig=hexbytes(leaf_parts[1],64,'LEAF_SIGNATURE')
        digest=SHA(SHA(checkpoint))
        verify_ed25519(signer_key,sig,b'sigsum.org/v1/tree-leaf\0'+digest,'LEAF')
        data['leaf_signature']=True
        require(val['size'].isdigit() and val['leaf_index'].isdigit(), 'MALFORMED_TREE_POSITION')
        size=int(val['size']);i=int(val['leaf_index'])
        require(1<=size<=2**63 and 0<=i<size,'INVALID_TREE_POSITION')
        root=hexbytes(val['root_hash'],32,'TREE_ROOT')
        log_sig=hexbytes(val['signature'],64,'TREE_SIGNATURE')
        sth=b'sigsum.org/v1/tree/'+val['log'].encode()+b'\n'+str(size).encode()+b'\n'+base64.b64encode(root)+b'\n'
        verify_ed25519(log_key,log_sig,sth,'LOG')
        data['log_signature']=True
        matched=set(); signed_witness_names=[]
        hashes={HEX(key):name for name,key in witnesses.items()}
        for keyhash,ts,sg_hex in cosigs:
            keyhash=hexbytes(keyhash,32,'COSIGNER_ID').hex()
            sg=hexbytes(sg_hex,64,'COSIGNATURE')
            if keyhash not in hashes:
                continue  # policy only needs cosignatures of its accepted named keys
            require(keyhash not in matched,'DUPLICATE_WITNESS_COSIGNATURE')
            matched.add(keyhash)
            name=hashes[keyhash]
            verify_ed25519(witnesses[name],sg,b'cosignature/v1\ntime '+ts.encode()+b'\n'+sth,'WITNESS')
            signed_witness_names.append(name)
        data['witness_signatures']=len(matched)
        data['witness_names']=signed_witness_names
        require(len(matched)>=quorum,'WITNESS_QUORUM_NOT_MET')
        data['quorum_met']=True
        # Leaf composition and RFC6962 audit path with exact traversal count.
        leaf=digest+sig+SHA(signer_key)
        r=SHA(b'\x00'+leaf)
        fn=i;sn=size-1
        for sibling in audit:
            if fn & 1 or fn==sn:
                r=SHA(b'\x01'+sibling+r)
                while fn!=0 and not (fn & 1):
                    fn>>=1;sn>>=1
            else: r=SHA(b'\x01'+r+sibling)
            fn>>=1;sn>>=1
        require(sn==0 and r==root, 'MERKLE_INCLUSION_FAILED')
        data['merkle_inclusion']=True
        data['tree_size']=size
        data['leaf_index']=i
        data['tree_root']=root.hex()
        data['proof_valid']=True
        return EvidenceObservation('VERIFIED_SYNTHETIC_INCLUSION','W35_PROOF_VALID'), data
    except CheckFailure as e:
        return EvidenceObservation('INVALID_OR_UNVERIFIED_RECEIPT',e.code), data


def evaluate_floor(evidence: EvidenceObservation, data: dict, floor: dict|None) -> str:
    """No claimed floor unless externally provided; this is a structural fixture check."""
    if evidence.receipt_status != 'VERIFIED_SYNTHETIC_INCLUSION':
        return 'UNKNOWN_INVALID_PROOF'
    if floor is None:
        return 'NOT_CHECKED_NO_EXTERNAL_FLOOR'
    if not floor.get('independently_retained',False):
        return 'UNKNOWN_SELF_REPORTED_FLOOR'
    if floor.get('scope') != EXPECTED_SCOPE:
        return 'UNKNOWN_FLOOR_SCOPE_MISMATCH'
    if floor.get('size') == data['tree_size']:
        return 'MOCK_FLOOR_MATCH' if floor.get('root')==data['tree_root'] else 'UNKNOWN_SAME_SIZE_ROOT_CONFLICT'
    if floor.get('size',0) > data['tree_size']:
        return 'UNKNOWN_STALE_PROOF_RELATIVE_TO_FLOOR'
    return 'UNKNOWN_NEWER_HEAD_REQUIRES_CONSISTENCY_PROOF'


def presentation(e: EvidenceObservation, data: dict) -> dict:
    return {'receipt_status':e.receipt_status,'reason':e.reason,
            **data,'temporal_assessment':e.temporal_assessment,
            'use_disposition':e.use_disposition.value,'may_use':may_use_from_receipt(e),
            'evidence_admission':e.evidence_admission,'trust_activation':e.trust_activation,
            'production':e.production,'signer_authority':e.signer_authority}
