# DR-RESTORE-240-v0.1 — Manifest evidence and corrected-package publication choice

**Status: PROPOSED / REVIEW-ONLY / NOT ADOPTED.** No release, DOI change, main merge, trust activation or signer action is authorized by this record.

**Source snapshot:** 204 Git-tracked blobs at commit 05ba5c960aaea96fc6bb80504b53b4d47e7d42f5, tree 8a9429d396c09fe17682a61dd91cb43672d3cb79.
**Historical manifest SHA-256:** f86fb10ef3eb71dd6e3c348b3f0c9b42c88b3837ae889918c33d8f5d62fe11d8, as recorded in existing checksums.json. A checksum stored beside its payload is **not** an independent trust anchor.

## What additional verification establishes

The stand-alone, read-only verify_pinned_manifest.py independently parses TXT (it does not call the restore parser) and checks whole source payload and record metadata against a separately supplied manifest. It first requires the caller-supplied --expected-manifest-sha256 and rejects if manifest bytes do not match. It also checks TXT header/footer bindings, source commit/tree, path, mode, encoding, raw sizes, Git blob SHA-1 and SHA-256 for every record.

**Conditional result:** Only if the caller has already obtained and validated the pin through a genuinely trusted, independent channel does this verify that inspected bytes correspond to the pinned manifest. It does not prove the pin is trustworthy, publisher identity, untracked/private data completeness, or truth of claims inside files. The output PIN_CUSTODY_NOT_VERIFIED is deliberate.

**Adversarial control:** An attacker can forge a replacement payload, record hashes, a new manifest, and matching TXT header/footer, such that structural restore passes. Comparing the forged manifest to the original externally supplied expected hash fails. Supplying the attacker's new hash would pass local checks; this is a custody/provenance boundary.

## Publication recommendation: B — new package, preserve historical download

A. **Overwrite the existing ZIP/TXT, site assets, or published DOI files:** NOT RECOMMENDED. Historical evidence and citations would silently change.

B. **New separately named packaging/tool correction (RECOMMENDED ONLY FOR FUTURE REVIEW):** Preserve source snapshot ID and distinguish the new tooling revision. Name a candidate with 05ba5c9, restore-hardened and a version. Bundle the hardened restore and verifier under EXPORT_META/, with source manifest and explicit trust-anchor instructions. Retain original historical artifacts and references. This is NOT a new Ario implementation snapshot.

C. **Remain on HOLD until source trust and independent review:** Valid fallback.

**Decision:** Recommend B as publication *form*, but keep the candidate UNPUBLISHED / DRAFT until ALL gates below are satisfied; otherwise C.

## Gates before corrected public publication

1. Independent adversarial review of exact source for restorer, verifier and generator. Verifier source bundled inside an untrusted ZIP must itself be trusted or independently reimplemented before reliance.
2. Exact-head Windows/Ubuntu CI, independent TXT-manifest pin verification, full 204-blob Git roundtrip, and self-consistent-forgery negative control. macOS filesystem testing remains UNKNOWN.
3. Exact candidate ZIP/TXT/manifest hashes and expected manifest hash disclosed in an independently accessible, versioned trust reference whose custody and authority are described. The bundled checksums.json is insufficient as an external anchor. No real signer keys or unapproved signatures.
4. Explicit release authorization after scope, version and release notes review; confirm DOI/versioning policy before upload; record bytes, SHA256, commit and reproducibility limits.
5. Warn that original checked-in RESTORE_FROM_TXT.py and previously distributed ZIPs remain historical and are NOT automatically repaired. Do not silently redirect or overwrite a prior artifact.

## Boundaries

- TXT remains ARIO_FULL_TEXT_EXPORT_V1; new tooling/package revision does not migrate a semantic schema.
- CI's historical SHA is a deterministic regression pin from existing repository records, not a separate authenticated signature.
- No relation to memory Issue #216 authority, signer R62/R63 or Rulesets.
- No merge, public release, site switch, key use, signing, historical DOI replacement or trust activation occurred.

**Verdict:** RESEARCH_ONLY / PUBLICATION_HOLD / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO.
