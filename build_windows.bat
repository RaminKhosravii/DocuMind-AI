@echo off
setlocal
cd /d "%~dp0"

py -3.11 -m venv .build-venv
call .build-venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-build.txt

pyinstaller --noconfirm --clean --windowed --onedir ^
  --name "DocuMindAI" ^
  --collect-all streamlit ^
  --collect-all altair ^
  --collect-all pydeck ^
  --collect-all webview ^
  --collect-all watchdog ^
  --collect-all pymupdf ^
  --collect-all docx ^
  --collect-all openpyxl ^
  --collect-all pptx ^
  --collect-all striprtf ^
  --collect-all cryptography ^
  --hidden-import streamlit.web.cli ^
  --hidden-import pymupdf ^
  --add-data "app.py;." ^
  --add-data "ai_engine.py;." ^
  --add-data "database.py;." ^
  --add-data "file_processor.py;." ^
  --add-data "security.py;." ^
  --add-data "assets;assets" ^
  desktop_launcher.py

if errorlevel 1 exit /b 1

set "ISCC=ISCC.exe"
if defined INNO_SETUP_COMPILER set "ISCC=%INNO_SETUP_COMPILER%"
if not defined INNO_SETUP_COMPILER (
  where ISCC.exe >nul 2>nul
  if errorlevel 1 set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
)

if not exist "%ISCC%" (
  echo ERROR: Inno Setup 6 was not found. The Windows installer cannot be created.
  exit /b 1
)

"%ISCC%" /DAppVersion=0.1.0 installer\DocuMindAI.iss
if errorlevel 1 exit /b 1

echo Build completed. See installer\output\
