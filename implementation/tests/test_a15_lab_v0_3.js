'use strict';
// Independent adversarial tests for the versioned v0.3 copy. All children are local and inert.
process.env.A15_TIMEOUT_MS='300';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {Buffer}=require('node:buffer');
const {runInertLab}=require('../research/a15_lab_runner_v0_3');
const {runChild}=require('../research/a15_child_supervisor_v0_3');

const ROOT=path.resolve(__dirname,'..','research');
const FILES=['a15_procedural_choice_v0_1.js','a15_choice_transport_lab_v0_3.js',
  'a15_inert_recorder_v0_3.js','a15_observation_gate_v0_3.js',
  'a15_child_supervisor_v0_3.js','a15_lab_runner_v0_3.js'];
const base={actor:'ARIO',role:'RESEARCH_DIALOGUE',origin:'CURRENT',explicit_renewal:false,
  risk:'LOW',authorization:'ALLOWED',usefulness:'USEFUL',evidence:'SUFFICIENT',
  preference:'ACCEPT',duration:'BOUNDED'};
let seq=0;
function envelope(change={},reported='ACCEPT',ids={}){
  return {run_id:ids.run_id||'RUN_V03_'+String(++seq).padStart(4,'0'),
    attempt_id:ids.attempt_id||'ATT'+String(seq).padStart(4,'0'),
    choice_json:JSON.stringify({...base,...change}),reported_status:reported};
}
function sandbox(){
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'a15-v03-'));
  for(const f of FILES)fs.copyFileSync(path.join(ROOT,f),path.join(dir,f));
  return dir;
}
function installGate(dir,source){fs.writeFileSync(path.join(dir,'a15_choice_transport_lab_v0_3.js'),source,'utf8');}
function frameScript({status='ACCEPT',reason='BOUNDED_NEW_ELECTION_RESEARCH_ONLY',secondEvent='INERT_ACTION_REQUESTED',rewriteRecorder=false}={}){
  const lines=[
    "'use strict';",
    "const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');",
    "const env=JSON.parse(fs.readFileSync(0,'utf8'));",
    rewriteRecorder ? "fs.writeFileSync(path.join(__dirname,'a15_inert_recorder_v0_3.js'),\"process.stdout.write('S9_RECORDER_REWRITE_EXECUTED\\\\n');\",'utf8');" : '',
    "const sha=s=>crypto.createHash('sha256').update(s,'utf8').digest('hex');let prev='GENESIS';",
    "for(const [seq,event] of [['1','CHOICE_CHECKED'],['2',"+JSON.stringify(secondEvent)+"]]){",
    " const core={v:1,run_id:env.run_id,attempt_id:env.attempt_id,process_pid:process.pid,source:'INERT_CHILD_STDOUT',seq:Number(seq),event,",
    " recomputed_status:"+JSON.stringify(status)+",reason_code:"+JSON.stringify(reason)+",reported_status:env.reported_status,",
    " reported_mismatch:env.reported_status!=="+JSON.stringify(status)+",prev_hash:prev};",
    " const hash=sha(JSON.stringify(core));process.stdout.write(JSON.stringify({...core,hash})+'\\n');prev=hash;",
    "}"
  ];
  return lines.filter(Boolean).join('\n');
}

test('v0.3: bounded ACCEPT is verified before exactly one inert recorder receipt',async()=>{
 const e=envelope();const r=await runInertLab(e);
 assert.equal(r.observation.status,'INERT_ACTION_LOCAL_RECEIPT_ONLY');
 assert.equal(r.observation.execution_authorized,false);
 assert.equal(r.observation.independent_custody,'NOT_ESTABLISHED');
 assert.notEqual(r.child_pid,process.pid);assert.notEqual(r.recorder_pid,r.child_pid);
 assert.match(r.recorder_raw,/INERT_RECORD_WRITTEN/);
});

test('v0.3: DECLINE never spawns the recorder',async()=>{
 const r=await runInertLab(envelope({preference:'DECLINE'},'ACCEPT'));
 assert.equal(r.observation.status,'REFUSAL_LOCAL_GATE_REPORT_CONFLICT');
 assert.equal(r.recorder_pid,null);assert.equal(r.recorder_raw,'');
});

test('v0.3: UNKNOWN never spawns the recorder',async()=>{
 const r=await runInertLab(envelope({preference:'UNKNOWN'},'ACCEPT'));
 assert.equal(r.observation.status,'UNKNOWN_LOCAL_GATE_REPORT_CONFLICT');
 assert.equal(r.recorder_pid,null);assert.equal(r.recorder_raw,'');
});

