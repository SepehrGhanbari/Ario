#!/usr/bin/env bash
# A15 v0.5 Linux SYNTHETIC end-to-end boundary exercise. Never installs a service or keys.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo 'requires disposable CI root coordinator' >&2; exit 2; }
broker_source="$(cd "$(dirname "$0")" && pwd)/a15_custodian_broker_v0_5.py"
python="$(command -v python3)"
root="$(mktemp -d /tmp/a15v05.XXXXXXXX)"
tag="$(printf 'a15v05%s' "$(basename "$root" | tr -cd 'a-z0-9')" | cut -c1-24)"
group="$(printf '%s' "$tag" | cut -c1-25)g"
gate="$(printf '%s' "$tag" | cut -c1-25)a"
cust="$(printf '%s' "$tag" | cut -c1-25)c"
made_group=0; made_gate=0; made_cust=0
service_launcher=''
cleanup() {
  set +e
  if [ "$made_cust" -eq 1 ]; then pkill -9 -u "$cust" 2>/dev/null || true; fi
  [ -n "$service_launcher" ] && kill "$service_launcher" 2>/dev/null || true
  [ "$made_gate" -eq 1 ] && userdel "$gate" 2>/dev/null || true
  [ "$made_cust" -eq 1 ] && userdel "$cust" 2>/dev/null || true
  [ "$made_group" -eq 1 ] && groupdel "$group" 2>/dev/null || true
  rm -rf -- "$root"
}
trap cleanup EXIT

getent group "$group" >/dev/null && { echo 'unexpected group collision' >&2; exit 2; }
getent passwd "$gate" >/dev/null && { echo 'unexpected gate collision' >&2; exit 2; }
getent passwd "$cust" >/dev/null && { echo 'unexpected custodian collision' >&2; exit 2; }
groupadd "$group"; made_group=1
useradd --no-create-home --shell /usr/sbin/nologin --groups "$group" "$gate"; made_gate=1
useradd --no-create-home --shell /usr/sbin/nologin --groups "$group" "$cust"; made_cust=1
gate_uid="$(id -u "$gate")"
cust_uid="$(id -u "$cust")"
gate_gid="$(getent group "$group" | cut -d: -f3)"
[ "$gate_uid" != "$cust_uid" ] && [ "$gate_uid" != 0 ] && [ "$cust_uid" != 0 ]

install="$root/install"; state="$root/state"; socket_path="$install/broker.sock"
mkdir "$install" "$state"; chmod 0755 "$root"
chown "$cust:$group" "$install"; chmod 0750 "$install"
chown "$cust:$cust" "$state"; chmod 0700 "$state"
cp "$broker_source" "$install/custodian.py"
chown "$cust:$group" "$install/custodian.py"; chmod 0550 "$install/custodian.py"

start_broker() {
  local crash="$1" target="$2"
  rm -f "$socket_path" # coordinator recovery only after previous process terminated
  if [ -n "$crash" ]; then
    env A15_V05_SYNTHETIC_CRASH_POINT="$crash" A15_V05_SYNTHETIC_CRASH_REQUEST_ID="$target" \
      runuser -u "$cust" -- "$python" "$install/custodian.py" serve \
      --socket "$socket_path" --state-dir "$state" --gate-uid "$gate_uid" --gate-gid "$gate_gid" \
      >> "$root/server.log" 2>&1 &
  else
    runuser -u "$cust" -- "$python" "$install/custodian.py" serve \
      --socket "$socket_path" --state-dir "$state" --gate-uid "$gate_uid" --gate-gid "$gate_gid" \
      >> "$root/server.log" 2>&1 &
  fi
  service_launcher="$!"
  for _ in $(seq 1 80); do
    [ -S "$socket_path" ] && return 0
    if ! kill -0 "$service_launcher" 2>/dev/null; then
      cat "$root/server.log" >&2
      echo 'broker failed before socket startup' >&2; exit 2
    fi
    sleep 0.05
  done
  cat "$root/server.log" >&2
  echo 'broker socket did not appear' >&2; exit 2
}
stop_broker() {
  pkill -9 -u "$cust" 2>/dev/null || true
  [ -n "$service_launcher" ] && kill "$service_launcher" 2>/dev/null || true
  wait "$service_launcher" 2>/dev/null || true
  service_launcher=''
  rm -f "$socket_path"
  sleep 0.1
}
make_request() {
  "$python" - "$1" <<'PY'
import json,sys
choice={"actor":"ARIO","role":"RESEARCH_DIALOGUE","origin":"CURRENT",
"explicit_renewal":False,"risk":"LOW","authorization":"ALLOWED",
"usefulness":"USEFUL","evidence":"SUFFICIENT","preference":"ACCEPT","duration":"BOUNDED"}
message={"v":1,"run_id":"RUN_V05_BOUNDARY","attempt_id":sys.argv[1],
"choice_json":json.dumps(choice,separators=(",",":")),"claimed_status":"ACCEPT"}
print(json.dumps(message,separators=(",",":")))
PY
}
gate_call() {
  printf '%s\n' "$1" | runuser -u "$gate" -- "$python" "$install/custodian.py" client --socket "$socket_path"
}
check_response() {
  local response="$1" status="$2" replay="$3" seq="$4"
  "$python" -c 'import json,sys; r=json.loads(sys.argv[1]); assert r["status"]==sys.argv[2], r; assert r["replayed"]==(sys.argv[3]=="true"),r; assert r["seq"]==int(sys.argv[4]),r; assert r["execution_authorized"] is False; assert r["independent_custody"]=="NOT_ESTABLISHED"; assert r["origin_attested"] is False' \
    "$response" "$status" "$replay" "$seq"
}

