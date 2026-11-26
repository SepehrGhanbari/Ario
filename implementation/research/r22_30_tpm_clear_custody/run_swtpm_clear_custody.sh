#!/usr/bin/env bash
set -euo pipefail

TMP="$(mktemp -d)"
STATE1="$TMP/tpm-state-1"
STATE2="$TMP/tpm-state-2"
SHARED="$TMP/shared"
CUSTODIAN_HOME="$TMP/custodian"
mkdir -p "$STATE1" "$STATE2" "$SHARED" "$CUSTODIAN_HOME"
# Allow traversal to the custodian-owned 0700 subdirectory without listing TMP.
chmod 711 "$TMP"
SWTPM_PIDS=()
cleanup() {
  for pid in "\${SWTPM_PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  done
  if id ario-custodian >/dev/null 2>&1; then sudo userdel ario-custodian >/dev/null 2>&1 || true; fi
  if getent group ario-custodian >/dev/null 2>&1; then sudo groupdel ario-custodian >/dev/null 2>&1 || true; fi
  sudo rm -rf -- "$TMP"
}
trap cleanup EXIT

OWNER_NV="0x01500017"
PLATFORM_NV="0x01500018"
OWNER_AUTH="ario-owner-before-clear"
PLATFORM_AUTH="ario-platform-lab-only"
LOCKOUT_AUTH="ario-lockout-lab-only"
ENDORSEMENT_AUTH="ario-endorsement-before-clear"
HEAD_SHA256="$(printf 'Ario synthetic last-confirmed checkpoint R22.30\n' | sha256sum | awk '{print $1}')"

pass(){ printf 'PASS %s\n' "$1"; }
fail(){ printf 'FAIL %s\n' "$1"; exit 1; }
expect_fail(){
  local label="$1"; shift
  if "$@" >"$TMP/negative.out" 2>&1; then
    cat "$TMP/negative.out"; fail "$label (unexpected success)"
  fi
  pass "$label"
}
expect_reject(){
  local label="$1" code="$2" request="$3" response="$4"
  if sudo -u ario-custodian -- python3 "$SHARED/custodian_gate.py" \
      --anchor "$CUSTODIAN_HOME/anchor.json" --anchor-signature "$CUSTODIAN_HOME/anchor.sig" \
      --public-key "$SHARED/custodian.pub" --private-key "$CUSTODIAN_HOME/custodian.key" \
      --nonce-ledger "$CUSTODIAN_HOME/consumed_nonces.jsonl" \
      --request "$request" --response "$response" >"$TMP/reject.out" 2>&1; then
    cat "$TMP/reject.out"; fail "$label (unexpected approval)"
  fi
  if ! grep -Fq "REJECT $code" "$TMP/reject.out"; then
    cat "$TMP/reject.out"; fail "$label (wrong rejection reason)"
  fi
  pass "$label"
}
start_tpm(){
  local state="$1" port="$2" ctrl="$3"
  swtpm socket --tpm2 --tpmstate "dir=$state" \
    --server "type=tcp,port=$port" --ctrl "type=tcp,port=$ctrl" \
    --flags startup-clear >"$TMP/swtpm-$port.log" 2>&1 &
  SWTPM_PIDS+=("$!")
  export TPM2TOOLS_TCTI="swtpm:host=127.0.0.1,port=$port"
  for _ in $(seq 1 100); do
    if tpm2_getrandom 8 >/dev/null 2>&1; then return 0; fi
    sleep 0.1
  done
  cat "$TMP/swtpm-$port.log"
  fail "swtpm startup on port $port"
}
pub_fingerprint(){
  openssl pkey -pubin -in "$1" -outform DER 2>/dev/null | sha256sum | awk '{print $1}'
}
make_request(){
  local path="$1" ek="$2" srk="$3" prev="$4" next="$5" head="$6" reason="$7" nonce="$8"
  python3 - "$path" "$ek" "$srk" "$prev" "$next" "$head" "$reason" "$nonce" <<'PY'
import json,sys
path,ek,srk,prev,nxt,head,reason,nonce=sys.argv[1:]
obj={
 "device_ek_sha256":ek,
 "storage_root_sha256":srk,
 "previous_epoch":int(prev),
 "next_epoch":int(nxt),
 "previous_head_sha256":head,
 "reason":reason,
 "nonce":nonce,
}
with open(path,"w",encoding="utf-8",newline="\n") as f:
    json.dump(obj,f,sort_keys=True,separators=(",",":"))
    f.write("\n")
PY
}

