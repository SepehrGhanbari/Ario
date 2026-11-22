'use strict';
const fs=require('fs'),vm=require('vm'),crypto=require('crypto'),assert=require('assert');
const path=require('path');const d=__dirname;
const html=fs.readFileSync(path.join(d,'g5_mobile_offline_verifier.html'),'utf8');
const match=html.match(/<script>([\s\S]*?)<\/script>/);
if(!match)throw Error('SCRIPT_MISSING');
const code=match[1].split('const fileBox=')[0];
const context=vm.createContext({TextEncoder,TextDecoder,Uint8Array,crypto:crypto.webcrypto,atob,console});
vm.runInContext(code,context,{timeout:5000});
async function call(v1,v2,epoch='research_nov_2026_no_signer'){
 const x={epoch,v1_b64:v1.toString('base64'),v2_b64:v2.toString('base64')};
 return vm.runInContext('verifyCandidate('+JSON.stringify(x)+')',context,{timeout:5000});
}
function file(s){return fs.readFileSync(path.join(d,s));}
(async()=>{
 const a=file('synthetic_seq3_v1.jsonl'), b=file('synthetic_seq3_v2.jsonl');
 const c=file('synthetic_rollback_seq2_v1.jsonl'), d2=file('synthetic_rollback_seq2_v2.jsonl');
 const good=await call(a,b);assert.equal(good.verdict,'CONSISTENT_WITH_HISTORICAL_MINIMUM_ONLY_NOT_LATEST');
 const rollback=await call(c,d2);assert.equal(rollback.verdict,'HOLD_ROLLBACK');
 const split=await call(c,b);assert.equal(split.verdict,'HOLD_INVALID_JOURNAL_OR_CRYPTO');
 const partial=await call(a,b.subarray(0,b.length-1));assert.equal(partial.verdict,'HOLD_INVALID_JOURNAL_OR_CRYPTO');
 const wrongEpoch=await call(a,b,'other');assert.equal(wrongEpoch.verdict,'HOLD_WRONG_EPOCH');
 const badHash=Buffer.from(b.toString().replace('6e1d74f7860e','0e1d74f7860e'));
 const corruption=await call(a,badHash);assert.equal(corruption.verdict,'HOLD_INVALID_JOURNAL_OR_CRYPTO');
 const badMeta=await vm.runInContext('verifyCandidate({foo:1})',context,{timeout:5000});assert.equal(badMeta.verdict,'HOLD_BAD_CANDIDATE_FORMAT');
 const corruptB64=await vm.runInContext('verifyCandidate({"epoch":"research_nov_2026_no_signer","v1_b64":"a%4","v2_b64":"="})',context,{timeout:5000});assert.equal(corruptB64.verdict,'HOLD_INVALID_JOURNAL_OR_CRYPTO');
 console.log('G5_MOBILE_OFFLINE_JS_NEGATIVE_AND_POSITIVE=8/8_PASS');
})().catch(e=>{console.error(e);process.exitCode=1});