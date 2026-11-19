#!/usr/bin/env python3
"""W32 external header corroboration for original W31 public synthetic digest.

Read-only GET from two public Bitcoin block-explorer APIs; NO Bitcoin node, NO
independent consensus attestation, NO production/security authority. Checks
exact W32 upgraded .ots proof bytes, OTS Merkle-root attestation and raw
80-byte Bitcoin header hash + Proof-of-Work target. Does not validate the
entire Bitcoin header chain or difficulty/retarget rules.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

from opentimestamps.core.timestamp import DetachedTimestampFile
from opentimestamps.core.serialize import StreamDeserializationContext
from opentimestamps.core.notary import BitcoinBlockHeaderAttestation

ROOT=Path(__file__).resolve().parent
W32_FILE="W32_TWO_READONLY_UPGRADED_OTS_RECEIPTS_2026-11-19.json"
DIGEST="2078bc80586d0e4b00afa48eb8dea31ab3d4749b4912c57a897e4d5e2fb436df"
HEIGHTS=frozenset((976596,976598))
APIS={
    "blockstream":"https://blockstream.info/api",
    "mempool":"https://mempool.space/api"
}
HEX=re.compile(r"[0-9a-f]+\Z")
MAX_HTTP=1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def hash_header(raw):
    if type(raw) is not bytes or len(raw)!=80:
        raise ValueError("BLOCK_HEADER_NOT_80_BYTES")
    return hashlib.sha256(hashlib.sha256(raw).digest()).digest()[::-1].hex()


def pow_valid(raw):
    if type(raw) is not bytes or len(raw)!=80:
        return False
    bits=int.from_bytes(raw[72:76],"little")
    exp,mantissa=bits>>24,bits&0xffffff
    if exp==0 or mantissa==0 or mantissa & 0x800000 or exp>32:
        return False
    target=(mantissa<<(8*(exp-3))) if exp>=3 else mantissa>>(8*(3-exp))
    # Bitcoin mainnet powLimit for SHA256d mining: 0x1d00ffff
    limit=0xffff<<(8*(0x1d-3))
    return 0<target<=limit and int.from_bytes(
        hashlib.sha256(hashlib.sha256(raw).digest()).digest(),"little"
    )<=target


def get_plain_text(url,*,opener=None):
    if (type(url) is not str or not any(url.startswith(base+"/") for base in APIS.values())
        or ".." in url or "?" in url or "#" in url or len(url)>250):
        raise ValueError("NOT_AN_ALLOWLISTED_EXPLORER_READ")
    if opener is None:opener=urllib.request.build_opener(NoRedirect())
    req=urllib.request.Request(url,headers={"Accept":"text/plain",
        "User-Agent":"Ario-W32-BITCOIN-HEADER-READONLY-PUBLIC-RESEARCH/1"},
        method="GET")
    try:
        with opener.open(req,timeout=10) as response:
            if response.status!=200:
                return None
            raw=response.read(MAX_HTTP+1)
        if len(raw)>MAX_HTTP:
            return None
        return raw.decode("ascii").strip().lower()
    except (OSError,UnicodeError,urllib.error.URLError,ValueError):
        return None


def explorer_header(provider,height,getter=get_plain_text):
    if provider not in APIS or type(height) is not int or height not in HEIGHTS:
        raise ValueError("INVALID_PINNED_BITCOIN_HEIGHT_OR_PROVIDER")
    base=APIS[provider]
    observed=getter(base+"/block-height/"+str(height))
    if type(observed) is not str or len(observed)!=64 or not HEX.fullmatch(observed):
        return {"provider":provider,"status":"HEIGHT_LOOKUP_UNAVAILABLE"}
    hdr=getter(base+"/block/"+observed+"/header")
    if type(hdr) is not str or len(hdr)!=160 or not HEX.fullmatch(hdr):
        return {"provider":provider,"status":"HEADER_UNAVAILABLE_OR_MALFORMED"}
    raw=bytes.fromhex(hdr)
    sha=hash_header(raw)
    power=pow_valid(raw)
    return {"provider":provider,
        "status":"RAW_HEADER_HASH_AND_POW_MATCHED" if sha==observed and power else "INVALID_HEADER_HASH_OR_POW",
        "reported_block_hash":observed,"derived_block_hash":sha,
        "header_hex":hdr,
        "header_sha256":hashlib.sha256(raw).hexdigest(),
        "merkle_root_raw_hex":raw[36:68].hex(),
        "header_unix_time":int.from_bytes(raw[68:72],"little"),
        "header_bits_hex":raw[72:76][::-1].hex(),
        "pow_target_satisfied":power}


def saved_proof_views():
    data=json.loads((ROOT/W32_FILE).read_text("utf-8"))
    if (data.get("w31_preimage_sha256")!=DIGEST
        or data.get("calendar_post_requests")!=0
        or type(data.get("results")) is not list or len(data["results"])!=2):
        raise ValueError("INVALID_OR_UNBOUND_W32_UPGRADE_EVIDENCE")
    views=[]
    for record in data["results"]:
        if (type(record) is not dict or
            record.get("result")!="CALENDAR_BITCOIN_ATTESTATION_UNVERIFIED"):
            raise ValueError("UNVERIFIED_OR_MISSING_UPGRADED_OTS")
        raw=base64.b64decode(record["upgraded_ots_b64"],validate=True)
        if hashlib.sha256(raw).hexdigest()!=record["upgraded_ots_sha256"]:
            raise ValueError("UPGRADED_OTS_BYTES_SHA256_MISMATCH")
        stream=StreamDeserializationContext(BytesIO(raw))
        detached=DetachedTimestampFile.deserialize(stream)
        stream.assert_eof()
        if detached.file_digest.hex()!=DIGEST:
            raise ValueError("UPGRADED_OTS_WRONG_ORIGINAL_DIGEST")
        att=[(msg,a) for msg,a in detached.timestamp.all_attestations()
             if isinstance(a,BitcoinBlockHeaderAttestation)]
        if len(att)!=1 or att[0][1].height not in HEIGHTS or len(att[0][0])!=32:
            raise ValueError("UNEXPECTED_BITCOIN_ATTESTATIONS")
        claimed=record["bitcoin_attestations_claimed_by_calendar"]
        if len(claimed)!=1 or claimed[0]["height"]!=att[0][1].height:
            raise ValueError("BITCOIN_HEIGHT_CLAIM_MISMATCH")
        views.append({"calendar":record["calendar"],
            "height":att[0][1].height,
            "proof_merkle_root_raw_hex":att[0][0].hex(),
            "upgraded_ots_sha256":record["upgraded_ots_sha256"]})
    if {view["height"] for view in views}!=HEIGHTS:
        raise ValueError("EXPECTED_TWO_DISTINCT_PINNED_BLOCKS")
    return views


def run(*,offline=False,getter=get_plain_text):
    views=saved_proof_views()
    results=[]
    for view in views:
        checks=[] if offline else [
            explorer_header(provider,view["height"],getter=getter)
            for provider in APIS
        ]
        good=(len(checks)==2 and all(
            c.get("status")=="RAW_HEADER_HASH_AND_POW_MATCHED"
            and c.get("merkle_root_raw_hex")==view["proof_merkle_root_raw_hex"]
            for c in checks)
            and checks[0]["header_hex"]==checks[1]["header_hex"]
            and checks[0]["derived_block_hash"]==checks[1]["derived_block_hash"]
        )
        results.append({**view,"public_api_checks":checks,
            "result":"TWO_PUBLIC_APIS_HEADER_AND_OTS_MERKLE_MATCH" if good
                else "OFFLINE_NO_EXTERNAL_HEADERS" if offline else "NOT_CORROBORATED_OR_MISSING_PROVIDER",
            "bitcoin_consensus_verified_by_own_node":False,
            "no_claim_of_operator_independence":True})
    summary={
        "schema":"ARIO_W32_EXTERNAL_BITCOIN_HEADER_CORROBORATION_V1",
        "verified_w31_preimage_sha256":DIGEST,
        "mode":"OFFLINE" if offline else "PUBLIC_HEADER_GET_ONLY",
        "bitcoin_node_connected":False,
        "explorer_operators_independently_authenticated":False,
        "full_bitcoin_header_chain_validated":False,
        "public_explorer_gets":0 if offline else 8,
        "calendar_posts":0,"new_timestamp_submissions":0,
        "trust_activation":"NO_GO","genesis":"NO_GO","production":"NO_GO",
        "research_only":True,
        "results":results,
    }
    print("W32_HEADER_EVIDENCE_JSON="+json.dumps(summary,sort_keys=True))
    return summary


def main():
    p=argparse.ArgumentParser()
    modes=p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline",action="store_true")
    modes.add_argument("--read-only-explorer-get",action="store_true")
    args=p.parse_args()
    if args.read_only_explorer_get and (os.environ.get("GITHUB_ACTIONS")!="true"
        or os.environ.get("ARIO_W32_HEADER_READONLY_ALLOW")!="1"):
        raise RuntimeError("NO_GO: external headers only on disposable explicit GitHub CI")
    run(offline=args.offline)


if __name__=="__main__":
    main()
