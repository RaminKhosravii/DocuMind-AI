# Windows desktop installer

DocuMind AI can be packaged as a Windows desktop application using PyInstaller, pywebview and Inno Setup 6. The installed app opens in its own native WebView window; it does not require the user to open a browser manually.

## End-user prerequisites

- Windows 10 or Windows 11, 64-bit.
- Microsoft Edge WebView2 Runtime. It is already present on most supported Windows installations; install the Evergreen Runtime if missing.
- Ollama for Windows: https://ollama.com/download/windows
- Download the local models once from PowerShell:

  ```powershell
  ollama pull qwen3:1.7b
  ollama pull nomic-embed-text
  ```

The setup program installs the DocuMind application files and creates Start menu shortcuts. Ollama and its models are deliberately not bundled: they are separate software and the model files are large. The SQLite database is stored under `%LOCALAPPDATA%\DocuMind AI\data`, so normal users do not need write access to Program Files and application upgrades do not overwrite the database.

## Build on Windows

Use a Windows 10/11 x64 machine with Python 3.11 and Inno Setup 6 installed.

```powershell
python -m pip install -r requirements.txt -r requirements-build.txt
.\build_windows.bat
```

The PyInstaller output is written to `dist\DocuMindAI`. The setup executable is written to `installer\output` when Inno Setup is available. If Inno Setup is installed after the PyInstaller build, run:

```powershell
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVersion=0.1.0 installer\DocuMindAI.iss
```

## GitHub Actions

Open **Actions → Build Windows installer → Run workflow**. The workflow runs unit tests, builds the desktop bundle on Windows, and uploads the setup executable as an artifact. Pushing a version tag such as `v0.1.0` also triggers the build.

## Important validation note

The source-level unit tests can run on other operating systems, but the installer itself must be built and smoke-tested on Windows 10 and Windows 11. A successful CI build does not replace testing installation, first launch, Ollama connectivity, upgrade, and uninstall on real Windows machines.
