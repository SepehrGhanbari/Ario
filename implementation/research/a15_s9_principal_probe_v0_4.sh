#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "S9 probe requires a privileged CI coordinator to provision disposable OS identities." >&2
  exit 77
fi
for command in useradd userdel groupadd groupdel runuser; do
  command -v "$command" >/dev/null || { echo "MISSING_TOOL:$command" >&2; exit 78; }
done

suffix="$$"
gate_user="a15s9g$suffix"
custodian_user="a15s9c$suffix"
reader_group="a15s9r$suffix"
root_dir="$(mktemp -d /tmp/a15-s9-v04.XXXXXX)"
protected_dir="$root_dir/protected"
recorder_file="$protected_dir/recorder.js"
ledger_file="$protected_dir/ledger.jsonl"
pid_file="$root_dir/custodian.pid"
service_pid=""

cleanup() {
  if [ -n "$service_pid" ]; then kill -KILL "$service_pid" 2>/dev/null || true; fi
  if id "$gate_user" >/dev/null 2>&1; then userdel "$gate_user" 2>/dev/null || true; fi
  if id "$custodian_user" >/dev/null 2>&1; then userdel "$custodian_user" 2>/dev/null || true; fi
  if getent group "$reader_group" >/dev/null 2>&1; then groupdel "$reader_group" 2>/dev/null || true; fi
  rm -rf "$root_dir"
}
trap cleanup EXIT

groupadd "$reader_group"
useradd --no-create-home --shell /usr/sbin/nologin --groups "$reader_group" "$gate_user"
useradd --no-create-home --shell /usr/sbin/nologin "$custodian_user"

mkdir "$protected_dir"
chown "$custodian_user:$reader_group" "$protected_dir"
chmod 0711 "$root_dir"
chmod 0750 "$protected_dir"

cat > "$recorder_file" <<'RECORDER'
'use strict';
// Synthetic immutable service image marker. This is not a production broker.
process.stdout.write('A15_CUSTODIAN_IMAGE_V04\n');
RECORDER
chown "$custodian_user:$reader_group" "$recorder_file"
chmod 0440 "$recorder_file"

printf '{"seq":1,"event":"GENESIS_SYNTHETIC"}\n' > "$ledger_file"
chown "$custodian_user:$custodian_user" "$ledger_file"
chmod 0600 "$ledger_file"

gate_uid="$(id -u "$gate_user")"
custodian_uid="$(id -u "$custodian_user")"
[ "$gate_uid" != "$custodian_uid" ] || { echo "FAIL: identities unexpectedly equal" >&2; exit 1; }

# Positive control: Gate may read/execute the installed service image, but not alter it.
runuser -u "$gate_user" -- cat "$recorder_file" >/dev/null
before="$(sha256sum "$recorder_file" | awk '{print $1}')"

if runuser -u "$gate_user" -- sh -c 'printf "MALICIOUS_REPLACEMENT\n" >> "$1"' _ "$recorder_file" 2>/dev/null; then
  echo "FAIL: Gate appended to custodian-owned executable" >&2; exit 1
fi
if runuser -u "$gate_user" -- rm -f "$recorder_file" 2>/dev/null; then
  echo "FAIL: Gate deleted custodian-owned executable" >&2; exit 1
fi
after="$(sha256sum "$recorder_file" | awk '{print $1}')"
[ "$before" = "$after" ] || { echo "FAIL: protected executable changed" >&2; exit 1; }

# Gate must not read or write the custodian-only ledger.
if runuser -u "$gate_user" -- cat "$ledger_file" >/dev/null 2>&1; then
  echo "FAIL: Gate read private custodian ledger" >&2; exit 1
fi
if runuser -u "$gate_user" -- sh -c 'printf "FORGED\n" >> "$1"' _ "$ledger_file" 2>/dev/null; then
  echo "FAIL: Gate wrote private custodian ledger" >&2; exit 1
fi

# Start a long-lived process under the distinct custodian UID. Its PID is retained across exec.
touch "$pid_file"
chown "$custodian_user:$reader_group" "$pid_file"
chmod 0640 "$pid_file"
runuser -u "$custodian_user" -- sh -c 'echo $$ > "$1"; exec sleep 90' _ "$pid_file" &
launcher_pid=$!
for _ in $(seq 1 100); do
  [ -s "$pid_file" ] && break
  sleep 0.05
done
[ -s "$pid_file" ] || { echo "FAIL: custodian process did not publish PID" >&2; exit 1; }
service_pid="$(cat "$pid_file")"
actual_uid="$(ps -o uid= -p "$service_pid" | tr -d ' ')"
[ "$actual_uid" = "$custodian_uid" ] || { echo "FAIL: service process is not custodian UID" >&2; exit 1; }

# Negative control: Gate cannot terminate a process owned by the custodian identity.
if runuser -u "$gate_user" -- kill -TERM "$service_pid" 2>/dev/null; then
  echo "FAIL: Gate terminated custodian process" >&2; exit 1
fi
kill -0 "$service_pid" 2>/dev/null || { echo "FAIL: custodian process did not survive Gate kill attempt" >&2; exit 1; }

# Positive control: the custodian can append its own ledger; Gate still cannot.
runuser -u "$custodian_user" -- sh -c 'printf "{\"seq\":2,\"event\":\"CUSTODIAN_WRITE\"}\n" >> "$1"' _ "$ledger_file"
if runuser -u "$gate_user" -- sh -c 'printf "FORGED\n" >> "$1"' _ "$ledger_file" 2>/dev/null; then
  echo "FAIL: Gate wrote ledger after custodian update" >&2; exit 1
fi

echo "S9_OS_PRINCIPAL_BOUNDARY=PASS"
echo "GATE_UID=$gate_uid"
echo "CUSTODIAN_UID=$custodian_uid"
echo "GATE_CAN_READ_EXECUTABLE=YES"
echo "GATE_CAN_WRITE_OR_DELETE_EXECUTABLE=NO"
echo "GATE_CAN_READ_OR_WRITE_LEDGER=NO"
echo "GATE_CAN_TERMINATE_CUSTODIAN_PROCESS=NO"
echo "SCOPE=LOCAL_OS_PRINCIPAL_ONLY_NOT_EXTERNAL_CUSTODY"
