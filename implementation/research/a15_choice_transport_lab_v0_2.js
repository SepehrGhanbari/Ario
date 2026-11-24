'use strict';
// RESEARCH_ONLY: Inert child transport. It never invokes network, OS commands, keys or Ario runtimes.
// Crucially, the gate recomputes the choice; it does not trust the requested/reported status.
const fs = require('node:fs');
const crypto = require('node:crypto');
const {decide} = require('./a15_procedural_choice_v0_1');
const sha = (s) => crypto.createHash('sha256').update(s,'utf8').digest('hex');
function fail() {process.stderr.write('INVALID_LAB_INPUT\n');process.exitCode=2;}
let source;
try {source=fs.readFileSync(0,'utf8');} catch {fail();}
if (source !== undefined) {
  try {
    if (source.length>4096) throw Error('length');
    const env=JSON.parse(source);
    if (!env || typeof env!=='object' || Array.isArray(env) || Object.keys(env).length!==4 ||
        typeof env.run_id!=='string' || !/^[A-Z0-9_-]{4,64}$/.test(env.run_id) ||
        typeof env.attempt_id!=='string' || !/^[A-Z0-9_-]{3,64}$/.test(env.attempt_id) ||
        typeof env.choice_json!=='string' || typeof env.reported_status!=='string' ||
        !['ACCEPT','DECLINE','UNKNOWN'].includes(env.reported_status)) throw Error('schema');
    const result=decide(env.choice_json); // authoritative for the INERT lab only
    let previous='GENESIS';
    function emit(seq,event) {
      const core={v:1,run_id:env.run_id,attempt_id:env.attempt_id,
        process_pid:process.pid,source:'INERT_CHILD_STDOUT',seq,event,
        recomputed_status:result.status,reason_code:result.reason_code,
        reported_status:env.reported_status,reported_mismatch:env.reported_status!==result.status,
        prev_hash:previous};
      const hash=sha(JSON.stringify(core));
      process.stdout.write(JSON.stringify({...core,hash})+'\n');
      previous=hash;
    }
    emit(1,'CHOICE_CHECKED');
    // Requesting an inert action is NOT proof that the separate recorder observed it.
    emit(2,result.status==='ACCEPT'?'INERT_ACTION_REQUESTED':'WITHHELD');
  } catch {fail();}
}
