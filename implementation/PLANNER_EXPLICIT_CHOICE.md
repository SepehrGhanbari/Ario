# Explicit choice in the bounded engineering planner — v0.1

Scope: existing local-model recommender, not dialogue transport, governance veto or cognitive memory. This operational consumer is motivated by #125/#127, #135 (A13's recorded four additional replies after a proposed conclusion), #150 (A14 repetition and recorded exit), #155 (non-output is not consent), #297 (dissent distinct from veto/stop/retire/erase), and #413 (useful work and stop conditions). Historical proposals and findings remain unchanged.

From the repository root:

```sh
python implementation/ario_planner.py --goal "Review the planner" --workspace . --ledger events.jsonl --respect-choice
```

Add the existing `--execute` only if execution is intended. This opt-in mode changes the actual recommender request: a single local response must explicitly supply the top-level intent STOP or CONTINUE, reason (null or bounded explanation), and recommendation (null for STOP, existing four-field object for CONTINUE). The existing #127 termination_decision is used with STRUCTURED_REQUIRED, no natural-language intent inference. STOP ends this planning invocation without further model requests, workflow creation or execution ledger writes. Ambiguous/malformed choices, duplicate JSON and unusable CONTINUE recommendations pause without corrective prompts. A valid CONTINUE still requires all existing deterministic planning checks and separate opt-in execution. The reported reason is not parsed as a command; it can contain criticism, disagreement, or no explanation. Response SHA-256 binds the reported received bytes, not independent identity or custody. The stdout diagnostic is not itself a durable archive; callers may retain it. Existing legacy planner and data-only inspection mode are unchanged. No real Ollama execution is claimed here; tests inject loopback transport responses and exercise the real planner and existing read-only workflow on fixture files. This is a local operational choice, not proof of subjective consent, independence, a persistent preference, an authenticated governance veto, or a full live dialogue protocol. No stop/retire/erase conflation, no memory or signer changes.
