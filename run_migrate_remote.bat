@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   TikTok 数据 UTC 迁移工具
echo ============================================
echo.

REM 检测 python 命令
where python >nul 2>&1
if %errorlevel%==0 (
    set PYCMD=python
    goto :run
)

where py >nul 2>&1
if %errorlevel%==0 (
    set PYCMD=py
    goto :run
)

echo [错误] 未找到 Python，请先安装 Python 并勾选 Add to PATH。
echo.
pause
exit /b 1

:run
echo 使用 Python: %PYCMD%
echo.
%PYCMD% backend\scripts\run_migrate_remote.py
echo.
echo ============================================
echo 脚本已结束。如果上方有错误信息，请截图。
echo ============================================
pause
