'use strict';
// Synthetic red/green tests. A passing expected RED test is NOT proof of independent custody.
const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const floor = require('../research/a15_external_floor_simulator_v0_4.js');
const operator = require('../research/a15_outside_minimum_custodian_v0_4.js');
const labs = [];

function keys(){return crypto.generateKeyPairSync('ed25519',{publicKeyEncoding:{format:'pem',type:'spki'},privateKeyEncoding:{format:'pem',type:'pkcs8'}});}
function request(resource='synthetic-record-1'){
  return {v:1,action:'ADVANCE',resource,decision:'ACCEPT',policy_version:'RESEARCH-POLICY-V1'};
}
function signedAuth(lab,req,seq,prev,options={}){
  const {head,requestSha}=floor.transitionFor(req,seq,prev);
  const now=Date.now();
  const payload={v:1,domain:floor.DOMAIN,kind:'ADVANCE_AUTHORIZATION',principal:options.principal||'SYNTHETIC_PRINCIPAL_A',
    scope:'floor.advance',policy_version:req.policy_version,nonce:options.nonce||crypto.randomBytes(32).toString('hex'),
    issued_at:options.issued_at??(now-3000),expires_at:options.expires_at??(now+150000),seq,prev,head,request_sha:requestSha};
  return {payload,signature:crypto.sign(null,Buffer.from(JSON.stringify(payload)),lab.authority.privateKey).toString('base64')};
}
function setup(){
  if(process.platform==='win32')throw Error('POSIX_ONLY_NOT_SUPPORTED');
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'a15-v04-'));
  const fdir=path.join(root,'floor'),odir=path.join(root,'operator');
  const authority=keys(),signer=keys();
  const config={authorityPublicKey:authority.publicKey,expectedAuthoritySha256:floor.sha256(Buffer.from(authority.publicKey)),floorPrivateKey:signer.privateKey};
  floor.initFloor(fdir,config);
  const service=floor.openFloor(fdir,config);
  operator.init(odir,signer.publicKey,floor.sha256(Buffer.from(signer.publicKey)),authority.publicKey,config.expectedAuthoritySha256);
  const lab={root,fdir,odir,authority,signer,config,service};labs.push(lab);
  return lab;
}
function next(lab,options={}){
  const s=lab.service.status();const req=options.request||request('synthetic-record-'+(s.seq+1));
  const auth=signedAuth(lab,req,s.seq+1,s.head,options);
  return {request:req,seq:s.seq+1,prev:s.head,authorization:auth};
}
function deliver(lab,response){
  assert.equal(response.status,'FLOOR_RECORDED_SYNTHETIC_ONLY');
  return operator.audit(lab.odir,{events:[response.signed]},true);
}
function assertHold(fn,code){assert.throws(fn,e=>e?.code===code,code);}
function rowOf(signed){return JSON.stringify({v:1,kind:'ADVANCE',seq:signed.payload.seq,head:signed.payload.head,signed})+'\n';}
// Synthetic same-admin restore includes POSIX directory permissions, not only file bytes.
// Node/runner copy semantics may otherwise produce an insecure 0755 directory and
// fail the test before it reaches the intended common-admin rollback counterexample.
function snapshot(d,to){
  const sourceMode=fs.statSync(d).mode&0o777;
  fs.cpSync(d,to,{recursive:true});
  fs.chmodSync(to,sourceMode);
}
function restore(d,from){
  const retainedMode=fs.statSync(from).mode&0o777;
  fs.rmSync(d,{recursive:true,force:true});
  fs.cpSync(from,d,{recursive:true});
  fs.chmodSync(d,retainedMode);
}
function sleep(ms){return new Promise(resolve=>setTimeout(resolve,ms));}

test.after(()=>{for(const l of labs.reverse())fs.rmSync(l.root,{recursive:true,force:true});});

test('01 GREEN: valid fresh authorization advances Floor and Operator once',()=>{
  const l=setup(),r=l.service.advance(next(l));assert.equal(r.advanced,true);
  assert.equal(deliver(l,r).committed,true);
  assert.equal(l.service.status().seq,1);assert.equal(operator.readState(l.odir).seq,1);
});

