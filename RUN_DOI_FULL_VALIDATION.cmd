@echo off
setlocal
cd /d "%~dp0"
python -I -B scripts\run_doi_bulk.py > DOI_FULL_RESULTS.json
set "RC=%ERRORLEVEL%"
type DOI_FULL_RESULTS.json
echo Exit code: %RC%
echo Return DOI_FULL_RESULTS.json to reviewer.
pause
exit /b %RC%
