import sqlite3
import hashlib
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "documind.db"


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database():
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

        columns = connection.execute(
            "PRAGMA table_info(documents)"
        ).fetchall()

        existing_columns = {
            column["name"] for column in columns
        }

        new_columns = {
            "file_data": "BLOB",
            "file_type": "TEXT",
            "file_size": "INTEGER NOT NULL DEFAULT 0",
        }

        for column_name, column_type in new_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    f"ALTER TABLE documents ADD COLUMN "
                    f"{column_name} {column_type}"
                )

        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(documents)"
            ).fetchall()
        }

        if "user_id" not in columns:
            connection.execute("""
                ALTER TABLE documents
                ADD COLUMN user_id INTEGER REFERENCES users(id)
            """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_user_id
            ON documents(user_id)
        """)


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        600_000,
    ).hex()


def create_user(username, password):
    username = username.strip()

    if len(username) < 3:
        return False, "نام کاربری باید حداقل ۳ کاراکتر باشد."

    if len(username) > 30:
        return False, "نام کاربری حداکثر باید ۳۰ کاراکتر باشد."

    if not username.replace("_", "").isalnum():
        return False, "نام کاربری فقط می‌تواند شامل حروف، اعداد و _ باشد."

    if len(password) < 8:
        return False, "رمز عبور باید حداقل ۸ کاراکتر باشد."

    salt = secrets.token_bytes(16).hex()
    password_hash = hash_password(password, salt)

    try:
        with get_connection() as connection:
            connection.execute("""
                INSERT INTO users (username, password_hash, salt)
                VALUES (?, ?, ?)
            """, (username, password_hash, salt))

        return True, "حساب کاربری با موفقیت ساخته شد."

    except sqlite3.IntegrityError:
        return False, "این نام کاربری قبلاً ثبت شده است."


def authenticate_user(username, password):
    with get_connection() as connection:
        user = connection.execute("""
            SELECT id, username, password_hash, salt
            FROM users
            WHERE username = ?
        """, (username.strip(),)).fetchone()

    if user is None:
        return None

    entered_hash = hash_password(password, user["salt"])

    if secrets.compare_digest(
        entered_hash,
        user["password_hash"],
    ):
        return {
            "id": user["id"],
            "username": user["username"],
        }

    return None


def get_documents(user_id=None):
    columns = "id, filename, page_count, created_at, file_type, file_size"

    with get_connection() as connection:
        if user_id is None:
            return connection.execute(f"""
                SELECT {columns}
                FROM documents
                ORDER BY id DESC
            """).fetchall()

        return connection.execute(f"""
            SELECT {columns}
            FROM documents
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,)).fetchall()


def get_document_contents(user_id, document_id=None):
    """متن سندها را بدون فایل اصلی برمی‌گرداند."""

    with get_connection() as connection:
        if document_id is None:
            return connection.execute("""
                SELECT id, filename, content
                FROM documents
                WHERE user_id = ?
                ORDER BY id DESC
            """, (user_id,)).fetchall()

        return connection.execute("""
            SELECT id, filename, content
            FROM documents
            WHERE id = ? AND user_id = ?
        """, (document_id, user_id)).fetchall()


def count_readable_documents(user_id, document_id=None):
    with get_connection() as connection:
        if document_id is None:
            row = connection.execute("""
                SELECT COUNT(*) AS total
                FROM documents
                WHERE user_id = ?
                  AND content IS NOT NULL
                  AND TRIM(content) != ''
            """, (user_id,)).fetchone()
        else:
            row = connection.execute("""
                SELECT COUNT(*) AS total
                FROM documents
                WHERE id = ? AND user_id = ?
                  AND content IS NOT NULL
                  AND TRIM(content) != ''
            """, (document_id, user_id)).fetchone()

    return row["total"]


def get_document(document_id, user_id=None):
    with get_connection() as connection:
        if user_id is None:
            return connection.execute("""
                SELECT *
                FROM documents
                WHERE id = ?
            """, (document_id,)).fetchone()

        return connection.execute("""
            SELECT *
            FROM documents
            WHERE id = ? AND user_id = ?
        """, (document_id, user_id)).fetchone()


def add_document(
    filename,
    content,
    page_count=0,
    user_id=None,
    file_data=None,
    file_type=None,
    file_size=0
):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO documents (
                filename,
                content,
                page_count,
                user_id,
                file_data,
                file_type,
                file_size
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            filename,
            content,
            page_count,
            user_id,
            file_data,
            file_type,
            file_size
        ))

        return cursor.lastrowid


def delete_document(document_id, user_id=None):
    with get_connection() as connection:
        if user_id is None:
            connection.execute("""
                DELETE FROM documents WHERE id = ?
            """, (document_id,))
        else:
            connection.execute("""
                DELETE FROM documents
                WHERE id = ? AND user_id = ?
            """, (document_id, user_id))


def like_pattern(query):
    """عبارت جست‌وجو را برای LIKE امن می‌کند تا % و _ عادی بمانند."""

    escaped = (
        query.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    return f"%{escaped}%"


def search_documents(query, user_id=None):
    query = query.strip()

    if not query:
        return []

    pattern = like_pattern(query)
    columns = "id, filename, page_count, created_at, file_type, file_size"

    with get_connection() as connection:
        if user_id is None:
            return connection.execute(f"""
                SELECT {columns}
                FROM documents
                WHERE content LIKE ? ESCAPE '\\'
                   OR filename LIKE ? ESCAPE '\\'
                ORDER BY id DESC
            """, (pattern, pattern)).fetchall()

        return connection.execute(f"""
            SELECT {columns}
            FROM documents
            WHERE user_id = ?
              AND (
                    content LIKE ? ESCAPE '\\'
                    OR filename LIKE ? ESCAPE '\\'
                  )
            ORDER BY id DESC
        """, (user_id, pattern, pattern)).fetchall()