@echo off
setlocal
chcp 65001 >nul
set "SCRIPT_DIR=%~dp0"
set "RUN_DIR=%LOCALAPPDATA%\Ario\ava-cloud-identity-20261103-FRESH"
if exist "%RUN_DIR%\events.jsonl" (
  py -3 "%SCRIPT_DIR%ario_ava_cloud_50.py" --run-dir "%RUN_DIR%" --letter "%SCRIPT_DIR%ARIO_IDENTITY_INTERIM_FINDINGS_LETTER_FA_2026-11-03.md"
) else (
  py -3 "%SCRIPT_DIR%ario_ava_cloud_50.py" --run-dir "%RUN_DIR%" --letter "%SCRIPT_DIR%ARIO_IDENTITY_INTERIM_FINDINGS_LETTER_FA_2026-11-03.md" --new --target 50
)
exit /b %ERRORLEVEL%
