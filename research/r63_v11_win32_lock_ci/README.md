# R63 V11 — Win32 separate-process witness and journal concurrency handoff

**Decision:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO

## Frozen source
Founder's original `R63-V9-Evidence.zip` SHA-256:
`db8f1b1a76795589d905fac3f52c1ec32323611585897dd9eb94b259ec6581e9`.

The new laboratory uses the original extracted `spend_chain_v2.py` SHA-256:
`c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd`.

V9's actual witness RPC runs in a daemon thread within the driver and uses a Python thread lock. This is not independently restartable and is not an inter-process lock.

## Scoped proof: Windows CI
Source: `research/r63_v11_win32_lock_ci/test_win32_cross_process_exclusion.py`, workflow `.github/workflows/r63-v11-win32-exclusion.yml`.

**Run:** [44354525767](https://github.com/SepehrGhanbari/Ario/actions/runs/44354525767), Windows Server 2022. The job log confirms:
- `EXCLUSIVE_WIN32_SECOND_PROCESS_BLOCKED=PASS`
- `CRASH_RELEASED_OS_LOCK=PASS`
- `MULTIPROCESS_CLIENTS_2=PASS`
- `MULTIPROCESS_CLIENTS_8=PASS`
- `MULTIPROCESS_CLIENTS_16=PASS`
- `CROSS_PROCESS_EXCLUSION=PASS`
- **Deliberate failing assumption demonstrated:** `UNCOOPERATIVE_WRITER_CAN_BYPASS_LOCK=EXPECTED_COUNTEREXAMPLE`.

Implementation uses Windows `CreateFileW(GENERIC_READ|GENERIC_WRITE, shareMode=0, OPEN_ALWAYS)` on a dedicated lock file, with handle held across review/write in cooperating code and automatically released by Windows on process exit. This is OS-enforced sharing exclusion for the *lockfile*, **not** a mandatory lock on the two journal files. A non-cooperating process (including a same-admin writer) can modify V1/V2 without taking that lock. Nothing here proves malicious-writer protection, independent custody, power-loss durability or native V9 integration.

## Founder-operated Sandbox candidate
Prepared a chat-only package `Ario-R63-V11-Separate-Witness-Windows-Sandbox.zip`, SHA-256:
`08139480300ac9d98b068d64aa10eb238b9718a17cc1b65b4a36f4090fdbadc9` (13,571 bytes; 8 members, 7/7 SHA256 manifest entries matched).

This package is **not checked into GitHub** due to user-machine-specific Sandbox mapping configuration. Static source validation and manifest checks passed; **the complete package has not yet been run in the founder's Windows Sandbox**.

Package contains:
- a **separate** `witness_parent.py` loopback TCP RPC server process using the Win32 file-sharing lock;
- a separate `witness_lab.py` controller and independent standard Python *processes* as RPC clients;
- exactly pinned historical V9 V2 sidecar source;
- fresh disposable per-scenario guest temporary journals and isolated synthetic token;
- a Windows Sandbox `.wsb` with **networking disabled, clipboard disabled, no LogonCommand/autorun**, input mounts read-only and a writable evidence-only export;
- a fail-closed guest-only `.cmd` launcher requiring the Windows Sandbox account and known read-only source/runtime mounts;
- Persian operator instructions and SHA256SUMS.

Planned guest-only observations: standalone Win32 lock holder blocks a contender; OS releases handle after holder exit; 2/8/16 independent clients produce exactly one new **reservation-only** record per group (not a signature); fault injection `crash_pre_v2`, `crash_post_v2`, `crash_post_v1` exits the witness RPC parent with 73 and restarts a new PID; pending uncertainty flag causes **HOLD_UNCERTAIN** without new append. Archived raw V1/V2 and bounded machine-readable report are exported to the founder only after PASS. No signer, CNG, SCM service, account, ACL or real key use.

## Strict evidence boundary
**PROVEN IN CI:** Windows-exclusive lock-file admission for cooperating processes, death-triggered handle release, 2/8/16 client reservation serialization, same-user uncooperative journal-writer counterexample.

**NOT EXECUTED:** exact guest package in user's Windows Sandbox; actual V9 witness RPC process split, LocalService/StandardUser SID separation, original signer crash, use-completeness, native receipt recovery, power cut, external witness custody.

**Next safety gate after the user-supplied guest report:** design an actual **journal-protecting transaction boundary** (not just a separate cooperative lockfile), enforce authorized write access with distinct OS identities or a restricted writer service in disposable guest, then retest file mutation attempts both with and without the lock. Do not treat two PIDs as independent administrative custody.

**No** original V9 ZIP rewrite, main merge, Ruleset modifications, host security changes, production keys or trust activation.
