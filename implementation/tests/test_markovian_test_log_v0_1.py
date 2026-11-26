from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.markovian_test_log_v0_1.markovian_test_log import (
    ORIGIN, WITNESS_NAME, WITNESS_VKEY, Hold, _b64, _SIGTYPE_COSIGN,
    append_synthetic_record, build_witness_request, canonical_json,
    consistency_proof, key_id, make_vkey, merkle_tree_hash, parse_checkpoint,
    parse_vkey, prepare_bundle, public_vkey_for_signer, sha256,
    sign_checkpoint, synthetic_capsule, synthetic_leaf, verify_bundle,
    verify_consistency, verify_cosigned_checkpoint, verify_log_checkpoint,
    verify_witness_cosignature_line,
)

def signer(seed: int = 1):
    return Ed25519PrivateKey.from_private_bytes(bytes([seed]) * 32)

def witness_vkey_for(key, name=WITNESS_NAME):
    pub=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    kid=key_id(name,pub,_SIGTYPE_COSIGN)
    return f"{name}+{kid.hex()}+{_b64(bytes([_SIGTYPE_COSIGN])+pub)}"

def witness_cosig(note, key, name=WITNESS_NAME, timestamp=1_800_000_000):
    parsed=parse_checkpoint(note)
    pub=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    kid=key_id(name,pub,_SIGTYPE_COSIGN)
    message=b"cosignature/v1\ntime "+str(timestamp).encode()+b"\n"+parsed["note_text"]
    payload=kid+timestamp.to_bytes(8,"big")+key.sign(message)
    return f"— {name} {_b64(payload)}\n".encode()

def test_c2sp_vkey_uses_signature_type_one_and_recomputed_key_id():
    key=signer(7)
    value=public_vkey_for_signer(key)
    name,kid,pub=parse_vkey(value,expected_sig_type=1)
    assert name==ORIGIN
    assert kid==key_id(ORIGIN,pub,1)
    assert len(pub)==32

def test_checkpoint_is_c2sp_note_and_signature_verifies():
    key=signer(8)
    leaves=[b'{"synthetic":true}']
    note=sign_checkpoint(ORIGIN,leaves,key)
    parsed=verify_log_checkpoint(note,make_vkey(ORIGIN,key.public_key().public_bytes(
        serialization.Encoding.Raw,serialization.PublicFormat.Raw)))
    assert parsed["tree_size"]==1
    assert parsed["root"]==merkle_tree_hash(leaves)
    assert note.endswith(b"\n")
    assert b"\n\n— "+ORIGIN.encode()+b" " in note

def test_consistency_proofs_match_rfc6962_for_all_prefixes():
    leaves=[f"synthetic-{i}".encode() for i in range(1,18)]
    for new_size in range(2,len(leaves)+1):
        for old_size in range(1,new_size):
            proof=consistency_proof(leaves[:new_size],old_size)
            assert verify_consistency(old_size,new_size,proof,
                merkle_tree_hash(leaves[:old_size]),merkle_tree_hash(leaves[:new_size]))

def test_witness_request_has_exact_c2sp_framing():
    note=b"origin\n1\n"+base64.b64encode(hashlib.sha256(b"x").digest())+b"\n\n— origin sig\n"
    proof=[bytes(range(32))]
    request=build_witness_request(1,proof,note)
    assert request.startswith(b"old 1\n"+_b64(proof[0]).encode()+b"\n\n")
    assert request.endswith(note)

def test_witness_cosignature_is_verified_against_pinned_key():
    log=signer(9); witness=signer(10)
    vkey=make_vkey(ORIGIN,log.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))
    note=sign_checkpoint(ORIGIN,[b"synthetic"],log)
    line=witness_cosig(note,witness)
    parsed=parse_checkpoint(note)
    verified=verify_witness_cosignature_line(parsed["note_text"],line,witness_vkey_for(witness))
    assert verified["witness"]==WITNESS_NAME
    assert verify_cosigned_checkpoint(note+line,vkey,witness_vkey_for(witness))["tree_size"]==1

def test_wrong_witness_key_rejects_cosignature():
    log=signer(11); witness=signer(12); wrong=signer(13)
    vkey=make_vkey(ORIGIN,log.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))
    note=sign_checkpoint(ORIGIN,[b"synthetic"],log)
    line=witness_cosig(note,witness)
    with pytest.raises(Hold):
        verify_cosigned_checkpoint(note+line,vkey,witness_vkey_for(wrong))

def test_prepare_bundle_is_public_only_and_verifies(tmp_path:Path):
    key=signer(14)
    out=tmp_path/"bundle"
    result=prepare_bundle(out,key)
    assert result["tree_size"]==1
    assert verify_bundle(out)["checkpoint_sha256"]==result["checkpoint_sha256"]
    assert sorted(p.name for p in out.iterdir())==[
        "capsule.json","checkpoint","entries","history","manifest.json","vkey.txt"
    ]
    assert not any("private" in p.name.lower() or p.suffix==".pem" for p in out.rglob("*"))

def test_append_builds_consistent_second_checkpoint(tmp_path:Path):
    key=signer(15); out=tmp_path/"bundle"
    prepare_bundle(out,key)
    first=(out/"checkpoint").read_bytes()
    result=append_synthetic_record(out,key)
    second=(out/"checkpoint").read_bytes()
    a=verify_log_checkpoint(first,public_vkey_for_signer(key))
    b=verify_log_checkpoint(second,public_vkey_for_signer(key))
    leaves=(out/"entries").read_bytes().splitlines()
    proof=consistency_proof(leaves,1)
    assert result["tree_size"]==2
    assert b["tree_size"]==2
    assert verify_consistency(1,2,proof,a["root"],b["root"])
    assert (out/"history"/"checkpoint-000001").read_bytes()==first

def test_append_refuses_a_different_private_key(tmp_path:Path):
    out=tmp_path/"bundle"
    prepare_bundle(out,signer(16))
    with pytest.raises(Hold,match="HOLD_SIGNER_DOES_NOT_MATCH_BUNDLE"):
        append_synthetic_record(out,signer(17))

def test_bundle_detects_tampered_entries_and_checkpoint(tmp_path:Path):
    out=tmp_path/"bundle"; prepare_bundle(out,signer(18))
    entries=(out/"entries").read_bytes()
    (out/"entries").write_bytes(entries.replace(b"alpha",b"ALPHA"))
    with pytest.raises(Hold):
        verify_bundle(out)
    out2=tmp_path/"bundle2"; prepare_bundle(out2,signer(19))
    cp=(out2/"checkpoint").read_bytes()
    (out2/"checkpoint").write_bytes(cp.replace(b"\n1\n",b"\n2\n",1))
    with pytest.raises(Hold):
        verify_bundle(out2)

def test_prepare_refuses_overwrite(tmp_path:Path):
    out=tmp_path/"bundle"; prepare_bundle(out,signer(20))
    with pytest.raises(Hold,match="HOLD_OUTPUT_ALREADY_EXISTS"):
        prepare_bundle(out,signer(20))

def test_canonical_json_duplicate_keys_rejected():
    from research.markovian_test_log_v0_1.markovian_test_log import parse_canonical_json
    with pytest.raises(Hold):
        parse_canonical_json(b'{"a":1,"a":2}')

def test_published_markovian_witness_vkey_is_well_formed():
    name,kid,pub=parse_vkey(WITNESS_VKEY,expected_sig_type=4)
    assert name==WITNESS_NAME
    assert len(kid)==4 and len(pub)==32
