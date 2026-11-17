# Ario R6 — Two OS Principals + Externally Witnessed Checkpoint Protocol

**RESEARCH_ONLY / DRAFT / HOLD / NOT_ADOPTED / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO**

## Goal and strict threat-model boundary

Find a *measurable, practical path* from one operator, two ordinary Windows computers and a phone to meaningful external observation **without inventing independent humans or treating same-admin keys as independent authority**.

This research proposal separates three statements that must NEVER be conflated:

1. **OS access separation:** Executor E cannot access Custodian C's private directory; C cannot access E's private signing key. This is testable via recorded EACCES/EPERM under genuinely different OS UIDs. An administrator/root of their shared machine can still take ownership of *both*. Therefore OS separation is **not administrative independence**.
2. **Custodian persistence:** C can maintain a locked, fsynced synthetic nonce/revocation journal and refuse a duplicate even during two simultaneous submissions. C still controls/replaces its own history; same-admin rollback and fork remain possible without independent anchoring.
3. **External observation:** publish a **test-only** signed SHA-256 checkpoint via Sigsum, obtain an inclusion proof with signatures from a distinct, published witness quorum, and verify it **offline** under an independently pinned policy. This would support **a witnessed public statement about a digest** only. It does NOT prove that the signer was authorized, that an actual tool executed, that the journal is freshest, or that the executor is independently operated.

**Nothing here touches any real Ario signer, owner key, policy activation, trust state or semantic memory.**

## Stage R6-A — disposable GitHub-hosted Linux VM (implemented)

Files:
- `os_custody_lab.py`: small research CLI using ephemeral Ed25519, strict canonical JSON, separate trusted *public* key file, C-held Unix `flock` journal, `fsync`, hash links, strict nonce and clock window checks, and output with all authority flags false.
- `.github/workflows/r6-synthetic-os-custody.yml`: runs on a fresh GitHub-hosted Ubuntu runner, creates `ario_r6_executor` and `ario_r6_custodian` as OS accounts in that same VM, with private directories at mode 0700.
- No private key or sensitive source content is printed to CI logs. The only keys are ephemeral synthetic test keys created per runner.

Prerecorded positive and negative expectations:
- `E` can sign a synthetic receipt but cannot read or modify `C`'s pinned public key and journal (`EACCES`).
- `C` cannot read `E`'s raw test-only private key (`EACCES`).
- `C` verifies receipt against its locally provisioned public key, uses its own runner clock, and records one nonce in a locked, fsynced journal; all authority remains denied.
- A replay is rejected.
- Two concurrent C processes racing to consume an identical second nonce produce **exactly one** spend and **one** replay refusal.
- After a synthetic revocation, a fresh properly signed receipt is rejected.
- The provisioning job's `root` user can still read both role directories, and the report explicitly states `ADMINISTRATIVE_INDEPENDENCE: NOT_ESTABLISHED`.

**Meaning:** establishes a measured Linux OS-UID and single-custodian concurrency boundary under a common root administrator. **Not an independent entity or production authorization.** CI only proves the exact runner it executed; not the Windows machines, laptop or cloud.

Security limitations in the implementation:
- Research-only root provisions E's public key into C; root can substitute it. This is NOT an independently authorized enrollment.
- The journal is writable by C, with only local file permissions and `fsync`. It is **not WORM** and cannot prevent malicious C/administrator truncation, checkpoint fork, host clock manipulation, snapshot restore, or denial of service.
- `flock` serializes concurrent participants that obey the protocol, not a malicious process bypassing the lock or an OS admin. A partial write/crash fails closed on next read; this lab does not provide transactional crash recovery.
- The result's `OBSERVED_ONLY` state is not a capability to act. No direct call is made to source monitoring, memory, tool execution, key signer, or prospective-memory activation.
- Receipt's declared result hash is **synthetic**; an Ed25519 signature over synthetic values says nothing about real execution.

## Stage R6-B — user's two physical computers (NOT executed, manual approval required)

Suggested physical roles based on *available equipment*, no new purchases:
- **Desktop:** isolated experimental executor E, no access to laptop C's journal. Keep existing Ario private keys untouched.
- **Laptop:** independent OS host for experimental C and durable state. C receives only public test policy + signed receipt bytes. Require C-controlled write permissions, an independent journal folder and a private non-admin service account. Keep the laptop's real signer/main Ario host untouched.
- **Phone:** out-of-band checkpoint monitor/observer (shows proof and previous public SHA). It does not receive private keys or act as a trusted clock by itself.

Preflight manually record: device/OS build, E and C OS principal identifiers, ACL/permission denial, process ownership, revocation/nonce replays and whether common administrative credentials still control both hosts. The user remains administrator of both machines, so **operator independence remains NOT_ESTABLISHED**; the improvement is separate physical failure domains and OS isolation.

