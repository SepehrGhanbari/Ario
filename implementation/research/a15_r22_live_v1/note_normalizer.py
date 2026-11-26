"""Select the Ed25519 witness note from a checkpoint that may also carry ML-DSA.

The R63 note verifier is intentionally Ed25519-only. Geomys can append a large
post-quantum signature under the same signer label. Do not pass that extra
signature to the Ed25519 parser or silently treat it as verified.
"""
import base64

LOG_SIGNATURE_BYTES = 68
WITNESS_ED25519_BYTES = 76
KNOWN_UNVERIFIED_EXTRA_BYTES = frozenset({2432})


def _line(line):
    parts = line.split(" ", 2)
    if len(parts) != 3 or parts[0] != "—":
        raise ValueError("signature line format")
    signer, encoded = parts[1], parts[2]
    raw = base64.b64decode(encoded, validate=True)
    if base64.b64encode(raw).decode("ascii") != encoded:
        raise ValueError("noncanonical signature base64")
    return signer, raw


def normalize_ed25519_note(raw, witness_name, keys, origin):
    """Return (two-signature normalized note, unverified extra signature lengths).

    Only one log signature (68 decoded bytes) and one pinned witness Ed25519
    signature (76 decoded bytes) are passed to the existing verifier. A
    same-signer 2432-byte extra signature is recorded but NOT verified.
    Unknown extra signers or lengths fail closed.
    """
    if type(raw) is not bytes or not 0 < len(raw) <= 16384:
        raise ValueError("response bounds")
    body, sig_text = raw.decode("utf-8").split("\n\n", 1)
    expected_witness = keys[witness_name].split("+", 1)[0]
    log_lines, witness_lines, extras = [], [], []
    for line in sig_text.splitlines():
        if not line:
            continue
        signer, sig = _line(line)
        if signer == origin and len(sig) == LOG_SIGNATURE_BYTES:
            log_lines.append(line)
        elif signer == expected_witness and len(sig) == WITNESS_ED25519_BYTES:
            witness_lines.append(line)
        elif signer == expected_witness and len(sig) in KNOWN_UNVERIFIED_EXTRA_BYTES:
            extras.append(len(sig))
        else:
            raise ValueError("unknown extra signature identity or format")
    if len(log_lines) != 1 or len(witness_lines) != 1:
        raise ValueError("required Ed25519 signature count")
    normalized = (body + "\n\n" + log_lines[0] + "\n" + witness_lines[0] + "\n").encode("utf-8")
    return normalized, extras
