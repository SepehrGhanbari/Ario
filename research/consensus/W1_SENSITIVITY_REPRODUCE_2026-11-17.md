# W1 input sensitivity — exact local reproduction recipe

Research-only offline demo; not a new certification of witness independence.

## Requirements

- Checked out Ario branch containing **exactly** `implementation/witness_provenance_experiment.py` blob `4faf010d73219af63c254097e9c135da68d60078` (26,726 bytes); the script fails closed when this pin mismatches.
- CPython 3.13.5 tested locally. Source script is stdlib-only and syntactically compatible with Python 3.11+. CI on other versions is separately required; do not assert it passed before observing real run logs.
- No installed network libraries, keys, credentials or external services required.

From repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s research/consensus -p 'test_w1_adversarial_input_sensitivity_v1.py' -v
PYTHONDONTWRITEBYTECODE=1 python -B research/consensus/w1_adversarial_input_sensitivity_v1.py
```

To save a result into a **new** file (the tool explicitly refuses overwriting existing file):

```bash
PYTHONDONTWRITEBYTECODE=1 python -B research/consensus/w1_adversarial_input_sensitivity_v1.py --json-out /tmp/w1-new-results.json
```

Be careful: the first step only checks model-harness consistency. The synthetic cases and expectations were authored by the experiment designers, so this is **not** a blinded benchmark. The 192 permutations exercise *invariance*, not 192 independent test conditions. The script's `latent_relation` metadata is never presented to the evaluator.

`--json-out` is opt-in; the default CLI prints only an aggregate; no modification to Ario memory, signing, or operational files. The script reads the pinned source byte image once, verifies Git blob and SHA-256 before executing that same image, and forbids oversized source input. Run in an isolated development environment as with any research code.

Do not change or merge production signer, trust activation, authorization, memory or `main` as part of these experiments.
