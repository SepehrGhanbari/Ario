"""Final reveal audit: compare cold recovery with withheld publisher bytes."""
import json
import sys
from pathlib import Path
import external_floor as f

def proof_fields(path):
    result={}
    for line in Path(path).read_text("ascii").splitlines():
        k,sep,v=line.partition("=")
        if sep and k in ("size","root_hash","leaf_index","log","leaf"):
            if k in result: raise ValueError("duplicate proof field")
            result[k]=v
    return result

def main(first,second,recovered,discovery):
    a,b,r=map(Path,(first,second,recovered))
    env_a=(a/"envelope.json").read_bytes(); led_a=(a/"ledger.jsonl").read_bytes()
    env_b=(b/"envelope.json").read_bytes(); led_b=(b/"ledger.jsonl").read_bytes()
    ev_a=json.loads((a/"event.json").read_text("ascii"))
    ev_b=json.loads((b/"event.json").read_text("ascii"))
    pub=(a/"nostr.pub").read_text("ascii").strip()
    plan=f.parse_json((a/"relay-plan.json").read_bytes(),8192)
    boot=f.parse_json((a/"bootstrap.json").read_bytes(),4096)
    rep=json.loads(Path(discovery).read_text("ascii").splitlines()[-1])
    recovery_report=json.loads((r/"report.json").read_bytes())
    recovered_env=(r/"envelope.json").read_bytes()
    recovered_led=(r/"ledger.jsonl").read_bytes()
    recovered_event=json.loads((r/"event.json").read_text("ascii"))
    fields_a=proof_fields(a/"event-id.txt.proof")
    fields_b=proof_fields(b/"event-id.txt.proof")
    prior_raw=(a/"prior-anchor"/"envelope.json").read_bytes()
    prior_ledger=(a/"prior-anchor"/"ledger.jsonl").read_bytes()
    prior_env=json.loads(prior_raw.decode("ascii"))
    x=f.verify_event(ev_a,pub);y=f.verify_event(ev_b,pub)
    assert f.sha(prior_raw)==f.parse_envelope(env_a)["prior_checkpoint_sha256"]
    assert f.sha(prior_ledger)==f.parse_envelope(env_a)["prior_ledger_sha256"]
    assert prior_env["record"]["ledger_sha256"]==f.sha(prior_ledger)
    assert prior_env["scope"]==f.parse_envelope(env_a)["scope"]
    assert x[0]==env_a and x[2]==led_a and y[0]==env_b and y[2]==led_b
    assert (a/"event-id.txt").read_bytes()==f.event_leaf_message(ev_a)
    assert (b/"event-id.txt").read_bytes()==f.event_leaf_message(ev_b)
    assert int(fields_a["leaf_index"])==boot["start"]
    assert int(fields_a["size"])==boot["size"]
    assert fields_a["root_hash"]==boot["root"]
    assert f.target_for_event(ev_a)==boot["first_checksum"]
    assert f.target_for_event(ev_b)==rep["matching_signed_leaves"][1]["checksum"]
    assert len(fields_a["leaf"].split())==2 and len(fields_a["leaf"].split()[1])==128
    assert len(fields_b["leaf"].split())==2 and len(fields_b["leaf"].split()[1])==128
    assert fields_a["log"]==fields_b["log"]==f.LOG_ID
    assert int(fields_b["leaf_index"])==rep["matching_signed_leaves"][1]["index"]
    assert int(fields_b["leaf_index"])>int(fields_a["leaf_index"])
    assert int(fields_b["size"])>int(fields_a["size"])
    assert fields_b["leaf"].split()[0]==fields_a["leaf"].split()[0]
    assert recovered_env==env_b and recovered_led==led_b and recovered_event==ev_b
    status,result=f.validate_successor(ev_a,ev_b,f.target_for_event(ev_b),pub,
                                       f.parse_envelope(env_a)["prior_checkpoint_sha256"])
    assert status=="RECOVERED_LINKED_SYNTHETIC_EXTERNAL_FLOOR_ONLY" and result["seq"]==8
    assert recovery_report["disposition"]==status and recovery_report["recovered_content"] is True
    assert recovery_report["forced_single_source_outage"]=="PASS_FALLBACK_FROM_OTHER_RELAY"
    assert recovery_report["stale_signed_event_replay"]=="HOLD_STALE_EVENT_REPLAY"
    assert recovery_report["both_content_sources_unavailable"]=="HOLD_CONTENT_UNAVAILABLE"
    assert recovery_report["both_unavailable_policy"]=="HOLD_OPAQUE_NEW_SIGNED_COMMITMENT"
    assert recovery_report["global_latest"]=="NOT_ESTABLISHED"
    assert recovery_report["trust_activation"]=="NO_GO" and recovery_report["production"]=="NO_GO"
    assert plan["private_key_exported"] is False
    assert plan["second_event_or_checksum_in_first_package"] is False
    names={p.name for p in a.iterdir()}
    assert "second" not in names and "second-event.json" not in names
    assert not any("private" in n.lower() or n.endswith(".key") for n in names)
    output={
      "result":"R22_20_EXTERNAL_MONOTONIC_FLOOR_RECOVERED",
      "first_seq":6,"recovered_seq":8,
      "first_sigsum_leaf_index":int(fields_a["leaf_index"]),
      "second_sigsum_leaf_index":int(fields_b["leaf_index"]),
      "second_event_id":ev_b["id"],
      "second_ledger_sha256":f.sha(led_b),
      "external_relays_accepted":plan["second_accepted_relays"],
      "external_relays_read_back":recovery_report["actual_relay_observations"],
      "forced_single_source_outage":"PASS",
      "stale_replay":"HOLD",
      "both_relays_unavailable":"HOLD_OPAQUE_NEW_SIGNED_COMMITMENT",
      "global_latest":"NOT_ESTABLISHED",
      "independent_relay_administration":"NOT_ESTABLISHED",
      "history_truth":"UNKNOWN","trust_activation":"NO_GO","production":"NO_GO",
    }
    print(json.dumps(output,sort_keys=True),flush=True)
    return output

if __name__=="__main__":
    main(*sys.argv[1:])
