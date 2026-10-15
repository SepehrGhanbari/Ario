/** Node.js second-language VIEW-BYTE consistency only. No network authority. */
import fs from 'node:fs';
import crypto from 'node:crypto';
const filename=new URL('./W4C_TEST_REGISTRY_VECTORS.json',import.meta.url);
const data=JSON.parse(fs.readFileSync(filename,'utf8'));
if(data.version!=='ARIO-W4C-REGISTRY-VIEW-SHAPE-TEST-ONLY-V0.1')throw Error('UNKNOWN_VECTOR_VERSION');
if(!Array.isArray(data.cases)||data.cases.length!==5)throw Error('VECTOR_COUNT');
const map=new Map();
for(const row of data.cases){
 const payload=JSON.stringify(row.declared_snapshot_array);
 if(!/^[\x00-\x7F]*$/.test(payload))throw Error('NON_ASCII_VECTOR');
 const hex=crypto.createHash('sha256').update(Buffer.from(payload,'ascii')).digest('hex');
 if(hex!==row.sha256_of_minimal_ascii_json)throw Error('DIGEST_DRIFT:'+row.name);
 map.set(row.name,hex);
 const corrupted=structuredClone(row.declared_snapshot_array);
 corrupted[1] = 'ATTACKER-ROOT-CHANGED';
 const changed=crypto.createHash('sha256').update(Buffer.from(JSON.stringify(corrupted),'ascii')).digest('hex');
 if(changed===hex)throw Error('MUTATION_NOT_DETECTED');
}
if(map.get('TWO_DISTINCT_DECLARATIONS')===map.get('FROZEN'))throw Error('FREEZE_NOT_BOUND');
if(map.get('TWO_DISTINCT_DECLARATIONS')===map.get('REORDERED_RECORDS'))throw Error('ORDER_NOT_BOUND');
console.log('W4C Node.js view-shape vectors: 5/5 PASS; mutation and state/order distinctions PASS');
console.log('NO_VERIFIED_TRUST=TRUE; NO_CONSENSUS_OR_ADMISSION=TRUE');
