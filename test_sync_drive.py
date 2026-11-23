import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import sync_drive


def make_docx():
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("word/document.xml", """\
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>Tiếng Việt</w:t></w:r></w:p>
  <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Nội dung bảng</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
  </w:body>
</w:document>""")
        archive.writestr("word/header1.xml", "Không xuất header")
    return data.getvalue()


class SyncTests(unittest.TestCase):
    def test_docx_body_and_tables_without_header(self):
        self.assertEqual(sync_drive.docx_text(make_docx()), "Tiếng Việt\nNội dung bảng")

    def test_pdf_repeated_edges_and_single_line_pages(self):
        class Page:
            def __init__(self, text):
                self.text = text

            def extract_text(self):
                return self.text

        class Reader:
            is_encrypted = False
            pages = [Page("Tiêu đề\nMột\nChân trang"),
                     Page("Tiêu đề\nHai\nChân trang"),
                     Page("Tiêu đề\nBa\nChân trang"),
                     Page("Riêng")]

        with patch.object(sync_drive, "PdfReader", return_value=Reader()):
            self.assertEqual(sync_drive.pdf_text(b""), "Một\n\nHai\n\nBa\n\nRiêng")

    def test_pagination_filters_and_rejects_repeated_token(self):
        pages = [
            {"files": [{"id": "b", "name": "B.pdf", "mimeType": sync_drive.PDF},
                       {"id": "x", "name": "x.txt", "mimeType": "text/plain"}],
             "nextPageToken": "next"},
            {"files": [{"id": "a", "name": "A.docx", "mimeType": sync_drive.DOCX}]},
        ]
        with patch.object(sync_drive, "drive_request",
                          side_effect=[json.dumps(page).encode() for page in pages]):
            self.assertEqual([x["id"] for x in sync_drive.documents(None)], ["a", "b"])
        pages[1]["nextPageToken"] = "next"
        with patch.object(sync_drive, "drive_request",
                          side_effect=[json.dumps(page).encode() for page in pages]):
            with self.assertRaises(ValueError):
                sync_drive.documents(None)

    def test_sync_writes_and_removes_stale_only_after_success(self):
        items = [{"id": "abc_1", "name": "Tên.docx", "mimeType": sync_drive.DOCX, "size": "30"}]
        folder = json.dumps({"id": sync_drive.FOLDER_ID,
                             "mimeType": "application/vnd.google-apps.folder"}).encode()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "documents").mkdir()
            (root / "documents" / "old.json").write_text("old", encoding="utf-8")
            (root / "documents.json").write_text("old index", encoding="utf-8")
            with patch.object(sync_drive, "documents", return_value=items):
                with patch.object(sync_drive, "drive_request", side_effect=[folder, make_docx()]):
                    sync_drive.sync(None, root)
            self.assertFalse((root / "documents" / "old.json").exists())
            self.assertEqual(json.loads((root / "documents.json").read_text())["results"],
                             [{"id": "abc_1", "title": "Tên.docx"}])
            self.assertEqual(json.loads((root / "documents" / "abc_1.json").read_text())["text"],
                             "Tiếng Việt\nNội dung bảng")

    def test_sync_skips_invalid_document_and_processes_valid_documents(self):
        items = [
            {"id": "bad_1", "name": "Scan.pdf", "mimeType": sync_drive.PDF, "size": "30"},
            {"id": "good_1", "name": "Tốt.docx", "mimeType": sync_drive.DOCX, "size": "40"},
        ]
        folder = json.dumps({"id": sync_drive.FOLDER_ID,
                             "mimeType": "application/vnd.google-apps.folder"}).encode()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(sync_drive, "documents", return_value=items):
                with patch.object(sync_drive, "drive_request",
                                  side_effect=[folder, b"invalid PDF", make_docx()]):
                    with self.assertLogs(level="WARNING") as logs:
                        sync_drive.sync(None, root)
            warning = "\n".join(logs.output)
            self.assertIn("Scan.pdf", warning)
            self.assertIn("bad_1", warning)
            self.assertEqual(json.loads((root / "documents.json").read_text())["results"],
                             [{"id": "good_1", "title": "Tốt.docx"}])
            self.assertFalse((root / "documents" / "bad_1.json").exists())
            self.assertTrue((root / "documents" / "good_1.json").exists())

    def test_inaccessible_folder_does_not_replace_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "documents.json").write_text("old", encoding="utf-8")
            with patch.object(sync_drive, "drive_request", side_effect=ValueError("404")):
                with self.assertRaises(ValueError):
                    sync_drive.sync(None, root)
            self.assertEqual((root / "documents.json").read_text(), "old")

    def test_rejects_unsafe_id(self):
        page = {"files": [{"id": "../escape", "name": "a.pdf", "mimeType": sync_drive.PDF}]}
        with patch.object(sync_drive, "drive_request", return_value=json.dumps(page).encode()):
            with self.assertRaises(ValueError):
                sync_drive.documents(None)


if __name__ == "__main__":
    unittest.main()
