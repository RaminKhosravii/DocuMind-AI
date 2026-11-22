"""Local SQLite storage with per-user authorization and encrypted document payloads."""
from __future__ import annotations

import base64
import ctypes
import hashlib
import os
import secrets
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE_DIR = Path(__file__).resolve().parent


def _resolve_data_dir() -> Path:
    configured = os.getenv("DOCUMIND_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    if getattr(sys, "frozen", False):
        root = Path(os.getenv("LOCALAPPDATA", Path.home()))
        return root / "DocuMind AI" / "data"
    return BASE_DIR / "data"


DATA_DIR = _resolve_data_dir()
DB_PATH = DATA_DIR / "documind.db"
KEY_PATH = DATA_DIR / "master.key.dpapi"
TEXT_MARKER = "DME1:"
BLOB_MARKER = b"DME1"


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi(data: bytes, *, decrypt: bool) -> bytes:
    """Protect/unprotect a small key with the current Windows user's DPAPI."""
    if os.name != "nt":
        raise RuntimeError("DPAPI is available only on Windows")
    source_buffer = ctypes.create_string_buffer(data)
    source = _DATA_BLOB(len(data), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = _DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt32.CryptProtectData.argtypes = [ctypes.POINTER(_DATA_BLOB), ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(_DATA_BLOB)]
    crypt32.CryptProtectData.restype = ctypes.c_int
    crypt32.CryptUnprotectData.argtypes = [ctypes.POINTER(_DATA_BLOB), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(_DATA_BLOB)]
    crypt32.CryptUnprotectData.restype = ctypes.c_int
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    if decrypt:
        ok = crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output))
    else:
        ok = crypt32.CryptProtectData(ctypes.byref(source), "DocuMind AI local data key", None, None, None, 0, ctypes.byref(output))
    if not ok:
        raise OSError("Windows could not protect or unlock the DocuMind data key")
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel32.LocalFree(output.pbData)


def _load_master_key() -> bytes:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if KEY_PATH.exists():
        protected = KEY_PATH.read_bytes()
        if os.name == "nt":
            return _dpapi(protected, decrypt=True)
        # Non-Windows is used for isolated development tests only.
        if len(protected) != 32:
            raise RuntimeError("Invalid local encryption key")
        return protected

    key = secrets.token_bytes(32)
    stored = _dpapi(key, decrypt=False) if os.name == "nt" else key
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(KEY_PATH, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(stored)
        stream.flush()
        os.fsync(stream.fileno())
    return key


_MASTER_KEY: bytes | None = None


def _aes() -> AESGCM:
    global _MASTER_KEY
    if _MASTER_KEY is None:
        _MASTER_KEY = _load_master_key()
    return AESGCM(_MASTER_KEY)


def _encrypt_bytes(value: bytes, purpose: bytes) -> bytes:
    nonce = secrets.token_bytes(12)
    return BLOB_MARKER + nonce + _aes().encrypt(nonce, value, purpose)


def _decrypt_bytes(value: bytes, purpose: bytes) -> bytes:
    if not value.startswith(BLOB_MARKER):
        return value  # Legacy plaintext, encrypted during initialization.
    payload = value[len(BLOB_MARKER):]
    if len(payload) < 13:
        raise ValueError("Encrypted local data is damaged.")
    return _aes().decrypt(payload[:12], payload[12:], purpose)


def _encrypt_text(value: str) -> str:
    if value.startswith(TEXT_MARKER):
        return value
    encrypted = _encrypt_bytes(value.encode("utf-8"), b"document-content")
    return TEXT_MARKER + base64.b64encode(encrypted[len(BLOB_MARKER):]).decode("ascii")


def _decrypt_text(value: str | None) -> str:
    if not value:
        return ""
    if not value.startswith(TEXT_MARKER):
        return value
    payload = base64.b64decode(value[len(TEXT_MARKER):], validate=True)
    return _decrypt_bytes(BLOB_MARKER + payload, b"document-content").decode("utf-8")


@contextmanager
def get_connection():
    """Always close SQLite connections and commit or roll back atomically."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 30000")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 600_000).hex()


def initialize_database() -> None:
    # Initialize the key before touching encrypted rows.
    _aes()
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                page_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(documents)")}
        additions = {
            "file_data": "BLOB",
            "file_type": "TEXT",
            "file_size": "INTEGER NOT NULL DEFAULT 0",
            "user_id": "INTEGER REFERENCES users(id)",
        }
        for name, kind in additions.items():
            if name not in columns:
                connection.execute(f"ALTER TABLE documents ADD COLUMN {name} {kind}")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id)")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                username TEXT PRIMARY KEY COLLATE NOCASE,
                failures INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT
            )
        """)
        # Preserve legacy unowned rows; never silently assign one user's files to another.
        rows = connection.execute("SELECT id, content, file_data FROM documents").fetchall()
        for row in rows:
            content = row["content"] or ""
            file_data = row["file_data"]
            new_content = _encrypt_text(content)
            new_file = _encrypt_bytes(bytes(file_data), b"document-file") if file_data and not bytes(file_data).startswith(BLOB_MARKER) else file_data
            if new_content != content or new_file != file_data:
                connection.execute(
                    "UPDATE documents SET content = ?, file_data = ? WHERE id = ?",
                    (new_content, new_file, row["id"]),
                )
    # Reclaim legacy plaintext pages after the encryption migration.
    with get_connection() as connection:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("VACUUM")


