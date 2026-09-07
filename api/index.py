"""Vercel endpoint for the supplied, editable HWPX originals.

Only the three originals used in the administrator screen are read.  Nothing
uploaded by a citizen is stored by this function.
"""
from datetime import datetime
from io import BytesIO
from base64 import b64encode
from html import escape
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
        "form10": "\uc815\ubcf4\ud1b5\uc2e0\uc124\ube44 \uc720\uc9c0\ubcf4\uc218\u318d\uad00\ub9ac\uc790 \uc120\uc784\u318d\ud574\uc784 \uc2e0\uace0\uc11c.hwpx",
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


def fill_form10(data):
    fields=((8,4,"ownerName"),(20,4,"ownerRepresentative"),(34,4,"businessNumber"),(8,5,"ownerAddress"),(34,5,"ownerPhone"),(12,6,"buildingArea"),(30,6,"buildingUse"),(8,7,"buildingAddress"),(8,11,"managerName"),(19,11,"managerBirth"),(8,12,"managerAddress"),(8,13,"managerGrade"),(19,13,"appointmentDate"),(33,13,"licenseNumber"),(0,18,"reportDate"),(25,19,"ownerName"))
    output=BytesIO()
    with zipfile.ZipFile(supplied_form("form10")) as original, zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED) as result:
        for info in original.infolist():
            content=original.read(info.filename)
            if info.filename=="Contents/section0.xml":
                root=ET.fromstring(content); table=root.findall(".//hp:tbl",NS)[0]
                for col,row,name in fields: put(table,col,row,data.get(name,""))
                content=ET.tostring(root,encoding="utf-8",xml_declaration=True)
            result.writestr(info,content)
    return output.getvalue()


def fill_draft(data):
    """Fill the supplied pre-approval draft's placeholders only."""
    replacements = {
        "\uc5ec\uc6b8\uc2dc\ud2f0 2\ucc28 \uad6c\ubd84\uc18c\uc720\uc790 \ub300\ud45c \uadc0\uc911": f"{data.get('ownerName', '')} \ub300\ud45c {data.get('ownerRepresentative', '')}".strip(),
        "\uc815\ubcf4\ud1b5\uc2e0\uc124\ube44 \uc720\uc9c0\ubcf4\uc218 \uad00\ub9ac\uc790 \uc120\uc784 \uc2e0\uace0\uc11c \uc218\ub9ac \uc54c\ub9bc [\uc8fc\uc18c_\uac74\ucd95\ubb3c\uba85]": f"\uc815\ubcf4\ud1b5\uc2e0\uc124\ube44 \uc720\uc9c0\ubcf4\uc218 \uad00\ub9ac\uc790 \uc120\uc784 \uc2e0\uace0\uc11c \uc218\ub9ac \uc54c\ub9bc [{data.get('buildingAddress', '')}_{data.get('buildingName', '')}]",
        "- \uc0c1\ud638(\uba85\uce6d) :": f"- \uc0c1\ud638(\uba85\uce6d) : {data.get('ownerName', '')}",
        "- \ub300\ud45c\uc790 :": f"- \ub300\ud45c\uc790 : {data.get('ownerRepresentative', '')}",
        "- \uc5f0\uba74\uc801 :": f"- \uc5f0\uba74\uc801 : {data.get('buildingArea', '')}m2",
        "- \uc6a9\ub3c4 :": f"- \uc6a9\ub3c4 : {data.get('buildingUse', '')}",
        "- \uc8fc\uc18c :": f"- \uc8fc\uc18c : {data.get('buildingAddress', '')}",
        "\uc120\uc784 / 000 / 0\uae09 /0000-00-00": f"\uc120\uc784 / {data.get('managerName', '')} / {data.get('managerGrade', '')} / {data.get('appointmentDate', '')}",
    }
    output = BytesIO()
    with zipfile.ZipFile(supplied_form("draft")) as original, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as result:
        for info in original.infolist():
            content = original.read(info.filename)
            if info.filename == "Contents/section0.xml":
                root = ET.fromstring(content)
                for text in root.findall(".//hp:t", NS):
                    key = (text.text or "").strip()
                    if key in replacements:
                        text.text = replacements[key]
                content = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            result.writestr(info, content)
    return output.getvalue()