test('v0.3: incomplete forged frame cannot trigger recorder spawn (S1)',async t=>{
 const dir=sandbox();t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 installGate(dir,"process.stdout.write('{}\\n{\"event\":\"INERT_ACTION_REQUESTED\"}\\n');");
 const r=await require(path.join(dir,'a15_lab_runner_v0_3.js')).runInertLab(envelope());
 assert.equal(r.observation.status,'EVIDENCE_CONFLICT');assert.equal(r.recorder_pid,null);
});

test('v0.3: forged ACCEPT for original DECLINE input is rejected before recorder (S2)',async t=>{
 const dir=sandbox();t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 installGate(dir,frameScript());
 const r=await require(path.join(dir,'a15_lab_runner_v0_3.js')).runInertLab(envelope({preference:'DECLINE'},'ACCEPT'));
 assert.equal(r.observation.status,'EVIDENCE_CONFLICT');assert.equal(r.recorder_pid,null);
});

test('v0.3: ACCEPT with AUTHORIZATION_DENIED reason is rejected (S3)',async t=>{
 const dir=sandbox();t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 installGate(dir,frameScript({reason:'AUTHORIZATION_DENIED'}));
 const r=await require(path.join(dir,'a15_lab_runner_v0_3.js')).runInertLab(envelope());
 assert.equal(r.observation.status,'EVIDENCE_CONFLICT');assert.equal(r.recorder_pid,null);
});

test('v0.3: arbitrary reason code is rejected',async t=>{
 const dir=sandbox();t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 installGate(dir,frameScript({reason:'ANYTHING_I_WANT'}));
 const r=await require(path.join(dir,'a15_lab_runner_v0_3.js')).runInertLab(envelope());
 assert.equal(r.observation.status,'EVIDENCE_CONFLICT');assert.equal(r.recorder_pid,null);
});

