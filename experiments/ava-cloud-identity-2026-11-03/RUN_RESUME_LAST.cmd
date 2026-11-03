@echo off
setlocal
chcp 65001 >nul
set "SCRIPT_DIR=%~dp0"
set "RUN_DIR=%LOCALAPPDATA%\Ario\ava-cloud-identity-20261103"
set "LETTER=%SCRIPT_DIR%ARIO_IDENTITY_INTERIM_FINDINGS_LETTER_FA_2026-11-03.md"
if exist "%RUN_DIR%\events.jsonl" (
  py -3 "%SCRIPT_DIR%ario_ava_cloud_50.py" --run-dir "%RUN_DIR%" --letter "%LETTER%"
) else (
  if "%~1"=="" (
    echo [HOLD] No saved run exists. For the first run, drag the genuine v0.5
    echo exported complete transcript JSONL, TXT, or MD onto RUN_RESUME_LAST.cmd.
    echo This does NOT edit or replace the original v0.5 session.
    exit /b 2
  )
  py -3 "%SCRIPT_DIR%ario_ava_cloud_50.py" --run-dir "%RUN_DIR%" --letter "%LETTER%" --import-legacy "%~1" --target 50
)
set "EXIT_CODE=%ERRORLEVEL%"
echo Local append-only log: %RUN_DIR%\events.jsonl
echo Runner exit code: %EXIT_CODE%
exit /b %EXIT_CODE%
