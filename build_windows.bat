@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title DocuMind AI - Local Windows Build

echo.
echo ==========================================
echo       DocuMind AI - Windows Builder
echo ==========================================
echo.

REM Require the Python Launcher and Python 3.11 (64-bit).
where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python Launcher was not found.
  echo Install Python 3.11 x64 from https://www.python.org/downloads/
  echo During setup, enable "Python Launcher" and "Add Python to PATH".
  pause
  exit /b 1
)

py -3.11 -c "import sys, struct; print('Python:', sys.version); print('Architecture:', struct.calcsize('P')*8)" >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.11 was not found.
  echo Install Python 3.11 x64, then run this file again.
  pause
  exit /b 1
)

py -3.11 -c "import struct,sys; sys.exit(0 if struct.calcsize('P')*8 == 64 else 1)"
if errorlevel 1 (
  echo ERROR: 64-bit Python is required.
  pause
  exit /b 1
)

REM Create an isolated build environment only once.
if not exist ".build-venv\Scripts\python.exe" (
  echo [1/6] Creating isolated build environment...
  py -3.11 -m venv .build-venv
  if errorlevel 1 goto :failed
) else (
  echo [1/6] Reusing existing build environment...
)

echo [2/6] Installing and checking build dependencies...
".build-venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed
".build-venv\Scripts\python.exe" -m pip install -r requirements.txt -r requirements-build.txt
if errorlevel 1 goto :failed

echo [3/6] Generating application icon...
".build-venv\Scripts\python.exe" scripts\build_icon.py
if errorlevel 1 goto :failed

echo [4/6] Building the desktop application...
".build-venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --onedir --noupx ^
  --name "DocuMindAI" ^
  --icon "assets\documind.ico" ^
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
  --hidden-import first_run_setup ^
  --hidden-import pymupdf ^
  --add-data "app.py;." ^
  --add-data "ai_engine.py;." ^
  --add-data "database.py;." ^
  --add-data "file_processor.py;." ^
  --add-data "security.py;." ^
  --add-data "assets;assets" ^
  desktop_launcher.py
if errorlevel 1 goto :failed

if not exist "dist\DocuMindAI\DocuMindAI.exe" (
  echo ERROR: PyInstaller did not create the expected application executable.
  goto :failed
)

echo [5/6] Checking for Inno Setup 6...
set "ISCC="
if defined INNO_SETUP_COMPILER set "ISCC=%INNO_SETUP_COMPILER%"
if not defined ISCC (
  for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do if not defined ISCC set "ISCC=%%I"
)
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" (
  echo ERROR: Inno Setup 6 was not found.
  echo Install it from https://jrsoftware.org/isdl.php
  echo Then run this file again. The desktop application bundle is already in dist\DocuMindAI.
  goto :failed
)

echo [6/6] Creating and signing the installer (if a trusted certificate is configured)...
if not exist "installer\output" mkdir "installer\output"
"%ISCC%" /DAppVersion=0.1.4 installer\DocuMindAI.iss
if errorlevel 1 goto :failed

set "INSTALLER=installer\output\DocuMindAI-Setup-0.1.4.exe"
if not exist "%INSTALLER%" (
  echo ERROR: Inno Setup did not create %INSTALLER%.
  goto :failed
)

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\sign_windows.ps1 -FilePath "%INSTALLER%"
if errorlevel 1 goto :failed

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='%INSTALLER%'; $h=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant(); Set-Content -LiteralPath 'installer\output\SHA256SUMS.txt' -Value ($h + '  DocuMindAI-Setup-0.1.4.exe') -Encoding ascii; Write-Host ('SHA-256: ' + $h)"
if errorlevel 1 goto :failed

echo.
echo ==========================================
echo BUILD SUCCESSFUL
echo Installer: %INSTALLER%
echo Checksum:  installer\output\SHA256SUMS.txt
echo ==========================================
echo.
pause
exit /b 0

:failed
echo.
echo BUILD FAILED. Read the error above and fix the reported prerequisite.
echo If the application build succeeded but Inno Setup is missing, install Inno Setup 6 and rerun this file.
echo.
pause
exit /b 1