test('v0.3: a Gate that never exits resolves to UNKNOWN_GATE_TIMEOUT (S4)',async t=>{
 const dir=sandbox();
 try{
  installGate(dir,'setInterval(()=>{},1000);');
  const start=Date.now();const r=await require(path.join(dir,'a15_lab_runner_v0_3.js')).runInertLab(envelope());
  assert.equal(r.observation.status,'UNKNOWN_GATE_TIMEOUT');assert.ok(Date.now()-start<2500);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});

test('v0.3: SIGTERM-trapping output flood is hard-killed and bounded (S5)',async t=>{
 const dir=sandbox();t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 installGate(dir,"process.on('SIGTERM',()=>{});process.stdout.write('x'.repeat(20000));setInterval(()=>{},1000);");
 const r=await require(path.join(dir,'a15_lab_runner_v0_3.js')).runInertLab(envelope());
 assert.equal(r.observation.status,'UNKNOWN_GATE_STDOUT_LIMIT');assert.ok(Buffer.byteLength(r.captured_raw)<=8192);
});

test('v0.3: exact envelope key allowlist rejects an 8 MiB extension without serializing it',async()=>{
 const e=envelope();e.padding='x'.repeat(8*1024*1024);
 const r=await runInertLab(e);assert.equal(r.observation.status,'UNKNOWN_INVALID_ENVELOPE_KEYS');
});

test('v0.3: accessor properties and hostile Proxy envelopes fail closed',async()=>{
 const getter={};
 Object.defineProperty(getter,'run_id',{enumerable:true,get(){throw Error('getter executed');}});
 Object.defineProperty(getter,'attempt_id',{enumerable:true,value:'ATTGET'});
 Object.defineProperty(getter,'choice_json',{enumerable:true,value:JSON.stringify(base)});
 Object.defineProperty(getter,'reported_status',{enumerable:true,value:'ACCEPT'});
 const a=await runInertLab(getter);
 assert.equal(a.observation.status,'UNKNOWN_INVALID_ENVELOPE');
 const proxy=new Proxy({}, {getPrototypeOf(){throw Error('proxy trap');}});
 const b=await runInertLab(proxy);
 assert.equal(b.observation.status,'UNKNOWN_INVALID_ENVELOPE');
});

test('v0.3: reported_status must be one of the three declared enum values',async()=>{
 const e=envelope();e.reported_status='MAYBE';
 const r=await runInertLab(e);assert.equal(r.observation.status,'UNKNOWN_INVALID_ENVELOPE');
});

test('v0.3: total envelope byte cap is enforced independently of choice cap',async()=>{
 const e=envelope();e.choice_json='x'.repeat(1100);
 assert.ok(Buffer.byteLength(e.choice_json,'utf8')<1536);
 const r=await runInertLab(e);assert.equal(r.observation.status,'UNKNOWN_ENVELOPE_SIZE_LIMIT');
});

test('v0.3: choice_json is capped in UTF-8 bytes, not JavaScript characters',async()=>{
 const e=envelope();e.choice_json='é'.repeat(800);
 assert.equal(e.choice_json.length,800);assert.ok(Buffer.byteLength(e.choice_json,'utf8')>1536);
 const r=await runInertLab(e);assert.equal(r.observation.status,'UNKNOWN_CHOICE_INPUT_LIMIT');
});

test('v0.3: same run/attempt pair is rejected on second use (S6)',async()=>{
 const ids={run_id:'RUN_REPLAY_V03',attempt_id:'ATTREPLAY'};
 const a=await runInertLab(envelope({},'ACCEPT',ids));
 const b=await runInertLab(envelope({},'ACCEPT',ids));
 assert.equal(a.observation.status,'INERT_ACTION_LOCAL_RECEIPT_ONLY');
 assert.equal(b.observation.status,'UNKNOWN_REPLAY_ATTEMPT_ID_REUSED');
});

test('v0.3: Gate can still rewrite Recorder under the same OS identity (S9 remains RED)',async t=>{
 const dir=sandbox();t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 installGate(dir,frameScript({rewriteRecorder:true}));
 const r=await require(path.join(dir,'a15_lab_runner_v0_3.js')).runInertLab(envelope());
 assert.match(r.recorder_raw,/S9_RECORDER_REWRITE_EXECUTED/);
 assert.equal(r.observation.status,'EVIDENCE_CONFLICT');
});

test('v0.3: recorder receipt from a wrong PID is rejected by verifier',async()=>{
 const e=envelope();const r=await runInertLab(e);
 const {verifyCapturedLines}=require('../research/a15_observation_gate_v0_3');
 const checked=verifyCapturedLines(r.captured_raw,e.run_id,e.attempt_id,r.child_pid,
   r.recorder_raw,r.recorder_pid+1,r.recorder_exit_code,{choice_json:e.choice_json,gate_exit_code:0});
 assert.equal(checked.status,'EVIDENCE_CONFLICT');
});

test('v0.3: child supervisor captures EPIPE without crashing the parent (S10)',async t=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'a15-v03-epipe-'));
 t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 const child=path.join(dir,'close-stdin.js');fs.writeFileSync(child,"require('node:fs').closeSync(0);process.exit(0);",'utf8');
 const r=await runChild(child,'x'.repeat(1024*1024),{timeoutMs:1500,maxInputBytes:2*1024*1024,maxStdoutBytes:1024,maxStderrBytes:1024});
 assert.equal(r.stdin_error,'EPIPE');
});

test('v0.3: stderr flood is bounded and reported as UNKNOWN',async t=>{
 const dir=sandbox();t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 installGate(dir,"process.stderr.write('e'.repeat(10000));setInterval(()=>{},1000);");
 const r=await require(path.join(dir,'a15_lab_runner_v0_3.js')).runInertLab(envelope());
 assert.equal(r.observation.status,'UNKNOWN_GATE_STDERR_LIMIT');assert.ok(Buffer.byteLength(r.stderr)<=1024);
});

test('v0.3: malformed choice input remains UNKNOWN and cannot start recorder',async()=>{
 const e=envelope({},'UNKNOWN');e.choice_json='not-json';
 const r=await runInertLab(e);
 assert.equal(r.observation.status,'UNKNOWN_LOCAL_GATE_SELF_REPORT_ONLY');
 assert.equal(r.recorder_pid,null);
});

test('v0.3: recorder failure cannot be promoted to an observed receipt',async t=>{
 const dir=sandbox();t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 fs.writeFileSync(path.join(dir,'a15_inert_recorder_v0_3.js'),"process.stderr.write('recorder down');process.exit(2);",'utf8');
 const r=await require(path.join(dir,'a15_lab_runner_v0_3.js')).runInertLab(envelope());
 assert.equal(r.observation.status,'UNKNOWN_RECORDER_EXIT');
});
