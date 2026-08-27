@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0build_windows_app.ps1" %*