def create_user(username: str, password: str):
    username = (username or "").strip()
    password = password or ""
    if len(username) < 3 or len(username) > 30 or not username.replace("_", "").isalnum():
        return False, "نام کاربری باید ۳ تا ۳۰ کاراکتر و فقط شامل حروف، اعداد و _ باشد."
    if len(password) < 12:
        return False, "رمز عبور باید حداقل ۱۲ کاراکتر باشد."
    if len(password) > 128:
        return False, "رمز عبور نمی‌تواند بیشتر از ۱۲۸ کاراکتر باشد."
    salt = secrets.token_bytes(16).hex()
    digest = hash_password(password, salt)
    try:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                (username, digest, salt),
            )
        return True, "حساب کاربری با موفقیت ساخته شد."
    except sqlite3.IntegrityError:
        return False, "این نام کاربری قبلاً ثبت شده است."


def authenticate_user(username: str, password: str):
    username = (username or "").strip()
    password = password or ""
    if not username or len(username) > 30 or len(password) > 128:
        return None
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        user = connection.execute(
            "SELECT id, username, password_hash, salt FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        attempt = connection.execute(
            "SELECT failures, locked_until FROM login_attempts WHERE username = ?",
            (username,),
        ).fetchone()
        if attempt and attempt["locked_until"]:
            try:
                if datetime.fromisoformat(attempt["locked_until"]) > now:
                    return None
            except ValueError:
                connection.execute("DELETE FROM login_attempts WHERE username = ?", (username,))
        if user is None:
            hash_password(password, "00112233445566778899aabbccddeeff")
            return None
        valid = secrets.compare_digest(hash_password(password, user["salt"]), user["password_hash"])
        if valid:
            connection.execute("DELETE FROM login_attempts WHERE username = ?", (username,))
            return {"id": user["id"], "username": user["username"]}
        failures = (attempt["failures"] if attempt else 0) + 1
        locked_until = (now + timedelta(minutes=15)).isoformat() if failures >= 5 else None
        connection.execute("""
            INSERT INTO login_attempts (username, failures, locked_until)
            VALUES (?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                failures = excluded.failures,
                locked_until = excluded.locked_until
        """, (username, failures, locked_until))
    return None


def get_documents(user_id):
    if user_id is None:
        raise ValueError("user_id is required")
    columns = "id, filename, page_count, created_at, file_type, file_size"
    with get_connection() as connection:
        return connection.execute(
            f"SELECT {columns} FROM documents WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()


def get_document_contents(user_id, document_id=None):
    if user_id is None:
        raise ValueError("user_id is required")
    with get_connection() as connection:
        if document_id is None:
            rows = connection.execute(
                "SELECT id, filename, content FROM documents WHERE user_id = ? ORDER BY id DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT id, filename, content FROM documents WHERE id = ? AND user_id = ?",
                (document_id, user_id),
            ).fetchall()
    return [{"id": row["id"], "filename": row["filename"], "content": _decrypt_text(row["content"])} for row in rows]


def count_readable_documents(user_id, document_id=None):
    if user_id is None:
        raise ValueError("user_id is required")
    docs = get_document_contents(user_id, document_id)
    return sum(bool(item["content"].strip()) for item in docs)


def get_document(document_id, user_id):
    if user_id is None:
        raise ValueError("user_id is required")
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM documents WHERE id = ? AND user_id = ?",
            (document_id, user_id),
        ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["content"] = _decrypt_text(result.get("content"))
    if result.get("file_data"):
        result["file_data"] = _decrypt_bytes(bytes(result["file_data"]), b"document-file")
    return result


def add_document(filename, content, user_id, page_count=0, file_data=None, file_type=None, file_size=0):
    if user_id is None:
        raise ValueError("user_id is required")
    encrypted_content = _encrypt_text(content or "")
    encrypted_file = _encrypt_bytes(bytes(file_data), b"document-file") if file_data else None
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO documents (filename, content, page_count, user_id, file_data, file_type, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (filename, encrypted_content, page_count, user_id, encrypted_file, file_type, file_size))
        return cursor.lastrowid


def delete_document(document_id, user_id):
    if user_id is None:
        raise ValueError("user_id is required")
    with get_connection() as connection:
        connection.execute("DELETE FROM documents WHERE id = ? AND user_id = ?", (document_id, user_id))


def like_pattern(query):
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def search_documents(query, user_id):
    if user_id is None:
        raise ValueError("user_id is required")
    query = (query or "").strip().casefold()
    if not query:
        return []
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, filename, content, page_count, created_at, file_type, file_size FROM documents WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    matches = []
    for row in rows:
        content = _decrypt_text(row["content"])
        if query in row["filename"].casefold() or query in content.casefold():
            matches.append({
                "id": row["id"],
                "filename": row["filename"],
                "page_count": row["page_count"],
                "created_at": row["created_at"],
                "file_type": row["file_type"],
                "file_size": row["file_size"],
            })
    return matches
