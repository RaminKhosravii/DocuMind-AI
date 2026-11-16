from pathlib import Path
from io import BytesIO
import csv

import pymupdf
from docx import Document as WordDocument
from openpyxl import load_workbook
from pptx import Presentation
from striprtf.striprtf import rtf_to_text


def extract_text(file_name, file_bytes):
    """
    متن فایل‌های پشتیبانی‌شده را استخراج می‌کند.
    فایل‌های ناشناخته بدون استخراج متن، قابل ذخیره‌سازی هستند.
    """

    extension = Path(file_name).suffix.lower()

    try:
        # PDF
        if extension == ".pdf":
            with pymupdf.open(stream=file_bytes, filetype="pdf") as pdf:
                text = "\n".join(page.get_text() for page in pdf)
                return text, pdf.page_count

        # Word
        elif extension == ".docx":
            document = WordDocument(BytesIO(file_bytes))
            parts = [
                paragraph.text.strip()
                for paragraph in document.paragraphs
                if paragraph.text.strip()
            ]

            for table_number, table in enumerate(document.tables, start=1):
                parts.append(f"جدول {table_number}")

                for row in table.rows:
                    cells = []
                    seen = set()

                    for cell in row.cells:
                        cell_text = cell.text.strip()

                        if cell_text and cell_text not in seen:
                            seen.add(cell_text)
                            cells.append(cell_text)

                    if cells:
                        parts.append(" | ".join(cells))

            return "\n".join(parts), 0

        # Excel
        elif extension == ".xlsx":
            workbook = load_workbook(
                BytesIO(file_bytes),
                read_only=True,
                data_only=True
            )

            parts = []

            for sheet in workbook.worksheets:
                parts.append(f"برگه: {sheet.title}")

                for row in sheet.iter_rows(values_only=True):
                    values = [
                        str(value)
                        for value in row
                        if value is not None
                    ]

                    if values:
                        parts.append(" | ".join(values))

            workbook.close()
            return "\n".join(parts), 0

        # PowerPoint
        elif extension == ".pptx":
            presentation = Presentation(BytesIO(file_bytes))
            parts = []

            for slide_number, slide in enumerate(
                presentation.slides,
                start=1
            ):
                parts.append(f"اسلاید {slide_number}")

                for shape in slide.shapes:
                    if shape.has_text_frame and shape.text.strip():
                        parts.append(shape.text)

                if slide.has_notes_slide:
                    notes = slide.notes_slide.notes_text_frame.text.strip()

                    if notes:
                        parts.append(notes)

            return "\n".join(parts), len(presentation.slides)

        # Text
        elif extension in {".txt", ".md", ".log"}:
            text = file_bytes.decode("utf-8", errors="replace")
            return text, 0

        # CSV
        elif extension == ".csv":
            decoded_text = file_bytes.decode(
                "utf-8-sig",
                errors="replace"
            )

            rows = csv.reader(decoded_text.splitlines())
            text = "\n".join(
                " | ".join(row)
                for row in rows
            )

            return text, 0

        # Rich Text Format
        elif extension == ".rtf":
            decoded_text = file_bytes.decode(
                "utf-8",
                errors="replace"
            )

            return rtf_to_text(decoded_text), 0

        # نوع ناشناخته یا پشتیبانی‌نشده
        return "", 0

    except Exception as error:
        raise ValueError(
            f"استخراج متن از فایل «{file_name}» ناموفق بود: {error}"
        ) from error


def get_file_type(file_name):
    """پسوند فایل را به‌عنوان نوع فایل برمی‌گرداند."""
    return Path(file_name).suffix.lower() or "unknown"