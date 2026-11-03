@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
py -3 "%SCRIPT_DIR%ario_ava_cloud_50.py" --run-dir "%LOCALAPPDATA%\Ario\ava-cloud-identity-20261103" --letter "%SCRIPT_DIR%ARIO_IDENTITY_INTERIM_FINDINGS_LETTER_FA_2026-11-03.md" --status
exit /b %ERRORLEVEL%
