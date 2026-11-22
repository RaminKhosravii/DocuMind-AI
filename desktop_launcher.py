"""Desktop entry point: run Streamlit inside a native WebView window."""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import traceback
from pathlib import Path

import requests
import webview


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def choose_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run_streamlit(port: int, app_dir: Path) -> None:
    os.chdir(app_dir)
    sys.path.insert(0, str(app_dir))
    sys.argv = [
        "streamlit", "run", str(app_dir / "app.py"),
        "--server.headless=true",
        "--server.enableCORS=true",
        "--server.enableXsrfProtection=true",
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    from streamlit.web import cli as stcli
    stcli.main()


def wait_for_server(port: int, timeout: float = 90.0) -> bool:
    health_url = f"http://127.0.0.1:{port}/_stcore/health"
    deadline = time.monotonic() + timeout
    session = requests.Session()
    session.trust_env = False
    try:
        while time.monotonic() < deadline:
            try:
                response = session.get(health_url, timeout=1.5)
                if response.ok:
                    return True
            except requests.RequestException:
                pass
            time.sleep(0.4)
        return False
    finally:
        session.close()


def main() -> int:
    app_dir = application_dir()
    app_file = app_dir / "app.py"
    if not app_file.exists():
        raise FileNotFoundError(f"Application files not found: {app_file}")

    local_app_data = Path(os.getenv("LOCALAPPDATA", Path.home()))
    data_dir = local_app_data / "DocuMind AI" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DOCUMIND_DATA_DIR"] = str(data_dir)
    os.environ.setdefault("DOCUMIND_OLLAMA_URL", "http://localhost:11434")

    # Keep the SQLite database outside Program Files in a writable user folder.
    import database as database_module
    database_module.DATA_DIR = data_dir
    database_module.DB_PATH = data_dir / "documind.db"

    port = choose_port()
    server_thread = threading.Thread(
        target=run_streamlit,
        args=(port, app_dir),
        daemon=True,
        name="DocuMind-Streamlit",
    )
    server_thread.start()

    if not wait_for_server(port):
        raise RuntimeError(
            "DocuMind could not start its local web server. "
            "Check the application files and Windows security software."
        )

    webview.create_window(
        "DocuMind AI",
        f"http://127.0.0.1:{port}",
        width=1280,
        height=820,
        min_size=(900, 620),
        background_color="#111019",
    )
    webview.start(debug=False)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        error_dir = Path(os.getenv("LOCALAPPDATA", Path.home())) / "DocuMind AI"
        error_dir.mkdir(parents=True, exist_ok=True)
        (error_dir / "startup-error.txt").write_text(
            traceback.format_exc(), encoding="utf-8"
        )
        raise
