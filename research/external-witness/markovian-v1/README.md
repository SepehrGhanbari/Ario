# Markovian synthetic test log public endpoint

**RESEARCH_ONLY / SYNTHETIC_ONLY / HOLD / NO_REAL_KEYS / NO_PRODUCTION / NO_TRUST_ACTIVATION.**

The public bundle was generated locally with the existing encrypted Ario Kladje research identity, then independently checked before publication. It contains one synthetic leaf and a C2SP signed checkpoint.

Never place private keys, passphrases, local key backups, or personal memory in this directory.

## Public artifacts

- checkpoint: https://raw.githubusercontent.com/SepehrGhanbari/Ario/research/markovian-synthetic-log-v0-1-20261127/research/external-witness/markovian-v1/checkpoint
- entries: https://raw.githubusercontent.com/SepehrGhanbari/Ario/research/markovian-synthetic-log-v0-1-20261127/research/external-witness/markovian-v1/entries
- vkey: https://raw.githubusercontent.com/SepehrGhanbari/Ario/research/markovian-synthetic-log-v0-1-20261127/research/external-witness/markovian-v1/vkey.txt
- capsule: https://raw.githubusercontent.com/SepehrGhanbari/Ario/research/markovian-synthetic-log-v0-1-20261127/research/external-witness/markovian-v1/capsule.json
- manifest: https://raw.githubusercontent.com/SepehrGhanbari/Ario/research/markovian-synthetic-log-v0-1-20261127/research/external-witness/markovian-v1/manifest.json

## Independent local verification

The submitted ZIP contained exactly these five files. Offline verification confirmed:
- synthetic-only capsule and entry;
- capsule SHA-256 and byte count bound into the leaf;
- single-leaf RFC 6962 Merkle root;
- C2SP Ed25519 vkey signature type and recomputed key ID;
- valid Ed25519 signature over the exact checkpoint note text;
- manifest fields and SHA-256 values match the archived bytes.

Checkpoint SHA-256: `84ef0c4abc6e06033219f3a34b12c5d4b3893e0a8bd3f082bc7fed1d6e5047cd`

Tree size: `1`

This publication does not mean Markovian has pinned or cosigned the origin. Do not send an add-checkpoint request until the Markovian operator confirms manual origin/key pinning. No witness cosignature is present yet.
