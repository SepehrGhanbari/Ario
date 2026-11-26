"""Memory cold-recovery bridge — RESEARCH_ONLY protocol model.
The model receipt/readback format below is NOT C2SP wire format. A real adapter
must verify the official C2SP/Sigsum log proof and Kladje cosignature first.
No live witness, real key, trust activation, or production memory is used here.
"""
from __future__ import annotations
import base64, hashlib, json, os, re, stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from core.memory_consolidation import ConsolidationEngine
from core.memory_snapshot import decode_cognitive_memory_snapshot

CHECKPOINT_FORMAT="ario.memory-cold-recovery-checkpoint"
CHECKPOINT_SCHEMA=1
SCOPE="ario.cognitive-memory-source-history.v1"
ZERO_HASH="0"*64
MAX_SNAPSHOT_BYTES=32*1024*1024
MAX_LEDGER_BYTES=16*1024*1024
MAX_CHECKPOINT_BYTES=64*1024
MAX_CHAIN_LENGTH=100_000
_HEX=re.compile(r"[0-9a-f]{64}\Z")
_WITNESS_DOMAIN=b"ARIO-MODEL-WITNESS-RECEIPT-v1\0"
_READBACK_DOMAIN=b"ARIO-MODEL-LATEST-READBACK-v1\0"

class RecoveryHold(ValueError):
    """Cold recovery failed closed; no memory state is installed."""

def sha256(raw: bytes)->str:
    if type(raw) is not bytes: raise RecoveryHold("HOLD_IMMUTABLE_BYTES_REQUIRED")
    return hashlib.sha256(raw).hexdigest()

def _valid_hash(value: Any)->bool:
    return type(value) is str and _HEX.fullmatch(value) is not None

def canonical_json(value: Any)->bytes:
    try: return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")
    except (TypeError,ValueError,UnicodeEncodeError,RecursionError) as exc: raise RecoveryHold("HOLD_NONCANONICAL_JSON") from exc

