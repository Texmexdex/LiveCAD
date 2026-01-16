@echo off
if not exist venv ( echo [ERROR] Run setup.bat first & pause & exit /b )
call venv\Scripts\activate
start /b python app.py