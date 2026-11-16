#!/usr/bin/env python3
"""Compare a generated file with the immutable Git blob, not checkout bytes."""
import argparse,pathlib,subprocess,sys
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--ref",required=True);ap.add_argument("--committed-path",required=True);ap.add_argument("--generated",required=True);a=ap.parse_args()
 expected=subprocess.check_output(["git","cat-file","blob",f"{a.ref}:{a.committed_path}"])
 actual=pathlib.Path(a.generated).read_bytes()
 if actual!=expected:
  print(f"BYTE_MISMATCH: generated file differs from Git blob {a.ref}:{a.committed_path}",file=sys.stderr);return 1
 print(f"GIT_BLOB_REPRODUCIBLE: {a.committed_path} ({len(actual)} bytes)")
 return 0
if __name__=="__main__":raise SystemExit(main())
