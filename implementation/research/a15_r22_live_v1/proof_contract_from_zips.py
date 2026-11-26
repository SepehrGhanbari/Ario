#!/usr/bin/env python3
"""Verify and safely unpack exact retained A15 workflow artifact ZIPs."""
from __future__ import annotations
import argparse, hashlib, io, stat, sys, tempfile, zipfile
from pathlib import Path, PurePosixPath

EXPECTED = {
 "first":("f6012b78741a23992be901141fb8eb560f7010d17ecc4ccf4e71d3f917cd5f97",{
  "checkpoint.json","bootstrap.json","event-id.txt.proof","event-id.txt","event.json","log-key.pub","nostr.pub","sigsum.pub"}),
 "second":("4eec66aeb8036e9628094acbe815c7418e88836d064b384dcd0558ed4910f3ec",{
  "checkpoint.json","event-id.txt.proof","event-id.txt","event.json","matched-state/custodian.floor.json",
  "matched-state/custodian.sqlite3","rollback-state/custodian.floor.json","rollback-state/custodian.sqlite3"}),
}
def unpack(label, archive, dest):
    expected_sha, expected_names=EXPECTED[label]; raw=archive.read_bytes()
    if not 0<len(raw)<=1024*1024 or hashlib.sha256(raw).hexdigest()!=expected_sha: raise ValueError("HOLD_ARCHIVE_PIN_"+label.upper())
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if z.testzip() is not None: raise ValueError("HOLD_ARCHIVE_CRC")
        infos=z.infolist(); names=[x.filename for x in infos if not x.is_dir()]
        if len(infos)>32 or len(names)!=len(set(names)) or set(names)!=expected_names: raise ValueError("HOLD_ARCHIVE_MANIFEST")
        total=0
        for info in infos:
            member=PurePosixPath(info.filename)
            if member.is_absolute() or not member.parts or any(x in ("",".","..") for x in member.parts): raise ValueError("HOLD_ARCHIVE_PATH")
            if stat.S_ISLNK((info.external_attr>>16)&0xffff): raise ValueError("HOLD_ARCHIVE_SYMLINK")
            total+=info.file_size
            if total>128*1024: raise ValueError("HOLD_ARCHIVE_EXPANSION")
            target=dest.joinpath(*member.parts)
            if info.is_dir(): target.mkdir(parents=True,exist_ok=True)
            else:
                target.parent.mkdir(parents=True,exist_ok=True); data=z.read(info)
                if len(data)!=info.file_size: raise ValueError("HOLD_ARCHIVE_MEMBER_SIZE")
                target.write_bytes(data)
    print("PINNED_ARTIFACT_"+label.upper()+" PASS "+expected_sha,flush=True)
    return dest
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first-zip",type=Path,required=True); p.add_argument("--second-zip",type=Path,required=True)
    p.add_argument("--r22-codec",type=Path,required=True); p.add_argument("--r22-pure-verifier",type=Path,required=True)
    p.add_argument("--sigsum-verify",type=Path,required=True); a=p.parse_args()
    proof=Path(__file__).with_name("proof_contract.py")
    with tempfile.TemporaryDirectory(prefix="a15-r22-compat-fixtures-") as n:
        root=Path(n); first=unpack("first",a.first_zip,root/"first"); second=unpack("second",a.second_zip,root/"second")
        sys.argv=[str(proof),"--first",str(first),"--second",str(second),"--r22-codec",str(a.r22_codec),
                  "--r22-pure-verifier",str(a.r22_pure_verifier),"--sigsum-verify",str(a.sigsum_verify)]
        import importlib.util
        spec=importlib.util.spec_from_file_location("a15_r22_proof_contract",proof)
        if spec is None or spec.loader is None: raise RuntimeError("HOLD_PROOF_CONTRACT_LOAD")
        module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module); module.main()
if __name__=="__main__":
    try: main()
    except (OSError,ValueError,TypeError,zipfile.BadZipFile):
        print('{"schema":"ARIO_A15_R22_PROOF_ENVELOPE_COMPATIBILITY_V1","status":"HOLD_PINNED_ARTIFACT_INPUT"}')
        raise SystemExit(2)
