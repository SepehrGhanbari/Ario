'use strict';
// Public-only, no private-key or trust-authority operation.
const {EPOCH,ZERO,verify,hash,canonical}=require('./a15_external_floor_simulator_v0_1');
const HEX=/^[0-9a-f]{64}$/;
function verifyFloorStatus(signed,pin){
  if(!verify(signed,pin,'FLOOR_STATUS'))return false;
  const p=signed.payload;
  return Object.keys(p).join(',')==='v,kind,epoch,seq,head'&&
    Number.isSafeInteger(p.seq)&&p.seq>=0&&p.seq<=1000&&typeof p.head==='string'&&HEX.test(p.head)&&
    (p.seq!==0||p.head===ZERO);
}
function verifyBrokerReceipt(record,pin){
  try{
    if(!record||typeof record!=='object'||Array.isArray(record)||
      Object.keys(record).join(',')!=='v,epoch,id,seq,prev,head,request_sha,floor_signed'||
      record.v!==1||record.epoch!==EPOCH||!HEX.test(record.id)||!HEX.test(record.prev)||
      !HEX.test(record.head)||!HEX.test(record.request_sha)||!Number.isSafeInteger(record.seq)||
      record.seq<1||record.seq>1000||!verify(record.floor_signed,pin,'FLOOR_ADVANCE'))return false;
    const p=record.floor_signed.payload;
    return Object.keys(p).join(',')==='v,kind,epoch,seq,prev,head,request_sha'&&
      p.seq===record.seq&&p.prev===record.prev&&p.head===record.head&&p.request_sha===record.request_sha;
  }catch{return false;}
}
function compareToMinimum(candidate,minimum){
  if(!candidate||!minimum||candidate.epoch!==EPOCH||minimum.epoch!==EPOCH||
     !Number.isSafeInteger(candidate.seq)||!Number.isSafeInteger(minimum.seq)||
     candidate.seq<0||minimum.seq<0||!HEX.test(candidate.head)||!HEX.test(minimum.head))return 'HOLD_UNVERIFIED_MINIMUM';
  if(candidate.seq<minimum.seq)return 'HOLD_ROLLBACK';
  if(candidate.seq===minimum.seq)return candidate.head===minimum.head?'MATCHES_HISTORICAL_MINIMUM_ONLY':'HOLD_FORK';
  return 'UNVERIFIED_FORWARD_CANDIDATE_NOT_LATEST';
}
module.exports=Object.freeze({verifyFloorStatus,verifyBrokerReceipt,compareToMinimum});
