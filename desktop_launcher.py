"""Windows desktop launcher with an isolated Streamlit server process.

Streamlit installs OS signal handlers during CLI startup. It must therefore
run on the main thread of its own process; running the CLI in a Python worker
thread raises "signal only works in main thread". The desktop GUI and the
Streamlit server are isolated into separate processes to avoid that conflict.
"""
from __future__ import annotations

import logging
import multiprocessing
import os
import socket
import sys
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
        format="%(asctime)s %(levelname)s [%(processName)s] %(message)s",
        encoding="utf-8",
        force=True,
    )
    logging.info("========== DocuMind AI starting ==========")
    logging.info(
        "Python=%s frozen=%s executable=%s",
        sys.version,
        getattr(sys, "frozen", False),
        sys.executable,
    )
    return log_path


def choose_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run_streamlit(port: int, app_dir: Path, log_path: Path) -> None:
    """Child-process entry point. Streamlit CLI runs on this process's main thread."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = open(log_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = log_handle
    sys.stderr = log_handle
    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(processName)s] %(message)s",
        encoding="utf-8",
        force=True,
    )
    try:
        os.chdir(app_dir)
        if str(app_dir) not in sys.path:
            sys.path.insert(0, str(app_dir))

        app_file = app_dir / "app.py"
        if not app_file.is_file():
            raise FileNotFoundError(
                f"app.py is missing from packaged application: {app_file}"
            )

        os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
        sys.argv = [
            "streamlit",
            "run",
            str(app_file),
            "--global.developmentMode=false",
            "--server.headless=true",
            "--server.enableCORS=true",
            "--server.enableXsrfProtection=true",
            "--server.address=127.0.0.1",
            f"--server.port={port}",
            "--server.fileWatcherType=none",
            "--browser.gatherUsageStats=false",
        ]
        logging.info("Starting isolated Streamlit process: app=%s port=%s", app_file, port)
        from streamlit.web import cli as stcli
        stcli.main()
        logging.error("Streamlit CLI returned before desktop shutdown")
    except BaseException:
        logging.exception("Streamlit child process failed")
        raise
    finally:
        try:
            log_handle.flush()
            log_handle.close()
        except Exception:
            pass


def wait_for_server(port: int, server_process: multiprocessing.Process,
                    timeout: float = 180.0) -> bool:
    health_url = f"http://127.0.0.1:{port}/_stcore/health"
    deadline = time.monotonic() + timeout
    session = requests.Session()
    session.trust_env = False
    try:
        while time.monotonic() < deadline:
            if not server_process.is_alive():
                logging.error(
                    "Streamlit child process exited before health check; exitcode=%s",
                    server_process.exitcode,
                )
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


def stop_server(server_process: multiprocessing.Process) -> None:
    if server_process.is_alive():
        logging.info("Stopping Streamlit child process")
        server_process.terminate()
        server_process.join(timeout=10)
        if server_process.is_alive():
            logging.warning("Streamlit did not stop gracefully; killing child process")
            server_process.kill()
            server_process.join(timeout=5)


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

    # Provision the local AI runtime before opening the UI.
    from first_run_setup import ensure_ai_runtime
    logging.info("Checking local AI runtime and required models")
    ensure_ai_runtime()

    # Keep SQLite and its DPAPI key in the writable per-user data directory.
    import database as database_module
    database_module.DATA_DIR = data_dir
    database_module.DB_PATH = data_dir / "documind.db"

    port = choose_port()
    context = multiprocessing.get_context("spawn")
    server_process = context.Process(
        target=run_streamlit,
        args=(port, app_dir, log_path),
        name="DocuMind-Streamlit",
        daemon=False,
    )
    server_process.start()
    logging.info("Started Streamlit child process pid=%s port=%s",
                 server_process.pid, port)

    try:
        if not wait_for_server(port, server_process):
            raise RuntimeError(
                "DocuMind local server did not become ready. "
                f"Detailed startup log: {log_path}; "
                f"server exit code: {server_process.exitcode}"
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
    finally:
        stop_server(server_process)
        if server_process.pid is not None:
            server_process.close()


if __name__ == "__main__":
    # Required for PyInstaller + multiprocessing on Windows. In frozen child
    # processes this dispatches the multiprocessing worker before main() runs.
    multiprocessing.freeze_support()
    try:
        raise SystemExit(main())
    except Exception:
        error_dir = user_data_root()
        error_dir.mkdir(parents=True, exist_ok=True)
        error_text = traceback.format_exc()
        logging.exception("Fatal application startup error")
        (error_dir / "startup-error.txt").write_text(error_text, encoding="utf-8")
        raise
