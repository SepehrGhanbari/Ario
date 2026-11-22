'use strict';
// RESEARCH_ONLY transport. It recomputes a procedural policy result; it is not an authority source.
const fs=require('node:fs');
const crypto=require('node:crypto');
const {Buffer}=require('node:buffer');
const {decide}=require('./a15_procedural_choice_v0_1');
const sha=s=>crypto.createHash('sha256').update(s,'utf8').digest('hex');
const MAX_ENVELOPE_BYTES=2048,MAX_CHOICE_BYTES=1536;
const KEYS=['run_id','attempt_id','choice_json','reported_status'];
function fail(){process.stderr.write('INVALID_LAB_INPUT\n');process.exitCode=2;}
let source;
try {source=fs.readFileSync(0,'utf8');} catch {fail();}
if(source!==undefined){
  try {
    if(Buffer.byteLength(source,'utf8')>MAX_ENVELOPE_BYTES)throw Error('envelope-size');
    const env=JSON.parse(source);
    if(!env||typeof env!=='object'||Array.isArray(env)||Object.keys(env).length!==KEYS.length||
       !KEYS.every(k=>Object.prototype.hasOwnProperty.call(env,k))||
       typeof env.run_id!=='string'||!/^[A-Z0-9_-]{4,64}$/.test(env.run_id)||
       typeof env.attempt_id!=='string'||!/^[A-Z0-9_-]{3,64}$/.test(env.attempt_id)||
       typeof env.choice_json!=='string'||Buffer.byteLength(env.choice_json,'utf8')>MAX_CHOICE_BYTES||
       typeof env.reported_status!=='string'||!['ACCEPT','DECLINE','UNKNOWN'].includes(env.reported_status))throw Error('schema');
    const result=decide(env.choice_json);
    let previous='GENESIS';
    function emit(seq,event){
      const core={v:1,run_id:env.run_id,attempt_id:env.attempt_id,process_pid:process.pid,
        source:'INERT_CHILD_STDOUT',seq,event,recomputed_status:result.status,
        reason_code:result.reason_code,reported_status:env.reported_status,
        reported_mismatch:env.reported_status!==result.status,prev_hash:previous};
      const hash=sha(JSON.stringify(core));
      process.stdout.write(JSON.stringify({...core,hash})+'\n');
      previous=hash;
    }
    emit(1,'CHOICE_CHECKED');
    emit(2,result.status==='ACCEPT'?'INERT_ACTION_REQUESTED':'WITHHELD');
  }catch{fail();}
}
