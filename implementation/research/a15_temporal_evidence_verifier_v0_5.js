'use strict';
// Public-only RESEARCH_ONLY evidence predicate. No admission, signing, persistence or trusted clock.
const crypto = require('node:crypto');
const v04 = require('./a15_external_floor_simulator_v0_4');
const DOMAIN = 'ARIO_A15_TEMPORAL_EVIDENCE_V0_5_SYNTHETIC';
const HEX = /^[0-9a-f]{64}$/;
const MAX_BYTES = 32768;
const MAX_UNCERTAINTY_MS = 1000; // Synthetic protocol profile, not a real clock guarantee.
const canonical = JSON.stringify;
const hash = x => crypto.createHash('sha256').update(canonical(x),'utf8').digest('hex');
const keys = (x,k) => x!==null && typeof x==='object' && !Array.isArray(x) && Object.keys(x).join(',')===k;
const out = status => ({status, evidence_verified:status==='SYNTHETIC_TEMPORAL_EVIDENCE_VERIFIED_ONLY',
  execution_authorized:false, admission_authorized:false, independent_custody:'NOT_ESTABLISHED',
  trusted_time:'NOT_ESTABLISHED', latest_state:'UNKNOWN'});
function publicPin(pem, expected){
  if(typeof pem!=='string'||pem.length>4096||typeof expected!=='string'||!HEX.test(expected)||
     v04.sha256(Buffer.from(pem))!==expected)throw Error('HOLD_PIN_INVALID');
  const key=crypto.createPublicKey(pem);
  if(key.asymmetricKeyType!=='ed25519')throw Error('HOLD_PIN_INVALID');
  // Require exact canonical SPKI PEM: no alternative formatting, private PEM or alternate key encoding.
  if(key.export({type:'spki',format:'pem'})!==pem)throw Error('HOLD_PIN_INVALID');
  return key.export({type:'spki',format:'der'}).toString('hex');
}
function signedBy(obj,pub){
  if(!keys(obj,'payload,signature')||typeof obj.signature!=='string'||!(/^[A-Za-z0-9+/]{86}==$/.test(obj.signature)))return false;
  const sig=Buffer.from(obj.signature,'base64');
  return sig.length===64&&sig.toString('base64')===obj.signature&&crypto.verify(null,Buffer.from(canonical(obj.payload),'utf8'),pub,sig);
}
function interval(p){
  if(!Number.isSafeInteger(p.time_ms)||p.time_ms<0||!Number.isSafeInteger(p.uncertainty_ms)||p.uncertainty_ms<0||p.uncertainty_ms>MAX_UNCERTAINTY_MS)return null;
  const lo=p.time_ms-p.uncertainty_ms,hi=p.time_ms+p.uncertainty_ms;
  return lo>=0&&Number.isSafeInteger(lo)&&Number.isSafeInteger(hi)?{lo,hi}:null;
}
function verifyEvidence(raw,pins){
  try{
    if(!keys(pins,'floorPublicKey,floorSha256,authorityPublicKey,authoritySha256,witnessPublicKey,witnessSha256'))return out('HOLD_PIN_INVALID');
    const ids=[publicPin(pins.floorPublicKey,pins.floorSha256),publicPin(pins.authorityPublicKey,pins.authoritySha256),publicPin(pins.witnessPublicKey,pins.witnessSha256)];
    if(new Set(ids).size!==3)return out('HOLD_KEY_ROLE_ALIAS');
    if(typeof raw!=='string'||Buffer.byteLength(raw,'utf8')>MAX_BYTES)return out('HOLD_EVIDENCE_INVALID');
    const e=JSON.parse(raw);
    if(canonical(e)!==raw||!keys(e,'v,domain,pre,binding,post')||e.v!==1||e.domain!==DOMAIN)return out('HOLD_EVIDENCE_INVALID');
    if(!e.pre||!e.binding||!e.post)return out('HOLD_TIME_EVIDENCE_MISSING');
    if(!signedBy(e.pre,pins.witnessPublicKey)||!signedBy(e.post,pins.witnessPublicKey))return out('HOLD_WITNESS_SIGNATURE');
    if(!signedBy(e.binding,pins.floorPublicKey))return out('HOLD_BINDING_SIGNATURE');
    const p=e.pre.payload,b=e.binding.payload,q=e.post.payload;
    if(!keys(p,'v,domain,kind,epoch,authorization_sha,challenge,time_ms,uncertainty_ms')||p.v!==1||p.domain!==DOMAIN||p.kind!=='PRE'||p.epoch!==v04.EPOCH||typeof p.challenge!=='string'||!HEX.test(p.challenge)||p.challenge===v04.ZERO||typeof p.authorization_sha!=='string'||!HEX.test(p.authorization_sha))return out('HOLD_PRE_SCHEMA');
    if(!keys(b,'v,domain,kind,epoch,pre_sha,event')||b.v!==1||b.domain!==DOMAIN||b.kind!=='FLOOR_BINDING'||b.epoch!==v04.EPOCH||b.pre_sha!==hash(e.pre))return out('HOLD_PRE_BINDING');
    if(!keys(q,'v,domain,kind,epoch,binding_sha,time_ms,uncertainty_ms')||q.v!==1||q.domain!==DOMAIN||q.kind!=='POST'||q.epoch!==v04.EPOCH||q.binding_sha!==hash(e.binding))return out('HOLD_POST_BINDING');
    if(!v04.verifyAdvance(b.event,pins.floorPublicKey,pins.authorityPublicKey,pins.authoritySha256))return out('HOLD_EVENT_INVALID');
    const event=b.event.payload,a=event.authorization.payload;
    if(p.authorization_sha!==hash(event.authorization))return out('HOLD_AUTHORIZATION_BINDING');
    const pre=interval(p),post=interval(q);
    if(!pre||!post)return out('HOLD_TIME_INTERVAL_INVALID');
    // The entire conservative interval must fit within the grant. Exclusive expiry.
    if(pre.lo<a.issued_at||post.hi>=a.expires_at)return out('HOLD_OUTSIDE_AUTHORIZATION_WINDOW');
    if(pre.hi>post.lo)return out('HOLD_WITNESS_ORDER_UNCERTAIN');
    if(event.accepted_at<pre.hi||event.accepted_at>post.lo)return out('HOLD_FLOOR_TIME_INCONSISTENT');
    return {...out('SYNTHETIC_TEMPORAL_EVIDENCE_VERIFIED_ONLY'),
      epoch:event.epoch,seq:event.seq,head:event.head,nonce_key:v04.nonceKey(event.authorization,pins.authoritySha256),
      interval:{earliest_ms:pre.lo,latest_ms:post.hi},evidence_sha:hash(e)};
  }catch{return out('HOLD_EVIDENCE_OR_PIN_INVALID');}
}
module.exports=Object.freeze({DOMAIN,hash,verifyEvidence});
