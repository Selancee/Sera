@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_sera.ps1" %*
if errorlevel 1 (
  echo.
  echo Sera web development startup failed. Check data\metadata logs.
  pause
)
