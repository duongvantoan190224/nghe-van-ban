import io
import json
import os
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pypdf import PdfReader


FOLDER_ID = "1G9hMq9r0g7KJoz09n61SqTTcXLiE1akl"
ORIGIN = "https://duongvantoan190224.github.io"
API = "https://www.googleapis.com/drive/v3/files"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF = "application/pdf"
MAX_FILE = 20 * 1024 * 1024
MAX_XML = 50 * 1024 * 1024
WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
API_KEY = os.environ.get("GOOGLE_DRIVE_API_KEY", "")


class ProxyError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(NoRedirect())


def drive_request(path="", params=None, limit=MAX_FILE):
    url = API + path + "?" + urllib.parse.urlencode(params or {})
    request = urllib.request.Request(url, headers={"X-Goog-Api-Key": API_KEY})
    try:
        with OPENER.open(request, timeout=30) as response:
            data = response.read(limit + 1)
            if len(data) > limit:
                raise ProxyError(413, "Dữ liệu vượt quá giới hạn cho phép.")
            return data
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise ProxyError(404, "Không tìm thấy tài liệu.") from error
        raise ProxyError(502, "Không thể truy cập Google Drive.") from error
    except ProxyError:
        raise
    except (OSError, ValueError) as error:
        raise ProxyError(502, "Không thể truy cập Google Drive.") from error


def drive_json(path="", params=None):
    try:
        return json.loads(drive_request(path, params, 4 * 1024 * 1024))
    except (ValueError, UnicodeDecodeError) as error:
        raise ProxyError(502, "Dữ liệu Google Drive không hợp lệ.") from error


def supported(item):
    name = item.get("name", "").lower()
    return ((item.get("mimeType") == DOCX and name.endswith(".docx"))
            or (item.get("mimeType") == PDF and name.endswith(".pdf")))


def documents(query):
    params = {
        "q": f"'{FOLDER_ID}' in parents and trashed = false",
        "fields": "nextPageToken,files(id,name,mimeType)",
        "pageSize": 1000,
    }
    results = []
    seen_tokens = set()
    while True:
        page = drive_json(params=params)
        for item in page.get("files", []):
            if supported(item) and query.casefold() in item["name"].casefold():
                results.append({"id": item["id"], "title": item["name"]})
        token = page.get("nextPageToken")
        if not token:
            break
        if token in seen_tokens:
            raise ProxyError(502, "Không thể phân trang Google Drive.")
        seen_tokens.add(token)
        params["pageToken"] = token
    return sorted(results, key=lambda item: item["title"].casefold())


def clean_text(text):
    text = unicodedata.normalize("NFC", text).replace("\u00a0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def docx_text(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        info = archive.getinfo("word/document.xml")
        if info.file_size > MAX_XML:
            raise ProxyError(413, "Nội dung tài liệu quá lớn.")
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
        raise ProxyError(422, "PDF được mã hóa không được hỗ trợ.")
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


def document_text(file_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", file_id):
        raise ProxyError(404, "Không tìm thấy tài liệu.")
    path = "/" + file_id
    item = drive_json(path, {"fields": "id,name,mimeType,parents,trashed,size"})
    if item.get("trashed") or FOLDER_ID not in item.get("parents", []) or not supported(item):
        raise ProxyError(404, "Không tìm thấy tài liệu.")
    try:
        size = int(item.get("size", 0))
    except (TypeError, ValueError) as error:
        raise ProxyError(502, "Kích thước tệp không hợp lệ.") from error
    if size > MAX_FILE:
        raise ProxyError(413, "Tệp vượt quá giới hạn 20 MB.")
    data = drive_request(path, {"alt": "media"})
    try:
        text = docx_text(data) if item["mimeType"] == DOCX else pdf_text(data)
    except ProxyError:
        raise
    except Exception as error:
        raise ProxyError(422, "Không thể trích xuất văn bản từ tệp.") from error
    if not text:
        raise ProxyError(422, "Tệp không có văn bản; PDF ảnh chưa được hỗ trợ OCR.")
    return text


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, result):
        data = json.dumps(result, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if self.headers.get("Origin") == ORIGIN:
            self.send_header("Access-Control-Allow-Origin", ORIGIN)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        origin = self.headers.get("Origin")
        if origin and origin != ORIGIN:
            self.send_json(403, {"error": "Origin không được phép."})
            return
        try:
            url = urllib.parse.urlsplit(self.path)
            if url.path == "/documents":
                query = urllib.parse.parse_qs(url.query).get("q", [""])[0].strip()
                if len(query) > 200:
                    raise ProxyError(400, "Từ khóa quá dài.")
                self.send_json(200, {"results": documents(query)})
            elif url.path.startswith("/documents/"):
                self.send_json(200, {"text": document_text(url.path[len("/documents/"):])})
            else:
                raise ProxyError(404, "Không tìm thấy đường dẫn.")
        except ProxyError as error:
            self.send_json(error.status, {"error": error.message})

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    if not API_KEY:
        raise SystemExit("Hãy đặt GOOGLE_DRIVE_API_KEY.")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