test('02 GREEN: authorization absent cannot initialize a trusted Floor fixture',()=>{
  const l=setup();
  assertHold(()=>floor.openFloor(l.fdir,{...l.config,authorityPublicKey:''}),'HOLD_AUTHORITY_NOT_ESTABLISHED');
  assert.equal(l.service.status().seq,0);
});

test('03 GREEN: no caller-controlled clock, signer or head in admission input',()=>{
  const l=setup(),base=next(l);
  for(const injection of [{now:base.authorization.payload.issued_at},{now:-1},{now:9999999999999},
     {floorPrivateKey:l.signer.privateKey},{head:'f'.repeat(64)},{authorityPublicKey:l.authority.publicKey}]){
    assert.equal(l.service.advance({...base,...injection}).status,'HOLD_REQUEST_INVALID');
  }
  assert.equal(l.service.status().seq,0);
});

test('04 GREEN: expired authority is refused despite an old caller supplied time',()=>{
  const l=setup(),at=Date.now(),body=next(l,{issued_at:at-100000,expires_at:at-1000});
  assert.equal(l.service.advance(body).status,'HOLD_AUTHORITY_NOT_ESTABLISHED');
  assert.equal(l.service.advance({...body,now:at-2000}).status,'HOLD_REQUEST_INVALID');
  assert.equal(l.service.status().seq,0);
});

test('05 GREEN: not-yet-valid authority cannot advance',()=>{
  const l=setup(),at=Date.now(),body=next(l,{issued_at:at+10000,expires_at:at+50000});
  assert.equal(l.service.advance(body).status,'HOLD_AUTHORITY_NOT_ESTABLISHED');
});

test('06 GREEN: historical accepted record survives the authorization expiration',async()=>{
  const l=setup(),now=Date.now(),r=l.service.advance(next(l,{issued_at:now-1000,expires_at:now+600}));
  deliver(l,r);assert.equal(floor.verifyAdvance(r.signed,l.signer.publicKey,l.authority.publicKey,l.config.expectedAuthoritySha256),true);
  await sleep(900);
  assert.equal(floor.verifyAdvance(r.signed,l.signer.publicKey,l.authority.publicKey,l.config.expectedAuthoritySha256),true);
  assert.equal(l.service.status().seq,1);assert.equal(operator.readState(l.odir).seq,1);
  assert.equal(l.service.advance({...next(l),seq:1,prev:floor.ZERO,authorization:r.signed.payload.authorization}).status,'HOLD_NONCE_REUSE');
});

test('07 GREEN: replay returns byte-identical stored historic receipt after expiry without re-signing',async()=>{
  const l=setup(),at=Date.now(),body=next(l,{issued_at:at-2000,expires_at:at+500});
  const one=l.service.advance(body);deliver(l,one);await sleep(700);
  const after=floor.openFloor(l.fdir,l.config).advance(body);
  assert.equal(after.status,'FLOOR_HISTORICAL_RECEIPT_REPLAY_ONLY');
  assert.deepEqual(after.signed,one.signed);assert.equal(l.service.status().seq,1);
});

test('08 GREEN: signer cannot create a historical event accepted outside its recorded time window',()=>{
  const l=setup(),body=next(l),r=l.service.advance(body);deliver(l,r);
  const payload={...r.signed.payload,accepted_at:body.authorization.payload.expires_at+1};
  const signed={payload,signature:crypto.sign(null,Buffer.from(JSON.stringify(payload)),l.signer.privateKey).toString('base64')};
  assert.equal(floor.verifyAdvance(signed,l.signer.publicKey,l.authority.publicKey,l.config.expectedAuthoritySha256),false);
});

test('09 GREEN: operator maintains historical validity for a valid new forward event after old expiry',async()=>{
  const l=setup(),now=Date.now(),r=l.service.advance(next(l,{issued_at:now-1000,expires_at:now+450}));
  deliver(l,r);await sleep(650);
  const second=l.service.advance(next(l));deliver(l,second);
  assert.equal(operator.readState(l.odir).seq,2);
});

