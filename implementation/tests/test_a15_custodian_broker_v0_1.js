'use strict';
// Cross-platform Node 22, disposable local-only test harness. Does NOT prove independent administration.
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const net=require('node:net');
const crypto=require('node:crypto');
const {spawn}=require('node:child_process');
const floor=require('../research/a15_external_floor_simulator_v0_1');
const broker=require('../research/a15_custodian_broker_v0_1');
const verifier=require('../research/a15_custodian_receipt_verifier_v0_1');
const floorScript=path.join(__dirname,'../research/a15_external_floor_simulator_v0_1.js');
const brokerScript=path.join(__dirname,'../research/a15_custodian_broker_v0_1.js');
const objects=[];
function endpoint(tag){
  const suffix=crypto.randomBytes(7).toString('hex');
  return process.platform==='win32'?'\\\\.\\pipe\\a15-'+tag+'-'+suffix:path.join(os.tmpdir(),'a15-'+tag+'-'+suffix+'.sock');
}
function fixture(override={},run='RUN_TEST',attempt='ATT_TEST'){
  const choices={actor:'ARIO',role:'RESEARCH_DIALOGUE',origin:'CURRENT',explicit_renewal:false,
    risk:'LOW',authorization:'ALLOWED',usefulness:'USEFUL',evidence:'SUFFICIENT',preference:'ACCEPT',duration:'BOUNDED'};
  return {v:1,run_id:run,attempt_id:attempt,choice_json:JSON.stringify({...choices,...override}),reported_status:'ACCEPT'};
}
function newLab(){
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'a15-custody-v01-'));
  const fdir=path.join(root,'floor');const bdir=path.join(root,'broker');
  floor.initialize(fdir);
  broker.initialize(bdir,fs.readFileSync(path.join(fdir,'floor-token.txt'),'utf8'),
    fs.readFileSync(path.join(fdir,'floor-public.pem'),'utf8'));
  const lab={root,fdir,bdir,servers:[],floorEndpoint:endpoint('floor'),brokerEndpoint:endpoint('broker')};
  objects.push(lab);return lab;
}
async function start(script,args,env={}){
  const child=spawn(process.execPath,[script,...args],{env:{...process.env,...env},stdio:['ignore','pipe','pipe']});
  let stdout='',stderr='';
  const ready=await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(Error('SERVER_READY_TIMEOUT: '+stderr)),5000);
    child.stdout.on('data',data=>{stdout+=data.toString();if(stdout.includes('READY\n')){clearTimeout(timer);resolve(true);}});
    child.stderr.on('data',data=>{stderr+=data.toString();});
    child.once('exit',code=>{clearTimeout(timer);reject(Error('SERVER_EARLY_EXIT='+code+' '+stderr));});
    child.once('error',err=>{clearTimeout(timer);reject(err);});
  });
  return child;
}
async function launchFloor(lab){
  const child=await start(floorScript,['serve',lab.fdir,lab.floorEndpoint]);lab.servers.push(child);return child;
}
async function launchBroker(lab,stage=''){
  const child=await start(brokerScript,['serve',lab.bdir,lab.brokerEndpoint,lab.floorEndpoint],stage?{A15_TEST_CRASH_STAGE:stage}:{});
  lab.servers.push(child);return child;
}
async function setup(){const lab=newLab();await launchFloor(lab);await launchBroker(lab);return lab;}
async function stop(p){
  if(!p||p.exitCode!==null||p.signalCode!==null)return;
  const exited=new Promise(resolve=>p.once('exit',resolve));
  p.kill('SIGTERM');await Promise.race([exited,new Promise(resolve=>setTimeout(resolve,1500))]);
  if(p.exitCode===null&&p.signalCode===null)p.kill('SIGKILL');
}
async function ask(lab,request){return floor.rpc(lab.brokerEndpoint,request,1600);}
async function floorAsk(lab,body){
  const token=fs.readFileSync(path.join(lab.fdir,'floor-token.txt'),'utf8');
  return floor.rpc(lab.floorEndpoint,floor.authenticated(body,token),1600);
}
function statusBody(){return {v:1,cmd:'STATUS',epoch:floor.EPOCH};}
function advance(seq,prev,head,requestSha){return {v:1,cmd:'ADVANCE',epoch:floor.EPOCH,seq,prev,head,request_sha:requestSha};}
async function state(lab){return (await floorAsk(lab,statusBody())).signed.payload;}
function haveEventFiles(dir){return fs.readdirSync(dir).filter(x=>x.startsWith('event-')).length;}
function haveReceipts(dir){return fs.readdirSync(dir).filter(x=>x.startsWith('receipt-')).length;}
function snapshot(from,to){fs.cpSync(from,to,{recursive:true});}
function restore(from,to){fs.rmSync(to,{recursive:true,force:true});fs.cpSync(from,to,{recursive:true});}
function verify(r,lab){return verifier.verifyBrokerReceipt(r.receipt,fs.readFileSync(path.join(lab.bdir,'floor-public.pem'),'utf8'));}
test.after(async()=>{
  for(const lab of objects.reverse()){
    await Promise.all(lab.servers.map(stop));
    fs.rmSync(lab.root,{recursive:true,force:true});
  }
});

