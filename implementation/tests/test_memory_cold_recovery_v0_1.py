from __future__ import annotations
import base64, hashlib, json, shutil
from pathlib import Path
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from core.memory_consolidation import ConsolidationEngine
from core.memory_snapshot import encode_cognitive_memory_snapshot
from core.source_monitoring import SourceMonitoringGuard
from research.memory_cold_recovery_v0_1.memory_cold_recovery import (
    ContentAddressedArchive, PriorFloor, RecoveryHold, SCOPE, ZERO_HASH,
    _READBACK_DOMAIN, _WITNESS_DOMAIN, build_checkpoint, canonical_json, recover_cold,
)

def public_bytes(key):
    return key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)

def signed_envelope(body,key,domain):
    sig=key.sign(domain+canonical_json(body))
    return canonical_json({"body":body,"signature":base64.b64encode(sig).decode("ascii")})

def witness_receipt(cp_sha,cp,key):
    body={"format":"ario.model-witness-receipt.v1","witness_id":"synthetic-witness","scope":SCOPE,
          "checkpoint_sha256":cp_sha,"generation":cp["generation"],
          "previous_checkpoint_sha256":cp["previous_checkpoint_sha256"]}
    return signed_envelope(body,key,_WITNESS_DOMAIN)

def latest_readback(cp_sha,generation,nonce,key):
    body={"format":"ario.model-latest-readback.v1","monitor_id":"synthetic-independent-monitor",
          "scope":SCOPE,"checkpoint_sha256":cp_sha,"generation":generation,"nonce":nonce}
    return signed_envelope(body,key,_READBACK_DOMAIN)

def synthetic_memory(record_count):
    engine=ConsolidationEngine(node_id_version="v2")
    guard=SourceMonitoringGuard(allowlisted_tools={"run_tests"})
    lines=[]
    for index in range(record_count):
        event={"event_id":f"SYNTHETIC-MEMORY-{index+1:03d}",
               "concept":f"synthetic_memory_concept_{index+1}",
               "assertion":f"synthetic memory assertion {index+1}","source":"research-fixture"}
        line=json.dumps(event,sort_keys=True,separators=(",",":")).encode("utf-8")
        lines.append(line+b"\n")
        line_hash=hashlib.sha256(line).hexdigest()
        assert engine.ingest_event_stream([(line_hash,event)])==1
        guard.record_unverified_ledger_report(assertion=event["assertion"],record_sha256=line_hash)
    ledger=b"".join(lines)
    return engine,guard,encode_cognitive_memory_snapshot(engine,guard),ledger

def publish_generation(archive,engine,guard,snapshot,ledger,generation,previous,witness_key):
    raw=build_checkpoint(snapshot,ledger,generation=generation,previous_checkpoint_sha256=previous,
                         node_count=len(engine.nodes),attribution_count=len(guard.attributions))
    cp_sha=archive.put(raw); archive.put(snapshot); archive.put(ledger)
    cp=json.loads(raw)
    return cp_sha,cp,witness_receipt(cp_sha,cp,witness_key)

def test_cold_recovery_after_complete_local_history_deletion(tmp_path:Path):
    archive=ContentAddressedArchive(tmp_path/"external-archive"); local=tmp_path/"local-memory"; local.mkdir()
    witness=Ed25519PrivateKey.generate(); monitor=Ed25519PrivateKey.generate()
    engine,guard,snapshot,ledger=synthetic_memory(3)
    cp_sha,cp,receipt=publish_generation(archive,engine,guard,snapshot,ledger,1,ZERO_HASH,witness)
    (local/"memory.snapshot.json").write_bytes(snapshot); (local/"agent-events.jsonl").write_bytes(ledger)
    (local/"local-floor.txt").write_text(cp_sha,encoding="ascii")
    shutil.rmtree(local); assert not local.exists()
    nonce="fresh-recovery-challenge-001"
    result=recover_cold(archive,receipt,public_bytes(witness),allowlisted_tools={"run_tests"},
        require_current=True,latest_readback=latest_readback(cp_sha,1,nonce,monitor),
        monitor_public_key=public_bytes(monitor),nonce=nonce)
    assert result.status=="RECOVERED_CURRENT_MODEL"
    assert result.freshness=="MODEL_NONCE_READBACK_VERIFIED"
    assert result.snapshot==snapshot and result.ledger==ledger and result.checkpoint_sha256==cp_sha
    assert len(result.engine.nodes)==3 and len(result.source_guard.attributions)==3
    assert encode_cognitive_memory_snapshot(result.engine,result.source_guard)==snapshot

def test_witnessed_checkpoint_without_fresh_readback_is_only_a_lower_bound(tmp_path:Path):
    archive=ContentAddressedArchive(tmp_path/"archive"); witness=Ed25519PrivateKey.generate()
    e,g,s,l=synthetic_memory(1); cp_sha,cp,receipt=publish_generation(archive,e,g,s,l,1,ZERO_HASH,witness)
    with pytest.raises(RecoveryHold,match="HOLD_FRESHNESS_UNAVAILABLE"):
        recover_cold(archive,receipt,public_bytes(witness),allowlisted_tools={"run_tests"},require_current=True)
    result=recover_cold(archive,receipt,public_bytes(witness),allowlisted_tools={"run_tests"},require_current=False)
    assert result.status=="RECOVERED_WITNESSED_LOWER_BOUND" and result.freshness=="LATESTNESS_NOT_ESTABLISHED"