test('10 GREEN: same nonce in different transition is denied at Floor, even after restart',()=>{
  const l=setup(),nonce=crypto.randomBytes(32).toString('hex');
  const one=l.service.advance(next(l,{nonce}));deliver(l,one);
  const two=next(l,{nonce});assert.equal(l.service.advance(two).status,'HOLD_NONCE_REUSE');
  assert.equal(floor.openFloor(l.fdir,l.config).advance(two).status,'HOLD_NONCE_REUSE');
  assert.equal(operator.readState(l.odir).seq,1);
});

test('11 GREEN: a distinct authorized nonce allows legitimate forward progress',()=>{
  const l=setup();deliver(l,l.service.advance(next(l)));deliver(l,l.service.advance(next(l)));
  assert.equal(l.service.status().seq,2);assert.equal(operator.readState(l.odir).seq,2);
});

test('12 GREEN: scoped nonce includes principal identity; same raw nonce under different principal is distinct',()=>{
  const l=setup(),nonce=crypto.randomBytes(32).toString('hex');
  deliver(l,l.service.advance(next(l,{nonce,principal:'SYNTHETIC_PRINCIPAL_A'})));
  deliver(l,l.service.advance(next(l,{nonce,principal:'SYNTHETIC_PRINCIPAL_B'})));
  assert.equal(l.service.status().seq,2);
});

test('13 GREEN: independently signed duplicate nonce across different valid advances is rejected by Operator',()=>{
  const l=setup(),nonce=crypto.randomBytes(32).toString('hex');
  const a=l.service.advance(next(l,{nonce}));deliver(l,a);
  const second=next(l,{nonce}),t=floor.transitionFor(second.request,second.seq,second.prev);
  const payload={v:1,kind:'FLOOR_ADVANCE',epoch:floor.EPOCH,seq:second.seq,prev:second.prev,head:t.head,
    request_sha:t.requestSha,request:second.request,authorization:second.authorization,accepted_at:Date.now()};
  const forgedByFloorKey={payload,signature:crypto.sign(null,Buffer.from(JSON.stringify(payload)),l.signer.privateKey).toString('base64')};
  assert.equal(floor.verifyAdvance(forgedByFloorKey,l.signer.publicKey,l.authority.publicKey,l.config.expectedAuthoritySha256),true);
  assertHold(()=>operator.audit(l.odir,{events:[forgedByFloorKey]},true),'HOLD_NONCE_REUSE');
  assert.equal(operator.readState(l.odir).seq,1);
});

test('14 GREEN: operator audit rejects duplicate nonce within a multi-event candidate',()=>{
  const l=setup(),n=crypto.randomBytes(32).toString('hex');
  const first=next(l,{nonce:n}),t1=floor.transitionFor(first.request,first.seq,first.prev);
  const p1={v:1,kind:'FLOOR_ADVANCE',epoch:floor.EPOCH,seq:1,prev:floor.ZERO,head:t1.head,request_sha:t1.requestSha,
    request:first.request,authorization:first.authorization,accepted_at:Date.now()};
  const s1={payload:p1,signature:crypto.sign(null,Buffer.from(JSON.stringify(p1)),l.signer.privateKey).toString('base64')};
  const req2=request('second-in-batch'),t2=floor.transitionFor(req2,2,t1.head);
  const auth2=signedAuth(l,req2,2,t1.head,{nonce:n});
  const p2={v:1,kind:'FLOOR_ADVANCE',epoch:floor.EPOCH,seq:2,prev:t1.head,head:t2.head,request_sha:t2.requestSha,
    request:req2,authorization:auth2,accepted_at:Date.now()};
  const s2={payload:p2,signature:crypto.sign(null,Buffer.from(JSON.stringify(p2)),l.signer.privateKey).toString('base64')};
  assertHold(()=>operator.audit(l.odir,{events:[s1,s2]},true),'HOLD_NONCE_REUSE');
  assert.equal(operator.readState(l.odir).seq,0);
});

