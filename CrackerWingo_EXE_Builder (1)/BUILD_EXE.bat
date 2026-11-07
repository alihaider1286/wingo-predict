@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo CRACKER WINGO SCANNER - EXE BUILDER
echo ==========================================
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.11+ not found. Install from https://www.python.org/downloads/windows/
  echo During install, tick "Add Python to PATH".
  pause
  exit /b 1
)
echo [1/3] Installing build dependencies...
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo [2/3] Building Windows executable...
py -m PyInstaller --noconfirm --clean --onefile --windowed --name CrackerWingoScanner cracker_wingo_scanner.py
if errorlevel 1 goto failed
echo [3/3] Done.
echo Your EXE is here: dist\CrackerWingoScanner.exe
echo IMPORTANT: Install Tesseract OCR on the target PC:
echo https://github.com/UB-Mannheim/tesseract/wiki
echo Default OCR path: C:\Program Files\Tesseract-OCR\tesseract.exe
pause
exit /b 0
:failed
echo Build failed. Copy the error text and send it for fixing.
pause
exit /b 1
