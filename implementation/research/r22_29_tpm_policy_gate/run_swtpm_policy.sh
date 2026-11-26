#!/usr/bin/env bash
set -euo pipefail

TMP="$(mktemp -d)"
STATE="$TMP/tpm-state"
mkdir -p "$STATE"
SWTPM_PID=""
cleanup() {
  if [[ -n "$SWTPM_PID" ]]; then kill "$SWTPM_PID" 2>/dev/null || true; wait "$SWTPM_PID" 2>/dev/null || true; fi
  rm -rf "$TMP"
}
trap cleanup EXIT

export TPM2TOOLS_TCTI="swtpm:host=127.0.0.1,port=2321"
NV="0x01500016"

pass(){ printf 'PASS %s\n' "$1"; }
fail(){ printf 'FAIL %s\n' "$1"; exit 1; }
expect_fail(){
  local label="$1"; shift
  if "$@" >"$TMP/negative.out" 2>&1; then
    cat "$TMP/negative.out"; fail "$label (unexpected success)"
  fi
  pass "$label"
}
run(){ "$@" >"$TMP/last.out" 2>&1 || { cat "$TMP/last.out"; return 1; }; }

tpm2 --version | head -n 1
swtpm --version | head -n 1
swtpm socket --tpm2 --tpmstate "dir=$STATE" --server type=tcp,port=2321 --ctrl type=tcp,port=2322 --flags startup-clear >"$TMP/swtpm.log" 2>&1 &
SWTPM_PID=$!
for _ in $(seq 1 80); do
  if tpm2_getrandom 8 >/dev/null 2>&1; then break; fi
  sleep 0.1
done
if ! tpm2_getrandom 8 >/dev/null 2>&1; then cat "$TMP/swtpm.log"; fail "swtpm startup"; fi
pass "software TPM 2.0 initialized"

# Create a TPM-resident signing key whose object authPolicy requires
# PolicyAuthorize under a separately pinned authorization public key.
tpm2_createprimary -C o -G ecc -g sha256 -c primary.ctx >/dev/null
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out policy-authority.private.pem >/dev/null 2>&1
openssl pkey -in policy-authority.private.pem -pubout -out policy-authority.public.pem >/dev/null 2>&1
tpm2_loadexternal -C o -G rsa -u policy-authority.public.pem -c policy-authority.ctx -n policy-authority.name >/dev/null
tpm2_startauthsession -S key-trial.ctx >/dev/null
tpm2_policyauthorize -S key-trial.ctx -n policy-authority.name -L key-auth.policy >/dev/null
echo "MARK flush-trial" >&2
tpm2_flushcontext key-trial.ctx >/dev/null
tpm2_flushcontext -t >/dev/null
tpm2_createprimary -C o -G ecc -g sha256 -c primary.ctx >/dev/null
tpm2_create -C primary.ctx -G ecc -g sha256 -L key-auth.policy \
  -a "fixedtpm|fixedparent|sensitivedataorigin|sign|noda" \
  -u signer.public -r signer.private >/dev/null
tpm2_load -C primary.ctx -u signer.public -r signer.private -c signer.ctx >/dev/null
tpm2_loadexternal -C o -G rsa -u policy-authority.public.pem -c policy-authority.ctx -n policy-authority.name >/dev/null
tpm2_readpublic -c signer.ctx -f yaml -o signer-public.yaml >/dev/null
grep -Eiq 'fixedtpm' signer-public.yaml || fail "fixedTPM attribute missing"
grep -Eiq 'fixedparent' signer-public.yaml || fail "fixedParent attribute missing"
if grep -q 'BEGIN .*PRIVATE KEY' signer.private; then fail "TPM private blob unexpectedly PEM"; fi
pass "TPM-generated fixedTPM/fixedParent signing object created"
tpm2_nvdefine -C o -a "nt=counter|ownerread|ownerwrite" "$NV" >/dev/null
tpm2_nvread -C o -s 8 -o counter-0.bin "$NV" >/dev/null
pass "TPM monotonic NV counter initialized"

