'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {produce,verifyChain}=require('./bridge');
function lab(t){const d=fs.mkdtempSync(path.join(os.tmpdir(),'a15-r22-offline-'));t.after(()=>fs.rmSync(d,{recursive:true,force:true}));return d;}
// Offline structural transport fixtures only, explicitly NOT valid Sigsum proof material.
function fixture(n,obj){return {payload:JSON.stringify(obj),envelope:'OFFLINE-ENVELOPE-'+n,proof:n===3?null:'NOT-A-SIGSUM-PROOF-'+n};}
const clone=x=>structuredClone(x);
const mutate=(p,i,fn)=>{const c=clone(p),x=JSON.parse(c[i].payload);fn(x);c[i].payload=JSON.stringify(x);return c;};
test('valid local v0.7 flow and semantic links; offline proof fixtures only',t=>{const a=produce(lab(t),fixture);assert.equal(a.verify.status,'SEMANTIC_LINKS_VERIFIED_SYNTHETIC_ONLY');assert.equal(a.verify.independent_custody,'NOT_ESTABLISHED');});
test('missing external reservation receipt prevents first stage',t=>{const d=lab(t);assert.throws(()=>produce(d,()=>{throw Error('NO_TRANSPORT')}),/HOLD_BEGIN/);assert.ok(fs.existsSync(path.join(d,'lab/state/reserve-0001.json')));assert.ok(!fs.existsSync(path.join(d,'lab/state/stage-0001.json')));});
test('missing stage transport prevents finalization',t=>{const d=lab(t);assert.throws(()=>produce(d,(n,x)=>{if(n===2)throw Error('NO_TRANSPORT');return fixture(n,x)}),/HOLD_COMPLETE/);assert.ok(!fs.existsSync(path.join(d,'lab/state/final-0001.json')));});
test('missing final external publication is not a live success',t=>{assert.throws(()=>produce(lab(t),(n,x)=>{if(n===3)throw Error('NO_TRANSPORT');return fixture(n,x)}),/NO_TRANSPORT/);});
for(const [name,fn] of [
 ['missing phase',p=>p.slice(0,2)],['reordered phases',p=>[p[1],p[0],p[2]]],
 ['substituted first proof',p=>{p=clone(p);p[0].proof+='X';return p;}],
 ['substituted second proof',p=>{p=clone(p);p[1].proof+='X';return p;}],
 ['substituted first envelope',p=>{p=clone(p);p[0].envelope+='X';return p;}],
 ['wrong first link',p=>mutate(p,1,x=>x.r1.checksum='0'.repeat(64))],
 ['tampered outer signature',p=>mutate(p,1,x=>x.outer.signature='A'.repeat(86)+'==')],
 ['wrong reserve bytes',p=>mutate(p,0,x=>{const r=JSON.parse(x.reservation);r.challenge='a'.repeat(64);x.reservation=JSON.stringify(r)})],
 ['wrong stage',p=>mutate(p,1,x=>{const r=JSON.parse(x.stage);r.pre.signature='A'.repeat(86)+'==';x.stage=JSON.stringify(r)})],
 ['missing POST',p=>mutate(p,2,x=>{const r=JSON.parse(x.final);delete r.post;x.final=JSON.stringify(r)})],
 ['wrong POST',p=>mutate(p,2,x=>{const r=JSON.parse(x.final);r.post.signature='A'.repeat(86)+'==';x.final=JSON.stringify(r)})],
 ['wrong authority pin',p=>mutate(p,0,x=>x.pins.authoritySha256='0'.repeat(64))],
 ['replayed final as second',p=>[p[0],p[2],p[2]]]
])test(name,t=>{const p=produce(lab(t),fixture).phases;assert.throws(()=>verifyChain(fn(p)));});
