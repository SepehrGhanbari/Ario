@echo off
setlocal
python -I -B "%~dp0scripts\ario_integrity_gate.py" --menu
set "RC=%ERRORLEVEL%"
echo Exit code: %RC%
pause
exit /b %RC%
