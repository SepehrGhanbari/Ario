#!/usr/bin/env python3
"""W8 source-pinned synthetic chain: source guard -> candidate filter -> semantic node -> prospective cue.
NO real tool invocation, external API, memory ledger, downstream task dispatcher, or signer.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

DIR = Path(__file__).parent
PIN = {
 "source_monitoring": "b3b500ebc8736aa5475d117f508a769a39b78d6d",
 "memory_consolidation": "b131bab9047d0c579e6a0dda6c0ee26861ef0100",
 "prospective_memory": "3991f38f4d6ed1b51c0753bec54dd66c446d9e25"
}
def load(name):
    path=DIR/(name+"_PR210_pinned.py")
    raw=path.read_bytes()
    actual=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
    if actual!=PIN[name]:
        raise ValueError(f"{name}: Git blob mismatch {actual}")
    spec=importlib.util.spec_from_file_location("w8_"+name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

s=load("source_monitoring")
m=load("memory_consolidation")
p=load("prospective_memory")

def scenario(exit_code):
    g=s.SourceMonitoringGuard(allowlisted_tools={"inspect_directory"})
    engine=m.ConsolidationEngine()
    pro=p.ProspectiveMemoryRegistry()

    claim=g.create_hypothesis("Target A exists",attribution_id=f"CLAIM_{exit_code}")
    stdout="NOT_FOUND: Target A" if exit_code==0 else "ERROR: refused"
    observation=g.record_empirical_observation(
      assertion="Synthetic directory check completed",tool="inspect_directory",target="Target A",
      exit_code=exit_code,stdout=stdout,execution_lock="pure-synthetic-lock",
      expected_execution_lock_sha256=hashlib.sha256(b"pure-synthetic-lock").hexdigest(),
      expected_stdout_sha256=hashlib.sha256(stdout.encode()).hexdigest(),
      attribution_id=f"OBS_{exit_code}")

    try:
        g.evaluate_claim_promotion(claim.attribution_id,[observation.attribution_id])
    except s.SelfCitationError:
        pass
    selected=g.filter_working_memory_candidates([claim.attribution_id],require_verified=True)

    if selected:
        event={"concept":"synthetic_fs_claim","assertion":selected[0].assertion,
               "source_type":selected[0].source_type.value,
               "veracity":selected[0].veracity_state.value,
               "source_attribution_id":selected[0].attribution_id}
        data=json.dumps(event,sort_keys=True,separators=(",",":")).encode()
        engine.ingest_event_stream([(hashlib.sha256(data).hexdigest(),event)])

    nodes=engine.retrieve_active_context("synthetic_fs_claim")
    pro.register_intention(description="Synthetic review marker only",
        predicate_expr="concept == 'synthetic_fs_claim' and status == 'ACCEPTED'",
        action_payload={"kind":"synthetic_status_marker_only"},
        created_at_epoch=100.0,ttl_epoch=200.0,
        source_attribution_id=claim.attribution_id,
        intention_id=f"INT_{exit_code}")
    if nodes:
        cue={"concept":nodes[0].concept,"status":nodes[0].status.value}
    else:
        cue={"concept":"synthetic_fs_claim","status":"UNKNOWN"}
    fired=pro.evaluate_cues(cue,current_epoch=150.0)
    return {
      "scenario":"stdout_NOT_FOUND_but_exit_0" if exit_code==0 else "exit_1_nonpromotion_control",
      "tool_exit":exit_code,
      "stdout":stdout,
      "hypothesis_veracity":g.attributions[claim.attribution_id].veracity_state.value,
      "verified_memory_candidates":len(selected),
      "consolidated_nodes":len(nodes),
      "node_status":nodes[0].status.value if nodes else "NONE",
      "prospective_triggered_count":len(fired),
      "prospective_status":pro.intentions[f"INT_{exit_code}"].status.value,
      "task_executed":False
    }

bad=scenario(0)
blocked=scenario(1)
assert bad["hypothesis_veracity"]=="VERIFIED_EMPIRICAL" and bad["verified_memory_candidates"]==1,bad
assert bad["node_status"]=="ACCEPTED" and bad["prospective_triggered_count"]==1,bad
assert blocked["hypothesis_veracity"]=="UNSUPPORTED" and blocked["verified_memory_candidates"]==0,blocked
assert blocked["consolidated_nodes"]==0 and blocked["prospective_triggered_count"]==0,blocked
print(json.dumps({"schema":"ARIO-W8-SYNTHETIC-THREE-MODULE-TRACE-v1",
  "source_head":"07068bdfa36abb29a3ce8e927077df3ffe02b0cf",
  "verified_git_blobs":PIN,
  "results":[bad,blocked],
  "external_actions_executed":False,
  "live_memory_mutated":False,
  "note":"This is a synthetic end-to-end prototype status/cue path and intentionally contradictory stdout. No actual task dispatcher, production signer, or conversational Ario was invoked."},indent=2,sort_keys=True))