def test_replayed_readback_nonce_is_rejected(tmp_path:Path):
    archive=ContentAddressedArchive(tmp_path/"archive"); witness=Ed25519PrivateKey.generate(); monitor=Ed25519PrivateKey.generate()
    e,g,s,l=synthetic_memory(1); cp_sha,cp,receipt=publish_generation(archive,e,g,s,l,1,ZERO_HASH,witness)
    old=latest_readback(cp_sha,1,"old-nonce",monitor)
    with pytest.raises(RecoveryHold,match="HOLD_LATEST_READBACK_NONCE"):
        recover_cold(archive,receipt,public_bytes(witness),allowlisted_tools={"run_tests"},require_current=True,
                     latest_readback=old,monitor_public_key=public_bytes(monitor),nonce="new-nonce")

def test_wrong_witness_or_monitor_key_is_rejected(tmp_path:Path):
    archive=ContentAddressedArchive(tmp_path/"archive"); witness=Ed25519PrivateKey.generate()
    wrong=Ed25519PrivateKey.generate(); monitor=Ed25519PrivateKey.generate()
    e,g,s,l=synthetic_memory(1); cp_sha,cp,receipt=publish_generation(archive,e,g,s,l,1,ZERO_HASH,witness)
    nonce="nonce-wrong-key"; rb=latest_readback(cp_sha,1,nonce,monitor)
    with pytest.raises(RecoveryHold,match="HOLD_EXTERNAL_SIGNATURE_INVALID"):
        recover_cold(archive,receipt,public_bytes(wrong),allowlisted_tools={"run_tests"},require_current=False)
    with pytest.raises(RecoveryHold,match="HOLD_EXTERNAL_SIGNATURE_INVALID"):
        recover_cold(archive,receipt,public_bytes(witness),allowlisted_tools={"run_tests"},require_current=True,
                     latest_readback=rb,monitor_public_key=public_bytes(wrong),nonce=nonce)

def test_snapshot_object_tampering_is_detected_by_content_address(tmp_path:Path):
    archive=ContentAddressedArchive(tmp_path/"archive"); witness=Ed25519PrivateKey.generate(); monitor=Ed25519PrivateKey.generate()
    e,g,s,l=synthetic_memory(1); cp_sha,cp,receipt=publish_generation(archive,e,g,s,l,1,ZERO_HASH,witness)
    archive._path(cp["snapshot_sha256"]).write_bytes(s[:-1]+bytes([s[-1]^1]))
    nonce="tamper-nonce"
    with pytest.raises(RecoveryHold,match="HOLD_EXTERNAL_OBJECT_DIGEST_MISMATCH"):
        recover_cold(archive,receipt,public_bytes(witness),allowlisted_tools={"run_tests"},require_current=True,
                     latest_readback=latest_readback(cp_sha,1,nonce,monitor),monitor_public_key=public_bytes(monitor),nonce=nonce)

def test_missing_snapshot_object_holds_without_partial_restore(tmp_path:Path):
    archive=ContentAddressedArchive(tmp_path/"archive"); witness=Ed25519PrivateKey.generate(); monitor=Ed25519PrivateKey.generate()
    e,g,s,l=synthetic_memory(1); cp_sha,cp,receipt=publish_generation(archive,e,g,s,l,1,ZERO_HASH,witness)
    archive._path(cp["snapshot_sha256"]).unlink(); nonce="missing-object"
    with pytest.raises(RecoveryHold,match="HOLD_EXTERNAL_OBJECT_MISSING"):
        recover_cold(archive,receipt,public_bytes(witness),allowlisted_tools={"run_tests"},require_current=True,
                     latest_readback=latest_readback(cp_sha,1,nonce,monitor),monitor_public_key=public_bytes(monitor),nonce=nonce)

def test_checkpoint_chain_and_prior_floor_reject_rollback(tmp_path:Path):
    archive=ContentAddressedArchive(tmp_path/"archive"); witness=Ed25519PrivateKey.generate(); monitor=Ed25519PrivateKey.generate()
    e1,g1,s1,l1=synthetic_memory(1); cp1,doc1,receipt1=publish_generation(archive,e1,g1,s1,l1,1,ZERO_HASH,witness)
    e2,g2,s2,l2=synthetic_memory(2); cp2,doc2,receipt2=publish_generation(archive,e2,g2,s2,l2,2,cp1,witness)
    nonce="floor-current"
    result=recover_cold(archive,receipt2,public_bytes(witness),allowlisted_tools={"run_tests"},require_current=True,
        latest_readback=latest_readback(cp2,2,nonce,monitor),monitor_public_key=public_bytes(monitor),nonce=nonce,
        prior_floor=PriorFloor(1,cp1))
    assert result.checkpoint["generation"]==2
    stale="floor-rollback"
    with pytest.raises(RecoveryHold,match="HOLD_PRIOR_FLOOR_NOT_ANCESTOR"):
        recover_cold(archive,receipt1,public_bytes(witness),allowlisted_tools={"run_tests"},require_current=True,
            latest_readback=latest_readback(cp1,1,stale,monitor),monitor_public_key=public_bytes(monitor),nonce=stale,
            prior_floor=PriorFloor(2,cp2))

