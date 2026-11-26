"""Read exact historical content, never assert full suffix or latest."""
import hashlib,json,sys
from pathlib import Path
kit,first,report,out=map(Path,sys.argv[1:])
sys.path.insert(0,str(kit/'r22_21_external_deletion'))
import experiment as x
r=json.loads(report.read_text())
expected=[{'index':281668,'checksum':'46aae12df174dd36537e66612a9c51cd9c8c114569ed89d2093c7da47597c3b4'},{'index':281669,'checksum':'e0f0e3c939401d4f39498a82613f5073f66fe829ef89a1441af03520e9938ab7'}]
if r['result']!='VERIFIED_RETAINED_RANGE_ONLY' or r['retained_floor_consistency']!='PASS' or r['bootstrap_consistency']!='PASS' or r['matching_signed_leaves']!=expected or r['verified_leaf_count']!=2 or r['scan_start']!=281668 or r['scan_end_exclusive']!=281670 or r['trust_activation']!='NO_GO' or r['global_latest']!='NOT_ESTABLISHED': raise ValueError('HOLD_RANGE_REPORT')
anchor=x.read(first/'event.json');old=x.read(first/'historical-first.json')
if x.f.target_for_event(anchor)!=expected[0]['checksum']: raise ValueError('HOLD_ANCHOR')
later,obs=x.query('wss://relay.nostr.net',anchor['pubkey'],expected[1]['checksum'])
if later is None: raise ValueError('HOLD_EXTERNAL_CONTENT_UNAVAILABLE')
env,ledger=x.link(old,anchor,later,expected[1]['checksum'],anchor['pubkey'])
if hashlib.sha256(ledger).hexdigest()!='2f4dc31993e113e884ebdc0befd6b7e7a21b28282093b32e35f68531bcf0faa0': raise ValueError('HOLD_LEDGER_PIN')
out.mkdir();(out/'ledger.jsonl').write_bytes(ledger);(out/'envelope.json').write_bytes(env);x.write(out/'event.json',later)
print(json.dumps({'result':'HISTORICAL_CONTENT_MATCH_ONLY','publication':'NONE','ledger_sha256':hashlib.sha256(ledger).hexdigest(),'relay':obs,'global_latest':'NOT_ESTABLISHED','freshness':'UNKNOWN','trust_activation':'NO_GO'},sort_keys=True))
