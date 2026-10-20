@echo off
chcp 65001 >nul
cd /d "%~dp0frontend"
echo [1/2] 构建前端……
echo （平时不用单独跑这个：双击 start.bat 会自动判断要不要重建）
call npm run build
if errorlevel 1 (
  echo.
  echo 构建失败，先看看上面的报错；如果是缺依赖，先在 frontend 目录跑 npm install。
  pause
  exit /b 1
)
echo.
echo [2/2] 完成。产物在 frontend\dist，后端会自动托管。
echo 现在只要启动 start.bat，打开 http://127.0.0.1:8000 即可。
pause
