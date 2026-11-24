'use strict';
// RESEARCH_ONLY process supervisor. Bounds input/output and settles once on every exit path.
const {spawn}=require('node:child_process');
const {Buffer}=require('node:buffer');

function hardKill(child) {
  if (!child || child.killed) return;
  try {
    // On Windows Node terminates the child process; on POSIX request an uncatchable kill.
    if (process.platform === 'win32') child.kill();
    else child.kill('SIGKILL');
  } catch {}
}

function runChild(script, input, options={}) {
  const timeoutMs=Number.isSafeInteger(options.timeoutMs)&&options.timeoutMs>0?options.timeoutMs:1500;
  const maxInputBytes=Number.isSafeInteger(options.maxInputBytes)&&options.maxInputBytes>0?options.maxInputBytes:4096;
  const maxStdoutBytes=Number.isSafeInteger(options.maxStdoutBytes)&&options.maxStdoutBytes>0?options.maxStdoutBytes:8192;
  const maxStderrBytes=Number.isSafeInteger(options.maxStderrBytes)&&options.maxStderrBytes>0?options.maxStderrBytes:2048;
  if (typeof script!=='string' || !script || typeof input!=='string') {
    return Promise.resolve({exit_code:null,signal:null,child_pid:null,stdout:'',stderr:'',timed_out:false,stdout_overflow:false,stderr_overflow:false,stdin_error:null,spawn_error:'INVALID_SUPERVISOR_INPUT'});
  }
  if (Buffer.byteLength(input,'utf8')>maxInputBytes) {
    return Promise.resolve({exit_code:null,signal:null,child_pid:null,stdout:'',stderr:'',timed_out:false,stdout_overflow:false,stderr_overflow:false,stdin_error:null,spawn_error:'INPUT_LIMIT'});
  }
  return new Promise(resolve=>{
    let settled=false,terminating=false,child=null,timer=null,killSettleTimer=null;
    let stdoutBytes=0,stderrBytes=0,stdoutParts=[],stderrParts=[];
    let timed_out=false,stdout_overflow=false,stderr_overflow=false,stdin_error=null,spawn_error=null,stream_error=null;
    const output=()=>({
      exit_code:null,signal:null,child_pid:child&&child.pid||null,
      stdout:Buffer.concat(stdoutParts).toString('utf8'),
      stderr:Buffer.concat(stderrParts).toString('utf8'),
      timed_out,stdout_overflow,stderr_overflow,stdin_error,spawn_error,stream_error
    });
    const done=(close={})=>{
      if(settled)return;
      settled=true;
      if(timer)clearTimeout(timer);
      if(killSettleTimer)clearTimeout(killSettleTimer);
      resolve({...output(),...close});
    };
    const terminate=(reason)=>{
      if(reason==='timeout')timed_out=true;
      if(reason==='stdout')stdout_overflow=true;
      if(reason==='stderr')stderr_overflow=true;
      if(terminating)return;
      terminating=true;
      hardKill(child);
      // A broken or detached child must not keep the caller's promise pending forever.
      killSettleTimer=setTimeout(()=>done({forced_settle:true}),250);
      if(killSettleTimer.unref)killSettleTimer.unref();
    };
    try {
      child=spawn(process.execPath,[script],{
        cwd:options.cwd,
        stdio:['pipe','pipe','pipe'],
        env:{NODE_ENV:'test'},
        shell:false,
        windowsHide:true
      });
    } catch (e) {
      spawn_error=e&&e.code||'SPAWN_FAILED';
      return done();
    }
    if(!child.stdout||!child.stderr||!child.stdin){
      spawn_error='MISSING_STREAMS';
      terminate('stream');
      return;
    }
    child.stdout.on('data',chunk=>{
      const b=Buffer.isBuffer(chunk)?chunk:Buffer.from(chunk);
      if(stdoutBytes+b.length>maxStdoutBytes){
        const remain=Math.max(0,maxStdoutBytes-stdoutBytes);
        if(remain)stdoutParts.push(b.subarray(0,remain));
        stdoutBytes=maxStdoutBytes;
        if(!stdout_overflow)terminate('stdout');
        return;
      }
      stdoutParts.push(b);stdoutBytes+=b.length;
    });
    child.stderr.on('data',chunk=>{
      const b=Buffer.isBuffer(chunk)?chunk:Buffer.from(chunk);
      if(stderrBytes+b.length>maxStderrBytes){
        const remain=Math.max(0,maxStderrBytes-stderrBytes);
        if(remain)stderrParts.push(b.subarray(0,remain));
        stderrBytes=maxStderrBytes;
        if(!stderr_overflow)terminate('stderr');
        return;
      }
      stderrParts.push(b);stderrBytes+=b.length;
    });
    child.stdin.on('error',err=>{stdin_error=err&&err.code||'STDIN_ERROR';});
    child.stdout.on('error',err=>{stream_error=err&&err.code||'STDOUT_ERROR';terminate('stream');});
    child.stderr.on('error',err=>{stream_error=err&&err.code||'STDERR_ERROR';terminate('stream');});
    child.on('error',err=>{
      spawn_error=err&&err.code||'CHILD_ERROR';
      // The close event is not guaranteed after a spawn error.
      done();
    });
    child.on('close',(exit_code,signal)=>done({exit_code,signal}));
    timer=setTimeout(()=>terminate('timeout'),timeoutMs);
    if(timer.unref)timer.unref();
    try { child.stdin.end(input); }
    catch (e) { stdin_error=e&&e.code||'STDIN_WRITE_ERROR'; }
  });
}

module.exports=Object.freeze({runChild});