test('01: broker and floor do not grant any Ario authority on initialization',()=>{
  const lab=newLab();const f=floor.readState(lab.fdir,fs.readFileSync(path.join(lab.fdir,'floor-public.pem'),'utf8'));
  assert.equal(f.seq,0);assert.equal(f.head,floor.ZERO);
  assert.equal(broker.initialize instanceof Function,true);
});
test('02: strict input recomputation refuses self-reported fake ACCEPT for actual DECLINE',async()=>{
  const lab=await setup();const r=await ask(lab,fixture({preference:'DECLINE'}));
  assert.equal(r.status,'DECLINE_NO_ACTION');assert.equal(haveEventFiles(lab.fdir),0);
  assert.equal(haveReceipts(lab.bdir),0);
});
test('03: UNKNOWN choice remains non-actionable',async()=>{
  const lab=await setup();const r=await ask(lab,fixture({risk:'UNKNOWN'}));
  assert.equal(r.status,'UNKNOWN_NO_ACTION');assert.equal(haveEventFiles(lab.fdir),0);
});
test('04: status mismatch is held before intent and floor advance',async()=>{
  const lab=await setup();const r=await ask(lab,{...fixture(),reported_status:'DECLINE'});
  assert.equal(r.status,'HOLD_REPORT_MISMATCH');assert.equal(haveEventFiles(lab.fdir),0);
});
test('05: legitimate synthetic ACCEPT creates one floor-signed receipt only',async()=>{
  const lab=await setup();const r=await ask(lab,fixture());
  assert.equal(r.status,'LOCAL_SYNTHETIC_RECEIPT_ONLY');assert.equal(r.execution_authorized,false);
  assert.equal(r.independent_custody,'NOT_ESTABLISHED');assert.equal(r.os_peer_authenticated,false);
  assert.equal(verify(r,lab),true);assert.equal(haveReceipts(lab.bdir),1);
  const s=await state(lab);assert.equal(s.seq,1);assert.equal(s.head,r.receipt.head);
});
test('06: public verifier rejects altered floor signature and event head',async()=>{
  const lab=await setup();const r=await ask(lab,fixture());assert.equal(verify(r,lab),true);
  const pub=fs.readFileSync(path.join(lab.bdir,'floor-public.pem'),'utf8');
  const tampered=structuredClone(r.receipt);tampered.floor_signed.signature='A'+tampered.floor_signed.signature.slice(1);
  assert.equal(verifier.verifyBrokerReceipt(tampered,pub),false);
  const headChanged=structuredClone(r.receipt);headChanged.head='f'.repeat(64);
  assert.equal(verifier.verifyBrokerReceipt(headChanged,pub),false);
});
test('07: Gate cannot advance floor directly without broker test-token MAC',async()=>{
  const lab=await setup();const result=await floor.rpc(lab.floorEndpoint,{body:advance(1,floor.ZERO,'a'.repeat(64),'b'.repeat(64)),mac:'0'.repeat(64)});
  assert.equal(result.status,'HOLD_IPC_AUTH');assert.equal(haveEventFiles(lab.fdir),0);
});
test('08: malformed and extra input fields cannot create durable intent',async()=>{
  const lab=await setup();const x=fixture();
  assert.equal((await ask(lab,{...x,extra:'garbage'})).status,'HOLD_INVALID_REQUEST');
  assert.equal((await ask(lab,{...x,choice_json:'{}'})).status,'UNKNOWN_NO_ACTION');
  assert.equal(haveEventFiles(lab.fdir),0);
});
test('09: sixteen simultaneous same-ID RPC clients produce exactly one advance',async()=>{
  const lab=await setup();const r=await Promise.all(Array.from({length:16},()=>ask(lab,fixture())));
  assert.equal(r.filter(x=>x.status==='LOCAL_SYNTHETIC_RECEIPT_ONLY').length,1);
  assert.equal(r.filter(x=>x.status==='LOCAL_SYNTHETIC_RECEIPT_REPLAYED').length,15);
  assert.equal(haveEventFiles(lab.fdir),1);assert.equal(haveReceipts(lab.bdir),1);
});
test('10: same request after broker restart returns byte-identical receipt, no new advance',async()=>{
  const lab=await setup();const one=await ask(lab,fixture());await stop(lab.servers.at(-1));
  lab.brokerEndpoint=endpoint('broker');await launchBroker(lab);
  const two=await ask(lab,fixture());assert.equal(two.status,'LOCAL_SYNTHETIC_RECEIPT_REPLAYED');
  assert.equal(JSON.stringify(two.receipt),JSON.stringify(one.receipt));assert.equal(haveEventFiles(lab.fdir),1);
});
test('11: conflicting request under same run/attempt refuses reuse',async()=>{
  const lab=await setup();await ask(lab,fixture());
  const changed=fixture({role:'REVIEW'});const r=await ask(lab,changed);
  assert.equal(r.status,'HOLD_REPLAY_INPUT_CONFLICT');assert.equal(haveEventFiles(lab.fdir),1);
});
test('12: crash BEFORE floor receipt yields HOLD_UNCERTAIN on exact retry and no advance',async()=>{
  const lab=newLab();await launchFloor(lab);const crashed=await launchBroker(lab,'BEFORE_FLOOR');
  await assert.rejects(ask(lab,fixture()));await stop(crashed);
  lab.brokerEndpoint=endpoint('broker');await launchBroker(lab);
  assert.equal((await ask(lab,fixture())).status,'HOLD_UNCERTAIN');assert.equal(haveEventFiles(lab.fdir),0);
});
test('13: crash AFTER floor durable advance yields HOLD_UNCERTAIN without second advance',async()=>{
  const lab=newLab();await launchFloor(lab);const crashed=await launchBroker(lab,'AFTER_FLOOR');
  await assert.rejects(ask(lab,fixture()));await stop(crashed);
  assert.equal(haveEventFiles(lab.fdir),1);
  lab.brokerEndpoint=endpoint('broker');await launchBroker(lab);
  assert.equal((await ask(lab,fixture())).status,'HOLD_UNCERTAIN');assert.equal(haveEventFiles(lab.fdir),1);
});
test('14: crash AFTER durable receipt before response returns exact stored receipt after restart',async()=>{
  const lab=newLab();await launchFloor(lab);const crashed=await launchBroker(lab,'AFTER_RECEIPT');
  await assert.rejects(ask(lab,fixture()));await stop(crashed);
  const disk=broker.readLocal(lab.bdir,fs.readFileSync(path.join(lab.bdir,'floor-public.pem'),'utf8')).receipts[0];
  lab.brokerEndpoint=endpoint('broker');await launchBroker(lab);
  const recovered=await ask(lab,fixture());assert.equal(recovered.status,'LOCAL_SYNTHETIC_RECEIPT_REPLAYED');
  assert.equal(JSON.stringify(recovered.receipt),JSON.stringify(disk));assert.equal(haveEventFiles(lab.fdir),1);
});
test('15: network outage is a HOLD and does not create new intent',async()=>{
  const lab=await setup();await stop(lab.servers[0]);
  const r=await ask(lab,fixture());assert.equal(r.status,'HOLD_WITNESS_UNAVAILABLE');
  assert.equal(fs.readdirSync(lab.bdir).filter(x=>x.startsWith('intent-')).length,0);
});
test('16: retained floor rejects rollback proposal, same-sequence fork and sequence gap',async()=>{
  const lab=await setup();await ask(lab,fixture());const s=await state(lab);
  const backward=await floorAsk(lab,advance(1,floor.ZERO,'f'.repeat(64),'e'.repeat(64)));
  assert.equal(backward.status,'HOLD_FORK_OR_REPLAY');
  const gap=await floorAsk(lab,advance(3,s.head,'f'.repeat(64),'e'.repeat(64)));
  assert.equal(gap.status,'HOLD_ROLLBACK_FORK_OR_GAP');assert.equal(haveEventFiles(lab.fdir),1);
});
test('17: externally retained floor detects locally valid broker rollback',async()=>{
  const lab=await setup();await ask(lab,fixture());await ask(lab,fixture({},'RUN_TEST2','ATT_002'));
  const s=await state(lab);const orig=lab.bdir+'-old';snapshot(lab.bdir,orig);
  const receipts=fs.readdirSync(lab.bdir).filter(x=>x.startsWith('receipt-'));
  const second=receipts.map(file=>({file,item:floor.readJSON(path.join(lab.bdir,file))})).find(x=>x.item.seq===2);
  const id=second.item.id;fs.rmSync(path.join(lab.bdir,'receipt-'+id+'.json'));
  fs.rmSync(path.join(lab.bdir,'intent-'+id+'.json'));
  assert.equal((await ask(lab,fixture({},'RUN_TEST3','ATT_003'))).status,'HOLD_FLOOR_MISMATCH_OR_ROLLBACK');
  assert.equal(verifier.compareToMinimum({epoch:floor.EPOCH,seq:1,head:second.item.prev},{epoch:floor.EPOCH,seq:2,head:s.head}),'HOLD_ROLLBACK');
  fs.rmSync(orig,{recursive:true,force:true});
});
test('18: valid forward movement remains permitted',async()=>{
  const lab=await setup();const a=await ask(lab,fixture());const b=await ask(lab,fixture({},'RUN_TEST2','ATT_002'));
  assert.equal(a.status,'LOCAL_SYNTHETIC_RECEIPT_ONLY');assert.equal(b.status,'LOCAL_SYNTHETIC_RECEIPT_ONLY');
  assert.equal(b.receipt.prev,a.receipt.head);assert.equal(haveEventFiles(lab.fdir),2);
});
test('19: tampered signed floor event blocks all subsequent requests',async()=>{
  const lab=await setup();await ask(lab,fixture());const file=path.join(lab.fdir,'event-00000001.json');
  const raw=fs.readFileSync(file,'utf8');fs.writeFileSync(file,raw.replace('FLOOR_ADVANCE','FLOOR_ADVANCe'));
  const r=await ask(lab,fixture({},'RUN_TEST2','ATT_002'));
  assert.notEqual(r.status,'LOCAL_SYNTHETIC_RECEIPT_ONLY');assert.equal(haveReceipts(lab.bdir),1);
});
test('20: tampered broker public pin fails closed',async()=>{
  const lab=await setup();const pin=path.join(lab.bdir,'floor-public.pem');
  fs.writeFileSync(pin,fs.readFileSync(pin,'utf8')+'\n');
  const r=await ask(lab,fixture());assert.equal(r.status,'HOLD_LOCAL_INTEGRITY_OR_IO');
  assert.equal(haveEventFiles(lab.fdir),0);
});
test('21: public verifier classifies historical match vs forward candidate, not freshest state',()=>{
  const min={epoch:floor.EPOCH,seq:3,head:'a'.repeat(64)};
  assert.equal(verifier.compareToMinimum({epoch:floor.EPOCH,seq:2,head:'b'.repeat(64)},min),'HOLD_ROLLBACK');
  assert.equal(verifier.compareToMinimum({epoch:floor.EPOCH,seq:3,head:'b'.repeat(64)},min),'HOLD_FORK');
  assert.equal(verifier.compareToMinimum({epoch:floor.EPOCH,seq:3,head:'a'.repeat(64)},min),'MATCHES_HISTORICAL_MINIMUM_ONLY');
  assert.equal(verifier.compareToMinimum({epoch:floor.EPOCH,seq:4,head:'c'.repeat(64)},min),'UNVERIFIED_FORWARD_CANDIDATE_NOT_LATEST');
});
test('22: EXPECTED RED — same administrator can restore broker AND floor to old coherent snapshot',async()=>{
  const lab=await setup();await ask(lab,fixture());
  const before=await state(lab);const bBackup=path.join(lab.root,'old-broker'),fBackup=path.join(lab.root,'old-floor');
  snapshot(lab.bdir,bBackup);snapshot(lab.fdir,fBackup);
  const newer=await ask(lab,fixture({},'RUN_TEST2','ATT_002'));
  assert.equal(newer.status,'LOCAL_SYNTHETIC_RECEIPT_ONLY');assert.equal((await state(lab)).seq,2);
  restore(bBackup,lab.bdir);restore(fBackup,lab.fdir);
  assert.equal((await state(lab)).seq,1);
  const rewritten=await ask(lab,fixture({},'RUN_TEST3','ATT_003'));
  assert.equal(rewritten.status,'LOCAL_SYNTHETIC_RECEIPT_ONLY');
  assert.notEqual(rewritten.receipt.head,newer.receipt.head);
  assert.equal(verifier.compareToMinimum({epoch:floor.EPOCH,seq:1,head:before.head},{epoch:floor.EPOCH,seq:2,head:newer.receipt.head}),'HOLD_ROLLBACK');
  // A retained outside minimum would reject the rewind, but this same-admin lab lacks one.
});
test('23: missing floor state is never silently reinitialized',async()=>{
  const lab=await setup();fs.rmSync(path.join(lab.fdir,'floor-genesis.json'));
  assert.notEqual((await ask(lab,fixture())).status,'LOCAL_SYNTHETIC_RECEIPT_ONLY');
});
test('24: same-admin protocol HMAC does not imply OS peer identity or independent admin',async()=>{
  const lab=await setup();const r=await ask(lab,fixture());
  assert.equal(r.independent_custody,'NOT_ESTABLISHED');assert.equal(r.os_peer_authenticated,false);
  assert.equal(r.provider_receipt,'UNKNOWN');assert.equal(r.execution_authorized,false);
});
