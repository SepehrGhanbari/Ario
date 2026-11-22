"""Rebuild G4 deterministic research baseline and one G6 event, no keys or IO outside workspace.

The source transcript of the founder's actual G4 ZIP is not checked into GitHub.
Recomputed synthetic bytes are pinned to the exact audited G4 SHA256s.
"""
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import g6_extension_gate as gate

HERE=Path(__file__).resolve().parent
SRC=HERE/'spend_chain_v2.py'
if not SRC.is_file():SRC=HERE.parent/'spend_chain_v2.py'
mod=gate.frozen_module(SRC)
v2=b'';v1=b''
for n,k in [('a'*64,'1'*64),('b'*64,'2'*64),('c'*64,'3'*64)]:
    v2,status=mod.append(v2,n,k)
    if status!='NEW_NEEDS_DURABLE_APPEND':raise RuntimeError('BASELINE_GEN_FAILED')
    v1+=mod.canonical([n,k])+b'\n'
assert gate.sha(v1)==gate.G4_RAW_V1_SHA and gate.sha(v2)==gate.G4_RAW_V2_SHA, 'G4_PIN_MISMATCH'
assert gate.audited_journals(v1,v2)['head']==gate.PINNED_HEAD
next1,next2=gate.build_candidate(v1,v2,SRC)
pin={'epoch':gate.PINNED_EPOCH,'seq':3,'head':gate.PINNED_HEAD}
files={
'g4_source_v1.jsonl':v1,'g4_source_v2.jsonl':v2,
'candidate_seq4_v1.jsonl':next1,'candidate_seq4_v2.jsonl':next2,
'G6_PHONE_NOTE_UNCHANGED_SEQ3_RESEARCH_INPUT.json':(json.dumps(pin,sort_keys=True,separators=(',',':'))+'\n').encode(),
}
for name,raw in files.items():
    p=HERE/name
    if p.exists() and p.read_bytes()!=raw:raise RuntimeError('REFUSE_OVERWRITE_DIFFERENT_FIXTURE_'+name)
    p.write_bytes(raw)
print('G6_REBUILT_DETERMINISTIC_SEQ3_4_BYTES=PASS')
print('G6_NEW_HEAD='+gate.audited_journals(next1,next2)['head'])
print('G6_MINIMUM_PIN_UNCHANGED_SEQ3=PASS')