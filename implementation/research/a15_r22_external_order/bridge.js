'use strict';
// Public synthetic research ONLY. Reuses v0.7 unchanged. No production signer or authority.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const f=require('../../tests/fixtures/a15_v07_fixture');
const {v04,v05,v07,canon,sign}=f;
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const checksum=x=>sha(crypto.createHash('sha256').update(x).digest());
const DOMAIN='ARIO_A15_R22_EXTERNAL_ORDER_V08_SYNTHETIC';
const check=(b,s)=>{if(!b)throw Error(s);};
const parse=x=>{check(typeof x==='string'&&Buffer.byteLength(x)<=32768,'HOLD_SIZE');let o=JSON.parse(x);check(canon(o)===x,'HOLD_CANONICAL');return o;};
const fields=(o,ks)=>o&&typeof o==='object'&&!Array.isArray(o)&&Object.keys(o).join(',')===ks;
const signed=(o,pub)=>fields(o,'payload,signature')&&typeof o.signature==='string'&&/^[A-Za-z0-9+/]{86}==$/.test(o.signature)&&crypto.verify(null,Buffer.from(canon(o.payload)),pub,Buffer.from(o.signature,'base64'));
const read=(dir,name)=>fs.readFileSync(path.join(dir,name),'utf8');
const proofRef=(raw,env)=>({checksum:checksum(env),proof_sha256:sha(raw)});
function readPhase(root,n){const p=path.join(root,'r'+n);return {payload:read(p,'payload.json'),envelope:read(p,'envelope.json'),proof:n===3?null:read(p,'envelope.json.proof')};}
function verifyChain(phases){
  check(Array.isArray(phases)&&phases.length===3,'HOLD_PHASE_COUNT');
  const [a,b,c]=phases, [r1,r2,r3]=phases.map(x=>parse(x.payload));
  check(fields(r1,'domain,kind,pins,reservation')&&r1.domain===DOMAIN&&r1.kind==='RESERVE','HOLD_R1_SCHEMA');
  check(fields(r2,'domain,kind,r1,proof1,outer,stage')&&r2.domain===DOMAIN&&r2.kind==='SIGNED_STAGE','HOLD_R2_SCHEMA');
  check(fields(r3,'domain,kind,r2,proof2,final')&&r3.domain===DOMAIN&&r3.kind==='FINAL','HOLD_R3_SCHEMA');
  check(typeof a.proof==='string'&&a.proof.length>0&&typeof b.proof==='string'&&b.proof.length>0,'HOLD_PROOF_MISSING');
  check(r2.proof1===a.proof&&canon(r2.r1)===canon(proofRef(a.proof,a.envelope)),'HOLD_R1_PROOF_LINK');
  check(r3.proof2===b.proof&&canon(r3.r2)===canon(proofRef(b.proof,b.envelope)),'HOLD_R2_PROOF_LINK');
  // Official Sigsum proof verification and fresh scanner verification are separate REQUIRED checks in the Python runner.
  // This function verifies only the semantic links, never claims inclusion by parsing a proof string.
  const reserve=parse(r1.reservation),stage=parse(r2.stage),final=parse(r3.final),pins=r1.pins;
  check(fields(reserve,'v,profile,input,challenge,nonce_key')&&reserve.v===7&&reserve.profile===v07.PROFILE,'HOLD_RESERVE');
  check(fields(stage,'v,domain,pre,binding')&&stage.domain===v05.DOMAIN&&stage.v===1,'HOLD_STAGE');
  const v=v05.verifyEvidence(r3.final,pins);check(v.evidence_verified,'HOLD_FINAL_EVIDENCE');
  check(canon({v:final.v,domain:final.domain,pre:final.pre,binding:final.binding})===r2.stage,'HOLD_STAGE_FINAL_LINK');
  const event=stage.binding.payload.event.payload;
  check(fields(reserve.input,'request,seq,prev,authorization')&&reserve.input.seq===1&&reserve.input.prev===v04.ZERO&&event.seq===1&&event.prev===v04.ZERO,'HOLD_SEQUENCE');
  check(canon(reserve.input.request)===canon(event.request)&&canon(reserve.input.authorization)===canon(event.authorization)&&reserve.challenge===stage.pre.payload.challenge&&reserve.nonce_key===v.nonce_key,'HOLD_RESERVE_STAGE_LINK');
  check(signed(r2.outer,pins.floorPublicKey),'HOLD_OUTER_SIGNATURE');
  const expected={domain:DOMAIN,kind:'R1_BOUND_STAGE',r1:r2.r1,reservation_sha256:sha(r1.reservation),stage_sha256:sha(r2.stage)};
  check(canon(r2.outer.payload)===canon(expected),'HOLD_OUTER_LINK');
  return {status:'SEMANTIC_LINKS_VERIFIED_SYNTHETIC_ONLY',execution_authorized:false,independent_custody:'NOT_ESTABLISHED',inner_signing_time:'UNKNOWN',local_durability_attestation:'NOT_ESTABLISHED',head:v.head};
}
function produce(work,transport){
  const root=path.join(work,'lab');fs.mkdirSync(root,{mode:0o700});
  const l=f.lab(root);let r1,r2;const cfg=f.config(l);
  const o=v07.openLedger(l.dir,f.config(l,{
    requestPre:q=>{
      const reservation=read(l.dir,'reserve-0001.json');
      r1=transport(1,{domain:DOMAIN,kind:'RESERVE',pins:l.pins,reservation});
      // Callback returns only after live transport has checked R1. Existing inner signatures follow this return.
      return cfg.requestPre(q);
    },requestPost:q=>{
      check(r1&&r1.proof,'HOLD_R1_MISSING');const stage=read(l.dir,'stage-0001.json');
      const a=proofRef(r1.proof,r1.envelope);
      const outer=sign({domain:DOMAIN,kind:'R1_BOUND_STAGE',r1:a,reservation_sha256:sha(parse(r1.payload).reservation),stage_sha256:sha(stage)},l.f);
      r2=transport(2,{domain:DOMAIN,kind:'SIGNED_STAGE',r1:a,proof1:r1.proof,outer,stage});
      return cfg.requestPost(q);
    }}));
  const input=f.input(l);check(o.begin(input).status==='STAGED_AWAITING_POST','HOLD_BEGIN');
  check(o.complete().status==='FINALIZED_SYNTHETIC_EVIDENCE_ONLY','HOLD_COMPLETE');
  const r=o.readFinal(1);check(r.status==='HISTORICAL_FINAL_EVIDENCE_ONLY','HOLD_FINAL');
  check(r2&&r2.proof,'HOLD_R2_MISSING');
  const r3=transport(3,{domain:DOMAIN,kind:'FINAL',r2:proofRef(r2.proof,r2.envelope),proof2:r2.proof,final:r.evidence});
  return {phases:[r1,r2,r3],verify:verifyChain([r1,r2,r3])};
}
function liveTransport(root){return (n,obj)=>{
  const p=path.join(root,'r'+n);fs.mkdirSync(p,{mode:0o700});fs.writeFileSync(path.join(p,'payload.json'),canon(obj),{mode:0o600,flag:'wx'});
  execFileSync('python3',[path.join(__dirname,'transport.py'),'commit',root,String(n)],{stdio:['ignore','inherit','inherit'],timeout:240000});
  return readPhase(root,n);
};}
if(require.main===module){try{const [cmd,root]=process.argv.slice(2);check(root&&process.argv.length===4,'HOLD_ARGUMENTS');if(cmd==='produce'){const x=produce(root,liveTransport(root));console.log(canon(x.verify));}else if(cmd==='verify')console.log(canon(verifyChain([1,2,3].map(n=>readPhase(root,n)))));else throw Error('HOLD_ARGUMENTS');}catch(e){console.error(e.message);process.exitCode=2;}}
module.exports={produce,verifyChain,DOMAIN,proofRef,sha,checksum};
