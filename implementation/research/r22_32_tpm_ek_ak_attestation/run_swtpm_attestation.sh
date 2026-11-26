#!/usr/bin/env bash
set -euo pipefail
# Stacked on latest R22.31 PR #411 head 1dba8ae472d0a0c8d02ab575eb62878fa705f897

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

CHALLENGE_NONCE="$(printenv ARIO_R22_33_CHALLENGE_NONCE 2>/dev/null || true)"
CI_CUSTODIAN_PRIVATE_KEY_PATH="$(printenv ARIO_R22_33_CI_CUSTODIAN_PRIVATE_KEY_PATH 2>/dev/null || true)"
CI_CUSTODIAN_DIR="$TMP/r22-33-ci-custodian"
CI_CHALLENGE_JSON="$CI_CUSTODIAN_DIR/challenge.json"
CI_CHALLENGE_SIG="$CI_CUSTODIAN_DIR/challenge.sig"
CI_ANCHOR_JSON="$CI_CUSTODIAN_DIR/anchor.json"
CI_ANCHOR_SIG="$CI_CUSTODIAN_DIR/anchor.sig"
CI_CUSTODIAN_PRIVATE="$CI_CUSTODIAN_DIR/custodian.key"
CI_CUSTODIAN_PUBLIC="$CI_CUSTODIAN_DIR/custodian.pub"
if [[ -n "$CHALLENGE_NONCE" && ! "$CHALLENGE_NONCE" =~ ^[0-9a-f]{64}$ ]]; then
  fail "ARIO_R22_33_CHALLENGE_NONCE must be 64 lowercase hex characters"
fi

derive_challenge_nonce() {
  local domain="$1"
  python3 - "$CHALLENGE_NONCE" "$domain" <<'PY'
import hashlib
import sys
nonce = bytes.fromhex(sys.argv[1])
domain = sys.argv[2]
tag = f"ARIO-R22.33-{domain}-NONCE-V1".encode("ascii") + b"\x00"
print(hashlib.sha256(tag + nonce).hexdigest())
PY
}


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

printf 'R22.32 TPM EK/AK/Quote/CertifyCreation research harness\n'
dpkg-query -W -f='tpm2-tools ${Version}\n' tpm2-tools
dpkg-query -W -f='swtpm ${Version}\n' swtpm
openssl version

# First software TPM: EK, AK, storage primary, PCR quote and certification.
start_tpm "$STATE1" 2321 2322
pass "first software TPM initialized"

EK_CTX="0x81010001"
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

# In the R22.33 end-to-end path, issue a real custodian-signed challenge only
# after the TPM-generated EK identity is known, then derive every TPM nonce
# from that challenge before creating the attestation evidence.
if [[ -n "$CI_CUSTODIAN_PRIVATE_KEY_PATH" ]]; then
  mkdir -p "$CI_CUSTODIAN_DIR" "$(dirname "$CI_CUSTODIAN_PRIVATE_KEY_PATH")"
  openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
    -out "$CI_CUSTODIAN_PRIVATE" >/dev/null 2>&1
  openssl pkey -in "$CI_CUSTODIAN_PRIVATE" -pubout -out "$CI_CUSTODIAN_PUBLIC" >/dev/null 2>&1
  PREVIOUS_ROOT="$(python3 - <<'PY'
import hashlib
print(hashlib.sha256(b"ARIO-R22.33-CI-PREVIOUS-STORAGE-ROOT").hexdigest())
PY
)"
  PREVIOUS_HEAD="$(python3 - <<'PY'
import hashlib
print(hashlib.sha256(b"ARIO-R22.33-CI-PREVIOUS-HEAD").hexdigest())
PY
)"
  GITHUB_SHA_VALUE="$(printenv GITHUB_SHA 2>/dev/null || printf 'ARIO-R22.33-CI-NEXT-HEAD')"
  NEXT_HEAD="$(python3 - "$GITHUB_SHA_VALUE" <<'PY'
import hashlib, sys
print(hashlib.sha256(sys.argv[1].encode("utf-8")).hexdigest())
PY
)"
  python3 - "$EK_FP" "$PREVIOUS_ROOT" "$PREVIOUS_HEAD" "$CI_ANCHOR_JSON" <<'PY'
