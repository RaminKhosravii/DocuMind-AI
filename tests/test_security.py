import unittest
from io import BytesIO
from zipfile import ZipFile

from security import validate_upload, sanitize_filename, MAX_UPLOAD_BYTES


class UploadSecurityTests(unittest.TestCase):
    def test_rejects_empty_file(self):
        with self.assertRaises(ValueError):
            validate_upload("empty.txt", b"")

    def test_rejects_oversized_file(self):
        with self.assertRaises(ValueError):
            validate_upload("large.txt", b"a" * (MAX_UPLOAD_BYTES + 1))

    def test_rejects_fake_pdf(self):
        with self.assertRaises(ValueError):
            validate_upload("fake.pdf", b"not a pdf")

    def test_accepts_pdf_signature(self):
        name, size = validate_upload("report.pdf", b"%PDF-1.7\nbody")
        self.assertEqual(name, "report.pdf")
        self.assertGreater(size, 0)

    def test_rejects_invalid_office_zip(self):
        with self.assertRaises(ValueError):
            validate_upload("report.docx", b"not a zip")

    def test_accepts_minimal_docx_container(self):
        stream = BytesIO()
        with ZipFile(stream, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("word/document.xml", "<document/>")
        name, _ = validate_upload("report.docx", stream.getvalue())
        self.assertEqual(name, "report.docx")

    def test_sanitizes_control_characters(self):
        name = sanitize_filename("report\x00.txt")
        self.assertEqual(name, "report.txt")


if __name__ == "__main__":
    unittest.main()
