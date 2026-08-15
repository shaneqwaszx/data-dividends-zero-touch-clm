@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0demo_lifecycle.ps1" -Action Start
set "DEMO_EXIT_CODE=%ERRORLEVEL%"
endlocal & exit /b %DEMO_EXIT_CODE%
