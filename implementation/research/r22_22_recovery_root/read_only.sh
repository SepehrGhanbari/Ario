#!/usr/bin/env bash
# Public synthetic, read-only; run in disposable Linux/WSL with Python 3.13 and Go 1.25.
set -euo pipefail
cd -- "$(dirname -- "$0")"
ROOT="$PWD"
export PYTHONDONTWRITEBYTECODE=1
umask 077
test "$#" = 1
OUT="$(realpath -m "$1")"
test ! -e "$OUT"
python3 - <<'PY'
import hashlib,json,pathlib,sys
assert sys.version_info[:2]==(3,13), "requires Python 3.13"
p=json.load(open('RECOVERY_PIN.json'))
assert p['trust_activation']==p['production']=='NO_GO'
for name,want in p['source_git_blobs'].items():
    b=pathlib.Path(name).read_bytes()
    got=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
    assert got==want,(name,'HOLD_SOURCE_PIN')
print('SIX_ORIGINAL_SOURCE_BLOBS_MATCH')
PY
mkdir -p "$OUT"
python3 -m venv "$OUT/venv"
"$OUT/venv/bin/python" -m pip install --disable-pip-version-check coincurve==21.0.0 websockets==15.0.1
GOBIN="$OUT/bin" go install sigsum.org/sigsum-go/cmd/sigsum-verify@v0.14.1
PY="$OUT/venv/bin/python"
ID="$("$PY" -c 'import json;print(json.load(open("RECOVERY_PIN.json"))["capsule_id"])')"
"$PY" r22_21_bootstrap_capsule/capsule.py recover "$ID" "$OUT/first" | tee "$OUT/bootstrap.jsonl"
F="$OUT/first"
"$OUT/bin/sigsum-verify" -k "$F/historical-log.pub" -P sigsum-test1-2025 "$F/historical-first.proof" < "$F/historical-first-id.txt"
"$OUT/bin/sigsum-verify" -k "$F/sigsum.pub" -P sigsum-test1-2025 "$F/event-id.txt.proof" < "$F/event-id.txt"
mkdir "$OUT/scanner"
cp r22_10_blind_discovery/{main.go,main_test.go,go.mod} "$OUT/scanner/"
cp "$F/bootstrap.json" "$OUT/scanner/"
(cd "$OUT/scanner"; go mod tidy; go test -count=1 ./...; go build -o scan .; ./scan) | tee "$OUT/discovery.jsonl"
"$PY" r22_21_external_deletion/experiment.py recover "$F" "$OUT/discovery.jsonl" "$OUT/recovered"
"$PY" - "$OUT" <<'PY' | tee "$OUT/decision.jsonl"
import json,hashlib,sys,pathlib,datetime
p=json.load(open('RECOVERY_PIN.json')); old=p['retained_observation']; root=pathlib.Path(sys.argv[1])
b=json.loads((root/'bootstrap.jsonl').read_text().splitlines()[-1])
d=json.loads((root/'discovery.jsonl').read_text().splitlines()[-1])
r=json.loads((root/'recovered/report.json').read_bytes())
assert b['archive_sha256']==p['archive_sha256'] and b['event_id']==p['capsule_id']
assert d['sampled_tree_size']>=old['tree_size']
if d['sampled_tree_size']==old['tree_size']: assert d['sampled_tree_root']==old['tree_root']
assert d['matching_signed_leaves']==[{'index':p['first_index'],'checksum':p['first_checksum']},{'index':old['later_index'],'checksum':old['later_checksum']}]
assert r['disposition']=='RECOVERED_EXACT_SYNTHETIC_CONTENT_ONLY' and r['stale_replay']=='HOLD'
assert hashlib.sha256((root/'recovered/ledger.jsonl').read_bytes()).hexdigest()==old['ledger_sha256']
# For a larger head, scanner establishes consistency from first bootstrap, NOT necessarily retained observation.
print(json.dumps({'result':'READBACK_MATCH_RETAINED_SYNTHETIC_EVIDENCE','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tree_size':d['sampled_tree_size'],'ledger_sha256':old['ledger_sha256'],'retained_head_comparison':'SAME_ROOT' if d['sampled_tree_size']==old['tree_size'] else 'LARGER_HEAD_CONSISTENCY_FROM_FIRST_ONLY','time_source':'RUNNER_CLOCK_UNATTESTED','publication':'NONE','trust_activation':'NO_GO','production':'NO_GO','freshness':'UNKNOWN'},sort_keys=True))
PY
