'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const v04=require('../../research/a15_external_floor_simulator_v0_4');
const v05=require('../../research/a15_temporal_evidence_verifier_v0_5');
const v07=require('../../research/a15_integrated_temporal_ledger_v0_7');
const t=1800000000000,canon=JSON.stringify;
const key=()=>crypto.generateKeyPairSync('ed25519');
const pem=k=>k.publicKey.export({type:'spki',format:'pem'});
const pin=p=>v04.sha256(Buffer.from(p));
const sign=(payload,k)=>({payload,signature:crypto.sign(null,Buffer.from(canon(payload)),k.privateKey).toString('base64')});
function config(l,override={}){return {profile:v07.PROFILE,pins:l.pins,floorPrivateKey:l.f.privateKey,
  requestPre:q=>sign({v:1,domain:v05.DOMAIN,kind:'PRE',epoch:q.epoch,authorization_sha:q.authorization_sha,challenge:q.challenge,time_ms:l.base+1000,uncertainty_ms:100},l.w),
  requestPost:q=>sign({v:1,domain:v05.DOMAIN,kind:'POST',epoch:q.epoch,binding_sha:q.binding_sha,time_ms:l.base+3000,uncertainty_ms:100},l.w),...override};}
function lab(root){const f=key(),a=key(),w=key(),pins={floorPublicKey:pem(f),floorSha256:pin(pem(f)),authorityPublicKey:pem(a),authoritySha256:pin(pem(a)),witnessPublicKey:pem(w),witnessSha256:pin(pem(w))};
const l={root,dir:path.join(root,'state'),f,a,w,pins,base:t};const r=v07.initialize(l.dir,pins);if(r.status!=='LEDGER_INITIALIZED_SYNTHETIC_ONLY')throw Error(r.status);return l;}
function input(l,o={}){const seq=o.seq??1,prev=o.prev??v04.ZERO,request={v:1,action:'ADVANCE',resource:o.resource??'INERT_TEST',decision:'ACCEPT',policy_version:'RESEARCH_V1'},x=v04.transitionFor(request,seq,prev);
const authorization=sign({v:1,domain:v04.DOMAIN,kind:'ADVANCE_AUTHORIZATION',principal:o.principal??'TEST_ACTOR',scope:'floor.advance',policy_version:request.policy_version,nonce:o.nonce??crypto.randomBytes(32).toString('hex'),issued_at:o.issued??l.base,expires_at:o.expires??l.base+10000,seq,prev,head:x.head,request_sha:x.requestSha},l.a);
return canon({request,seq,prev,authorization});}
function saveConfig(l){const p=path.join(l.root,'worker-config.json');fs.writeFileSync(p,canon({pins:l.pins,base:l.base,dir:l.dir,f:l.f.privateKey.export({type:'pkcs8',format:'pem'}),w:l.w.privateKey.export({type:'pkcs8',format:'pem'})}),{mode:0o600});return p;}
module.exports={v04,v05,v07,canon,t,key,sign,config,lab,input,saveConfig};
