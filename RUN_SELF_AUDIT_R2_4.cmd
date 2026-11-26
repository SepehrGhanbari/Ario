@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo ARIO SELF-AUDIT R2.4 - READ ONLY / RESEARCH ONLY
echo ============================================================
echo.
pushd "%~dp0scripts"
where py >nul 2>nul
if errorlevel 1 (
  echo Running adversarial tests with python...
  python -B -m unittest -v test_ario_self_audit_r24
) else (
  echo Running adversarial tests with Python 3...
  py -3 -B -m unittest -v test_ario_self_audit_r24
)
set "TEST_RC=%ERRORLEVEL%"
popd
if not "%TEST_RC%"=="0" (
  echo.
  echo SELF-TEST FAILED. Verification will not continue.
  pause
  exit /b 2
)
echo.
echo Tests passed. Now select the folder created by R2.3-D.
echo It must contain LOG_TRANSPORT_REPORT.json and the six .log files.
echo No token is needed. This verifier is offline.
echo.
set /p EVIDENCE_DIR=Paste the full R2.3-D output folder path: 
if not defined EVIDENCE_DIR (
  echo No folder supplied.
  pause
  exit /b 3
)
where py >nul 2>nul
if errorlevel 1 (
  python -I -B scripts\ario_self_audit_r24.py --verify "%EVIDENCE_DIR%"
) else (
  py -3 -I -B scripts\ario_self_audit_r24.py --verify "%EVIDENCE_DIR%"
)
set "RC=%ERRORLEVEL%"
echo.
echo R2.4 exit code: %RC%
pause
exit /b %RC%
