# Ario Local Ollama Planner V1

## Purpose

\`ario_planner.py\` connects a locally running Ollama model to Ario's bounded workflow runtime. It collects a bounded read-only workspace inventory and Git status, adds a bounded allowlist of implementation/test excerpts, asks the local model for a declarative workflow, validates the response against \`ario_workflow.py\`, validates relative paths, and assigns runtime task IDs locally.

The planner does not read arbitrary workspace files. In addition to the metadata inventory, it reads small excerpts from a fixed allowlist of implementation modules and regression tests (at most four files, 4,000 bytes per file, and 16,000 characters total) and sends those excerpts to the local Ollama model as untrusted planning context. It does not read user files, secrets, or arbitrary paths for this context. The model can request bounded \`read_text\` steps in its proposed workflow; those steps only run if execution is explicitly requested.

## Requirements

- Python 3.13 (same as the implementation regression workflow)
- Ollama running locally at \`http://127.0.0.1:11434\`
- The selected model already pulled into Ollama; default: \`qwen2.5:7b\`

No third-party Python dependency is added. The planner uses the Python standard library and the existing Ario runtime. Ollama recommends a bounded engineering question and rationale only; it does not author workflow stages, conditions, action lists, or operational identifiers. Ario validates that recommendation and builds a fixed one-stage, two-action, read-only workflow locally.

## Plan only (default)

Run from the repository root in PowerShell:

\`\`\`powershell
python .\implementation\ario_planner.py --goal "Inspect the Ario implementation and identify the next bounded engineering task" --workspace "$HOME\Ario" --ledger "$HOME\Ario\runtime\agent-events.jsonl"
\`\`\`

The command prints JSON with \`status: PLAN_READY\` and the validated workflow. It does not execute the workflow and does not append to the execution ledger.

The Ollama request timeout defaults to 300 seconds. Use `--timeout 600` for slower local inference; accepted values are 1–1800 seconds.

## Explicit execution

To ask the local model for a plan and immediately execute that exact in-memory plan through the bounded runtime:

\`\`\`powershell
python .\implementation\ario_planner.py --goal "Inspect the Ario implementation and identify the next bounded engineering task" --workspace "$HOME\Ario" --ledger "$HOME\Ario\runtime\agent-events.jsonl" --execute
\`\`\`

\`--execute\` is intentionally explicit. The runtime still enforces the strict workflow/task schemas, relative workspace paths, allowlisted tools, duplicate-ID checks, exclusive locks, guarded replacement/restore, and postcondition checks. A model-generated plan is not itself evidence that the goal was achieved; the final status and observations must be examined.

## Boundaries

- Only plain HTTP loopback Ollama endpoints are accepted; remote hosts and HTTPS endpoints are rejected. When `localhost` is supplied, Ario validates its DNS results and rewrites the endpoint to the validated numeric loopback address so the HTTP client does not resolve the hostname a second time.
- The metadata inventory lists at most 250 workspace entries, omits common generated/dependency directories and symbolic links, and includes bounded Git status text. Separate planning context is restricted to the fixed allowlist and size limits above.
- Ollama responses are capped at 1 MB. The goal is capped at 2,000 characters. The existing workflow limit is eight stages and each task is limited to eight actions.
- Unknown fields, unsupported tools, invalid branch conditions, and workspace path escapes are rejected before execution.
- Unresolved model template values (for example, `unique-id` or `short task goal`) are rejected; they cannot be reported as `PLAN_READY`.
- If the model returns a workflow with an invalid top-level schema, the planner sends one schema-specific correction request. It stops with `UNKNOWN` if the second response is still invalid; it does not execute an invalid plan. The prompt explicitly requires the first stage to omit `when` and later conditions to reference only exact earlier stage IDs.
- The model returns only four recommendation fields: an approved implementation path, its paired regression-test path, one bounded engineering question, and a short rationale. Both files must be present in the bounded planning context. Ario constructs the workflow locally with one fixed stage and two distinct `read_text` actions, so model-generated duplicate stage IDs, conditions, action IDs, or write instructions cannot enter the workflow schema. Workflow and task IDs are generated locally for each run.
- The model is instructed not to invent SHA-256 preconditions. A write that lacks a correct current hash fails closed; a planner response cannot bypass runtime validation.
- The planner prioritizes `ario_planner.py` and its regression tests in the bounded context. Its prompt now requires exactly one stage with two distinct `read_text` actions: an observed implementation module and its relevant test file. Directory listings are disallowed for this request because inventory is already supplied. The task goal must name both paths and one concrete bounded engineering question. A post-schema quality gate still rejects repeated identical actions and directory-only plans; these constraints improve evidence quality but do not establish that the proposed task is the best possible task.
- The plan may still be wrong, incomplete, or semantically inadequate. Exact postconditions and the append-only application ledger provide bounded checks, not proof of general correctness or tamper-proof history.
- This is local model-assisted planning, not unrestricted autonomy. There is no arbitrary shell tool, arbitrary network tool, automatic retry, or automatic repair loop.

## Deterministic inspection planning (no Ollama required)

The existing local-model engineering recommendation mode is unchanged. For explicit audit/ledger/revision goals, a second input mode compiles the already merged Agent consumers (#431–#433) into an ordered read-only Workflow. The request is a bounded JSON object with a goal and one or more of the following optional input groups:

```json
{
  "goal": "Check prior execution and supplied assessment revision",
  "ledger": {"path": "prior.jsonl", "manifest_path": "manifest.json", "expected_sha256": "<manifest SHA-256>"},
  "audit": {"path": "audit.json", "expected_sha256": "<audit input SHA-256>"},
  "revision": {"path": "after.json", "expected_sha256": "<after SHA-256>", "prior_path": "before.json", "prior_sha256": "<before SHA-256>"}
}
```

All hashes are real caller-supplied 64-hex pins; placeholders above are not executable. Omit a group if its inputs are unavailable or the inspection is not wanted. No model is called, no hashes are guessed, and no data file is submitted to a model. The planner selects the fixed tool for each supplied group and executes stages in ledger → audit → revision order, stopping normal continuation on failure. A successful synthetic revision can still return epistemic UNKNOWN. The three groups need not describe the same claim; this sequence proves neither cross-input identity nor causal linkage. Planning alone only validates schema and paths; the tools check bytes at execution. The active output ledger is not accepted as an input. The request file itself is limited to 16 KiB.

```powershell
python .\implementation\ario_planner.py --inspection-request "$env:TEMP\inspection.json" --workspace "$HOME\Ario" --ledger "$HOME\Ario\runtime\inspection-events.jsonl"
```

Add the existing explicit `--execute` flag to execute the generated workflow. No automatic action from free-form model output, generalized belief revision, evidence admission or production authority is introduced.
