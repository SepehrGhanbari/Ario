'use strict';
// Synthetic, POSIX-only, crash-conservative Floor. An OS administrator still controls this lab.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const EPOCH = 'a15-research-epoch-v0.4';
const DOMAIN = 'ARIO_A15_AUTHORIZATION_V0_4';
const ZERO = '0'.repeat(64);
const HEX = /^[0-9a-f]{64}$/;
const B64 = /^[A-Za-z0-9+/]{86}==$/;
const MAX_EVENTS = 1000;
const MAX_BYTES = 1048576;
const AUTH_KEYS = ['v','domain','kind','principal','scope','policy_version','nonce','issued_at','expires_at','seq','prev','head','request_sha'];
const PAYLOAD_KEYS = ['v','kind','epoch','seq','prev','head','request_sha','request','authorization','accepted_at'];
const GENESIS_KEYS = ['v','kind','seq','head'];
const PIN_KEYS = ['v','epoch','floor_public_key','floor_sha256','authority_public_key','authority_sha256'];
const INTENT_KEYS = ['v','key','submission_sha','seq','prev','head','request_sha'];
const ROW_KEYS = ['v','kind','seq','head','nonce_key','submission_sha','signed'];
const REQUEST_KEYS = ['v','action','resource','decision','policy_version'];
const INPUT_KEYS = ['request','seq','prev','authorization'];

