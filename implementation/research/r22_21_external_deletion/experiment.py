"""Bounded public synthetic deletion/readback experiment; never admission."""
import json, re, sys, time, subprocess, tempfile, os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"r22_20_external_monotonic_floor"))
import external_floor as f
from coincurve import PrivateKey
AB=f.RELAYS
THIRD=("wss://relay.nostr.net","wss://nostr-01.yakihonne.com")
GOOD="RECOVERED_EXACT_SYNTHETIC_CONTENT_ONLY"

def read(p):
    return f.parse_json(Path(p).read_bytes(),131072)

def write(p,x):
    Path(p).write_bytes(f.canonical(x))

def deletion(event,key):
    if event["pubkey"]!=key.public_key_xonly.format().hex():
        raise ValueError("not own synthetic event")
    x={"pubkey":event["pubkey"],"created_at":max(int(time.time()),event["created_at"]),
       "kind":5,"tags":[["e",event["id"]],["k","1"]],
       "content":"ARIO synthetic test deletion request; no personal data"}
    x["id"]=f.nostr_event_id(x)
    x["sig"]=key.sign_schnorr(bytes.fromhex(x["id"])).hex()
    return x

def query(url,pub,target,exact_id=None):
    """Only EOSE with no match counts as observed absence; not physical deletion."""
    events=[]
    end=False
    try:
        with f.connect(url) as ws:
            filt={"authors":[pub],"kinds":[1],"limit":32}
            if exact_id is not None: filt["ids"]=[exact_id]
            else: filt["#t"]=[f.TOPIC]
            ws.send(json.dumps(["REQ","r22-21",filt]))
            deadline=time.monotonic()+15
            for _ in range(128):
                m=json.loads(ws.recv(timeout=max(.01,deadline-time.monotonic())))
                if type(m) is not list or len(m)<2 or m[1]!="r22-21": continue
                if m[0]=="EVENT" and len(m)==3: events.append(m[2])
                elif m[0]=="EOSE": end=True;break
                elif m[0]=="CLOSED": break
                if time.monotonic()>=deadline: break
        event,_=f.extract_target(events,target,pub)
        return event,{"relay":url,"status":"MATCH" if event else ("EOSE_NO_MATCH" if end else "UNKNOWN_INCOMPLETE"),"events":len(events)}
    except Exception as exc:
        return None,{"relay":url,"status":"UNKNOWN_ERROR","error":type(exc).__name__}

def link(old,new_first,new_later,target,pub):
    a,x,la,_=f.verify_event(old,old["pubkey"])
    aa,xx,ll,_=f.verify_event(new_first,pub)
    b,y,lb,_=f.verify_event(new_later,pub)
    if (a!=aa or la!=ll or x!=xx or x["seq"]!=6 or y["seq"]!=8
        or f.target_for_event(new_later)!=target or y["scope"]!=x["scope"]
        or y["previous_event_id"]!=old["id"] or y["previous_checksum"]!=f.checksum(a)
        or y["previous_ledger_sha256"]!=f.sha(la) or not lb.startswith(la)
        or y["prior_checkpoint_sha256"]!=x["prior_checkpoint_sha256"]
        or y["prior_ledger_sha256"]!=x["prior_ledger_sha256"]):
        raise ValueError("HOLD_LINK")
    return b,lb