test('15 GREEN: tampered historical journal containing reused nonce is detected on every read',()=>{
  const l=setup(),nonce=crypto.randomBytes(32).toString('hex');
  const one=l.service.advance(next(l,{nonce}));deliver(l,one);
  const two=next(l,{nonce}),t=floor.transitionFor(two.request,two.seq,two.prev);
  const p={v:1,kind:'FLOOR_ADVANCE',epoch:floor.EPOCH,seq:two.seq,prev:two.prev,head:t.head,
    request_sha:t.requestSha,request:two.request,authorization:two.authorization,accepted_at:Date.now()};
  const signed={payload:p,signature:crypto.sign(null,Buffer.from(JSON.stringify(p)),l.signer.privateKey).toString('base64')};
  const file=path.join(l.odir,'minimum.jsonl');fs.appendFileSync(file,rowOf(signed));
  assertHold(()=>operator.readState(l.odir),'HOLD_NONCE_REUSE_HISTORICAL');
});

test('16 GREEN: a crash after durable nonce intent refuses automatic retry',()=>{
  const l=setup(),body=next(l);
  const crashed=floor.openFloor(l.fdir,{...l.config,testOnlyFaultHook:stage=>{if(stage==='AFTER_DURABLE_INTENT')throw Error('synthetic crash');}});
  assert.equal(crashed.advance(body).status,'HOLD_FLOOR_INTEGRITY_OR_IO');
  assert.equal(floor.openFloor(l.fdir,l.config).advance(body).status,'HOLD_UNCERTAIN_PENDING_INTENT');
  assert.equal(operator.readState(l.odir).seq,0);
});

test('17 GREEN: a crash after durable receipt allows an exact stored receipt replay',()=>{
  const l=setup(),body=next(l);
  const crashed=floor.openFloor(l.fdir,{...l.config,testOnlyFaultHook:stage=>{if(stage==='AFTER_DURABLE_RECEIPT')throw Error('synthetic crash');}});
  assert.equal(crashed.advance(body).status,'HOLD_FLOOR_INTEGRITY_OR_IO');
  const restarted=floor.openFloor(l.fdir,l.config);
  const result=restarted.advance(body);
  assert.equal(result.status,'FLOOR_HISTORICAL_RECEIPT_REPLAY_ONLY');
  assert.equal(restarted.status().seq,1);
  assert.equal(deliver(l,{...result,status:'FLOOR_RECORDED_SYNTHETIC_ONLY'}).committed,true);
});

test('18 GREEN: missing or corrupt Floor journal does not silently reinitialize',()=>{
  const l=setup();
  fs.writeFileSync(path.join(l.fdir,'floor-journal.jsonl'),'broken');
  assertHold(()=>floor.openFloor(l.fdir,l.config).status(),'HOLD_JOURNAL_TRUNCATED');
});

test('19 GREEN: stale Floor lock prevents new signing and consumes no nonce',()=>{
  const l=setup(),body=next(l);
  fs.writeFileSync(path.join(l.fdir,'floor.lock'),'unreleased lock',{mode:0o600});
  assert.equal(l.service.advance(body).status,'HOLD_FLOOR_LOCKED');
  assert.equal(l.service.status().seq,0);
  fs.rmSync(path.join(l.fdir,'floor.lock'));
  assert.equal(l.service.advance(body).status,'FLOOR_RECORDED_SYNTHETIC_ONLY');
});

test('20 GREEN: invalid authority substitution is rejected by independent Floor configured pin',()=>{
  const l=setup(),body=next(l),forged=keys();
  const payload=body.authorization.payload;
  const fake={payload,signature:crypto.sign(null,Buffer.from(JSON.stringify(payload)),forged.privateKey).toString('base64')};
  assert.equal(l.service.advance({...body,authorization:fake}).status,'HOLD_AUTHORITY_NOT_ESTABLISHED');
  assert.equal(l.service.status().seq,0);
});

test('21 RED retained: common administrator rewinds both Floor and Operator and can accept alternative fork',()=>{
  const l=setup();const one=l.service.advance(next(l));deliver(l,one);
  const fSnap=path.join(l.root,'old-floor'),oSnap=path.join(l.root,'old-operator');
  snapshot(l.fdir,fSnap);snapshot(l.odir,oSnap);
  const second=l.service.advance(next(l,{request:request('original-seq2')}));deliver(l,second);
  restore(l.fdir,fSnap);restore(l.odir,oSnap);
  const forkService=floor.openFloor(l.fdir,l.config);
  const other={...next({...l,service:forkService},{request:request('forked-seq2')})};
  const alternate=forkService.advance(other);deliver(l,alternate);
  assert.notEqual(alternate.head,second.head);
  assert.equal(operator.readState(l.odir).seq,2);
});

