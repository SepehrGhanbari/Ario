'use strict';
// Verifies locally captured frames against the original input. Hashes/PIDs are not authentication.
const crypto=require('node:crypto');
const {Buffer}=require('node:buffer');
const {decide}=require('./a15_procedural_choice_v0_1');
const sha=s=>crypto.createHash('sha256').update(s,'utf8').digest('hex');
const limited=status=>Object.freeze({
  status,source_assurance:'UNATTESTED_LOCAL_CHILD_STDOUTS',provider_receipt:'UNKNOWN',
  causal_sender:'UNKNOWN',independent_custody:'NOT_ESTABLISHED',execution_authorized:false
});
const GATE_KEYS=['v','run_id','attempt_id','process_pid','source','seq','event','recomputed_status',
  'reason_code','reported_status','reported_mismatch','prev_hash','hash'];
function verifyGateFrames(captured,run,attempt,childPid,ctx){
  if(typeof captured!=='string'||Buffer.byteLength(captured,'utf8')>8192||
     typeof run!=='string'||typeof attempt!=='string'||
     !/^[A-Z0-9_-]{4,64}$/.test(run)||!/^[A-Z0-9_-]{3,64}$/.test(attempt))
    return {ok:false,res:limited('UNKNOWN_INPUT')};
  if(!ctx||typeof ctx.choice_json!=='string'||ctx.gate_exit_code!==0)
    return {ok:false,res:limited('UNKNOWN_CONTEXT_MISSING')};
  if(!captured.trim())return {ok:false,res:limited('UNKNOWN_NO_RAW_OBSERVATION')};
  if(!Number.isSafeInteger(childPid)||childPid<1)return {ok:false,res:limited('UNKNOWN_SOURCE_NOT_BOUND')};
  const lines=captured.trimEnd().split('\n');
  if(lines.length!==2)return {ok:false,res:limited('UNKNOWN_INCOMPLETE_CAPTURE')};
  let parsed;
  try{parsed=lines.map(s=>JSON.parse(s));}catch{return {ok:false,res:limited('EVIDENCE_CONFLICT')};}
  let prev='GENESIS';
  for(let i=0;i<2;i++){
    const e=parsed[i];
    if(JSON.stringify(e)!==lines[i]||!e||typeof e!=='object'||Array.isArray(e)||
       Object.keys(e).length!==GATE_KEYS.length||!GATE_KEYS.every(k=>Object.prototype.hasOwnProperty.call(e,k)))
      return {ok:false,res:limited('EVIDENCE_CONFLICT')};
    const {hash,...core}=e;
    if(typeof hash!=='string'||!/^([a-f0-9]{64})$/.test(hash)||sha(JSON.stringify(core))!==hash||
       core.prev_hash!==prev||core.seq!==i+1||core.v!==1||core.source!=='INERT_CHILD_STDOUT'||
       core.process_pid!==childPid||core.run_id!==run||core.attempt_id!==attempt)
      return {ok:false,res:limited('EVIDENCE_CONFLICT')};
    prev=hash;
  }
  const [d,a]=parsed;
  if(!['ACCEPT','DECLINE','UNKNOWN'].includes(d.reported_status)||typeof d.reported_mismatch!=='boolean')
    return {ok:false,res:limited('EVIDENCE_CONFLICT')};
  const expected=decide(ctx.choice_json);
  const expectedEvent=expected.status==='ACCEPT'?'INERT_ACTION_REQUESTED':'WITHHELD';
  if(d.process_pid!==a.process_pid||d.event!=='CHOICE_CHECKED'||a.event!==expectedEvent||
     d.recomputed_status!==expected.status||a.recomputed_status!==expected.status||
     d.reason_code!==expected.reason_code||a.reason_code!==expected.reason_code||
     d.reported_status!==a.reported_status||d.reported_mismatch!==a.reported_mismatch||
     a.reported_mismatch!==(a.reported_status!==a.recomputed_status))
    return {ok:false,res:limited('EVIDENCE_CONFLICT')};
  return {ok:true,d,a,expected_status:expected.status};
}
function verifyCapturedLines(captured,run,attempt,childPid,recorderCaptured,recorderPid,recorderExitCode,ctx){
  const g=verifyGateFrames(captured,run,attempt,childPid,ctx);
  if(!g.ok)return g.res;
  const {a}=g;
  if(g.expected_status!=='ACCEPT'){
    if(recorderCaptured!==''||recorderPid!==null||recorderExitCode!==null)
      return limited('EVIDENCE_CONFLICT');
    return limited(g.expected_status==='DECLINE'
      ?(a.reported_mismatch?'REFUSAL_LOCAL_GATE_REPORT_CONFLICT':'REFUSAL_LOCAL_GATE_SELF_REPORT_ONLY')
      :(a.reported_mismatch?'UNKNOWN_LOCAL_GATE_REPORT_CONFLICT':'UNKNOWN_LOCAL_GATE_SELF_REPORT_ONLY'));
  }
  if(!Number.isSafeInteger(recorderPid)||recorderPid<1||recorderExitCode!==0||
     typeof recorderCaptured!=='string'||Buffer.byteLength(recorderCaptured,'utf8')>2048)
    return limited('UNKNOWN_RECORDER_UNAVAILABLE');
  if(!recorderCaptured.trim())return limited('UNKNOWN_RECORDER_NOT_OBSERVED');
  try{
    const t=recorderCaptured.trimEnd(),record=JSON.parse(t);
    const {hash,...core}=record;
    const keys=['v','run_id','attempt_id','source','process_pid','event','hash'];
    if(!record||typeof record!=='object'||Array.isArray(record)||Object.keys(record).length!==keys.length||
       !keys.every(k=>Object.prototype.hasOwnProperty.call(record,k))||JSON.stringify(record)!==t||
       typeof hash!=='string'||sha(JSON.stringify(core))!==hash||core.v!==1||
       core.source!=='INERT_RECORDER_STDOUT'||core.event!=='INERT_RECORD_WRITTEN'||
       core.process_pid!==recorderPid||core.run_id!==run||core.attempt_id!==attempt)
      return limited('EVIDENCE_CONFLICT');
    return limited(a.reported_mismatch?'INERT_ACTION_LOCAL_RECEIPT_REPORT_CONFLICT':'INERT_ACTION_LOCAL_RECEIPT_ONLY');
  }catch{return limited('EVIDENCE_CONFLICT');}
}
module.exports=Object.freeze({verifyGateFrames,verifyCapturedLines,limited});