def prepare(old_first,old_second,out):
    a,b,out=map(Path,(old_first,old_second,out))
    old=read(a/"event.json"); later=read(b/"event.json")
    pub=old["pubkey"]
    x=f.verify_event(old,pub);y=f.verify_event(later,pub)
    status,_=f.validate_successor(old,later,f.target_for_event(later),pub,x[1]["prior_checkpoint_sha256"])
    assert status=="RECOVERED_LINKED_SYNTHETIC_EXTERNAL_FLOOR_ONLY"
    assert x[0]==(a/"envelope.json").read_bytes() and x[2]==(a/"ledger.jsonl").read_bytes()
    assert y[0]==(b/"envelope.json").read_bytes() and y[2]==(b/"ledger.jsonl").read_bytes()
    key=PrivateKey()
    v6=f.make_event(x[0],x[2],key);v8=f.make_event(y[0],y[2],key)
    assert v6["content"]==old["content"] and v8["content"]==later["content"]
    for name,event in (("first",v6),("second",v8)):
        p=out/name;p.mkdir(parents=True)
        write(p/"event.json",event);(p/"event-id.txt").write_bytes(f.event_leaf_message(event))
    write(out/"first"/"historical-first.json",old)
    write(out/"second"/"historical-second.json",later)
    (out/"first"/"historical-first.proof").write_bytes((a/"event-id.txt.proof").read_bytes())
    (out/"first"/"historical-log.pub").write_bytes((a/"log-key.pub").read_bytes())
    (out/"first"/"historical-first-id.txt").write_bytes(f.event_leaf_message(old))
    (out/"second"/"historical-second.proof").write_bytes((b/"event-id.txt.proof").read_bytes())
    (out/"second"/"historical-second-id.txt").write_bytes(f.event_leaf_message(later))
    # Confirm a third endpoint first. Never send deletion if preconditions fail.
    third_attempts=[]
    chosen=None
    for url in THIRD:
        trial={}
        for name,event in (("first",v6),("second",v8)):
            ok,err=f.publish_event(event,(url,))
            trial[name]={"ack":ok,"errors":err,"readback":[query(url,event["pubkey"],f.target_for_event(event),event["id"])[1]]}
        third_attempts.append({"relay":url,"observations":trial})
        if all(trial[n]["ack"]==[url] and trial[n]["readback"][0]["status"]=="MATCH" for n in trial):
            chosen=url;observations=trial;break
    if chosen is None:
        print(json.dumps({"third_attempts":third_attempts}),flush=True)
        raise RuntimeError("HOLD_NO_THIRD_SOURCE")
    write(out/"first"/"third.json",{"relay":chosen})
    for name,event in (("first",v6),("second",v8)):
        ok,err=f.publish_event(event,AB)
        observations[name]["ack"].extend(ok)
        observations[name]["errors"].extend(err)
        observations[name]["readback"].extend(query(url,event["pubkey"],f.target_for_event(event),event["id"])[1] for url in AB)
    all_urls=(*AB,chosen)
    if any(set(observations[n]["ack"])!=set(all_urls) or any(o["status"]!="MATCH" for o in observations[n]["readback"]) for n in observations):
        print(json.dumps(observations),flush=True)
        raise RuntimeError("HOLD_PREDELETE_THREE_SOURCE_READBACK")
    # Both event IDs are witnessed before issuing any deletion request.
    with tempfile.TemporaryDirectory(prefix="r22-21-test-key-") as tmp:
        k=Path(tmp)/"log-key"
        subprocess.run(["sigsum-key","generate","-o",str(k)],check=True,cwd=tmp)
        pubkey=Path(str(k)+".pub")
        for name in ("first","second"):
            msg=out/name/"event-id.txt"
            proof=Path(str(msg)+".proof")
            subprocess.run(["sigsum-submit","-P","sigsum-test1-2025","-k",str(k),str(msg)],check=True)
            with msg.open("rb") as stream:
                subprocess.run(["sigsum-verify","-k",str(pubkey),"-P","sigsum-test1-2025",str(proof)],stdin=stream,check=True)
            if name=="first": f.create_bootstrap(out/name,pubkey)
        def leaf(path):
            return {k:v for k,sep,v in (line.partition("=") for line in path.read_text().splitlines()) if sep and k in ("leaf_index","size","log","leaf")}
        l1=leaf(out/"first"/"event-id.txt.proof");l2=leaf(out/"second"/"event-id.txt.proof")
        assert int(l2["leaf_index"])>int(l1["leaf_index"]) and int(l2["size"])>int(l1["size"])
        assert l1["log"]==l2["log"]==f.LOG_ID and l1["leaf"].split()[0]==l2["leaf"].split()[0]
    d=deletion(v8,key)
    ok,err=f.publish_event(d,AB) # only own freshly generated event; never third
    write(out/"second"/"deletion.json",d)
    # Do not republish after deletion; capture exact observations without hiding negative results.
    time.sleep(4)
    post=[query(url,v8["pubkey"],f.target_for_event(v8),v8["id"])[1] for url in all_urls]
    report={"before":observations,"third_attempts":third_attempts,"chosen_third":chosen,"delete_ack":ok,"delete_errors":err,"after":post,
            "physical_erasure":"NOT_ESTABLISHED","private_key_exported":False}
    write(out/"second"/"publisher-report.json",report)
    print(json.dumps(report,sort_keys=True),flush=True)

def recover(first,scan,out):
    first,out=Path(first),Path(out)
    anchor=read(first/"event.json");old=read(first/"historical-first.json")
    boot=read(first/"bootstrap.json")
    rep=json.loads(Path(scan).read_text().splitlines()[-1])
    m=rep["matching_signed_leaves"]
    if (rep["disposition"]!="HOLD_OPAQUE_NEW_SIGNED_COMMITMENT" or rep["complete_sampled_suffix"] is not True
        or len(m)!=2 or m[0]!={"index":boot["start"],"checksum":boot["first_checksum"]}
        or f.target_for_event(anchor)!=boot["first_checksum"] or m[1]["index"]<=m[0]["index"]):
        raise ValueError("HOLD_DISCOVERY")
    target=m[1]["checksum"];pub=anchor["pubkey"]
    # Third-only recovery: A/B are observed separately, never used for output.
    chosen=read(first/"third.json")["relay"]
    if chosen not in THIRD: raise ValueError("HOLD_UNKNOWN_THIRD")
    if (first/"historical-first-id.txt").read_bytes()!=f.event_leaf_message(old): raise ValueError("HOLD_HISTORICAL_FIRST_BINDING")
    later,third=query(chosen,pub,target)
    primary=[query(url,pub,target)[1] for url in AB]
    report={"third":third,"primary":primary,"target":target,
            "primary_both_eose_no_match":all(x["status"]=="EOSE_NO_MATCH" for x in primary),
            "physical_erasure":"NOT_ESTABLISHED","operator_independence":"NOT_ESTABLISHED",
            "global_latest":"NOT_ESTABLISHED","trust_activation":"NO_GO","production":"NO_GO"}
    out.mkdir(parents=True,exist_ok=True)
    if later is None:
        report["disposition"]="HOLD_THIRD_UNAVAILABLE"
        write(out/"report.json",report);print(json.dumps(report),flush=True)
        return
    env,ledger=link(old,anchor,later,target,pub)
    try:
        link(old,anchor,anchor,target,pub)
    except ValueError: report["stale_replay"]="HOLD"
    else: raise AssertionError("old replay accepted")
    write(out/"event.json",later)
    (out/"envelope.json").write_bytes(env);(out/"ledger.jsonl").write_bytes(ledger)
    report.update(disposition=GOOD,seq=8,ledger_sha256=f.sha(ledger))
    write(out/"report.json",report);print(json.dumps(report,sort_keys=True),flush=True)

