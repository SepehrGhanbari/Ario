#!/usr/bin/env python3
"""W32 read-only GET upgrade for the TWO original public W31 OTS receipts.

Uses published W31 detached proofs, not a new stamp. No POST, no real Ario data,
no keys, no signer, no production, no Genesis/trust. A calendar-provided
BitcoinBlockHeaderAttestation is NOT independently blockchain verified here.
"""
from __future__ import annotations
import argparse
import base64
import binascii
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.request

from opentimestamps.core.timestamp import DetachedTimestampFile, Timestamp
from opentimestamps.core.serialize import StreamDeserializationContext, StreamSerializationContext
from opentimestamps.core.notary import PendingAttestation, BitcoinBlockHeaderAttestation

ROOT=Path(__file__).resolve().parent
GIT_BLOB="138c8b056dd3387f31f5a0facedf43b0f221b742"
EXPECTED_DIGEST="2078bc80586d0e4b00afa48eb8dea31ab3d4749b4912c57a897e4d5e2fb436df"
EVIDENCE_FILE="W31_OTS_OFFLINE_VALIDATED_DETACHED_PROOFS_2026-11-19.json"
ALLOWLIST=frozenset((
    "https://alice.btc.calendar.opentimestamps.org",
    "https://bob.btc.calendar.opentimestamps.org"
))
MAX_REMOTE=65536


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _decode(value, limit):
    if type(value) is not str or len(value)>limit*2:
        raise ValueError("BAD_BASE64_LENGTH")
    raw=base64.b64decode(value,validate=True)
    if len(raw)>limit or base64.b64encode(raw).decode("ascii")!=value:
        raise ValueError("NONCANONICAL_BASE64")
    return raw


def _parse_detached(raw):
    stream=StreamDeserializationContext(BytesIO(raw))
    value=DetachedTimestampFile.deserialize(stream)
    stream.assert_eof()
    return value


def _serialize_detached(value):
    stream=BytesIO()
    value.serialize(StreamSerializationContext(stream))
    return stream.getvalue()


def originals():
    preimage=subprocess.run(["git","cat-file","blob",GIT_BLOB],
        cwd=str(ROOT.parents[1]),check=True,capture_output=True).stdout
    digest=hashlib.sha256(preimage).hexdigest()
    if digest!=EXPECTED_DIGEST or len(preimage)!=765:
        raise ValueError("W31_PINNED_BLOB_MISMATCH")
    data=json.loads((ROOT/EVIDENCE_FILE).read_text("utf-8"))
    checks=data.get("checks")
    if (data.get("preimage_sha256")!=digest or type(checks) is not list
        or len(checks)!=2 or {item.get("calendar") for item in checks if type(item) is dict}!=ALLOWLIST):
        raise ValueError("W31_EVIDENCE_MISMATCH")
    out=[]
    for c in checks:
        raw=_decode(c["detached_ots_b64"],4096)
        if hashlib.sha256(raw).hexdigest()!=c["detached_ots_sha256"]:
            raise ValueError("W31_DETACHED_HASH_MISMATCH")
        detached=_parse_detached(raw)
        if detached.file_digest.hex()!=digest:
            raise ValueError("W31_DETACHED_DIGEST_MISMATCH")
        pending=[(msg,att) for msg,att in detached.timestamp.all_attestations()
                 if isinstance(att,PendingAttestation)]
        if len(pending)!=1 or pending[0][1].uri != c["calendar"]:
            raise ValueError("W31_CALENDAR_COMMITMENT_MISMATCH")
        # A calendar may attest an OTS operation output of bounded variable
        # length, not necessarily exactly the original 32-byte file digest.
        if not 1 <= len(pending[0][0]) <= 64:
            raise ValueError("W31_BAD_CALENDAR_COMMITMENT")
        if any(isinstance(att,BitcoinBlockHeaderAttestation)
               for _,att in detached.timestamp.all_attestations()):
            raise ValueError("W31_ORIGINAL_WAS_NOT_PENDING")
        out.append((c["calendar"],pending[0][0],detached,raw))
    return out


def get_existing_timestamp(calendar_url, commitment, *, opener=None):
    """Only one allowlisted HTTPS GET per calendar. NEVER stamp/submit."""
    if calendar_url not in ALLOWLIST or type(commitment) is not bytes or not (1 <= len(commitment) <= 64):
        raise ValueError("W32_NOT_ALLOWLISTED")
    # Match the *actual* commitment embedded in the previously recorded proof.
    # Arbitrary GET probes are not part of this experiment.
    if commitment not in {msg for host,msg,_,_ in originals() if host==calendar_url}:
        raise ValueError("W32_UNRECOGNIZED_ORIGIN_COMMITMENT")
    url=calendar_url+"/timestamp/"+commitment.hex()
    request=urllib.request.Request(
        url,headers={"Accept":"application/vnd.opentimestamps.v1",
                     "User-Agent":"Ario-W32-READONLY-PUBLIC-SYNTHETIC/1"},
        method="GET")
    if opener is None:
        opener=urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request,timeout=12) as response:
            code=response.status
            body=response.read(MAX_REMOTE+1)
            media=response.headers.get("Content-Type","")
    except urllib.error.HTTPError as ex:
        if ex.code in (404,202):
            return {"fetch":"PENDING_NOT_UPGRADED","http_status":ex.code,
                    "response_bytes":None,"content_type":None}
        return {"fetch":"HTTP_FAILURE","http_status":ex.code,
                "response_bytes":None,"content_type":None}
    except (OSError,ValueError,urllib.error.URLError) as ex:
        return {"fetch":"NETWORK_OR_PROTOCOL_ERROR","error_class":type(ex).__name__,
                "response_bytes":None}
    if code!=200 or not 0<len(body)<=MAX_REMOTE:
        return {"fetch":"HTTP_OR_SIZE_FAILURE","http_status":code,
                "response_bytes":None,"content_type":media}
    return {"fetch":"HTTP_200_PROOF_BYTES","http_status":200,
            "response_bytes":body,"content_type":media}


