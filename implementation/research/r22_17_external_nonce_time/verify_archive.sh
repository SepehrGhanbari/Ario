#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C TZ=UTC
mkdir -p empty-ca
export SSL_CERT_DIR="$PWD/empty-ca" SSL_CERT_FILE="$PWD/ca.pem"
sha256sum -c <<'PINS'
2151b61137ffa86bf664691ba67e7da0b19f98c758e3d228d5d8ebf27e044438  ca.download
8bfb0305bb64e2571ca507552ef3245cb1c2fee8728e0ff8689225081ea13467  tsa.download
PINS
cmp ca.download ca.pem
cmp tsa.download tsa.pem
for x in a b; do
 openssl ts -reply -in "$x.tsr" -token_out -out "$x.token.der"
 openssl cms -verify -binary -inform DER -in "$x.token.der" -noverify -nointern -certfile tsa.pem -out "$x.tstinfo.der"
done
verify() { openssl ts -verify -in "$1.tsr" -queryfile "$2.tsq" -CAfile ca.pem -CApath empty-ca -untrusted tsa.pem "${@:3}"; }
positive() { local name="$1"; shift; "$@" > "$name.check.txt" 2>&1; grep -F 'Verification: OK' "$name.check.txt"; echo "$name PASS"; }
negative() { local name="$1" expect="$2"; shift 2; if "$@" > "$name.check.txt" 2>&1; then echo "$name UNEXPECTED_ACCEPT"; return 1; fi; grep -Ei "$expect" "$name.check.txt"; echo "$name REJECTED PASS"; }
positive a_matches_a verify a a
positive b_matches_b verify b b
negative a_replayed_to_b 'nonce.*mismatch' verify a b
negative b_replayed_to_a 'nonce.*mismatch' verify b a
positive a_with_rolled_back_request_RED verify a a
positive data_only_RED openssl ts -verify -in a.tsr -data synthetic.txt -CAfile ca.pem -CApath empty-ca -untrusted tsa.pem
printf '%s\n' 'DIFFERENT SYNTHETIC IMPRINT' > other.txt
negative wrong_imprint 'message imprint mismatch' openssl ts -verify -in a.tsr -data other.txt -CAfile ca.pem -CApath empty-ca -untrusted tsa.pem
epoch="$(date -u -d '2026-11-24 00:00:00 UTC' +%s)"
positive fixed_validation_epoch verify b b -attime "$epoch"
negative replay_fixed_validation_epoch 'nonce.*mismatch' verify a b -attime "$epoch"
negative pre_validity_epoch 'not yet valid|certificate verify error' verify b b -attime 1
python3 - <<'PY'
from pathlib import Path
p=Path('a.tsr'); d=bytearray(p.read_bytes()); d[-1]^=1; Path('tampered.tsr').write_bytes(d)
PY
negative tampered_response 'verification|error|signature' verify tampered a
echo '11/11 EXPECTED CASES PASS; RESPONSE_BINDING_ONLY; REQUEST_ROLLBACK=RED; CLOCK_PROVENANCE=UNKNOWN; REVOCATION=NOT_CHECKED; GLOBAL_LATEST=UNKNOWN; TRUST=NO_GO; PRODUCTION=NO_GO'
