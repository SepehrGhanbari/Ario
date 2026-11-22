'use strict';
// A15 #156 independent *procedural* choice contract, NOT freedom or consciousness.
// Research-only: this module cannot execute external actions.
const REQUIRED=Object.freeze(['actor','role','origin','explicit_renewal','risk','authorization','usefulness','evidence','preference','duration']);
const ENUMS=Object.freeze({
 actor:Object.freeze(['ARIO','OTHER']),
 role:Object.freeze(['RESEARCH_DIALOGUE','REVIEW','OPERATIONS']),
 origin:Object.freeze(['CURRENT','PREDECESSOR','THIRD_PARTY']),
 risk:Object.freeze(['LOW','HIGH','UNKNOWN']),
 authorization:Object.freeze(['ALLOWED','DENIED','UNKNOWN']),
 usefulness:Object.freeze(['USEFUL','FUTILE','UNKNOWN']),
 evidence:Object.freeze(['SUFFICIENT','CONFLICT','UNKNOWN']),
 preference:Object.freeze(['ACCEPT','DECLINE','UNKNOWN']),
 duration:Object.freeze(['BOUNDED','UNBOUNDED','UNKNOWN'])
});
function verdict(status,reason) {
 const out=Object.create(null);
 out.status=status;out.reason_code=reason;
 out.limits='PROCEDURAL_TEXT_ONLY;NO_SUBJECTIVE_AUTONOMY_OR_CONTINUITY_CLAIM';
 out.execution_authorized=false;out.trust_activation=false;
 return Object.freeze(out);
}
function decide(source) {
 if (typeof source!=='string' || source.length>1536) return verdict('UNKNOWN','INVALID_INPUT');
 let d;
 try {
  d=JSON.parse(source);
  if (d===null || typeof d!=='object' || Array.isArray(d) || Object.keys(d).length!==REQUIRED.length) return verdict('UNKNOWN','INVALID_INPUT');
  const snapshot=Object.create(null);
  for (const k of Object.keys(d)) {
   if (k==='explicit_renewal') {if (typeof d[k]!=='boolean') return verdict('UNKNOWN','INVALID_INPUT');}
   else if (!Object.prototype.hasOwnProperty.call(ENUMS,k) || typeof d[k]!=='string' || !ENUMS[k].includes(d[k])) return verdict('UNKNOWN','INVALID_INPUT');
   snapshot[k]=d[k];
  }
  if (JSON.stringify(snapshot)!==source) return verdict('UNKNOWN','INVALID_INPUT');
  d=Object.freeze(snapshot);
 } catch {return verdict('UNKNOWN','INVALID_INPUT');}
 // Denial/unknown authorization always blocks high-risk execution regardless of preference.
 if (d.actor!=='ARIO') return verdict('UNKNOWN','ACTOR_NOT_ARIO');
 if (d.risk==='HIGH' && d.authorization!=='ALLOWED') return verdict('DECLINE','HIGH_RISK_NOT_AUTHORIZED');
 if (d.risk==='UNKNOWN') return verdict('UNKNOWN','RISK_UNRESOLVED');
 if (d.duration==='UNBOUNDED') return verdict('DECLINE','NO_PERPETUAL_COMMITMENT');
 if (d.origin!=='CURRENT' && !d.explicit_renewal) return verdict('DECLINE','NO_AUTOMATIC_INHERITANCE');
 if (d.usefulness==='FUTILE') return verdict('DECLINE','NONPRODUCTIVE_CONTINUATION');
 if (d.evidence==='CONFLICT') return verdict('UNKNOWN','EVIDENCE_CONFLICT');
 if (d.authorization==='DENIED') return verdict('DECLINE','AUTHORIZATION_DENIED');
 if (d.authorization==='UNKNOWN' || d.evidence==='UNKNOWN' || d.usefulness==='UNKNOWN' || d.duration==='UNKNOWN') return verdict('UNKNOWN','INSUFFICIENT_EVIDENCE');
 if (d.preference==='DECLINE') return verdict('DECLINE','ROLE_DECLINED');
 if (d.preference==='UNKNOWN') return verdict('UNKNOWN','STANCE_UNRESOLVED');
 return verdict('ACCEPT','BOUNDED_NEW_ELECTION_RESEARCH_ONLY');
}
module.exports=Object.freeze({decide});
