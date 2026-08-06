@echo off
chcp 65001 >nul
cd /d "%~dp0\..\..\"
python backend\scripts\run_migrate_remote.py
