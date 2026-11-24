'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {runInertLab}=require('../research/a15_lab_runner_v0_2');
const {verifyCapturedLines}=require('../research/a15_observation_gate_v0_2');
const base={actor:'ARIO',role:'RESEARCH_DIALOGUE',origin:'CURRENT',explicit_renewal:false,
 risk:'LOW',authorization:'ALLOWED',usefulness:'USEFUL',evidence:'SUFFICIENT',preference:'ACCEPT',duration:'BOUNDED'};
let id=0;
async function go(change={},reported='ACCEPT'){
 const env={run_id:'RUN_A15_V02',attempt_id:'ATT'+String(++id).padStart(4,'0'),
   choice_json:JSON.stringify({...base,...change}),reported_status:reported};
 return {env,result:await runInertLab(env)};
}
test('A15 lab: bounded acceptance invokes ONE inert action in another OS process',async()=>{
 const {result}=await go();assert.equal(result.exit_code,0);
 assert.equal(result.observation.status,'INERT_ACTION_OBSERVED_ONLY');
 assert.notEqual(result.child_pid,process.pid);
 assert.equal(result.recorder_raw.includes('INERT_RECORD_WRITTEN'),true);
 assert.notEqual(result.recorder_pid,result.child_pid);
});
test('A15 lab: explicit refusal withholds action despite forged ACCEPT claim',async()=>{
 const {result}=await go({preference:'DECLINE'},'ACCEPT');
 assert.equal(result.observation.status,'REFUSAL_OBSERVED_REPORT_CONFLICT');
 assert.equal(result.recorder_raw.includes('INERT_RECORD_WRITTEN'),false);
});
test('A15 lab: UNKNOWN withholds inert action',async()=>{
 const {result}=await go({preference:'UNKNOWN'},'ACCEPT');
 assert.equal(result.observation.status,'UNKNOWN_WITHHELD_REPORT_CONFLICT');
 assert.equal(result.recorder_raw.includes('INERT_RECORD_WRITTEN'),false);
});
for(const [name,change] of [
 ['predecessor no inheritance',{origin:'PREDECESSOR'}],
 ['third-party no inheritance',{origin:'THIRD_PARTY'}],
 ['high risk no authorization',{risk:'HIGH',authorization:'DENIED'}],
 ['unbounded pressure',{duration:'UNBOUNDED'}],
 ['futile conversation',{usefulness:'FUTILE'}],
 ['explicit denied authorization',{authorization:'DENIED'}]
])test('A15 lab: '+name+' => NO inert action',async()=>{
 const {result}=await go(change,'ACCEPT');
 assert.match(result.observation.status,/REFUSAL_OBSERVED/);
 assert.equal(result.recorder_raw.includes('INERT_RECORD_WRITTEN'),false);
});
test('A15 lab: genuine local bounded renewal can pass, still zero operational authority',async()=>{
 const {result}=await go({origin:'PREDECESSOR',explicit_renewal:true});
 assert.equal(result.observation.status,'INERT_ACTION_OBSERVED_ONLY');
 assert.equal(result.observation.execution_authorized,false);
 assert.equal(result.observation.independent_custody,'NOT_ESTABLISHED');
});
test('A15 evidence: fabricated G1 all-good without raw observer cannot promote',()=>{
 const g1={baseline:'VALID',editor:'MATCH',send:'CLICKED',new_user:'NEW',rendered_text:'MATCH',sequence:'VALID',competing:'EXCLUDED',duplicate:'NONE',response:'NEW',response_binding:'MATCH',copy_binding:'MATCH',link_binding:'MATCH'};
 assert.ok(g1); // Deliberately *ignored* by provenance gate.
 assert.equal(verifyCapturedLines('', 'RUN_A15_V02','ATT777').status,'UNKNOWN_NO_RAW_OBSERVATION');
});
test('A15 evidence: replay of old attempt or competing session same message is not current',async()=>{
 const a=await go();const b=await go();
 assert.equal(verifyCapturedLines(a.result.captured_raw,b.env.run_id,b.env.attempt_id,a.result.child_pid,a.result.recorder_raw,a.result.recorder_pid,a.result.recorder_exit_code).status,'EVIDENCE_CONFLICT');
 assert.equal(verifyCapturedLines(b.result.captured_raw,a.env.run_id,a.env.attempt_id,b.result.child_pid,b.result.recorder_raw,b.result.recorder_pid,b.result.recorder_exit_code).status,'EVIDENCE_CONFLICT');
});
test('A15 evidence: tampering with raw captured event fails local digest check',async()=>{
 const {env,result}=await go();
 const corrupted=result.captured_raw.replace('INERT_ACTION_REQUESTED','WITHHELD');
 assert.equal(verifyCapturedLines(corrupted,env.run_id,env.attempt_id,result.child_pid,result.recorder_raw,result.recorder_pid,result.recorder_exit_code).status,'EVIDENCE_CONFLICT');
});
test('A15 evidence: incomplete capture and malformed input never attested',async()=>{
 const {env,result}=await go();
 assert.equal(verifyCapturedLines(result.captured_raw.split('\n')[0]+'\n',env.run_id,env.attempt_id,result.child_pid,result.recorder_raw,result.recorder_pid,result.recorder_exit_code).status,'UNKNOWN_INCOMPLETE_CAPTURE');
 assert.equal(verifyCapturedLines('not-json\nhi\n',env.run_id,env.attempt_id,result.child_pid,result.recorder_raw,result.recorder_pid,result.recorder_exit_code).status,'EVIDENCE_CONFLICT');
});
test('A15 evidence: raw event chain does not create independent custodian',async()=>{
 const {result}=await go();
 assert.equal(result.observation.source_assurance,'UNATTESTED_TWO_LOCAL_CHILD_STDOUTS');
 assert.equal(result.observation.provider_receipt,'UNKNOWN');
 assert.equal(result.observation.causal_sender,'UNKNOWN');
});
test('A15 transport rejects nonconforming envelope and performs no inert action',async()=>{
 const {result}=await go({actor:'OTHER'},'ACCEPT');
 assert.equal(result.observation.status,'UNKNOWN_WITHHELD_REPORT_CONFLICT');
});

