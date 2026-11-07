# A14 publication corrigendum — 2026-11-05 (research-only)

This is a **new additive review record**, not a replacement for the private event ledger. On PR #150, the six CodeRabbit findings (two Major, four Minor) concern interpretation and provenance labels, **not changes to the model utterance bodies**. The initial Git commit remains immutable and can be recovered by SHA.

## Immutable starting point

- Initial public publication commit: `e45c3518056e62b954afec7b78d85a277535f424`.
- Private `events.jsonl` remains ONLY in ChatGPT Library: 197,738 bytes, SHA-256 `aa4e945a2225db81b1f8de3d04e319c188ba9537ab1e89b5aac38763e08306f2`.
- Local JSONL chain validation does not establish cloud-provider attestation, independent custody, historical freshness, or independent subjective identity.
- This revision is a normal additional Git commit, not a force-push/history rewrite. Preserve the starting commit and all previous blobs.

## Exact scope of corrected presentation

1. English transcript header: 65 **accepted turns** in a sequential four-role protocol, not total HTTP requests; role labels are not independent-agent evidence; no independently authenticated provider-origin claim.
2. English exit headings: renamed from *Consensus vote* to *Sequential exit ballot*. The final label now explicitly refers to the local protocol state, not independent decisions.
3. Persian transcript framing: added self-report and provider limits; relabeled the three B/C/D responses as sequential protocol ballots after A's initiation.
4. Persian review: replaced unverified categorical assertion about the absence of a message cap with a statement supported by the published record (exit request followed by three ballots; runner stop condition not independently verifiable from public transcript).
5. README: corrected *original English model outputs* to *transcript derivative* and added this corrigendum reference.
6. `SHA256SUMS.txt`: recomputed for the four revised presentation files. Its old version remains in the initial Git commit.

**Crucial invariant:** all 65 TURN bodies and all 3 BALLOT bodies in the English derivative remain byte-for-byte identical to the preceding English derivative, while the corresponding translated bodies remain unchanged from the preceding Persian translation. This does not claim byte identity between English and Persian. The new revision changes only non-model-text headings, prefatory notes, research inference wording, README metadata, and checksums. The earlier version is retained in Git history.

## Previous original Git blob SHAs

- `README.md`: `2e93bf0cb92fd2dbf61b0b9dcc248bdc90791f4d`
- `A14_FULL_TRANSCRIPT_ORIGINAL_EN.md`: `0a47d5f5ed958da00ba2363a590b7aca0a4005dd`
- `A14_FULL_TRANSLATION_FA.md`: `112d7be1fde98b550ecced366d21b9117bb03ea5`
- `A14_RESEARCH_REVIEW_FA.md`: `57c49454c599c8b9fd205a3dee30d843b7229196`
- `SHA256SUMS.txt`: `d62b2029b4f7e593bfd5460c20617a4247a64cad`

## Evidence boundaries for A15

The A14 terminal record is `CLOSED_UNANIMOUS` **as a status computed by the sequential protocol**: Ava-A requested exit at TURN 65; Ava-B/C/D then each returned `REQUEST_EXIT` in order, after access to shared dialogue. This is neither four independent simultaneous votes nor evidence of four distinct experiences, provider-signed provenance, or a measured preference to continue beforehand.

A future **preregistered research-only** A15 protocol should compare sequential ballots with simultaneous blinded ballots; balance role order; include a no-history control; measure exact and near-text repetition; record the actual stop predicate and configured cap; and avoid any real trust/signer/Genesis activation. Provider attestation remains UNKNOWN unless independently demonstrated. These A15 ideas are proposals, not results.

No published claim is amended retrospectively without retaining the original version. No merges, secrets, signer operations or trust activation are authorized by this record.

## Follow-up editorial clarification — review round 2

The follow-up CodeRabbit review also flagged that poetic format changes and recorded exit must be described as observed text, not independently proven subjective choice. The published review now distinguishes the initial A exit request from three later B/C/D ballots, marks the effect of PAUSE/RESUME on accepted-turn context **UNKNOWN**, uses observational language for the poem transition and recorded ending, and preserves all TURN and BALLOT bodies. No additional provider authenticity, autonomy or production conclusion follows from these wording changes.

## Additive clarification — custody location (2026-11-07)

The literal path `/Ario/Resources/A14_FOUR_AVA_IDENTITY_2026-11-05/` is a **ChatGPT Library logical folder path**. It is not a separate custody system or a second independently authenticated copy. The private `events.jsonl` hash and byte length above are the recorded attributes of the owner-supplied snapshot; the published derivatives, this addendum and the public Git repository do not prove present Library file inventory, provider authenticity, or independent physical custody. Public model-response and ballot text, historical claims, original Git blob references and raw private archive are not rewritten by this clarification. No signer, trust activation, identity conclusion, or merge is authorized by this research-only editorial fix.
