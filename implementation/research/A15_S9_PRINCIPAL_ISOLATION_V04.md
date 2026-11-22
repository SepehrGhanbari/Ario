# A15 S9 v0.4 — OS-principal isolation feasibility

**Disposition:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NO_TRUST_ACTIVATION / NO_PRODUCTION.

**Parent:** Draft PR #334 at v0.3 head 35f9171b751033ab20a491a1f90c6b1b2334f7a4. This is a stacked feasibility probe. It does not modify v0.3 or its historical evidence.

## 1. Why S9 is still RED

The v0.3 Gate and Recorder are separate child PIDs but run under the same OS identity and share a writable directory. The Gate can replace the Recorder program before the runner launches it.

The new test test_a15_s9_v0_4.js reproduces a stronger attack than the earlier arbitrary-string mutation: the malicious Gate replaces Recorder with a program that reads the runner's command and emits a structurally valid, self-hashed INERT_RECORDER_STDOUT record using its own PID. The v0.3 verifier accepts that output as INERT_ACTION_LOCAL_RECEIPT_ONLY.

That status is explicitly local-only, but the test demonstrates that a distinct PID, a hash chain, matching run IDs, and a matching Recorder PID do not prove that the intended Recorder binary ran.

**A passing S9 RED-reproduction test means the vulnerability was reproduced. It is not a security pass.**

## 2. Proposed minimum local separation

Use two non-administrative runtime principals, not two processes under one account:

- **Gate principal:** unprivileged. It may read/execute the installed Custodian image and submit a bounded request to the broker. It cannot write/delete the image, change its ACL, read/write the Custodian ledger, or terminate the Custodian service.
- **Custodian principal:** a separate OS identity/service account. It owns the protected executable, service configuration, and private ledger. The service manager starts and supervises it; Gate receives no service-control or process-termination authority.
- **Protected installation/state:** no shared Gate-writable directory. Gate gets read/execute only on the installed service image and no access to the ledger. Custodian alone can update its private state.
- **Narrow IPC:** a Windows named pipe with a restrictive DACL or a Unix-domain socket with restrictive ownership/mode and peer-identity checks. Do not use a shared writable file as the request channel.
- **Independent decision:** the broker must parse and recompute from the original bounded input itself. It must not trust Gate's claimed ACCEPT, reason code, PID, timestamp, or hash.
- **Durable replay handling:** the broker, not Gate, allocates or validates a unique request identity and persists consumption before returning a receipt. An in-memory Set is insufficient.
- **Receipt semantics:** a local broker receipt proves only that this service recorded this request under its configured OS boundary. It does not prove provider delivery, user intent provenance, historical truth, or independence from the host administrator.

## 3. Platform implementation target

### Linux

A dedicated service UID/GID (or a systemd DynamicUser) owns /opt/ario-custodian and /var/lib/ario-custodian. The Gate process runs as a different unprivileged UID. A systemd unit should use a read-only system view and a narrowly writable state path, for example:

- User=ario-custodian
- Group=ario-custodian
- NoNewPrivileges=yes
- ProtectSystem=strict
- ProtectHome=yes
- PrivateTmp=yes
- ReadWritePaths=/var/lib/ario-custodian

The Unix socket is owned by the Custodian identity and exposed only to the designated Gate group. The broker validates the connecting peer UID and a strict, length-bounded request schema.

### Windows

Run the broker as a dedicated virtual service account/service SID (for example NT SERVICE\ArioCustodian) rather than the interactive Gate user. Protect the service image and state directory with explicit ACLs. Gate receives read/execute on the image, no write/delete/ownership/ACL rights, and no Service Control Manager rights to stop, reconfigure, or replace the service. Expose a named pipe whose DACL admits only the intended Gate principal and the Custodian service SID.

A separate local user is an acceptable synthetic test identity; it is not the final service installation model.

## 4. What this v0.4 probe actually tests

- test_a15_s9_v0_4.js: reproduces the v0.3 same-UID replacement attack and confirms the old verifier accepts the forged local receipt.
- a15_s9_principal_probe_v0_4.sh: on Linux, creates disposable identities with cleanup ownership flags; the Gate process verifies its real UID/EUID and supplementary groups, reads and executes the read-only image, and must receive exact EACCES/EPERM denials for overwrite, delete, chmod, rename, ledger read/write, and process signaling. A Custodian positive control reads the image and appends to its own ledger.
- a15_s9_principal_probe_v0_4.ps1: on Windows, creates disposable local accounts with per-run cleanup flags; the Gate probe verifies its SID, non-administrator status and absence of the Custodian SID, reads and executes the image, and classifies file, ACL, ledger and process failures only when the underlying error is access-denied. The Custodian SID/process owner and a positive ledger-write control are checked.
- The workflow runs frozen G0/G1, v0.2, v0.3 and the S9 exploit reproduction in separate steps so a later successful native command cannot mask an earlier failure, then runs the OS-principal probes on Linux and Windows.

An independent review found and drove fixes for unsafe cleanup of pre-existing identities, a misplaced Linux chmod check, Windows native-exit masking, and denial checks that previously accepted unrelated errors. The revised probes track only resources created by the current run, check exact permission-denied outcomes, and include positive controls.

This is a **kernel-enforced boundary feasibility probe**, not an integrated Custodian broker. It does not yet prove a complete end-to-end request/receipt path, service-manager hardening, named-pipe/socket peer authentication, durable replay protection, or external custody.

## 5. Threat boundary and non-claims

Separate OS principals on one host can constrain a compromised Gate process. They do not protect against:

- root/Administrator, kernel compromise, or an administrator who can take ownership/change ACLs;
- compromise of the Custodian account or its service binary;
- rollback/deletion by the host administrator;
- Gate supplying false or unproven source fields as the original choice input;
- a provider or user action that is not independently observed.

If one human or one automation account controls both OS identities and the host administrator, the setup is not independent human custody. Stronger independence requires a separately administered host/service or an external custodian with separately retained state/checkpoints.

## 6. S9 acceptance gates — not yet satisfied

1. The v0.3 same-UID forged-receipt attack is reproducible and retained as a negative control.
2. On Linux and Windows, Gate cannot replace, edit, rename, or delete the protected Custodian image.
3. Gate cannot read, append, truncate, or replace the Custodian ledger.
4. Gate cannot terminate, stop, reconfigure, or impersonate the Custodian service.
5. Custodian can independently recompute the original request and reject a forged Gate verdict.
6. Durable replay, crash/restart, lost-response, truncation, and rollback probes pass.
7. Independent reviewers inspect the threat model, implementation, and exact CI evidence.

Until the integrated broker and all gates pass, **S9 remains RED / NOT ESTABLISHED**. No trust activation, signer, real key, production path, or merge is part of this work.
