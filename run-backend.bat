@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ==========================================================
echo   线上自习室 - 一键启动（会先把前端构建到最新）
echo ==========================================================
echo.

if not exist ".venv\Scripts\python.exe" goto :no_env
if not exist "frontend\node_modules" goto :no_env

rem ---------- 1/2 前端：源码比 dist 新就自动重建 ----------
set "NEED_BUILD="
if not exist "frontend\dist\index.html" set "NEED_BUILD=1"
if not defined NEED_BUILD (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=(Get-Item -LiteralPath 'frontend\dist\index.html').LastWriteTime; $s=(Get-ChildItem -LiteralPath 'frontend' -Recurse -File -Include *.vue,*.js,*.mjs,*.css,*.html,*.json | Where-Object { $_.FullName -notmatch 'node_modules|dist' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime; if ($s -gt $d) { exit 9 }"
  if errorlevel 9 set "NEED_BUILD=1"
)

if defined NEED_BUILD (
  echo [1/2] 前端源码有更新，正在重新构建……
  pushd "frontend"
  call npm run build
  if errorlevel 1 (
    popd
    echo.
    echo [!] 前端构建失败，请看上面的报错。
    echo     如果提示缺依赖，先在 frontend 目录执行 npm install。
    echo.
    pause
    exit /b 1
  )
  popd
  echo [1/2] 构建完成，frontend\dist 已是最新
) else (
  echo [1/2] 前端已经是最新的，跳过构建
)
echo.

rem ---------- 2/2 后端：端口占用就先不重复起 ----------
set "PORT_BUSY="
powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=New-Object Net.Sockets.TcpClient; try { if ($c.ConnectAsync('127.0.0.1',8000).Wait(700) -and $c.Connected) { exit 9 } } catch {} finally { $c.Close() }"
if errorlevel 9 set "PORT_BUSY=1"
if defined PORT_BUSY goto :already_running

echo [2/2] 启动后端：http://127.0.0.1:8000   接口文档：/docs
echo       浏览器会自动打开；关掉这个窗口就停掉服务。
echo.
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "$u='http://127.0.0.1:8000/api/health'; for ($i=0; $i -lt 45; $i++) { try { Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep -Milliseconds 700 } }; Start-Process 'http://127.0.0.1:8000'"

cd /d "%~dp0backend"
"..\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
exit /b 0

:already_running
echo [2/2] 8000 端口已经有服务在跑，直接打开浏览器。
echo       如果刚刚改过后端代码，请在原来那个窗口按 Ctrl+C 重启一次。
echo.
start "" http://127.0.0.1:8000
exit /b 0

:no_env
echo [!] 运行环境还没装好，先双击 setup.bat 走一遍安装。
echo     需要：.venv 和 frontend\node_modules
echo.
pause
exit /b 1
