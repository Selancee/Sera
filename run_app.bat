@echo off
setlocal
cd /d "%~dp0"
set "SERA_PACKAGED=%~dp0dist_desktop\release\win-unpacked\Sera.exe"
if exist "%SERA_PACKAGED%" (
  start "" "%SERA_PACKAGED%"
  exit /b 0
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_sera_desktop.ps1" %*
if errorlevel 1 (
  echo.
  echo Sera Desktop startup failed. Review the message above.
  pause
)
