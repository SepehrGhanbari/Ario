@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python -I -B scripts\ario_verified_release.py download --directory .
) else (
  py -3 -I -B scripts\ario_verified_release.py download --directory .
)
set "RC=%ERRORLEVEL%"
echo Exit code: %RC%
pause
exit /b %RC%
