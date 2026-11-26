"""Bind direct authenticated hint to actual Nostr event and existing semantic verifier."""
import hashlib,json,sys
from pathlib import Path
kit,first,report,out=map(Path,sys.argv[1:])
sys.path.insert(0,str(kit/'r22_21_external_deletion'))
import experiment as x
r=json.loads(report.read_text())
assert r['result']=='HOLD_LATER_HINT_INCLUSION_VERIFIED' and r['complete_sampled_suffix'] is False and r['global_latest']=='NOT_ESTABLISHED'
assert len(r['matching_signed_leaves'])==1 and r['get_leaves_requests']==0 and r['proof_requests']==3 and r['rejected']==2 and r['bootstrap_replays']==1 and r['duplicate_hints']==1
target=r['matching_signed_leaves'][0]['checksum']
anchor=x.read(first/'event.json');old=x.read(first/'historical-first.json')
later,obs=x.query('wss://relay.nostr.net',anchor['pubkey'],target)
if later is None: raise ValueError('HOLD_CONTENT_UNAVAILABLE')
env,ledger=x.link(old,anchor,later,target,anchor['pubkey'])
out.mkdir();(out/'ledger.jsonl').write_bytes(ledger);(out/'envelope.json').write_bytes(env);x.write(out/'event.json',later)
# Check original expected payload digest only AFTER candidate verification and retrieval.
assert hashlib.sha256(ledger).hexdigest()=='2f4dc31993e113e884ebdc0befd6b7e7a21b28282093b32e35f68531bcf0faa0'
print(json.dumps({'result':'HINT_CONTENT_MATCH_ONLY','ledger_sha256':hashlib.sha256(ledger).hexdigest(),'publication':'NONE','global_latest':'NOT_ESTABLISHED','freshness':'UNKNOWN','relay':obs},sort_keys=True))