def _pairs_no_duplicates(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise RecoveryHold("HOLD_DUPLICATE_JSON_KEY")
        result[key]=value
    return result

def _reject_constant(_): raise RecoveryHold("HOLD_NONSTANDARD_JSON_CONSTANT")

def parse_canonical_json(raw:bytes,*,max_bytes:int):
    if type(raw) is not bytes or not raw or len(raw)>max_bytes: raise RecoveryHold("HOLD_JSON_SIZE")
    try:
        value=json.loads(raw.decode("ascii",errors="strict"),object_pairs_hook=_pairs_no_duplicates,parse_constant=_reject_constant)
    except RecoveryHold: raise
    except (UnicodeDecodeError,json.JSONDecodeError,RecursionError) as exc: raise RecoveryHold("HOLD_INVALID_JSON") from exc
    if canonical_json(value)!=raw: raise RecoveryHold("HOLD_NONCANONICAL_JSON_BYTES")
    return value

def _parse_ledger(raw:bytes)->list[str]:
    if type(raw) is not bytes or len(raw)>MAX_LEDGER_BYTES: raise RecoveryHold("HOLD_LEDGER_SIZE")
    if raw and not raw.endswith(b"\n"): raise RecoveryHold("HOLD_LEDGER_INCOMPLETE_TAIL")
    hashes=[]
    for line_no,line in enumerate(raw.splitlines(keepends=True),start=1):
        if not line.endswith(b"\n"): raise RecoveryHold(f"HOLD_LEDGER_INCOMPLETE_LINE_{line_no}")
        clean=line.strip(b" \t\r\n")
        if not clean: continue
        try:
            event=json.loads(clean.decode("utf-8",errors="strict"),object_pairs_hook=_pairs_no_duplicates,parse_constant=_reject_constant)
        except RecoveryHold: raise
        except (UnicodeDecodeError,json.JSONDecodeError,RecursionError) as exc: raise RecoveryHold(f"HOLD_LEDGER_INVALID_JSON_LINE_{line_no}") from exc
        if type(event) is not dict: raise RecoveryHold(f"HOLD_LEDGER_EVENT_NOT_OBJECT_{line_no}")
        hashes.append(hashlib.sha256(clean).hexdigest())
    return hashes

def build_checkpoint(snapshot:bytes,ledger:bytes,*,generation:int,previous_checkpoint_sha256:str,node_count:int,attribution_count:int)->bytes:
    if type(snapshot) is not bytes or not 0<len(snapshot)<=MAX_SNAPSHOT_BYTES: raise RecoveryHold("HOLD_SNAPSHOT_SIZE")
    if type(generation) is not int or isinstance(generation,bool) or not 1<=generation<2**63: raise RecoveryHold("HOLD_GENERATION")
    if not _valid_hash(previous_checkpoint_sha256): raise RecoveryHold("HOLD_PREVIOUS_CHECKPOINT_HASH")
    if (generation==1)!=(previous_checkpoint_sha256==ZERO_HASH): raise RecoveryHold("HOLD_GENESIS_LINK")
    if type(node_count) is not int or isinstance(node_count,bool) or node_count<0: raise RecoveryHold("HOLD_NODE_COUNT")
    if type(attribution_count) is not int or isinstance(attribution_count,bool) or attribution_count<0: raise RecoveryHold("HOLD_ATTRIBUTION_COUNT")
    ledger_hashes=_parse_ledger(ledger)
    document={
        "format":CHECKPOINT_FORMAT,"schema_version":CHECKPOINT_SCHEMA,"scope":SCOPE,
        "generation":generation,"previous_checkpoint_sha256":previous_checkpoint_sha256,
        "snapshot_sha256":sha256(snapshot),"snapshot_bytes":len(snapshot),
        "ledger_sha256":sha256(ledger),"ledger_bytes":len(ledger),
        "ledger_record_count":len(ledger_hashes),"ledger_unique_hash_count":len(set(ledger_hashes)),
        "node_count":node_count,"attribution_count":attribution_count,
    }
    encoded=canonical_json(document)
    if len(encoded)>MAX_CHECKPOINT_BYTES: raise RecoveryHold("HOLD_CHECKPOINT_SIZE")
    return encoded

def parse_checkpoint(raw:bytes,expected_sha256:str)->dict[str,Any]:
    if not _valid_hash(expected_sha256) or sha256(raw)!=expected_sha256: raise RecoveryHold("HOLD_CHECKPOINT_DIGEST_MISMATCH")
    value=parse_canonical_json(raw,max_bytes=MAX_CHECKPOINT_BYTES)
    expected={"format","schema_version","scope","generation","previous_checkpoint_sha256","snapshot_sha256","snapshot_bytes","ledger_sha256","ledger_bytes","ledger_record_count","ledger_unique_hash_count","node_count","attribution_count"}
    if type(value) is not dict or set(value)!=expected: raise RecoveryHold("HOLD_CHECKPOINT_SCHEMA")
    if value["format"]!=CHECKPOINT_FORMAT or value["schema_version"]!=CHECKPOINT_SCHEMA: raise RecoveryHold("HOLD_CHECKPOINT_VERSION")
    if value["scope"]!=SCOPE: raise RecoveryHold("HOLD_CHECKPOINT_SCOPE")
    if type(value["generation"]) is not int or isinstance(value["generation"],bool) or value["generation"]<1: raise RecoveryHold("HOLD_CHECKPOINT_GENERATION")
    for field in ("previous_checkpoint_sha256","snapshot_sha256","ledger_sha256"):
        if not _valid_hash(value[field]): raise RecoveryHold("HOLD_CHECKPOINT_HASH_FIELD")
    for field in ("snapshot_bytes","ledger_bytes","ledger_record_count","ledger_unique_hash_count","node_count","attribution_count"):
        if type(value[field]) is not int or isinstance(value[field],bool) or value[field]<0: raise RecoveryHold("HOLD_CHECKPOINT_COUNT_FIELD")
    if value["snapshot_bytes"]==0 or value["snapshot_bytes"]>MAX_SNAPSHOT_BYTES: raise RecoveryHold("HOLD_CHECKPOINT_SNAPSHOT_BYTES")
    if value["ledger_bytes"]>MAX_LEDGER_BYTES or value["ledger_unique_hash_count"]>value["ledger_record_count"]: raise RecoveryHold("HOLD_CHECKPOINT_LEDGER_COUNTS")
    if (value["generation"]==1)!=(value["previous_checkpoint_sha256"]==ZERO_HASH): raise RecoveryHold("HOLD_CHECKPOINT_GENESIS_LINK")
    return value

class ContentAddressedArchive:
    """Create-only byte store used by the lab; not a deployed independent custodian."""
    def __init__(self,root:str|os.PathLike[str])->None:
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        if self.root.is_symlink() or not self.root.is_dir(): raise RecoveryHold("HOLD_ARCHIVE_ROOT_NOT_DIRECTORY")
    def _path(self,digest:str)->Path:
        if not _valid_hash(digest): raise RecoveryHold("HOLD_ARCHIVE_OBJECT_HASH")
        return self.root/digest
    def put(self,raw:bytes)->str:
        if type(raw) is not bytes or not raw or len(raw)>MAX_SNAPSHOT_BYTES: raise RecoveryHold("HOLD_ARCHIVE_OBJECT_SIZE")
        digest=sha256(raw); target=self._path(digest)
        try:
            with target.open("xb") as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        except FileExistsError:
            if target.is_symlink() or not target.is_file() or target.read_bytes()!=raw: raise RecoveryHold("HOLD_ARCHIVE_IMMUTABLE_CONFLICT")
        except OSError as exc: raise RecoveryHold("HOLD_ARCHIVE_WRITE_FAILED") from exc
        return digest
    def get(self,digest:str)->bytes:
        target=self._path(digest)
        try:
            metadata=target.stat()
            if target.is_symlink() or not stat.S_ISREG(metadata.st_mode): raise RecoveryHold("HOLD_ARCHIVE_OBJECT_NOT_REGULAR")
            if metadata.st_size<=0 or metadata.st_size>MAX_SNAPSHOT_BYTES: raise RecoveryHold("HOLD_ARCHIVE_OBJECT_SIZE")
            raw=target.read_bytes()
        except RecoveryHold: raise
        except FileNotFoundError as exc: raise RecoveryHold("HOLD_EXTERNAL_OBJECT_MISSING") from exc
        except OSError as exc: raise RecoveryHold("HOLD_ARCHIVE_READ_FAILED") from exc
        if sha256(raw)!=digest: raise RecoveryHold("HOLD_EXTERNAL_OBJECT_DIGEST_MISMATCH")
        return raw

@dataclass(frozen=True)
class PriorFloor:
    generation:int
    checkpoint_sha256:str

@dataclass(frozen=True)
class RecoveryResult:
    status:str
    freshness:str
    checkpoint_sha256:str
    checkpoint:dict[str,Any]
    snapshot:bytes
    ledger:bytes
    engine:ConsolidationEngine
    source_guard:Any

def _verify_signed_envelope(raw:bytes,public_key:bytes,*,domain:bytes,expected_body_keys:set[str])->dict[str,Any]:
    if type(public_key) is not bytes or len(public_key)!=32: raise RecoveryHold("HOLD_PINNED_PUBLIC_KEY")
    envelope=parse_canonical_json(raw,max_bytes=16*1024)
    if type(envelope) is not dict or set(envelope)!={"body","signature"}: raise RecoveryHold("HOLD_SIGNED_ENVELOPE_SCHEMA")
    body=envelope["body"]
    if type(body) is not dict or set(body)!=expected_body_keys: raise RecoveryHold("HOLD_SIGNED_BODY_SCHEMA")
    if type(envelope["signature"]) is not str: raise RecoveryHold("HOLD_SIGNATURE_ENCODING")
    try:
        signature=base64.b64decode(envelope["signature"],validate=True)
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature,domain+canonical_json(body))
    except (ValueError,InvalidSignature) as exc: raise RecoveryHold("HOLD_EXTERNAL_SIGNATURE_INVALID") from exc
    return body

