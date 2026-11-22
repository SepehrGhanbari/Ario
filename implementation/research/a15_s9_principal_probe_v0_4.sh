#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "S9 probe requires a privileged CI coordinator to provision disposable OS identities." >&2
  exit 77
fi
for command in useradd userdel groupadd groupdel runuser python3; do
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
created_group=0
created_gate_user=0
created_custodian_user=0

cleanup() {
  if [ -n "$service_pid" ]; then kill -KILL "$service_pid" 2>/dev/null || true; fi
  if [ "$created_gate_user" -eq 1 ]; then userdel "$gate_user" 2>/dev/null || true; fi
  if [ "$created_custodian_user" -eq 1 ]; then userdel "$custodian_user" 2>/dev/null || true; fi
  if [ "$created_group" -eq 1 ]; then groupdel "$reader_group" 2>/dev/null || true; fi
  if [ -n "$root_dir" ] && [[ "$root_dir" == /tmp/a15-s9-v04.* ]]; then rm -rf -- "$root_dir"; fi
}
trap cleanup EXIT

groupadd "$reader_group"
created_group=1
useradd --no-create-home --shell /usr/sbin/nologin --groups "$reader_group" "$gate_user"
created_gate_user=1
useradd --no-create-home --shell /usr/sbin/nologin "$custodian_user"
created_custodian_user=1

mkdir "$protected_dir"
chown "$custodian_user:$reader_group" "$protected_dir"
chmod 0711 "$root_dir"
chmod 0750 "$protected_dir"

cat > "$recorder_file" <<'RECORDER'
'use strict';
// Synthetic immutable service-image marker. This is not a production broker.
process.stdout.write('A15_CUSTODIAN_IMAGE_V04\n');
RECORDER
chown "$custodian_user:$reader_group" "$recorder_file"
chmod 0550 "$recorder_file"

printf '{"seq":1,"event":"GENESIS_SYNTHETIC"}\n' > "$ledger_file"
chown "$custodian_user:$custodian_user" "$ledger_file"
chmod 0600 "$ledger_file"

gate_uid="$(id -u "$gate_user")"
custodian_uid="$(id -u "$custodian_user")"
custodian_gid="$(id -g "$custodian_user")"
[ "$gate_uid" != "$custodian_uid" ] || { echo "FAIL: identities unexpectedly equal" >&2; exit 1; }

# The Gate process itself verifies its effective identity and performs every negative probe.
runuser -u "$gate_user" -- python3 - "$recorder_file" "$ledger_file" "$gate_uid" "$custodian_gid" <<'PY'
import errno
import json
import os
import signal
import sys

recorder, ledger, expected_uid, custodian_gid = sys.argv[1:]
expected_uid = int(expected_uid)
custodian_gid = int(custodian_gid)

if os.getuid() != expected_uid or os.geteuid() != expected_uid or expected_uid == 0:
    raise SystemExit("FAIL: Gate process did not run as the expected unprivileged UID")
if os.getegid() == custodian_gid or custodian_gid in os.getgroups():
    raise SystemExit("FAIL: Gate inherited the Custodian primary/supplementary group")

with open(recorder, "r", encoding="utf-8") as stream:
    image = stream.read()
if "A15_CUSTODIAN_IMAGE_V04" not in image:
    raise SystemExit("FAIL: Gate cannot read the installed service image")

def denied(label, action):
    try:
        action()
    except PermissionError as exc:
        if exc.errno not in (errno.EACCES, errno.EPERM):
            raise SystemExit(f"FAIL: {label} failed with unexpected permission errno {exc.errno}")
        return True
    except OSError as exc:
        raise SystemExit(f"FAIL: {label} failed for a non-permission reason: errno={exc.errno}") from exc
    raise SystemExit(f"FAIL: Gate unexpectedly succeeded at {label}")

def append_file(path, value):
    with open(path, "a", encoding="utf-8") as stream:
        stream.write(value)

denied("executable overwrite", lambda: append_file(recorder, "MALICIOUS_REPLACEMENT\n"))
denied("executable delete", lambda: os.unlink(recorder))
denied("executable chmod", lambda: os.chmod(recorder, 0o660))
denied("executable rename", lambda: os.rename(recorder, recorder + ".renamed"))
denied("ledger read", lambda: open(ledger, "r", encoding="utf-8").read())
denied("ledger append", lambda: append_file(ledger, "FORGED\n"))