**Do not launch any script on the host or change OS ACLs on real Ario directories without specific consent.** Use disposable research-only accounts, directories and keys. Avoid unsafe elevated operations outside a disposable sandbox.

## Stage R6-C — external witness quorum using public Sigsum (NOT executed)

The official Sigsum getting-started flow supports Ed25519 signing of a file digest, public log submission, collecting an inclusion proof co-signed by external witnesses, and **offline proof verification**. The documented `sigsum-test1-2025` policy includes an external 2-of-3 witness quorum. This is a **TEST policy/service**, not a production reliability guarantee.

Official source: https://www.sigsum.org/getting-started/
- A verifier must pin the Sigsum log + witness public keys **from independently distributed policy data** (not from the same untrusted E message).
- Obtain C's *post-fsync* high-water checkpoint `(sequence, head_sha256)`, generate a new **public SYNTHETIC** checkpoint file containing no private information, credentials, or private ledger contents.
- Sign/publish the checkpoint checksum with **an ephemeral, dedicated test key** and collect the proof. This does not sign the Ario kernel or any real trust transition.
- Verify the proof on another machine with `sigsum-verify` under the predefined test policy and separately observe the public log using `sigsum-monitor`.
- Store checkpoint file, public key, proof, verification stdout/exit code, policy hash, runner/operator IDs and a manifest of SHA-256 hashes. Maintain at least two observations to check monotonicity and detect equivocation. A proof of inclusion is **not proof of latest state**; monitor/compare heads and require an explicitly bounded freshness policy.

### Reference commands (NOT run by this PR)

These commands come from the current official Sigsum getting-started page. They require **Go >= 1.23** and network access. Run only on disposable **test-only data** when explicitly authorized, never on real keys or private logs.

```sh
go install sigsum.org/sigsum-go/cmd/sigsum-key@v0.14.1
go install sigsum.org/sigsum-go/cmd/sigsum-policy@v0.14.1
go install sigsum.org/sigsum-go/cmd/sigsum-submit@v0.14.1
go install sigsum.org/sigsum-go/cmd/sigsum-verify@v0.14.1
go install sigsum.org/sigsum-go/cmd/sigsum-monitor@v0.14.1

sigsum-policy show sigsum-test1-2025
sigsum-key generate -o r6-SYNTHETIC-anchor-key

# Create r6-SYNTHETIC-checkpoint.txt with ONLY a disposable public digest;
# do not place any real Ario secrets or raw journals in this public log.
sigsum-submit -P sigsum-test1-2025 -k r6-SYNTHETIC-anchor-key r6-SYNTHETIC-checkpoint.txt
sigsum-verify -k r6-SYNTHETIC-anchor-key.pub -P sigsum-test1-2025 \
  r6-SYNTHETIC-checkpoint.txt.proof < r6-SYNTHETIC-checkpoint.txt

# Separately monitor the public log for use of the synthetic anchor key.
sigsum-monitor --interval 10s -P sigsum-test1-2025 r6-SYNTHETIC-anchor-key.pub
```

**What a verified proof could establish:** a particular *signed digest* was publicly logged under a log's independently witnessed checkpoint, subject to the pinned policy and its threat model. This reduces the ability of a single local administrator to silently rewrite already-observed history. It does **not** prove truthful execution, durable replay prevention at C, independent ownership of E/C keys, freshness of all state or authority to admit into Ario memory.

**Next hard gates:** a separately administered policy/revocation signer A (not the user pretending to be another person), truly external C custody or HSM/managed key with scoped non-exportability and audit, independent monitoring, and mandatory sink re-verification. Same person managing all machines cannot honestly claim independent *administration*; a cloud provider operating its own transparency witnesses gives independence of log operators, but not policy-source identity.

## Pre-registered STOP/GO matrix

| Evidence | PASS means | What it NEVER proves |
|---|---|---|
| EACCES E->C and C->E | OS filesystem barriers for specific user IDs | root/admin custody separation |
| C flock concurrent nonce | one ledger spend while participants obey lock | atomic durable distributed consensus |
| Revocation checked from C journal | C correctly denies that synthetic key after local revocation | C cannot roll back its own state |
| Sigsum witnessed proof + independent monitor | external observation of signed digest | execution provenance or current head freshness |
| Independent policy admin, nonextractable custody, sink gate | future candidate for stronger security under explicit model | unconditional truth or resistance to compromise of all roles |

**Final verdict even with all R6-A tests green: `RESEARCH_ONLY / ADMIN_INDEPENDENCE_NOT_ESTABLISHED / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO`.**
