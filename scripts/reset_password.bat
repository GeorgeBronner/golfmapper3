@echo off
cd /d "%~dp0..\backend"
call uv run python ..\scripts\reset_user_password.py
pause
