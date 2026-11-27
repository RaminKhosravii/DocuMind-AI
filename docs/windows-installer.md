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

## Build locally on Windows (recommended for a direct installer)

You can build without GitHub Actions. Use a Windows 10/11 x64 computer with:

- Python 3.11 x64, including the Python Launcher (`py`).
- Inno Setup 6: https://jrsoftware.org/isdl.php
- An internet connection for the first dependency installation.

Steps:

1. Download or clone this repository and switch to the `feature/windows-desktop-installer` branch.
2. Install Python 3.11 x64 and Inno Setup 6.
3. Open the project folder in File Explorer.
4. Double-click `build_windows.bat`.
5. Wait for the build to finish. Do not close the terminal window.

The script creates an isolated `.build-venv` environment, installs the build dependencies, generates the app icon, packages the desktop application, creates the Inno Setup installer, and writes a SHA-256 checksum.

Expected outputs:

- Desktop bundle: `dist\DocuMindAI\DocuMindAI.exe`
- Installer: `installer\output\DocuMindAI-Setup-0.1.4.exe`
- Checksum: `installer\output\SHA256SUMS.txt`

The first build may take several minutes because Python packages must be downloaded. Later builds reuse the local build environment. If dependencies change, the script updates them automatically.

### If the build reports a missing prerequisite

- **Python 3.11 not found:** install Python 3.11 x64 and enable the Python Launcher option.
- **Inno Setup 6 not found:** install Inno Setup 6, then run `build_windows.bat` again.
- **pip download fails:** check the internet connection or package index access, then rerun the script.
- **Signing skipped:** the installer is unsigned unless a trusted code-signing certificate has been configured. An unsigned build can still trigger Windows SmartScreen or Defender warnings. A self-signed certificate does not establish public publisher trust.

## GitHub Actions

Open **Actions → Build Windows installer → Run workflow**. The workflow runs unit tests, builds the desktop bundle on Windows, and uploads the setup executable as an artifact. Pushing a version tag such as `v0.1.0` also triggers the build.

## Important validation note

A successful local or CI build only confirms that packaging completed. Before distributing it, install and smoke-test it on Windows 10 and Windows 11, including first launch, Ollama connectivity, document import/search, upgrade, and uninstall. Keep existing user data backed up before testing upgrades.
