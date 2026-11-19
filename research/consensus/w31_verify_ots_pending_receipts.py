#!/usr/bin/env python3
"""W31 parser-only validation of public OTS calendar pending responses.

Read-only: no network, no keys, no stamping, no trust, no Bitcoin claims.
Requires opentimestamps==0.5.0 (official Python proof-format library).
"""
from __future__ import annotations
import base64
import hashlib
from io import BytesIO
import json
from pathlib import Path

from opentimestamps.core.timestamp import Timestamp, DetachedTimestampFile
from opentimestamps.core.serialize import (
    StreamDeserializationContext, StreamSerializationContext
)
from opentimestamps.core.op import OpSHA256
from opentimestamps.core.notary import PendingAttestation, BitcoinBlockHeaderAttestation

ROOT=Path(__file__).resolve().parent
MANIFEST="W31_PUBLIC_SYNTHETIC_TIMESTAMP_PREIMAGE_2026-11-19.json"
EVIDENCE="W31_OTS_TWO_CALENDAR_PENDING_RECEIPTS_2026-11-19.json"
EXPECT={
    "https://alice.btc.calendar.opentimestamps.org",
    "https://bob.btc.calendar.opentimestamps.org",
}


def validate():
    manifest=(ROOT/MANIFEST).read_bytes()
    digest=hashlib.sha256(manifest).digest()
    data=json.loads((ROOT/EVIDENCE).read_text("utf-8"))
    assert data["preimage_sha256"]==digest.hex()
    assert data["preimage_bytes"]==len(manifest)==765
    assert data["confirmed_200_responses"]==2
    assert {r["calendar_url"] for r in data["calendar_results"]}==EXPECT
    checks=[]
    for receipt in data["calendar_results"]:
        raw=base64.b64decode(receipt["pending_proof_b64"],validate=True)
        assert receipt["http_status"]==200
        assert receipt["status"]=="HTTP_200_PENDING_RESPONSE_UNVALIDATED"
        assert receipt["proof_bytes"]==len(raw)>0
        assert receipt["response_content_type"]=="application/vnd.opentimestamps.v1"
        assert receipt["pending_proof_sha256"]==hashlib.sha256(raw).hexdigest()
        # Raw POST /digest response is an OTS Timestamp, NOT a detached .ots file.
        stream=StreamDeserializationContext(BytesIO(raw))
        pending=Timestamp.deserialize(stream,digest)
        stream.assert_eof()
        assert pending.msg==digest
        att=list(pending.all_attestations())
        urls=[a.uri for _,a in att if isinstance(a,PendingAttestation)]
        assert receipt["calendar_url"] in urls, (receipt["calendar_url"],urls)
        confirmations=[a for _,a in att if isinstance(a,BitcoinBlockHeaderAttestation)]
        assert len(confirmations)==0, "No unexpected Bitcoin confirmation claim"
        detached=DetachedTimestampFile(OpSHA256(),pending)
        output=BytesIO()
        detached.serialize(StreamSerializationContext(output))
        ots=output.getvalue()
        ctx=StreamDeserializationContext(BytesIO(ots))
        roundtrip=DetachedTimestampFile.deserialize(ctx)
        assert roundtrip.file_digest==digest
        ctx.assert_eof()
        checks.append({
            "calendar":receipt["calendar_url"],
            "raw_calendar_timestamp_bytes":len(raw),
            "pending_uri_matches_calendar":True,
            "pending_attestations":len(urls),
            "bitcoin_attestations":0,
            "detached_ots_bytes":len(ots),
            "detached_ots_sha256":hashlib.sha256(ots).hexdigest(),
            "detached_ots_b64":base64.b64encode(ots).decode("ascii"),
            "offline_verify": "VALID_PENDING_TIMESTAMP_FORMAT_ONLY",
        })
    summary={
        "schema":"ARIO_W31_OFFLINE_OTS_FORMAT_VERIFICATION_V1",
        "preimage_sha256":digest.hex(),
        "result":"2_OF_2_PARSABLE_PENDING_RECEIPTS",
        "verified_bitcoin_anchor":False,
        "independent_c2sp_keeper":"NOT_ESTABLISHED",
        "external_operator_key_pin":"NOT_ESTABLISHED",
        "trust_activation":"NO_GO","production":"NO_GO",
        "external_post_requests_in_this_verification":0,
        "checks":checks,
    }
    print("W31_PROOFS_PARSED_JSON="+json.dumps(summary,sort_keys=True))
    return summary


if __name__=="__main__":
    validate()
