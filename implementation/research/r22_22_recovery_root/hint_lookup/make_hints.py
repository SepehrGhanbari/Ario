"""Create untrusted candidate hints from two archived public synthetic receipts.
No receipt proof path, leaf index, or head is supplied to verifier by index.
"""
import hashlib,json,sys,zipfile
from pathlib import Path
def hint(p,proof='event-id.txt.proof',message='event-id.txt'):
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        raw=z.read(message)
        fields=[s[5:].split() for s in z.read(proof).decode('ascii').splitlines() if s.startswith('leaf=')]
        assert len(fields)==1 and len(fields[0])==2
        k,s=fields[0]
        return dict(message_hex=raw.hex(),signature=s,key_hash=k)
first,second,out=map(Path,sys.argv[1:])
assert hashlib.sha256(first.read_bytes()).hexdigest()=='2bedc6d0cc85857cfaed3ceafeb5d7700d78923057e661d9c5675d6925e6262b'
assert hashlib.sha256(second.read_bytes()).hexdigest()=='717fbcf540cba37e7d5c6c83f3740fe301ece42fdc983fe4e9af484a37d56d27'
a,b=hint(first),hint(second)
foreign=hint(first,'historical-first.proof','historical-first-id.txt')
tamper=dict(b,signature=('0' if b['signature'][0]!='0' else '1')+b['signature'][1:])
out.write_text(json.dumps([a,b,tamper,foreign,b],sort_keys=True)+'\n')