def verify_model_witness_receipt(raw:bytes,public_key:bytes)->dict[str,Any]:
    """Test-only direct Ed25519 receipt; deliberately not C2SP wire-compatible."""
    keys={"format","witness_id","scope","checkpoint_sha256","generation","previous_checkpoint_sha256"}
    body=_verify_signed_envelope(raw,public_key,domain=_WITNESS_DOMAIN,expected_body_keys=keys)
    if body["format"]!="ario.model-witness-receipt.v1" or body["scope"]!=SCOPE: raise RecoveryHold("HOLD_WITNESS_RECEIPT_SCOPE")
    if not _valid_hash(body["checkpoint_sha256"]) or not _valid_hash(body["previous_checkpoint_sha256"]): raise RecoveryHold("HOLD_WITNESS_RECEIPT_HASH")
    if type(body["generation"]) is not int or isinstance(body["generation"],bool) or body["generation"]<1: raise RecoveryHold("HOLD_WITNESS_RECEIPT_GENERATION")
    if type(body["witness_id"]) is not str or not body["witness_id"]: raise RecoveryHold("HOLD_WITNESS_ID")
    return body

def verify_model_latest_readback(raw:bytes,public_key:bytes,*,expected_nonce:str)->dict[str,Any]:
    """Test-only nonce-bound monitor readback; not an IPng/Kladje endpoint."""
    keys={"format","monitor_id","scope","checkpoint_sha256","generation","nonce"}
    body=_verify_signed_envelope(raw,public_key,domain=_READBACK_DOMAIN,expected_body_keys=keys)
    if body["format"]!="ario.model-latest-readback.v1" or body["scope"]!=SCOPE: raise RecoveryHold("HOLD_LATEST_READBACK_SCOPE")
    if type(expected_nonce) is not str or not expected_nonce or body["nonce"]!=expected_nonce: raise RecoveryHold("HOLD_LATEST_READBACK_NONCE")
    if not _valid_hash(body["checkpoint_sha256"]): raise RecoveryHold("HOLD_LATEST_READBACK_HASH")
    if type(body["generation"]) is not int or isinstance(body["generation"],bool) or body["generation"]<1: raise RecoveryHold("HOLD_LATEST_READBACK_GENERATION")
    if type(body["monitor_id"]) is not str or not body["monitor_id"]: raise RecoveryHold("HOLD_LATEST_READBACK_MONITOR_ID")
    return body

