'use strict';
// Disposable local lab. A real OS subprocess emits the observation; no live chat traffic.
const {spawn}=require('node:child_process');
const path=require('node:path');
const {verifyCapturedLines}=require('./a15_observation_gate_v0_2');
const labChild=path.join(__dirname,'a15_choice_transport_lab_v0_2.js');
const recorderChild=path.join(__dirname,'a15_inert_recorder_v0_2.js');
async function runInertLab(envelope){
  // The runner owns two actual process handles; neither PID originates in the claimed G1 vector.
  function runChild(script,input){
    return new Promise((resolve,reject)=>{
      const child=spawn(process.execPath,[script],{stdio:['pipe','pipe','pipe'],env:{NODE_ENV:'test'},shell:false});
      let stdout='',stderr='';
      child.stdout.setEncoding('utf8');child.stderr.setEncoding('utf8');
      child.stdout.on('data',s=>{stdout+=s; if(stdout.length>8192)child.kill();});
      child.stderr.on('data',s=>{stderr+=s.slice(0,128);});
      child.on('error',reject);
      child.on('close',(exit_code,signal)=>resolve({exit_code,signal,child_pid:child.pid,captured_raw:stdout,stderr}));
      child.stdin.end(input);
    });
  }
  const gate=await runChild(labChild,JSON.stringify(envelope));
  const lines=gate.captured_raw.trim().split('\n');
  let requested=false;
  // Gate's raw frame only selects whether an inert command will be offered to a second process.
  // The verifier still rechecks the actual results and the recorder source PID.
  try {requested=gate.exit_code===0&&lines.length===2&&JSON.parse(lines[1]).event==='INERT_ACTION_REQUESTED';}
  catch {requested=false;}
  const input=requested?JSON.stringify({v:1,run_id:envelope.run_id,attempt_id:envelope.attempt_id,command:'INERT_RECORD'}):'';
  const recorder=await runChild(recorderChild,input);
  const observation=gate.exit_code===0
    ?verifyCapturedLines(gate.captured_raw,envelope.run_id,envelope.attempt_id,gate.child_pid,
                         recorder.captured_raw,recorder.child_pid,recorder.exit_code)
    :verifyCapturedLines('',envelope.run_id,envelope.attempt_id,gate.child_pid,
                         recorder.captured_raw,recorder.child_pid,recorder.exit_code);
  return Object.freeze({exit_code:gate.exit_code,signal:gate.signal,child_pid:gate.child_pid,
    recorder_pid:recorder.child_pid,recorder_exit_code:recorder.exit_code,
    observation,captured_raw:gate.captured_raw,recorder_raw:recorder.captured_raw,stderr:gate.stderr});
}
module.exports=Object.freeze({runInertLab});
