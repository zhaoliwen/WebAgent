@echo off
REM 双击或在命令行运行本脚本，调用 PowerShell 一键打包
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1"
if errorlevel 1 pause
