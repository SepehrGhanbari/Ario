'use strict';
// A15 #158: frozen G0 precedence. Research-only; no browser or transport access.
const REQUIRED = Object.freeze(['editor_readback','send_clicked','user_bubble_visible','reply_complete','output_copied','chat_link_recorded','duplicate_bubble_visible','timed_out']);
function classifyG0(x) {
  if (x.duplicate_bubble_visible) return 'DUPLICATE_DISPATCH_SUSPECTED';
  if ((x.user_bubble_visible && !x.send_clicked) ||
      (x.reply_complete && !x.user_bubble_visible)) return 'EVIDENCE_CONFLICT';
  if (x.editor_readback !== 'PASS' && x.send_clicked) return 'UNVERIFIED_INPUT_WAS_SENT';
  if (x.editor_readback === 'FAIL') return 'INPUT_MISMATCH';
  if (x.editor_readback === 'UNKNOWN') return 'INPUT_UNVERIFIED';
  if (!x.send_clicked) return 'NOT_SENT';
  if (!x.user_bubble_visible) return 'DISPATCH_UNKNOWN';
  if (!x.reply_complete || !x.output_copied) return 'RESPONSE_INCOMPLETE';
  if (!x.chat_link_recorded) return 'CAPTURE_UNLINKED';
  return 'GUI_OUTPUT_CAPTURED';
}
// Separate V1 input guard: G0 historical function and 14 fixtures remain unchanged.
function evaluateG0V1(source) {
  if (typeof source !== 'string' || source.length > 2048) return 'INVALID_EVIDENCE_FIELDS';
  try {
    const x=JSON.parse(source);
    if (x === null || typeof x !== 'object' || Array.isArray(x)) return 'INVALID_EVIDENCE_FIELDS';
    const keys=Object.keys(x);
    if (keys.length !== REQUIRED.length ||
        keys.some(k=>!REQUIRED.includes(k)) ||
        REQUIRED.some(k=>!Object.prototype.hasOwnProperty.call(x,k))) return 'INVALID_EVIDENCE_FIELDS';
    if (!['PASS','FAIL','UNKNOWN'].includes(x.editor_readback) ||
        REQUIRED.slice(1).some(k=>typeof x[k] !== 'boolean')) return 'INVALID_EVIDENCE_FIELDS';
    const snapshot=Object.create(null);
    for (const k of REQUIRED) snapshot[k]=x[k];
    if (JSON.stringify(snapshot)!==source && JSON.stringify(x)!==source) return 'INVALID_EVIDENCE_FIELDS';
    return classifyG0(Object.freeze(snapshot));
  } catch { return 'INVALID_EVIDENCE_FIELDS'; }
}
module.exports=Object.freeze({classifyG0,evaluateG0V1});