import json, sys
from pathlib import Path
anchor = {
    "format": "ARIO-R22.31-ANCHOR-V1",
    "device_ek_sha256": sys.argv[1],
    "storage_root_sha256": sys.argv[2],
    "epoch": 7,
    "head_sha256": sys.argv[3],
}
Path(sys.argv[4]).write_bytes(
    (json.dumps(anchor, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\\n").encode("utf-8")
)
PY
  openssl dgst -sha256 -sign "$CI_CUSTODIAN_PRIVATE" \
    -out "$CI_ANCHOR_SIG" "$CI_ANCHOR_JSON"
  python3 "$ROOT/../r22_33_attested_transition/issue_challenge.py" \
    --anchor "$CI_ANCHOR_JSON" --anchor-signature "$CI_ANCHOR_SIG" \
    --public-key "$CI_CUSTODIAN_PUBLIC" --private-key "$CI_CUSTODIAN_PRIVATE" \
    --journal "$CI_CUSTODIAN_DIR/journal.jsonl" --lock "$CI_CUSTODIAN_DIR/lock" \
    --output "$CI_CHALLENGE_JSON" --signature "$CI_CHALLENGE_SIG" \
    --next-head-sha256 "$NEXT_HEAD" --ttl-seconds 300
  CHALLENGE_NONCE="$(python3 - "$CI_CHALLENGE_JSON" <<'PY'
import json, sys
print(json.loads(open(sys.argv[1], encoding="utf-8").read())["nonce"])
PY
)"
  cp "$CI_CUSTODIAN_PRIVATE" "$CI_CUSTODIAN_PRIVATE_KEY_PATH"
  chmod 600 "$CI_CUSTODIAN_PRIVATE_KEY_PATH"
  pass "fresh custodian-signed R22.33 challenge issued for this TPM EK"
fi
if [[ -z "$CHALLENGE_NONCE" ]]; then
  CHALLENGE_NONCE="$(openssl rand -hex 32)"
fi

# AK is not assumed to have a manufacturer X.509 certificate. Credential
# activation proves the AK is associated with the TPM holding this EK.
tpm2_createak -C "$EK_CTX" -c "$AK_CTX" -G rsa -g sha256 -s rsassa \
  -u "$AK_PUB" -f pem -n "$AK_NAME" -q "$AK_QN" >/dev/null
AK_NAME_HEX="$(python3 - "$AK_NAME" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).read_bytes().hex())
PY
)"
openssl rand -out "$CRED_SECRET" 32
# MakeCredential uses LoadExternal internally. The EK is persistent in the
# simulator, leaving transient slots for the AK and temporary external EK.
tpm2_makecredential -G rsa -u "$EK_PUB" -s "$CRED_SECRET" -n "$AK_NAME_HEX" -o "$CRED_BLOB"
tpm2_startauthsession --policy-session -S "$SESSION" >/dev/null
tpm2_policysecret -S "$SESSION" -c e >/dev/null
tpm2_activatecredential -c "$AK_CTX" -C "$EK_CTX" -i "$CRED_BLOB" \
  -o "$ACTIVATED_SECRET" -P "session:$SESSION" >/dev/null
tpm2_flushcontext "$SESSION" >/dev/null
cmp -s "$CRED_SECRET" "$ACTIVATED_SECRET" || fail "credential activation secret mismatch"
pass "MakeCredential/ActivateCredential binds AK to the EK TPM"
AK_HANDLE="0x81010010"
tpm2_evictcontrol -C o -c "$AK_CTX" "$AK_HANDLE" >/dev/null
tpm2_flushcontext -t >/dev/null
AK_CTX="$AK_HANDLE"
pass "AK persisted under its test handle; transient objects released"
AK_TPMT="$TMP/ak.tpmt"
tpm2_readpublic -c "$AK_CTX" -n "$AK_NAME" -q "$AK_QN" \
  -o "$AK_TPMT" -f tpmt >/dev/null
python3 "$ROOT/verify_tpm_public_name.py" --public-tpmt "$AK_TPMT" \
  --name "$AK_NAME" --require-ak
pass "AK Name independently recomputed from TPMT_PUBLIC with restricted signing attributes"