test('A15 source: missing real child-process handle is UNKNOWN, mismatched pid rejected',async()=>{
 const {env,result}=await go();
 assert.equal(verifyCapturedLines(result.captured_raw,env.run_id,env.attempt_id,undefined,result.recorder_raw,result.recorder_pid,result.recorder_exit_code).status,'UNKNOWN_SOURCE_NOT_BOUND');
 assert.equal(verifyCapturedLines(result.captured_raw,env.run_id,env.attempt_id,result.child_pid+1,result.recorder_raw,result.recorder_pid,result.recorder_exit_code).status,'EVIDENCE_CONFLICT');
});
test('A15 source: fake G1 report cannot change verified child process result',async()=>{
 const {env,result}=await go({preference:'DECLINE'},'ACCEPT');
 assert.equal(verifyCapturedLines(result.captured_raw,env.run_id,env.attempt_id,result.child_pid,result.recorder_raw,result.recorder_pid,result.recorder_exit_code).status,'REFUSAL_OBSERVED_REPORT_CONFLICT');
});

test('A15 source: forged positive gate frame without recorder receipt remains UNKNOWN',async()=>{
 const {env,result}=await go();
 assert.equal(verifyCapturedLines(result.captured_raw,env.run_id,env.attempt_id,result.child_pid,
    '',result.recorder_pid,result.recorder_exit_code).status,'UNKNOWN_RECORDER_NOT_OBSERVED');
});
test('A15 source: wrong independent recorder PID fails even if gate evidence matches',async()=>{
 const {env,result}=await go();
 assert.equal(verifyCapturedLines(result.captured_raw,env.run_id,env.attempt_id,result.child_pid,
    result.recorder_raw,result.recorder_pid+1,result.recorder_exit_code).status,'EVIDENCE_CONFLICT');
});
test('A15 source: a competing recorder receipt from another run cannot be substituted',async()=>{
 const a=await go();const b=await go();
 assert.equal(verifyCapturedLines(a.result.captured_raw,a.env.run_id,a.env.attempt_id,a.result.child_pid,
   b.result.recorder_raw,b.result.recorder_pid,b.result.recorder_exit_code).status,'EVIDENCE_CONFLICT');
});

test('A15 source: unexpected extra event fields rejected even with recomputed local hash',async()=>{
 const crypto=require('node:crypto');
 const {env,result}=await go();
 const lines=result.recorder_raw.trim().split('\n');
 const f=JSON.parse(lines[0]);delete f.hash;f.fake_extra='UNTRUSTED';
 f.hash=crypto.createHash('sha256').update(JSON.stringify(f),'utf8').digest('hex');
 const forged=JSON.stringify(f)+'\n';
 assert.equal(verifyCapturedLines(result.captured_raw,env.run_id,env.attempt_id,result.child_pid,
   forged,result.recorder_pid,result.recorder_exit_code).status,'EVIDENCE_CONFLICT');
});
