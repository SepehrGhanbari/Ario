# R63 external WORM pilot — GCS candidate, not an enrolled custodian

2026-11-24 · RESEARCH_ONLY / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.

G9 reproduced a second native signature when a common administrator erased both histories. This branch adds a concrete provider-bound **synthetic marker** adapter and default read-only preflight, not another native signature micro-test. No cloud account, billing, bucket, retention lock, credentials or cloud write was created.

## Provider basis
- https://docs.cloud.google.com/storage/docs/bucket-lock — locked bucket retention; irreversible lock, project lien, account standing and finite retention caveats.
- https://docs.cloud.google.com/storage/docs/request-preconditions — conditional create using ifGenerationMatch=0.
- https://docs.cloud.google.com/storage/docs/consistency — strongly consistent object reads/listing.
- https://docs.cloud.google.com/storage/docs/json_api/v1/buckets/testIamPermissions — caller's effective bucket permission probe, not a cross-project admin audit.
- https://docs.cloud.google.com/storage/docs/access-control/iam-roles — objectCreator cannot overwrite/delete; object read and bucket metadata checks require separate narrowly granted permissions.
- https://docs.cloud.google.com/free/docs/free-cloud-features — eligible billing account required even for free tier; availability and costs NOT verified for founder.

S3 Compliance and Azure locked immutability are alternatives, not activated. The cloud provider is a storage service, NOT an extra voting actor or private-key holder.

## Implemented
gcs_pilot.py pins a dedicated research bucket name and project number, deployment id, and minimum retention from an operator-controlled non-secret configuration. Requires locked policy, uniform bucket access, public access prevention, required narrow create/read/metadata permissions and rejects enumerated excessive bucket/object permissions. This permission probe is not exhaustive; inherited organization, recovery, impersonation and project-level powers need independent audit.
Default: GET-only preflight. Explicit synthetic-write flag only: conditional create of fixed synthetic marker at deployment/epoch/nonce, with exact known seq3 and seq4 candidate; nonce object key does NOT change with payload or signer identity. 412 -> HOLD_EXTERNAL_SPENT; ambiguous response -> HOLD; fresh creation requires generation-bound metadata and exact byte readback, retention check and another preflight. A successful creation is NEVER a grant to sign. Local pin and local clock remain untrusted if the desktop admin controls them. Lost reply fails closed; no auto-sign or delete. No automatic authoritative latest floor or signed custodian ACK is implemented. A local Windows administrator may bypass a software-only broker even if cloud storage is protected; a separately enforced key-use gate remains necessary.

## Executed evidence
[CI run 45411252851](https://github.com/SepehrGhanbari/Ario/actions/runs/45411252851): 17/17 **mock transport** unittest controls PASS, no live provider request. Tests include conditional create, repeated request, commit-then-timeout, altered/missing readback, bad retention, overprivileged caller, missing permission and no signing authority. The nonce-key test only checks fixed deterministic naming and different nonces; does not test cross-epoch or real signer identity binding. Mock pass is not independent custody.

## Finite next field action
Founder/operator checks availability of an existing separately administered eligible Google Cloud account (no payment or irreversible lock yet). If available and separately authorized, provision one disposable **dedicated** bucket and narrow lab principal; do not use personal data, private keys, production or shared cloud admin credentials. Retention lock is irreversible for its lifetime: operator must explicitly approve its interval/cost BEFORE setting it. Independently inspect admin/backup/restore/rotation and IAM escalation, pin bucket/project/deployment outside publisher scope. Execute GET-only preflight first; only then one authorized synthetic write followed by the identical request. Expected 412/HOLD, then independently test actual publisher delete/overwrite/restore/pin-rebinding denial. Preserve evidence, do not promote seq4. After this, a signed fresh external consume/latest protocol and real protected key-use enforcement are separate integration gates.
No access to a connected GCS administration account is established here. Live cloud tests NOT_EXECUTED. No actual cloud or signer state changed.

VERDICT: PROVIDER_ADAPTER=IMPLEMENTED / MOCK_CONTRACT_17=PASS / CLOUD_PROVISIONED=NO / LIVE_CUSTODY=NOT_ESTABLISHED / INDEPENDENT_LATEST=NOT_ESTABLISHED / REAL_ARIO_SIGNER=NO_GO.