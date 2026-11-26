@echo off
setlocal
cd /d "%~dp0"
python -I -B scripts\ario_verify_coverage.py doi-catalog > DOI_CATALOG_RESULTS.json
set "RC=%ERRORLEVEL%"
type DOI_CATALOG_RESULTS.json
echo Exit code: %RC% (3 means metadata only or unknown, not verified bytes)
pause
exit /b %RC%