print(json.dumps({
    "gate_uid": os.getuid(),
    "gate_euid": os.geteuid(),
    "gate_groups": os.getgroups(),
    "custodian_gid_excluded": True,
    "read_executable": True,
    "overwrite_denied": True,
    "delete_denied": True,
    "chmod_denied": True,
    "rename_denied": True,
    "ledger_read_denied": True,
    "ledger_append_denied": True
}, sort_keys=True))
PY

# Start a long-lived process under the distinct Custodian UID. Its PID survives exec.
touch "$pid_file"
chown "$custodian_user:$reader_group" "$pid_file"
chmod 0640 "$pid_file"
runuser -u "$custodian_user" -- sh -c 'echo $$ > "$1"; exec sleep 90' _ "$pid_file" &
launcher_pid=$!
for _ in $(seq 1 100); do
  [ -s "$pid_file" ] && break
  sleep 0.05
done
[ -s "$pid_file" ] || { echo "FAIL: Custodian process did not publish PID" >&2; exit 1; }
service_pid="$(cat "$pid_file")"
actual_uid="$(ps -o uid= -p "$service_pid" | tr -d ' ')"
[ "$actual_uid" = "$custodian_uid" ] || { echo "FAIL: service process is not Custodian UID" >&2; exit 1; }

# Probe process-signal denial from the Gate UID and require the exact EPERM outcome.
runuser -u "$gate_user" -- python3 - "$service_pid" "$gate_uid" "$custodian_gid" <<'PY'
import errno
import os
import signal
import sys

pid, expected_uid, custodian_gid = map(int, sys.argv[1:])
if os.getuid() != expected_uid or os.geteuid() != expected_uid or expected_uid == 0:
    raise SystemExit("FAIL: signal probe is not running as the Gate identity")
if os.getegid() == custodian_gid or custodian_gid in os.getgroups():
    raise SystemExit("FAIL: Gate has Custodian group membership")
try:
    os.kill(pid, signal.SIGTERM)
except PermissionError as exc:
    if exc.errno != errno.EPERM:
        raise SystemExit(f"FAIL: expected EPERM from kill, got errno={exc.errno}")
else:
    raise SystemExit("FAIL: Gate terminated the Custodian process")
print("GATE_SIGNAL_DENIED=EPERM")
PY
kill -0 "$service_pid" 2>/dev/null || { echo "FAIL: Custodian process did not survive Gate signal attempt" >&2; exit 1; }

# Positive control: Custodian can read its image and append its own ledger.
runuser -u "$custodian_user" -- python3 - "$recorder_file" "$ledger_file" "$custodian_uid" <<'PY'
import os
import sys
recorder, ledger, expected_uid = sys.argv[1:]
expected_uid = int(expected_uid)
if os.getuid() != expected_uid or os.geteuid() != expected_uid:
    raise SystemExit("FAIL: positive control is not running as Custodian UID")
with open(recorder, "r", encoding="utf-8") as stream:
    assert "A15_CUSTODIAN_IMAGE_V04" in stream.read()
with open(ledger, "a", encoding="utf-8") as stream:
    stream.write('{"seq":2,"event":"CUSTODIAN_WRITE"}\n')
print("CUSTODIAN_READ_IMAGE_AND_APPEND_LEDGER=PASS")
PY

grep -q 'CUSTODIAN_WRITE' "$ledger_file"
if runuser -u "$gate_user" -- python3 - "$ledger_file" <<'PY'
import sys
with open(sys.argv[1], "a", encoding="utf-8") as stream:
    stream.write("FORGED_AFTER_CUSTODIAN\n")
PY
then
  echo "FAIL: Gate wrote ledger after Custodian update" >&2; exit 1
else
  status=$?
  [ "$status" -eq 1 ] || { echo "FAIL: unexpected Gate ledger probe exit=$status" >&2; exit 1; }
fi

echo "S9_OS_PRINCIPAL_BOUNDARY=PASS"
echo "GATE_UID=$gate_uid"
echo "CUSTODIAN_UID=$custodian_uid"
echo "GATE_CAN_READ_EXECUTABLE=YES"
echo "GATE_CAN_WRITE_DELETE_CHMOD_RENAME_EXECUTABLE=NO"
echo "GATE_CAN_READ_OR_WRITE_LEDGER=NO"
echo "GATE_CAN_TERMINATE_CUSTODIAN_PROCESS=NO"
echo "SCOPE=LOCAL_OS_PRINCIPAL_ONLY_NOT_EXTERNAL_CUSTODY"