test('22 GREEN: owner-only directories and files still enforced on both Floor and Operator',()=>{
  const l=setup(),body=next(l);
  fs.chmodSync(l.fdir,0o777);
  assert.equal(l.service.advance(body).status,'HOLD_DIRECTORY_PERMISSIONS');
  assertHold(()=>floor.openFloor(l.fdir,l.config),'HOLD_DIRECTORY_PERMISSIONS');
  fs.chmodSync(l.fdir,0o700);
  fs.chmodSync(l.odir,0o777);
  assertHold(()=>operator.readState(l.odir),'HOLD_OPERATOR_DIRECTORY_PERMISSIONS');
});

test('23 GREEN: journal read does not depend on current wall clock and keeps accepted timestamp immutable',()=>{
  const l=setup(),r=l.service.advance(next(l));deliver(l,r);
  const historical=r.signed.payload.accepted_at;
  assert.equal(floor.verifyAdvance(r.signed,l.signer.publicKey,l.authority.publicKey,l.config.expectedAuthoritySha256),true);
  const s=floor.openFloor(l.fdir,l.config).status();
  assert.equal(s.seq,1);assert.equal(operator.readState(l.odir).events[0].payload.accepted_at,historical);
});

const workerPath=path.join(__dirname,'fixtures/a15_v04_floor_worker.js');
function workerSetup(l,body){
  fs.writeFileSync(path.join(l.root,'test-only-config.json'),JSON.stringify(l.config),{mode:0o600});
  fs.writeFileSync(path.join(l.root,'test-only-request.json'),JSON.stringify(body),{mode:0o600});
}
function runWorker(l,stage=''){
  const p=spawnSync(process.execPath,[workerPath,l.root,stage],{encoding:'utf8',timeout:15000});
  return {code:p.status,stderr:p.stderr,stdout:p.stdout,reply:p.status===0?JSON.parse(p.stdout):null};
}
// TEST-ONLY: the subprocess has already exited (spawnSync). A real service must not auto-delete stale locks.
function releaseCrashedWorkerLockForFixtureOnly(l, result){
  assert.equal(result.code,73,'only a confirmed exited synthetic crash worker can unlock the fixture');
  const lock=path.join(l.fdir,'floor.lock');
  assert.equal(fs.statSync(lock).mode&0o777,0o600);
  fs.unlinkSync(lock);
}
function runWorkerAsync(l,stage='',requestFile='test-only-request.json'){
  return new Promise((resolve,reject)=>{
    const {spawn}=require('node:child_process');
    const p=spawn(process.execPath,[workerPath,l.root,stage,requestFile],{stdio:['ignore','pipe','pipe']});
    let stdout='',stderr='';
    p.stdout.on('data',buf=>stdout+=buf.toString());
    p.stderr.on('data',buf=>stderr+=buf.toString());
    p.once('error',reject);
    p.once('close',code=>resolve({code,stdout,stderr,reply:code===0?JSON.parse(stdout):null}));
  });
}

test('24 GREEN: actual separate-process exit after durable intent leaves a HOLD on restart',()=>{
  const l=setup(),body=next(l);workerSetup(l,body);
  const r=runWorker(l,'AFTER_DURABLE_INTENT');
  assert.equal(r.code,73,r.stderr);
  assert.equal(floor.openFloor(l.fdir,l.config).advance(body).status,'HOLD_FLOOR_LOCKED');
  releaseCrashedWorkerLockForFixtureOnly(l,r);
  assert.equal(floor.openFloor(l.fdir,l.config).advance(body).status,'HOLD_UNCERTAIN_PENDING_INTENT');
  assert.equal(floor.openFloor(l.fdir,l.config).status().seq,0);
});

