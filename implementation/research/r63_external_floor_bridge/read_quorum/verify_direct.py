from audit import H, check

def consistency(m,n,old,new,nodes):
    check(0<m<=n,'sizes')
    if m==n:
        check(not nodes and old==new,'same size mismatch'); return
    fn,sn=m-1,n-1
    while fn&1: fn>>=1; sn>>=1
    if fn==0: fr=sr=old
    else: fr=sr=nodes[0]; nodes=nodes[1:]
    for node in nodes:
        check(sn>0,'extra consistency node')
        if fn&1 or fn==sn:
            fr=H(b'\x01'+node+fr); sr=H(b'\x01'+node+sr)
            while fn and not fn&1: fn>>=1; sn>>=1
        else: sr=H(b'\x01'+sr+node)
        fn>>=1; sn>>=1
    check(sn==0 and fr==old and sr==new,'consistency roots')
