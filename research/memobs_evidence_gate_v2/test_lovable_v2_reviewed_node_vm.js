/** MEM-OBS-01 — Node VM regression against the embedded JS, with a mocked DOM.
 * Not a real-browser or external authority test. No npm dependencies.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');
const assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, 'ario-memory-observability-demo-v2-reviewed.html'), 'utf8');
const match = html.match(/<script>([\s\S]*?)<\/script>/);
assert(match, 'embedded JS exists');
const cardHTML = [];
const elements = new Map();
const document = {
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, {
      addEventListener() {}, appendChild() {}, style: {}, textContent: '', innerHTML: ''
    });
    return elements.get(id);
  },
  createElement() {
    return {
      className: '', style: {},
      set innerHTML(value) { this._html = value; cardHTML.push(value); },
      get innerHTML() { return this._html || ''; }
    };
  }
};
const sandbox = { document, Date, TextEncoder, console,
  crypto: { subtle: { digest: async (_alg, bytes) => crypto.createHash('sha256').update(Buffer.from(bytes)).digest() } }
};
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(match[1], sandbox);
const source = (id, provenanceType = 'LOCAL_EMPIRICAL', rawEvidence = '{"fabricated":true}') => ({
  id, concept: id, assertion: `claim ${id}`, provenanceType,
  sourceId: 'caller_supplied', rawEvidence
});
(async () => {
  const empirical = await sandbox.ingestRecord(source('empirical'));
  assert.strictEqual(empirical.status, 'RECORDED');
  const witness = await sandbox.ingestRecord(source('witness', 'SIGNED_WITNESS', 'fake-sig'));
  assert.strictEqual(witness.status, 'RECORDED');
  assert.throws(() => { empirical.status = 'SUPPORTED'; }, /read-only/);
  assert.throws(() => Object.defineProperty(empirical, 'status', { value: 'SUPPORTED' }), TypeError);
  await assert.rejects(sandbox.ingestRecord(empirical), /HOLD_UNAUTHORIZED_STATUS_AT_INGEST/);
  const missing = await sandbox.ingestRecord({ ...source('missing', 'MISSING'), sourceId: '' });
  assert.strictEqual(missing.status, 'UNKNOWN');
  const ai = await sandbox.ingestRecord(source('ai', 'AI_GENERATED'));
  assert.strictEqual(ai.status, 'UNSUPPORTED');

  const injected = '<img src=x onerror=alert(1)>';
  const attack = await sandbox.ingestRecord({ ...source(injected), concept: '__proto__', sourceId: injected, parentId: injected });
  assert.strictEqual(attack.status, 'RECORDED');
  assert(!cardHTML.some(card => card.includes(injected)), 'raw metadata injected into markup');
  assert(cardHTML.some(card => card.includes('&lt;img src=x onerror=alert(1)&gt;')), 'metadata not visibly escaped');

  const original = await sandbox.ingestRecord({ ...source('one'), concept: 'same', assertion: 'A' });
  const conflict = await sandbox.ingestRecord({ ...source('two'), concept: 'same', assertion: 'B' });
  assert.strictEqual(original.status, 'CONTESTED');
  assert.strictEqual(conflict.status, 'CONTESTED');
  const version = await sandbox.ingestRecord({ ...source('revision'), concept: 'different', assertion: 'old' });
  const next = await sandbox.reviseRecord('revision', 'new', 'unverified', 'author');
  assert.strictEqual(version.status, 'REVISED');
  assert.strictEqual(next.status, 'RECORDED');
  assert.strictEqual(next.parentId, version.id);
  const before = sandbox.journal.length;
  const rollback = await sandbox.rollback('checkpoint-0', 'synthetic');
  assert.strictEqual(rollback.status, 'RECORDED');
  assert.strictEqual(sandbox.journal.length, before + 1);
  assert.strictEqual(sandbox.journal.filter(r => ['SUPPORTED', 'ACCEPTED'].includes(r.status)).length, 0);
  console.log('PASS: 12 bounded checks + preserved synthetic journal semantics (Node VM mocked DOM)');
})().catch(err => { console.error(err); process.exitCode = 1; });
