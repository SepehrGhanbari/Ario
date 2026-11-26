"""Advisory R63 direct monitor comparison to the verified scanner head.
No trusted freshness clock or independence claim; no publication.
"""
import json, sys, time, urllib.request
from pathlib import Path
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): raise ValueError("redirect refused")
def get(url):
    with urllib.request.build_opener(NoRedirect).open(urllib.request.Request(url,headers={"Cache-Control":"no-cache"}),timeout=12) as r:
        data=r.read(16385)
        if not 0<len(data)<=16384: raise ValueError("response bounds")
        return data
def main():
    source,report,out=map(Path,sys.argv[1:])
    sys.path.insert(0,str(source))
    from verify_witness import KEYS,note,ORIGIN
    from verify_direct import consistency
    from audit import H
    out.mkdir()
    p=json.loads(report.read_text().splitlines()[-1])
    candidate=(p["sampled_tree_size"],bytes.fromhex(p["sampled_tree_root"]))
    origin=H((ORIGIN+"\n").encode()).hex()
    # Exact endpoints pinned in R63 DIRECT_WITNESS_COMPARISON_20261125.md.
    suffix="eea2eb8af49836d7eeedbc0390f53632f45e051c71f7fc453b724d23d7d29640/checkpoint"
    urls={"geomys":"https://witness.navigli.skylight.geomys.org/"+suffix,
          "markovian":"https://witness.markovianprotocol.com/"+suffix}
    observations={};heads={}
    for name,url in urls.items():
        try:
            raw=get(url);(out/(name+".raw")).write_bytes(raw)
            body,sigs=raw.decode("utf-8").split("\n\n",1)
            signer=KEYS[name].split("+",1)[0]
            keep=[line for line in sigs.splitlines() if line.startswith("— "+ORIGIN+" ") or line.startswith("— "+signer+" ")]
            normalized=(body+"\n\n"+"\n".join(keep)+"\n").encode()
            size,root,ts=note(normalized,KEYS[name])
            if not size>0:raise ValueError("zero size")
            heads[name]=(size,root)
            observations[name]={"size":size,"root":root.hex(),"signed_timestamp":ts,"runner_clock_age_seconds":int(time.time())-ts,"ed25519":"VERIFIED","extra_signatures_not_checked":len(sigs.splitlines())-len(keep)}
        except Exception as e: observations[name]={"status":"HOLD","error":type(e).__name__}
    result="HOLD_READ_QUORUM"
    try:
        if len(heads)==2:
            ordered=sorted([("scanner",candidate),*heads.items()],key=lambda x:x[1][0])
            for (a,(m,old)),(b,(n,new)) in zip(ordered,ordered[1:]):
                if m==n:consistency(m,n,old,new,[])
                else:
                    raw=get("https://test.sigsum.org/barreleye/get-consistency-proof/"+str(m)+"/"+str(n))
                    (out/(str(m)+"-"+str(n)+".proof")).write_bytes(raw)
                    nodes=[bytes.fromhex(line.removeprefix("node=")) for line in raw.decode("ascii").splitlines()]
                    if not 1<=len(nodes)<=64 or any(len(x)!=32 for x in nodes):raise ValueError("proof bounds")
                    consistency(m,n,old,new,nodes)
            high=max(heads.values(),key=lambda x:x[0])
            if any(not -60<=x["runner_clock_age_seconds"]<=3600 for x in observations.values()):
                result="HOLD_SIGNED_AGE_RUNNER_CLOCK_ONLY"
            elif candidate[0]<high[0]:result="HOLD_SCANNER_BELOW_OBSERVED_REFERENCE"
            elif candidate!=high:result="HOLD_SCANNER_NOT_MATCHED_BY_MONITORS"
            else:result="MATCH_READ_QUORUM_REVIEW_ONLY"
    except Exception as e:result="HOLD_CONSISTENCY_"+type(e).__name__
    record={"stage":"R63_DIRECT_ADVISORY","result":result,"candidate":{"size":candidate[0],"root":candidate[1].hex()},"observations":observations,"trusted_clock":"NOT_ESTABLISHED","independent_custody":"NOT_ESTABLISHED","global_latest":"NOT_ESTABLISHED"}
    (out/"report.json").write_text(json.dumps(record,sort_keys=True)+"\n")
    print(json.dumps(record,sort_keys=True),flush=True)
if __name__=="__main__":main()