make_authorization(){
  local message="$1" counter="$2" tag="$3"
  tpm2_sign --cphash "$tag.cphash" -c signer.ctx -g sha256 "$message" >/dev/null
  tpm2_startauthsession -S "$tag.trial.ctx" >/dev/null
  tpm2_policycommandcode -S "$tag.trial.ctx" TPM2_CC_Sign >/dev/null
  tpm2_policynv -S "$tag.trial.ctx" -C o "$NV" eq -i "$counter" >/dev/null
  tpm2_policycphash -S "$tag.trial.ctx" -L "$tag.approved.policy" --cphash "$tag.cphash" >/dev/null
  tpm2_flushcontext "$tag.trial.ctx" >/dev/null
  openssl dgst -sha256 -sign policy-authority.private.pem -out "$tag.approved.sig" "$tag.approved.policy" >/dev/null 2>&1
  tpm2_verifysignature -c policy-authority.ctx -g sha256 -m "$tag.approved.policy" \
    -s "$tag.approved.sig" -t "$tag.ticket" -f rsassa >/dev/null
}
start_policy(){
  local tag="$1" counter="$2"
  tpm2_startauthsession --policy-session -S "$tag.session.ctx" >/dev/null
  tpm2_policycommandcode -S "$tag.session.ctx" TPM2_CC_Sign >/dev/null
  tpm2_policynv -S "$tag.session.ctx" -C o "$NV" eq -i "$counter" >/dev/null
  tpm2_policycphash -S "$tag.session.ctx" --cphash "$tag.cphash" >/dev/null
  tpm2_policyauthorize -S "$tag.session.ctx" -i "$tag.approved.policy" \
    -n policy-authority.name -t "$tag.ticket" >/dev/null
}
sign_authorized(){
  local tag="$1" message="$2"
  tpm2_sign -c signer.ctx -g sha256 -o "$tag.signature" \
    -p "session:$tag.session.ctx" "$message" >/dev/null
  tpm2_verifysignature -c signer.ctx -g sha256 -m "$message" -s "$tag.signature" >/dev/null
  tpm2_flushcontext "$tag.session.ctx" >/dev/null
}

printf 'Ario commitment A — generation 1\n' > message-a.bin
printf 'Ario conflicting commitment B — generation 1\n' > message-b.bin
printf 'Ario commitment C — generation 2\n' > message-c.bin

expect_fail "raw TPM sign without policy session" tpm2_sign -c signer.ctx -g sha256 -o raw.signature message-a.bin
expect_fail "fixed TPM object duplication blocked" tpm2_duplicate -C primary.ctx -c signer.ctx -G null -r duplicate.private -s duplicate.seed

# Authorize A only for the current NV counter and exact TPM2_Sign cpHash.
make_authorization message-a.bin counter-0.bin a
# Reuse A's policy session for B: command cpHash differs, so TPM must reject.
start_policy a counter-0.bin
expect_fail "altered message rejected by TPM cpHash policy" tpm2_sign -c signer.ctx -g sha256 -o altered.signature -p session:a.session.ctx message-b.bin
tpm2_flushcontext a.session.ctx >/dev/null
# The exact authorized command succeeds and verifies.
start_policy a counter-0.bin
sign_authorized a message-a.bin
pass "exact externally authorized TPM signature verified"
# Same token is tied to counter zero; advance hardware NV counter.
tpm2_nvincrement -C o "$NV" >/dev/null
tpm2_nvread -C o -s 8 -o counter-1.bin "$NV" >/dev/null
tpm2_startauthsession --policy-session -S stale-counter.session >/dev/null
expect_fail "stale authorization rejected after NV counter increment" tpm2_policynv -S stale-counter.session -C o "$NV" eq -i counter-0.bin
tpm2_flushcontext stale-counter.session >/dev/null

# A new counter value and new exact command hash require a fresh authority signature.
make_authorization message-c.bin counter-1.bin c
start_policy c counter-1.bin
sign_authorized c message-c.bin
pass "generation two signed only under fresh counter-bound authorization"
tpm2_nvincrement -C o "$NV" >/dev/null

# RED control: owner can undefine/recreate an owner-managed NV counter with
# the same public definition and reset its value. This is not a security pass.
tpm2_nvundefine -C o "$NV" >/dev/null
tpm2_nvdefine -C o -a "nt=counter|ownerread|ownerwrite" "$NV" >/dev/null
tpm2_nvread -C o -s 8 -o counter-reset.bin "$NV" >/dev/null
cmp -s counter-0.bin counter-reset.bin || fail "counter reset control not reproduced"
start_policy a counter-0.bin
sign_authorized a message-a.bin
pass "RED owner NV undefine/recreate restored stale policy eligibility"

printf 'R22_29_TPM_POLICY_SIMULATOR_COMPLETE RESEARCH_ONLY HOLD REAL_HARDWARE_NOT_TESTED ROOT_OWNER_CAN_RESET_NV\n'
