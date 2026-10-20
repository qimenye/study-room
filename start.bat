@echo off
chcp 65001 >nul
rem 双击这个就行：会自动把前端构建到最新、启动后端、并把浏览器打开。
rem 真正的逻辑在 run-backend.bat 里，这里只是个好记的入口。
call "%~dp0run-backend.bat" %*
