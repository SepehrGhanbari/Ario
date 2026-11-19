"""Read-only manifest-pack for a known disposable G3 evidence directory.

Not an externally authenticated record; SHA manifest travels inside ZIP.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import sys
import zipfile


def main(root: Path, out: Path):
    if not root.is_dir() or root.name != 'captured':
        raise RuntimeError('REFUSE_UNEXPECTED_SOURCE')
    if out.exists():
        raise RuntimeError('REFUSE_EXISTING_EVIDENCE_ZIP')
    files=sorted(x for x in root.rglob('*') if x.is_file())
    if len(files) > 100 or sum(p.stat().st_size for p in files)>2_000_000:
        raise RuntimeError('BOUNDED_EVIDENCE_LIMIT_EXCEEDED')
    lines=[]
    with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for f in files:
            rel=f.relative_to(root).as_posix()
            if '..' in Path(rel).parts or '\\' in rel:
                raise RuntimeError('UNSAFE_ENTRY')
            data=f.read_bytes()
            z.writestr(rel,data)
            lines.append(hashlib.sha256(data).hexdigest()+'  '+rel)
        z.writestr('SHA256SUMS.txt','\n'.join(lines)+'\n')
    with zipfile.ZipFile(out) as z:
        if z.testzip() is not None:
            raise RuntimeError('ZIP_CRC_ERROR')
    print('EVIDENCE_ZIP_MEMBERS='+str(len(files)+1))

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('usage: evidence_g3.py captured out.zip')
    main(Path(sys.argv[1]),Path(sys.argv[2]))
