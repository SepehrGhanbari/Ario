"""R63 G4: bounded raw evidence ZIP; no code execution or remote calls."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import zipfile

EXPECTED=('report-before-cleanup.json','server-peer-log.txt','v1.jsonl','v2.jsonl')
def sha(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()
def pack(source:Path,dest:Path):
    if dest.exists():raise ValueError('REFUSE_EXISTING_OUTPUT')
    actual=tuple(sorted(x.name for x in source.iterdir() if x.is_file()))
    if actual!=EXPECTED:raise ValueError('MISSING_OR_UNEXPECTED_G4_EVIDENCE_CONTENT '+str(actual))
    payload={n:(source/n).read_bytes() for n in EXPECTED}
    if any(len(x)>1_000_000 for x in payload.values()): raise ValueError('EXCESSIVE_EVIDENCE_FILE')
    hashes=''.join(f'{sha(payload[n])}  {n}\n' for n in sorted(EXPECTED)).encode('ascii')
    with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n in sorted(payload):z.writestr(n,payload[n])
        z.writestr('SHA256SUMS.txt',hashes)
    with zipfile.ZipFile(dest) as z:
        if z.testzip() is not None: raise ValueError('BAD_ZIP_CRC')
        if set(z.namelist())!=set(EXPECTED)|{'SHA256SUMS.txt'}:raise ValueError('BAD_ZIP_LIST')
    print(f'G4_EVIDENCE_SHA256={sha(dest.read_bytes())}')
if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('USAGE: pack_g4_evidence.py <inputdir> <outputzip>')
    pack(Path(sys.argv[1]),Path(sys.argv[2]))
