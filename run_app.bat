@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_sera.ps1" %*
if errorlevel 1 (
  echo.
  echo Sera startup failed. Check data\metadata\sera_backend.err.log and data\metadata\sera_frontend.err.log.
  pause
)