def preview_svg(kind, data):
    """Overlay current values onto the supplied preview image in browser-safe SVG."""
    template = supplied_form("draft" if kind == "draft" else "form12")
    with zipfile.ZipFile(template) as archive:
        encoded = b64encode(archive.read("Preview/PrvImage.png")).decode("ascii")
    if kind == "draft":
        fields = [(114,194,540,data.get("ownerName","")+" \ub300\ud45c "+data.get("ownerRepresentative", "")),
                  (114,241,540,"\uc815\ubcf4\ud1b5\uc2e0\uc124\ube44 \uc720\uc9c0\ubcf4\uc218 \uad00\ub9ac\uc790 \uc120\uc784 \uc2e0\uace0\uc11c \uc218\ub9ac \uc54c\ub9bc ["+data.get("buildingAddress","")+"_"+data.get("buildingName","")+"]"),
                  (114,411,500,data.get("ownerName", "")),(114,434,500,data.get("ownerRepresentative", "")),
                  (114,505,500,data.get("buildingArea", "")+"m2"),(114,528,500,data.get("buildingUse", "")),
                  (114,551,500,data.get("buildingAddress", "")),
                  (114,619,500,"\uc120\uc784 / "+data.get("managerName","")+" / "+data.get("managerGrade","")+" / "+data.get("appointmentDate", ""))]
    else:
        fields = [(150,188,300,data.get("ownerName", "")),(462,188,180,data.get("ownerRepresentative", "")),
                  (150,240,300,data.get("businessNumber", "")),(462,240,180,data.get("ownerPhone", "")),
                  (150,293,485,data.get("ownerAddress", "")),(350,368,55,data.get("buildingArea", "")),
                  (515,375,100,data.get("buildingUse", "")),(150,433,485,data.get("buildingAddress", "")),
                  (150,546,235,data.get("certificateReason", "")),(475,530,120,data.get("certificateCopies", "")),
                  (442,680,135,data.get("ownerName", ""))]
        try:
            year, month, day = data.get("reportDate", "").split("-")
            fields.extend([(510,632,45,year),(580,632,30,str(int(month))),(622,632,30,str(int(day)))])
        except ValueError:
            pass
    overlay = ''.join(f'<rect x="{x}" y="{y-16}" width="{width}" height="22" fill="white"/><text x="{x}" y="{y}" font-size="13" font-family="Malgun Gothic, Arial, sans-serif">{escape(str(value))}</text>' for x,y,width,value in fields)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="724" height="1024" viewBox="0 0 724 1024"><image href="data:image/png;base64,' + encoded + '" width="724" height="1024"/>' + overlay + '</svg>').encode("utf-8")


def citizen_preview_svg(data):
    """Portable in-browser preview for the citizen form on Vercel."""
    lines = [("\uad00\ub9ac\uc8fc\uccb4", data.get("ownerName", "")), ("\ub300\ud45c\uc790", data.get("ownerRepresentative", "")),
             ("\ub300\uc0c1 \uac74\ucd95\ubb3c", data.get("buildingName", "")), ("\uc8fc\uc18c", data.get("buildingAddress", "")),
             ("\uc5f0\uba74\uc801", data.get("buildingArea", "") + " m2"), ("\uc6a9\ub3c4", data.get("buildingUse", "")),
             ("\uc720\uc9c0\uad00\ub9ac\uc790", data.get("managerName", "")), ("\uae30\uc220\uc790 \ub4f1\uae09", data.get("managerGrade", "")),
             ("\uc120\uc784\uc77c", data.get("appointmentDate", "")), ("\uc2e0\uace0\uc77c", data.get("reportDate", ""))]
    text = ''.join(f'<text x="75" y="{180+i*62}" font-size="21" font-family="Malgun Gothic, Arial, sans-serif">{escape(label)} : {escape(str(value))}</text>' for i,(label,value) in enumerate(lines))
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="724" height="1024"><rect width="100%" height="100%" fill="white"/><text x="75" y="95" font-size="30" font-weight="bold" font-family="Malgun Gothic, Arial, sans-serif">\uc815\ubcf4\ud1b5\uc2e0\uc124\ube44 \uc120\uc784 \uc2e0\uace0\uc11c \ubbf8\ub9ac\ubcf4\uae30</text>'+text+'</svg>').encode('utf-8')


def form10_preview_svg(data):
    with zipfile.ZipFile(supplied_form("form10")) as source:
        image=b64encode(source.read("Preview/PrvImage.png")).decode("ascii")
    fields=[(190,183,165,data.get("ownerName","")),(360,183,150,data.get("ownerRepresentative","")),(518,183,130,data.get("businessNumber","")),(190,216,320,data.get("ownerAddress","")),(518,216,130,data.get("ownerPhone","")),(370,252,54,data.get("buildingArea","")),(465,252,180,data.get("buildingUse","")),(190,304,455,data.get("buildingAddress","")),(190,421,150,data.get("managerName","")),(348,421,150,data.get("managerBirth","")),(190,454,455,data.get("managerAddress","")),(190,488,150,data.get("managerGrade","")),(348,488,150,data.get("appointmentDate","")),(508,488,135,data.get("licenseNumber",""))]
    overlay=''.join(f'<rect x="{x}" y="{y-18}" width="{w}" height="25" fill="white"/><text x="{x}" y="{y}" font-size="13" font-family="Malgun Gothic, Arial, sans-serif">{escape(str(v))}</text>' for x,y,w,v in fields)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="724" height="1024" viewBox="0 0 724 1024"><image href="data:image/png;base64,'+image+'" width="724" height="1024"/>'+overlay+'</svg>').encode('utf-8')


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
        if path == "/preview/generated/form10":
            body, content_type = form10_preview_svg(data), "image/svg+xml; charset=utf-8"
        elif path == "/generate/form10":
            body, content_type = fill_form10(data), "application/vnd.hancom.hwpx"
        elif path in ("/admin/preview/draft", "/admin/preview/certificate"):
            if path.endswith("certificate"):
                data.setdefault("reportDate", datetime.now().date().isoformat())
            body, content_type = preview_svg("draft" if path.endswith("draft") else "certificate", data), "image/svg+xml; charset=utf-8"
        elif path == "/admin/document/draft":
            body, content_type = fill_draft(data), "application/vnd.hancom.hwpx"
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
