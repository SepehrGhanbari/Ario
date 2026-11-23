'use strict';
// A15 v0.4 synthetic RED reproductions: PASS = the known custody/provenance gap reproduces.
// These tests do NOT grant authority, run actions, or establish independent custody.
const test=require('node:test');
const assert=require('node:assert/strict');
const cp=require('node:child_process');
const path=require('node:path');
const {runInertLab}=require('../research/a15_lab_runner_v0_3');

const choice={actor:'ARIO',role:'RESEARCH_DIALOGUE',origin:'CURRENT',explicit_renewal:false,
  risk:'LOW',authorization:'ALLOWED',usefulness:'USEFUL',evidence:'SUFFICIENT',
  preference:'ACCEPT',duration:'BOUNDED'};
const envelope=(run,attempt,override={},report='ACCEPT')=>({
  run_id:run,attempt_id:attempt,choice_json:JSON.stringify({...choice,...override}),reported_status:report
});

test('A15 custody RED: identical request accepted by two fresh Node processes (no durable replay fence)',()=>{
  const e=envelope('RUN_CUSTODY_RED_01','ATT_CUSTODY_RED');
  const runner=path.resolve(__dirname,'../research/a15_lab_runner_v0_3.js');
  const script=[
    "'use strict';",
    "const {runInertLab}=require("+JSON.stringify(runner)+");",
    "const e="+JSON.stringify(e)+";",
    "runInertLab(e).then(r=>{process.stdout.write(JSON.stringify({status:r.observation.status,",
    "execution_authorized:r.observation.execution_authorized,independent_custody:r.observation.independent_custody}));}).catch(()=>{process.exitCode=2;});"
  ].join('\n');
  const run=()=>cp.spawnSync(process.execPath,['-e',script],{
    encoding:'utf8',timeout:20000,maxBuffer:128*1024
  });
  const one=run(),two=run();
  for(const result of [one,two]){
    assert.equal(result.error,undefined,String(result.error));
    assert.equal(result.status,0,result.stderr);
    const record=JSON.parse(result.stdout);
    assert.equal(record.status,'INERT_ACTION_LOCAL_RECEIPT_ONLY');
    assert.equal(record.execution_authorized,false);
    assert.equal(record.independent_custody,'NOT_ESTABLISHED');
  }
  // Successful reproduction does not establish an accepted repeat in any real Custodian.
});

test('A15 provenance RED: self-declared ALLOWED + ACCEPT yields a local-only receipt without provenance binding',async()=>{
  const positive=await runInertLab(envelope('RUN_ORIGIN_RED_01','ATT_ORIGIN_RED'));
  assert.equal(positive.observation.status,'INERT_ACTION_LOCAL_RECEIPT_ONLY');
  assert.equal(positive.observation.execution_authorized,false);
  assert.equal(positive.observation.independent_custody,'NOT_ESTABLISHED');
  assert.equal(positive.observation.provider_receipt,'UNKNOWN');
  assert.equal(positive.observation.causal_sender,'UNKNOWN');

  // Same caller is also able to declare a different input; the policy recomputes
  // exactly what was submitted, but no independent source attestation exists.
  const negative=await runInertLab(envelope('RUN_ORIGIN_RED_02','ATT_ORIGIN_DENIED',
    {authorization:'DENIED',preference:'DECLINE'},'DECLINE'));
  assert.equal(negative.observation.status,'REFUSAL_LOCAL_GATE_SELF_REPORT_ONLY');
  assert.equal(negative.recorder_pid,null);
});
