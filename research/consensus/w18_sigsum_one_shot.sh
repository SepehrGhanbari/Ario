#!/usr/bin/env bash
# W18 — explicit opt-in only; no scheduled/automatic publication.
set -euo pipefail
POLICY='sigsum-test1-2025'
# Exact public-only W17 research snapshot; refuse arbitrary file submission.
EXPECTED_SHA256='ee83050bff68f9b73afb115949bca8c46bb09462a6f000eecb9ed07bf2855769'

die() { printf 'W18_HOLD: %s\n' "$*" >&2; exit 2; }
check_pinned_manifest() {
  [[ -f "$1" ]] || die 'missing manifest'
  [[ "$(sha256sum "$1" | awk '{print $1}')" == "$EXPECTED_SHA256" ]] || die 'unapproved manifest bytes; source must match pinned public W17 snapshot exactly'
}
usage() {
  cat <<'USAGE'
Usage:
  bash w18_sigsum_one_shot.sh --dry-run PUBLIC_MANIFEST.json
  ARIO_W18_PUBLIC_SUBMISSION_APPROVED=YES bash w18_sigsum_one_shot.sh --submit PUBLIC_MANIFEST.json OUT_DIR
  bash w18_sigsum_one_shot.sh --verify PUBLIC_MANIFEST.json SUBMITTER_PUBLIC_KEY.pub PROOF_FILE

--dry-run: does NOT connect or generate a key.
--submit: explicitly publishes a signed checksum to a third-party *test* log;
          the included PUBLIC_MANIFEST is permanent/public at the provider.
--verify: offline cryptographic verification via official sigsum-verify.
Never use the Ario owner signer or production keys.
USAGE
}

[[ $# -gt 0 ]] || { usage; exit 2; }
mode="$1"; shift
case "$mode" in
  --dry-run)
    [[ $# -eq 1 && -f "$1" ]] || die 'expected one existing public manifest'
    manifest="$1"
    check_pinned_manifest "$manifest"
    printf 'W18_DRY_RUN_ONLY: public manifest path=%s sha256=%s\n' "$manifest" "$(sha256sum "$manifest" | awk '{print $1}')"
    printf 'POLICY=%s; EXTERNAL_PROOF=NOT_OBTAINED; WITNESSED_ARIO_LOG=NOT_ESTABLISHED; AUTHORITY=NONE\n' "$POLICY"
    ;;
  --verify)
    [[ $# -eq 3 && -f "$1" && -f "$2" && -s "$3" ]] || die 'requires manifest, public submitter key and nonempty proof'
    check_pinned_manifest "$1"
    command -v sigsum-verify >/dev/null 2>&1 || die 'sigsum-verify is not installed'
    sigsum-verify -P "$POLICY" -k "$2" "$3" < "$1" || die 'Sigsum cryptographic/quorum proof verification FAILED'
    printf 'W18_EXTERNAL_SIGSUM_PROOF_VERIFIED_FOR_SUPPLIED_BYTES; POLICY=%s; ARIO_LOG_WITNESSED=NOT_ESTABLISHED; FRESHNESS=NOT_ESTABLISHED; AUTHORITY=NONE\n' "$POLICY"
    ;;
  --submit)
    [[ $# -eq 2 && -f "$1" ]] || die 'requires existing public manifest and output directory'
    [[ "${ARIO_W18_PUBLIC_SUBMISSION_APPROVED:-}" == 'YES' ]] || die 'no explicit approval: set ARIO_W18_PUBLIC_SUBMISSION_APPROVED=YES only after reviewing publication'
    manifest="$1"; outdir="$2"
    check_pinned_manifest "$manifest"
    [[ ! -e "$outdir" ]] || die 'OUT_DIR must not exist: avoid overwriting existing evidence'
    for tool in sigsum-key sigsum-policy sigsum-submit sigsum-verify; do
      command -v "$tool" >/dev/null 2>&1 || die "missing verified Sigsum CLI: $tool"
    done
    tmp="$(mktemp -d)" || die 'cannot create isolated scratch'
    chmod 700 "$tmp"
    trap 'rm -rf -- "$tmp"' EXIT
    cp -- "$manifest" "$tmp/public_research_anchor.json"
    chmod 600 "$tmp/public_research_anchor.json"
    sigsum-policy show "$POLICY" > "$tmp/policy.txt"
    grep -Fq 'group quorum-rule 2 poc.sigsum.org/nisse rgdd.se/poc-witness witness1.smartit.nu/witness1' "$tmp/policy.txt" || die 'test policy quorum changed; independent review required'
    sigsum-key generate -o "$tmp/submitter.key"
    [[ -f "$tmp/submitter.key.pub" ]] || die 'submitter public key not generated'
    sigsum-submit -P "$POLICY" -k "$tmp/submitter.key" "$tmp/public_research_anchor.json"
    [[ -s "$tmp/public_research_anchor.json.proof" ]] || die 'public proof missing after submission'
    sigsum-verify -P "$POLICY" -k "$tmp/submitter.key.pub" "$tmp/public_research_anchor.json.proof" < "$tmp/public_research_anchor.json" || die 'proof failed mandatory re-verification'
    mkdir -m 700 -- "$outdir"
    cp -- "$tmp/public_research_anchor.json" "$outdir/manifest.json"
    cp -- "$tmp/submitter.key.pub" "$outdir/submitter.pub"
    cp -- "$tmp/public_research_anchor.json.proof" "$outdir/manifest.proof"
    cp -- "$tmp/policy.txt" "$outdir/policy.txt"
    printf 'W18_PUBLIC_TEST_PROOF_VERIFIED: output=%s manifest_sha256=%s\n' "$outdir" "$(sha256sum "$outdir/manifest.json" | awk '{print $1}')"
    printf 'PUBLISH ONLY THE PUBLIC RECEIPT FILES AFTER INDEPENDENT REVIEW. PRIVATE SUBMITTER KEY WAS IN TEMP SCRATCH. ARIO_SIGNER/REAL_ARIO_LOG/OWNER_CONSENT=NOT_ESTABLISHED.\n'
    ;;
  *) usage; die "unknown mode $mode" ;;
esac
