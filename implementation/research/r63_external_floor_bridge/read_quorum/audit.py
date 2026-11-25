"""Extracted verification primitives from prior R63 witness audit."""
import base64, hashlib, re
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
LOG = bytes.fromhex('4644af2abd40f4895a003bca350f9d5912ab301a49c77f13e5b6d905c20a5fe6')
H=lambda b:hashlib.sha256(b).digest()
def check(ok, message):
    if not ok: raise ValueError(message)
def verify_sig(key, sig, data):
    Ed25519PublicKey.from_public_bytes(key).verify(sig,data)
def dec(s):
    check(bool(re.fullmatch('0|[1-9][0-9]{0,19}',s)), 'decimal field')
    x=int(s); check(x<2**64,'uint64'); return x
