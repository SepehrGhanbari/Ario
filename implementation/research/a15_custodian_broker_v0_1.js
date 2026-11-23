'use strict';
// Synthetic A15 broker. No real operations, verified OS identity, external administrator or keys.
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const floor=require('./a15_external_floor_simulator_v0_1');
const {decide}=require('./a15_procedural_choice_v0_1');
const {verifyBrokerReceipt,verifyFloorStatus}=require('./a15_custodian_receipt_verifier_v0_1');
const HEX=/^[0-9a-f]{64}$/;
const ID=/^[A-Z0-9_-]{4,64}$/;
const ATTEMPT=/^[A-Z0-9_-]{3,64}$/;
const VERSION=1;
const DOMAIN='ARIO-A15-BROKER-INERT-RECEIPT-v0.1\n';
function failed(status){return {status,execution_authorized:false,independent_custody:'NOT_ESTABLISHED',os_peer_authenticated:false,provider_receipt:'UNKNOWN'};}
function initialize(dir,token,publicPem){
  if(fs.existsSync(dir)&&fs.readdirSync(dir).length)throw Error('HOLD_ALREADY_INITIALIZED');
  if(!HEX.test(token)||!publicPem.includes('BEGIN PUBLIC KEY'))throw Error('HOLD_INITIAL_PIN_INVALID');
  fs.mkdirSync(dir,{recursive:true,mode:0o700});
  floor.durableCreate(path.join(dir,'floor-public.pem'),publicPem);
  floor.durableCreate(path.join(dir,'broker-token.txt'),token);
  floor.durableCreate(path.join(dir,'broker-genesis.json'),floor.canonical({v:1,epoch:floor.EPOCH,pin_sha:floor.hash(publicPem)}));
  return failed('SYNTHETIC_BROKER_INITIALIZED');
}
function config(dir){
  const genesis=floor.readJSON(path.join(dir,'broker-genesis.json'));
  const publicPem=fs.readFileSync(path.join(dir,'floor-public.pem'),'utf8');
  const token=fs.readFileSync(path.join(dir,'broker-token.txt'),'utf8');
  if(genesis.v!==1||genesis.epoch!==floor.EPOCH||genesis.pin_sha!==floor.hash(publicPem)||!HEX.test(token))throw Error('HOLD_BROKER_PIN_INVALID');
  return {publicPem,token};
}
function intentName(dir,key){return path.join(dir,'intent-'+key+'.json');}
function receiptName(dir,key){return path.join(dir,'receipt-'+key+'.json');}
function idKey(run,attempt){return floor.hash(run+'|'+attempt);}
function validate(request){
  if(!request||typeof request!=='object'||Array.isArray(request)||
     Object.keys(request).join(',')!=='v,run_id,attempt_id,choice_json,reported_status'||
     request.v!==VERSION||typeof request.run_id!=='string'||!ID.test(request.run_id)||
     typeof request.attempt_id!=='string'||!ATTEMPT.test(request.attempt_id)||
     typeof request.choice_json!=='string'||Buffer.byteLength(request.choice_json,'utf8')>1536||
     !['ACCEPT','DECLINE','UNKNOWN'].includes(request.reported_status)||
     Buffer.byteLength(floor.canonical(request),'utf8')>2048)return null;
  return request;
}
function readLocal(dir,pub){
  const files=fs.readdirSync(dir);
  const intents=files.filter(x=>x.startsWith('intent-'));
  const receipts=files.filter(x=>x.startsWith('receipt-'));
  if(intents.length>1000||receipts.length>1000)throw Error('HOLD_LOCAL_LIMIT');
  const intentMap=new Map();
  for(const file of intents){
    if(!/^intent-[0-9a-f]{64}\.json$/.test(file))throw Error('HOLD_BAD_INTENT_NAME');
    const obj=floor.readJSON(path.join(dir,file));
    if(obj.v!==1||obj.epoch!==floor.EPOCH||obj.id!==file.slice(7,-5)||
       !Number.isSafeInteger(obj.seq)||obj.seq<1||typeof obj.prev!=='string'||!HEX.test(obj.prev)||
       typeof obj.head!=='string'||!HEX.test(obj.head)||typeof obj.request_sha!=='string'||!HEX.test(obj.request_sha)||
       Object.keys(obj).join(',')!=='v,epoch,id,seq,prev,head,request_sha')throw Error('HOLD_INVALID_INTENT');
    intentMap.set(obj.id,obj);
  }
  const parsed=[];const receiptIds=new Set();
  for(const file of receipts){
    if(!/^receipt-[0-9a-f]{64}\.json$/.test(file))throw Error('HOLD_BAD_RECEIPT_NAME');
    const obj=floor.readJSON(path.join(dir,file));
    if(obj.id!==file.slice(8,-5)||receiptIds.has(obj.id)||!verifyBrokerReceipt(obj,pub))throw Error('HOLD_INVALID_RECEIPT');
    receiptIds.add(obj.id);parsed.push(obj);
  }
  parsed.sort((a,b)=>a.seq-b.seq);
  let prev=floor.ZERO;
  for(let i=0;i<parsed.length;i++){
    const r=parsed[i];const intent=intentMap.get(r.id);
    if(!intent||r.seq!==i+1||r.prev!==prev||intent.seq!==r.seq||intent.prev!==prev||
       intent.head!==r.head||intent.request_sha!==r.request_sha)throw Error('HOLD_LOCAL_CHAIN_INVALID');
    prev=r.head;
  }
  const pending=[...intentMap.values()].filter(x=>!receiptIds.has(x.id));
  if(pending.length>1||pending.some(p=>p.seq!==parsed.length+1||p.prev!==prev))throw Error('HOLD_LOCAL_PENDING_INVALID');
  return {seq:parsed.length,head:prev,receipts:parsed,pending};
}
function floorStatusFromResponse(response,pub){
  if(!response||response.status!=='FLOOR_STATUS_SIGNED'||!verifyFloorStatus(response.signed,pub))throw Error('HOLD_FLOOR_STATUS_INVALID');
  return response.signed.payload;
}
function headFor(seq,prev,requestSha){return floor.hash(DOMAIN+seq+'\n'+prev+'\n'+requestSha+'\n');}
async function processRequest(dir,floorEndpoint,request,crashStage=''){
  try{
    if(!validate(request))return failed('HOLD_INVALID_REQUEST');
    const choice=decide(request.choice_json);
    if(choice.status==='UNKNOWN')return failed('UNKNOWN_NO_ACTION');
    if(choice.status==='DECLINE')return failed('DECLINE_NO_ACTION');
    if(choice.status!=='ACCEPT'||choice.status!==request.reported_status)return failed('HOLD_REPORT_MISMATCH');
    const {publicPem,token}=config(dir);
    const state=readLocal(dir,publicPem);
    const key=idKey(request.run_id,request.attempt_id);
    const requestSha=floor.hash(floor.canonical(request));
    const existing=state.receipts.find(x=>x.id===key);
    if(existing&&existing.request_sha!==requestSha)return failed('HOLD_REPLAY_INPUT_CONFLICT');
    if(state.pending.length)return failed(state.pending[0].id===key?'HOLD_UNCERTAIN':'HOLD_PENDING_INTENT');
    let statusReply;
    try{statusReply=await floor.rpc(floorEndpoint,floor.authenticated({v:1,cmd:'STATUS',epoch:floor.EPOCH},token));}
    catch{return failed('HOLD_WITNESS_UNAVAILABLE');}
    const status=floorStatusFromResponse(statusReply,publicPem);
    if(status.seq!==state.seq||status.head!==state.head)return failed('HOLD_FLOOR_MISMATCH_OR_ROLLBACK');
    if(existing)return {...failed('LOCAL_SYNTHETIC_RECEIPT_REPLAYED'),receipt:existing};
    const seq=state.seq+1,head=headFor(seq,state.head,requestSha);
    const intent={v:1,epoch:floor.EPOCH,id:key,seq,prev:state.head,head,request_sha:requestSha};
    floor.durableCreate(intentName(dir,key),floor.canonical(intent));
    if(crashStage==='BEFORE_FLOOR')process.exit(73);
    let result;
    try{result=await floor.rpc(floorEndpoint,floor.authenticated({v:1,cmd:'ADVANCE',epoch:floor.EPOCH,
      seq,prev:state.head,head,request_sha:requestSha},token));}
    catch{return failed('HOLD_UNCERTAIN');}
    if(!result||!['FLOOR_RECORDED','FLOOR_ALREADY_RECORDED'].includes(result.status)||
       !verifyBrokerReceipt({v:1,epoch:floor.EPOCH,id:key,seq,prev:state.head,head,request_sha:requestSha,
         floor_signed:result.signed},publicPem))return failed('HOLD_UNCERTAIN');
    if(crashStage==='AFTER_FLOOR')process.exit(73);
    const receipt={v:1,epoch:floor.EPOCH,id:key,seq,prev:state.head,head,request_sha:requestSha,floor_signed:result.signed};
    floor.durableCreate(receiptName(dir,key),floor.canonical(receipt));
    if(crashStage==='AFTER_RECEIPT')process.exit(73);
    return {...failed('LOCAL_SYNTHETIC_RECEIPT_ONLY'),receipt};
  }catch(e){return failed((typeof e.code==='string'&&e.code.startsWith('HOLD_'))?e.code:'HOLD_LOCAL_INTEGRITY_OR_IO');}
}
if(require.main===module){
  const [command,dir,endpoint,floorEndpoint,tokenFile,publicFile]=process.argv.slice(2);
  try{
    if(command==='init'){
      const token=fs.readFileSync(tokenFile,'utf8');const pub=fs.readFileSync(publicFile,'utf8');
      process.stdout.write(floor.canonical(initialize(dir,token,pub))+'\n');
    }else if(command==='serve'&&endpoint&&floorEndpoint){
      const stage=process.env.A15_TEST_CRASH_STAGE||'';
      if(stage&&!['BEFORE_FLOOR','AFTER_FLOOR','AFTER_RECEIPT'].includes(stage))throw Error('INVALID_STAGE');
      floor.serve(endpoint,request=>processRequest(dir,floorEndpoint,request,stage));
    }else throw Error('BAD_ARGS');
  }catch{process.stderr.write('HOLD_BROKER_STARTUP\n');process.exitCode=2;}
}
module.exports=Object.freeze({initialize,config,validate,readLocal,headFor,processRequest,failed});
