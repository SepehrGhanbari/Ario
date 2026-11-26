"""Detect targeted regressions using independent individual source mutations."""
import os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'candidate/ario_github_crosscheck_v0_4.py').read_text()
runner=ROOT/'tests/test_r14_http.py'
mutants=[('overread', 'response.read(declared if declared is not None else MAX_REFERENCE_BYTES + 1)', 'response.read(MAX_REFERENCE_BYTES + 1)', 'test_combined_equal_content_length_held_open','ReferenceUnknown: GitHub reference unavailable over validated HTTPS'),('ignore_content_coding','if codings and [value.strip(" \\t").lower() for value in codings] != ["identity"]:', 'if False:', 'test_gzip_correct_registry_is_unknown_before_pin','VerificationRejected: OFFICIAL_REFERENCE_PIN_MISMATCH')]
for name,old,new,test,reason in mutants:
    assert source.count(old)==1
    with tempfile.TemporaryDirectory() as t:
        path=Path(t)/'verifier.py'; path.write_text(source)
        env=dict(os.environ,ARIO_TEST_TARGET=str(path));cmd=[sys.executable,'-I','-B',str(runner),'Controls.'+test]
        baseline=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=10)
        assert baseline.returncode==0,baseline.stderr
        path.write_text(source.replace(old,new))
        result=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=10)
        assert result.returncode==1 and reason in result.stderr, result.stderr
        print(name,'DETECTED; passing control; expected failure:',reason)
print('2/2 distinct mutants detected')
