"""Security helpers for local document ingestion."""
from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZipFile
import re

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 5000
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100

SUPPORTED_FORMATS = {".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md", ".csv", ".rtf", ".log"}


def sanitize_filename(filename: str) -> str:
    """Keep a display-only basename; never trust client supplied paths."""
    name = Path(str(filename or "")).name.replace("\\", "_").replace("/", "_")
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip(" .")
    if not name or len(name) > 180:
        raise ValueError("نام فایل معتبر نیست یا بیش از حد طولانی است.")
    return name


def validate_upload(filename: str, data: bytes) -> tuple[str, int]:
    """Apply conservative size, extension and container-signature checks."""
    name = sanitize_filename(filename)
    extension = Path(name).suffix.lower()
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise ValueError("فایل خالی یا نامعتبر است.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("حداکثر حجم مجاز هر فایل ۲۵ مگابایت است.")

    if extension == ".pdf":
        if not bytes(data[:1024]).lstrip().startswith(b"%PDF-"):
            raise ValueError("ساختار فایل PDF معتبر نیست.")
    elif extension in {".docx", ".xlsx", ".pptx"}:
        try:
            with ZipFile(__import__("io").BytesIO(data)) as archive:
                infos = archive.infolist()
                if len(infos) > MAX_ARCHIVE_ENTRIES:
                    raise ValueError("تعداد اجزای فایل فشرده بیش از حد مجاز است.")
                total = sum(info.file_size for info in infos)
                if total > MAX_UNCOMPRESSED_BYTES:
                    raise ValueError("حجم بازشده فایل بیش از حد مجاز است.")
                for info in infos:
                    if info.flag_bits & 0x1:
                        raise ValueError("فایل‌های فشرده رمزگذاری‌شده پشتیبانی نمی‌شوند.")
                    if info.file_size > 1024 * 1024 and info.compress_size == 0:
                        raise ValueError("ساختار فشرده‌سازی فایل معتبر نیست.")
                    if info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                        raise ValueError("نسبت فشرده‌سازی فایل بیش از حد مجاز است.")
                required = {
                    ".docx": "word/document.xml",
                    ".xlsx": "xl/workbook.xml",
                    ".pptx": "ppt/presentation.xml",
                }[extension]
                if "[Content_Types].xml" not in archive.namelist() or required not in archive.namelist():
                    raise ValueError("ساختار سند Office معتبر نیست.")
        except BadZipFile as error:
            raise ValueError("فایل Office خراب یا نامعتبر است.") from error
    elif extension in {".txt", ".md", ".csv", ".rtf", ".log"}:
        if bytes([0]) in bytes(data[:8192]):
            raise ValueError("فایل متنی دارای داده باینری نامعتبر است.")
    # Unknown extensions may still be stored, but are never passed to an extractor.
    return name, len(data)
