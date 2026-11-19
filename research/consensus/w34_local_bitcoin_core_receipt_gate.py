#!/usr/bin/env python3
"""W34 — read-only Bitcoin Core RPC acceptance gate for original W31 OTS receipts.

OFFLINE by default. --local-rpc is deliberately manual-only and requires
a *locally available* bitcoin-cli authenticated via Bitcoin Core's own cookie.
No install, sync, wallet creation, key readback, remote RPC, network POST,
or real Ario action. A simulated/substituted RPC is NOT real full-node proof.
No output can grant Genesis, production, signer or memory authority.

Evidence source: exact W32 upgraded OpenTimestamps receipts pinned by Git blob.
W31 is PUBLIC SYNTHETIC ONLY — never infer claims about real Ario events.
"""
from __future__ import annotations
import argparse
import base64
import binascii
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess

from opentimestamps.core.timestamp import DetachedTimestampFile
from opentimestamps.core.serialize import StreamDeserializationContext
from opentimestamps.core.notary import BitcoinBlockHeaderAttestation

SCHEMA="ARIO_W34_CORE_LOCAL_RPC_RESEARCH_V1"
BASE=Path(__file__).resolve().parent
REPO=BASE.parents[1]
OTS_BLOB="5d0a7edc1eb8c80cfc52a6d9f0ed9bc1c5fb9b1c"
DIGEST="2078bc80586d0e4b00afa48eb8dea31ab3d4749b4912c57a897e4d5e2fb436df"
GENESIS="000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
EXPECTED={
    976596:{
        "blockhash":"00000000000000000000a6c168915b99fd83334afdc40023901275ac3064ab2d",
        "ots_sha256":"5968fd87749621f96c42d1763bd41a8d457187cd55380d2e1ca7132a4518ac35",
        "calendar":"https://alice.btc.calendar.opentimestamps.org"
    },
    976598:{
        "blockhash":"00000000000000000000cc5208897fe9ecf9e7ef72cf8b20140599a3d8e0c5b1",
        "ots_sha256":"886a46e7ffe9bc7dcb4d8a118bf98cc1805fa5df7f6002aa1fb15573648dc70a",
        "calendar":"https://bob.btc.calendar.opentimestamps.org"
    },
}
HEX64=re.compile(r"[0-9a-f]{64}\Z")
HEX160=re.compile(r"[0-9a-f]{160}\Z")
MAX_CLI_STDOUT=65536


def verdict(reason, **detail):
    result={
        "status":"HOLD","reason":reason,
        "core_rpc_observation":"NOT_ESTABLISHED",
        "fully_validated_bitcoin_node_independently_attested":False,
        "bitcoin_core_operator_provenance":"NOT_ESTABLISHED",
        "c2sp_external_custody":"NOT_ESTABLISHED",
        "actual_ario_log_witnessed":False,
        "bitcoin_transaction_sent":False,
        "calendar_posts":0,"new_timestamps":0,
        "node_mutations":0,"new_wallet":False,"secrets_exposed":False,
        "genesis":"NO_GO","trust_activation":"NO_GO",
        "production":"NO_GO","memory_admitted":False,
        "signatures_issued":0,"authority":"NONE",
    }
    allowed={"core_rpc_observation","anchor_heights","anchor_hashes",
             "core_bestblockhash","core_height","core_headers",
             "core_pruned","core_chainwork_sha256",
             "ots_merkle_roots","input_digest","input_git_blob",
             "local_rpc_methods_invoked","warnings"}
    if set(detail)-allowed:
        return dict(result,reason="UNEXPECTED_DIAGNOSTIC_FIELD")
    result.update(detail)
    return result


def git_blob_raw(blob):
    if blob!=OTS_BLOB:
        raise ValueError("UNEXPECTED_GIT_BLOB")
    x=subprocess.run(["git","cat-file","blob",blob],
        cwd=str(REPO),capture_output=True,check=True,timeout=10)
    if len(x.stdout)>16384:
        raise ValueError("OVERSIZED_PINNED_EVIDENCE")
    return x.stdout


def _parse_ots(raw):
    ctx=StreamDeserializationContext(BytesIO(raw))
    detached=DetachedTimestampFile.deserialize(ctx)
    ctx.assert_eof()
    return detached


