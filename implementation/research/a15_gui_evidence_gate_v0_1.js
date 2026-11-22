'use strict';
// A15 #159 G1 primary order is frozen. This pure evaluator asserts no transport authority.
// Input boundary: a primitive JSON string, not an arbitrary JS object or Proxy.
const ENUMS=Object.freeze({
  baseline:Object.freeze(['VALID','INVALID','UNKNOWN']),
  editor:Object.freeze(['MATCH','MISMATCH','UNKNOWN']),
  send:Object.freeze(['CLICKED','NOT_CLICKED','UNKNOWN']),
  new_user:Object.freeze(['NEW','ABSENT','UNKNOWN']),
  rendered_text:Object.freeze(['MATCH','MISMATCH','UNKNOWN']),
  sequence:Object.freeze(['VALID','INVALID','UNKNOWN']),
  competing:Object.freeze(['EXCLUDED','OBSERVED','UNKNOWN']),
  duplicate:Object.freeze(['NONE','DETECTED','UNKNOWN']),
  response:Object.freeze(['NEW','ABSENT','UNKNOWN']),
  response_binding:Object.freeze(['MATCH','MISMATCH','UNKNOWN']),
  copy_binding:Object.freeze(['MATCH','MISMATCH','UNKNOWN']),
  link_binding:Object.freeze(['MATCH','MISMATCH','UNKNOWN'])
});
const FIELD_NAMES=Object.freeze(Object.keys(ENUMS));
const DEFAULT=Object.freeze({baseline:'VALID',editor:'MATCH',send:'CLICKED',new_user:'NEW',rendered_text:'MATCH',sequence:'VALID',competing:'EXCLUDED',duplicate:'NONE',response:'NEW',response_binding:'MATCH',copy_binding:'MATCH',link_binding:'MATCH'});
function classifyG1(x) {
  if ((x.send==='NOT_CLICKED' && x.new_user==='NEW') ||
      (x.new_user==='ABSENT' && x.response==='NEW') ||
      (x.response==='ABSENT' && x.response_binding==='MATCH')) return 'EVIDENCE_CONFLICT';
  if (x.duplicate==='DETECTED') return 'DUPLICATE_DISPATCH_SUSPECTED';
  if (x.competing==='OBSERVED') return 'COMPETING_ACTION_DETECTED';
  if (x.send==='CLICKED' && x.editor!=='MATCH') return 'UNVERIFIED_INPUT_SEND_ATTEMPT';
  if (x.editor!=='MATCH') return 'INPUT_NOT_ATTESTED';
  if (x.baseline!=='VALID') return 'ATTEMPT_BASELINE_UNKNOWN';
  if (x.send==='NOT_CLICKED') return 'NOT_SENT';
  if (x.send==='UNKNOWN') return 'SEND_ACTION_UNKNOWN';
  if (x.new_user!=='NEW') return 'DISPATCH_UNKNOWN';
  if (x.rendered_text==='MISMATCH') return 'RENDERED_PROMPT_MISMATCH';
  if (x.rendered_text==='UNKNOWN') return 'RENDERED_PROMPT_UNKNOWN';
  if (x.sequence==='INVALID') return 'EVIDENCE_ORDER_CONFLICT';
  if (x.sequence==='UNKNOWN') return 'CURRENT_ATTEMPT_CORRELATION_UNKNOWN';
  if (x.competing==='UNKNOWN') return 'CURRENT_ATTEMPT_CORRELATION_UNKNOWN';
  if (x.duplicate==='UNKNOWN') return 'DUPLICATE_VISIBILITY_UNKNOWN';
  if (x.response!=='NEW') return 'RESPONSE_INCOMPLETE';
  if (x.response_binding==='MISMATCH') return 'RESPONSE_ASSOCIATION_CONFLICT';
  if (x.response_binding==='UNKNOWN') return 'RESPONSE_ASSOCIATION_UNKNOWN';
  if (x.copy_binding!=='MATCH') return 'COPY_NOT_ATTESTED';
  if (x.link_binding!=='MATCH') return 'CAPTURE_UNLINKED';
  return 'GUI_CORRELATED_OBSERVATION_ONLY';
}
function hazardList(x) {
  const a=[];
  Object.setPrototypeOf(a,null);
  const add=s=>Object.defineProperty(a,a.length,{value:s,enumerable:true,writable:false,configurable:false});
  if (x.duplicate==='DETECTED') add('DUPLICATE_DISPATCH_SUSPECTED');
  if (x.competing==='OBSERVED') add('COMPETING_ACTION_DETECTED');
  if (x.send==='CLICKED' && x.editor!=='MATCH') add('UNVERIFIED_INPUT_SEND_ATTEMPT');
  if (x.competing==='UNKNOWN') add('CURRENT_ATTEMPT_CORRELATION_UNKNOWN');
  if (x.duplicate==='UNKNOWN') add('DUPLICATE_VISIBILITY_UNKNOWN');
  if (x.response_binding==='MISMATCH') add('RESPONSE_ASSOCIATION_CONFLICT');
  if (x.copy_binding==='MISMATCH') add('COPY_NOT_ATTESTED');
  return Object.freeze(a);
}
function result(primary,hazards,snapshot) {
  const r=Object.create(null);
  r.primary=primary; r.hazards=hazards; r.snapshot=snapshot;
  r.provider_receipt='UNKNOWN'; r.causal_sender='UNKNOWN'; r.execution_authorized=false;
  return Object.freeze(r);
}
function invalid() {
  const a=['INVALID_EVIDENCE_FIELDS']; Object.setPrototypeOf(a,null);
  return result('INVALID_EVIDENCE_FIELDS',Object.freeze(a),null);
}
function evaluateG1(source) {
  if (typeof source!=='string' || source.length>2048) return invalid();
  try {
    const parsed=JSON.parse(source);
    if (parsed===null || typeof parsed!=='object' || Array.isArray(parsed)) return invalid();
    const keys=Object.keys(parsed);
    if (keys.length!==FIELD_NAMES.length) return invalid();
    const snapshot=Object.create(null);
    for (const k of keys) {
      if (!Object.prototype.hasOwnProperty.call(ENUMS,k)) return invalid();
      const d=Object.getOwnPropertyDescriptor(parsed,k);
      if (!d || !Object.prototype.hasOwnProperty.call(d,'value') ||
          typeof d.value!=='string' || !ENUMS[k].includes(d.value)) return invalid();
      snapshot[k]=d.value;
    }
    Object.freeze(snapshot);
    // Reject duplicate keys, whitespace/non-canonical encodings and escaped equivalents.
    // The reserialized object is null-prototype: inherited toJSON is never consulted.
    if (JSON.stringify(snapshot)!==source) return invalid();
    return result(classifyG1(snapshot),hazardList(snapshot),snapshot);
  } catch { return invalid(); }
}
module.exports=Object.freeze({evaluateG1,classifyG1,DEFAULT,FIELD_NAMES});
