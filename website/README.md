# Ario website deployment source

This folder is the complete source for the static public Vercel site `ario-research-independent.vercel.app`.

- **Vercel project:** `ario-research-independent`.
- **Git repository:** `SepehrGhanbari/Ario`; production branch `main`; **Root Directory:** `website`.
- **Source-of-truth:** changes to the published site should be reviewed in GitHub PRs before merge; a released Git commit is not an independent certification of correctness.
- **Required paths:** `index.html`, `research.html`, `404.html`, `vercel.json`, `robots.txt`, `sitemap.xml`, both root verification files, and `papers/evidence-laundering-2026-10-27/Manuscript.md`.
- **Preserve** Google and TXT verification files unless the site owner explicitly rotates/removes them.
- **Security:** preserve `vercel.json` CSP/security headers; new inline styles/scripts must be evaluated against CSP before publishing.
- **Source caveat:** `research.html` was reconstructed in October 2026 from public repo sources after the Vercel file retrieval truncated its payload. It is not an exact byte reconstruction of the old version; the old production deployment is the historical reference.
- **Archived data:** `10.5281/zenodo.23651704` is a pinned historical release, not live repo state or the submitted manuscript DOI.

- **AI/model-readable download:** `/Ario-Read-Light-For-Models.txt` is the exact existing Git blob `9b0eb4daa25146fc74c31661db3c92e562777b34` from `releases/zenodo-23651704/`; it is a fixed **2,857,981-byte** historic snapshot (SHA-256 `63f170645e67131025e1d3b8d6e9002a8f3312741ecfce121b886f8d085bd68b`). Serving it under the `website/` root enables direct same-origin browser downloads, while the Zenodo original remains the archival reference. No new or updated snapshot was produced.
