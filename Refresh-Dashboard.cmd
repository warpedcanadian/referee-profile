@echo off
powershell.exe -NoProfile -STA -File "%~dp0scripts\refresh.ps1" %*
if errorlevel 1 exit /b 1
