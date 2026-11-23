import io
import json
import os
import re
import shutil
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from pypdf import PdfReader

FOLDER_ID = "1G9hMq9r0g7KJoz09n61SqTTcXLiE1akl"
API = "https://www.googleapis.com/drive/v3/files"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF = "application/pdf"
MAX_FILE = 20 * 1024 * 1024
MAX_XML = 50 * 1024 * 1024
WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class DocumentError(Exception):
    pass


def drive_request(session, path="", params=None, limit=MAX_FILE):
    with session.get(API + path, params=params, timeout=60, stream=True,
                     allow_redirects=False) as response:
        if response.status_code != 200:
            raise ValueError(f"Google Drive trả về HTTP {response.status_code}.")
        chunks = []
        size = 0
        for chunk in response.iter_content(chunk_size=65536):
            size += len(chunk)
            if size > limit:
                raise ValueError("Dữ liệu vượt quá giới hạn cho phép.")
            chunks.append(chunk)
        return b"".join(chunks)


def documents(session):
    params = {
        "q": f"'{FOLDER_ID}' in parents and trashed = false",
        "fields": "nextPageToken,files(id,name,mimeType,size)",
        "pageSize": 1000,
    }
    results = []
    seen_tokens = set()
    seen_ids = set()
    while True:
        page = json.loads(drive_request(session, params=params, limit=4 * 1024 * 1024))
        if not isinstance(page.get("files"), list):
            raise ValueError("Danh sách Google Drive không hợp lệ.")
        for item in page["files"]:
            name = item.get("name", "")
            mime = item.get("mimeType")
            if not ((mime == DOCX and name.lower().endswith(".docx"))
                    or (mime == PDF and name.lower().endswith(".pdf"))):
                continue
            file_id = item.get("id", "")
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", file_id) or file_id in seen_ids:
                raise ValueError("ID tài liệu không hợp lệ hoặc bị trùng.")
            seen_ids.add(file_id)
            results.append(item)
        token = page.get("nextPageToken")
        if not token:
            break
        if not isinstance(token, str) or token in seen_tokens:
            raise ValueError("Không thể phân trang Google Drive.")
        seen_tokens.add(token)
        params["pageToken"] = token
    return sorted(results, key=lambda item: (item["name"].casefold(), item["id"]))


def clean_text(text):
    text = unicodedata.normalize("NFC", text).replace("\u00a0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def docx_text(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        info = archive.getinfo("word/document.xml")
        if info.file_size > MAX_XML:
            raise ValueError("Nội dung tài liệu quá lớn.")
        root = ET.fromstring(archive.read(info))
    body = root.find(WORD + "body")
    if body is None:
        return ""
    paragraphs = []
    for paragraph in body.iter(WORD + "p"):
        parts = []

        def append_text(element):
            if element is not paragraph and element.tag == WORD + "p":
                return
            if element.tag == WORD + "t":
                parts.append(element.text or "")
            elif element.tag == WORD + "tab":
                parts.append("\t")
            elif element.tag in (WORD + "br", WORD + "cr"):
                parts.append("\n")
            for child in element:
                append_text(child)

        append_text(paragraph)
        paragraphs.append("".join(parts))
    return clean_text("\n".join(paragraphs))


def pdf_text(data):
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ValueError("PDF được mã hóa không được hỗ trợ.")
    pages = [clean_text(page.extract_text() or "").splitlines() for page in reader.pages]
    if len(pages) >= 3:
        first = Counter(page[0] for page in pages if len(page) > 1 and page[0])
        last = Counter(page[-1] for page in pages if len(page) > 1 and page[-1])
        threshold = max(3, (len(pages) * 2 + 2) // 3)
        for page in pages:
            if len(page) > 1 and first[page[0]] >= threshold:
                page.pop(0)
            if len(page) > 1 and last[page[-1]] >= threshold:
                page.pop()
    return clean_text("\n\n".join("\n".join(page) for page in pages))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sync(session, root):
    folder = json.loads(drive_request(session, "/" + FOLDER_ID,
                                      {"fields": "id,mimeType,trashed"},
                                      limit=4 * 1024 * 1024))
    if (folder.get("id") != FOLDER_ID
            or folder.get("mimeType") != "application/vnd.google-apps.folder"
            or folder.get("trashed")):
        raise ValueError("Không thể truy cập thư mục Google Drive.")
    items = documents(session)
    with tempfile.TemporaryDirectory() as temporary:
        staging = Path(temporary)
        results = []
        for item in items:
            file_id = item["id"]
            try:
                size = int(item.get("size", 0))
                if size < 0 or size > MAX_FILE:
                    raise ValueError("Tệp vượt quá giới hạn 20 MB.")
                data = drive_request(session, "/" + file_id, {"alt": "media"})
                text = docx_text(data) if item["mimeType"] == DOCX else pdf_text(data)
                if not text:
                    raise ValueError("Không có văn bản; PDF ảnh chưa được hỗ trợ OCR.")
            except Exception:
                raise DocumentError(f"Không thể xử lý tài liệu ID {file_id}. "
                                    "Kiểm tra định dạng, kích thước và lớp văn bản.") from None
            write_json(staging / (file_id + ".json"), {"text": text})
            results.append({"id": file_id, "title": item["name"]})
        target = root / "documents"
        target.mkdir(exist_ok=True)
        for path in target.glob("*.json"):
            path.unlink()
        for path in staging.iterdir():
            shutil.copyfile(path, target / path.name)
        write_json(root / "documents.json", {"results": results})
    print(f"Đã đồng bộ {len(results)} tài liệu.")


def main():
    try:
        info = json.loads(os.environ["NGHE_VB"])
        if info.get("token_uri") != "https://oauth2.googleapis.com/token":
            raise ValueError("token_uri không hợp lệ.")
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/drive.readonly"])
        with AuthorizedSession(credentials) as session:
            sync(session, Path(__file__).resolve().parent)
    except DocumentError as error:
        raise SystemExit(str(error)) from None
    except Exception:
        raise SystemExit("Đồng bộ thất bại. Kiểm tra secret NGHE_VB, quyền Drive và định dạng tài liệu.") from None


if __name__ == "__main__":
    main()
