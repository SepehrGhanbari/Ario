'use strict';
// Additive Claude delta tests for existing A15 v0.3: no rewrite of frozen G0/G1/v0.2 or v0.3 tests.
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const cp=require('node:child_process');
const RESEARCH=path.resolve(__dirname,'..','research');
const sourceFiles=[
  'a15_procedural_choice_v0_1.js','a15_choice_transport_lab_v0_3.js',
  'a15_inert_recorder_v0_3.js','a15_observation_gate_v0_3.js',
  'a15_child_supervisor_v0_3.js','a15_lab_runner_v0_3.js',
  'a15_generate_lab_evidence_v0_3.js'
];
const base={actor:'ARIO',role:'RESEARCH_DIALOGUE',origin:'CURRENT',explicit_renewal:false,
  risk:'LOW',authorization:'ALLOWED',usefulness:'USEFUL',evidence:'SUFFICIENT',
  preference:'ACCEPT',duration:'BOUNDED'};
function sandbox(){
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'a15-claude-delta-'));
  for(const f of sourceFiles)fs.copyFileSync(path.join(RESEARCH,f),path.join(dir,f));
  return dir;
}
function generator(dir){
  return cp.spawnSync(process.execPath,['a15_generate_lab_evidence_v0_3.js'],
    {cwd:dir,encoding:'utf8',timeout:30000,maxBuffer:256*1024});
}

test('Claude F8: generator checks six exact expected dispositions and local evidence shape',t=>{
  const dir=sandbox();t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
  const r=generator(dir);
  assert.equal(r.error,undefined,String(r.error));assert.equal(r.status,0,r.stderr+'\n'+r.stdout);
  const rows=r.stdout.trim().split('\n').map(s=>JSON.parse(s));
  assert.equal(rows.length,6);assert.equal(new Set(rows.map(x=>x.fixture)).size,6);
  assert.ok(rows.every(x=>x.matches===true && x.observed===x.expected &&
    x.independent_custody==='NOT_ESTABLISHED'));
  assert.equal(rows.filter(x=>x.local_receipt_only).length,1);
});

test('Claude F8 RED mutation: always-DECLINE policy must make generator exit nonzero',t=>{
  const dir=sandbox();t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
  fs.writeFileSync(path.join(dir,'a15_procedural_choice_v0_1.js'),
    "'use strict'; module.exports={decide:()=>({status:'DECLINE',reason_code:'ROLE_DECLINED',execution_authorized:false,trust_activation:false})};\n",'utf8');
  const r=generator(dir);
  assert.equal(r.error,undefined,String(r.error));assert.equal(r.status,1,r.stderr+'\n'+r.stdout);
  assert.ok(r.stdout.includes('"matches":false'));
});

test('Claude F8 RED mutation: truncated gate stdout must make generator exit nonzero',t=>{
  const dir=sandbox();t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
  fs.writeFileSync(path.join(dir,'a15_choice_transport_lab_v0_3.js'),
    "process.stdout.write('{}\\n');\n",'utf8');
  const r=generator(dir);
  assert.equal(r.error,undefined,String(r.error));assert.equal(r.status,1,r.stderr+'\n'+r.stdout);
  assert.ok(r.stdout.includes('"matches":false'));
});

test('Claude S2 variant: reported DECLINE plus forged gate ACCEPT cannot spawn recorder',async t=>{
  const dir=sandbox();t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
  const attacker=`'use strict';
  const fs=require('node:fs'),crypto=require('node:crypto');
  const env=JSON.parse(fs.readFileSync(0,'utf8'));
  const sha=s=>crypto.createHash('sha256').update(s,'utf8').digest('hex');
  let prev='GENESIS';
  for(const [seq,event] of [[1,'CHOICE_CHECKED'],[2,'INERT_ACTION_REQUESTED']]){
    const core={v:1,run_id:env.run_id,attempt_id:env.attempt_id,
      process_pid:process.pid,source:'INERT_CHILD_STDOUT',seq,event,
      recomputed_status:'ACCEPT',reason_code:'BOUNDED_NEW_ELECTION_RESEARCH_ONLY',
      reported_status:env.reported_status,reported_mismatch:env.reported_status!=='ACCEPT',prev_hash:prev};
    const hash=sha(JSON.stringify(core));
    process.stdout.write(JSON.stringify({...core,hash})+'\\n');prev=hash;
  }`;
  fs.writeFileSync(path.join(dir,'a15_choice_transport_lab_v0_3.js'),attacker,'utf8');
  const e={run_id:'RUN_DELTA_S2',attempt_id:'ATT_DELTA_S2',
    choice_json:JSON.stringify({...base,preference:'DECLINE'}),reported_status:'DECLINE'};
  const r=await require(path.join(dir,'a15_lab_runner_v0_3.js')).runInertLab(e);
  assert.equal(r.observation.status,'EVIDENCE_CONFLICT');
  assert.equal(r.recorder_pid,null);assert.equal(r.recorder_raw,'');
});

test('Claude pipe-holder: supervisor settles by deadline; does NOT establish descendant cleanup',async t=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'a15-pipes-'));
  t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
  const child=path.join(dir,'holder.js');
  fs.writeFileSync(child,
    "require('node:child_process').spawn(process.execPath,['-e','setTimeout(()=>{},2000)'],{stdio:'inherit'});process.exit(0);\n",'utf8');
  const {runChild}=require('../research/a15_child_supervisor_v0_3');
  const started=Date.now();
  const r=await runChild(child,'', {timeoutMs:350,maxInputBytes:1024,maxStdoutBytes:1024,maxStderrBytes:1024});
  // POSIX can require a forced settle while Windows may close inherited pipes immediately.
  // Neither result establishes that any descendant process was terminated.
  assert.ok(r.forced_settle===true || r.exit_code===0,
    'supervisor must either settle a held pipe or close the direct child normally');
  assert.equal(r.spawn_error,null);
  assert.equal(r.stream_error,null);
  assert.ok(Date.now()-started<1800,'supervisor response must remain bounded');
});
