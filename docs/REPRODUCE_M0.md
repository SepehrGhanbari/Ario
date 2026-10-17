# Reproduce the deterministic M0 audit

This procedure runs the existing M0 engine on three small synthetic fixtures and
then runs the implementation regression suite. No model, Ollama server, API key,
network service, production ledger, signing authority or external dataset is
needed to execute the demo. Installation initially requires access to Python
packages, or an independently prepared local wheel directory.

## Version and dependencies

Use CPython **3.13**. The reference engine is `M0-1.2` at main commit
`b8652f94d7d57272371d0a8347002ca324659ca1`. Record the commit containing this
pack with `git rev-parse HEAD`; a checkout of that older reference commit alone
does not contain these new files. Use the exact pack commit when comparing runs.

The existing [Implementation Regression workflow](../.github/workflows/implementation-regression.yml)
already runs the complete suite on Python 3.13. Its successful
[main run 39020072817](https://github.com/SepehrGhanbari/Ario/actions/runs/39020072817)
used Python 3.13.16, pytest 9.1.1 and cryptography 46.0.4 and reported **1,022
passed, 92 subtests passed** before this pack was added. Those are historical CI
counts, not a prediction for later commits or different environments.

M0, its JSON runtime and this demo use only Python's standard library.
`implementation/requirements-research.txt` pins the two direct test dependencies:

- `pytest==9.1.1`, including its built-in subtest support;
- `cryptography==46.0.4`, already required by the W4-C synthetic signature tests.

Neither is a new production dependency. The requirements file is a minimal
direct-dependency pin, not a transitive or hash-locked environment. Pip resolves
platform-dependent dependencies such as cffi and colorama. Record `pip freeze`
to identify the actual resolved environment; keep wheel hashes as well if exact
offline package reconstruction is required. Do not install a separate
`pytest-subtests` plugin for this procedure.

## Obtain a separate checkout

Clone the repository into a new directory, then check out the exact commit
containing this pack. Preserve existing workspaces and pending changes.

```text
git clone https://github.com/SepehrGhanbari/Ario.git Ario-research
cd Ario-research
git rev-parse HEAD
git status --short
```

All subsequent commands start at that repository root unless stated otherwise.
The commands below keep the environment outside the checkout and disable Python
bytecode and pytest cache writes. Regression tests still create disposable
fixtures in the operating system's temporary directory.

## Windows PowerShell

```powershell
py -3.13 -m venv ..\ario-m0-venv
$python = (Resolve-Path ..\ario-m0-venv\Scripts\python.exe).Path
$env:PYTHONDONTWRITEBYTECODE = "1"
& $python --version
& $python -m pip install -r implementation/requirements-research.txt
& $python -m pip check
& $python -m pip freeze
& $python -B implementation/m0_reproducibility_demo.py
```

Use a new virtual environment path if that name already exists. If the Windows
Store launcher is inaccessible, substitute the absolute path of an installed
CPython 3.13 executable for `py -3.13`. No activation script is needed.

Compile both new sources in memory (without creating `.pyc` files), then test:

```powershell
& $python -B -c "from pathlib import Path; paths = ('implementation/m0_reproducibility_demo.py', 'implementation/tests/test_m0_reproducibility_demo.py'); [compile(Path(p).read_bytes(), p, 'exec') for p in paths]; print('2 sources compiled')"
Push-Location implementation
& $python -B -m pytest -p no:cacheprovider -q tests/test_m0_reproducibility_demo.py
& $python -B -m pytest -p no:cacheprovider -p tests.test_m0_reproducibility_demo -q tests
Pop-Location
```

Check `$LASTEXITCODE` immediately after each Python command. Each should be 0.

The full Windows command explicitly loads the new test module as an optional
pytest plugin. Its `pytest_make_parametrize_id` hook shortens display IDs for
byte parameters longer than 256 bytes using their length and SHA-256. An existing
W4-B test supplies 65,537 bytes; the default ID exceeds Windows' 32,767-character
environment-variable limit in pytest setup/teardown. The hook changes only the
display ID, preserving the entire payload, test body, assertions and collection.
It skips no tests. No existing test or workflow needs modification. Linux/macOS
can use the ordinary command below; the hook is also portable if desired.

## Linux / macOS shell

```sh
python3.13 -m venv ../ario-m0-venv
PYTHON="$(cd ../ario-m0-venv/bin && pwd)/python"
export PYTHONDONTWRITEBYTECODE=1
"$PYTHON" --version
"$PYTHON" -m pip install -r implementation/requirements-research.txt
"$PYTHON" -m pip check
"$PYTHON" -m pip freeze
"$PYTHON" -B implementation/m0_reproducibility_demo.py
"$PYTHON" -B -c "from pathlib import Path; paths = ('implementation/m0_reproducibility_demo.py', 'implementation/tests/test_m0_reproducibility_demo.py'); [compile(Path(p).read_bytes(), p, 'exec') for p in paths]; print('2 sources compiled')"
(cd implementation && "$PYTHON" -B -m pytest -p no:cacheprovider -q tests/test_m0_reproducibility_demo.py)
(cd implementation && "$PYTHON" -B -m pytest -p no:cacheprovider -q tests)
```

Check each exit status (`echo $?`) immediately. These portable shell commands
describe the same procedure; local validation of this pack was on Windows.

## Inputs and output

Print all complete input requests without auditing them:

```text
python -B implementation/m0_reproducibility_demo.py --inputs
```

Here and below, `python` means the virtual environment executable selected above.
Each printed request can be saved individually as UTF-8 JSON and replayed with
the existing runtime: `python -B implementation/ario_cli.py --input request.json`.
The printed top-level object is a mapping of case names to requests; it is not
itself a single runtime request. For example, the essential empty request is:

```json
{"audit_id":"DEMO-empty_input","rule_versions":["M0-1.0"],"configuration_id":"M0-REPRODUCIBILITY-DEMO-1","execution_timestamp":"2026-10-17T00:00:00Z","artifacts":{}}
```

The other two cases each supply exactly one claim, one observation, one evidence
wrapper and one assessment. Their declared ancestry is
`DEMO-A1 -> DEMO-E1 -> DEMO-O1 -> DEMO-C1`. Both observation and assessment bind
to `DEMO-C1`. The claim status stays `UNKNOWN`; the evidence declares `DEPENDENT`.
The fixed timestamp and all identifiers are fixture labels, not observed events.

| Case | Requested use / property | Actual representative verdict | Violations | Use disposition |
|---|---|---|---|---|
| `empty_input` | No artifacts | `UNKNOWN` | `[]` | No assessment |
| `record_presence` | `RECORD_DESCRIPTION` / `SUPPLIED_RECORD_PRESENT` | `PASS` | `[]` | `RECORD_DESCRIPTION_ONLY` |
| `self_support` | `INDEPENDENT_TARGET_SUPPORT` / `SYNTHETIC_PROPERTY` | `FAIL` | `["EVIDENCE_INADMISSIBLE"]` | `KNOWN_INADMISSIBLE` |

The presence case uses the engine's fixed `M0-EAG-RECORD-PRESENCE-0.1` rule and
`SUPPLIED_INPUT_RECORDS_ONLY` scope. It reports presence `MATCH`. The independent
support case exposes exact self-confirmation and reports presence
`NOT_EVALUATED`. Both resolve the declared ancestry within the supplied snapshot;
neither authenticates a source.

The demo prints a JSON object with `demo_version` and `cases`. Each case includes
the full real runtime `result` (including `verdict_basis`) and its parsed
`ancestry_findings`. For example, this is a **selected-fields excerpt**, not the
complete output:

```json
{"case":"record_presence","result":{"verdict":"PASS","violations":[]},"ancestry_findings":{"claim_truth":"UNKNOWN","entity_continuity":"UNKNOWN","independent_admission_authority":"NONE"}}
```

The demo's process exit 0 means it executed and serialized its results. The
intentional `FAIL` audit is a successful negative control, not a process failure.
Unexpected runtime/decoding failures propagate as nonzero process errors.

## Interpretation and evidence limits

```text
OBSERVED != INTEGRITY_CHECKED != SOURCE_AUTHENTICATED != REVIEW_AUTHORIZED != ADMITTED != TRUE
```

A structural `PASS` means only that the implemented checks found no violation
for the supplied inputs and rules. Here it establishes only literal presence of
a supplied claim record. It does not establish the claim's truth, independent
origin, historical occurrence, quotation fidelity, identity or consciousness.
A `FAIL` refuses the requested structural/evidentiary use; it does not prove a
claim false. `UNKNOWN` remains a valid open state. Under the current engine,
an `UNKNOWN` violation on a primary-artifact request contributes to aggregate
`FAIL`; an empty primary input instead returns verdict `UNKNOWN`.

The engine owns the mandatory `M0-REF-GUARD-1.0` and `M0-EAG-0.1` guards. The
demo declares only `M0-1.0`; omission from the caller's list does not disable
those guards. Parsed findings are reporting, not credentials. Consult the
[ancestry contract](../implementation/M0_EVIDENCE_ANCESTRY_GUARD_SPEC_V0_1.md),
[reference firewall contract](../implementation/M0_F11_F15_SECURITY_CONTRACT_V1.md)
and [JSON runtime guide](../implementation/M0_JSON_RUNTIME_V1.md) for boundaries.

## Capture a reproducible run

Record the pack commit, OS, Python version, `pip freeze`, exact commands, exit
codes and pytest summaries. Save both `--inputs` and demo output outside the
checkout. The demo uses no clock, randomness or absolute paths; its JSON output
is stable for identical code and inputs, including across Python hash seeds.
For cross-platform byte comparison, normalize console CRLF/LF to LF before
hashing. A matching SHA-256 establishes byte equality, not authenticity or truth.

For source hashes use `Get-FileHash -Algorithm SHA256` on Windows or `sha256sum`
on Linux (macOS: `shasum -a 256`) for each of the four pack files. Hash saved
input/output bytes as well. Do not compare console timing or pytest progress
lines as deterministic scientific outputs. The demo fixtures cover these three
bounded scenarios; passing them does not prove all M0 behavior or production
security. Future changes may legitimately alter counts, versions or outputs.

## Troubleshooting

- `No module named core` or another local module: run the demo by its script path
  from the root; run pytest from `implementation` as shown. No editable package
  installation or global `PYTHONPATH` change is needed.
- Missing pytest/cryptography or unsupported subtests: check the selected
  interpreter with `python --version` and `python -m pip --version`; install the
  pinned requirements into that same new environment. Avoid ambient plugins;
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` can isolate a contaminated environment.
- Package download failure: check network/index access. For offline use, obtain
  compatible CPython 3.13/platform wheels and dependencies first, then use
  `python -m pip install --no-index --find-links WHEEL_DIRECTORY -r implementation/requirements-research.txt`.
  Record their provenance and hashes. Do not silently substitute versions.
- Temporary-directory permission error: select a writable operating-system
  temporary directory for this run. Preserve existing caches and historical
  outputs; do not clean unrelated workspaces to make tests pass.
- Windows `ValueError: the environment variable is longer than 32767 characters`
  from pytest: use the full Windows command with the explicit display-ID plugin
  above. This is a runner limitation on an existing large byte parameter, not an
  audit verdict. Preserve the original error when reporting validation.
- Unexpected verdict or failed test: retain the complete input, full result,
  environment and exact failure. Compare the commit and bindings before drawing
  a conclusion. Do not weaken epistemic checks to match this example.