def _verify_chain(archive:ContentAddressedArchive,checkpoint_sha256:str,current:dict[str,Any],prior_floor:PriorFloor|None)->list[str]:
    chain=[]; seen=set(); digest=checkpoint_sha256; checkpoint=current
    while True:
        if digest in seen or len(chain)>=MAX_CHAIN_LENGTH: raise RecoveryHold("HOLD_CHECKPOINT_CHAIN_CYCLE_OR_LIMIT")
        seen.add(digest); chain.append(digest)
        generation=checkpoint["generation"]; previous=checkpoint["previous_checkpoint_sha256"]
        if generation==1:
            if previous!=ZERO_HASH: raise RecoveryHold("HOLD_CHECKPOINT_CHAIN_GENESIS")
            break
        if previous==ZERO_HASH: raise RecoveryHold("HOLD_CHECKPOINT_CHAIN_GAP")
        parent=parse_checkpoint(archive.get(previous),previous)
        if parent["scope"]!=checkpoint["scope"] or parent["generation"]!=generation-1: raise RecoveryHold("HOLD_CHECKPOINT_CHAIN_GAP_OR_SCOPE")
        digest,checkpoint=previous,parent
    if prior_floor is not None:
        if (type(prior_floor.generation) is not int or isinstance(prior_floor.generation,bool) or prior_floor.generation<1 or not _valid_hash(prior_floor.checkpoint_sha256)):
            raise RecoveryHold("HOLD_PRIOR_FLOOR_SCHEMA")
        if prior_floor.checkpoint_sha256 not in chain: raise RecoveryHold("HOLD_PRIOR_FLOOR_NOT_ANCESTOR")
        if chain.index(prior_floor.checkpoint_sha256)!=current["generation"]-prior_floor.generation: raise RecoveryHold("HOLD_PRIOR_FLOOR_GENERATION_MISMATCH")
    return chain

