'use strict';
// Disposable local lab. No network, real action, signer, key, or operational authority.
const path=require('node:path');
const {Buffer}=require('node:buffer');
const {runChild}=require('./a15_child_supervisor_v0_3');
const {verifyGateFrames,verifyCapturedLines,limited}=require('./a15_observation_gate_v0_3');
const gateChild=path.join(__dirname,'a15_choice_transport_lab_v0_3.js');
const recorderChild=path.join(__dirname,'a15_inert_recorder_v0_3.js');
const TIMEOUT_MS=Math.max(100,Math.min(5000,Number(process.env.A15_TIMEOUT_MS)||1500));
const MAX_ENVELOPE_BYTES=1024,MAX_CHOICE_BYTES=1536;
const used=new Set(); // In-process only. This is NOT a durable replay ledger.
const ENVELOPE_KEYS=['run_id','attempt_id','choice_json','reported_status'];
function bad(status){return Object.freeze({exit_code:null,signal:null,child_pid:null,recorder_pid:null,
  recorder_exit_code:null,observation:limited(status),captured_raw:'',recorder_raw:'',stderr:''});}
function validateEnvelope(envelope){
  try {
    if(!envelope||typeof envelope!=='object'||Array.isArray(envelope)||
       (Object.getPrototypeOf(envelope)!==Object.prototype&&Object.getPrototypeOf(envelope)!==null))
      return {error:'UNKNOWN_INVALID_ENVELOPE'};
    const keys=Reflect.ownKeys(envelope);
    if(keys.length!==ENVELOPE_KEYS.length||!keys.every(k=>typeof k==='string'&&ENVELOPE_KEYS.includes(k)))
      return {error:'UNKNOWN_INVALID_ENVELOPE_KEYS'};
    const descriptors=Object.getOwnPropertyDescriptors(envelope),snapshot=Object.create(null);
    for(const key of ENVELOPE_KEYS){
      const d=descriptors[key];
      if(!d||!Object.prototype.hasOwnProperty.call(d,'value'))return {error:'UNKNOWN_INVALID_ENVELOPE'};
      snapshot[key]=d.value;
    }
    if(typeof snapshot.run_id!=='string'||!/^[A-Z0-9_-]{4,64}$/.test(snapshot.run_id)||
       typeof snapshot.attempt_id!=='string'||!/^[A-Z0-9_-]{3,64}$/.test(snapshot.attempt_id)||
       typeof snapshot.choice_json!=='string'||typeof snapshot.reported_status!=='string'||
       !['ACCEPT','DECLINE','UNKNOWN'].includes(snapshot.reported_status))
      return {error:'UNKNOWN_INVALID_ENVELOPE'};
    if(Buffer.byteLength(snapshot.choice_json,'utf8')>MAX_CHOICE_BYTES)
      return {error:'UNKNOWN_CHOICE_INPUT_LIMIT'};
    const serialized=JSON.stringify(snapshot);
    if(Buffer.byteLength(serialized,'utf8')>MAX_ENVELOPE_BYTES)
      return {error:'UNKNOWN_ENVELOPE_SIZE_LIMIT'};
    return {error:null,envelope:Object.freeze(snapshot),serialized};
  } catch {
    return {error:'UNKNOWN_INVALID_ENVELOPE'};
  }
}
function childFailure(result,prefix){
  if(result.timed_out)return 'UNKNOWN_'+prefix+'_TIMEOUT';
  if(result.stdout_overflow)return 'UNKNOWN_'+prefix+'_STDOUT_LIMIT';
  if(result.stderr_overflow)return 'UNKNOWN_'+prefix+'_STDERR_LIMIT';
  if(result.stdin_error)return 'UNKNOWN_'+prefix+'_STDIN_ERROR';
  if(result.stream_error)return 'UNKNOWN_'+prefix+'_STREAM_ERROR';
  if(result.spawn_error)return 'UNKNOWN_'+prefix+'_SPAWN_FAILED';
  if(result.exit_code!==0)return 'UNKNOWN_'+prefix+'_EXIT';
  return null;
}
async function runInertLab(envelope){
  const checked=validateEnvelope(envelope);
  if(checked.error)return bad(checked.error);
  envelope=checked.envelope;
  const replayKey=envelope.run_id+'|'+envelope.attempt_id;
  if(used.has(replayKey))return bad('UNKNOWN_REPLAY_ATTEMPT_ID_REUSED');
  used.add(replayKey);

  const gate=await runChild(gateChild,checked.serialized,{
    timeoutMs:TIMEOUT_MS,maxInputBytes:MAX_ENVELOPE_BYTES,maxStdoutBytes:8192,maxStderrBytes:1024
  });
  const gateFailure=childFailure(gate,'GATE');
  if(gateFailure)return Object.freeze({exit_code:gate.exit_code,signal:gate.signal,child_pid:gate.child_pid,
    recorder_pid:null,recorder_exit_code:null,observation:limited(gateFailure),
    captured_raw:gate.stdout,recorder_raw:'',stderr:gate.stderr});

  const ctx={choice_json:envelope.choice_json,gate_exit_code:gate.exit_code};
  const pre=verifyGateFrames(gate.stdout,envelope.run_id,envelope.attempt_id,gate.child_pid,ctx);
  if(!pre.ok)return Object.freeze({exit_code:gate.exit_code,signal:gate.signal,child_pid:gate.child_pid,
    recorder_pid:null,recorder_exit_code:null,observation:pre.res,
    captured_raw:gate.stdout,recorder_raw:'',stderr:gate.stderr});

  // The recorder is not even spawned unless the complete Gate transcript verifies as ACCEPT.
  if(pre.expected_status!=='ACCEPT'){
    const observation=verifyCapturedLines(gate.stdout,envelope.run_id,envelope.attempt_id,gate.child_pid,
      '',null,null,ctx);
    return Object.freeze({exit_code:gate.exit_code,signal:gate.signal,child_pid:gate.child_pid,
      recorder_pid:null,recorder_exit_code:null,observation,captured_raw:gate.stdout,recorder_raw:'',stderr:gate.stderr});
  }

  const command=JSON.stringify({v:1,run_id:envelope.run_id,attempt_id:envelope.attempt_id,command:'INERT_RECORD'});
  const recorder=await runChild(recorderChild,command,{
    timeoutMs:TIMEOUT_MS,maxInputBytes:1024,maxStdoutBytes:2048,maxStderrBytes:1024
  });
  const recorderFailure=childFailure(recorder,'RECORDER');
  if(recorderFailure)return Object.freeze({exit_code:gate.exit_code,signal:gate.signal,child_pid:gate.child_pid,
    recorder_pid:recorder.child_pid,recorder_exit_code:recorder.exit_code,
    observation:limited(recorderFailure),captured_raw:gate.stdout,recorder_raw:recorder.stdout,stderr:gate.stderr+'\n'+recorder.stderr});
  const observation=verifyCapturedLines(gate.stdout,envelope.run_id,envelope.attempt_id,gate.child_pid,
    recorder.stdout,recorder.child_pid,recorder.exit_code,ctx);
  return Object.freeze({exit_code:gate.exit_code,signal:gate.signal,child_pid:gate.child_pid,
    recorder_pid:recorder.child_pid,recorder_exit_code:recorder.exit_code,
    observation,captured_raw:gate.stdout,recorder_raw:recorder.stdout,stderr:gate.stderr+'\n'+recorder.stderr});
}
module.exports=Object.freeze({runInertLab});
