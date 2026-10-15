/**
 * W4-B vector-only SECOND-LANGUAGE verification (Node.js >=20).
 * No signer, no keys minted, no identity claims, no network and no authorization.
 * Verifies fixed public Ed25519 TEST-ONLY message and byte serializer independently.
 */
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash, createPublicKey, verify} from 'node:crypto';

const doc=JSON.parse(fs.readFileSync(new URL('./W4B_TEST_VECTORS.json',import.meta.url),'utf8'));
const keyPattern=/^[A-Za-z0-9._:/-]{1,128}$/;
const att=doc.attestation;
const expectedFields=[
 'profile','payload_sha256','payload_byte_length','event_namespace','event_id','event_type',
 'event_epoch','claim_id','claim_scope','requested_use','audience','request_id',
 'witness_key_id','source_id','custodian_id','control_group_id','parent_refs'
].sort();
assert.deepEqual(Object.keys(att).sort(),expectedFields);
for(const [name,val] of Object.entries(att)){
 if(name==='profile'){
   assert.equal(val,'ARIO-W4B-ED25519-ASCIIJSON-V0.1-TEST-ONLY');
 }else if(name==='payload_sha256'){
   assert.match(val,/^[0-9a-f]{64}$/);
 }else if(name==='payload_byte_length'){
   assert.equal(Number.isSafeInteger(val),true);
   assert(val>=1 && val<=65536);
 }else if(name==='parent_refs'){
   assert(Array.isArray(val) && val.length<=16);
   assert(val.every(v=>typeof v==='string' && keyPattern.test(v)));
   assert.deepEqual(val,[...new Set(val)].sort());
 }else{
   assert.equal(typeof val,'string');
   assert.match(val,keyPattern);
 }
}
assert(['RECORD_DESCRIPTION','INDEPENDENT_TARGET_SUPPORT'].includes(att.requested_use));
const canonical=Buffer.from(JSON.stringify(Object.fromEntries(Object.entries(att).sort(([a],[b]) => a < b ? -1 : a > b ? 1 : 0))),'ascii');
assert.equal(canonical.toString('hex'),doc.canonical_attestation_utf8_hex);
const domain=Buffer.from('ARIO-W4B-SOURCE-ATTESTATION-V0.1-TEST\0','ascii');
assert.equal(domain.toString('hex'),doc.domain_hex);
const message=Buffer.concat([domain,canonical]);
assert.equal(message.toString('hex'),doc.signed_message_hex);

const payload=Buffer.from(doc.synthetic_payload_utf8_hex,'hex');
const hash=createHash('sha256').update(payload).digest('hex');
assert.equal(hash,att.payload_sha256);
assert.equal(payload.length,att.payload_byte_length);

const publicRaw=Buffer.from(doc.test_public_key_hex,'hex');
const keyId='sha256:'+createHash('sha256').update(publicRaw).digest('hex');
assert.equal(keyId,doc.test_key_id);
assert.equal(keyId,att.witness_key_id);
// SPKI wrapper over raw Ed25519 32-byte public key (RFC8410) — independent of Python serializer.
const spkiDer=Buffer.concat([Buffer.from('302a300506032b6570032100','hex'),publicRaw]);
const key=createPublicKey({key:spkiDer,format:'der',type:'spki'});
const signature=Buffer.from(doc.test_signature_hex,'hex');
assert.equal(verify(null,message,key,signature),true);
const flipped=Buffer.from(signature);flipped[0]^=1;
assert.equal(verify(null,message,key,flipped),false);
assert.equal(verify(null,Buffer.concat([Buffer.from('DIFFERENT-DOMAIN\0'),canonical]),key,signature),false);
const actualWire=Buffer.concat([
 Buffer.from('{"attestation":','ascii'),canonical,
 Buffer.from(',"signature_hex":"'+signature.toString('hex')+'"}','ascii')
]);
assert.equal(actualWire.toString('hex'),doc.wire_message_utf8_hex);
assert.equal(doc.expected_outcome.status,'UNKNOWN');
assert.equal(doc.expected_outcome.admission_decision,'NOT_EVALUATED');
assert.equal(doc.expected_outcome.source_authentication,'UNKNOWN');
assert.equal(doc.expected_outcome.source_independence,'UNKNOWN');
assert.equal(doc.expected_outcome.reviewer_authorization,'UNKNOWN');
assert.equal(doc.expected_outcome.claim_truth,'UNKNOWN');
console.log('W4B_SECOND_LANGUAGE_NODE_VECTOR=PASS');
console.log('BYTE_CANONICALIZATION_AND_WIRE_IDENTITY=PASS');
console.log('REAL_ED25519_TEST_SIGNATURE_VERIFICATION=PASS');
console.log('NEGATIVE_TAMPER_AND_DOMAIN_CONTROLS=PASS');
console.log('NO_EPISTEMIC_AUTHORITY_OR_ADMISSION=PASS');
