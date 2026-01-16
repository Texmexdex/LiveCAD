@echo off
echo [INFO] Initializing LiveCAD Environment...
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
echo [INFO] Setup Complete.
pause