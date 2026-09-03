"""Fill only the original, supplied HWPX forms at their original table cells."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from io import BytesIO
import json
import zipfile
import xml.etree.ElementTree as ET
from qa_backend import QAConfigurationError, ask as ask_qa

ROOT = Path(__file__).parent
NS = {'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph'}
ET.register_namespace('hp', NS['hp'])


def template_for(kind):
    if kind == 'form10':
        return next(p for p in ROOT.glob('*.hwpx') if p.name.endswith('선임ㆍ해임 신고서.hwpx'))
    return next(p for p in ROOT.glob('*.hwpx') if '선임신고증명서 발급신청서' in p.name)


def cell_at(table, col, row):
    for cell in table.findall('.//hp:tc', NS):
        address = cell.find('hp:cellAddr', NS)
        if address is not None and address.get('colAddr') == str(col) and address.get('rowAddr') == str(row):
            return cell
    raise ValueError(f'Missing original-form cell ({col}, {row})')


def put(table, col, row, value):
    if value in (None, ''):
        return
    cell = cell_at(table, col, row)
    text = cell.find('.//hp:t', NS)
    if text is None:
        # Empty value cells in the supplied form contain a run but no text node.
        # Add text to that existing run so the original table layout is preserved.
        run = cell.find('.//hp:run', NS)
        if run is None:
            raise ValueError(f'Missing text run at ({col}, {row})')
        text = ET.SubElement(run, f"{{{NS['hp']}}}t")
    text.text = (text.text or '') + '\n' + str(value)


def checked(table, col, row):
    text = cell_at(table, col, row).find('.//hp:t', NS)
    text.text = (text.text or '').replace('[  ]', '[√]').replace('[ ]', '[√]')


def date_kr(value):
    try:
        year, month, day = value.split('-')
        return f'{year}년 {int(month)}월 {int(day)}일'
    except Exception:
        return value or ''


def put_date_line(table, col, row, value):
    """The original form has one cell containing year/month/day placeholders."""
    if not value:
        return
    try:
        year, month, day = value.split('-')
        display = f'{year}년          {int(month)}월          {int(day)}일'
    except ValueError:
        display = value
    text = cell_at(table, col, row).find('.//hp:t', NS)
    if text is None:
        raise ValueError(f'Missing date text at ({col}, {row})')
    text.text = display


def fill(template, data, fields, appointment=False):
    buffer = BytesIO()
    with zipfile.ZipFile(template, 'r') as source, zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as destination:
        for info in source.infolist():
            content = source.read(info.filename)
            if info.filename == 'Contents/section0.xml':
                root = ET.fromstring(content)
                table = root.findall('.//hp:tbl', NS)[0]
                for col, row, name in fields:
                    if name == 'reportDate':
                        put_date_line(table, col, row, data.get(name, ''))
                        continue
                    value = date_kr(data.get(name, '')) if name in {'appointmentDate', 'reportDate'} else data.get(name, '')
                    if name == 'buildingArea' and value:
                        value = f'{value} ㎡'
                    put(table, col, row, value)
                if appointment:
                    mode = data.get('appointmentType', '')
                    if mode == '직접 선임': checked(table, 8, 8)
                    elif mode == '위탁 수행': checked(table, 8, 9)
                content = ET.tostring(root, encoding='utf-8', xml_declaration=True)
            destination.writestr(info, content)
    return buffer.getvalue()


def fill_form10(data):
    # Supplied 별지 제10호서식, table 0. Different address/name cells stay distinct.
    fields = [
        (8, 4, 'ownerName'), (20, 4, 'ownerRepresentative'), (34, 4, 'businessNumber'),
        (8, 5, 'ownerAddress'), (34, 5, 'ownerPhone'),
        (12, 6, 'buildingArea'), (30, 6, 'buildingUse'), (8, 7, 'buildingAddress'),
        (8, 11, 'managerName'), (19, 11, 'managerBirth'), (8, 12, 'managerAddress'),
        (8, 13, 'managerGrade'), (19, 13, 'appointmentDate'), (33, 13, 'licenseNumber'),
        (0, 18, 'reportDate'),
        # The signature line at the bottom is a separate blank cell.
        (25, 19, 'ownerName'),
    ]
    return fill(template_for('form10'), data, fields, appointment=True)


def fill_form12(data):
    # Supplied 별지 제12호서식, table 0.
    fields = [
        (1, 4, 'ownerName'), (8, 4, 'ownerRepresentative'), (1, 5, 'businessNumber'),
        (8, 5, 'ownerPhone'), (1, 6, 'ownerAddress'),
        (2, 8, 'buildingArea'), (8, 8, 'buildingUse'), (1, 9, 'buildingAddress'),
        # Keep the printed labels ("신청사유", "신청부수") intact and write only
        # into their adjacent blank value cells.
        (1, 11, 'certificateReason'), (7, 11, 'certificateCopies'),
        (0, 13, 'reportDate'), (0, 14, 'ownerName'),
    ]
    return fill(template_for('form12'), data, fields)


class Handler(BaseHTTPRequestHandler):
    def cors_origin(self):
        """Allow the two local addresses used when opening the portal."""
        origin = self.headers.get('Origin', '')
        if origin in ('http://127.0.0.1:8080', 'http://localhost:8080'):
            return origin
        return 'http://127.0.0.1:8080'

    def send_response_headers(self, length=0, name=''):
        self.send_header('Access-Control-Allow-Origin', self.cors_origin())
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        if length:
            self.send_header('Content-Type', 'application/vnd.hancom.hwpx')
            self.send_header('Content-Length', str(length))
            self.send_header('Content-Disposition', f'attachment; filename="{name}"')

    def do_OPTIONS(self):
        self.send_response(204); self.send_response_headers(); self.end_headers()

    def do_GET(self):
        previews = {'/preview/form10': 'form10', '/preview/form12': 'form12'}
        if self.path not in previews:
            self.send_error(404); return
        with zipfile.ZipFile(template_for(previews[self.path])) as source:
            content = source.read('Preview/PrvImage.png')
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', self.cors_origin())
        self.send_header('Content-Type', 'image/png')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers(); self.wfile.write(content)

    def do_POST(self):
        try:
            data = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))))
            if self.path == '/qa/ask':
                question = str(data.get('question', '')).strip()
                if not question:
                    payload = json.dumps({'error': '질문을 입력해 주세요.'}, ensure_ascii=False).encode('utf-8')
                    self.send_response(400); self.send_header('Access-Control-Allow-Origin', self.cors_origin()); self.send_header('Content-Type', 'application/json; charset=utf-8'); self.send_header('Content-Length', str(len(payload))); self.end_headers(); self.wfile.write(payload); return
                answer, sources = ask_qa(question)
                payload = json.dumps({'answer': answer, 'sources': sources}, ensure_ascii=False).encode('utf-8')
                self.send_response(200); self.send_header('Access-Control-Allow-Origin', self.cors_origin()); self.send_header('Content-Type', 'application/json; charset=utf-8'); self.send_header('Content-Length', str(len(payload))); self.end_headers(); self.wfile.write(payload); return
            if self.path == '/generate/form10':
                content, name = fill_form10(data), 'form10-filled.hwpx'
            elif self.path == '/generate/form12':
                content, name = fill_form12(data), 'form12-filled.hwpx'
            else:
                self.send_error(404); return
            self.send_response(200); self.send_response_headers(len(content), name); self.end_headers(); self.wfile.write(content)
        except QAConfigurationError as error:
            payload = json.dumps({'error': str(error)}, ensure_ascii=False).encode('utf-8')
            self.send_response(503); self.send_header('Access-Control-Allow-Origin', self.cors_origin()); self.send_header('Content-Type', 'application/json; charset=utf-8'); self.send_header('Content-Length', str(len(payload))); self.end_headers(); self.wfile.write(payload)
        except Exception as error:
            self.send_response(500); self.send_response_headers(); self.end_headers(); self.wfile.write(str(error).encode())

    def log_message(self, *_):
        pass


if __name__ == '__main__':
    HTTPServer(('127.0.0.1', 8091), Handler).serve_forever()
