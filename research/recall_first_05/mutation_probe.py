"""RF05 negative controls; edits only disposable source copies, never Ario/GitHub."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
SOURCE = (ROOT/'equivalence_read_view.py').read_text(encoding='utf-8')
TEST = (ROOT/'test_equivalence_read_view.py').read_text(encoding='utf-8')
RF01 = ROOT.parent / 'recall_first_01'
MUTANTS = {
    'bypass_semantic_contrast': (
        "contrast = semantic_contrast(selected['original_question'], selected['question'])",
        "contrast = None  # synthetic mutation"),
    'bypass_current_reassessment': (
        "intent = _mode(question, mode)",
        "intent = 'HISTORICAL'  # synthetic mutation"),
    'bypass_pinned_review_floor': (
        "if self._floor != (self.review_sequence, self.review_head):",
        "if False:  # synthetic mutation"),
    'disable_revocation': (
        "self._revoked.add(e['binding_id'])",
        "pass  # synthetic mutation: ignore revoke")
}

def main() -> int:
    for name,(old,new) in MUTANTS.items():
        if SOURCE.count(old) != 1:
            raise RuntimeError(f'UNKNOWN_MUTATION_SITE: {name} matched {SOURCE.count(old)} times')
        with tempfile.TemporaryDirectory(prefix='ario-rf05-mutate-') as t:
            p=Path(t)
            (p/'equivalence_read_view.py').write_text(SOURCE.replace(old,new),encoding='utf-8')
            (p/'test_equivalence_read_view.py').write_text(TEST,encoding='utf-8')
            env=dict(os.environ)
            env['PYTHONPATH']=str(p)+os.pathsep+str(RF01)
            result=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(p),'-p','test_*.py','-q'],
                                  cwd=p,env=env,text=True,capture_output=True,timeout=15)
            text=result.stdout+result.stderr
            failed='FAILED (' in text and 'failures=' in text and 'errors=' not in text
            print(f'{name}: exit={result.returncode}; expected_assertion_red={failed}; '+
                  (text.strip().splitlines()[-1] if text.strip() else '(no output)'))
            if result.returncode==0 or not failed:
                raise RuntimeError(f'MUTATION_NOT_DETECTED: {name}')
    print(f'{len(MUTANTS)}/{len(MUTANTS)} purposeful mutations detected; original source unchanged')
    return 0

if __name__=='__main__':
    raise SystemExit(main())