'use strict';
// A15 synthetic, single-admin floor and IPC. NOT independent administrative custody.
const fs = require('node:fs');
const path = require('node:path');
const net = require('node:net');
const crypto = require('node:crypto');
const {once} = require('node:events');
const EPOCH='a15-research-epoch-v1';
const ZERO='0'.repeat(64);
const HEX=/^[0-9a-f]{64}$/;
const LIMIT=4096;
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
function fail(code){throw Object.assign(new Error(code),{code});}
function canonical(value){return JSON.stringify(value);}
function readJSON(file,max=LIMIT){
  const b=fs.readFileSync(file);
  if(b.length>max||!b.length)fail('HOLD_INVALID_BYTES');
  const raw=b.toString('utf8');
  const o=JSON.parse(raw);
  if(canonical(o)!==raw)fail('HOLD_NONCANONICAL_JSON');
  return o;
}
function durableCreate(file,text){
  let fd;
  try{
    fd=fs.openSync(file,'wx',0o600);fs.writeFileSync(fd,text,'utf8');fs.fsyncSync(fd);
  }finally{if(fd!==undefined)fs.closeSync(fd);}
  if(process.platform!=='win32'){
    try{const dir=fs.openSync(path.dirname(file),'r');try{fs.fsyncSync(dir);}finally{fs.closeSync(dir);}}catch{fail('HOLD_DIRECTORY_FSYNC');}
  }
}
function sign(privateKey,payload){return {payload,signature:crypto.sign(null,Buffer.from(canonical(payload)),privateKey).toString('base64')};}
function verify(signed,pub,kind){
  try{
    if(!signed||typeof signed!=='object'||Array.isArray(signed)||Object.keys(signed).join(',')!=='payload,signature')return false;
    const p=signed.payload;
    if(!p||typeof p!=='object'||Array.isArray(p)||p.v!==1||p.kind!==kind||p.epoch!==EPOCH||typeof signed.signature!=='string'||!/^([A-Za-z0-9+/]{86}==)$/.test(signed.signature))return false;
    const sig=Buffer.from(signed.signature,'base64');
    return sig.length===64&&crypto.verify(null,Buffer.from(canonical(p)),pub,sig);
  }catch{return false;}
}
function initialize(dir){
  if(fs.existsSync(dir)&&fs.readdirSync(dir).length)fail('HOLD_ALREADY_INITIALIZED');
  fs.mkdirSync(dir,{recursive:true,mode:0o700});
  const keys=crypto.generateKeyPairSync('ed25519',{publicKeyEncoding:{type:'spki',format:'pem'},privateKeyEncoding:{type:'pkcs8',format:'pem'}});
  const token=crypto.randomBytes(32).toString('hex');
  durableCreate(path.join(dir,'floor-public.pem'),keys.publicKey);
  durableCreate(path.join(dir,'floor-private.pem'),keys.privateKey);
  durableCreate(path.join(dir,'floor-token.txt'),token);
  durableCreate(path.join(dir,'floor-genesis.json'),canonical({v:1,epoch:EPOCH,pub_sha:hash(keys.publicKey),seq:0,head:ZERO}));
  return {status:'SYNTHETIC_FLOOR_INITIALIZED',epoch:EPOCH,seq:0,head:ZERO,public_sha256:hash(keys.publicKey),independent_custody:'NOT_ESTABLISHED',execution_authorized:false};
}
function keys(dir){
  const genesis=readJSON(path.join(dir,'floor-genesis.json'));
  const pub=fs.readFileSync(path.join(dir,'floor-public.pem'),'utf8');
  const priv=fs.readFileSync(path.join(dir,'floor-private.pem'),'utf8');
  if(genesis.v!==1||genesis.epoch!==EPOCH||genesis.pub_sha!==hash(pub)||genesis.seq!==0||genesis.head!==ZERO)fail('HOLD_GENESIS_INVALID');
  const token=fs.readFileSync(path.join(dir,'floor-token.txt'),'utf8');
  if(!/^[0-9a-f]{64}$/.test(token))fail('HOLD_TOKEN_INVALID');
  const probe={v:1,kind:'FLOOR_STATUS',epoch:EPOCH,seq:0,head:ZERO};
  if(!verify(sign(priv,probe),pub,'FLOOR_STATUS'))fail('HOLD_KEY_MISMATCH');
  return {pub,priv,token};
}
function eventFile(dir,seq){return path.join(dir,'event-'+String(seq).padStart(8,'0')+'.json');}
function readState(dir,pub){
  const files=fs.readdirSync(dir).filter(x=>x.startsWith('event-'));
  if(files.length>1000)fail('HOLD_EVENT_LIMIT');
  files.sort();
  let head=ZERO;
  const events=[];
  for(let i=0;i<files.length;i++){
    if(files[i]!==path.basename(eventFile(dir,i+1)))fail('HOLD_EVENT_GAP_OR_ALIAS');
    const loc=path.join(dir,files[i]);
    if(!fs.lstatSync(loc).isFile())fail('HOLD_EVENT_NOT_REGULAR');
    const signed=readJSON(loc);
    if(!verify(signed,pub,'FLOOR_ADVANCE'))fail('HOLD_EVENT_SIGNATURE');
    const p=signed.payload;
    if(Object.keys(p).join(',')!=='v,kind,epoch,seq,prev,head,request_sha'||
       p.seq!==i+1||p.prev!==head||typeof p.head!=='string'||!HEX.test(p.head)||
       typeof p.request_sha!=='string'||!HEX.test(p.request_sha))fail('HOLD_EVENT_CHAIN');
    events.push(signed);head=p.head;
  }
  return {seq:events.length,head,events};
}
function authenticate(request,token){
  if(!request||typeof request!=='object'||Array.isArray(request)||
     Object.keys(request).join(',')!=='body,mac'||typeof request.mac!=='string'||!HEX.test(request.mac))return false;
  const a=Buffer.from(request.mac,'hex');
  const b=crypto.createHmac('sha256',Buffer.from(token,'hex')).update(canonical(request.body)).digest();
  return a.length===b.length&&crypto.timingSafeEqual(a,b);
}
function authenticated(body,token){return {body,mac:crypto.createHmac('sha256',Buffer.from(token,'hex')).update(canonical(body)).digest('hex')};}
function handle(dir,request){
  const {pub,priv,token}=keys(dir);
  if(!authenticate(request,token))return {status:'HOLD_IPC_AUTH'};
  const body=request.body;
  if(!body||body.v!==1||body.epoch!==EPOCH||!['STATUS','ADVANCE'].includes(body.cmd))return {status:'HOLD_REQUEST_SCHEMA'};
  const s=readState(dir,pub);
  if(body.cmd==='STATUS'){
    if(Object.keys(body).join(',')!=='v,cmd,epoch')return {status:'HOLD_REQUEST_SCHEMA'};
    return {status:'FLOOR_STATUS_SIGNED',signed:sign(priv,{v:1,kind:'FLOOR_STATUS',epoch:EPOCH,seq:s.seq,head:s.head})};
  }
  if(Object.keys(body).join(',')!=='v,cmd,epoch,seq,prev,head,request_sha'||
     !Number.isSafeInteger(body.seq)||body.seq<1||body.seq>1000||
     !HEX.test(body.prev)||!HEX.test(body.head)||!HEX.test(body.request_sha))return {status:'HOLD_REQUEST_SCHEMA'};
  if(body.seq===s.seq){
    const old=s.events[s.seq-1];
    return old&&canonical(old.payload)===canonical({v:1,kind:'FLOOR_ADVANCE',epoch:EPOCH,seq:body.seq,prev:body.prev,head:body.head,request_sha:body.request_sha})?
      {status:'FLOOR_ALREADY_RECORDED',signed:old}:{status:'HOLD_FORK_OR_REPLAY'};
  }
  if(body.seq!==s.seq+1||body.prev!==s.head)return {status:'HOLD_ROLLBACK_FORK_OR_GAP'};
  const signed=sign(priv,{v:1,kind:'FLOOR_ADVANCE',epoch:EPOCH,seq:body.seq,prev:body.prev,head:body.head,request_sha:body.request_sha});
  durableCreate(eventFile(dir,body.seq),canonical(signed));
  return {status:'FLOOR_RECORDED',signed};
}
function rpc(endpoint,message,timeoutMs=800){
  return new Promise((resolve,reject)=>{
    const socket=net.createConnection(endpoint);let text='';let settled=false;
    const done=(error,value)=>{if(settled)return;settled=true;socket.destroy();error?reject(error):resolve(value);};
    socket.setTimeout(timeoutMs,()=>done(new Error('IPC_TIMEOUT')));
    socket.on('error',err=>done(err));
    socket.on('connect',()=>socket.write(canonical(message)+'\n'));
    socket.on('data',data=>{
      text+=data.toString('utf8');
      if(Buffer.byteLength(text)>LIMIT)return done(new Error('IPC_OVERFLOW'));
      if(text.includes('\n')){
        const raw=text.slice(0,text.indexOf('\n'));
        try{const parsed=JSON.parse(raw);if(canonical(parsed)!==raw)throw Error('IPC_NONCANONICAL');done(null,parsed);}catch(e){done(e);}
      }
    });
    socket.on('end',()=>done(new Error('IPC_EOF')));
  });
}
function serve(endpoint,onRequest){
  let queue=Promise.resolve();
  const server=net.createServer(socket=>{
    let line='';let complete=false;
    socket.setTimeout(2500,()=>socket.destroy());
    socket.on('data',buf=>{
      if(complete)return;
      line+=buf.toString('utf8');
      if(Buffer.byteLength(line)>LIMIT){complete=true;socket.end(canonical({status:'HOLD_IPC_SIZE'})+'\n');return;}
      if(!line.includes('\n'))return;
      complete=true;
      const raw=line.slice(0,line.indexOf('\n'));
      queue=queue.then(async()=>{
        let reply;
        try{const req=JSON.parse(raw);if(canonical(req)!==raw)throw Error('INVALID_CANONICAL');reply=await onRequest(req);}
        catch(e){reply={status:e.code||'HOLD_INVALID_OR_INTERNAL'};}
        if(!socket.destroyed)socket.end(canonical(reply)+'\n');
      }).catch(()=>{if(!socket.destroyed)socket.end('{"status":"HOLD_INTERNAL"}\n');});
    });
    socket.on('error',()=>{});
  });
  server.listen(endpoint,()=>process.stdout.write('READY\n'));
  return server;
}
if(require.main===module){
  const [command,dir,endpoint]=process.argv.slice(2);
  try{
    if(command==='init')process.stdout.write(canonical(initialize(dir))+'\n');
    else if(command==='serve'&&endpoint)serve(endpoint,req=>handle(dir,req));
    else fail('HOLD_WRONG_CLI');
  }catch(e){process.stderr.write((e.code||'HOLD_FLOOR_FAILURE')+'\n');process.exitCode=2;}
}
module.exports=Object.freeze({EPOCH,ZERO,hash,canonical,readJSON,durableCreate,verify,sign,initialize,keys,readState,handle,authenticated,rpc,serve});
