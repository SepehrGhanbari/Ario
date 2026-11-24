'use strict';
// Inert local recorder only. Its unkeyed receipt is a local self-report, never independent custody.
const fs=require('node:fs');
const crypto=require('node:crypto');
const {Buffer}=require('node:buffer');
const sha=s=>crypto.createHash('sha256').update(s,'utf8').digest('hex');
const KEYS=['v','run_id','attempt_id','command'];
try{
  const raw=fs.readFileSync(0,'utf8');
  if(Buffer.byteLength(raw,'utf8')>1024)throw Error('size');
  if(raw.length===0)process.exitCode=0;
  else{
    const cmd=JSON.parse(raw);
    if(!cmd||typeof cmd!=='object'||Array.isArray(cmd)||Object.keys(cmd).length!==KEYS.length||
       !KEYS.every(k=>Object.prototype.hasOwnProperty.call(cmd,k))||cmd.v!==1||cmd.command!=='INERT_RECORD'||
       typeof cmd.run_id!=='string'||!/^[A-Z0-9_-]{4,64}$/.test(cmd.run_id)||
       typeof cmd.attempt_id!=='string'||!/^[A-Z0-9_-]{3,64}$/.test(cmd.attempt_id))throw Error('command');
    const core={v:1,run_id:cmd.run_id,attempt_id:cmd.attempt_id,source:'INERT_RECORDER_STDOUT',
      process_pid:process.pid,event:'INERT_RECORD_WRITTEN'};
    process.stdout.write(JSON.stringify({...core,hash:sha(JSON.stringify(core))}));
    process.stdout.write('\n');
  }
}catch{process.stderr.write('INVALID_RECORDER_COMMAND\n');process.exitCode=2;}
