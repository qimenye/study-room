@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0frontend"

if not exist "node_modules" (
  echo [!] node_modules not found. Run setup.bat first.
  exit /b 1
)

echo Frontend: http://127.0.0.1:5173
call npm run dev