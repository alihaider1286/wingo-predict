@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt
py cracker_wingo_scanner.py
pause