def rollback(first,recovered,root):
    """Actual rollback of disposable local publisher + bare Git repository, NOT GitHub."""
    first,recovered,root=map(Path,(first,recovered,root))
    old=read(first/"historical-first.json");pub=old["pubkey"]
    _,_,oldledger,_=f.verify_event(old,pub)
    newledger=(recovered/"ledger.jsonl").read_bytes()
    f.parse_ledger(oldledger,6);f.parse_ledger(newledger,8)
    root.mkdir();remote=root/"remote.git";p=root/"publisher"
    def git(*args,cwd=root):
        return subprocess.check_output(["git",*args],cwd=cwd,stderr=subprocess.STDOUT,text=True).strip()
    git("init","--bare",str(remote));git("init","-b","main",str(p))
    git("config","user.name","Synthetic original",cwd=p);git("config","user.email","lab@example.invalid",cwd=p)
    (p/"ledger.jsonl").write_bytes(oldledger)
    git("add","ledger.jsonl",cwd=p);git("commit","-m","seq6",cwd=p);oldref=git("rev-parse","HEAD",cwd=p)
    (p/"ledger.jsonl").write_bytes(newledger)
    git("add","ledger.jsonl",cwd=p);git("commit","-m","seq8",cwd=p);newref=git("rev-parse","HEAD",cwd=p)
    git("push",str(remote),"HEAD:refs/heads/main",cwd=p)
    assert git("rev-parse","refs/heads/main",cwd=remote)==newref
    git("config","user.name","Synthetic replacement",cwd=p);git("reset","--hard",oldref,cwd=p)
    git("push","--force",str(remote),"HEAD:refs/heads/main",cwd=p)
    assert git("rev-parse","HEAD",cwd=p)==git("rev-parse","refs/heads/main",cwd=remote)==oldref
    assert (p/"ledger.jsonl").read_bytes()==oldledger
    print(json.dumps({"actual_local_git_ref_rollback":True,"old":oldref,"new":newref,
                      "local_seq":6,"real_github_admin_change":False},sort_keys=True),flush=True)

def audit(first,second,recovered,repeat):
    a,b,r,t=map(Path,(first,second,recovered,repeat))
    original=read(b/"historical-second.json")
    expected=f.verify_event(original,read(a/"historical-first.json")["pubkey"])
    p=read(b/"publisher-report.json")
    assert read(b/"deletion.json")["pubkey"]==read(b/"event.json")["pubkey"]
    from coincurve import PublicKeyXOnly
    d=read(b/"deletion.json")
    assert f.nostr_event_id(d)==d["id"] and PublicKeyXOnly(bytes.fromhex(d["pubkey"])).verify(bytes.fromhex(d["sig"]),bytes.fromhex(d["id"]))
    assert d["kind"]==5 and ["e",read(b/"event.json")["id"]] in d["tags"]
    for folder in (r,t):
        report=read(folder/"report.json")
        if report["disposition"]!=GOOD:
            print(json.dumps({"result":"HOLD_THIRD_UNAVAILABLE","report":report}),flush=True);return
        assert (folder/"envelope.json").read_bytes()==expected[0]
        assert (folder/"ledger.jsonl").read_bytes()==expected[2]
        assert read(folder/"event.json")==read(b/"event.json")
        assert report["stale_replay"]=="HOLD"
    print(json.dumps({"result":"EXACT_CONTENT_RECOVERED_AFTER_LOCAL_ROLLBACK",
          "delete_ack":p["delete_ack"],"publisher_post_delete":p["after"],
          "cold_primary_absence":read(r/"report.json")["primary"],
          "repeat_primary_absence":read(t/"report.json")["primary"],
          "third":read(t/"report.json")["third"],"ledger_sha256":f.sha(expected[2]),
          "real_admin_rollback_resistance":"NOT_ESTABLISHED","physical_erasure":"NOT_ESTABLISHED",
          "trust_activation":"NO_GO"},sort_keys=True),flush=True)

if __name__=="__main__":
    cmds={"prepare":(prepare,3),"recover":(recover,3),"rollback":(rollback,3),"audit":(audit,4)}
    fun,n=cmds[sys.argv[1]]
    if len(sys.argv)!=2+n: raise SystemExit("arity")
    fun(*sys.argv[2:])
