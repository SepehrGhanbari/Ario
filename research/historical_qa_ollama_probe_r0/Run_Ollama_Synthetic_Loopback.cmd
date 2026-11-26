@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
echo ARIO RESEARCH_ONLY - SYNTHETIC LOCAL OLLAMA TEST - NO ARCHIVE
echo No signer, no QwenMemory, no model tools, no memory writes.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -B "ollama_synthetic_probe.py" --run-local-only --model llama3.2 --local-port 11600
) else (
  python -B "ollama_synthetic_probe.py" --run-local-only --model llama3.2 --local-port 11600
)
set RESULT=%errorlevel%
echo.
echo Only fixed synthetic examples were sent to 127.0.0.1:11600.
echo This is NOT an OS sandbox or proof of model security.
echo Exit code: %RESULT%
pause
exit /b %RESULT%