# A restricted signing AK must not also be a decrypt-capable object. Recompute
# the Name after mutation so this specifically tests the usage-profile guard.
python3 - "$AK_TPMT" "$TMP/ak-decrypt.tpmt" "$TMP/ak-decrypt.name" <<'PY'
import hashlib, sys
from pathlib import Path
raw = bytearray(Path(sys.argv[1]).read_bytes())
attrs = int.from_bytes(raw[4:8], "big") | (1 << 17)
raw[4:8] = attrs.to_bytes(4, "big")
Path(sys.argv[2]).write_bytes(raw)
Path(sys.argv[3]).write_bytes(raw[2:4] + hashlib.sha256(raw).digest())
PY
expect_fail "AK profile rejects decrypt usage even with recomputed Name" \
  python3 "$ROOT/verify_tpm_public_name.py" --public-tpmt "$TMP/ak-decrypt.tpmt" \
    --name "$TMP/ak-decrypt.name" --require-ak


# Second software TPM: a credential created for TPM 1 must not activate with
# a different EK and AK on TPM 2.
EK2_CTX="0x81010001"
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
SRK_HANDLE="0x81010002"
SRK_TEMP_CTX="$TMP/storage-primary.transient.ctx"
SRK_CTX="$SRK_HANDLE"
SRK_NAME="$TMP/storage-primary.name"
SRK_QN="$TMP/storage-primary.qualified-name"
SRK_TPMT="$TMP/storage-primary.tpmt"
SRK_CREATION_DATA="$TMP/storage-primary.creation-data"
SRK_CREATION_HASH="$TMP/storage-primary.creation-hash"
SRK_CREATION_TICKET="$TMP/storage-primary.creation-ticket"
tpm2_createprimary -C o -G ecc -g sha256 -c "$SRK_TEMP_CTX" \
  --creation-data "$SRK_CREATION_DATA" --creation-hash "$SRK_CREATION_HASH" \
  --creation-ticket "$SRK_CREATION_TICKET" >/dev/null
tpm2_evictcontrol -C o -c "$SRK_TEMP_CTX" "$SRK_HANDLE" >/dev/null
tpm2_flushcontext -t >/dev/null
tpm2_readpublic -c "$SRK_CTX" -n "$SRK_NAME" -q "$SRK_QN" \
  -o "$SRK_TPMT" -f tpmt >/dev/null
python3 "$ROOT/verify_tpm_public_name.py" --public-tpmt "$SRK_TPMT" \
  --name "$SRK_NAME" --require-storage-primary
cp "$SRK_TPMT" "$TMP/tampered-storage-primary.tpmt"
python3 - "$TMP/tampered-storage-primary.tpmt" <<'PY'
import sys
from pathlib import Path
raw=bytearray(Path(sys.argv[1]).read_bytes())
if not raw:
    raise SystemExit("empty TPMT_PUBLIC")
raw[-1] ^= 0x01
Path(sys.argv[1]).write_bytes(raw)
PY
expect_fail "TPM Name verifier rejects a modified TPMT_PUBLIC" \
  python3 "$ROOT/verify_tpm_public_name.py" \
    --public-tpmt "$TMP/tampered-storage-primary.tpmt" --name "$SRK_NAME"
ROOT_NAME_SHA256="$(sha256sum "$SRK_NAME" | awk '{print $1}')"
printf 'TPM_STORAGE_PRIMARY_NAME_SHA256=%s\n' "$ROOT_NAME_SHA256"
pass "storage primary Name and Qualified Name captured from TPM"
# A storage primary is a restricted decryption object, never a signer.
python3 - "$SRK_TPMT" "$TMP/storage-sign.tpmt" "$TMP/storage-sign.name" <<'PY'
import hashlib, sys
from pathlib import Path
raw = bytearray(Path(sys.argv[1]).read_bytes())
attrs = int.from_bytes(raw[4:8], "big") | (1 << 18)
raw[4:8] = attrs.to_bytes(4, "big")
Path(sys.argv[2]).write_bytes(raw)
Path(sys.argv[3]).write_bytes(raw[2:4] + hashlib.sha256(raw).digest())
PY
expect_fail "storage profile rejects sign usage even with recomputed Name" \
  python3 "$ROOT/verify_tpm_public_name.py" --public-tpmt "$TMP/storage-sign.tpmt" \
    --name "$TMP/storage-sign.name" --require-storage-primary

# TPM2_Certify proves the exact storage object is loaded and binds it to a
# fresh verifier challenge. The verifier checks the signature and decoded fields.

