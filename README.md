# DocuMind AI

<p align="center">
  <strong>A local-first AI assistant for understanding and searching documents.</strong>
</p>

<p align="center">
  <a href="https://github.com/RaminKhosravii/DocuMind-AI"><img src="https://img.shields.io/badge/status-active%20development-8B5CF6?style=for-the-badge" alt="Active development"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-app-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/Ollama-local%20AI-black?style=for-the-badge" alt="Ollama">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License">
</p>

DocuMind AI is an experimental document assistant built with Python and Streamlit. It extracts text from common document formats, stores documents locally, retrieves relevant passages, and uses a locally running language model through [Ollama](https://ollama.com/) to answer questions grounded in those passages.

> **Project status:** Under active development. Features, architecture, and setup instructions may change. This is not yet a production-ready application.

## Features

- **Local-first workflow:** documents and application data are stored in a local SQLite database.
- **Document ingestion:** upload and manage documents through a Streamlit interface.
- **Text extraction:** PDF, DOCX, XLSX, PPTX, TXT, Markdown, CSV, RTF, and LOG.
- **AI-assisted Q&A:** ask questions about one document or a collection of documents.
- **Retrieval-augmented answers:** retrieve relevant text passages before generating an answer.
- **Local inference:** communicate with an Ollama model through its local HTTP API.
- **Persian-friendly interface:** right-to-left layout and Vazirmatn typography.

## How it works

1. A user uploads a document.
2. DocuMind AI extracts its readable text and stores the document in SQLite.
3. When a question is submitted, the retrieval engine searches for relevant passages.
4. The selected passages are sent to the local Ollama model as context.
5. The model streams an answer based on the retrieved evidence.

The current retrieval pipeline combines semantic and lexical relevance scoring. The project is evolving; advanced multi-step reasoning, persistent embedding storage, and stronger evaluation are planned rather than claimed as completed features.

## Supported formats

| Format | Extension | Extraction |
|---|---|---|
| PDF | `.pdf` | Yes |
| Microsoft Word | `.docx` | Yes |
| Microsoft Excel | `.xlsx` | Yes |
| Microsoft PowerPoint | `.pptx` | Yes |
| Plain text | `.txt` | Yes |
| Markdown | `.md` | Yes |
| CSV | `.csv` | Yes |
| Rich Text | `.rtf` | Yes |
| Log | `.log` | Yes |

Other file types may be stored, but their text is not currently extracted.

## Requirements

- Windows, macOS, or Linux
- Python 3.10 or newer
- [Ollama](https://ollama.com/) installed and running
- Enough memory for the selected local language and embedding models

The application has been developed and tested in a resource-constrained local environment. Actual performance depends on the computer, document size, and models selected.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/RaminKhosravii/DocuMind-AI.git
cd DocuMind-AI
```

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install and prepare local models

Install Ollama, start its local service, then pull the models used by the current configuration:

```bash
ollama pull qwen3:1.7b
ollama pull nomic-embed-text
```

Model downloads require an internet connection. Once downloaded, inference is performed locally through Ollama.

### 5. Run the application

```bash
python -m streamlit run app.py
```

Streamlit will print a local URL in the terminal, usually `http://localhost:8501`.

## Project structure

```text
DocuMind-AI/
├── assets/
│   └── fonts/              # Local UI fonts
├── data/                   # Local runtime data (not committed)
├── ai_engine.py            # Retrieval and Ollama response generation
├── app.py                  # Streamlit user interface
├── database.py             # SQLite persistence and user/document operations
├── file_processor.py       # Document text extraction
├── migrate_documents.py    # Database migration utility
├── requirements.txt        # Python dependencies
├── test_ai.py
├── test_ai_engine.py
└── test_rag.py
```

## Privacy and security

- Do not commit databases, uploaded documents, credentials, API keys, or personal information.
- Document text and original file bytes are encrypted at rest with AES-256-GCM; on Windows, the encryption key is protected with the current Windows user's DPAPI.
- Passwords use salted PBKDF2-HMAC-SHA256 hashes and repeated failed logins trigger a temporary lockout.
- Keep the database and `master.key.dpapi` together in `%LOCALAPPDATA%\\DocuMind AI\\data`; a backup missing the key cannot be restored.
- Local encryption does not protect against malware or an attacker already running as the same Windows user. Use Windows sign-in protection and BitLocker where available.
- Ollama communication is restricted to loopback (`127.0.0.1`) and bypasses inherited system proxy settings.
- If sensitive data was ever committed to a public repository, deleting the file in a later commit does **not** remove it from Git history. Treat it as exposed and follow GitHub's guidance for sensitive data removal.


## Windows desktop installer

DocuMind AI includes a Windows desktop packaging target. The installed program opens in its own application window using Microsoft Edge WebView2; users do not need to open a browser manually. The setup package includes the Python application and its runtime libraries, but **does not bundle Ollama or the language models**.

### Requirements on the target PC

- Windows 10 or Windows 11, 64-bit.
- Microsoft Edge WebView2 Runtime (install the Evergreen Runtime if it is missing).
- [Ollama for Windows](https://ollama.com/download/windows).
- Run these commands once after installing Ollama:

  ```powershell
  ollama pull qwen3:1.7b
  ollama pull nomic-embed-text
  ```

The installer creates a Start menu shortcut and optionally a desktop shortcut. The local database is stored in `%LOCALAPPDATA%\DocuMind AI\data`, outside Program Files, so it remains writable for standard Windows users and is preserved when the application is upgraded.

### Build the installer

Build on Windows 10/11 x64 with Python 3.11 and Inno Setup 6 installed:

```powershell
python -m pip install -r requirements.txt -r requirements-build.txt
.\build_windows.bat
```

PyInstaller writes the application bundle to `dist\DocuMindAI`; Inno Setup writes the setup executable to `installer\output`.

### Build using GitHub Actions

Open **Actions → Build Windows installer → Run workflow**. The workflow runs the unit tests, builds the Windows application and uploads the installer as an artifact. Creating and pushing a version tag such as `v0.1.0` also triggers the workflow.

> The Windows installer must be built and smoke-tested on Windows. Unit tests passing on another operating system do not prove that the installer works on Windows 10/11. Test installation, first launch, Ollama connectivity, upgrade, and uninstall before publishing a public release.

## Roadmap

- [x] Local document library and SQLite storage
- [x] Text extraction for common office and text formats
- [x] Local Ollama-based question answering
- [x] Semantic and lexical retrieval
- [ ] Persistent embedding cache
- [ ] Multi-step question decomposition and retrieval
- [ ] Evidence validation and answer-quality evaluation
- [ ] Page-level source references
- [ ] Improved automated test coverage
- [ ] Optional web application and synchronization

## Contributing

Issues, bug reports, and thoughtful suggestions are welcome. Before submitting a pull request:

1. Describe the problem or improvement.
2. Keep changes focused and documented.
3. Test the affected functionality locally.
4. Never include real user data, local databases, or secrets.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with Python, Streamlit, and local AI.
</p>
