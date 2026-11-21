# Published book v7.1 — local ZIP / Zenodo metadata cross-check

**Date:** 18 November 2026  
**Zenodo:** https://doi.org/10.5281/zenodo.24343618  
**Publication record checked:** https://zenodo.org/api/records/24343618  
**Local source examined:** `Being_With_the_Other_V7_1_FULL_MULTILINGUAL_DRAFTS_13_LANG_2026-11-18.zip`

- Source ZIP size: **11,179,597 bytes**.
- Source ZIP SHA-256: `e2e87a95c6efd1a00880b572cc3fe42985a4476001ad1b00942ca6a37c5d57cf`.
- ZIP contains **17 files**: 13 language PDFs and 4 text sidecars (README_EN, README_FA, QA_COVERAGE.json, SHA256SUMS.txt).
- For **all 13 PDFs**, MD5 calculated from this ZIP equals the published MD5 in the Zenodo API.
- For **all 13 PDFs**, SHA-256 calculated from this ZIP equals the corresponding value in its `SHA256SUMS.txt`.
- The 4 sidecars' MD5 values also match their listed Zenodo counterparts.
- The separately published book license `LICENSE_BOOK_CC_BY_4_0.md` matches the later local license copy by MD5 `70efc19163865294fe1cd461d1023174`; the license is **not** a member of the 17-file ZIP.
- The live Zenodo record describes **18 files**: 13 PDFs, 4 listed text sidecars, 1 license.

### Interpretation

This yields **13/13 local-PDF MD5 matches to the Zenodo provider's record**, plus **13/13 local-PDF SHA-256 matches to the uploaded SHA manifest**. It is stronger than a comparison with later working-directory files. It does **not** claim a cryptographically authenticated Zenodo API, an independent re-download-and-hash of the remote PDF bytes, a digital founder signature, human native-language validation, or peer review.

The earlier apparent hash discrepancy was from **later-repacked local files sharing the published filenames**; the original release ZIP matches the published metadata. Treat the original ZIP as the matched local publication snapshot, not the later repack.

This note is additive and does not rewrite previous source-history observations.