tpm2 --version | head -n 1
swtpm --version | head -n 1
start_tpm "$STATE1" 2321 2322
pass "first software TPM initialized"

# Configure distinct hierarchy authorizations for the synthetic device.
tpm2_changeauth -c p "$PLATFORM_AUTH" >/dev/null
tpm2_changeauth -c o "$OWNER_AUTH" >/dev/null
tpm2_changeauth -c l "$LOCKOUT_AUTH" >/dev/null
tpm2_changeauth -c e "$ENDORSEMENT_AUTH" >/dev/null

# Two NV indices deliberately use different creation hierarchies.
tpm2_nvdefine -C o -P "$OWNER_AUTH" -a "nt=counter|ownerread|ownerwrite" "$OWNER_NV" >/dev/null
tpm2_nvincrement -C o -P "$OWNER_AUTH" "$OWNER_NV" >/dev/null
tpm2_nvread -C o -P "$OWNER_AUTH" -s 8 -o "$TMP/owner-before.bin" "$OWNER_NV" >/dev/null

tpm2_nvdefine -C p -P "$PLATFORM_AUTH" -a "nt=counter|platformcreate|ppread|ppwrite" "$PLATFORM_NV" >/dev/null
tpm2_nvincrement -C p -P "$PLATFORM_AUTH" "$PLATFORM_NV" >/dev/null
tpm2_nvread -C p -P "$PLATFORM_AUTH" -s 8 -o "$TMP/platform-before.bin" "$PLATFORM_NV" >/dev/null
pass "owner-created and platform-created NV counters initialized separately"

# EK identity derives from EPS; the storage primary key derives from SPS.
tpm2_createek -P "$ENDORSEMENT_AUTH" -G rsa -c "$TMP/ek-before.ctx" -u "$TMP/ek-before.pub" >/dev/null
tpm2_readpublic -c "$TMP/ek-before.ctx" -f pem -o "$TMP/ek-before.pem" >/dev/null
EK_BEFORE="$(pub_fingerprint "$TMP/ek-before.pem")"
tpm2_flushcontext -t >/dev/null
tpm2_createprimary -C o -P "$OWNER_AUTH" -G ecc -g sha256 -c "$TMP/srk-before.ctx" >/dev/null
tpm2_readpublic -c "$TMP/srk-before.ctx" -f pem -o "$TMP/srk-before.pem" >/dev/null
SRK_BEFORE="$(pub_fingerprint "$TMP/srk-before.pem")"
pass "pre-clear EK identity and storage-root fingerprints captured"

# The lockout hierarchy cannot clear while disableClear is set.
tpm2_clearcontrol -C l -P "$LOCKOUT_AUTH" s >/dev/null
expect_fail "lockout-authorized TPM_Clear blocked by disableClear" tpm2_clear -c l "$LOCKOUT_AUTH"
# Platform authority can re-enable TPM_Clear. This is intentionally not claimed
# to be protected from the platform/firmware administrator.
tpm2_clearcontrol -C p -P "$PLATFORM_AUTH" c >/dev/null
pass "platform authority can re-enable TPM_Clear"

# TPM_Clear is a destructive hierarchy transition; no Ario signer is connected.
tpm2_clear -c p "$PLATFORM_AUTH" >/dev/null
pass "platform-authorized TPM_Clear executed"

# TCG v185: Clear changes SPS, resets Owner/Endorsement/Lockout auth, removes
# non-platform-created NV indices, but does not replace EPS or platform NV.
tpm2_createek -G rsa -c "$TMP/ek-after.ctx" -u "$TMP/ek-after.pub" >/dev/null
tpm2_readpublic -c "$TMP/ek-after.ctx" -f pem -o "$TMP/ek-after.pem" >/dev/null
EK_AFTER="$(pub_fingerprint "$TMP/ek-after.pem")"
tpm2_flushcontext -t >/dev/null
[[ "$EK_BEFORE" == "$EK_AFTER" ]] || fail "EK identity unexpectedly changed across TPM_Clear"
pass "EK identity remains stable across owner TPM_Clear"

