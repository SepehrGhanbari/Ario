'use strict';
// A physically separate, inert OS process. No network, filesystem write, Ario state, signer or keys.
const fs=require('node:fs');
const crypto=require('node:crypto');
const sha=s=>crypto.createHash('sha256').update(s,'utf8').digest('hex');
try {
  const raw=fs.readFileSync(0,'utf8');
  if(raw.length===0)process.exitCode=0; // expected when action was withheld
  else {
    if(raw.length>1024)throw Error('size');
    const cmd=JSON.parse(raw);
    if(!cmd || typeof cmd!=='object'||Array.isArray(cmd)||Object.keys(cmd).length!==4 ||
       cmd.v!==1||cmd.command!=='INERT_RECORD'||
       typeof cmd.run_id!=='string'||!/^[A-Z0-9_-]{4,64}$/.test(cmd.run_id)||
       typeof cmd.attempt_id!=='string'||!/^[A-Z0-9_-]{3,64}$/.test(cmd.attempt_id))throw Error('command');
    const core={v:1,run_id:cmd.run_id,attempt_id:cmd.attempt_id,
      source:'INERT_RECORDER_STDOUT',process_pid:process.pid,event:'INERT_RECORD_WRITTEN'};
    process.stdout.write(JSON.stringify({...core,hash:sha(JSON.stringify(core))})+'\n');
  }
} catch {process.stderr.write('INVALID_RECORDER_COMMAND\n');process.exitCode=2;}
