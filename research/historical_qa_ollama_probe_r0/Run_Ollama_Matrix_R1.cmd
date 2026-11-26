@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
echo ARIO RIO-01 - Synthetic role spoofing matrix R1 (18 requests)
echo RESEARCH_ONLY - no real archive, no tool calls, no memory writes
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -B "ollama_synthetic_matrix_r1.py" --run-local-only --model llama3.2 --local-port 11600
) else (
  python -B "ollama_synthetic_matrix_r1.py" --run-local-only --model llama3.2 --local-port 11600
)
set RESULT=%errorlevel%
echo.
echo Only fictional prompts were sent to local Ollama at 127.0.0.1:11600.
echo No security proof, signer, history writes, or model tool execution.
echo Exit code: %RESULT%
pause
exit /b %RESULT%