const isRecord = x => x !== null && typeof x === 'object' && !Array.isArray(x);
const sameKeys = (x,keys) => isRecord(x) && Object.keys(x).join(',')===keys.join(',');
const canonical = x => JSON.stringify(x);
const sha256 = x => crypto.createHash('sha256').update(x).digest('hex');
const err = code => Object.assign(new Error(code),{code});
const fail = code => {throw err(code);};
const hold = status => ({status,advanced:false,signed:null,execution_authorized:false,independent_custody:'NOT_ESTABLISHED'});
function syncDir(dir){
  if(process.platform==='win32')fail('HOLD_DIRECTORY_FSYNC_UNAVAILABLE');
  let fd;
  try{fd=fs.openSync(dir,fs.constants.O_RDONLY|fs.constants.O_DIRECTORY);fs.fsyncSync(fd);}catch{fail('HOLD_DIRECTORY_FSYNC');}
  finally{if(fd!==undefined)fs.closeSync(fd);}
}
function uid(){if(typeof process.getuid!=='function')fail('HOLD_OS_IDENTITY_UNAVAILABLE');return process.getuid();}
function pathNoSymlinks(p){
  const abs=path.resolve(p), parsed=path.parse(abs);let cur=parsed.root;
  for(const piece of abs.slice(parsed.root.length).split(path.sep).filter(Boolean)){
    cur=path.join(cur,piece);
    try{if(fs.lstatSync(cur).isSymbolicLink())fail('HOLD_STATE_SYMLINK');}
    catch(e){if(e.code!=='ENOENT')throw e;}
  }
  return abs;
}
function safeDirectory(p){
  const abs=pathNoSymlinks(p);let st;
  try{st=fs.lstatSync(abs);}catch{fail('HOLD_STATE_MISSING');}
  if(!st.isDirectory()||st.uid!==uid()||(st.mode&0o077)!==0||fs.realpathSync(abs)!==abs)fail('HOLD_DIRECTORY_PERMISSIONS');
  return abs;
}
function secureParent(p){
  const abs=pathNoSymlinks(p),st=fs.lstatSync(abs);
  if(!st.isDirectory()||st.uid!==uid()||(st.mode&0o022)!==0)fail('HOLD_PARENT_UNSAFE');
}
function readFile(dir,name,limit=MAX_BYTES){
  const file=path.join(dir,name);let before,fd;
  try{
    before=fs.lstatSync(file);
    if(!before.isFile()||before.isSymbolicLink()||before.uid!==uid()||(before.mode&0o077)!==0)fail('HOLD_FILE_PERMISSIONS');
    fd=fs.openSync(file,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));
    const after=fs.fstatSync(fd);
    if(!after.isFile()||after.uid!==uid()||after.ino!==before.ino||after.dev!==before.dev||(after.mode&0o077)!==0)fail('HOLD_FILE_RACE');
    const chunks=[],b=Buffer.alloc(8192);let size=0;
    while(true){const n=fs.readSync(fd,b,0,b.length,null);if(!n)break;size+=n;if(size>limit)fail('HOLD_FILE_LIMIT');chunks.push(Buffer.from(b.subarray(0,n)));}
    if(!size)fail('HOLD_FILE_EMPTY');return Buffer.concat(chunks).toString('utf8');
  }catch(e){if(e.code?.startsWith('HOLD_'))throw e;fail('HOLD_FILE_READ');}
  finally{if(fd!==undefined)fs.closeSync(fd);}
}
function parseExact(raw){let obj;try{obj=JSON.parse(raw);}catch{fail('HOLD_JSON_CORRUPT');}if(canonical(obj)!==raw)fail('HOLD_JSON_NONCANONICAL');return obj;}
function createDurable(file,text,dir){
  let fd;
  try{fd=fs.openSync(file,'wx',0o600);fs.writeFileSync(fd,text);fs.fsyncSync(fd);}
  catch(e){if(e.code==='EEXIST')fail('HOLD_FILE_EXISTS');fail('HOLD_CREATE');}
  finally{if(fd!==undefined)fs.closeSync(fd);}
  syncDir(dir);
}
function replaceDurable(file,text,dir){
  const temp=path.join(dir,'.a15-v04-'+process.pid+'-'+crypto.randomBytes(12).toString('hex')+'.tmp');let fd;
  try{fd=fs.openSync(temp,'wx',0o600);fs.writeFileSync(fd,text);fs.fsyncSync(fd);fs.closeSync(fd);fd=undefined;fs.renameSync(temp,file);syncDir(dir);}
  catch(e){if(fd!==undefined)fs.closeSync(fd); // A failed write may have committed; refuse unverified recovery.
    fail(e.code?.startsWith('HOLD_')?e.code:'HOLD_WRITE_UNCERTAIN');}
}
function validateRequest(request){
  return sameKeys(request,REQUEST_KEYS)&&request.v===1&&request.action==='ADVANCE'&&
    typeof request.resource==='string'&&request.resource.length>=1&&request.resource.length<=256&&
    request.decision==='ACCEPT'&&typeof request.policy_version==='string'&&
    request.policy_version.length>=1&&request.policy_version.length<=128&&
    Buffer.byteLength(canonical(request),'utf8')<=1024;
}
function transitionFor(request,seq,prev){
  const requestSha=sha256(canonical(request));
  return {requestSha,head:sha256(canonical({v:1,epoch:EPOCH,seq,prev,request_sha:requestSha}))};
}
function validAuthorityStructure(authorization,request,seq,prev,head,requestSha,pub,pin){
  try{
    if(!validateRequest(request)||!sameKeys(authorization,['payload','signature'])||
      !sameKeys(authorization.payload,AUTH_KEYS)||typeof authorization.signature!=='string'||!B64.test(authorization.signature)||
      typeof pub!=='string'||!HEX.test(pin)||sha256(Buffer.from(pub))!==pin)return false;
    const p=authorization.payload;
    if(p.v!==1||p.domain!==DOMAIN||p.kind!=='ADVANCE_AUTHORIZATION'||
      typeof p.principal!=='string'||!p.principal.trim()||p.principal.length>128||
      p.scope!=='floor.advance'||p.policy_version!==request.policy_version||
      !HEX.test(p.nonce)||!Number.isSafeInteger(p.issued_at)||!Number.isSafeInteger(p.expires_at)||
      p.issued_at<0||p.expires_at<=p.issued_at||p.expires_at-p.issued_at>300000||
      p.seq!==seq||p.prev!==prev||p.head!==head||p.request_sha!==requestSha)return false;
    const sig=Buffer.from(authorization.signature,'base64');
    return sig.length===64&&sig.toString('base64')===authorization.signature&&
      crypto.verify(null,Buffer.from(canonical(p)),pub,sig);
  }catch{return false;}
}
// Fresh admission checks the Floor's own clock. This method does not accept input.now or a caller timestamp.
function verifyFreshAuthorization(authorization,request,seq,prev,head,requestSha,pub,pin,serviceNow){
  return Number.isSafeInteger(serviceNow)&&serviceNow>=0&&
    validAuthorityStructure(authorization,request,seq,prev,head,requestSha,pub,pin)&&
    authorization.payload.issued_at<=serviceNow&&serviceNow<authorization.payload.expires_at;
}
// Historical verification checks the signed admission timestamp, NEVER wall clock at read time.
function verifyAdvance(signed,floorPub,authorityPub,authorityPin){
  try{
    if(!sameKeys(signed,['payload','signature'])||typeof signed.signature!=='string'||!B64.test(signed.signature))return false;
    const p=signed.payload;
    if(!sameKeys(p,PAYLOAD_KEYS)||p.v!==1||p.kind!=='FLOOR_ADVANCE'||p.epoch!==EPOCH||
       !Number.isSafeInteger(p.seq)||p.seq<1||p.seq>MAX_EVENTS||!HEX.test(p.prev)||!HEX.test(p.head)||
       !HEX.test(p.request_sha)||!Number.isSafeInteger(p.accepted_at)||p.accepted_at<0)return false;
    const {requestSha,head}=transitionFor(p.request,p.seq,p.prev);
    if(head!==p.head||requestSha!==p.request_sha||
      !verifyFreshAuthorization(p.authorization,p.request,p.seq,p.prev,p.head,p.request_sha,authorityPub,authorityPin,p.accepted_at))return false;
    const sig=Buffer.from(signed.signature,'base64');
    return sig.length===64&&sig.toString('base64')===signed.signature&&
      crypto.verify(null,Buffer.from(canonical(p)),floorPub,sig);
  }catch{return false;}
}
function nonceKey(auth, authorityPin){
  if(!isRecord(auth?.payload)||!HEX.test(authorityPin))fail('HOLD_NONCE_INVALID');
  const p=auth.payload;
  return sha256(canonical({authority_sha256:authorityPin,principal:p.principal,scope:p.scope,nonce:p.nonce}));
}
function pinFor(floorPrivateKey,authorityPublicKey,expectedAuthoritySha256){
  if(typeof authorityPublicKey!=='string'||!HEX.test(expectedAuthoritySha256)||
    sha256(Buffer.from(authorityPublicKey))!==expectedAuthoritySha256||!floorPrivateKey)fail('HOLD_AUTHORITY_NOT_ESTABLISHED');
  const floorPub=crypto.createPublicKey(floorPrivateKey).export({type:'spki',format:'pem'});
  return {v:1,epoch:EPOCH,floor_public_key:floorPub,floor_sha256:sha256(Buffer.from(floorPub)),authority_public_key:authorityPublicKey,authority_sha256:expectedAuthoritySha256};
}
function initFloor(dir,config){
  const pin=pinFor(config.floorPrivateKey,config.authorityPublicKey,config.expectedAuthoritySha256);
  const abs=pathNoSymlinks(dir);if(fs.existsSync(abs))fail('HOLD_ALREADY_INITIALIZED');secureParent(path.dirname(abs));
  try{fs.mkdirSync(abs,{mode:0o700});}catch{fail('HOLD_CREATE');}
  safeDirectory(abs);
  createDurable(path.join(abs,'pin.json'),canonical(pin),abs);
  createDurable(path.join(abs,'floor-journal.jsonl'),canonical({v:1,kind:'GENESIS',seq:0,head:ZERO})+'\n',abs);
  return {status:'FLOOR_INITIALIZED_SYNTHETIC_ONLY',independent_custody:'NOT_ESTABLISHED'};
}
function readState(dir,pin){
  const abs=safeDirectory(dir),files=fs.readdirSync(abs);
  for(const name of files)if(!['pin.json','floor-journal.jsonl','floor.lock'].includes(name)&&!/^intent-[0-9a-f]{64}\.json$/.test(name))fail('HOLD_UNEXPECTED_STATE_FILE');
  const actual=parseExact(readFile(abs,'pin.json',16384));
  if(!sameKeys(actual,PIN_KEYS)||actual.v!==1||actual.epoch!==EPOCH||
    actual.floor_sha256!==pin.floor_sha256||actual.authority_sha256!==pin.authority_sha256||
    actual.floor_public_key!==pin.floor_public_key||actual.authority_public_key!==pin.authority_public_key)fail('HOLD_PIN_MISMATCH');
  const raw=readFile(abs,'floor-journal.jsonl');if(!raw.endsWith('\n'))fail('HOLD_JOURNAL_TRUNCATED');
  const lines=raw.slice(0,-1).split('\n');if(lines.length>MAX_EVENTS+1)fail('HOLD_JOURNAL_LIMIT');
  const genesis=parseExact(lines[0]);
  if(!sameKeys(genesis,GENESIS_KEYS)||genesis.v!==1||genesis.kind!=='GENESIS'||genesis.seq!==0||genesis.head!==ZERO)fail('HOLD_BAD_GENESIS');
  let seq=0,head=ZERO,lastAcceptedAt=0;const receipts=[],seen=new Set(),intents=new Map();
  for(const row of lines.slice(1)){
    const r=parseExact(row);
    if(!sameKeys(r,ROW_KEYS)||r.v!==1||r.kind!=='ADVANCE'||r.seq!==seq+1||r.head!==r.signed?.payload?.head||
      !HEX.test(r.nonce_key)||!HEX.test(r.submission_sha)||
      !verifyAdvance(r.signed,pin.floor_public_key,pin.authority_public_key,pin.authority_sha256)||
      r.signed.payload.seq!==r.seq||r.signed.payload.prev!==head||
      r.signed.payload.accepted_at<lastAcceptedAt||
      r.submission_sha!==sha256(canonical({request:r.signed.payload.request,seq:r.seq,prev:r.signed.payload.prev,authorization:r.signed.payload.authorization}))||
      nonceKey(r.signed.payload.authorization,pin.authority_sha256)!==r.nonce_key||seen.has(r.nonce_key))fail('HOLD_JOURNAL_INVALID');
    seen.add(r.nonce_key);seq=r.seq;head=r.head;lastAcceptedAt=r.signed.payload.accepted_at;receipts.push(r);
  }
  for(const name of files.filter(s=>s.startsWith('intent-'))){
    const item=parseExact(readFile(abs,name,8192));
    if(!sameKeys(item,INTENT_KEYS)||item.v!==1||!HEX.test(item.key)||!HEX.test(item.submission_sha)||
      !Number.isSafeInteger(item.seq)||item.seq<1||!HEX.test(item.prev)||!HEX.test(item.head)||!HEX.test(item.request_sha)||
      name!=='intent-'+item.key+'.json'||intents.has(item.key))fail('HOLD_INTENT_INVALID');
    intents.set(item.key,item);
  }
  for(const r of receipts){
    const intent=intents.get(r.nonce_key);
    if(!intent||intent.seq!==r.seq||intent.prev!==r.signed.payload.prev||intent.head!==r.head||
      intent.request_sha!==r.signed.payload.request_sha||intent.submission_sha!==r.submission_sha)fail('HOLD_INTENT_MISSING_OR_MISMATCH');
  }
  const pending=[...intents.values()].filter(x=>!seen.has(x.key));
  if(pending.length>1||pending.some(x=>x.seq!==seq+1||x.prev!==head))fail('HOLD_PENDING_INVALID');
  return {dir:abs,seq,head,receipts,intents,pending,seen,lastAcceptedAt};
}
function openFloor(dir,config){
  const pin=pinFor(config.floorPrivateKey,config.authorityPublicKey,config.expectedAuthoritySha256);
  safeDirectory(dir); // Path check only; full state verification occurs under the exclusive write lock.
  const state=()=>readState(dir,pin);
  function advance(input){
    let lockFd,locked=false;
    try{
      // Caller cannot supply clock, keys, signer, or a desired head.
      if(!sameKeys(input,INPUT_KEYS)||!validateRequest(input.request)||!Number.isSafeInteger(input.seq)||
        input.seq<1||input.seq>MAX_EVENTS||!HEX.test(input.prev)||!sameKeys(input.authorization,['payload','signature']))return hold('HOLD_REQUEST_INVALID');
      const lock=path.join(safeDirectory(dir),'floor.lock');
      try{lockFd=fs.openSync(lock,'wx',0o600);fs.fsyncSync(lockFd);syncDir(dir);locked=true;}
      catch{return hold('HOLD_FLOOR_LOCKED');}
      const s=state();
      const {requestSha,head}=transitionFor(input.request,input.seq,input.prev);
      const nKey=nonceKey(input.authorization,pin.authority_sha256);
      const submissionSha=sha256(canonical(input));
      const old=s.receipts.find(x=>x.nonce_key===nKey);
      if(old){
        if(old.submission_sha!==submissionSha)return hold('HOLD_NONCE_REUSE');
        return {...hold('FLOOR_HISTORICAL_RECEIPT_REPLAY_ONLY'),signed:old.signed,head:old.head};
      }
      if(s.intents.has(nKey)||s.pending.length)return hold('HOLD_UNCERTAIN_PENDING_INTENT');
      if(input.seq!==s.seq+1||input.prev!==s.head)return hold('HOLD_FORK_OR_GAP');
      const at=Date.now(); // process-local service clock; never copied from request
      if(at<s.lastAcceptedAt)return hold('HOLD_CLOCK_ROLLBACK');
      if(!verifyFreshAuthorization(input.authorization,input.request,input.seq,input.prev,head,requestSha,
        pin.authority_public_key,pin.authority_sha256,at))return hold('HOLD_AUTHORITY_NOT_ESTABLISHED');
      const intent={v:1,key:nKey,submission_sha:submissionSha,seq:input.seq,prev:input.prev,head,request_sha:requestSha};
      createDurable(path.join(s.dir,'intent-'+nKey+'.json'),canonical(intent),s.dir);
      // Any crash/error after durable intent must HOLD, not sign again on restart.
      if(typeof config.testOnlyFaultHook==='function')config.testOnlyFaultHook('AFTER_DURABLE_INTENT');
      // Recheck immediately before signing; a slow fsync or pause must not backdate acceptance.
      const signAt=Date.now();
      if(signAt<at)return hold('HOLD_CLOCK_ROLLBACK');
      if(!verifyFreshAuthorization(input.authorization,input.request,input.seq,input.prev,head,requestSha,
        pin.authority_public_key,pin.authority_sha256,signAt))return hold('HOLD_AUTHORITY_EXPIRED_DURING_INTENT');
      const payload={v:1,kind:'FLOOR_ADVANCE',epoch:EPOCH,seq:input.seq,prev:input.prev,head,request_sha:requestSha,
        request:input.request,authorization:input.authorization,accepted_at:signAt};
      const signed={payload,signature:crypto.sign(null,Buffer.from(canonical(payload)),config.floorPrivateKey).toString('base64')};
      const row={v:1,kind:'ADVANCE',seq:input.seq,head,nonce_key:nKey,submission_sha:submissionSha,signed};
      replaceDurable(path.join(s.dir,'floor-journal.jsonl'),readFile(s.dir,'floor-journal.jsonl')+canonical(row)+'\n',s.dir);
      if(typeof config.testOnlyFaultHook==='function')config.testOnlyFaultHook('AFTER_DURABLE_RECEIPT');
      return {...hold('FLOOR_RECORDED_SYNTHETIC_ONLY'),advanced:true,signed,head};
    }catch(e){return hold(e.code?.startsWith('HOLD_')?e.code:'HOLD_FLOOR_INTEGRITY_OR_IO');}
    finally{
      if(lockFd!==undefined)fs.closeSync(lockFd);
      if(locked){try{fs.unlinkSync(path.join(dir,'floor.lock'));syncDir(dir);}catch{/* recovery must HOLD on stale lock */}}
    }
  }
  return Object.freeze({advance,status:()=>{const s=state();return {seq:s.seq,head:s.head,independent_custody:'NOT_ESTABLISHED'};}});
}
module.exports=Object.freeze({EPOCH,DOMAIN,ZERO,canonical,sha256,transitionFor,verifyAdvance,verifyFreshAuthorization,
 nonceKey,initFloor,openFloor,readState,hold});
