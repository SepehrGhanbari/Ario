"""Bounded read-only OpenTimestamps pending response parser. No Bitcoin verification."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass

PENDING_TAG=bytes.fromhex("83dfe30d2ef90c8e")
ALLOWED_URI="https://alice.btc.calendar.opentimestamps.org"

class InvalidPendingProof(ValueError):pass

@dataclass(frozen=True)
class PendingProof:
    uri:str
    ops:tuple[str,...]
    commitment_hex:str

def _varint(buf:bytes,i:int)->tuple[int,int]:
    v=0
    for shift in range(0,63,7):
        if i>=len(buf):raise InvalidPendingProof("TRUNCATED_VARINT")
        b=buf[i];i+=1;v|=(b&127)<<shift
        if b<128:return v,i
    raise InvalidPendingProof("OVERSIZED_VARINT")

def parse_pending(raw:bytes,initial_digest:bytes,allowed_uri:str=ALLOWED_URI)->PendingProof:
    if type(raw) is not bytes or len(raw)>8192 or len(raw)<12:
        raise InvalidPendingProof("INVALID_SIZE")
    if type(initial_digest) is not bytes or len(initial_digest)!=32:
        raise InvalidPendingProof("INVALID_DIGEST")
    if not allowed_uri.startswith("https://"):
        raise InvalidPendingProof("INVALID_ALLOWLIST")
    head=initial_digest;i=0;ops=[]
    while i<len(raw):
        kind=raw[i];i+=1
        if kind==0x08:
            head=hashlib.sha256(head).digest();ops.append("SHA256")
        elif kind in (0xf0,0xf1):
            n,i=_varint(raw,i)
            if not 1<=n<=256 or i+n>len(raw):
                raise InvalidPendingProof("MALFORMED_DATA_OP")
            val=raw[i:i+n];i+=n
            head=head+val if kind==0xf0 else val+head
            ops.append(("APPEND" if kind==0xf0 else "PREPEND")+f"({n})")
        elif kind==0x00:
            if i+8>len(raw):raise InvalidPendingProof("TRUNCATED_ATTESTATION_TAG")
            tag=raw[i:i+8];i+=8
            if tag!=PENDING_TAG:raise InvalidPendingProof("UNEXPECTED_ATTESTATION_TAG")
            n,i=_varint(raw,i)
            if not 1<=n<=256 or i+n!=len(raw):
                raise InvalidPendingProof("MALFORMED_CALENDAR_URI")
            try:uri=raw[i:i+n].decode("utf8","strict")
            except UnicodeError as exc:raise InvalidPendingProof("INVALID_URI_UTF8") from exc
            if uri!=allowed_uri:
                raise InvalidPendingProof("PENDING_URI_NOT_EXACT_ALLOWLIST_MATCH:"+repr(uri))
            return PendingProof(uri,tuple(ops),head.hex())
        else:raise InvalidPendingProof(f"UNSUPPORTED_OP_{kind:02x}")
    raise InvalidPendingProof("MISSING_FINAL_ATTESTATION")
