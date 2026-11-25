"""Research-only readback of the existing A15 v0.8 commitments; never submits."""
import hashlib, json, sys
from pathlib import Path

# Fixed observation from the verified original run, NOT a new authority or global latest.
SIZE = 281653
ROOT = '19530988e672bb6290bf5d70e361c062d2dd990699c978a06acf1b2eff83f2af'
FLOOR_SIZE = 281670
FLOOR_ROOT = 'dafc6911b16d150b1628937dd5030ba1b188b6ffe916837d41db37e4b867cefc'
SOURCE_BLOB = '2276889ea769dd7377c26fb5f5bf2d55963e0b44'
FIRST_ZIP = '0c440d4c2871f49656b8d9d3b7502b79e071dc78d79588cd5da7309855df9d31'
RELAYS = ('wss://nos.lol','wss://relay.primal.net')

def replace_once(s, old, new):
    if s.count(old) != 1:
        raise ValueError('HOLD_SOURCE_PATCH_ANCHOR')
    return s.replace(old,new,1)

def prepare_scanner(source, output):
    raw=Path(source).read_bytes()
    blob=hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
    if blob != SOURCE_BLOB:
        raise ValueError('HOLD_SCANNER_SOURCE_PIN')
    s=raw.decode('utf-8')
    old=' end := cth.Size\n if end-start > maxLeaves { end = start+maxLeaves }'
    new=f''' // The retained checkpoint is from the earlier observed experiment, not the publisher's current state.
 retained := types.TreeHead{{Size:{SIZE}, RootHash:hash("{ROOT}")}}
 if retained.Size < prior.Size || retained.Size <= start || retained.Size-start > maxLeaves {{ log.Fatal("HOLD: retained range invalid") }}
 if cth.Size < retained.Size {{ log.Fatal("HOLD: stale relative to retained checkpoint") }}
 if cth.Size == retained.Size {{
  if cth.RootHash != retained.RootHash {{ log.Fatal("HOLD: retained checkpoint conflict") }}
 }} else {{
  proof, err := cli.GetConsistencyProof(ctx, requests.ConsistencyProof{{OldSize:retained.Size, NewSize:cth.Size}})
  require(err)
  require(proof.Verify(&retained, &cth.TreeHead))
 }}
 floor := types.TreeHead{{Size:{FLOOR_SIZE}, RootHash:hash("{FLOOR_ROOT}")}}
 if cth.Size < floor.Size {{ log.Fatal("HOLD: stale relative to later observed checkpoint") }}
 if cth.Size == floor.Size {{
  if cth.RootHash != floor.RootHash {{ log.Fatal("HOLD: later checkpoint conflict") }}
 }} else {{
  proof, err := cli.GetConsistencyProof(ctx, requests.ConsistencyProof{{OldSize:floor.Size, NewSize:cth.Size}})
  require(err)
  require(proof.Verify(&floor, &cth.TreeHead))
 }}
 // Inclusion checks use the live witnessed head, but the target range is the retained historical prefix.
 // Do not reinterpret completeness of this bounded historical range as completeness of the live suffix.
 end := retained.Size'''
    s=replace_once(s,old,new)
    s=replace_once(s,'resolve(matches,start,boot.First,cursor==cth.Size)','resolve(matches,start,boot.First,cursor==retained.Size)')
    s=replace_once(s,'"complete_sampled_suffix":cursor==cth.Size, "matching_signed_leaves":matches,','"complete_sampled_suffix":cursor==cth.Size, "complete_retained_range":cursor==retained.Size, "retained_tree_size":retained.Size, "retained_tree_root":hex.EncodeToString(retained.RootHash[:]), "retained_consistency":"PASS", "floor_size":floor.Size, "floor_root":hex.EncodeToString(floor.RootHash[:]), "floor_consistency":"PASS", "matching_signed_leaves":matches,')
    s=replace_once(s,'if discovered!=1 || disposition!=','if discovered!=2 || disposition!=')
    Path(output).write_text(s,encoding='utf-8')

def verify_retained_discovery(boot,report):
    """Called only on output of the locally executed pinned scanner, not a caller-supplied proof."""
    import re
    if not (report.get('retained_tree_size')==SIZE and report.get('retained_tree_root')==ROOT
            and report.get('retained_consistency')=='PASS' and report.get('complete_retained_range') is True
            and report.get('scan_end_exclusive')==SIZE and type(report.get('sampled_tree_size')) is int
            and report['sampled_tree_size']>=FLOOR_SIZE and report.get('scan_start')==281650
            and report.get('verified_leaf_count')==3 and report.get('global_latest_scope')=='NOT_ESTABLISHED'
            and report.get('floor_size')==FLOOR_SIZE and report.get('floor_root')==FLOOR_ROOT
            and report.get('floor_consistency')=='PASS'):
        raise ValueError('HOLD_RETAINED_RANGE_REPORT')
    if report['sampled_tree_size']==FLOOR_SIZE and report.get('sampled_tree_root')!=FLOOR_ROOT:
        raise ValueError('HOLD_RETAINED_HEAD_CONFLICT')
    matches=report.get('matching_signed_leaves')
    if not (report.get('disposition')=='HOLD_OPAQUE_NEW_SIGNED_COMMITMENT'
            and report.get('new_opaque_signed_commitments')==2 and type(matches) is list and len(matches)==3
            and matches[0]=={'index':boot['start'],'checksum':boot['first_checksum']}):
        raise ValueError('HOLD_MATCH_COUNT')
    seen=set()
    for i,m in enumerate(matches):
        if not (type(m) is dict and set(m)=={'index','checksum'} and type(m['index']) is int
                and m['index']==281650+i and isinstance(m['checksum'],str)
                and re.fullmatch('[0-9a-f]{64}',m['checksum']) and m['checksum'] not in seen):
            raise ValueError('HOLD_MATCH_ORDER')
        seen.add(m['checksum'])
    return matches

def recover(first, reportfile, output, mode):
    if mode not in ('only-nos','only-primal','both'):
        raise ValueError('HOLD_RELAY_MODE')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'a15_r22_external_order'))
    import transport
    first=Path(first);output=Path(output)
    # Same transport and cryptographic verification; replace only its discovery-report policy.
    # Keep the original report intact, never mark historical range as a complete live suffix.
    transport.verify_discovery=verify_retained_discovery
    transport.env.RELAYS=RELAYS if mode=='both' else (RELAYS[0 if mode=='only-nos' else 1],)
    transport.recover(first,Path(reportfile),output)
    print(json.dumps({'mode':mode,'status':'HISTORICAL_READBACK_ONLY','global_latest':'NOT_ESTABLISHED','production':'NO_GO'}))

if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='prepare':prepare_scanner(*sys.argv[2:])
    elif len(sys.argv)==6 and sys.argv[1]=='recover':recover(*sys.argv[2:])
    else:raise SystemExit('HOLD_ARGUMENTS')