def _find_exact_pending_node(stamp, commitment, calendar_url):
    # The root of a detached .ots is the ORIGINAL file digest; the upgraded
    # calendar response attests a derived child commitment reached via OTS
    # operations. Merging into the file-digest root would be incorrect.
    if (stamp.msg == commitment and any(
        isinstance(att,PendingAttestation) and att.uri==calendar_url
        for att in stamp.attestations
    )):
        return stamp
    for child in stamp.ops.values():
        found=_find_exact_pending_node(child,commitment,calendar_url)
        if found is not None:
            return found
    return None


def check_one(calendar_url, commitment, detached, original, *, getter=get_existing_timestamp):
    result={
        "calendar":calendar_url,"commitment_hex":commitment.hex(),
        "commitment_bytes":len(commitment),
        "original_ots_sha256":hashlib.sha256(original).hexdigest(),
        "original_ots_bytes":len(original),
        "no_post_requests":True,"independent_admin":"NOT_ESTABLISHED",
        "independent_bitcoin_consensus_verification":False,
        "actual_ario_log":False,"authority":"NONE",
    }
    response=getter(calendar_url,commitment)
    result["http_status"]=response.get("http_status")
    result["fetch"]=response.get("fetch")
    if response.get("fetch")!="HTTP_200_PROOF_BYTES":
        result["result"]="PENDING_OR_UNAVAILABLE_NO_CONFIRMATION"
        return result
    body=response["response_bytes"]
    result["calendar_reply_sha256"]=hashlib.sha256(body).hexdigest()
    result["calendar_reply_b64"]=base64.b64encode(body).decode("ascii")
    if len(body)>MAX_REMOTE:
        result["result"]="INVALID_REMOTE_PROOF";return result
    try:
        ctx=StreamDeserializationContext(BytesIO(body))
        upgraded=Timestamp.deserialize(ctx,commitment)
        ctx.assert_eof()
        if upgraded.msg!=commitment:raise ValueError("incorrect returned commitment")
        # Only merge into the matching *leaf* (NOT the file hash root).
        pending_leaf=_find_exact_pending_node(detached.timestamp,commitment,calendar_url)
        if pending_leaf is None:
            raise ValueError("unrecognized pending witness branch")
        pending_leaf.merge(upgraded)
        after=_serialize_detached(detached)
        roundtrip=_parse_detached(after)
        if roundtrip.file_digest.hex()!=EXPECTED_DIGEST:
            raise ValueError("digest changed across upgrade")
        attest=list(roundtrip.timestamp.all_attestations())
        btc=[{"height":a.height,"merkle_root_little_endian_hex":msg[::-1].hex()}
             for msg,a in attest if isinstance(a,BitcoinBlockHeaderAttestation)]
        result.update({
            "result":"CALENDAR_BITCOIN_ATTESTATION_UNVERIFIED" if btc else "PROOF_UPDATED_BUT_STILL_PENDING",
            "bitcoin_attestations_claimed_by_calendar":btc,
            "upgraded_ots_sha256":hashlib.sha256(after).hexdigest(),
            "upgraded_ots_bytes":len(after),
            "upgraded_ots_b64":base64.b64encode(after).decode("ascii"),
            "bitcoin_consensus_verified":False
        })
    except (ValueError,TypeError,AssertionError,binascii.Error):
        result["result"]="INVALID_REMOTE_PROOF"
    except Exception as ex:
        # Fail closed without returning to an authoritative state.
        result["result"]="REMOTE_PROOF_PARSE_FAILED"
        result["error_class"]=type(ex).__name__
    return result


def run(*, offline=False):
    sources=originals()
    results=[]
    for host,commitment,detached,raw in sources:
        if offline:
            results.append({
                "calendar":host,"commitment_hex":commitment.hex(),
                "commitment_bytes":len(commitment),
                "original_ots_sha256":hashlib.sha256(raw).hexdigest(),
                "result":"OFFLINE_ORIGINAL_PENDING_VALIDATED",
                "bitcoin_consensus_verified":False,"no_post_requests":True
            })
        else:
            results.append(check_one(host,commitment,detached,raw))
    evidence={
        "schema":"ARIO_W32_READ_ONLY_OTS_UPGRADE_V1",
        "w31_preimage_sha256":EXPECTED_DIGEST,
        "mode":"OFFLINE" if offline else "GET_ONLY_EXISTING_COMMITMENTS",
        "original_receipts":len(sources),
        "calendar_queries":0 if offline else len(sources),
        "calendar_post_requests":0,"new_stamp_submissions":0,
        "actual_ario_memory":False,"external_independent_c2sp_witness":"NOT_ESTABLISHED",
        "blockchain_consensus_verified":False,
        "trust_activation":"NO_GO","genesis":"NO_GO","production":"NO_GO",
        "research_only":True,"results":results
    }
    print("W32_EVIDENCE_JSON="+json.dumps(evidence,sort_keys=True))
    return evidence


def main():
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--offline",action="store_true")
    g.add_argument("--read-only-get",action="store_true")
    args=p.parse_args()
    if args.read_only_get and (os.environ.get("GITHUB_ACTIONS")!="true"
        or os.environ.get("ARIO_W32_READONLY_GET_ALLOW")!="1"):
        raise RuntimeError("NO_GO: read-only GET restricted to disposable opted-in CI")
    run(offline=args.offline)


if __name__=="__main__":
    main()