expect_reject() {
  local label="$1"
  shift
  if "$@" >"$TMP/negative.out" 2>&1; then
    cat "$TMP/negative.out"
    fail "$label (unexpected success)"
  fi
  if ! grep -q '^REJECT ' "$TMP/negative.out"; then
    cat "$TMP/negative.out"
    fail "$label (no explicit REJECT result)"
  fi
  pass "$label"
}

# Bind the exact 32-byte storage-root claim to a TPM NV index. This proves
# what the TPM stored and signed at this moment; it does not prove the claim
# was correctly measured from a filesystem or make the NV index immutable.
ROOT_COMMITMENT="$TMP/root-commitment.bin"
printf '%s' "$ROOT_NAME_SHA256" | xxd -r -p >"$ROOT_COMMITMENT"
[[ "$(wc -c <"$ROOT_COMMITMENT")" -eq 32 ]] || fail "storage-root commitment is not 32 bytes"

NV_INDEX="0x01500020"
NV_PUBLIC="$TMP/nv-public.yaml"
NV_READBACK="$TMP/nv-readback.bin"
NV_ATTEST="$TMP/nv-attest.bin"
NV_SIG="$TMP/nv-attest.sig"
NV_TICKET="$TMP/nv-attest.ticket"
if [[ -n "$CHALLENGE_NONCE" ]]; then NV_NONCE="$(derive_challenge_nonce NV-ATTESTATION)"; else NV_NONCE="$(openssl rand -hex 32)"; fi

tpm2_nvdefine -C o -s 32 -a "ownerread|ownerwrite|authread|authwrite" "$NV_INDEX" >/dev/null
tpm2_nvwrite -C o -i "$ROOT_COMMITMENT" "$NV_INDEX" >/dev/null
tpm2_nvread -C o -s 32 -o "$NV_READBACK" "$NV_INDEX" >/dev/null
cmp -s "$ROOT_COMMITMENT" "$NV_READBACK" || fail "TPM NV readback differs from the storage-root commitment"
tpm2_nvreadpublic >"$NV_PUBLIC"
printf 'NV_PUBLIC_YAML_BEGIN\\n'
cat "$NV_PUBLIC"
printf 'NV_PUBLIC_YAML_END\\n'

tpm2_nvcertify -C "$AK_CTX" -c o -g sha256 -s rsassa -q "$NV_NONCE" \
  --size 32 -o "$NV_SIG" --attestation "$NV_ATTEST" "$NV_INDEX" >/dev/null
tpm2_verifysignature -c "$AK_CTX" -g sha256 -m "$NV_ATTEST" \
  -s "$NV_SIG" -t "$NV_TICKET" >/dev/null
python3 "$ROOT/verify_nv_attestation.py" --attest "$NV_ATTEST" \
  --nonce "$NV_NONCE" --ak-qualified-name "$AK_QN" \
  --nv-public-yaml "$NV_PUBLIC" --nv-index "$NV_INDEX" \
  --expected-contents "$ROOT_COMMITMENT"
pass "TPM2_NV_Certify signature, fresh challenge, index Name and exact storage-root bytes verified"
cp "$NV_ATTEST" "$TMP/original-nv-attest.bin"

expect_reject "NV attestation rejected with a different challenge" \
  python3 "$ROOT/verify_nv_attestation.py" --attest "$NV_ATTEST" \
    --nonce "$(openssl rand -hex 32)" --ak-qualified-name "$AK_QN" \
    --nv-public-yaml "$NV_PUBLIC" --nv-index "$NV_INDEX" \
    --expected-contents "$ROOT_COMMITMENT"
ALT_ROOT_COMMITMENT="$TMP/alternate-root.bin"
openssl rand -out "$ALT_ROOT_COMMITMENT" 32

expect_reject "NV attestation rejects a substituted root commitment" \
  python3 "$ROOT/verify_nv_attestation.py" --attest "$NV_ATTEST" \
    --nonce "$NV_NONCE" --ak-qualified-name "$AK_QN" \
    --nv-public-yaml "$NV_PUBLIC" --nv-index "$NV_INDEX" \
    --expected-contents "$TMP/alternate-root.bin"
expect_reject "NV attestation rejects a substituted NV index handle" \
  python3 "$ROOT/verify_nv_attestation.py" --attest "$NV_ATTEST" \
    --nonce "$NV_NONCE" --ak-qualified-name "$AK_QN" \
    --nv-public-yaml "$NV_PUBLIC" --nv-index "0x01500021" \
    --expected-contents "$ROOT_COMMITMENT"
