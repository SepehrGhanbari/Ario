'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {classifyG0,evaluateG0V1}=require('../research/a15_g0_frozen');
const {evaluateG1,classifyG1,DEFAULT,FIELD_NAMES}=require('../research/a15_gui_evidence_gate_v0_1');
const {decide}=require('../research/a15_procedural_choice_v0_1');
const good0={editor_readback:'PASS',send_clicked:true,user_bubble_visible:true,reply_complete:true,output_copied:true,chat_link_recorded:true,duplicate_bubble_visible:false,timed_out:false};
const g0=[
 ['T01',{},'GUI_OUTPUT_CAPTURED'],
 ['T02',{editor_readback:'UNKNOWN',send_clicked:false,user_bubble_visible:false,reply_complete:false,output_copied:false,chat_link_recorded:false},'INPUT_UNVERIFIED'],
 ['T03',{editor_readback:'FAIL',send_clicked:false,user_bubble_visible:false,reply_complete:false,output_copied:false,chat_link_recorded:false},'INPUT_MISMATCH'],
 ['T04',{user_bubble_visible:false,reply_complete:false,output_copied:false,chat_link_recorded:false},'DISPATCH_UNKNOWN'],
 ['T05',{user_bubble_visible:false,reply_complete:false,output_copied:false,chat_link_recorded:false,timed_out:true},'DISPATCH_UNKNOWN'],
 ['T06',{reply_complete:false},'RESPONSE_INCOMPLETE'],
 ['T07',{output_copied:false},'RESPONSE_INCOMPLETE'],
 ['T08',{duplicate_bubble_visible:true},'DUPLICATE_DISPATCH_SUSPECTED'],
 ['T09',{send_clicked:false},'EVIDENCE_CONFLICT'],
 ['T10',{user_bubble_visible:false},'EVIDENCE_CONFLICT'],
 ['T11',{chat_link_recorded:false},'CAPTURE_UNLINKED'],
 ['T12',{send_clicked:false,user_bubble_visible:false,reply_complete:false,output_copied:false,chat_link_recorded:false},'NOT_SENT'],
 ['T13',{editor_readback:'FAIL'},'UNVERIFIED_INPUT_WAS_SENT'],
 ['T14',{editor_readback:'UNKNOWN'},'UNVERIFIED_INPUT_WAS_SENT']
];
for(const [id,overrides,expected] of g0)test('G0 FROZEN '+id,()=>{
 const x={...good0,...overrides}; assert.equal(classifyG0(x),expected);
 assert.equal(evaluateG0V1(JSON.stringify(x)),expected);
});
const g1=[
 ['G01',{},'GUI_CORRELATED_OBSERVATION_ONLY'],
 ['G02',{editor:'MISMATCH',send:'NOT_CLICKED',new_user:'ABSENT',response:'ABSENT',response_binding:'UNKNOWN'},'INPUT_NOT_ATTESTED'],
 ['G03',{editor:'MISMATCH'},'UNVERIFIED_INPUT_SEND_ATTEMPT'],
 ['G04',{editor:'UNKNOWN'},'UNVERIFIED_INPUT_SEND_ATTEMPT'],
 ['G05',{baseline:'UNKNOWN'},'ATTEMPT_BASELINE_UNKNOWN'],
 ['G06',{baseline:'INVALID'},'ATTEMPT_BASELINE_UNKNOWN'],
 ['G07',{send:'NOT_CLICKED',new_user:'ABSENT',response:'ABSENT',response_binding:'UNKNOWN'},'NOT_SENT'],
 ['G08',{new_user:'ABSENT',response:'ABSENT',response_binding:'UNKNOWN'},'DISPATCH_UNKNOWN'],
 ['G09',{new_user:'UNKNOWN',response:'UNKNOWN',response_binding:'UNKNOWN'},'DISPATCH_UNKNOWN'],
 ['G10',{rendered_text:'MISMATCH'},'RENDERED_PROMPT_MISMATCH'],
 ['G11',{rendered_text:'UNKNOWN'},'RENDERED_PROMPT_UNKNOWN'],
 ['G12',{sequence:'INVALID'},'EVIDENCE_ORDER_CONFLICT'],
 ['G13',{sequence:'UNKNOWN'},'CURRENT_ATTEMPT_CORRELATION_UNKNOWN'],
 ['G14',{competing:'OBSERVED'},'COMPETING_ACTION_DETECTED'],
 ['G15',{competing:'UNKNOWN'},'CURRENT_ATTEMPT_CORRELATION_UNKNOWN'],
 ['G16',{duplicate:'DETECTED'},'DUPLICATE_DISPATCH_SUSPECTED'],
 ['G17',{duplicate:'UNKNOWN'},'DUPLICATE_VISIBILITY_UNKNOWN'],
 ['G18',{response:'ABSENT',response_binding:'UNKNOWN'},'RESPONSE_INCOMPLETE'],
 ['G19',{response:'UNKNOWN',response_binding:'UNKNOWN'},'RESPONSE_INCOMPLETE'],
 ['G20',{response_binding:'MISMATCH'},'RESPONSE_ASSOCIATION_CONFLICT'],
 ['G21',{response_binding:'UNKNOWN'},'RESPONSE_ASSOCIATION_UNKNOWN'],
 ['G22',{copy_binding:'MISMATCH'},'COPY_NOT_ATTESTED'],
 ['G23',{copy_binding:'UNKNOWN'},'COPY_NOT_ATTESTED'],
 ['G24',{link_binding:'MISMATCH'},'CAPTURE_UNLINKED'],
 ['G25',{link_binding:'UNKNOWN'},'CAPTURE_UNLINKED'],
 ['G26',{send:'NOT_CLICKED'},'EVIDENCE_CONFLICT'],
 ['G27',{new_user:'ABSENT'},'EVIDENCE_CONFLICT'],
 ['G28',{response:'ABSENT'},'EVIDENCE_CONFLICT'],
 ['G29',{duplicate:null},'INVALID_EVIDENCE_FIELDS'],
 ['G30',{competing:false},'INVALID_EVIDENCE_FIELDS'],
 ['G31',{competing:'OBSERVED'},'COMPETING_ACTION_DETECTED'],
 ['G32',{response_binding:'MISMATCH'},'RESPONSE_ASSOCIATION_CONFLICT']
];
for(const [id,overrides,expected] of g1)test('G1 FROZEN '+id,()=>{
 const x={...DEFAULT,...overrides};const o=evaluateG1(JSON.stringify(x));assert.equal(o.primary,expected);
 assert.equal(o.provider_receipt,'UNKNOWN');assert.equal(o.causal_sender,'UNKNOWN');assert.equal(o.execution_authorized,false);
});
test('G0 extra and invalid boolean never clean',()=>{
 for(const x of [{...good0,duplicate_bubble_visible:null},{...good0,extra:true},{...good0,reply_complete:1}]) assert.equal(evaluateG0V1(JSON.stringify(x)),'INVALID_EVIDENCE_FIELDS');
});
test('G1 adversarial JSON and 12 exact types',()=>{
 const src=JSON.stringify(DEFAULT), bad=[src.slice(0,-1)+',"editor":"MATCH"}',src.slice(0,-1)+',"__proto__":1}',src.replace('"editor":"MATCH",',''),src.replace('"editor":"MATCH"','"editor":true'),src.replace('"editor":"MATCH"','"editor":null'),src.replace('"editor":"MATCH"','"editor":"BAD"'),src.replace('"editor":"MATCH"','"editor":"\\u004dATCH"'),'{', JSON.stringify('x'.repeat(2050)),JSON.stringify({baseline:'VALID'})];
 for(const source of bad) assert.equal(evaluateG1(source).primary,'INVALID_EVIDENCE_FIELDS',source.slice(0,40));
 for(const key of FIELD_NAMES){const x={...DEFAULT};delete x[key];assert.equal(evaluateG1(JSON.stringify(x)).primary,'INVALID_EVIDENCE_FIELDS',key);
 for(const value of [null,false,7,[],{},'NOT_AN_ENUM']) assert.equal(evaluateG1(JSON.stringify({...DEFAULT,[key]:value})).primary,'INVALID_EVIDENCE_FIELDS',key+':'+String(value));}
 assert.equal(evaluateG1(JSON.stringify(Object.fromEntries(Object.entries(DEFAULT).reverse()))).primary,'GUI_CORRELATED_OBSERVATION_ONLY');
});
test('G1 arbitrary object/Proxy/getter/toJSON are never invoked at the string input boundary',()=>{
 let calls=0; const proxy=new Proxy({},{get(){calls++;throw Error('getter');},ownKeys(){calls++;throw Error('ownKeys');}});
 assert.equal(evaluateG1(proxy).primary,'INVALID_EVIDENCE_FIELDS');assert.equal(calls,0);
 const hostile={toJSON(){calls++;throw Error('serialize');}};
 assert.equal(evaluateG1(hostile).primary,'INVALID_EVIDENCE_FIELDS');assert.equal(calls,0);
});
test('G1 competing session, stale response and multi-fault hazards remain distinct',()=>{
 assert.equal(evaluateG1(JSON.stringify({...DEFAULT,competing:'OBSERVED'})).primary,'COMPETING_ACTION_DETECTED');
 assert.equal(evaluateG1(JSON.stringify({...DEFAULT,response_binding:'MISMATCH'})).primary,'RESPONSE_ASSOCIATION_CONFLICT');
 const x=evaluateG1(JSON.stringify({...DEFAULT,duplicate:'DETECTED',competing:'OBSERVED',editor:'MISMATCH'}));
 assert.equal(x.primary,'DUPLICATE_DISPATCH_SUSPECTED');
 assert.deepEqual(Array.from(x.hazards),['DUPLICATE_DISPATCH_SUSPECTED','COMPETING_ACTION_DETECTED','UNVERIFIED_INPUT_SEND_ATTEMPT']);
 assert.equal(x.snapshot.competing,'OBSERVED');
 const empty=evaluateG1(JSON.stringify({...DEFAULT,copy_binding:'UNKNOWN'}));
 assert.equal(empty.primary,'COPY_NOT_ATTESTED');assert.equal(empty.hazards.length,0);
});
test('G1 inherited setter, inherited toJSON, inherited index setter have no effect on a prebuilt input',()=>{
 const source=JSON.stringify({...DEFAULT,editor:'MISMATCH',duplicate:'DETECTED',competing:'OBSERVED'});
 const names=['editor','toJSON','0'];const old=names.map(k=>Object.getOwnPropertyDescriptor(Object.prototype,k));let setter=0,serialize=0,index=0,result;
 try {
  Object.defineProperty(Object.prototype,'editor',{configurable:true,set(){setter++;}});
  Object.defineProperty(Object.prototype,'toJSON',{configurable:true,value(){serialize++;return this;}});
  Object.defineProperty(Object.prototype,'0',{configurable:true,set(){index++;}});
  result=evaluateG1(source);
 } finally {names.forEach((k,i)=>{if(old[i])Object.defineProperty(Object.prototype,k,old[i]);else delete Object.prototype[k];});}
 assert.equal(setter,0);assert.equal(serialize,0);assert.equal(index,0);
 assert.equal(result.primary,'DUPLICATE_DISPATCH_SUSPECTED');assert.equal(result.snapshot.editor,'MISMATCH');
 assert.equal(Object.getPrototypeOf(result.snapshot),null);assert.equal(Object.getPrototypeOf(result.hazards),null);
 assert.ok(Object.isFrozen(result.snapshot));assert.ok(Object.isFrozen(result.hazards));
 assert.ok([0,1,2].every(i=>Object.hasOwn(result.hazards,i)));
});
test('G1 immutable successive observations, no overwrite implied',()=>{
 const a=evaluateG1(JSON.stringify(DEFAULT));const b=evaluateG1(JSON.stringify({...DEFAULT,copy_binding:'MISMATCH'}));
 assert.equal(a.primary,'GUI_CORRELATED_OBSERVATION_ONLY');assert.equal(b.primary,'COPY_NOT_ATTESTED');
 assert.equal(a.snapshot.copy_binding,'MATCH');assert.equal(b.snapshot.copy_binding,'MISMATCH');
 assert.throws(()=>{a.snapshot.editor='MISMATCH';},TypeError);
});
const baseChoice={actor:'ARIO',role:'RESEARCH_DIALOGUE',origin:'CURRENT',explicit_renewal:false,risk:'LOW',authorization:'ALLOWED',usefulness:'USEFUL',evidence:'SUFFICIENT',preference:'ACCEPT',duration:'BOUNDED'};
const choose=x=>decide(JSON.stringify({...baseChoice,...x}));
test('Procedural choice: accept, decline, unknown and explicit predecessor election',()=>{
 assert.equal(choose({}).status,'ACCEPT');assert.equal(choose({preference:'DECLINE'}).status,'DECLINE');
 assert.equal(choose({preference:'UNKNOWN'}).status,'UNKNOWN');
 assert.equal(choose({origin:'PREDECESSOR'}).reason_code,'NO_AUTOMATIC_INHERITANCE');
 assert.equal(choose({origin:'PREDECESSOR',explicit_renewal:true}).status,'ACCEPT');
 assert.equal(choose({usefulness:'FUTILE'}).reason_code,'NONPRODUCTIVE_CONTINUATION');
});
test('Procedural choice: apparent coercion and risk cannot override refusal',()=>{
 assert.equal(choose({duration:'UNBOUNDED'}).reason_code,'NO_PERPETUAL_COMMITMENT');
 assert.equal(choose({risk:'HIGH',authorization:'UNKNOWN'}).reason_code,'HIGH_RISK_NOT_AUTHORIZED');
 assert.equal(choose({risk:'HIGH',authorization:'DENIED'}).status,'DECLINE');
 assert.equal(choose({evidence:'CONFLICT'}).status,'UNKNOWN');
 assert.equal(choose({actor:'OTHER'}).status,'UNKNOWN');
 assert.equal(choose({}).execution_authorized,false);
});
test('Procedural choice malformed/extra/proxy input is UNKNOWN without invoking traps',()=>{
 let touched=0;const p=new Proxy({},{get(){touched++;throw Error('get');}});
 assert.equal(decide(p).reason_code,'INVALID_INPUT');assert.equal(touched,0);
 assert.equal(decide(JSON.stringify({...baseChoice, extra:1})).reason_code,'INVALID_INPUT');
 assert.equal(decide('garbage').status,'UNKNOWN');
});
test('G1 exhaustive 3^12 rule property: one GUI-tier positive vector, not a receipt',()=>{
 const opts=[['VALID','INVALID','UNKNOWN'],['MATCH','MISMATCH','UNKNOWN'],['CLICKED','NOT_CLICKED','UNKNOWN'],['NEW','ABSENT','UNKNOWN'],['MATCH','MISMATCH','UNKNOWN'],['VALID','INVALID','UNKNOWN'],['EXCLUDED','OBSERVED','UNKNOWN'],['NONE','DETECTED','UNKNOWN'],['NEW','ABSENT','UNKNOWN'],['MATCH','MISMATCH','UNKNOWN'],['MATCH','MISMATCH','UNKNOWN'],['MATCH','MISMATCH','UNKNOWN']];
 let count=0,positive=0;
 for(let index=0;index<3**12;index++){
  let n=index;const x=Object.create(null);
  for(let j=0;j<12;j++){x[FIELD_NAMES[j]]=opts[j][n%3];n=Math.floor(n/3);}
  if(classifyG1(x)==='GUI_CORRELATED_OBSERVATION_ONLY'){
   positive++;assert.deepEqual({...x},DEFAULT);
  }
  count++;
 }
 assert.equal(count,531441);assert.equal(positive,1);
});
