"""Vercel endpoint for the supplied, editable HWPX originals.

Only the three originals used in the administrator screen are read.  Nothing
uploaded by a citizen is stored by this function.
"""
from datetime import datetime
from io import BytesIO
import json
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parent.parent
NS = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
ET.register_namespace("hp", NS["hp"])


def supplied_form(kind):
    names = {
        "draft": "\uc815\ubcf4\ud1b5\uc2e0\uc124\ube44 \uc720\uc9c0\ubcf4\uc218 \uad00\ub9ac\uc790 \uc120\uc784 \uc2e0\uace0\uc11c \uc218\ub9ac \uc54c\ub9bc(TEST) [\uc8fc\uc18c_\uac74\ucd95\ubb3c\uba85].hwpx",
        "form12": "\uc815\ubcf4\ud1b5\uc2e0\uc124\ube44 \uc720\uc9c0\ubcf4\uc218\u318d\uad00\ub9ac\uc790 \uc120\uc784\uc2e0\uace0\uc99d\uba85\uc11c \ubc1c\uae09\uc2e0\uccad\uc11c.hwpx",
    }
    path = ROOT / names[kind]
    if not path.is_file():
        raise FileNotFoundError(path.name)
    return path


def cell_at(table, col, row):
    for cell in table.findall(".//hp:tc", NS):
        address = cell.find("hp:cellAddr", NS)
        if address is not None and address.get("colAddr") == str(col) and address.get("rowAddr") == str(row):
            return cell
    raise ValueError(f"missing source-form cell ({col}, {row})")


def put(table, col, row, value):
    if value in (None, ""):
        return
    cell = cell_at(table, col, row)
    text = cell.find(".//hp:t", NS)
    if text is None:
        run = cell.find(".//hp:run", NS)
        if run is None:
            raise ValueError(f"missing source-form run ({col}, {row})")
        text = ET.SubElement(run, f"{{{NS['hp']}}}t")
        text.text = str(value)
    else:
        text.text = (text.text or "") + "\n" + str(value)


def put_area(table, value):
    if value in (None, ""):
        return
    cell = cell_at(table, 2, 8)
    texts = cell.findall(".//hp:t", NS)
    unit = next((item for item in texts if "m" in (item.text or "")), texts[-1])
    unit.text = " " * 23 + str(value) + " m²"


def put_date(table, value):
    if not value:
        return
    year, month, day = value.split("-")
    text = cell_at(table, 0, 13).find(".//hp:t", NS)
    text.text = f"{year}      \ub144    {int(month)}      \uc6d4    {int(day)}      \uc77c"


def fill_certificate(data):
    source = supplied_form("form12")
    fields = ((1, 4, "ownerName"), (8, 4, "ownerRepresentative"),
              (1, 5, "businessNumber"), (8, 5, "ownerPhone"),
              (1, 6, "ownerAddress"), (8, 8, "buildingUse"),
              (1, 9, "buildingAddress"), (1, 11, "certificateReason"),
              (7, 11, "certificateCopies"), (0, 14, "ownerName"))
    output = BytesIO()
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as result:
        for info in original.infolist():
            content = original.read(info.filename)
            if info.filename == "Contents/section0.xml":
                root = ET.fromstring(content)
                table = root.findall(".//hp:tbl", NS)[0]
                for col, row, name in fields:
                    put(table, col, row, data.get(name, ""))
                put_area(table, data.get("buildingArea", ""))
                put_date(table, data.get("reportDate", ""))
                content = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            result.writestr(info, content)
    return output.getvalue()


def preview(kind):
    template = supplied_form("draft" if kind == "draft" else "form12")
    with zipfile.ZipFile(template) as archive:
        return archive.read("Preview/PrvImage.png")


def app(environ, start_response):
    """A dependency-free WSGI application understood directly by Vercel."""
    try:
        if environ.get("REQUEST_METHOD") == "OPTIONS":
            start_response("204 No Content", [("Access-Control-Allow-Origin", "*"),
                                                ("Access-Control-Allow-Headers", "Content-Type")])
            return [b""]
        if environ.get("REQUEST_METHOD") != "POST":
            start_response("405 Method Not Allowed", [("Content-Type", "text/plain")])
            return [b"POST only"]
        path = environ.get("PATH_INFO", "")
        if "/api/" in path:
            path = path[path.index("/api/") + 4:]
        length = int(environ.get("CONTENT_LENGTH") or 0)
        data = json.loads(environ["wsgi.input"].read(length) or b"{}")
        if path in ("/admin/preview/draft", "/admin/preview/certificate"):
            body, content_type = preview("draft" if path.endswith("draft") else "certificate"), "image/png"
        elif path == "/admin/document/draft":
            body, content_type = supplied_form("draft").read_bytes(), "application/vnd.hancom.hwpx"
        elif path == "/admin/document/certificate":
            data["reportDate"] = datetime.now().date().isoformat()
            body, content_type = fill_certificate(data), "application/vnd.hancom.hwpx"
        else:
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            return [b"unknown API route"]
        start_response("200 OK", [("Content-Type", content_type), ("Content-Length", str(len(body))),
                                    ("Cache-Control", "no-store")])
        return [body]
    except Exception as error:
        message = f"API error: {error}".encode("utf-8", "replace")
        start_response("500 Internal Server Error", [("Content-Type", "text/plain; charset=utf-8"),
                                                       ("Content-Length", str(len(message)))])
        return [message]


application = app
