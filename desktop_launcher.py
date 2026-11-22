"""Windows desktop launcher with persistent startup diagnostics."""
from __future__ import annotations

import logging
import os
import socket
import sys
import threading
import time
import traceback
from pathlib import Path

import requests
import webview


def user_data_root() -> Path:
    return Path(os.getenv("LOCALAPPDATA", Path.home())) / "DocuMind AI"


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def configure_logging() -> Path:
    log_dir = user_data_root() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "startup.log"
    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(threadName)s] %(message)s",
        encoding="utf-8",
        force=True,
    )

    def thread_exception_hook(args):
        logging.error(
            "Unhandled exception in thread %s",
            args.thread.name if args.thread else "<unknown>",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = thread_exception_hook
    logging.info("========== DocuMind AI starting ==========")
    logging.info("Python=%s frozen=%s executable=%s", sys.version, getattr(sys, "frozen", False), sys.executable)
    return log_path


def choose_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run_streamlit(port: int, app_dir: Path) -> None:
    os.chdir(app_dir)
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))

    app_file = app_dir / "app.py"
    if not app_file.is_file():
        raise FileNotFoundError(f"app.py is missing from packaged application: {app_file}")

    sys.argv = [
        "streamlit", "run", str(app_file),
        "--server.headless=true",
        "--server.enableCORS=true",
        "--server.enableXsrfProtection=true",
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    logging.info("Starting Streamlit: app=%s port=%s", app_file, port)
    from streamlit.web import cli as stcli
    stcli.main()
    logging.error("Streamlit CLI returned before the desktop server became ready")


def wait_for_server(port: int, server_thread: threading.Thread, timeout: float = 120.0) -> bool:
    health_url = f"http://127.0.0.1:{port}/_stcore/health"
    deadline = time.monotonic() + timeout
    session = requests.Session()
    session.trust_env = False
    try:
        while time.monotonic() < deadline:
            if not server_thread.is_alive():
                logging.error("Streamlit thread exited before health check succeeded")
                return False
            try:
                response = session.get(health_url, timeout=2)
                if response.ok:
                    logging.info("Streamlit health check passed on port %s", port)
                    return True
                logging.warning("Health endpoint returned HTTP %s", response.status_code)
            except requests.RequestException as exc:
                logging.debug("Waiting for Streamlit: %s", exc)
            time.sleep(0.5)
        logging.error("Timed out waiting for Streamlit after %.1f seconds", timeout)
        return False
    finally:
        session.close()


def main() -> int:
    log_path = configure_logging()
    app_dir = application_dir()
    app_file = app_dir / "app.py"
    if not app_file.is_file():
        raise FileNotFoundError(f"Application files not found: {app_file}")

    data_dir = user_data_root() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DOCUMIND_DATA_DIR"] = str(data_dir)
    os.environ["DOCUMIND_OLLAMA_URL"] = "http://127.0.0.1:11434"

    # Prepare Ollama and the exact models used by ai_engine.py before starting the UI.
    from first_run_setup import ensure_ai_runtime
    logging.info("Checking local AI runtime and required models")
    ensure_ai_runtime()

    # Keep SQLite and its DPAPI key in the writable per-user data directory.
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

    if not wait_for_server(port, server_thread):
        raise RuntimeError(
            "DocuMind local server did not become ready. "
            f"Detailed startup log: {log_path}"
        )

    icon_path = app_dir / "assets" / "documind.ico"
    window_options = {
        "title": "DocuMind AI",
        "url": f"http://127.0.0.1:{port}",
        "width": 1280,
        "height": 820,
        "min_size": (900, 620),
        "background_color": "#111019",
    }
    if icon_path.is_file():
        window_options["icon"] = str(icon_path)

    logging.info("Opening desktop window")
    webview.create_window(**window_options)
    webview.start(debug=False)
    logging.info("Desktop window closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        error_dir = user_data_root()
        error_dir.mkdir(parents=True, exist_ok=True)
        error_text = traceback.format_exc()
        logging.exception("Fatal application startup error")
        (error_dir / "startup-error.txt").write_text(error_text, encoding="utf-8")
        raise
