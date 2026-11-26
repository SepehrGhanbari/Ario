"""Exact checkpoint/event/message binding; reuse existing A15 verifier."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import live

def bind(first, second, pub):
    a,b=(live.parse_json(d["event.json"],32768) for d in (first,second))
    for event,d in ((a,first),(b,second)):
        raw,_=live.verify_event(event,pub)
        live.check(raw==d["checkpoint.json"],"checkpoint bytes")
        live.check(live.event_leaf_message(event)==d["event-id.txt"],"event ID bytes")
    live.successor(a,b,live.target_for_event(b),pub)

def main(root):
    root=Path(root)
    first,second=({k:(root/name/k).read_bytes() for k in ("event.json","checkpoint.json","event-id.txt")} for name in ("first","second"))
    pub=(root/"first"/"nostr.pub").read_text("ascii").strip()
    bind(first,second,pub)
    for k in ("event.json","checkpoint.json","event-id.txt"):
        bad=dict(second);bad[k]=first[k]
        try: bind(first,bad,pub)
        except (ValueError,TypeError,KeyError): pass
        else: raise RuntimeError("accepted substituted "+k)
    print("CHECKPOINT_EVENT_LEAF_BINDING_AND_3_SUBSTITUTION_CONTROLS PASS")

if __name__=="__main__": main(sys.argv[1])
