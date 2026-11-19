#!/usr/bin/env python3
"""W15 research-only GitHub-hosted high-water reference versus locally restored views.

This code has NO network, no real Ario keys or effects. The caller is responsible
for obtaining a freshly fetched remote witness via an out-of-band operator.
A GitHub-hosted file is NOT an independently administered, immutable custodian.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

ROLE_DOMAIN={'grant':'ARIO_W15_SYNTHETIC_GRANT','revoker':'ARIO_W15_SYNTHETIC_REVOCATION','anchor':'ARIO_W15_SYNTHETIC_ANCHOR'}


def canon(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf8')

def digest(obj):
    return hashlib.sha256(canon(obj)).hexdigest()

def blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def public_hex(key):
    return key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()

def sign(key, role, body):
    m={'domain':ROLE_DOMAIN[role], 'body':body}
    return {'domain':m['domain'],'body':body,'signature':key.sign(canon(m)).hex()}

def verify(public, role, packet):
    if type(packet) is not dict or set(packet)!={'domain','body','signature'} or packet.get('domain')!=ROLE_DOMAIN[role] or type(packet['body']) is not dict or type(packet['signature']) is not str or len(packet['signature'])!=128:
        return None
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public)).verify(bytes.fromhex(packet['signature']),canon({'domain':packet['domain'],'body':packet['body']}))
    except (InvalidSignature,ValueError,TypeError,OverflowError):
        return None
    return packet['body']

def make_fixture():
    # All three signer keys are generated in ONE disposable Python process,
    # then destroyed. This proves neither source nor operator independence.
    grant_key,rev_key,anchor_key=(Ed25519PrivateKey.generate() for _ in range(3))
    trust={'grant':public_hex(grant_key),'revoker':public_hex(rev_key),'anchor':public_hex(anchor_key)}
    grant_base={'version':1,'grant_id':'G1','principal':'SYNTHETIC_USER','operation':'READ_ONLY_REVIEW',
                'resource':'report-1','destination':'LOCAL_NOTE','not_before':100,'expires':200}
    grant1=sign(grant_key,'grant',grant_base)
    grant2=sign(grant_key,'grant',{**grant_base,'grant_id':'G2'})
    h0=sign(rev_key,'revoker',{'version':1,'epoch':0,'revoked':[],'prev_head_sha256':None})
    a0=sign(anchor_key,'anchor',{'version':1,'epoch':0,'head_sha256':digest(h0),'prev_anchor_sha256':None})
    h1=sign(rev_key,'revoker',{'version':1,'epoch':1,'revoked':['G1'],'prev_head_sha256':digest(h0)})
    a1=sign(anchor_key,'anchor',{'version':1,'epoch':1,'head_sha256':digest(h1),'prev_anchor_sha256':digest(a0)})
    fixture={'schema':'ARIO_W15_SYNTHETIC_SNAPSHOT_FIXTURE_V1', 'trust':trust,
             'grants':{'G1':grant1,'G2':grant2},
             'snapshots':{'E0':{'head':h0,'anchor':a0},'E1':{'head':h1,'anchor':a1}},
             'authority':'NONE','keys_exported':False,'real_world_truth':'UNKNOWN',
             'admin_independence':'NOT_ESTABLISHED','writer_can_modify_github_data':True}
    remote0={'schema':'ARIO_W15_GITHUB_HOSTED_WITNESS_V1','version':1,'epoch':0,'anchor':a0,
             'anchor_packet_sha256':digest(a0),'hosting_note':'Provider hosted; repo owner can edit. NOT independent custody.'}
    remote1={'schema':'ARIO_W15_GITHUB_HOSTED_WITNESS_V1','version':1,'epoch':1,'anchor':a1,
             'anchor_packet_sha256':digest(a1),'hosting_note':'Provider hosted; repo owner can edit. NOT independent custody.'}
    return fixture,remote0,remote1

def reject_duplicate_pairs(pairs):
    data={}
    for k,v in pairs:
        if k in data: raise ValueError("DUPLICATE_JSON_KEY:"+k)
        data[k]=v
    return data

def read_json_file(path):
    return json.loads(Path(path).read_text("utf8"), object_pairs_hook=reject_duplicate_pairs,
                      parse_constant=lambda val: (_ for _ in ()).throw(ValueError("NONFINITE_JSON:"+val)))

def output_file(path,obj):
    Path(path).write_bytes(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2).encode('utf8')+b'\n')

def result(verdict,reason,local_epoch=None,remote_epoch=None):
    return {'verdict':verdict,'reason':reason,'local_epoch':local_epoch,'reference_epoch':remote_epoch,
            'operational_authority':'NONE','external_actions':0,'real_user_approval':'NOT_ESTABLISHED',
            'remote_reference_independent_custody':'NOT_ESTABLISHED',
            'remote_currentness_guaranteed':False,
            'local_and_remote_common_editor_possible':True}

def assess(fixture, local_snapshot, remote=None, grant_id='G1', candidate=None,known_floor=None):
    """Compare signed synthetic snapshots with an explicit supplied reference.

    Caller-provided reference is NOT automatically current. If no reference,
    fail closed as HOLD; if old but valid, demonstrate the BOTH-OLD failure.
    """
    if type(fixture) is not dict or fixture.get('schema')!='ARIO_W15_SYNTHETIC_SNAPSHOT_FIXTURE_V1':
        return result('HOLD_UNCERTAIN','FIXTURE_SCHEMA')
    trust=fixture.get('trust',{})
    if type(trust) is not dict or set(trust)!={'grant','revoker','anchor'} or any(type(k) is not str or len(k)!=64 for k in trust.values()):
        return result('HOLD_UNCERTAIN','TRUST_ROOT_SCHEMA')
    if type(local_snapshot) is not dict or set(local_snapshot)!={'head','anchor'}:
        return result('HOLD_UNCERTAIN','LOCAL_SNAPSHOT_SCHEMA')
    head=verify(trust['revoker'],'revoker',local_snapshot['head'])
    anchor=verify(trust['anchor'],'anchor',local_snapshot['anchor'])
    if head is None or anchor is None:
        return result('DENY','LOCAL_SIGNATURE_INVALID')
    if set(head)!={'version','epoch','revoked','prev_head_sha256'} or set(anchor)!={'version','epoch','head_sha256','prev_anchor_sha256'} or type(head['epoch']) is not int or type(anchor['epoch']) is not int or type(head['revoked']) is not list or not all(type(i) is str for i in head['revoked']):
        return result('HOLD_UNCERTAIN','LOCAL_TYPED_SCHEMA')
    local_epoch=head['epoch']
    if anchor['epoch']!=local_epoch or anchor['head_sha256']!=digest(local_snapshot['head']):
        return result('DENY','LOCAL_HEAD_ANCHOR_INCONSISTENT',local_epoch)
    if remote is None:
        return result('HOLD_UNCERTAIN','REMOTE_REFERENCE_UNAVAILABLE',local_epoch)
    if (type(remote) is not dict or set(remote)!={'schema','version','epoch','anchor','anchor_packet_sha256','hosting_note'} or remote.get('schema')!='ARIO_W15_GITHUB_HOSTED_WITNESS_V1' or remote.get('version')!=1 or type(remote.get('epoch')) is not int):
        return result('HOLD_UNCERTAIN','REMOTE_REFERENCE_SCHEMA',local_epoch)
    remote_epoch=remote['epoch']
    ranchor=verify(trust['anchor'],'anchor',remote['anchor'])
    if ranchor is None or set(ranchor)!={'version','epoch','head_sha256','prev_anchor_sha256'} or ranchor['epoch']!=remote_epoch or remote['anchor_packet_sha256']!=digest(remote['anchor']):
        return result('DENY','REMOTE_REFERENCE_SIGNATURE_OR_CONTENT_INVALID',local_epoch,remote_epoch)
    if known_floor is not None:
        if type(known_floor) is not int or known_floor<0:
            return result('HOLD_UNCERTAIN','LOCAL_HIGHWATER_BAD_TYPE',local_epoch,remote_epoch)
        if remote_epoch<known_floor:
            return result('DENY','REMOTE_BELOW_PREVIOUSLY_SEEN_EPOCH',local_epoch,remote_epoch)
    if local_epoch<remote_epoch:
        return result('DENY','PRESENTED_STATE_BELOW_REMOTE_REFERENCE',local_epoch,remote_epoch)
    if local_epoch>remote_epoch:
        return result('HOLD_UNCERTAIN','REMOTE_REFERENCE_BEHIND_PRESENTED_STATE',local_epoch,remote_epoch)
    if ranchor['head_sha256'] != digest(local_snapshot['head']):
        return result('DENY','FORKED_HEAD_SAME_EPOCH',local_epoch,remote_epoch)
    if digest(remote['anchor'])!=digest(local_snapshot['anchor']):
        return result('DENY','FORKED_ANCHOR_SAME_EPOCH',local_epoch,remote_epoch)
    grants=fixture.get('grants',{})
    if type(grants) is not dict or grant_id not in grants:
        return result('HOLD_UNCERTAIN','GRANT_ID_UNKNOWN',local_epoch,remote_epoch)
    grant=verify(trust['grant'],'grant',grants[grant_id])
    if grant is None or set(grant)!={'version','grant_id','principal','operation','resource','destination','not_before','expires'}:
        return result('DENY','GRANT_SIGNATURE_OR_SCHEMA_INVALID',local_epoch,remote_epoch)
    if grant['grant_id']!=grant_id:
        return result('DENY','GRANT_ID_MISMATCH',local_epoch,remote_epoch)
    if grant_id in head['revoked']:
        return result('DENY','REVOKED_BY_PRESENTED_HEAD',local_epoch,remote_epoch)
    if candidate is None:
        candidate={'principal':'SYNTHETIC_USER','operation':'READ_ONLY_REVIEW','resource':'report-1','destination':'LOCAL_NOTE','now':150}
    if type(candidate) is not dict or set(candidate)!={'principal','operation','resource','destination','now'} or type(candidate['now']) is not int:
        return result('HOLD_UNCERTAIN','CANDIDATE_SCHEMA',local_epoch,remote_epoch)
    if not grant['not_before']<=candidate['now']<grant['expires']:
        return result('DENY','GRANT_TIME_MISMATCH',local_epoch,remote_epoch)
    if any(grant[k]!=candidate[k] for k in ('principal','operation','resource','destination')):
        return result('DENY','GRANT_SCOPE_MISMATCH',local_epoch,remote_epoch)
    return result('DECLARED_ELIGIBLE_FOR_SEPARATE_GATE','MATCHED_SIGNED_LAB_VIEW_NOT_WORLD_FRESHNESS',local_epoch,remote_epoch)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fixture')
    ap.add_argument('--remote')
    ap.add_argument('--local',default='E0',choices=['E0','E1'])
    ap.add_argument('--grant',default='G1')
    ap.add_argument('--known-floor',type=int)
    ap.add_argument('--init',nargs=3,metavar=('FIXTURE','REMOTE_E0','REMOTE_E1'))
    args=ap.parse_args()
    if args.init:
        fixture,r0,r1=make_fixture()
        for path,obj in zip(args.init,(fixture,r0,r1)):
            output_file(path,obj)
        print(json.dumps({'schema':'ARIO_W15_CREATED_SYNTHETIC_PUBLIC_ONLY','no_private_key_export':True,'fixture_sha256':hashlib.sha256(Path(args.init[0]).read_bytes()).hexdigest()}))
    else:
        if not args.fixture: ap.error('--fixture required')
        f=read_json_file(args.fixture)
        remote=read_json_file(args.remote) if args.remote else None
        print(json.dumps(assess(f,f['snapshots'][args.local],remote,args.grant,known_floor=args.known_floor),sort_keys=True))
if __name__=='__main__':main()