tpm2_createprimary -C o -G ecc -g sha256 -c "$TMP/srk-after.ctx" >/dev/null
tpm2_readpublic -c "$TMP/srk-after.ctx" -f pem -o "$TMP/srk-after.pem" >/dev/null
SRK_AFTER="$(pub_fingerprint "$TMP/srk-after.pem")"
[[ "$SRK_BEFORE" != "$SRK_AFTER" ]] || fail "storage primary key did not change across TPM_Clear"
pass "storage-root identity changed across TPM_Clear"

expect_fail "pre-clear storage-root context invalidated" \
  tpm2_readpublic -c "$TMP/srk-before.ctx" -f pem -o "$TMP/old-srk-after.pem"
expect_fail "owner-created NV index removed by TPM_Clear" \
  tpm2_nvread -C o -s 8 -o "$TMP/owner-after.bin" "$OWNER_NV"

tpm2_nvread -C p -P "$PLATFORM_AUTH" -s 8 -o "$TMP/platform-after.bin" "$PLATFORM_NV" >/dev/null
cmp -s "$TMP/platform-before.bin" "$TMP/platform-after.bin" || fail "platform-created NV index did not survive TPM_Clear"
pass "platform-created NV index and counter survive TPM_Clear"

expect_fail "old owner authorization rejected after TPM_Clear" \
  tpm2_changeauth -c o -p "$OWNER_AUTH" ario-owner-after-clear
tpm2_changeauth -c o ario-owner-after-clear >/dev/null
expect_fail "old endorsement authorization rejected after TPM_Clear" \
  tpm2_createek -P "$ENDORSEMENT_AUTH" -G rsa -c "$TMP/ek-old-auth.ctx"
expect_fail "old lockout authorization rejected after TPM_Clear" \
  tpm2_changeauth -c l -p "$LOCKOUT_AUTH" ario-lockout-after-clear
pass "owner, endorsement and lockout authorization reset behavior verified"

# A second fresh swtpm state models a replacement TPM. Its EK must differ.
start_tpm "$STATE2" 2323 2324
tpm2_createek -G rsa -c "$TMP/ek-replacement.ctx" -u "$TMP/ek-replacement.pub" >/dev/null
tpm2_readpublic -c "$TMP/ek-replacement.ctx" -f pem -o "$TMP/ek-replacement.pem" >/dev/null
EK_REPLACEMENT="$(pub_fingerprint "$TMP/ek-replacement.pem")"
tpm2_flushcontext -t >/dev/null
[[ "$EK_REPLACEMENT" != "$EK_BEFORE" ]] || fail "replacement simulator reused original EK identity"
tpm2_createprimary -C o -G ecc -g sha256 -c "$TMP/srk-replacement.ctx" >/dev/null
tpm2_readpublic -c "$TMP/srk-replacement.ctx" -f pem -o "$TMP/srk-replacement.pem" >/dev/null
SRK_REPLACEMENT="$(pub_fingerprint "$TMP/srk-replacement.pem")"
pass "replacement TPM presents a different EK identity"

# Build a narrowly scoped, separate-UID custodian model. This is NOT an
# independently administered custodian: the CI runner's root can still read it.
if getent passwd ario-custodian >/dev/null 2>&1; then sudo userdel ario-custodian >/dev/null 2>&1 || true; fi
if getent group ario-custodian >/dev/null 2>&1; then sudo groupdel ario-custodian >/dev/null 2>&1 || true; fi
sudo groupadd --system ario-custodian
sudo useradd --system --no-create-home --gid ario-custodian --home-dir "$CUSTODIAN_HOME" --shell /usr/sbin/nologin ario-custodian
sudo chown ario-custodian:ario-custodian "$CUSTODIAN_HOME"
sudo chmod 700 "$CUSTODIAN_HOME"
pass "separate custodian UID and private home created"
sudo -u ario-custodian -- openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
  -out "$CUSTODIAN_HOME/custodian.key" >/dev/null 2>&1
pass "custodian private key generated under custodian UID"
sudo -u ario-custodian -- openssl pkey -in "$CUSTODIAN_HOME/custodian.key" -pubout \
  -out "$CUSTODIAN_HOME/custodian.pub" >/dev/null 2>&1
sudo cp "$CUSTODIAN_HOME/custodian.pub" "$SHARED/custodian.pub"
sudo chmod 644 "$SHARED/custodian.pub"
pass "custodian public key exported read-only to publisher"

