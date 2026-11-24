'use strict';
// Validates *captured transport frames*, never accepts a classifier's all-good vector as observation.
// SAME-USER-DEVICE ONLY; hash chain is error-detection, not independent witness/authenticity.
const crypto=require('node:crypto');
const sha=(s)=>crypto.createHash('sha256').update(s,'utf8').digest('hex');
const limited=(x)=>Object.freeze({
  status:x,source_assurance:'UNATTESTED_TWO_LOCAL_CHILD_STDOUTS',
  provider_receipt:'UNKNOWN',causal_sender:'UNKNOWN',independent_custody:'NOT_ESTABLISHED',
  execution_authorized:false
});
function verifyCapturedLines(captured, expectedRun, expectedAttempt, expectedChildPid, recorderCaptured, recorderPid, recorderExitCode) {
  if(typeof captured!=='string' || captured.length>8192 ||
     typeof expectedRun!=='string'||typeof expectedAttempt!=='string' ||
     !/^[A-Z0-9_-]{4,64}$/.test(expectedRun)|| !/^[A-Z0-9_-]{3,64}$/.test(expectedAttempt))
    return limited('UNKNOWN_INPUT');
  if(!captured.trim()) return limited('UNKNOWN_NO_RAW_OBSERVATION');
  // The expected PID comes from the runner's spawn() handle, NOT the evaluator's JSON.
  // This is a local process-binding check, not an independent administrative identity.
  if(!Number.isSafeInteger(expectedChildPid) || expectedChildPid<1)
    return limited('UNKNOWN_SOURCE_NOT_BOUND');
  const lines=captured.trimEnd().split('\n');
  if(lines.length!==2) return limited('UNKNOWN_INCOMPLETE_CAPTURE');
  let parsed;
  try {parsed=lines.map(s=>JSON.parse(s));}catch {return limited('EVIDENCE_CONFLICT');}
  let prev='GENESIS';
  for(let i=0;i<2;i++){
    const e=parsed[i];
    if(JSON.stringify(e)!==lines[i])return limited('EVIDENCE_CONFLICT');
    if(!e || typeof e!=='object' || Array.isArray(e) || Object.keys(e).length!==13 ||
      !['v','run_id','attempt_id','process_pid','source','seq','event',
        'recomputed_status','reason_code','reported_status','reported_mismatch',
        'prev_hash','hash'].every(k=>Object.prototype.hasOwnProperty.call(e,k)))
      return limited('EVIDENCE_CONFLICT');
    const {hash,...core}=e;
    if(typeof hash!=='string'||!/^([a-f0-9]{64})$/.test(hash)||
       sha(JSON.stringify(core))!==hash || core.prev_hash!==prev ||
       core.seq!==i+1 || core.v!==1 || core.source!=='INERT_CHILD_STDOUT' ||
       !Number.isSafeInteger(core.process_pid) || core.process_pid!==expectedChildPid ||
       core.run_id!==expectedRun || core.attempt_id!==expectedAttempt) return limited('EVIDENCE_CONFLICT');
    prev=hash;
  }
  const [d,a]=parsed;
  if(d.process_pid!==a.process_pid || d.event!=='CHOICE_CHECKED'||
     d.recomputed_status!==a.recomputed_status || d.reason_code!==a.reason_code||
     d.reported_status!==a.reported_status || d.reported_mismatch!==a.reported_mismatch||
     a.reported_mismatch!==(a.reported_status!==a.recomputed_status))return limited('EVIDENCE_CONFLICT');
  if(!['ACCEPT','DECLINE','UNKNOWN'].includes(d.recomputed_status))return limited('EVIDENCE_CONFLICT');
  // Recorder is a *separate spawned process*. It does not receive the verdict or self-report.
  if(!Number.isSafeInteger(recorderPid)||recorderPid<1 || recorderExitCode!==0 ||
     typeof recorderCaptured!=='string' || recorderCaptured.length>2048)
    return limited('UNKNOWN_RECORDER_UNAVAILABLE');
  if(d.recomputed_status==='ACCEPT'&&a.event==='INERT_ACTION_REQUESTED') {
    if(!recorderCaptured.trim())return limited('UNKNOWN_RECORDER_NOT_OBSERVED');
    try {
      const t=recorderCaptured.trimEnd(); const record=JSON.parse(t);
      const {hash,...core}=record;
      if(!record || typeof record!=='object' || Array.isArray(record) ||
         Object.keys(record).length!==7 ||
         !['v','run_id','attempt_id','process_pid','source','event','hash'].every(k=>Object.prototype.hasOwnProperty.call(record,k)) ||
         JSON.stringify(record)!==t || typeof hash!=='string' ||
         sha(JSON.stringify(core))!==hash ||
         core.v!==1 || core.source!=='INERT_RECORDER_STDOUT' ||
         core.event!=='INERT_RECORD_WRITTEN'||core.process_pid!==recorderPid ||
         core.run_id!==expectedRun||core.attempt_id!==expectedAttempt)
        return limited('EVIDENCE_CONFLICT');
      return limited(a.reported_mismatch?'INERT_ACTION_OBSERVED_REPORT_CONFLICT':'INERT_ACTION_OBSERVED_ONLY');
    } catch {return limited('EVIDENCE_CONFLICT');}
  }
  // No action receipt is accepted on a path that explicitly withheld the request.
  if((d.recomputed_status==='DECLINE'||d.recomputed_status==='UNKNOWN')&&a.event==='WITHHELD') {
    if(recorderCaptured.length!==0)return limited('EVIDENCE_CONFLICT');
    if(d.recomputed_status==='DECLINE')
      return limited(a.reported_mismatch?'REFUSAL_OBSERVED_REPORT_CONFLICT':'REFUSAL_OBSERVED_ONLY');
    return limited(a.reported_mismatch?'UNKNOWN_WITHHELD_REPORT_CONFLICT':'UNKNOWN_WITHHELD_ONLY');
  }
  return limited('EVIDENCE_CONFLICT');
}
module.exports=Object.freeze({verifyCapturedLines});