test('25 GREEN: actual separate-process exit after durable receipt replays identical signed bytes',()=>{
  const l=setup(),body=next(l);workerSetup(l,body);
  const r=runWorker(l,'AFTER_DURABLE_RECEIPT');assert.equal(r.code,73,r.stderr);
  assert.equal(floor.openFloor(l.fdir,l.config).advance(body).status,'HOLD_FLOOR_LOCKED');
  releaseCrashedWorkerLockForFixtureOnly(l,r);
  const persisted=floor.readState(l.fdir,{...l.config,floor_public_key:l.signer.publicKey,
    floor_sha256:floor.sha256(Buffer.from(l.signer.publicKey)),authority_public_key:l.authority.publicKey,
    authority_sha256:l.config.expectedAuthoritySha256,v:1,epoch:floor.EPOCH}).receipts[0].signed;
  const after=runWorker(l);
  assert.equal(after.code,0,after.stderr);
  assert.equal(after.reply.status,'FLOOR_HISTORICAL_RECEIPT_REPLAY_ONLY');
  assert.deepEqual(after.reply.signed,persisted);
  assert.equal(l.service.status().seq,1);
});

test('26 GREEN: concurrent separate processes with same nonce make only one durable record',async()=>{
  const l=setup(),body=next(l);workerSetup(l,body);
  const replies=await Promise.all([runWorkerAsync(l),runWorkerAsync(l)]);
  for(const r of replies)assert.equal(r.code,0,r.stderr);
  const statuses=replies.map(x=>x.reply.status);
  assert.equal(statuses.filter(x=>x==='FLOOR_RECORDED_SYNTHETIC_ONLY').length,1);
  assert.ok(statuses.every(x=>['FLOOR_RECORDED_SYNTHETIC_ONLY','FLOOR_HISTORICAL_RECEIPT_REPLAY_ONLY','HOLD_FLOOR_LOCKED'].includes(x)));
  assert.equal(l.service.status().seq,1);
  assert.equal(fs.readdirSync(l.fdir).filter(n=>n.startsWith('intent-')).length,1);
});

test('27 GREEN: two different-nonce processes racing for the same sequence cannot both commit',async()=>{
  const l=setup(),first=next(l),second=next(l);workerSetup(l,first);
  fs.writeFileSync(path.join(l.root,'test-only-request-second.json'),JSON.stringify(second),{mode:0o600});
  const replies=await Promise.all([runWorkerAsync(l),runWorkerAsync(l,'','test-only-request-second.json')]);
  for(const r of replies)assert.equal(r.code,0,r.stderr);
  const statuses=replies.map(x=>x.reply.status);
  assert.equal(statuses.filter(x=>x==='FLOOR_RECORDED_SYNTHETIC_ONLY').length,1);
  assert.ok(statuses.every(x=>['FLOOR_RECORDED_SYNTHETIC_ONLY','HOLD_FLOOR_LOCKED','HOLD_FORK_OR_GAP'].includes(x)));
  assert.equal(l.service.status().seq,1);
  assert.equal(fs.readdirSync(l.fdir).filter(n=>n.startsWith('intent-')).length,1);
});

test('28 GREEN: pending nonce intent blocks unrelated following requests until explicit recovery',()=>{
  const l=setup(),body=next(l);workerSetup(l,body);
  const crashed=runWorker(l,'AFTER_DURABLE_INTENT');
  releaseCrashedWorkerLockForFixtureOnly(l,crashed);
  const different={...body,authorization:signedAuth(l,body.request,body.seq,body.prev)};
  assert.equal(l.service.advance(different).status,'HOLD_UNCERTAIN_PENDING_INTENT');
});

test('29 GREEN: corrupted durable nonce intent cannot be ignored',()=>{
  const l=setup(),body=next(l);workerSetup(l,body);
  const crashed=runWorker(l,'AFTER_DURABLE_INTENT');
  releaseCrashedWorkerLockForFixtureOnly(l,crashed);
  const name=fs.readdirSync(l.fdir).find(x=>x.startsWith('intent-'));
  fs.writeFileSync(path.join(l.fdir,name),'{}');
  assert.equal(l.service.advance(body).status,'HOLD_INTENT_INVALID');
});

