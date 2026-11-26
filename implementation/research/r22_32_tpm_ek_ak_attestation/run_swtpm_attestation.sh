#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
STATE1="$TMP/tpm-state-1"
STATE2="$TMP/tpm-state-2"
mkdir -p "$STATE1" "$STATE2"
SWTPM_PIDS=()

cleanup() {
  for pid in "${SWTPM_PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  done
  rm -rf -- "$TMP"
}
trap cleanup EXIT

pass() { printf 'PASS %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1"; exit 1; }

expect_fail() {
  local label="$1"
  shift
  if "$@" >"$TMP/negative.out" 2>&1; then
    cat "$TMP/negative.out"
    fail "$label (unexpected success)"
  fi
  pass "$label"
}

start_tpm() {
  local state="$1" port="$2" ctrl="$3"
  swtpm socket --tpm2 --tpmstate "dir=$state" \
    --server "type=tcp,port=$port" --ctrl "type=tcp,port=$ctrl" \
    --flags startup-clear >"$TMP/swtpm-$port.log" 2>&1 &
  SWTPM_PIDS+=("$!")
  export TPM2TOOLS_TCTI="swtpm:host=127.0.0.1,port=$port"
  for _ in $(seq 1 100); do
    if tpm2_getrandom 8 >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.1
  done
  cat "$TMP/swtpm-$port.log"
  fail "swtpm startup on port $port"
}

pub_fingerprint() {
  openssl pkey -pubin -in "$1" -outform DER 2>/dev/null | sha256sum | awk '{print $1}'
}

printf 'R22.32 TPM EK/AK/Quote/Certify research harness\n'
tpm2 --version | head -n 1
swtpm --version | head -n 1
openssl version

# First software TPM: EK, AK, storage primary, PCR quote and certification.
start_tpm "$STATE1" 2321 2322
pass "first software TPM initialized"

EK_CTX="$TMP/ek.ctx"
EK_PUB="$TMP/ek.pem"
AK_CTX="$TMP/ak.ctx"
AK_PUB="$TMP/ak.pem"
AK_NAME="$TMP/ak.name"
AK_QN="$TMP/ak.qualified-name"
CRED_SECRET="$TMP/credential.secret"
CRED_BLOB="$TMP/credential.blob"
ACTIVATED_SECRET="$TMP/activated.secret"
SESSION="$TMP/endorsement.session"

tpm2_createek -G rsa -c "$EK_CTX" -u "$EK_PUB" -f pem >/dev/null
pass "TPM-generated EK public key exported"

# A local lab CA issues a synthetic certificate containing the TPM EK public
# key. This validates chain and SPKI-binding mechanics, not manufacturer trust.
CA_KEY="$TMP/lab-root.key"
CA_CERT="$TMP/lab-root.crt"
EK_CERT="$TMP/synthetic-ek-cert.crt"
WRONG_CA_KEY="$TMP/wrong-root.key"
WRONG_CA_CERT="$TMP/wrong-root.crt"
EK_EXT="$TMP/ek-extensions.cnf"

openssl req -x509 -newkey rsa:2048 -nodes -keyout "$CA_KEY" -out "$CA_CERT" \
  -sha256 -days 2 -subj "/CN=Ario Synthetic Lab Root CA" \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign,cRLSign" >/dev/null 2>&1
cat >"$EK_EXT" <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,keyEncipherment
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer
EOF
openssl x509 -new -force_pubkey "$EK_PUB" -subj "/CN=Ario Synthetic TPM EK" \
  -CA "$CA_CERT" -CAkey "$CA_KEY" -set_serial 0x22320001 \
  -days 1 -sha256 -extfile "$EK_EXT" -out "$EK_CERT"
openssl verify -CAfile "$CA_CERT" -purpose any "$EK_CERT" >/dev/null
pass "synthetic EK certificate chains to the pinned lab root"

openssl req -x509 -newkey rsa:2048 -nodes -keyout "$WRONG_CA_KEY" -out "$WRONG_CA_CERT" \
  -sha256 -days 2 -subj "/CN=Untrusted Wrong Root" \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign,cRLSign" >/dev/null 2>&1
expect_fail "EK certificate rejected under an unrelated root" \
  openssl verify -CAfile "$WRONG_CA_CERT" -purpose any "$EK_CERT"

openssl x509 -in "$EK_CERT" -pubkey -noout >"$TMP/ek-from-cert.pem"
EK_FP="$(pub_fingerprint "$EK_PUB")"
CERT_EK_FP="$(pub_fingerprint "$TMP/ek-from-cert.pem")"
[[ "$EK_FP" == "$CERT_EK_FP" ]] || fail "EK certificate SPKI does not match TPM EK public key"
pass "EK certificate SubjectPublicKeyInfo matches TPM EK public key"

# AK is not assumed to have a manufacturer X.509 certificate. Credential
# activation proves the AK is associated with the TPM holding this EK.
tpm2_createak -C "$EK_CTX" -c "$AK_CTX" -G rsa -g sha256 -s rsassa \
  -u "$AK_PUB" -f pem -n "$AK_NAME" -q "$AK_QN" >/dev/null
openssl rand -out "$CRED_SECRET" 32
tpm2_makecredential -G rsa -u "$EK_PUB" -s "$CRED_SECRET" -n "$AK_NAME" -o "$CRED_BLOB"
tpm2_startauthsession --policy-session -S "$SESSION" >/dev/null
tpm2_policysecret -S "$SESSION" -c e >/dev/null
tpm2_activatecredential -c "$AK_CTX" -C "$EK_CTX" -i "$CRED_BLOB" \
  -o "$ACTIVATED_SECRET" -P "session:$SESSION" >/dev/null
tpm2_flushcontext "$SESSION" >/dev/null
cmp -s "$CRED_SECRET" "$ACTIVATED_SECRET" || fail "credential activation secret mismatch"
pass "MakeCredential/ActivateCredential binds AK to the EK TPM"

# Second software TPM: a credential created for TPM 1 must not activate with
# a different EK and AK on TPM 2.
EK2_CTX="$TMP/ek2.ctx"
EK2_PUB="$TMP/ek2.pem"
AK2_CTX="$TMP/ak2.ctx"
AK2_PUB="$TMP/ak2.pem"
AK2_NAME="$TMP/ak2.name"
AK2_QN="$TMP/ak2.qualified-name"
SESSION2="$TMP/endorsement2.session"
start_tpm "$STATE2" 2323 2324
tpm2_createek -G rsa -c "$EK2_CTX" -u "$EK2_PUB" -f pem >/dev/null
tpm2_createak -C "$EK2_CTX" -c "$AK2_CTX" -G rsa -g sha256 -s rsassa \
  -u "$AK2_PUB" -f pem -n "$AK2_NAME" -q "$AK2_QN" >/dev/null
[[ "$(pub_fingerprint "$EK2_PUB")" != "$EK_FP" ]] || fail "replacement TPM reused EK public key"
tpm2_startauthsession --policy-session -S "$SESSION2" >/dev/null
tpm2_policysecret -S "$SESSION2" -c e >/dev/null
expect_fail "credential for TPM 1 rejected by replacement TPM 2" \
  tpm2_activatecredential -c "$AK2_CTX" -C "$EK2_CTX" -i "$CRED_BLOB" \
    -o "$TMP/wrong-activated.secret" -P "session:$SESSION2"
tpm2_flushcontext "$SESSION2" >/dev/null || true
pass "replacement simulator has a distinct EK identity"
export TPM2TOOLS_TCTI="swtpm:host=127.0.0.1,port=2321"

# Create an Owner-hierarchy storage primary and capture the TPM-computed
# Name and Qualified Name. These are stronger object identifiers than a
# caller-supplied hash of an exported PEM file.
SRK_CTX="$TMP/storage-primary.ctx"
SRK_NAME="$TMP/storage-primary.name"
SRK_QN="$TMP/storage-primary.qualified-name"
SRK_TPMT="$TMP/storage-primary.tpmt"
tpm2_createprimary -C o -G ecc -g sha256 -c "$SRK_CTX" >/dev/null
tpm2_readpublic -c "$SRK_CTX" -n "$SRK_NAME" -q "$SRK_QN" \
  -o "$SRK_TPMT" -f tpmt >/dev/null
ROOT_NAME_SHA256="$(sha256sum "$SRK_NAME" | awk '{print $1}')"
printf 'TPM_STORAGE_PRIMARY_NAME_SHA256=%s\n' "$ROOT_NAME_SHA256"
pass "storage primary Name and Qualified Name captured from TPM"

# TPM2_Certify proves the exact storage object is loaded and binds it to a
# fresh verifier challenge. The verifier checks the signature and decoded fields.
CERTIFY_NONCE="$(openssl rand -hex 32)"
CERTIFY_ATTEST="$TMP/storage-primary.attest"
CERTIFY_SIG="$TMP/storage-primary.sig"
CERTIFY_TICKET="$TMP/storage-primary.ticket"
CERTIFY_YAML="$TMP/storage-primary.yaml"
tpm2_certify -c "$SRK_CTX" -C "$AK_CTX" -g sha256 -q "$CERTIFY_NONCE" \
  -o "$CERTIFY_ATTEST" -s "$CERTIFY_SIG" >/dev/null
tpm2_verifysignature -c "$AK_CTX" -g sha256 -m "$CERTIFY_ATTEST" \
  -s "$CERTIFY_SIG" -t "$CERTIFY_TICKET" >/dev/null
tpm2_print -t TPMS_ATTEST "$CERTIFY_ATTEST" >"$CERTIFY_YAML"
python3 "$ROOT/verify_attestation_yaml.py" --mode certify --yaml "$CERTIFY_YAML" \
  --nonce "$CERTIFY_NONCE" --ak-qualified-name "$AK_QN" \
  --object-name "$SRK_NAME" --object-qualified-name "$SRK_QN"
pass "TPM2_Certify signature, fresh nonce, AK signer, storage Name and Qualified Name verified"

expect_fail "certify attestation rejected with a different challenge" \
  python3 "$ROOT/verify_attestation_yaml.py" --mode certify --yaml "$CERTIFY_YAML" \
    --nonce "$(openssl rand -hex 32)" --ak-qualified-name "$AK_QN" \
    --object-name "$SRK_NAME" --object-qualified-name "$SRK_QN"

# A different storage primary must not be accepted as the certified object.
ALT_SRK_CTX="$TMP/alternate-storage-primary.ctx"
ALT_SRK_NAME="$TMP/alternate-storage-primary.name"
ALT_SRK_QN="$TMP/alternate-storage-primary.qualified-name"
ALT_SRK_TPMT="$TMP/alternate-storage-primary.tpmt"
tpm2_createprimary -C o -G rsa -g sha256 -c "$ALT_SRK_CTX" >/dev/null
tpm2_readpublic -c "$ALT_SRK_CTX" -n "$ALT_SRK_NAME" -q "$ALT_SRK_QN" \
  -o "$ALT_SRK_TPMT" -f tpmt >/dev/null
expect_fail "certify attestation rejects substituted storage object Name" \
  python3 "$ROOT/verify_attestation_yaml.py" --mode certify --yaml "$CERTIFY_YAML" \
    --nonce "$CERTIFY_NONCE" --ak-qualified-name "$AK_QN" \
    --object-name "$ALT_SRK_NAME" --object-qualified-name "$ALT_SRK_QN"

# Quote a known application PCR measurement. The expected PCR value is
# independently recomputed as H(oldPCR || eventDigest), then checked against
# the PCR value returned after the quote to detect read/quote races.
PCR_BEFORE="$TMP/pcr-before.bin"
PCR_AFTER="$TMP/pcr-after.bin"
PCR_CHANGED="$TMP/pcr-changed.bin"
MEASUREMENT_HASH="$(printf 'Ario R22.32 synthetic measurement v1\n' | sha256sum | awk '{print $1}')"
tpm2_pcrread -o "$PCR_BEFORE" sha256:23 >/dev/null
tpm2_pcrextend "23:sha256=$MEASUREMENT_HASH" >/dev/null
tpm2_pcrread -o "$PCR_AFTER" sha256:23 >/dev/null
python3 - "$PCR_BEFORE" "$PCR_AFTER" "$MEASUREMENT_HASH" <<'PY'
import hashlib,sys
from pathlib import Path
before=Path(sys.argv[1]).read_bytes()
after=Path(sys.argv[2]).read_bytes()
event=bytes.fromhex(sys.argv[3])
if len(before) != 32 or len(after) != 32:
    raise SystemExit("PCR output is not one SHA-256 PCR value")
expected=hashlib.sha256(before + event).digest()
if after != expected:
    raise SystemExit("PCR extend result does not match H(oldPCR || eventDigest)")
print("PASS PCR 23 independently recomputed from its prior value and event digest")
PY

QUOTE_NONCE="$(openssl rand -hex 32)"
QUOTE_MSG="$TMP/pcr.quote"
QUOTE_SIG="$TMP/pcr.quote.sig"
QUOTE_YAML="$TMP/pcr.quote.yaml"
tpm2_quote -c "$AK_CTX" -l sha256:23 -q "$QUOTE_NONCE" \
  -m "$QUOTE_MSG" -s "$QUOTE_SIG" -g sha256 >/dev/null
tpm2_print -t TPMS_ATTEST "$QUOTE_MSG" >"$QUOTE_YAML"
python3 "$ROOT/verify_attestation_yaml.py" --mode quote --yaml "$QUOTE_YAML" \
  --nonce "$QUOTE_NONCE" --ak-qualified-name "$AK_QN"
tpm2_checkquote -u "$AK_PUB" -m "$QUOTE_MSG" -s "$QUOTE_SIG" \
  -f "$PCR_AFTER" -l sha256:23 -g sha256 -q "$QUOTE_NONCE" >/dev/null
pass "TPM Quote signature, fresh nonce and PCR 23 digest verified"

expect_fail "quote rejected with a different challenge" \
  tpm2_checkquote -u "$AK_PUB" -m "$QUOTE_MSG" -s "$QUOTE_SIG" \
    -f "$PCR_AFTER" -l sha256:23 -g sha256 -q "$(openssl rand -hex 32)"

openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
  -out "$TMP/wrong-ak.key" >/dev/null 2>&1
openssl pkey -in "$TMP/wrong-ak.key" -pubout -out "$TMP/wrong-ak.pub" >/dev/null 2>&1
expect_fail "quote rejected under an unrelated AK public key" \
  tpm2_checkquote -u "$TMP/wrong-ak.pub" -m "$QUOTE_MSG" -s "$QUOTE_SIG" \
    -f "$PCR_AFTER" -l sha256:23 -g sha256 -q "$QUOTE_NONCE"

python3 - "$QUOTE_SIG" "$TMP/tampered.quote.sig" <<'PY'
import sys
from pathlib import Path
raw=bytearray(Path(sys.argv[1]).read_bytes())
if not raw:
    raise SystemExit("empty quote signature")
raw[-1] ^= 0x01
Path(sys.argv[2]).write_bytes(raw)
PY
expect_fail "tampered quote signature rejected" \
  tpm2_checkquote -u "$AK_PUB" -m "$QUOTE_MSG" -s "$TMP/tampered.quote.sig" \
    -f "$PCR_AFTER" -l sha256:23 -g sha256 -q "$QUOTE_NONCE"

SECOND_MEASUREMENT_HASH="$(printf 'Ario R22.32 synthetic measurement v2\n' | sha256sum | awk '{print $1}')"
tpm2_pcrextend "23:sha256=$SECOND_MEASUREMENT_HASH" >/dev/null
tpm2_pcrread -o "$PCR_CHANGED" sha256:23 >/dev/null
expect_fail "quote rejected after PCR 23 changes after attestation" \
  tpm2_checkquote -u "$AK_PUB" -m "$QUOTE_MSG" -s "$QUOTE_SIG" \
    -f "$PCR_CHANGED" -l sha256:23 -g sha256 -q "$QUOTE_NONCE"

printf 'R22_32_TPM_ATTESTATION_COMPLETE RESEARCH_ONLY SOFTWARE_TPM SYNTHETIC_EK_CA NO_MANUFACTURER_TRUST NO_PHYSICAL_TPM NO_INDEPENDENT_CUSTODY\n'
