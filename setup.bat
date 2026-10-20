@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo [1/3] Creating backend virtualenv (.venv) ...
if exist ".venv\Scripts\python.exe" (
  echo     .venv already exists, skip.
) else (
  python -m venv .venv
  if errorlevel 1 (
    echo     [!] Failed. Try: C:\Users\LEGION\anaconda3\envs\py310\python.exe -m venv .venv
    exit /b 1
  )
)

echo [2/3] Installing backend dependencies ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
if errorlevel 1 (
  echo     [!] pip install failed. Check your network.
  exit /b 1
)

echo [3/3] Installing frontend dependencies ...
cd frontend
call npm install
if errorlevel 1 (
  echo     [!] npm install failed. Check your network.
  exit /b 1
)

echo.
echo Done. Next:
echo   start.bat          one-click: rebuild frontend if needed + open http://127.0.0.1:8000
echo   run-frontend.bat   dev mode with hot reload: http://127.0.0.1:5173