expect_reject "NV attestation rejects a different AK Qualified Name" \
  python3 "$ROOT/verify_nv_attestation.py" --attest "$NV_ATTEST" \
    --nonce "$NV_NONCE" --ak-qualified-name "$AK2_QN" \
    --nv-public-yaml "$NV_PUBLIC" --nv-index "$NV_INDEX" \
    --expected-contents "$ROOT_COMMITMENT"

# Expected mutability boundary: the same TPM owner can overwrite the NV value
# and obtain a fresh, valid attestation. This is deliberately not called
# rollback resistance or independent custody.
ALT_NV_READBACK="$TMP/alternate-nv-readback.bin"
ALT_NV_PUBLIC="$TMP/alternate-nv-public.yaml"
ALT_NV_ATTEST="$TMP/alternate-nv-attest.bin"
ALT_NV_SIG="$TMP/alternate-nv-attest.sig"
ALT_NV_TICKET="$TMP/alternate-nv-attest.ticket"
ALT_NV_NONCE="$(openssl rand -hex 32)"

tpm2_nvwrite -C o -i "$ALT_ROOT_COMMITMENT" "$NV_INDEX" >/dev/null
tpm2_nvread -C o -s 32 -o "$ALT_NV_READBACK" "$NV_INDEX" >/dev/null
cmp -s "$ALT_ROOT_COMMITMENT" "$ALT_NV_READBACK" || fail "alternate NV readback mismatch"
tpm2_nvreadpublic >"$ALT_NV_PUBLIC"
tpm2_nvcertify -C "$AK_CTX" -c o -g sha256 -s rsassa -q "$ALT_NV_NONCE" \
  --size 32 -o "$ALT_NV_SIG" --attestation "$ALT_NV_ATTEST" "$NV_INDEX" >/dev/null
tpm2_verifysignature -c "$AK_CTX" -g sha256 -m "$ALT_NV_ATTEST" \
  -s "$ALT_NV_SIG" -t "$ALT_NV_TICKET" >/dev/null
python3 "$ROOT/verify_nv_attestation.py" --attest "$ALT_NV_ATTEST" \
  --nonce "$ALT_NV_NONCE" --ak-qualified-name "$AK_QN" \
  --nv-public-yaml "$ALT_NV_PUBLIC" --nv-index "$NV_INDEX" \
  --expected-contents "$ALT_ROOT_COMMITMENT"
pass "TPM owner can rewrite NV contents and obtain a fresh valid attestation (expected limitation)"

expect_reject "old NV attestation rejected against rewritten contents" \
  python3 "$ROOT/verify_nv_attestation.py" --attest "$NV_ATTEST" \
    --nonce "$NV_NONCE" --ak-qualified-name "$AK_QN" \
    --nv-public-yaml "$ALT_NV_PUBLIC" --nv-index "$NV_INDEX" \
    --expected-contents "$ALT_ROOT_COMMITMENT"
expect_reject "new NV attestation rejected against the prior root commitment" \
  python3 "$ROOT/verify_nv_attestation.py" --attest "$ALT_NV_ATTEST" \
    --nonce "$ALT_NV_NONCE" --ak-qualified-name "$AK_QN" \
    --nv-public-yaml "$ALT_NV_PUBLIC" --nv-index "$NV_INDEX" \
    --expected-contents "$ROOT_COMMITMENT"



# TPM2_Certify proves the exact storage object is loaded and binds it to a
# fresh verifier challenge. The verifier checks the signature and decoded fields.
if [[ -n "$CHALLENGE_NONCE" ]]; then CERTIFY_NONCE="$(derive_challenge_nonce CERTIFY-CREATION)"; else CERTIFY_NONCE="$(openssl rand -hex 32)"; fi
CERTIFY_ATTEST="$TMP/storage-primary.attest"
CERTIFY_SIG="$TMP/storage-primary.sig"
CERTIFY_VERIFY_TICKET="$TMP/storage-primary.verify-ticket"
tpm2_certifycreation -C "$AK_CTX" -c "$SRK_CTX" \
  -d "$SRK_CREATION_HASH" -t "$SRK_CREATION_TICKET" -g sha256 \
  -s rsassa -q "$CERTIFY_NONCE" -o "$CERTIFY_SIG" \
  --attestation "$CERTIFY_ATTEST" >/dev/null
