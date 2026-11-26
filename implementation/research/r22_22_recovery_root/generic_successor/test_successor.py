import base64,io,json,sys,tempfile,zipfile
from pathlib import Path
from coincurve import PrivateKey
import successor as s
import event_codec as f

def expect(name,fn,valid):
    try: fn();good=True
    except (ValueError,TypeError,KeyError,zipfile.BadZipFile,OSError): good=False
    assert good==valid,(name,good,valid)
    print(name,'PASS',flush=True)

def test(a,b,v):
    old,op,_=s.bundle(a,True);new,np,_=s.bundle(b)
    result=s.evaluate(a,b,v);assert result['result']=='HOLD_LIVE_CONSISTENCY_NOT_RUN' and result['new_seq']>result['old_seq'];print('01_real_archived_proofs_and_link PASS')
    expect('02_old_replay',lambda:s.link(old,old,s.NOSTR),False)
    expect('03_reverse',lambda:s.link(new,old,s.NOSTR),False)
    d=json.loads(new);d['sig']=('0' if d['sig'][0]!='0' else '1')+d['sig'][1:]
    expect('04_bad_nostr_sig',lambda:s.link(old,f.canonical(d),s.NOSTR),False)
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'candidate.zip'
        def write(ev,proof):
            with zipfile.ZipFile(p,'w') as z:z.writestr('historical-second.json',ev);z.writestr('historical-second.proof',proof)
        write(new,op);expect('05_old_proof_substitution',lambda:s.evaluate(a,p,v),False)
        proof=np.replace(b'node_hash=',b'node_hash=0',1);write(new,proof);expect('06_tampered_merkle',lambda:s.evaluate(a,p,v),False)
        write(new,np);expect('07_repacked_unpinned_candidate',lambda:s.evaluate(a,p,v),True)
    # Separate local synthetic signer; no publication and no external proof for these cases.
    key=PrivateKey();pub=key.public_key_xonly.format().hex()
    _,x,ledger,_=f.verify_event(json.loads(new),s.NOSTR)
    ar=f.make_envelope(x['scope'],x['seq'],ledger,x['prior_checkpoint_sha256'],x['prior_ledger_sha256'],x['previous_checksum'],x['previous_event_id'],x['previous_ledger_sha256'])
    ae=f.make_event(ar,ledger,key);a_raw=f.canonical(ae)
    def extension(n,prev=None):
        raw=ledger;previous=f.parse_ledger(raw)[-1]['sha256']
        for i in range(x['seq'],n):
            row={'record_id':f'ROW-{i}','observed_at':'LAB','payload':{'test':str(i)},'previous_sha256':previous}
            row['sha256']=f.sha(json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii'));previous=row['sha256'];raw+=f.canonical(row)
        return raw
    def candidate(n,**changes):
        raw=extension(n);env=json.loads(f.make_envelope(x['scope'],n,raw,x['prior_checkpoint_sha256'],x['prior_ledger_sha256'],f.checksum(ar),ae['id'],f.sha(ledger)));env.update(changes)
        er=f.canonical(env)
        event={"pubkey":pub,"created_at":0,"kind":1,"tags":[["t",f.TOPIC],["x",f.checksum(er)]],"content":f.PREFIX+base64.b64encode(er).decode()+"."+base64.b64encode(raw).decode()}
        event["id"]=f.nostr_event_id(event);event["sig"]=key.sign_schnorr(bytes.fromhex(event["id"])).hex()
        return f.canonical(event)
    expect('08_synthetic_8_to_10_semantics',lambda:s.link(a_raw,candidate(10),pub),True)
    expect('09_synthetic_8_to_11_semantics',lambda:s.link(a_raw,candidate(11),pub),True)
    expect('10_wrong_predecessor',lambda:s.link(a_raw,candidate(10,previous_event_id='0'*64),pub),False)
    expect('11_wrong_scope',lambda:s.link(a_raw,candidate(10,scope='0'*48),pub),False)
    expect('12_wrong_previous_ledger',lambda:s.link(a_raw,candidate(10,previous_ledger_sha256='0'*64),pub),False)
    expect('13_wrong_previous_envelope',lambda:s.link(a_raw,candidate(10,previous_checksum='0'*64),pub),False)
    expect('14_wrong_prior_anchor',lambda:s.link(a_raw,candidate(10,prior_checkpoint_sha256='0'*64),pub),False)
    expect('15_wrong_signer',lambda:s.link(a_raw,candidate(10),s.NOSTR),False)
    expect('16_no_authority',lambda:s.link(a_raw,candidate(10,authoritative=True),pub),False)
    print('16/16 EXPECTED CONTROLS PASS; SYNTHETIC_8_TO_10_SEMANTICS_ONLY; NO_ADMISSION')
if __name__=='__main__':test(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]).resolve())