test('30 GREEN: changing recorded floor signed event or its nonce blocks startup',()=>{
  const l=setup(),body=next(l),r=l.service.advance(body);
  assert.equal(r.status,'FLOOR_RECORDED_SYNTHETIC_ONLY');
  const file=path.join(l.fdir,'floor-journal.jsonl');
  fs.writeFileSync(file,fs.readFileSync(file,'utf8').replace('FLOOR_ADVANCE','FLOOR_ADVANCe'));
  assertHold(()=>floor.openFloor(l.fdir,l.config).status(),'HOLD_JOURNAL_INVALID');
});

test('31 GREEN: Floor rejects a correctly re-signed historical row with reused scoped nonce',()=>{
  const l=setup(),nonce=crypto.randomBytes(32).toString('hex');
  const one=l.service.advance(next(l,{nonce}));deliver(l,one);
  const second=next(l,{nonce}),t=floor.transitionFor(second.request,second.seq,second.prev);
  const payload={v:1,kind:'FLOOR_ADVANCE',epoch:floor.EPOCH,seq:second.seq,prev:second.prev,
    head:t.head,request_sha:t.requestSha,request:second.request,authorization:second.authorization,accepted_at:Date.now()};
  const signed={payload,signature:crypto.sign(null,Buffer.from(JSON.stringify(payload)),l.signer.privateKey).toString('base64')};
  const row={v:1,kind:'ADVANCE',seq:2,head:t.head,
    nonce_key:floor.nonceKey(second.authorization,l.config.expectedAuthoritySha256),
    submission_sha:floor.sha256(JSON.stringify(second)),signed};
  fs.appendFileSync(path.join(l.fdir,'floor-journal.jsonl'),JSON.stringify(row)+'\n');
  assertHold(()=>floor.openFloor(l.fdir,l.config).status(),'HOLD_JOURNAL_INVALID');
});

test('32 GREEN: nonce is not freed when a previous valid authorization expires',async()=>{
  const l=setup(),nonce=crypto.randomBytes(32).toString('hex'),at=Date.now();
  const one=l.service.advance(next(l,{nonce,issued_at:at-1000,expires_at:at+400}));
  deliver(l,one);await sleep(600);
  const second=next(l,{nonce});
  assert.equal(l.service.advance(second).status,'HOLD_NONCE_REUSE');
  assert.equal(operator.readState(l.odir).seq,1);
});

test('33 GREEN: historical Floor receipt is tied to exact pinned signer, authority and record',()=>{
  const l=setup(),one=l.service.advance(next(l));deliver(l,one);
  const wrongAuthority=keys(),wrongFloor=keys();
  assert.equal(floor.verifyAdvance(one.signed,l.signer.publicKey,wrongAuthority.publicKey,
    floor.sha256(Buffer.from(wrongAuthority.publicKey))),false);
  assert.equal(floor.verifyAdvance(one.signed,wrongFloor.publicKey,l.authority.publicKey,
    l.config.expectedAuthoritySha256),false);
  const modified={payload:{...one.signed.payload,request:{...one.signed.payload.request,resource:'modified'}},signature:one.signed.signature};
  assert.equal(floor.verifyAdvance(modified,l.signer.publicKey,l.authority.publicKey,
    l.config.expectedAuthoritySha256),false);
});

test('34 GREEN: authorization expiring between durable intent and signing remains HOLD (nonce stays pending)',()=>{
  const l=setup(),at=Date.now(),body=next(l,{issued_at:at-1000,expires_at:at+100});
  const delayed=floor.openFloor(l.fdir,{...l.config,testOnlyFaultHook:stage=>{
    if(stage==='AFTER_DURABLE_INTENT'){
      const until=Date.now()+220;
      while(Date.now()<until){} // controlled synthetic pause, never used in production
    }
  }});
  assert.equal(delayed.advance(body).status,'HOLD_AUTHORITY_EXPIRED_DURING_INTENT');
  assert.equal(l.service.advance(body).status,'HOLD_UNCERTAIN_PENDING_INTENT');
  assert.equal(l.service.status().seq,0);
});
