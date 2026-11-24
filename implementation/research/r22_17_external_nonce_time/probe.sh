#!/usr/bin/env bash
# Bounded RFC3161 public synthetic experiment. No authority, no private data or keys.
set -euo pipefail
umask 077
export LC_ALL=C TZ=UTC
test "$#" = 1
mkdir -p "$1"
cd "$1"
exec > >(tee results.log) 2>&1
trap 'echo "HOLD: experiment incomplete (line $LINENO); no authority"' ERR
openssl version
fetch() {
  curl --proto '=https' --tlsv1.2 --fail --silent --show-error --connect-timeout 8 --max-time 20 --max-filesize 65536 "$@"
}
# Pins published by provider, captured before this run. Same-provider provenance, not independent enrollment.
fetch https://freetsa.org/files/cacert.pem -o ca.download
fetch https://freetsa.org/files/tsa.crt -o tsa.download
pin() {
  local file="$1" expected="$2" out="$3" raw der
  raw="$(sha256sum "$file" | cut -d' ' -f1)"
  openssl x509 -in "$file" -out "$out"
  der="$(openssl x509 -in "$out" -outform DER | sha256sum | cut -d' ' -f1)"
  if [[ "$raw" = "$expected" ]]; then echo "PIN_FILE_MATCH $file $raw"
  elif [[ "$der" = "$expected" ]]; then echo "PIN_DER_MATCH $file $der"
  else echo "HOLD_PIN_MISMATCH $file raw=$raw der=$der"; return 1; fi
}
pin ca.download 2151b61137ffa86bf664691ba67e7da0b19f98c758e3d228d5d8ebf27e044438 ca.pem
pin tsa.download 8bfb0305bb64e2571ca507552ef3245cb1c2fee8728e0ff8689225081ea13467 tsa.pem
# Same fixed synthetic imprint isolates nonce matching. No user/project record is sent.
printf '%s\n' 'ARIO-R22.17-PUBLIC-SYNTHETIC-NONCE-TEST-v1' > synthetic.txt
openssl ts -query -sha256 -data synthetic.txt -cert -out a.tsq
openssl ts -query -sha256 -data synthetic.txt -cert -out b.tsq
for x in a b; do
  openssl ts -query -in "$x.tsq" -text > "$x.query.txt"
done
nonce() { awk '/^Nonce:/ { print $2 }' "$1"; }
na="$(nonce a.query.txt)"; nb="$(nonce b.query.txt)"
[[ "$na" =~ ^0x[0-9A-Fa-f]+$ && "$nb" =~ ^0x[0-9A-Fa-f]+$ && "$na" != "$nb" ]]
echo "DISTINCT_REQUEST_NONCES $na $nb"
for x in a b; do
  fetch -H 'Content-Type: application/timestamp-query' -H 'Accept: application/timestamp-reply' --data-binary "@$x.tsq" https://freetsa.org/tsr -o "$x.tsr"
  test "$(wc -c < "$x.tsr")" -le 65536
  openssl ts -reply -in "$x.tsr" -text > "$x.response.txt"
  grep -E '^(Status:|Time stamp:|Nonce:|Policy OID:|Serial number:)' "$x.response.txt"
  test "$(nonce "$x.response.txt")" = "$(nonce "$x.query.txt")"
  openssl ts -reply -in "$x.tsr" -token_out -out "$x.token.der"
  # Additional pinned signer check. -noverify here skips only duplicate chain validation;
  # mandatory full chain / purpose / nonce validation follows, so this alone never passes.
  openssl cms -verify -binary -inform DER -in "$x.token.der" -noverify -nointern -certfile tsa.pem -out "$x.tstinfo.der"
done
verify() { openssl ts -verify -in "$1.tsr" -queryfile "$2.tsq" -CAfile ca.pem -untrusted tsa.pem -no-CApath -no-CAstore "${@:3}"; }
positive() {
  local name="$1"; shift
  "$@" > "$name.check.txt" 2>&1
  grep -F 'Verification: OK' "$name.check.txt"
  echo "$name PASS"
}
negative() {
  local name="$1" expect="$2"; shift 2
  if "$@" > "$name.check.txt" 2>&1; then echo "$name UNEXPECTED_ACCEPT"; return 1; fi
  grep -Ei "$expect" "$name.check.txt"
  echo "$name REJECTED PASS"
}
positive a_matches_a verify a a
positive b_matches_b verify b b
negative a_replayed_to_b 'nonce.*(mismatch|not)' verify a b
negative b_replayed_to_a 'nonce.*(mismatch|not)' verify b a
# Repeated old request state deliberately reproduces indistinguishability.
positive a_with_rolled_back_request_RED verify a a
# Data-only verification is a historical proof, NOT a challenge-bound response.
positive data_only_RED openssl ts -verify -in a.tsr -data synthetic.txt -CAfile ca.pem -untrusted tsa.pem -no-CApath -no-CAstore
printf '%s\n' 'DIFFERENT SYNTHETIC IMPRINT' > other.txt
negative wrong_imprint 'message imprint mismatch' openssl ts -verify -in a.tsr -data other.txt -CAfile ca.pem -untrusted tsa.pem -no-CApath -no-CAstore
# Explicit reference epoch inside certificate validity; not derived from host now.
# This is a controlled alternate verification time, not a trusted-clock solution.
epoch="$(date -u -d '2026-11-24 00:00:00 UTC' +%s)"
positive fixed_validation_epoch verify b b -attime "$epoch"
negative replay_fixed_validation_epoch 'nonce.*(mismatch|not)' verify a b -attime "$epoch"
negative pre_validity_epoch 'not yet valid|certificate verify error' verify b b -attime 1
# Damage signature/token (last byte may be a signed attribute or signature); no acceptance allowed.
python3 - <<'PY'
from pathlib import Path
p=Path('a.tsr')
d=bytearray(p.read_bytes())
d[-1]^=1
Path('tampered.tsr').write_bytes(d)
PY
negative tampered_response 'verification|error|signature' verify tampered a
echo '11/11 EXPECTED CASES PASS; RESPONSE_BINDING_ONLY; REQUEST_ROLLBACK=RED; CLOCK_PROVENANCE=UNKNOWN; REVOCATION=NOT_CHECKED; GLOBAL_LATEST=UNKNOWN; TRUST=NO_GO; PRODUCTION=NO_GO'
