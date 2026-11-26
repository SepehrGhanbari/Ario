import json, pathlib, subprocess, sys, tempfile, hashlib
p=pathlib.Path(__file__).parent
tool=p/'w1_blind_intake_and_score.py'
def call(*args):
    q=subprocess.run([sys.executable,'-B',str(tool),*map(str,args)], capture_output=True,text=True)
    return q.returncode,q.stdout,q.stderr
with tempfile.TemporaryDirectory() as d:
    base=pathlib.Path(d)
    x=[]
    y=[]
    o=[]
    for i,(true,adjud) in enumerate([(True,'AGREED'),(False,'AGREED'),(None,'DISPUTED')]):
        cid='case-'+str(i)
        x.append({'case_id':cid,'graph':{'origin':'LAB','nodes':[],'edges':[]},'scope':'scope','witness_artifact_refs':['A','B'],'complete_control_surface':True,'complete_source_surface':True,'completeness_origin':'LAB'})
        y.append({'case_id':cid,'admin_status':'LAB_CONDITIONALLY_SEPARATE' if i==1 else 'UNKNOWN','source_status':'LAB_CONDITIONALLY_DISTINCT' if i==0 else 'UNKNOWN','evaluator_blob_sha1':'a'*40,'runner_version':'synthetic-test'})
        o.append({'case_id':cid,'latent_admin_independent':true,'latent_source_independent':true,'adjudication':adjud,'labeler_a_ref':'lab-a','labeler_b_ref':'lab-b','rationale_ref':'private'})
    for name,rows in [('masked',x),('pred',y),('oracle',o)]:
        (base/(name+'.jsonl')).write_text(''.join(json.dumps(z)+'\n' for z in rows),encoding='utf-8')
    a=call('freeze','--kind','masked','--input',base/'masked.jsonl','--output',base/'masked.commit.json')
    b=call('freeze','--kind','predictions','--input',base/'pred.jsonl','--output',base/'pred.commit.json')
    c=call('score','--masked',base/'masked.jsonl','--masked-commit',base/'masked.commit.json','--predictions',base/'pred.jsonl','--predictions-commit',base/'pred.commit.json','--private-oracle',base/'oracle.jsonl','--output',base/'aggregate.json')
    assert a[0]==b[0]==c[0]==0,(a,b,c)
    agg=json.loads((base/'aggregate.json').read_text())
    assert agg['n_all']==3 and agg['n_agreed']==2,agg
    assert agg['axes']['admin']['conditional_on_dependent']==1,agg
    z=call('freeze','--kind','masked','--input',base/'oracle.jsonl','--output',base/'should_fail.commit.json')
    assert z[0]==2,z
    w=call('score','--masked',base/'masked.jsonl','--masked-commit',base/'masked.commit.json','--predictions',base/'pred.jsonl','--predictions-commit',base/'pred.commit.json','--private-oracle',base/'oracle.jsonl','--output',base/'aggregate.json')
    assert w[0]==2,w
    (base/'pred.jsonl').write_text((base/'pred.jsonl').read_text()+'\n')
    v=call('score','--masked',base/'masked.jsonl','--masked-commit',base/'masked.commit.json','--predictions',base/'pred.jsonl','--predictions-commit',base/'pred.commit.json','--private-oracle',base/'oracle.jsonl','--output',base/'changed.json')
    assert v[0]==2,v
    print('W1-B local smoke tests PASS: frozen masked, frozen predictions, scored 3 synthetic cases; oracle-as-masked rejected, overwrite rejected, modified prediction rejected')
