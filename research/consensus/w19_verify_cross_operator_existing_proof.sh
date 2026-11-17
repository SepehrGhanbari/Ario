#!/usr/bin/env bash
# W19 source-backed cryptographic review ONLY of EXISTING W18 public Sigsum proof.
# NO sigsum-submit, NO signing, NO Ario key, NO external log update.
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
manifest="$here/W18_PUBLIC_RESEARCH_ANCHOR_MANIFEST_2026-11-17.json"
pub="$here/W18_SIGSUM_VERIFIED_SUBMITTER_PUBLIC_KEY_2026-11-17.pub"
proof="$here/W18_SIGSUM_VERIFIED_INCLUSION_PROOF_2026-11-17.proof"
policy_a="$here/W19_GLASKLAR_GOOGLE_REQUIRED.policy"
policy_b="$here/W19_REMORA_GOOGLE_REQUIRED.policy"
expected_manifest="ee83050bff68f9b73afb115949bca8c46bb09462a6f000eecb9ed07bf2855769"
expected_proof="edae4603b5f8a32a3ab9f989ebf499f31fb12864708e5fc675308cf6d847d8b6"

die() { echo "W19_FAIL: $*" >&2; exit 1; }
command -v sigsum-verify >/dev/null || die "needs official sigsum-verify v0.14.1"
test "$(sha256sum "$manifest" | cut -d' ' -f1)" = "$expected_manifest" || die "unapproved manifest"
test "$(sha256sum "$proof" | cut -d' ' -f1)" = "$expected_proof" || die "unapproved receipt"
for f in "$pub" "$policy_a" "$policy_b"; do test -s "$f" || die "missing $f"; done

# Verify that selected policy keys correspond to independently-published test
# operator identities and match existing receipt key-hashes. This is structural
# matching; subsequent sigsum-verify does ACTUAL cryptographic verification.
eval "$(python3 - "$proof" "$policy_a" "$policy_b" <<'PY'
import hashlib,pathlib,sys
proof=pathlib.Path(sys.argv[1]).read_text('ascii')
candidates={line.split()[0].split('=',1)[1] for line in proof.splitlines() if line.startswith('cosignature=')}
assert len(candidates)==15,('unexpected real proof witness hash count',len(candidates))
found={}
for path in sys.argv[2:]:
    for line in pathlib.Path(path).read_text('utf8').splitlines():
        columns=line.split()
        if len(columns)==3 and columns[0]=='witness':
            name,public=columns[1],columns[2]
            digest=hashlib.sha256(bytes.fromhex(public)).hexdigest()
            assert digest in candidates,('published operator key not in W18 proof',name)
            found[name]=digest
for name,var in [('transparency.dev/DEV:witness-little-garden','google'),
                  ('poc.sigsum.org/nisse','glasklar'),
                  ('remora.n621.de','remora')]:
    assert name in found,name
    print(f'{var}_keyhash={found[name]}')
PY
)"

# The TWO positive proofs are under stricter explicitly all-of-2 keys.
sigsum-verify -p "$policy_a" -k "$pub" "$proof" < "$manifest"
echo "W19_P01_GLASKLAR_AND_GOOGLE_STRICT_CROSS_OPERATOR_POLICY_PASS"
sigsum-verify -p "$policy_b" -k "$pub" "$proof" < "$manifest"
echo "W19_P02_REMORA_AND_GOOGLE_STRICT_CROSS_OPERATOR_POLICY_PASS"

tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
grep -v "^cosignature=${google_keyhash} " "$proof" > "$tmp/no_google.proof"
grep -v "^cosignature=${glasklar_keyhash} " "$proof" > "$tmp/no_glasklar.proof"
grep -v "^cosignature=${remora_keyhash} " "$proof" > "$tmp/no_remora.proof"
test "$(wc -l < "$tmp/no_google.proof")" -lt "$(wc -l < "$proof")" || die "Google signature was not removed"
test "$(wc -l < "$tmp/no_glasklar.proof")" -lt "$(wc -l < "$proof")" || die "Glasklar signature was not removed"
test "$(wc -l < "$tmp/no_remora.proof")" -lt "$(wc -l < "$proof")" || die "Remora signature was not removed"
# Original weaker test policy is allowed to pass with the Google signature
# removed; this is the counterexample that it does NOT enforce cross-company quorum.
sigsum-verify -P sigsum-test1-2025 -k "$pub" "$tmp/no_google.proof" < "$manifest"
echo "W19_N01_ORIGINAL_TEST_POLICY_STILL_ACCEPTS_WITHOUT_GOOGLE_CONFIRMS_COMMON_ORG_RISK"

if sigsum-verify -p "$policy_a" -k "$pub" "$tmp/no_google.proof" < "$manifest" >/dev/null 2>&1; then
  die "cross-operator A accepted missing Google"
fi
if sigsum-verify -p "$policy_b" -k "$pub" "$tmp/no_google.proof" < "$manifest" >/dev/null 2>&1; then
  die "cross-operator B accepted missing Google"
fi
echo "W19_N02_BOTH_STRICT_POLICIES_REJECT_MISSING_GOOGLE"

if sigsum-verify -p "$policy_a" -k "$pub" "$tmp/no_glasklar.proof" < "$manifest" >/dev/null 2>&1; then
  die "cross-operator A accepted missing Glasklar"
fi
echo "W19_N03_STRICT_A_REJECTS_MISSING_GLASKLAR"

if sigsum-verify -p "$policy_b" -k "$pub" "$tmp/no_remora.proof" < "$manifest" >/dev/null 2>&1; then
  die "cross-operator B accepted missing Remora"
fi
echo "W19_N04_STRICT_B_REJECTS_MISSING_REMORA"

python3 - "$policy_a" "$tmp/false_google.policy" <<'PY'
import pathlib,re,sys
s=pathlib.Path(sys.argv[1]).read_text('utf8')
needle='2b6eb0ec483503544cde4e8fc1ce6d1921db21dffccc186865f808f7625443cc'
assert s.count(needle)==1
bad=needle[:-1]+('0' if needle[-1]!='0' else '1')
pathlib.Path(sys.argv[2]).write_text(s.replace(needle,bad),'utf8')
PY
if sigsum-verify -p "$tmp/false_google.policy" -k "$pub" "$proof" < "$manifest" >/dev/null 2>&1; then
  die "cross-operator verifier accepted forged Google public key"
fi
echo "W19_N05_STRICT_A_REJECTS_FORGED_GOOGLE_PUBLIC_KEY"
echo "W19_OFFLINE_STRICTER_VERIFICATION_COMPLETE; PUBLIC_TEST_RECORD_ONLY; ADMIN_CUSTODY_NOT_INDEPENDENTLY_ATTESTED; NO_REAL_ARIO_LOG; ACTION_AUTHORITY=NONE"
