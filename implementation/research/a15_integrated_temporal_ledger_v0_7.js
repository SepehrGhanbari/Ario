'use strict';
// RESEARCH_ONLY: v0.6 persistence profile extended with pre-sign reservation and inert evidence production.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const v04=require('./a15_external_floor_simulator_v0_4');
const v05=require('./a15_temporal_evidence_verifier_v0_5');
const {DOMAIN,hash,verifyEvidence}=v05;
const HEX=/^[0-9a-f]{64}$/;
const LIMIT=32768, MAX=1000;
const canon=JSON.stringify;
const fields=(o,k)=>o!==null&&typeof o==='object'&&!Array.isArray(o)&&Object.keys(o).join(',')===k;
function fail(code){throw Object.assign(new Error(code),{code});}
function result(status,extra={}){return {status,finalized:false,execution_authorized:false,admission_authorized:false,independent_custody:'NOT_ESTABLISHED',trusted_time:'NOT_ESTABLISHED',...extra};}
function uid(){if(process.platform==='win32'||typeof process.getuid!=='function')fail('HOLD_POSIX_REQUIRED');return process.getuid();}
function directory(p,privateMode=true){
  const abs=path.resolve(p);if(fs.realpathSync(abs)!==abs)fail('HOLD_STATE_SYMLINK');
  const s=fs.lstatSync(abs);if(!s.isDirectory()||s.uid!==uid()||(s.mode&(privateMode?0o077:0o022)))fail('HOLD_DIRECTORY_PERMISSIONS');return abs;
}
function syncDir(dir){const fd=fs.openSync(dir,fs.constants.O_RDONLY|fs.constants.O_DIRECTORY);try{fs.fsyncSync(fd);}finally{fs.closeSync(fd);}}
function read(dir,name,limit=LIMIT){
  const file=path.join(dir,name),before=fs.lstatSync(file);
  if(!before.isFile()||before.uid!==uid()||(before.mode&0o077)||before.nlink!==1)fail('HOLD_FILE_PERMISSIONS');
  const fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);
  try{const s=fs.fstatSync(fd);if(!s.isFile()||s.dev!==before.dev||s.ino!==before.ino||s.uid!==uid()||(s.mode&0o077)||s.nlink!==1||s.size>limit)fail('HOLD_FILE_INVALID');
    const buf=Buffer.alloc(limit+1);let n=0;while(n<buf.length){const got=fs.readSync(fd,buf,n,buf.length-n,null);if(!got)break;n+=got;}
    if(!n||n>limit)fail('HOLD_FILE_INVALID');const raw=buf.subarray(0,n).toString('utf8');parse(raw,limit);return raw;
  }finally{fs.closeSync(fd);}
}
function parse(raw,limit=LIMIT){if(typeof raw!=='string'||Buffer.byteLength(raw)>limit)fail('HOLD_RECORD_INVALID');const obj=JSON.parse(raw);if(canon(obj)!==raw)fail('HOLD_RECORD_NONCANONICAL');return obj;}
function create(dir,name,raw){const fd=fs.openSync(path.join(dir,name),'wx',0o600);try{fs.writeFileSync(fd,raw);fs.fsyncSync(fd);}finally{fs.closeSync(fd);}syncDir(dir);}
function pinsChecked(p){
  if(!fields(p,'floorPublicKey,floorSha256,authorityPublicKey,authoritySha256,witnessPublicKey,witnessSha256'))fail('HOLD_PIN_INVALID');
  const der=[];for(const role of ['floor','authority','witness']){const pem=p[role+'PublicKey'],pin=p[role+'Sha256'];if(typeof pem!=='string'||pem.length>4096||typeof pin!=='string'||!HEX.test(pin)||v04.sha256(Buffer.from(pem))!==pin)fail('HOLD_PIN_INVALID');const k=crypto.createPublicKey(pem);if(k.asymmetricKeyType!=='ed25519'||k.export({type:'spki',format:'pem'})!==pem)fail('HOLD_PIN_INVALID');der.push(pem);}
  if(new Set(der).size!==3)fail('HOLD_KEY_ROLE_ALIAS');return Object.freeze({...p});
}
function signed(obj,pub){if(!fields(obj,'payload,signature')||typeof obj.signature!=='string'||!(/^[A-Za-z0-9+/]{86}==$/.test(obj.signature)))return false;const b=Buffer.from(obj.signature,'base64');return b.length===64&&b.toString('base64')===obj.signature&&crypto.verify(null,Buffer.from(canon(obj.payload)),pub,b);}
function stagePart(e){return {v:e.v,domain:e.domain,pre:e.pre,binding:e.binding};}
function verifyStage(raw,pins){
  const s=parse(raw);if(!fields(s,'v,domain,pre,binding')||s.v!==1||s.domain!==DOMAIN||!signed(s.pre,pins.witnessPublicKey)||!signed(s.binding,pins.floorPublicKey))fail('HOLD_STAGE_SIGNATURE');
  const p=s.pre.payload,b=s.binding.payload;
  if(!fields(p,'v,domain,kind,epoch,authorization_sha,challenge,time_ms,uncertainty_ms')||p.v!==1||p.domain!==DOMAIN||p.kind!=='PRE'||p.epoch!==v04.EPOCH||typeof p.challenge!=='string'||!HEX.test(p.challenge)||p.challenge===v04.ZERO)fail('HOLD_PRE_SCHEMA');
  if(!fields(b,'v,domain,kind,epoch,pre_sha,event')||b.v!==1||b.domain!==DOMAIN||b.kind!=='FLOOR_BINDING'||b.epoch!==v04.EPOCH||b.pre_sha!==hash(s.pre)||!v04.verifyAdvance(b.event,pins.floorPublicKey,pins.authorityPublicKey,pins.authoritySha256))fail('HOLD_STAGE_BINDING');
  const e=b.event.payload,a=e.authorization.payload,lo=p.time_ms-p.uncertainty_ms,hi=p.time_ms+p.uncertainty_ms;
  if(p.authorization_sha!==hash(e.authorization)||!Number.isSafeInteger(p.time_ms)||!Number.isSafeInteger(p.uncertainty_ms)||p.uncertainty_ms<0||p.uncertainty_ms>1000||!Number.isSafeInteger(lo)||!Number.isSafeInteger(hi)||lo<a.issued_at||hi>e.accepted_at)fail('HOLD_STAGE_TIME');
  return {raw,seq:e.seq,prev:e.prev,head:e.head,accepted:e.accepted_at,nonce:v04.nonceKey(e.authorization,pins.authoritySha256),challenge:p.challenge,sha:hash(s)};
}
function file(kind,seq){return kind+'-'+String(seq).padStart(4,'0')+'.json';}
const PROFILE='A15_V07_SYNTHETIC_RESERVE_BEFORE_SIGN';
const genesis=pins=>canon({v:7,profile:PROFILE,epoch:v04.EPOCH,pins,seq:0,head:v04.ZERO});
function initialize(dir,config){try{const pins=pinsChecked(config),abs=path.resolve(dir);directory(path.dirname(abs),false);fs.mkdirSync(abs,{mode:0o700});directory(abs);create(abs,'genesis.json',genesis(pins));syncDir(path.dirname(abs));return result('LEDGER_INITIALIZED_SYNTHETIC_ONLY');}catch(e){return result(e.code?.startsWith('HOLD_')?e.code:'HOLD_INIT');}}
function inputChecked(raw,pins){
  const x=parse(raw);
  if(!fields(x,'request,seq,prev,authorization')||!Number.isSafeInteger(x.seq)||x.seq<1||x.seq>MAX||typeof x.prev!=='string'||!HEX.test(x.prev))fail('HOLD_REQUEST_INVALID');
  const t=v04.transitionFor(x.request,x.seq,x.prev);
  // issued_at is used only as a structural/signature validation point, NOT a fresh time observation.
  if(!v04.verifyFreshAuthorization(x.authorization,x.request,x.seq,x.prev,t.head,t.requestSha,pins.authorityPublicKey,pins.authoritySha256,x.authorization?.payload?.issued_at))fail('HOLD_AUTHORITY_NOT_ESTABLISHED');
  return {x,head:t.head,requestSha:t.requestSha,nonce:v04.nonceKey(x.authorization,pins.authoritySha256),inputSha:hash(x)};
}
function reservationChecked(raw,pins){
  const r=parse(raw);
  if(!fields(r,'v,profile,input,challenge,nonce_key')||r.v!==7||r.profile!==PROFILE||typeof r.challenge!=='string'||!HEX.test(r.challenge)||r.challenge===v04.ZERO)fail('HOLD_RESERVATION_INVALID');
  const i=inputChecked(canon(r.input),pins);if(r.nonce_key!==i.nonce)fail('HOLD_RESERVATION_INVALID');
  return {...i,raw,challenge:r.challenge};
}
function checkPre(pre,r,pins){
  if(!signed(pre,pins.witnessPublicKey))fail('HOLD_PRE_SIGNATURE');const p=pre.payload,a=r.x.authorization.payload;
  if(!fields(p,'v,domain,kind,epoch,authorization_sha,challenge,time_ms,uncertainty_ms')||p.v!==1||p.domain!==DOMAIN||p.kind!=='PRE'||p.epoch!==v04.EPOCH||p.authorization_sha!==hash(r.x.authorization)||p.challenge!==r.challenge)fail('HOLD_PRE_BINDING');
  const lo=p.time_ms-p.uncertainty_ms,hi=p.time_ms+p.uncertainty_ms;
  if(!Number.isSafeInteger(p.time_ms)||!Number.isSafeInteger(p.uncertainty_ms)||p.uncertainty_ms<0||p.uncertainty_ms>1000||!Number.isSafeInteger(lo)||!Number.isSafeInteger(hi)||lo<a.issued_at||hi>=a.expires_at)fail('HOLD_PRE_OUTSIDE_WINDOW');
  return hi;
}
function matchStage(s,r,pins){
  const st=parse(s.raw),e=st.binding.payload.event.payload;
  const expected=checkPre(st.pre,r,pins);
  if(s.seq!==r.x.seq||s.prev!==r.x.prev||s.head!==r.head||s.nonce!==r.nonce||s.challenge!==r.challenge||s.accepted!==expected||canon(e.request)!==canon(r.x.request)||canon(e.authorization)!==canon(r.x.authorization))fail('HOLD_RESERVATION_STAGE_MISMATCH');
}
function cloneResponse(x){return parse(canon(x));}
function signInert(payload,key){return {payload,signature:crypto.sign(null,Buffer.from(canon(payload)),key).toString('base64')};}
// No caller-supplied signer or clock per request. The configured witness functions are SYNTHETIC fixtures.
// No key generation/export, real signer API, external network, or execution/admission authorization.
function openLedger(dir,config){
  const pins=pinsChecked(config.pins),abs=directory(dir);
  if(config.profile!==PROFILE)fail('HOLD_SYNTHETIC_PROFILE_REQUIRED');
  const floorKey=config.floorPrivateKey;
  if(!floorKey||floorKey.type!=='private'||floorKey.asymmetricKeyType!=='ed25519'||crypto.createPublicKey(floorKey).export({type:'spki',format:'pem'})!==pins.floorPublicKey)fail('HOLD_FLOOR_PIN_INVALID');
  const requestPre=config.requestPre,requestPost=config.requestPost;
  function state(){
    directory(abs);const names=fs.readdirSync(abs);
    if(names.length>2+MAX*3||names.some(n=>!['genesis.json','ledger.lock'].includes(n)&&!(/^(reserve|stage|final)-[0-9]{4}\.json$/.test(n))))fail('HOLD_UNEXPECTED_STATE_FILE');
    if(read(abs,'genesis.json')!==genesis(pins))fail('HOLD_GENESIS_OR_PIN_MISMATCH');
    const reservations=names.filter(n=>n.startsWith('reserve-')).sort(),stages=names.filter(n=>n.startsWith('stage-')).sort(),finals=names.filter(n=>n.startsWith('final-')).sort();
    if(reservations.length>MAX||reservations.length<stages.length||stages.length<finals.length||reservations.length>finals.length+1)fail('HOLD_LEDGER_SHAPE');
    let seq=0,head=v04.ZERO,lastAccepted=0,pending=null;const receipts=[],nonces=new Set(),challenges=new Set();
    for(let i=0;i<reservations.length;i++){
      const n=i+1;if(reservations[i]!==file('reserve',n))fail('HOLD_LEDGER_GAP');
      const r=reservationChecked(read(abs,reservations[i]),pins);
      if(r.x.seq!==n||r.x.prev!==head||nonces.has(r.nonce)||challenges.has(r.challenge))fail('HOLD_RESERVATION_CHAIN');
      nonces.add(r.nonce);challenges.add(r.challenge);
      if(i===stages.length){pending={reservation:r,stage:null};break;}
      if(stages[i]!==file('stage',n))fail('HOLD_LEDGER_GAP');
      const s=verifyStage(read(abs,stages[i]),pins);matchStage(s,r,pins);if(s.accepted<lastAccepted)fail('HOLD_TIME_ORDER');
      if(i===finals.length){pending={reservation:r,stage:s};break;}
      if(finals[i]!==file('final',n))fail('HOLD_LEDGER_GAP');
      const raw=read(abs,finals[i]),e=parse(raw),v=verifyEvidence(raw,pins);
      if(!v.evidence_verified||canon(stagePart(e))!==s.raw||v.seq!==s.seq||v.head!==s.head||v.nonce_key!==s.nonce)fail('HOLD_FINAL_EVIDENCE_INVALID');
      receipts.push({reservation:r,stage:s,raw,evidence_sha:v.evidence_sha});seq=n;head=s.head;lastAccepted=s.accepted;
    }
    return {seq,head,lastAccepted,pending,receipts,nonces,challenges};
  }
  function locked(fn){let fd,owned=false,uncertain=false,answer;try{directory(abs);try{fd=fs.openSync(path.join(abs,'ledger.lock'),'wx',0o600);owned=true;}catch{return result('HOLD_LEDGER_LOCKED');}uncertain=true;fs.fsyncSync(fd);syncDir(abs);uncertain=false;
    const persist=(name,raw)=>{uncertain=true;create(abs,name,raw);uncertain=false;};answer=fn(state(),persist);}catch(e){answer=result(e.code?.startsWith('HOLD_')?e.code:'HOLD_LEDGER_INTEGRITY_OR_IO');}
    finally{if(fd!==undefined){try{fs.closeSync(fd);}catch{answer=result('HOLD_LOCK_CLEANUP');}}if(owned&&!uncertain){try{fs.unlinkSync(path.join(abs,'ledger.lock'));syncDir(abs);}catch{answer=result('HOLD_LOCK_CLEANUP');}}}return uncertain?result('HOLD_DURABLE_WRITE_UNCERTAIN'):answer;
  }
  function begin(raw){return locked((s,persist)=>{
    const i=inputChecked(raw,pins),old=s.receipts.find(r=>r.reservation.x.seq===i.x.seq);
    if(old)return result(old.reservation.inputSha===i.inputSha?'HISTORICAL_REQUEST_REPLAY_ONLY':'HOLD_FINAL_CONFLICT',{seq:s.seq,head:s.head});
    if(s.pending)return result(s.pending.reservation.inputSha===i.inputSha?(s.pending.stage?'STAGE_ALREADY_PENDING':'HOLD_UNCERTAIN_PRE_SIGN_RESERVATION'):'HOLD_PENDING_CONFLICT',{seq:s.seq,head:s.head});
    if(s.nonces.has(i.nonce))return result('HOLD_NONCE_REUSE');
    if(i.x.seq!==s.seq+1||i.x.prev!==s.head)return result('HOLD_FORK_GAP');
    if(typeof requestPre!=='function')return result('HOLD_PRE_WITNESS_UNAVAILABLE');
    const challenge=crypto.randomBytes(32).toString('hex');if(challenge===v04.ZERO||s.challenges.has(challenge))return result('HOLD_CHALLENGE_REUSE');
    const reserve=canon({v:7,profile:PROFILE,input:i.x,challenge,nonce_key:i.nonce});
    // Both file and directory fsync complete BEFORE any witness callback or Floor signing call.
    persist(file('reserve',i.x.seq),reserve);
    const r=reservationChecked(reserve,pins);let pre;
    try{pre=cloneResponse(requestPre(Object.freeze({authorization_sha:hash(i.x.authorization),challenge,epoch:v04.EPOCH})));}catch{return result('HOLD_PRE_WITNESS_UNAVAILABLE');}
    const accepted=checkPre(pre,r,pins);if(accepted<s.lastAccepted)return result('HOLD_TIME_ORDER');
    // accepted_at denotes a synthetic PRE interval bound, not a measured signing instant.
    // Never retry signing if a reservation exists without a durable stage.
    const event=signInert({v:1,kind:'FLOOR_ADVANCE',epoch:v04.EPOCH,seq:i.x.seq,prev:i.x.prev,head:i.head,request_sha:i.requestSha,request:i.x.request,authorization:i.x.authorization,accepted_at:accepted},floorKey);
    const binding=signInert({v:1,domain:DOMAIN,kind:'FLOOR_BINDING',epoch:v04.EPOCH,pre_sha:hash(pre),event},floorKey);
    const stage=canon({v:1,domain:DOMAIN,pre,binding});const checked=verifyStage(stage,pins);matchStage(checked,r,pins);
    persist(file('stage',i.x.seq),stage);
    return result('STAGED_AWAITING_POST',{seq:s.seq,head:s.head,pending_seq:i.x.seq,stage_sha:checked.sha});
  });}
  function complete(){if(arguments.length)return result('HOLD_REQUEST_INVALID');return locked((s,persist)=>{
    if(!s.pending)return result('NO_PENDING_STAGE',{seq:s.seq,head:s.head});
    if(!s.pending.stage)return result('HOLD_UNCERTAIN_PRE_SIGN_RESERVATION',{seq:s.seq,head:s.head});
    if(typeof requestPost!=='function')return result('HOLD_POST_WITNESS_UNAVAILABLE',{seq:s.seq,head:s.head});
    const st=parse(s.pending.stage.raw);let post;
    // Only the configured witness receives the inert binding; no public pending-event accessor.
    try{post=cloneResponse(requestPost(Object.freeze({epoch:v04.EPOCH,binding_sha:hash(st.binding),binding:st.binding})));}catch{return result('HOLD_POST_WITNESS_UNAVAILABLE',{seq:s.seq,head:s.head});}
    // Reparse the persisted-stage bytes: a callback cannot modify them through its argument.
    const raw=canon({...parse(s.pending.stage.raw),post}),v=verifyEvidence(raw,pins);
    if(!v.evidence_verified)return result(v.status,{seq:s.seq,head:s.head});
    if(v.seq!==s.pending.stage.seq||v.head!==s.pending.stage.head||v.nonce_key!==s.pending.stage.nonce)return result('HOLD_PENDING_BINDING_MISMATCH');
    // Sole final-file write in this module; only after verification of exact durable stage + POST.
    persist(file('final',v.seq),raw);return result('FINALIZED_SYNTHETIC_EVIDENCE_ONLY',{finalized:true,seq:v.seq,head:v.head,evidence_sha:v.evidence_sha});
  });}
  function readFinal(seq){return locked(s=>{if(!Number.isSafeInteger(seq)||seq<1||seq>s.seq)return result('HOLD_FINAL_NOT_AVAILABLE',{seq:s.seq,head:s.head});const r=s.receipts[seq-1];return result('HISTORICAL_FINAL_EVIDENCE_ONLY',{seq:r.stage.seq,head:r.stage.head,evidence_sha:r.evidence_sha,evidence:r.raw});});}
  function status(){return locked(s=>result(s.pending?(s.pending.stage?'PENDING_POST':'HOLD_UNCERTAIN_PRE_SIGN_RESERVATION'):'LEDGER_READ_ONLY',{seq:s.seq,head:s.head,pending_seq:s.pending?.reservation.x.seq??null,latest_evidence_sha:s.receipts.at(-1)?.evidence_sha??null}));}
  return Object.freeze({begin,complete,readFinal,status});
}
module.exports=Object.freeze({PROFILE,initialize,openLedger});
