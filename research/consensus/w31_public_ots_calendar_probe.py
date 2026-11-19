#!/usr/bin/env python3
"""W31 one-shot REAL calendar experiment with ONE PUBLIC synthetic digest.

Never submit real Ario memory, a key, or a user file. Only the SHA-256 digest
of the committed public W31 preimage is transmitted to two allowlisted
OpenTimestamps calendars. A reply is only a PENDING calendar commitment,
NOT Bitcoin confirmation, C2SP cosignature, independent operator proof,
or authorization to activate any trust.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import ssl

PREIMAGE = "W31_PUBLIC_SYNTHETIC_TIMESTAMP_PREIMAGE_2026-11-19.json"
HOSTS = (
    "alice.btc.calendar.opentimestamps.org",
    "bob.btc.calendar.opentimestamps.org",
)
MEDIA_TYPE = "application/vnd.opentimestamps.v1"


def preimage_digest():
    path = Path(__file__).resolve().parent / PREIMAGE
    raw = path.read_bytes()
    if not 100 <= len(raw) <= 4096:
        raise ValueError("NO_GO: bounded public preimage size")
    payload = json.loads(raw)
    if (type(payload) is not dict
        or payload.get("schema") != "ARIO_W31_EXTERNAL_TIMESTAMP_PUBLIC_SYNTHETIC_V1"
        or payload.get("no_personal_data") is not True
        or payload.get("no_actual_ario_log") is not True
        or payload.get("no_witness_cosignature") is not True
        or payload.get("genesis") != "NO_GO"
        or payload.get("trust_activation") != "NO_GO"
        or payload.get("production") != "NO_GO"):
        raise ValueError("NO_GO: preimage safety fields changed")
    return hashlib.sha256(raw).digest(), len(raw)


def calendar_post(host, digest):
    if host not in HOSTS or type(digest) is not bytes or len(digest) != 32:
        raise ValueError("NO_GO: only two allowlisted endpoints and 32 raw bytes")
    connection = http.client.HTTPSConnection(host, timeout=15, context=ssl.create_default_context())
    try:
        # No Authorization headers, cookies, redirect-following or file upload.
        connection.request(
            "POST", "/digest", body=digest,
            headers={"Accept": MEDIA_TYPE, "User-Agent":"Ario-W31-Public-Synthetic-Research/1.0"}
        )
        response = connection.getresponse()
        body = response.read(16385)
        if len(body)>16384:
            raise ValueError("NO_GO: oversized calendar proof response")
        media = response.getheader("Content-Type", "")
        return {
            "calendar_url": "https://" + host,
            "http_status": response.status,
            "response_content_type": media,
            "proof_bytes": len(body),
            "pending_proof_sha256": hashlib.sha256(body).hexdigest(),
            "pending_proof_b64": base64.b64encode(body).decode("ascii"),
            "is_pending_not_bitcoin_verified": True,
            "c2sp_witness_cosignature": False,
            "independent_administration": "NOT_ESTABLISHED",
            "status": "HTTP_200_PENDING_RESPONSE_UNVALIDATED" if response.status == 200 and body else "REJECTED_OR_EMPTY"
        }
    finally:
        connection.close()


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--submit", action="store_true")
    args=parser.parse_args()
    if args.dry_run == args.submit:
        parser.error("choose exactly one mode")
    digest,length=preimage_digest()
    common = {
        "schema": "ARIO_W31_EXTERNAL_OTS_EXPERIMENT_EVIDENCE_V1",
        "synthetic_public_preimage": PREIMAGE, "preimage_bytes": length,
        "preimage_sha256": digest.hex(),
        "submitted_data": "RAW_SHA256_DIGEST_ONLY_32_BYTES",
        "actual_ario_log": False, "source_truth": "UNKNOWN",
        "externally_retained_c2sp_witness": "NOT_ESTABLISHED",
        "btc_anchor_confirmed": False, "trust_activation": "NO_GO",
        "production": "NO_GO", "genesis": "NO_GO",
        "external_public_irreversible_submission": bool(args.submit),
    }
    if args.dry_run:
        common["mode"]="DRY_RUN_NO_NETWORK"
        print("W31_EVIDENCE_JSON=" + json.dumps(common,sort_keys=True))
        return
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("ARIO_W31_ONE_SHOT_SYNTHETIC_ALLOWED") != "1":
        raise RuntimeError("NO_GO: submit allowed only on explicitly opted-in disposable GitHub-hosted runner")
    responses=[]
    for host in HOSTS:
        try:
            responses.append(calendar_post(host,digest))
        except (OSError,ValueError,http.client.HTTPException) as exc:
            responses.append({"calendar_url":"https://"+host,"status":"FAILED_NO_PROOF",
                              "error_class":type(exc).__name__,
                              "independent_administration":"NOT_ESTABLISHED"})
    common["mode"]="EXPLICIT_ONE_SHOT_PUBLIC_SYNTHETIC_SUBMISSION"
    common["calendar_results"]=responses
    common["confirmed_200_responses"]=sum(
        x.get("status")=="HTTP_200_PENDING_RESPONSE_UNVALIDATED" for x in responses
    )
    print("W31_EVIDENCE_JSON="+json.dumps(common,sort_keys=True))
    # Receipt existence claims need 2 successful responses; partial results
    # must still be preserved in GitHub logs, never relabeled as success.
    if common["confirmed_200_responses"] < 2:
        raise RuntimeError("W31_PARTIAL_OR_FAILED_CALENDAR_POST: see W31_EVIDENCE_JSON; no automatic retry")


if __name__=="__main__":
    run()