def load_receipt_roots(*, raw_loader=git_blob_raw):
    data=json.loads(raw_loader(OTS_BLOB).decode("utf-8"))
    rows=data.get("results")
    if (data.get("w31_preimage_sha256")!=DIGEST
        or data.get("calendar_posts",data.get("calendar_post_requests"))!=0
        or type(rows) is not list or len(rows)!=2):
        raise ValueError("UNBOUND_PINNED_W32_EVIDENCE")
    out={}
    for item in rows:
        if type(item) is not dict or item.get("result")!="CALENDAR_BITCOIN_ATTESTATION_UNVERIFIED":
            raise ValueError("NO_VERIFIABLE_BITCOIN_ATTESTATION")
        b64=item.get("upgraded_ots_b64")
        if type(b64) is not str or len(b64)>8192:
            raise ValueError("MALFORMED_OTS_BASE64")
        try:
            raw=base64.b64decode(b64,validate=True)
        except (ValueError,binascii.Error):
            raise ValueError("MALFORMED_OTS_BASE64") from None
        if base64.b64encode(raw).decode("ascii")!=b64 or len(raw)>4096:
            raise ValueError("UNSAFE_OR_NONCANONICAL_OTS")
        stamp=_parse_ots(raw)
        if stamp.file_digest.hex()!=DIGEST:
            raise ValueError("OTS_NOT_BOUND_TO_PUBLIC_W31_DIGEST")
        matched=[(value,a) for value,a in stamp.timestamp.all_attestations()
                 if isinstance(a,BitcoinBlockHeaderAttestation)]
        if len(matched)!=1 or len(matched[0][0])!=32:
            raise ValueError("EXPECTED_ONE_EXACT_32B_MERKLE_ROOT")
        root,att=matched[0]
        height=att.height
        if type(height) is not int or height not in EXPECTED or height in out:
            raise ValueError("UNEXPECTED_OR_DUPLICATE_HEIGHT")
        pin=EXPECTED[height]
        if (item.get("calendar")!=pin["calendar"]
            or hashlib.sha256(raw).hexdigest()!=pin["ots_sha256"]
            or item.get("upgraded_ots_sha256")!=pin["ots_sha256"]):
            raise ValueError("OTS_SOURCE_PIN_MISMATCH")
        out[height]={"height":height,"raw_merkle_root":root.hex(),
                     "blockhash":pin["blockhash"],"ots_sha256":pin["ots_sha256"]}
    if set(out)!=set(EXPECTED):
        raise ValueError("INCOMPLETE_OTS_RECEIPTS")
    return out


def check_header(rawhex,expected_hash,expected_merkle):
    if (type(rawhex) is not str or HEX160.fullmatch(rawhex) is None
        or type(expected_hash) is not str or HEX64.fullmatch(expected_hash) is None
        or type(expected_merkle) is not str or HEX64.fullmatch(expected_merkle) is None):
        return False
    raw=bytes.fromhex(rawhex)
    h=hashlib.sha256(hashlib.sha256(raw).digest()).digest()
    bits=int.from_bytes(raw[72:76],"little")
    exp=bits>>24
    mantissa=bits&0xffffff
    if exp<3 or exp>32 or mantissa==0 or mantissa&0x800000:
        return False
    target=mantissa<<(8*(exp-3))
    powlimit=0xffff<<(8*(0x1d-3))
    return (0<target<=powlimit
            and int.from_bytes(h,"little")<=target
            and h[::-1].hex()==expected_hash
            and raw[36:68].hex()==expected_merkle)


def _safe_chain_info(info):
    if type(info) is not dict:
        return False
    blocks=info.get("blocks")
    headers=info.get("headers")
    progress=info.get("verificationprogress")
    chainwork=info.get("chainwork")
    return (
        info.get("chain")=="main"
        and type(blocks) is int and blocks>=976604
        and type(headers) is int and headers>=blocks
        and headers-blocks <= 2
        and info.get("initialblockdownload") is False
        and type(progress) in (int,float) and 0.999 <= progress<=1.0
        and type(info.get("pruned")) is bool
        and type(info.get("bestblockhash")) is str
        and HEX64.fullmatch(info["bestblockhash"]) is not None
        and type(chainwork) is str
        and re.fullmatch(r"[0-9a-fA-F]{1,64}",chainwork) is not None
        and int(chainwork,16)>0
    )