def recover_cold(archive:ContentAddressedArchive,witness_receipt:bytes,witness_public_key:bytes,*,allowlisted_tools:set[str],require_current:bool=True,latest_readback:bytes|None=None,monitor_public_key:bytes|None=None,nonce:str|None=None,prior_floor:PriorFloor|None=None)->RecoveryResult:
    """Recover a fresh candidate. Without readback, only a witnessed lower bound is proven."""
    if not isinstance(archive,ContentAddressedArchive): raise RecoveryHold("HOLD_EXTERNAL_ARCHIVE_REQUIRED")
    if type(allowlisted_tools) is not set: raise RecoveryHold("HOLD_SOURCE_ALLOWLIST_REQUIRED")
    receipt=verify_model_witness_receipt(witness_receipt,witness_public_key)
    checkpoint_sha=receipt["checkpoint_sha256"]
    checkpoint=parse_checkpoint(archive.get(checkpoint_sha),checkpoint_sha)
    for field in ("scope","generation","previous_checkpoint_sha256"):
        if receipt[field]!=checkpoint[field]: raise RecoveryHold("HOLD_WITNESS_CHECKPOINT_BINDING")
    _verify_chain(archive,checkpoint_sha,checkpoint,prior_floor)
    if require_current:
        if latest_readback is None or monitor_public_key is None or nonce is None: raise RecoveryHold("HOLD_FRESHNESS_UNAVAILABLE")
        readback=verify_model_latest_readback(latest_readback,monitor_public_key,expected_nonce=nonce)
        if readback["checkpoint_sha256"]!=checkpoint_sha or readback["generation"]!=checkpoint["generation"]:
            raise RecoveryHold("HOLD_LATEST_READBACK_MISMATCH")
        freshness="MODEL_NONCE_READBACK_VERIFIED"; status="RECOVERED_CURRENT_MODEL"
    else:
        freshness="LATESTNESS_NOT_ESTABLISHED"; status="RECOVERED_WITNESSED_LOWER_BOUND"
    snapshot=archive.get(checkpoint["snapshot_sha256"]); ledger=archive.get(checkpoint["ledger_sha256"])
    if len(snapshot)!=checkpoint["snapshot_bytes"] or len(ledger)!=checkpoint["ledger_bytes"]: raise RecoveryHold("HOLD_EXTERNAL_OBJECT_LENGTH")
    ledger_hashes=_parse_ledger(ledger)
    if len(ledger_hashes)!=checkpoint["ledger_record_count"]: raise RecoveryHold("HOLD_LEDGER_RECORD_COUNT")
    if len(set(ledger_hashes))!=checkpoint["ledger_unique_hash_count"]: raise RecoveryHold("HOLD_LEDGER_UNIQUE_HASH_COUNT")
    engine,source_guard=decode_cognitive_memory_snapshot(ConsolidationEngine,snapshot,expected_sha256=checkpoint["snapshot_sha256"],allowlisted_tools=allowlisted_tools)
    if set(ledger_hashes)!=engine.known_ledger_hashes: raise RecoveryHold("HOLD_SNAPSHOT_LEDGER_COVERAGE_MISMATCH")
    if len(engine.nodes)!=checkpoint["node_count"]: raise RecoveryHold("HOLD_SNAPSHOT_NODE_COUNT")
    if len(source_guard.attributions)!=checkpoint["attribution_count"]: raise RecoveryHold("HOLD_SNAPSHOT_ATTRIBUTION_COUNT")
    return RecoveryResult(status,freshness,checkpoint_sha,checkpoint,snapshot,ledger,engine,source_guard)
