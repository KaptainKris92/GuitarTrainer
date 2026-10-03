@echo off
rem Starts the Guitar Trainer web app and opens it in your browser.
cd /d "%~dp0web"
if not exist node_modules call npm install
call npm run dev -- --open
if errorlevel 1 pause