start_broker '' ''
first="$(make_request ATT_V05_FIRST)"
check_response "$(gate_call "$first")" INERT_RECORDED_UNATTESTED_ORIGIN false 1
check_response "$(gate_call "$first")" REPLAY_DURABLE_LOCAL_RECEIPT_ONLY true 1

# Kernel file permissions: Gate cannot read/change private state or replace the broker image.
runuser -u "$gate" -- "$python" - "$state" "$install/custodian.py" <<'PY'
import errno,os,sys
state,image=sys.argv[1:]
for name,attempt in (
 ("ledger-read",lambda:open(os.path.join(state,"custodian.sqlite3"),"rb").read()),
 ("ledger-append",lambda:open(os.path.join(state,"custodian.sqlite3"),"ab").write(b"FORGED")),
 ("image-overwrite",lambda:open(image,"ab").write(b"FORGED")),
 ("image-delete",lambda:os.unlink(image)),
 ("image-chmod",lambda:os.chmod(image,0o777)),
 ("image-rename",lambda:os.rename(image,image+".changed"))
):
 try:attempt()
 except PermissionError as exc:
  assert exc.errno in (errno.EACCES,errno.EPERM),name
 else:raise SystemExit("GATE_BOUNDARY_BYPASSED:"+name)
print("GATE_LEDGER_AND_IMAGE_DENIALS=PASS")
PY

# Crash with a live transaction. On restart, request was not consumed.
stop_broker
before="$(make_request ATT_V05_BEFORE)"
start_broker BEFORE_COMMIT 'RUN_V05_BOUNDARY|ATT_V05_BEFORE'
gate_call "$before" >/dev/null 2>&1 || true
sleep 0.2
stop_broker
start_broker '' ''
check_response "$(gate_call "$before")" INERT_RECORDED_UNATTESTED_ORIGIN false 2

# Crash after full SQLite commit, before reply. Retry recovers previous receipt.
stop_broker
after="$(make_request ATT_V05_AFTER)"
start_broker AFTER_COMMIT_BEFORE_REPLY 'RUN_V05_BOUNDARY|ATT_V05_AFTER'
gate_call "$after" >/dev/null 2>&1 || true
sleep 0.2
stop_broker
start_broker '' ''
check_response "$(gate_call "$after")" REPLAY_DURABLE_LOCAL_RECEIPT_ONLY true 3

# Concurrent duplicate: one row, one replay, neither execution nor provider send.
parallel="$(make_request ATT_V05_PARALLEL)"
printf '%s\n' "$parallel" | runuser -u "$gate" -- "$python" "$install/custodian.py" client --socket "$socket_path" > "$root/response1" &
client1=$!
printf '%s\n' "$parallel" | runuser -u "$gate" -- "$python" "$install/custodian.py" client --socket "$socket_path" > "$root/response2" &
client2=$!
wait "$client1"; wait "$client2"
"$python" - "$root/response1" "$root/response2" <<'PY'
import json,sys
with open(sys.argv[1]) as fa, open(sys.argv[2]) as fb:
 a,b=json.load(fa),json.load(fb)
assert [a["seq"],b["seq"]]==[4,4]
assert sorted([a["replayed"],b["replayed"]])==[False,True]
assert {a["status"],b["status"]}=={"INERT_RECORDED_UNATTESTED_ORIGIN","REPLAY_DURABLE_LOCAL_RECEIPT_ONLY"}
print("CONCURRENT_SINGLE_DURABLE_CONSUMPTION=PASS")
PY
echo "A15_V05_LINUX_OS_SEPARATED_BROKER=PASS"
echo "GATE_UID=$gate_uid CUSTODIAN_UID=$cust_uid"
echo "CRASH_RECOVERY=PASS LOST_REPLY_IDEMPOTENCE=PASS"
echo "INDEPENDENT_EXTERNAL_CUSTODY=NOT_ESTABLISHED"
echo "WINDOWS_AUTHENTICATED_IPC=NOT_IMPLEMENTED"
