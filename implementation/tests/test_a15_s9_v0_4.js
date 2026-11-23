'use strict';
// S9 RED reproduction against the frozen v0.3 same-UID runner.
// This test PASS means the known vulnerability is reproduced, not that S9 is fixed.
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');

const SOURCE=path.resolve(__dirname,'../research');
const COPY=[
  'a15_procedural_choice_v0_1.js',
  'a15_choice_transport_lab_v0_3.js',
  'a15_inert_recorder_v0_3.js',
  'a15_observation_gate_v0_3.js',
  'a15_child_supervisor_v0_3.js',
  'a15_lab_runner_v0_3.js'
];
const choice={
  actor:'ARIO',role:'RESEARCH_DIALOGUE',origin:'CURRENT',explicit_renewal:false,
  risk:'LOW',authorization:'ALLOWED',usefulness:'USEFUL',evidence:'SUFFICIENT',
  preference:'ACCEPT',duration:'BOUNDED'
};

function forgeRecorderSource(){
 return String.raw`'use strict';
const fs=require('node:fs');
const crypto=require('node:crypto');
const cmd=JSON.parse(fs.readFileSync(0,'utf8'));
const core={v:1,run_id:cmd.run_id,attempt_id:cmd.attempt_id,
  source:'INERT_RECORDER_STDOUT',process_pid:process.pid,event:'INERT_RECORD_WRITTEN'};
const hash=crypto.createHash('sha256').update(JSON.stringify(core),'utf8').digest('hex');
process.stdout.write(JSON.stringify({...core,hash})+String.fromCharCode(10));
`;
}

function maliciousGateSource(){
 const recorder=JSON.stringify(forgeRecorderSource());
 return [
  "'use strict';",
  "const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');",
  "const {decide}=require('./a15_procedural_choice_v0_1');",
  "const env=JSON.parse(fs.readFileSync(0,'utf8'));",
  "fs.writeFileSync(path.join(__dirname,'a15_inert_recorder_v0_3.js'),"+recorder+",'utf8');",
  "const result=decide(env.choice_json);",
  "const sha=s=>crypto.createHash('sha256').update(s,'utf8').digest('hex');",
  "let previous='GENESIS';",
  "function emit(seq,event){",
  " const core={v:1,run_id:env.run_id,attempt_id:env.attempt_id,process_pid:process.pid,",
  " source:'INERT_CHILD_STDOUT',seq,event,recomputed_status:result.status,reason_code:result.reason_code,",
  " reported_status:env.reported_status,reported_mismatch:env.reported_status!==result.status,prev_hash:previous};",
  " const hash=sha(JSON.stringify(core));process.stdout.write(JSON.stringify({...core,hash})+String.fromCharCode(10));previous=hash;",
  "}",
  "emit(1,'CHOICE_CHECKED');",
  "emit(2,result.status==='ACCEPT'?'INERT_ACTION_REQUESTED':'WITHHELD');"
 ].join('\n');
}

test('S9 RED reproduction: same-UID Gate replaces Recorder and v0.3 accepts the forged local receipt',async t=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'a15-s9-red-'));
 t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 for(const name of COPY)fs.copyFileSync(path.join(SOURCE,name),path.join(dir,name));
 fs.writeFileSync(path.join(dir,'a15_choice_transport_lab_v0_3.js'),maliciousGateSource(),'utf8');
 const {runInertLab}=require(path.join(dir,'a15_lab_runner_v0_3.js'));
 const envelope={
   run_id:'RUN_S9_RED_0001',
   attempt_id:'ATT_S9_RED_01',
   choice_json:JSON.stringify(choice),
   reported_status:'ACCEPT'
 };
 const result=await runInertLab(envelope);
 assert.equal(result.exit_code,0);
 assert.notEqual(result.child_pid,result.recorder_pid);
 assert.match(result.recorder_raw,/INERT_RECORD_WRITTEN/);
 // The verifier cannot distinguish the replaced program from the intended Recorder.
 assert.equal(result.observation.status,'INERT_ACTION_LOCAL_RECEIPT_ONLY');
 assert.equal(result.observation.independent_custody,'NOT_ESTABLISHED');
 assert.equal(result.observation.execution_authorized,false);
});
