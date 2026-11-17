#!/usr/bin/env bash
# No network or Sigsum binary required: only fail-closed research checks.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/w18_sigsum_one_shot.sh"
MANIFEST="$HERE/W18_PUBLIC_RESEARCH_ANCHOR_MANIFEST_2026-11-17.json"
EXPECTED_SHA256='ee83050bff68f9b73afb115949bca8c46bb09462a6f000eecb9ed07bf2855769'
[[ -f "$SCRIPT" && -f "$MANIFEST" ]]
bash -n "$SCRIPT"
actual="$(sha256sum "$MANIFEST" | awk '{print $1}')"
[[ "$actual" == "$EXPECTED_SHA256" ]] || { echo 'FAIL: anchor manifest changed' >&2; exit 1; }
result="$(bash "$SCRIPT" --dry-run "$MANIFEST")"
grep -Fq 'W18_DRY_RUN_ONLY' <<< "$result"
grep -Fq 'EXTERNAL_PROOF=NOT_OBTAINED' <<< "$result"
grep -Fq 'AUTHORITY=NONE' <<< "$result"
set +e
bash "$SCRIPT" --submit "$MANIFEST" "$HERE/should_not_be_created" > /dev/null 2>&1
status_submit=$?
bash "$SCRIPT" --verify "$MANIFEST" "$HERE/no_public_key" "$HERE/no_external_proof" > /dev/null 2>&1
status_verify=$?
set -e
[[ "$status_submit" == 2 && "$status_verify" == 2 ]] || { echo "FAIL: unsafe submit=$status_submit verify=$status_verify" >&2; exit 1; }
[[ ! -e "$HERE/should_not_be_created" ]] || { echo 'FAIL: output created without approval' >&2; exit 1; }
python3 - "$MANIFEST" <<'PY'
import json,sys,re
x=json.load(open(sys.argv[1],encoding='utf-8'))
assert set(x)=={'schema','scope','snapshot_label','repository','snapshot_commit','snapshot_epoch','previous_manifest_sha256','artifacts','assertions_not_made'}
assert x['scope']=='PUBLIC_SYNTHETIC_RESEARCH_ONLY'
assert x['snapshot_epoch']==0 and x['previous_manifest_sha256'] is None
assert re.fullmatch('[a-f0-9]{40}',x['snapshot_commit'])
assert len(x['artifacts'])==4
for f in x['artifacts']:
    assert f['path'].startswith('research/consensus/') and re.fullmatch('[a-f0-9]{40}',f['git_blob_sha1'])
print('W18_MANIFEST_SCHEMA_PASS')
PY
printf 'W18_DRY_RUN_TEST_PASS: 4 checks: shell syntax, immutable manifest hash/schema, default no-network, unauthorized submit and missing proof denied. REAL_EXTERNAL_PROOF=NOT_OBTAINED\n'