cat > "$SHARED/custodian_gate.py" <<'PY'
#!/usr/bin/env python3
import argparse, hashlib, json, os, re, subprocess, sys
from pathlib import Path
p=argparse.ArgumentParser()
for n in ("anchor","anchor_signature","public_key","private_key","nonce_ledger","request","response"):
    p.add_argument("--"+n.replace("_","-"),required=True)
a=p.parse_args()
def reject(code):
    print("REJECT "+code)
    raise SystemExit(3)
def canonical(obj):
    return (json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()
try:
    subprocess.run(["openssl","dgst","-sha256","-verify",a.public_key,
        "-signature",a.anchor_signature,a.anchor],check=True,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
except subprocess.CalledProcessError:
    reject("ANCHOR_SIGNATURE_INVALID")
anchor=json.loads(Path(a.anchor).read_text())
req=json.loads(Path(a.request).read_text())
if req.get("device_ek_sha256") != anchor.get("device_ek_sha256"):
    reject("DEVICE_IDENTITY_MISMATCH")
if req.get("previous_epoch") != anchor.get("epoch") or req.get("next_epoch") != anchor.get("epoch")+1:
    reject("EPOCH_STEP_INVALID")
if req.get("previous_head_sha256") != anchor.get("head_sha256"):
    reject("PREVIOUS_HEAD_MISMATCH")
if req.get("reason") != "TPM_CLEAR_RECOVERY":
    reject("UNEXPECTED_RECOVERY_REASON")
if req.get("storage_root_sha256") == anchor.get("storage_root_sha256"):
    reject("RESET_NOT_PROVEN")
nonce=req.get("nonce","")
if not re.fullmatch(r"[0-9a-f]{64}",nonce):
    reject("NONCE_FORMAT_INVALID")
ledger=Path(a.nonce_ledger)
if ledger.exists():
    for line in ledger.read_text().splitlines():
        try:
            if json.loads(line).get("nonce")==nonce:
                reject("NONCE_REPLAY")
        except json.JSONDecodeError:
            reject("NONCE_LEDGER_CORRUPT")
entry={"nonce":nonce,"request_sha256":hashlib.sha256(canonical(req)).hexdigest()}
with ledger.open("a",encoding="utf-8") as f:
    f.write(json.dumps(entry,sort_keys=True,separators=(",",":"))+"\n")
    f.flush()
    os.fsync(f.fileno())
response={
 "decision":"APPROVED_EXPLICIT_RECOVERY",
 "device_ek_sha256":req["device_ek_sha256"],
 "new_storage_root_sha256":req["storage_root_sha256"],
 "previous_head_sha256":req["previous_head_sha256"],
 "next_epoch":req["next_epoch"],
 "request_sha256":entry["request_sha256"],
 "policy":"R22.30_SIMULATED_CUSTODIAN_V1",
}
Path(a.response).write_bytes(canonical(response))
subprocess.run(["openssl","dgst","-sha256","-sign",a.private_key,
    "-out",a.response+".sig",a.response],check=True,
    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
print("APPROVED EXPLICIT_RECOVERY epoch="+str(req["next_epoch"]))
PY
chmod 755 "$SHARED/custodian_gate.py"

# Initial anchor enrollment is performed by the custodian UID.
python3 - "$SHARED/anchor.json" "$EK_BEFORE" "$SRK_BEFORE" "$HEAD_SHA256" <<'PY'
import json,sys
path,ek,srk,head=sys.argv[1:]
obj={"device_ek_sha256":ek,"storage_root_sha256":srk,"epoch":7,"head_sha256":head}
with open(path,"w",encoding="utf-8",newline="\n") as f:
    json.dump(obj,f,sort_keys=True,separators=(",",":")); f.write("\n")
PY
sudo install -o ario-custodian -g ario-custodian -m 600 \
  "$SHARED/anchor.json" "$CUSTODIAN_HOME/anchor.json"
sudo -u ario-custodian -- openssl dgst -sha256 -sign "$CUSTODIAN_HOME/custodian.key" \
  -out "$CUSTODIAN_HOME/anchor.sig" "$CUSTODIAN_HOME/anchor.json" >/dev/null 2>&1
sudo chmod 600 "$CUSTODIAN_HOME/anchor.sig"
pass "custodian enrolled signed device, storage-root, epoch and checkpoint anchor"

if cat "$CUSTODIAN_HOME/custodian.key" >/dev/null 2>&1; then
  fail "publisher UID unexpectedly read custodian private key"
fi
pass "publisher UID cannot directly read custodian private key"
sudo cat "$CUSTODIAN_HOME/custodian.key" >/dev/null
printf 'RED runner-root can read custodian private key; UID split is not independent custody\n'

# Same TPM EK + changed SPS-derived storage root requires explicit recovery,
# a one-step epoch advance, the exact previous head and a one-use nonce.
NONCE="$(openssl rand -hex 32)"
make_request "$SHARED/recovery-request.json" "$EK_AFTER" "$SRK_AFTER" 7 8 \
  "$HEAD_SHA256" TPM_CLEAR_RECOVERY "$NONCE"
sudo -u ario-custodian -- python3 "$SHARED/custodian_gate.py" \
  --anchor "$CUSTODIAN_HOME/anchor.json" --anchor-signature "$CUSTODIAN_HOME/anchor.sig" \
  --public-key "$SHARED/custodian.pub" --private-key "$CUSTODIAN_HOME/custodian.key" \
  --nonce-ledger "$CUSTODIAN_HOME/consumed_nonces.jsonl" \
  --request "$SHARED/recovery-request.json" --response "$SHARED/recovery-response.json" \
  >"$TMP/approval.out"
grep -Fq "APPROVED EXPLICIT_RECOVERY epoch=8" "$TMP/approval.out" || fail "custodian recovery approval missing"
openssl dgst -sha256 -verify "$SHARED/custodian.pub" \
  -signature "$SHARED/recovery-response.json.sig" "$SHARED/recovery-response.json" >/dev/null 2>&1 \
  || fail "custodian recovery response signature invalid"
python3 - "$SHARED/recovery-response.json" "$EK_AFTER" "$SRK_AFTER" "$HEAD_SHA256" <<'PY'
import json,sys
obj=json.load(open(sys.argv[1],encoding="utf-8"))
assert obj["decision"]=="APPROVED_EXPLICIT_RECOVERY"
assert obj["device_ek_sha256"]==sys.argv[2]
assert obj["new_storage_root_sha256"]==sys.argv[3]
assert obj["previous_head_sha256"]==sys.argv[4]
assert obj["next_epoch"]==8
PY
pass "same-device TPM_Clear requires and receives signed epoch-8 recovery approval"

expect_reject "custodian rejects replayed recovery nonce" NONCE_REPLAY \
  "$SHARED/recovery-request.json" "$SHARED/replay-response.json"

make_request "$SHARED/replacement-request.json" "$EK_REPLACEMENT" "$SRK_REPLACEMENT" 7 8 \
  "$HEAD_SHA256" TPM_CLEAR_RECOVERY "$(openssl rand -hex 32)"
expect_reject "custodian rejects replacement TPM identity" DEVICE_IDENTITY_MISMATCH \
  "$SHARED/replacement-request.json" "$SHARED/replacement-response.json"

make_request "$SHARED/skipped-epoch-request.json" "$EK_AFTER" "$SRK_AFTER" 7 9 \
  "$HEAD_SHA256" TPM_CLEAR_RECOVERY "$(openssl rand -hex 32)"
expect_reject "custodian rejects skipped epoch" EPOCH_STEP_INVALID \
  "$SHARED/skipped-epoch-request.json" "$SHARED/skipped-epoch-response.json"

make_request "$SHARED/stale-head-request.json" "$EK_AFTER" "$SRK_AFTER" 7 8 \
  "$(printf 'stale checkpoint' | sha256sum | awk '{print $1}')" TPM_CLEAR_RECOVERY "$(openssl rand -hex 32)"
expect_reject "custodian rejects stale previous checkpoint" PREVIOUS_HEAD_MISMATCH \
  "$SHARED/stale-head-request.json" "$SHARED/stale-head-response.json"

make_request "$SHARED/no-reset-request.json" "$EK_AFTER" "$SRK_BEFORE" 7 8 \
  "$HEAD_SHA256" TPM_CLEAR_RECOVERY "$(openssl rand -hex 32)"
expect_reject "custodian rejects unchanged storage-root identity" RESET_NOT_PROVEN \
  "$SHARED/no-reset-request.json" "$SHARED/no-reset-response.json"

printf 'R22_30_TPM_CLEAR_CUSTODY_COMPLETE RESEARCH_ONLY HOLD HARDWARE_NOT_TESTED INDEPENDENT_CUSTODY_NOT_ESTABLISHED ROOT_CAN_BYPASS_UID\n'
