#!/usr/bin/env python3
"""W33: 5 contiguous mainnet headers surrounding W31 OTS attestations.

Strictly research-only: two public explorers are evidence providers, NOT
full Bitcoin consensus nodes or independently authenticated custodians.
No POST, no secrets, no real Ario events, no signing, no trust activation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parent
W32="W32_TWO_EXPLORER_HEADER_CORROBORATION_2026-11-19.json"
HEIGHTS=tuple(range(976596,976601))
FETCH_HEIGHTS=(976597,976599,976600)
PROVIDERS={"blockstream":"https://blockstream.info/api",
           "mempool":"https://mempool.space/api"}
HEX64=re.compile(r"[0-9a-f]{64}\Z")
HEX160=re.compile(r"[0-9a-f]{160}\Z")
MAX_RESPONSE=256


def result(reason,**extra):
    state={
        "status":"HOLD","reason":reason,
        "header_linkage":"NOT_VERIFIED",
        "public_explorer_corroboration":"NOT_VERIFIED",
        "bitcoin_consensus_full_node":"NOT_ESTABLISHED",
        "explorer_operator_independence":"NOT_ESTABLISHED",
        "independent_c2sp_witness":"NOT_ESTABLISHED",
        "genesis":"NO_GO","trust_activation":"NO_GO","production":"NO_GO",
        "memory_admitted":False,"authority":"NONE",
        "bitcoin_tx_sent":False,"new_timestamp_posts":0,
    }
    state.update(extra)
    return state


def header_info(hex_data):
    if type(hex_data) is not str or HEX160.fullmatch(hex_data) is None:
        raise ValueError("MALFORMED_HEADER")
    b=bytes.fromhex(hex_data)
    digest=hashlib.sha256(hashlib.sha256(b).digest()).digest()
    bits=int.from_bytes(b[72:76],"little")
    mantissa=bits&0xffffff
    exponent=bits>>24
    if mantissa==0 or mantissa&0x800000 or exponent<3 or exponent>32:
        raise ValueError("INVALID_COMPACT_TARGET")
    target=mantissa<<(8*(exponent-3))
    limit=0xffff<<(8*(0x1d-3))
    if target<=0 or target>limit or int.from_bytes(digest,"little")>target:
        raise ValueError("HEADER_POW_INVALID")
    return {
        "hash":digest[::-1].hex(),
        "prev_hash":b[4:36][::-1].hex(),
        "merkle_root_raw":b[36:68].hex(),
        "time":int.from_bytes(b[68:72],"little"),
        "bits":bits,
        "nonce":int.from_bytes(b[76:80],"little"),
        "header_sha256":hashlib.sha256(b).hexdigest(),
    }


def stored_w32():
    obj=json.loads((ROOT/W32).read_text("utf-8"))
    if (obj.get("verified_w31_preimage_sha256") !=
        "2078bc80586d0e4b00afa48eb8dea31ab3d4749b4912c57a897e4d5e2fb436df"
        or type(obj.get("results")) is not list or len(obj["results"])!=2):
        raise ValueError("W32_REFERENCE_NOT_EXACT")
    found={}
    for row in obj["results"]:
        height=row.get("height")
        if type(height) is not int or height not in (976596,976598):
            raise ValueError("UNEXPECTED_W32_HEIGHT")
        checks=row.get("public_api_checks")
        if type(checks) is not list or len(checks)!=2:
            raise ValueError("W32_TWO_PROVIDER_EVIDENCE_REQUIRED")
        if {v.get("provider") for v in checks}!={"blockstream","mempool"}:
            raise ValueError("W32_PROVIDER_IDENTITY_MISMATCH")
        if len({v.get("header_hex") for v in checks})!=1:
            raise ValueError("W32_PROVIDER_DISAGREEMENT")
        h=header_info(checks[0]["header_hex"])
        if (h["hash"]!=checks[0]["derived_block_hash"]
            or h["hash"]!=checks[1]["derived_block_hash"]
            or h["merkle_root_raw"]!=row["proof_merkle_root_raw_hex"]):
            raise ValueError("W32_HEADER_NOT_BOUND_TO_OTS")
        if height in found:
            raise ValueError("W32_DUPLICATE_ANCHOR")
        found[height]={"height":height,"header_hex":checks[0]["header_hex"],
                       "source":"PINNED_W32_TWO_APIS","info":h}
    if set(found)!={976596,976598}:
        raise ValueError("W32_ANCHORS_INCOMPLETE")
    return found


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None


def _read_endpoint(url,opener=None):
    # Accept only exact API prefixes, no path traversal, query or redirects.
    if (type(url) is not str or
        not any(url.startswith(prefix+"/") for prefix in PROVIDERS.values())
        or ".." in url or "?" in url or "#" in url or len(url)>200):
        raise ValueError("NON_ALLOWLISTED_ENDPOINT")
    if opener is None:
        opener=urllib.request.build_opener(NoRedirect())
    request=urllib.request.Request(url,method="GET",headers={
        "Accept":"text/plain","User-Agent":"Ario-W33-FIVE-HEADERS-GET-ONLY/1"})
    try:
        with opener.open(request,timeout=12) as response:
            if response.status!=200:
                return None
            body=response.read(MAX_RESPONSE+1)
        if len(body)>MAX_RESPONSE:
            return None
        return body.decode("ascii").strip().lower()
    except (OSError,UnicodeError,urllib.error.URLError,ValueError):
        return None


def fetch_one(provider,height,reader=_read_endpoint):
    if provider not in PROVIDERS or type(height) is not int or height not in FETCH_HEIGHTS:
        raise ValueError("UNAPPROVED_PROVIDER_OR_HEIGHT")
    base=PROVIDERS[provider]
    blockhash=reader(base+"/block-height/"+str(height))
    if type(blockhash) is not str or HEX64.fullmatch(blockhash) is None:
        return {"provider":provider,"height":height,"status":"BLOCKHASH_UNAVAILABLE"}
    header=reader(base+"/block/"+blockhash+"/header")
    if type(header) is not str or HEX160.fullmatch(header) is None:
        return {"provider":provider,"height":height,"status":"RAW_HEADER_UNAVAILABLE"}
    try:
        info=header_info(header)
    except ValueError as ex:
        return {"provider":provider,"height":height,"status":"INVALID_HEADER",
                "error_code":str(ex)}
    if info["hash"]!=blockhash:
        return {"provider":provider,"height":height,"status":"HEADER_HASH_MISMATCH"}
    return {"provider":provider,"height":height,"status":"HEADER_HASH_POW_PASS",
            "header_hex":header,"info":info}


def validate_five(pinned,new_responses):
    """Validate bounded 5-block linking and PoW, not full Bitcoin consensus."""
    if type(pinned) is not dict or set(pinned)!={976596,976598}:
        return result("ANCHOR_LIST_INCOMPLETE")
    if type(new_responses) is not list or len(new_responses)!=6:
        return result("EXPECTED_SIX_EXTERNAL_HEADER_RESPONSES")
    found={}
    for row in new_responses:
        if type(row) is not dict:
            return result("INVALID_PROVIDER_RESPONSE")
        h=row.get("height")
        p=row.get("provider")
        if type(h) is not int or h not in FETCH_HEIGHTS or p not in PROVIDERS:
            return result("WRONG_HEIGHT_OR_PROVIDER")
        key=(h,p)
        if key in found:
            return result("DUPLICATE_HEIGHT_PROVIDER")
        if row.get("status")!="HEADER_HASH_POW_PASS":
            return result("MISSING_OR_INVALID_PROVIDER_RESULT")
        try:
            info=header_info(row["header_hex"])
        except (KeyError,TypeError,ValueError):
            return result("MALFORMED_HEADER_EVIDENCE")
        if info!=row.get("info"):
            return result("UNTRUSTWORTHY_PARSED_HEADER_METADATA")
        found[key]=row
    if set(found)!={(h,p) for h in FETCH_HEIGHTS for p in PROVIDERS}:
        return result("INCOMPLETE_PROVIDER_PAIR")
    combined=dict(pinned)
    for h in FETCH_HEIGHTS:
        a,b=found[h,"blockstream"],found[h,"mempool"]
        if a["header_hex"]!=b["header_hex"]:
            return result("TWO_EXPLORERS_REPORT_DIFFERENT_BYTES",height=h)
        combined[h]={"height":h,"header_hex":a["header_hex"],
                     "source":"TWO_PUBLIC_API_MATCH","info":a["info"]}
    heads=[combined[h]["info"] for h in HEIGHTS]
    for pos in range(1,len(heads)):
        if heads[pos]["prev_hash"]!=heads[pos-1]["hash"]:
            return result("BROKEN_PREVIOUS_HEADER_LINK",height=HEIGHTS[pos])
    if len({item["bits"] for item in heads})!=1:
        return result("N_BITS_CHANGED_INSIDE_NONRETARGET_WINDOW")
    # These heights are not a 2016-block retarget boundary. Do not silently
    # infer full network target validation from a five-block sample.
    if any(h%2016==0 for h in HEIGHTS):
        return result("DIFFICULTY_RETARGET_BOUNDARY_NOT_VALIDATED")
    return result(
        "BOUNDED_FIVE_HEADER_LINK_AND_TWO_API_POW_PASS",
        header_linkage="FIVE_CONTIGUOUS_HEADERS_LINKED",
        public_explorer_corroboration="TWO_PUBLIC_API_IDENTICAL_FOR_FETCHED_HEIGHTS",
        heights=list(HEIGHTS),
        block_hashes=[item["hash"] for item in heads],
        nbits=heads[0]["bits"],
        no_full_chain_validation=True
    )


def core_gate(snapshot,expected_hashes):
    """A hypothetical caller-provided RPC response must NEVER grant authority.

    Even when fields match, this method cannot prove the node operator, local
    RPC endpoint, synchronization provenance, chain ancestry or full consensus.
    Actual independent OTS verification requires trustworthy Bitcoin Core.
    """
    if (type(snapshot) is not dict or
        set(snapshot)!={"chain","blocks","headers","initialblockdownload",
                        "verificationprogress","hash_at_976596","hash_at_976598"}):
        return result("CORE_RPC_SNAPSHOT_MALFORMED")
    if (snapshot["chain"]!="main"
        or type(snapshot["blocks"]) is not int or snapshot["blocks"]<976600
        or type(snapshot["headers"]) is not int or snapshot["headers"]<snapshot["blocks"]
        or snapshot["initialblockdownload"] is not False
        or type(snapshot["verificationprogress"]) not in (int,float)
        or not 0.999 <= snapshot["verificationprogress"]<=1.0):
        return result("CORE_RPC_SYNC_OR_CHAIN_NOT_ESTABLISHED")
    if (type(expected_hashes) is not dict or
        set(expected_hashes)!={976596,976598}
        or snapshot["hash_at_976596"]!=expected_hashes[976596]
        or snapshot["hash_at_976598"]!=expected_hashes[976598]):
        return result("CORE_RPC_CHECKPOINT_HASH_MISMATCH")
    return result("CORE_RPC_FIELDS_MATCH_ONLY_UNAUTHENTICATED",
                  rpc_snapshot_fields="CONSISTENT_WITH_EXPECTED_HEADERS",
                  full_node_verification="NOT_ESTABLISHED_BY_CALLER_SUPPLIED_JSON")


def run(online=False):
    old=stored_w32()
    fresh=[] if not online else [fetch_one(p,h)
                                 for h in FETCH_HEIGHTS for p in PROVIDERS]
    outcome=(result("OFFLINE_PINS_ONLY_NO_CHAIN_VERIFICATION")
             if not online else validate_five(old,fresh))
    obj={
        "schema":"ARIO_W33_FIVE_HEADER_CHAIN_RESEARCH_V1",
        "mode":"GET_ONLY_2_PUBLIC_APIS" if online else "OFFLINE_ZERO_NETWORK",
        "cached_w32_anchor_heights":[976596,976598],
        "fetched_heights":list(FETCH_HEIGHTS) if online else [],
        "raw_provider_observations":fresh,
        "verdict":outcome,
        "get_requests_max":12 if online else 0,
        "http_posts":0,"real_ario_data":False,
        "full_node_bitcoin_core_rpc_used":False,
        "full_consensus_verified":False,
        "research_only":True,
    }
    print("W33_CHAIN_EVIDENCE_JSON="+json.dumps(obj,sort_keys=True))
    return obj


def main():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--offline",action="store_true")
    group.add_argument("--read-only-get",action="store_true")
    args=parser.parse_args()
    if args.read_only_get and (os.environ.get("GITHUB_ACTIONS")!="true"
                               or os.environ.get("ARIO_W33_READONLY_ALLOW")!="1"):
        raise RuntimeError("NO_GO: opt-in GET confined to disposable GitHub Actions")
    run(online=args.read_only_get)


if __name__=="__main__":
    main()
