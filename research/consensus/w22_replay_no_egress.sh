#!/usr/bin/env bash
# W22 no-network reproducibility: Python 9 methods + Go stdlib note verifier
# + author-selected 11 mutations. DOES NOT publish or create real Ario keys.
set -euo pipefail
cd "$(dirname "$0")"
export GOTOOLCHAIN=local GOPROXY=off GO111MODULE=off
python -W error::ResourceWarning -B -m unittest -v test_w22_checkpoint_interop.py
python -B w22_selected_mutation_audit.py > W22_SELECTED_MUTATION_REPLAY.json
python - <<'PY'
import json
r=json.load(open('W22_SELECTED_MUTATION_REPLAY.json'))
assert r['selected']==11 and r['detected']==11 and not r['survivors'],r
print('W22_SELECTED_MUTANTS=11/11_Detected (author-selected only)')
PY
origin='ario-w22-research.invalid/synthetic-log'
oldroot='75083d7695c5844879981e3f066c1bddb7d77cebd4e3e9aa71e43aed0a0d3f21'
newroot='fe85584d081e74fadc9fa050c7cf1e29c1bc02639407bff9bd4b78b35bdcb392'
go run w22_note_go_check.go -vkey-file W22_PUBLIC_LOG_VERIFIER.vkey -note-file W22_PREVIOUS_CHECKPOINT.note -origin "$origin" -size 3 -root "$oldroot"
go run w22_note_go_check.go -vkey-file W22_PUBLIC_LOG_VERIFIER.vkey -note-file W22_CURRENT_CHECKPOINT.note -origin "$origin" -size 8 -root "$newroot"
tampered="$(mktemp)"
trap 'rm -f -- "$tampered"' EXIT
python - "$tampered" <<'PY'
import pathlib,sys
p=pathlib.Path('W22_CURRENT_CHECKPOINT.note')
s=p.read_bytes().replace(b'\n8\n',b'\n08\n',1)
assert s!=p.read_bytes()
pathlib.Path(sys.argv[1]).write_bytes(s)
PY
if go run w22_note_go_check.go -vkey-file W22_PUBLIC_LOG_VERIFIER.vkey -note-file "$tampered" -origin "$origin" -size 8 -root "$newroot" >/dev/null 2>&1; then
  echo 'W22_SECURITY_FAIL: malformed checkpoint unexpectedly accepted' >&2
  exit 1
fi
echo 'W22_GO_REJECTS_MALFORMED_SIZE_AND_VALIDATES_BOTH_C2SP_NOTES'
echo 'W22_REPLAY_PASS / HISTORICAL_ONLY / INDEPENDENT_ADMIN=NOT_ESTABLISHED / REAL_ARIO_LOG_WITNESS=NO / NO_AUTOMATION'