def evaluate(rpc, *, receipts=None):
    """rpc is a CALLER-SUPPLIED adapter. Its source cannot authenticate itself.

    This function **never** grants FULL_NODE_VERIFIED even on perfect-looking
    RPC results. Operator must separately establish actual local Core custody,
    mainnet initial sync and independent provenance before trust claims.
    """
    if receipts is None:
        try:
            receipts=load_receipt_roots()
        except (OSError,ValueError,TypeError,subprocess.CalledProcessError):
            return verdict("INVALID_OR_MISSING_W32_PROOF_INPUT")
    try:
        info=rpc("getblockchaininfo")
    except (OSError,RuntimeError,ValueError,TimeoutError):
        return verdict("CORE_RPC_UNAVAILABLE_OR_UNTRUSTED")
    if not _safe_chain_info(info):
        return verdict("CORE_NOT_SYNCED_MAINNET_OR_BAD_STATUS")
    try:
        if rpc("getblockhash",0)!=GENESIS:
            return verdict("GENESIS_MISMATCH")
        for height in sorted(EXPECTED):
            h=rpc("getblockhash",height)
            entry=receipts.get(height)
            if type(entry) is not dict or h!=entry.get("blockhash") or h!=EXPECTED[height]["blockhash"]:
                return verdict("LOCAL_CORE_BLOCKHASH_MISMATCH")
            header=rpc("getblockheader",h,False)
            if not check_header(header,h,entry["raw_merkle_root"]):
                return verdict("LOCAL_CORE_HEADER_OR_OTS_MERKLE_MISMATCH")
        final=rpc("getblockhash",info["blocks"])
        if final!=info["bestblockhash"]:
            return verdict("CORE_TIP_CHANGED_DURING_REVIEW_RETRY_REQUIRED")
    except (OSError,RuntimeError,ValueError,TypeError,TimeoutError,KeyError,AttributeError):
        return verdict("CORE_RPC_RESPONSE_MALFORMED_OR_UNAVAILABLE")
    return verdict(
        "LOCAL_CORE_RPC_CLAIMS_MATCH_ORIGINAL_OTS_PROOFS_BUT_OPERATOR_UNATTESTED",
        core_rpc_observation="CALLER_RPC_ADAPTER_MATCHES_PINNED_HEADERS",
        core_height=info["blocks"],core_headers=info["headers"],
        core_bestblockhash=info["bestblockhash"],core_pruned=info["pruned"],
        core_chainwork_sha256=hashlib.sha256(info["chainwork"].encode("ascii")).hexdigest(),
        anchor_heights=sorted(EXPECTED),
        anchor_hashes=[EXPECTED[h]["blockhash"] for h in sorted(EXPECTED)],
        ots_merkle_roots=[receipts[h]["raw_merkle_root"] for h in sorted(EXPECTED)],
        input_digest=DIGEST,input_git_blob=OTS_BLOB,
        local_rpc_methods_invoked=[
            "getblockchaininfo","getblockhash(0)",
            "getblockhash(976596)","getblockheader(976596,false)",
            "getblockhash(976598)","getblockheader(976598,false)",
            "getblockhash(best_height)"
        ],
        warnings="RPC source supplied by caller. Local node existence/authenticity cannot be proven by JSON alone."
    )


def local_bitcoin_cli(method,*args):
    """Local read-only CLI. NEVER allow dynamic RPC method or arbitrary flags."""
    methods={
        "getblockchaininfo":0,
        "getblockhash":1,
        "getblockheader":2,
    }
    if method not in methods or len(args)!=methods[method]:
        raise ValueError("UNAPPROVED_BITCOIN_RPC_METHOD")
    if method=="getblockhash" and (
        type(args[0]) is not int or args[0] not in (0,976596,976598)
        and not (976604<=args[0]<=4_000_000)
    ):
        raise ValueError("UNAPPROVED_RPC_BLOCK_HEIGHT")
    if method=="getblockheader" and (
        type(args[0]) is not str or HEX64.fullmatch(args[0]) is None
        or args[1] is not False
    ):
        raise ValueError("UNAPPROVED_HEADER_REQUEST")
    cmd=[
        "bitcoin-cli","-chain=main",
        "-rpcconnect=127.0.0.1","-rpcport=8332",
        "-rpcclienttimeout=10",method,
        *(str(a).lower() if type(a) is bool else str(a) for a in args)
    ]
    try:
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         timeout=15,check=True)
    except (FileNotFoundError,subprocess.CalledProcessError,subprocess.TimeoutExpired):
        raise RuntimeError("LOCAL_BITCOIN_CORE_CLI_NOT_READY") from None
    if len(p.stdout)>MAX_CLI_STDOUT:
        raise ValueError("OVERSIZED_RPC_RESPONSE")
    try:
        text=p.stdout.decode("utf-8").strip()
        return json.loads(text) if method=="getblockchaininfo" else text.strip('"')
    except (UnicodeError,json.JSONDecodeError):
        raise ValueError("MALFORMED_LOCAL_BITCOIN_CLI_OUTPUT") from None


def main():
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline",action="store_true")
    mode.add_argument("--local-rpc",action="store_true")
    args=parser.parse_args()
    try:
        receipts=load_receipt_roots()
        if args.offline:
            output=verdict("VALID_ORIGINAL_PUBLIC_W31_OTS_INPUT_ONLY",
                input_digest=DIGEST,input_git_blob=OTS_BLOB,
                anchor_heights=sorted(EXPECTED),
                ots_merkle_roots=[receipts[h]["raw_merkle_root"] for h in sorted(EXPECTED)])
        else:
            # Explicit manual operator action only. No automatic CI online
            # test and no network except bitcoin-cli to 127.0.0.1.
            output=evaluate(local_bitcoin_cli,receipts=receipts)
    except (OSError,ValueError,TypeError,subprocess.CalledProcessError):
        output=verdict("W34_INPUT_OR_EXECUTION_ERROR_NO_GO")
    print("W34_CORE_EVIDENCE_JSON="+json.dumps(output,sort_keys=True))
    if output["reason"] == "LOCAL_CORE_RPC_CLAIMS_MATCH_ORIGINAL_OTS_PROOFS_BUT_OPERATOR_UNATTESTED":
        # Even perfect-looking caller-supplied RPC is NOT independent Core
        # validation. Exit distinctly nonzero; do not let CI turn this
        # diagnostic agreement into a green verification check.
        raise SystemExit(3)
    if output["reason"] != "VALID_ORIGINAL_PUBLIC_W31_OTS_INPUT_ONLY":
        # Invalid or unavailable node / malformed input is an actual error.
        raise SystemExit(2)


if __name__=="__main__":
    main()
