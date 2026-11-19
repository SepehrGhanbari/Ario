#!/usr/bin/env bash
# W18 verifier-only (no network submission; no Ario signer; no live memory).
# Requires official Sigsum v0.14.1 sigsum-verify in PATH.
set -euo pipefail
dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
manifest="$dir/W18_PUBLIC_RESEARCH_ANCHOR_MANIFEST_2026-11-17.json"
pub="$dir/W18_SIGSUM_VERIFIED_SUBMITTER_PUBLIC_KEY_2026-11-17.pub"
proof="$dir/W18_SIGSUM_VERIFIED_INCLUSION_PROOF_2026-11-17.proof"
policy=sigsum-test1-2025
expected_manifest=ee83050bff68f9b73afb115949bca8c46bb09462a6f000eecb9ed07bf2855769
expected_proof=edae4603b5f8a32a3ab9f989ebf499f31fb12864708e5fc675308cf6d847d8b6

die() { echo "W18_VERIFY_FAIL: $*" >&2; exit 1; }
command -v sigsum-verify >/dev/null || die 'missing sigsum-verify'
test -s "$manifest" && test -s "$pub" && test -s "$proof" || die 'missing source / public key / receipt'
test "$(sha256sum "$manifest" | awk '{print $1}')" = "$expected_manifest" || die 'manifest digest changed'
test "$(sha256sum "$proof" | awk '{print $1}')" = "$expected_proof" || die 'receipt digest changed'
sigsum-verify -P "$policy" -k "$pub" "$proof" < "$manifest" || die 'real proof denied under official quorum policy'
echo 'W18_V01_VALID_EXTERNAL_SIGSUM_RECEIPT_PASS'

tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT

cp -- "$manifest" "$tmp/tampered_manifest.json"
printf ' ' >> "$tmp/tampered_manifest.json"
if sigsum-verify -P "$policy" -k "$pub" "$proof" < "$tmp/tampered_manifest.json" >/dev/null 2>&1; then
  die 'changed manifest erroneously verified'
fi
echo 'W18_N01_SINGLE_BYTE_MANIFEST_CORRUPTION_DENIED'

grep -v '^cosignature=' "$proof" > "$tmp/no_cosignatures.proof"
test "$(wc -c < "$tmp/no_cosignatures.proof")" -gt 0 || die 'empty negative proof'
if sigsum-verify -P "$policy" -k "$pub" "$tmp/no_cosignatures.proof" < "$manifest" >/dev/null 2>&1; then
  die 'missing witness cosignatures erroneously verified'
fi
echo 'W18_N02_REMOVED_ALL_COSIGNATURES_DENIED'

python3 - "$proof" "$tmp/tampered_node.proof" <<'PY'
import pathlib,re,sys
s=pathlib.Path(sys.argv[1]).read_text('ascii')
t,n=re.subn(r'^node_hash=[0-9a-f]{64}$','node_hash='+'0'*64,s,count=1,flags=re.M)
if n!=1 or t==s: raise SystemExit('failed to mutate node_hash')
pathlib.Path(sys.argv[2]).write_text(t,'ascii')
PY
if sigsum-verify -P "$policy" -k "$pub" "$tmp/tampered_node.proof" < "$manifest" >/dev/null 2>&1; then
  die 'modified inclusion node hash erroneously verified'
fi
echo 'W18_N03_CORRUPTED_INCLUSION_NODE_DENIED'

python3 - "$pub" "$tmp/tampered.pub" <<'PY'
import base64,pathlib,sys
s=pathlib.Path(sys.argv[1]).read_text('ascii')
parts=s.split(' ',2)
if len(parts)<2 or parts[0]!='ssh-ed25519': raise SystemExit('unexpected public key format')
raw=bytearray(base64.b64decode(parts[1],validate=True))
if len(raw)<32: raise SystemExit('not an Ed25519 public key')
raw[-1]^=1
parts[1]=base64.b64encode(raw).decode('ascii')
pathlib.Path(sys.argv[2]).write_text(' '.join(parts),'ascii')
PY
if sigsum-verify -P "$policy" -k "$tmp/tampered.pub" "$proof" < "$manifest" >/dev/null 2>&1; then
  die 'modified submitter public key erroneously verified'
fi
echo 'W18_N04_MODIFIED_SUBMITTER_PUBLIC_KEY_DENIED'
echo 'W18_OFFLINE_REVERIFY_RESULT=PASS_VALID_AND_4_EXPECTED_REJECTIONS'
echo 'ARIA_ACTION_AUTHORITY=NONE; REAL_ARIO_LOG_WITNESSED=NOT_ESTABLISHED; ORIGINAL_USER_CONSENT=NOT_ESTABLISHED'
