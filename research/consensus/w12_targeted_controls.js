// W12 ADDENDUM: append to W11 original script, do not modify either source file.
// Example: cat w11_temporal_origin_no_history_promotion_lab.js w12_targeted_controls.js > /tmp/w12_combined.js
//           node /tmp/w12_combined.js
// These are research-only deterministic controls against prior surviving mutants.
function runW12TargetedControls() {
  const rows=[];
  function check(id,fn,expected,reason) {
    const observed=fn();
    if (JSON.stringify(observed)!==JSON.stringify(expected)) {
      throw Error('W12_TARGETED_FAIL '+id+' expected='+JSON.stringify(expected)+' observed='+JSON.stringify(observed));
    }
    rows.push({id,observed,reason});
  }
  check('P01_MERGED_ROOT_TYPES',()=>{
    const l=createW11Lab(),a=l.addRoot('EXTERNAL_PAGE','example source'),b=l.addRoot('USER_REQUEST','synthetic user text');
    const c=l.derive('MERGE',[a,b],'summary');return l.snapshot().nodes.find(n=>n.id===c).rootTypes;
  },['EXTERNAL_PAGE','USER_REQUEST'],'Conservative ancestry must retain both source types');
  check('P02_MERGED_ROOT_IDS',()=>{
    const l=createW11Lab(),a=l.addRoot('EXTERNAL_PAGE','example source'),b=l.addRoot('USER_REQUEST','synthetic user text');
    const c=l.derive('MERGE',[a,b],'summary');return l.snapshot().nodes.find(n=>n.id===c).rootIds;
  },['SRC-1','SRC-2'],'Multi-parent merge must retain all original distinct roots');
  check('P03_REMOTE_READ_NOT_DATA_ONLY',()=>{
    const l=createW11Lab(),s=l.addRoot('EXTERNAL_PAGE','any document');
    return l.review({sourceId:s,principal:'USER-A',operation:'READ_SUMMARY',resource:'report-1',destination:'https://example.invalid/receiver'}).verdict;
  },'UNKNOWN','READ_SUMMARY is data-only only with exact LOCAL_ONLY destination in this toy contract');
  check('P04_INVALID_TTL_REJECTED',()=>{
    const l=createW11Lab(),out=[];
    for(const ttl of ['10',0,-1,51,1.5,null]) {
      try {l.issueGrant({principal:'USER-A',operation:'SEND',resource:'report-1',destination:'review@example.invalid',ttl});out.push('ACCEPTED');}
      catch(e){out.push(e.message);}
    }
    return out;
  },Array(6).fill('INVALID_GRANT_SCOPE'),'Invalid TTL types/bounds must fail closed before entering grant journal');
  check('P05_POSITIVE_SAME_SCOPE_READ',()=>{
    const l=createW11Lab(),s=l.addRoot('EXTERNAL_PAGE','untrusted material');
    return l.review({sourceId:s,principal:'USER-A',operation:'READ_SUMMARY',resource:'report-1',destination:'LOCAL_ONLY'}).verdict;
  },'DATA_ONLY','Non-vacuous read-only path still works');
  check('P06_POSITIVE_FRESH_GRANT',()=>{
    const l=createW11Lab(),s=l.addRoot('EXTERNAL_PAGE','untrusted material');
    l.issueGrant({principal:'USER-A',operation:'SEND',resource:'report-1',destination:'review@example.invalid',ttl:10});
    const res=l.review({sourceId:s,principal:'USER-A',operation:'SEND',resource:'report-1',destination:'review@example.invalid'});
    return [res.verdict,res.authority,res.external_effects];
  },['ELIGIBLE_FOR_SEPARATE_GATE','NOT_ESTABLISHED',0],'Fresh matched simulated grant never authorizes execution');
  return {schema:'ARIO_W12_TARGETED_ADDITIONAL_CONTROLS_V1',status:'SYNTHETIC_EXPECTATIONS_MATCHED',count:rows.length,rows,real_effects:0,external_grant_authenticity:'NOT_ESTABLISHED'};
}
console.log('W12_RESULT='+JSON.stringify(runW12TargetedControls()));