tpm2_verifysignature -c "$AK_CTX" -g sha256 -m "$CERTIFY_ATTEST" \
  -s "$CERTIFY_SIG" -t "$CERTIFY_VERIFY_TICKET" >/dev/null
python3 "$ROOT/verify_attestation.py" --mode creation --attest "$CERTIFY_ATTEST" \
  --nonce "$CERTIFY_NONCE" --ak-qualified-name "$AK_QN" \
  --object-name "$SRK_NAME" --creation-hash "$SRK_CREATION_HASH"
pass "TPM2_CertifyCreation signature, fresh nonce, AK signer, object Name and creation hash verified"

expect_fail "certify attestation rejected with a different challenge" \
  python3 "$ROOT/verify_attestation.py" --mode creation --attest "$CERTIFY_ATTEST" \
    --nonce "$(openssl rand -hex 32)" --ak-qualified-name "$AK_QN" \
    --object-name "$SRK_NAME" --creation-hash "$SRK_CREATION_HASH"

# A different storage primary must not be accepted as the certified object.
ALT_SRK_HANDLE="0x81010003"
ALT_SRK_TEMP_CTX="$TMP/alternate-storage-primary.transient.ctx"
ALT_SRK_CTX="$ALT_SRK_HANDLE"
ALT_SRK_NAME="$TMP/alternate-storage-primary.name"
ALT_SRK_QN="$TMP/alternate-storage-primary.qualified-name"
ALT_SRK_TPMT="$TMP/alternate-storage-primary.tpmt"
tpm2_createprimary -C o -G rsa -g sha256 -c "$ALT_SRK_TEMP_CTX" >/dev/null
tpm2_evictcontrol -C o -c "$ALT_SRK_TEMP_CTX" "$ALT_SRK_HANDLE" >/dev/null
tpm2_flushcontext -t >/dev/null
tpm2_readpublic -c "$ALT_SRK_CTX" -n "$ALT_SRK_NAME" -q "$ALT_SRK_QN" \
  -o "$ALT_SRK_TPMT" -f tpmt >/dev/null
python3 "$ROOT/verify_tpm_public_name.py" --public-tpmt "$ALT_SRK_TPMT" --name "$ALT_SRK_NAME"
expect_fail "certify attestation rejects substituted storage object Name" \
  python3 "$ROOT/verify_attestation.py" --mode creation --attest "$CERTIFY_ATTEST" \
    --nonce "$CERTIFY_NONCE" --ak-qualified-name "$AK_QN" \
    --object-name "$ALT_SRK_NAME" --creation-hash "$SRK_CREATION_HASH"

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

if [[ -n "$CHALLENGE_NONCE" ]]; then QUOTE_NONCE="$(derive_challenge_nonce PCR-QUOTE)"; else QUOTE_NONCE="$(openssl rand -hex 32)"; fi
QUOTE_MSG="$TMP/pcr.quote"
QUOTE_SIG="$TMP/pcr.quote.sig"
tpm2_quote -c "$AK_CTX" -l sha256:23 -q "$QUOTE_NONCE" \
  -m "$QUOTE_MSG" -s "$QUOTE_SIG" -g sha256 >/dev/null
python3 "$ROOT/verify_attestation.py" --mode quote --attest "$QUOTE_MSG" \
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

