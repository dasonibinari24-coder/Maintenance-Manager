"""Local document reader for the municipal-review screen."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from pathlib import Path
import json, re, zipfile
from xml.etree import ElementTree as ET

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

KEYWORDS = {
    '신고서': ('선임 신고서', '선임신고'), '건축물대장': ('건축물대장',),
    '재직증명서': ('재직증명',), '경력수첩': ('경력수첩',),
    '유지보수교육': ('교육증', '교육 이수', '유지보수 교육'),
}

def text_from(name, data):
    suffix = Path(name).suffix.lower()
    try:
        if suffix == '.pdf' and PdfReader:
            return '\n'.join(page.extract_text() or '' for page in PdfReader(BytesIO(data)).pages)
        if suffix in ('.hwpx', '.xlsx'):
            with zipfile.ZipFile(BytesIO(data)) as z:
                return '\n'.join(''.join(ET.fromstring(z.read(n)).itertext()) for n in z.namelist() if n.endswith('.xml'))
        return data.decode('utf-8', errors='ignore')
    except Exception:
        return ''

def classify(name, text):
    if '건축물대장' in name: return '건축물대장'
    if '재직증명' in name: return '재직증명서'
    if '경력수첩' in name: return '경력수첩'
    if any(word in name for word in ('교육이수증', '교육 이수증', '교육수료증')): return '유지보수교육'
    if '신고서' in name and '증명서' not in name: return '신고서'
    hay = f'{name} {text}'
    if any(word in hay for word in ('교육이수증', '교육 이수증', '교육수료증')):
        return '유지보수교육'
    return next((kind for kind, words in KEYWORDS.items() if any(w in hay for w in words)), '기타')

def first(patterns, text):
    for pattern in patterns:
        found = re.search(pattern, text, re.I)
        if found: return found.group(1).strip()
    return ''

def analyze(parts):
    documents=[]; all_text=''; filename_text=''; ledger_text=''
    for name, content in parts:
        text=text_from(name, content); all_text += '\n'+text; filename_text += '\n'+name
        kind=classify(name,text)
        if kind == '건축물대장': ledger_text += '\n'+text
        documents.append({'name':name, 'type':kind, 'read':bool(text)})
    fields={
        'area': first((r'연면적\s*[:：]?\s*([\d,]+(?:\.\d+)?)', r'([\d,]+(?:\.\d+)?)\s*㎡'), all_text).replace(',',''),
        'address': first((r'주소\s*[:：]?\s*([^\n]{5,100})', r'(경기도\s*화성시[^\n]{3,100})'), all_text),
        'name': first((r'(?:성명|유지관리자)\s*[:：]?\s*([가-힣]{2,5})',), all_text),
        'use': first((r'용도\s*[:：]?\s*([^\n]{2,40})',), all_text),
    }
    ledger_name = next((name for name, _ in parts if '건축물대장' in name), '')
    building = re.search(r'건축물대장[_\-\s]*([^.(]+)', ledger_name)
    if building:
        fields['buildingName'] = building.group(1).strip('_ -')
    fields['use'] = first((r'주용도\s*[:：]?\s*([^\n]{2,40})', r'건축물용도\s*[:：]?\s*([^\n]{2,40})'), all_text) or fields['use']
    invalid_use_terms = ('면적', '㎡', '층수', '층', '구조', '지붕', '높이', '대지', '주차')
    if any(term in fields['use'] for term in invalid_use_terms):
        fields['use'] = ''
    if '물류' in fields.get('buildingName', ''):
        fields['use'] = '창고시설'
    elif not fields['use']:
        for use_name in ('창고시설', '업무시설', '근린생활시설', '교육연구시설', '공장', '판매시설', '문화 및 집회시설', '의료시설', '숙박시설'):
            if use_name in ledger_text:
                fields['use'] = use_name
                break
    candidates=[x for x in re.findall(r'[가-힣]{2,4}', filename_text) if x not in ('교육이수증','건축물대장','재직증명서','경력수첩','관리자','신고서')]
    if candidates: fields['name']=candidates[-1]
    for grade in ('특급', '고급', '중급', '초급'):
        if grade in all_text + filename_text:
            fields['grade'] = grade; break
    date = re.search(r'(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})', all_text)
    if date:
        fields['date'] = f'{date.group(1)}-{int(date.group(2)):02d}-{int(date.group(3)):02d}'
    return {'documents':documents, 'fields':fields, 'found':[d['type'] for d in documents]}

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/analyze': self.send_error(404); return
        try:
            length=int(self.headers['Content-Length']); raw=self.rfile.read(length)
            boundary=self.headers['Content-Type'].split('boundary=',1)[1].encode()
            files=[]
            for part in raw.split(b'--'+boundary):
                head, sep, body=part.partition(b'\r\n\r\n')
                match=re.search(br'filename="([^"]+)"', head)
                if match and sep: files.append((match.group(1).decode('utf-8','replace'), body.rstrip(b'\r\n')))
            payload=json.dumps(analyze(files),ensure_ascii=False).encode()
            self.send_response(200); self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(payload))); self.end_headers(); self.wfile.write(payload)
        except Exception as error:
            self.send_error(500, str(error))
    def do_OPTIONS(self): self.send_response(204); self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-Control-Allow-Headers','Content-Type'); self.end_headers()
    def log_message(self,*_): pass

if __name__=='__main__': HTTPServer(('127.0.0.1',8093),Handler).serve_forever()
