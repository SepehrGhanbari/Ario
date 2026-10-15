"""Reproduce OFFLINE PUBLIC test vectors; NEVER use the RFC seed as a real key."""
from __future__ import annotations
import json
from hashlib import sha256
from pathlib import Path
from test_w4b_profile_lab import (
    RFC8032_TEST_ONLY_SEED, RFC8032_EXPECTED_PUBLIC,
    RFC8032_EMPTY_SIGNATURE, TEST_PAYLOAD,
    attestation, private_test_key,
)
import w4b_profile_lab as lab


def main() -> None:
    a=attestation()
    canonical=lab.canonical_attestation(a)
    signed=lab.bytes_to_sign(a)
    sig=private_test_key().sign(signed)
    wire=lab.encode_wire(a,sig)
    outcome=lab.inspect(wire,lambda:TEST_PAYLOAD,{lab.public_key_id(RFC8032_EXPECTED_PUBLIC):RFC8032_EXPECTED_PUBLIC},
                        __import__('test_w4b_profile_lab').context(a))
    assert outcome.test_signature_check == 'VALID_UNDER_INJECTED_TEST_KEY'
    doc={
        'notice':'PUBLIC RFC8032 TEST-ONLY seed; DO NOT IMPORT, ENROLL, OR REUSE AS A REAL CREDENTIAL',
        'algorithm':'Ed25519 TEST ONLY',
        'profile':lab.PROFILE,
        'encoding':'narrow ASCII-token canonical JSON with ASCII sorted keys, no whitespace; NOT RFC8785 JCS',
        'domain_ascii_repr':repr(lab.DOMAIN),
        'domain_hex':lab.DOMAIN.hex(),
        'test_private_seed_hex_PUBLISHED_NOT_SECRET':RFC8032_TEST_ONLY_SEED.hex(),
        'test_public_key_hex':RFC8032_EXPECTED_PUBLIC.hex(),
        'rfc8032_empty_message_sig_hex':RFC8032_EMPTY_SIGNATURE.hex(),
        'test_key_id':lab.public_key_id(RFC8032_EXPECTED_PUBLIC),
        'synthetic_payload_utf8_hex':TEST_PAYLOAD.hex(),
        'synthetic_payload_sha256':sha256(TEST_PAYLOAD).hexdigest(),
        'attestation':a,
        'canonical_attestation_utf8_hex':canonical.hex(),
        'signed_message_hex':signed.hex(),
        'test_signature_hex':sig.hex(),
        'wire_message_utf8_hex':wire.hex(),
        'expected_outcome':outcome.__dict__,
        'warning':'No real source authentication, trusted enrollment, grant, event truth, or admission.'
    }
    out=Path(__file__).with_name('W4B_TEST_VECTORS.json')
    out.write_text(json.dumps(doc,indent=2,ensure_ascii=True,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    print(out.name, len(wire),len(signed),sha256(wire).hexdigest())

if __name__=='__main__':main()
