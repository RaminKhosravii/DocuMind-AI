"""First-run provisioning for the Windows desktop edition.

Installs the official Ollama Windows runtime when absent, verifies its
Authenticode signature, starts the local API, and downloads the models used
by DocuMind. All model downloads are resumable through Ollama's pull API.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from urllib.request import Request, urlopen

import requests

OLLAMA_INSTALLER_URL = "https://ollama.com/download/OllamaSetup.exe"
OLLAMA_API = "http://127.0.0.1:11434"
REQUIRED_MODELS = ("qwen3:1.7b", "nomic-embed-text")
MIN_FREE_GB = 8


class SetupError(RuntimeError):
    pass


class FirstRunSetup:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("راه‌اندازی اولیه DocuMind AI")
        self.root.geometry("560x230")
        self.root.resizable(False, False)
        self.root.configure(bg="#171421")
        self.status = tk.StringVar(value="در حال بررسی پیش‌نیازهای هوش مصنوعی…")
        self.detail = tk.StringVar(value="لطفاً پنجره را نبندید.")
        tk.Label(self.root, text="DocuMind AI", fg="white", bg="#171421",
                 font=("Segoe UI", 17, "bold")).pack(pady=(18, 8))
        tk.Label(self.root, textvariable=self.status, fg="#eee8ff", bg="#171421",
                 font=("Segoe UI", 10), wraplength=510).pack(pady=4)
        self.bar = ttk.Progressbar(self.root, mode="determinate", maximum=100, length=490)
        self.bar.pack(pady=12)
        tk.Label(self.root, textvariable=self.detail, fg="#b8adc9", bg="#171421",
                 font=("Segoe UI", 9), wraplength=510).pack(pady=4)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.cancelled = False
        self.error = None

    def _on_close(self):
        # Do not interrupt an installer or model layer write mid-operation.
        self.status.set("راه‌اندازی در حال انجام است؛ لطفاً صبر کنید.")
        self.detail.set("پس از تکمیل، برنامه به‌صورت خودکار ادامه می‌یابد.")

    def update(self, status, detail="", percent=None):
        self.status.set(status)
        self.detail.set(detail)
        if percent is not None:
            self.bar["value"] = max(0, min(100, percent))
        self.root.update_idletasks()
        self.root.update()

    def run(self):
        try:
            self.provision()
        except Exception as exc:
            self.error = exc
        finally:
            self.root.destroy()
        if self.error:
            raise SetupError(str(self.error)) from self.error

    def provision(self):
        if os.name != "nt":
            raise SetupError("راه‌اندازی خودکار Ollama فقط در نسخه ویندوز پشتیبانی می‌شود.")

        free_gb = shutil.disk_usage(Path.home()).free / (1024 ** 3)
        if free_gb < MIN_FREE_GB:
            raise SetupError(
                f"فضای خالی کافی نیست. حداقل {MIN_FREE_GB} گیگابایت فضای آزاد لازم است؛ "
                f"فضای فعلی: {free_gb:.1f} گیگابایت."
            )

        if not self.api_ready():
            self.install_ollama_if_needed()
            self.start_ollama()
        if not self.wait_for_api(180):
            raise SetupError(
                "سرویس Ollama اجرا نشد. لطفاً سیستم را راه‌اندازی مجدد کنید و دوباره DocuMind AI را باز کنید."
            )

        for index, model in enumerate(REQUIRED_MODELS):
            if self.model_exists(model):
                self.update(f"مدل {model} آماده است.", "در حال بررسی مدل بعدی…",
                            int((index + 1) * 100 / len(REQUIRED_MODELS)))
                continue
            self.pull_model(model, index)
        self.update("راه‌اندازی هوش مصنوعی کامل شد.", "در حال باز کردن DocuMind AI…", 100)
        time.sleep(0.5)

    def api_ready(self):
        try:
            response = requests.get(f"{OLLAMA_API}/api/tags", timeout=2)
            return response.ok
        except requests.RequestException:
            return False

    def install_ollama_if_needed(self):
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama app.exe",
        ]
        if shutil.which("ollama") or any(path.is_file() for path in candidates):
            return

        temp_installer = Path(tempfile.gettempdir()) / "DocuMind-OllamaSetup.exe"
        self.update("در حال دانلود موتور هوش مصنوعی Ollama…",
                    "این مرحله به اینترنت نیاز دارد و ممکن است چند دقیقه طول بکشد.", 0)
        request = Request(OLLAMA_INSTALLER_URL, headers={"User-Agent": "DocuMindAI/0.1.2"})
        with urlopen(request, timeout=60) as response, temp_installer.open("wb") as output:
            total = int(response.headers.get("Content-Length", "0") or 0)
            downloaded = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                downloaded += len(chunk)
                percent = int(downloaded * 100 / total) if total else None
                self.update("در حال دانلود Ollama…",
                            f"{downloaded / (1024 ** 2):.0f} مگابایت دریافت شده", percent)

        self.update("در حال بررسی امضای دیجیتال نصب‌کننده Ollama…", "", 100)
        verify_script = (
            "$s=Get-AuthenticodeSignature -LiteralPath $args[0]; "
            "if($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'Ollama Inc') "
            "{exit 17}; exit 0"
        )
        check = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-Command", verify_script, str(temp_installer)],
            capture_output=True, text=True, timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if check.returncode != 0:
            temp_installer.unlink(missing_ok=True)
            raise SetupError("امضای دیجیتال نصب‌کننده Ollama معتبر نیست؛ برای امنیت نصب متوقف شد.")

        self.update("در حال نصب Ollama…", "نصب در سطح حساب کاربری انجام می‌شود.", 0)
        try:
            process = subprocess.Popen(
                [str(temp_installer), "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            while process.poll() is None:
                self.update("در حال نصب Ollama…", "لطفاً منتظر بمانید.")
                time.sleep(0.5)
            if process.returncode != 0:
                raise SetupError(f"نصب Ollama با کد {process.returncode} ناموفق بود.")
        finally:
            temp_installer.unlink(missing_ok=True)

    def start_ollama(self):
        if self.api_ready():
            return
        executable = shutil.which("ollama")
        if not executable:
            for path in (
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama app.exe",
            ):
                if path.is_file():
                    executable = str(path)
                    break
        if executable:
            subprocess.Popen(
                [executable, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

    def wait_for_api(self, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.api_ready():
                return True
            self.update("در انتظار آماده‌شدن Ollama…",
                        "در حال اتصال به سرویس محلی روی همین کامپیوتر.")
            time.sleep(1)
        return False

    def model_exists(self, model):
        try:
            response = requests.get(f"{OLLAMA_API}/api/tags", timeout=10)
            response.raise_for_status()
            names = {item.get("name") for item in response.json().get("models", [])}
            return model in names or f"{model}:latest" in names
        except (requests.RequestException, ValueError):
            return False

    def pull_model(self, model, index):
        self.update(f"در حال دریافت مدل {model}…",
                    "دانلود ممکن است حجیم باشد؛ در صورت قطع اینترنت، Ollama امکان ادامه دانلود را دارد.", 0)
        response = requests.post(
            f"{OLLAMA_API}/api/pull",
            json={"model": model, "stream": True},
            stream=True, timeout=(15, 180),
        )
        response.raise_for_status()
        last_status = "شروع دانلود…"
        try:
            for raw in response.iter_lines():
                if not raw:
                    continue
                item = json.loads(raw)
                last_status = item.get("status", last_status)
                total = item.get("total") or 0
                completed = item.get("completed") or 0
                percent = int(completed * 100 / total) if total else None
                self.update(f"در حال دریافت {model}…",
                            f"{last_status} — {completed / (1024 ** 2):.0f} / "
                            f"{total / (1024 ** 2):.0f} مگابایت" if total else last_status,
                            percent)
                if item.get("error"):
                    raise SetupError(f"دریافت مدل {model} ناموفق بود: {item['error']}")
        finally:
            response.close()
        if not self.model_exists(model):
            raise SetupError(f"مدل {model} پس از دانلود در فهرست Ollama پیدا نشد.")


def ensure_ai_runtime():
    """Provision the local AI runtime before opening the main application."""
    FirstRunSetup().run()
