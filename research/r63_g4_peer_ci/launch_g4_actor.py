"""G4 research-only synthetic OS-token launcher; no key, privilege or policy changes."""
from __future__ import annotations
import os
import subprocess
import sys

def main(argv):
    if os.name != 'nt': raise RuntimeError('WINDOWS_ONLY')
    if len(argv) < 4: raise RuntimeError('INVALID_LAUNCHER_ARGUMENTS')
    exe, actor, *rest = argv
    if not exe.lower().endswith('\\powershell.exe') or not actor.endswith('Invoke-G4PipeActor.ps1'):
        raise RuntimeError('REFUSE_NON_G4_WINDOWS_ACTOR')
    result = subprocess.run([exe,'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
        '-File',actor,*rest],stdin=subprocess.DEVNULL,capture_output=True,timeout=55)
    sys.stdout.buffer.write(result.stdout)
    sys.stderr.buffer.write(result.stderr)
    return result.returncode

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