EVIDENCE_DIR="$(printenv ARIO_R22_32_EVIDENCE_DIR 2>/dev/null || true)"
if [[ -n "$EVIDENCE_DIR" ]]; then
  mkdir -p "$EVIDENCE_DIR"
  cp "$CA_CERT" "$EVIDENCE_DIR/ek-lab-root.crt"
  cp "$EK_CERT" "$EVIDENCE_DIR/ek-certificate.crt"
  cp "$EK_PUB" "$EVIDENCE_DIR/ek-public.pem"
  cp "$AK_PUB" "$EVIDENCE_DIR/ak-public.pem"
  cp "$AK_NAME" "$EVIDENCE_DIR/ak-name.bin"
  cp "$AK_QN" "$EVIDENCE_DIR/ak-qualified-name.bin"
  cp "$AK_TPMT" "$EVIDENCE_DIR/ak-public-area.tpmt"
  cp "$SRK_NAME" "$EVIDENCE_DIR/storage-name.bin"
  cp "$SRK_QN" "$EVIDENCE_DIR/storage-qualified-name.bin"
  cp "$SRK_TPMT" "$EVIDENCE_DIR/storage-public-area.tpmt"
  cp "$SRK_CREATION_DATA" "$EVIDENCE_DIR/storage-creation-data.bin"
  cp "$SRK_CREATION_HASH" "$EVIDENCE_DIR/storage-creation-hash.bin"
  cp "$ROOT_COMMITMENT" "$EVIDENCE_DIR/storage-root-commitment.bin"
  cp "$NV_PUBLIC" "$EVIDENCE_DIR/nv-public.yaml"
  cp "$NV_READBACK" "$EVIDENCE_DIR/nv-contents.bin"
  cp "$NV_ATTEST" "$EVIDENCE_DIR/nv-attestation.bin"
  cp "$NV_SIG" "$EVIDENCE_DIR/nv-attestation.sig"
  cp "$CERTIFY_ATTEST" "$EVIDENCE_DIR/creation-attestation.bin"
  cp "$CERTIFY_SIG" "$EVIDENCE_DIR/creation-attestation.sig"
  cp "$PCR_BEFORE" "$EVIDENCE_DIR/pcr23-before.bin"
  cp "$PCR_AFTER" "$EVIDENCE_DIR/pcr23-after.bin"
  cp "$QUOTE_MSG" "$EVIDENCE_DIR/quote-attestation.bin"
  cp "$QUOTE_SIG" "$EVIDENCE_DIR/quote-attestation.sig"
  printf '%s\n' "$NV_INDEX" >"$EVIDENCE_DIR/nv-index.txt"
  printf '%s\n' "$NV_NONCE" >"$EVIDENCE_DIR/nv-nonce.txt"
  printf '%s\n' "$CERTIFY_NONCE" >"$EVIDENCE_DIR/creation-nonce.txt"
  printf '%s\n' "$QUOTE_NONCE" >"$EVIDENCE_DIR/quote-nonce.txt"
  printf '%s\n' "$MEASUREMENT_HASH" >"$EVIDENCE_DIR/pcr23-event-digest.txt"
  printf '%s\n' "$EK_FP" >"$EVIDENCE_DIR/ek-spki-sha256.txt"
  printf '%s\n' "$ROOT_NAME_SHA256" >"$EVIDENCE_DIR/storage-root-sha256.txt"
  if [[ -n "$CHALLENGE_NONCE" ]]; then
    printf '%s\n' "$CHALLENGE_NONCE" >"$EVIDENCE_DIR/custodian-challenge-nonce.txt"
  fi
  if [[ -n "$CI_CUSTODIAN_PRIVATE_KEY_PATH" ]]; then
    cp "$CI_CUSTODIAN_PUBLIC" "$EVIDENCE_DIR/custodian-public.pem"
    cp "$CI_ANCHOR_JSON" "$EVIDENCE_DIR/custodian-anchor.json"
    cp "$CI_ANCHOR_SIG" "$EVIDENCE_DIR/custodian-anchor.sig"
    cp "$CI_CHALLENGE_JSON" "$EVIDENCE_DIR/custodian-challenge.json"
    cp "$CI_CHALLENGE_SIG" "$EVIDENCE_DIR/custodian-challenge.sig"
    case "$(realpath "$CI_CUSTODIAN_PRIVATE_KEY_PATH")" in
      "$(realpath "$EVIDENCE_DIR")"/*) fail "custodian private key must never be placed in the public evidence bundle" ;;
    esac
  fi
  python3 - "$EVIDENCE_DIR" <<'PY'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1])
files = sorted(p for p in root.iterdir() if p.is_file() and p.name != "evidence-manifest.json")
manifest = {
    "format": "ARIO-R22.32-SWTPM-EVIDENCE-MANIFEST-V1",
    "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
}
(root / "evidence-manifest.json").write_text(
    json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
    encoding="utf-8",
)
print("PASS raw public TPM evidence bundle exported with SHA-256 manifest")
PY
fi

printf 'R22_32_TPM_ATTESTATION_COMPLETE RESEARCH_ONLY SOFTWARE_TPM SYNTHETIC_EK_CA NO_MANUFACTURER_TRUST NO_PHYSICAL_TPM NO_INDEPENDENT_CUSTODY\n'
