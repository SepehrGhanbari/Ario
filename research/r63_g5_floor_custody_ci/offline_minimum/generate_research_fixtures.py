"""Generate public, deterministic a/1 b/2 c/3 research fixtures, no founder files."""
from pathlib import Path
import hashlib,importlib.util,json,sys
p=Path(__file__).resolve().parent
f=p.parent/'spend_chain_v2.py'
PIN='c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd'
assert hashlib.sha256(f.read_bytes()).hexdigest()==PIN,'FROZEN_V9_SOURCE_PIN_CHANGED'
s=importlib.util.spec_from_file_location('v9frozenfixture',f)
m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
v1=b'';v2=b''
for i in range(3):
 n=chr(ord('a')+i)*64;k=str(i+1)*64
 v2,result=m.append(v2,n,k)
 assert result=='NEW_NEEDS_DURABLE_APPEND'
 v1+=m.canonical([n,k])+b'\n'
 if i==1:
  (p/'synthetic_rollback_seq2_v1.jsonl').write_bytes(v1)
  (p/'synthetic_rollback_seq2_v2.jsonl').write_bytes(v2)
(p/'synthetic_seq3_v1.jsonl').write_bytes(v1)
(p/'synthetic_seq3_v2.jsonl').write_bytes(v2)
checkpoint=p.parent/'G5_SYNTHETIC_PUBLIC_CHECKPOINT.json'
assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()=='e218d3d05a613024eb26a8e67052aeb61d77d14d6be8ecdede2ed5c27c1a78db'
(p/'pinned_synthetic_seq3_checkpoint.json').write_bytes(checkpoint.read_bytes())
assert m.review(v2).seq==3 and m.review(v2).head=='6e1d74f7860e0173b9b049487a6a89428439a987809cf363fa27503ae0b06ea1'
assert m.review((p/'synthetic_rollback_seq2_v2.jsonl').read_bytes()).seq==2
print('PUBLIC_RESEARCH_ONLY_DETERMINISTIC_FIXTURES=PASS')