def test_checkpoint_generation_gap_is_rejected(tmp_path:Path):
    archive=ContentAddressedArchive(tmp_path/"archive"); witness=Ed25519PrivateKey.generate()
    e,g,s,l=synthetic_memory(1); cp1,doc1,receipt=publish_generation(archive,e,g,s,l,1,ZERO_HASH,witness)
    e3,g3,s3,l3=synthetic_memory(2)
    raw=build_checkpoint(s3,l3,generation=3,previous_checkpoint_sha256=cp1,node_count=len(e3.nodes),attribution_count=len(g3.attributions))
    cp3=archive.put(raw); doc3=json.loads(raw); receipt3=witness_receipt(cp3,doc3,witness)
    with pytest.raises(RecoveryHold,match="HOLD_CHECKPOINT_CHAIN_GAP_OR_SCOPE"):
        recover_cold(archive,receipt3,public_bytes(witness),allowlisted_tools={"run_tests"},require_current=False)

def test_ledger_and_snapshot_must_describe_the_same_memory(tmp_path:Path):
    archive=ContentAddressedArchive(tmp_path/"archive"); witness=Ed25519PrivateKey.generate()
    e,g,s,l=synthetic_memory(1)
    other={"event_id":"OTHER","concept":"other","assertion":"not the same"}
    other_line=json.dumps(other,sort_keys=True,separators=(",",":")).encode(); other_ledger=other_line+b"\n"
    raw=build_checkpoint(s,other_ledger,generation=1,previous_checkpoint_sha256=ZERO_HASH,
                         node_count=len(e.nodes),attribution_count=len(g.attributions))
    cp_sha=archive.put(raw); archive.put(s); archive.put(other_ledger); doc=json.loads(raw)
    receipt=witness_receipt(cp_sha,doc,witness)
    with pytest.raises(RecoveryHold,match="HOLD_SNAPSHOT_LEDGER_COVERAGE_MISMATCH"):
        recover_cold(archive,receipt,public_bytes(witness),allowlisted_tools={"run_tests"},require_current=False)

def test_restored_historical_empirical_labels_do_not_restore_live_authority(tmp_path:Path):
    archive=ContentAddressedArchive(tmp_path/"archive"); witness=Ed25519PrivateKey.generate()
    e,g,s,l=synthetic_memory(1); stdout=b"synthetic test result"; lock=b"synthetic execution lock"
    g.record_empirical_observation(assertion="synthetic test was observed",tool="run_tests",target="synthetic-fixture",
        exit_code=0,stdout=stdout,execution_lock=lock,
        expected_execution_lock_sha256=hashlib.sha256(lock).hexdigest(),
        expected_stdout_sha256=hashlib.sha256(stdout).hexdigest(),attribution_id="ATTR-SYNTHETIC-VERIFIED")
    s=encode_cognitive_memory_snapshot(e,g)
    cp,doc,receipt=publish_generation(archive,e,g,s,l,1,ZERO_HASH,witness)
    result=recover_cold(archive,receipt,public_bytes(witness),allowlisted_tools={"run_tests"},require_current=False)
    assert "ATTR-SYNTHETIC-VERIFIED" in result.source_guard.attributions
    assert result.source_guard._active_verified_ids==set()
    assert encode_cognitive_memory_snapshot(result.engine,result.source_guard)==s

def test_known_red_joint_rollback_of_archive_witness_and_monitor_is_undetectable(tmp_path:Path):
    """Expected RED boundary: a fresh client cannot detect a common rollback of every anchor."""
    witness=Ed25519PrivateKey.generate(); monitor=Ed25519PrivateKey.generate()
    old_archive=ContentAddressedArchive(tmp_path/"old-archive"); current=ContentAddressedArchive(tmp_path/"current-archive")
    e1,g1,s1,l1=synthetic_memory(1); cp1,doc1,receipt1=publish_generation(old_archive,e1,g1,s1,l1,1,ZERO_HASH,witness)
    for digest in (cp1,doc1["snapshot_sha256"],doc1["ledger_sha256"]): current.put(old_archive.get(digest))
    e2,g2,s2,l2=synthetic_memory(2); cp2,doc2,receipt2=publish_generation(current,e2,g2,s2,l2,2,cp1,witness)
    assert cp2!=cp1
    nonce="fresh-but-common-domain-rollback"
    recovered=recover_cold(old_archive,receipt1,public_bytes(witness),allowlisted_tools={"run_tests"},require_current=True,
        latest_readback=latest_readback(cp1,1,nonce,monitor),monitor_public_key=public_bytes(monitor),nonce=nonce,prior_floor=None)
    assert recovered.checkpoint["generation"]==1
    assert recovered.status=="RECOVERED_CURRENT_MODEL"
    # This passing assertion records the attack's success, not a security pass.
