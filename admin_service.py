"""Local document reader for the municipal-review screen."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from pathlib import Path
import json, re, subprocess, tempfile, zipfile
from xml.etree import ElementTree as ET

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import fitz
except ImportError:
    fitz = None

TESSERACT = Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe')
TESSDATA = Path(__file__).parent / 'assets' / 'tessdata'

KEYWORDS = {
    '신고서': ('선임 신고서', '선임신고'), '건축물대장': ('건축물대장',),
    '재직증명서': ('재직증명',), '경력수첩': ('경력수첩',),
    '유지보수교육': ('교육증', '교육 이수', '유지보수 교육'),
}

def ocr_pdf(data):
    if not fitz or not TESSERACT.exists() or not (TESSDATA / 'kor.traineddata').exists():
        return ''
    try:
        with tempfile.TemporaryDirectory() as folder:
            document = fitz.open(stream=data, filetype='pdf')
            pages = []
            for page_number in range(min(2, len(document))):
                image_path = Path(folder) / f'page-{page_number}.png'
                document[page_number].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(image_path)
                result = subprocess.run(
                    [str(TESSERACT), '--tessdata-dir', str(TESSDATA), str(image_path), 'stdout', '-l', 'kor+eng'],
                    capture_output=True, timeout=30, check=False,
                )
                pages.append(result.stdout.decode('utf-8', errors='replace'))
            document.close()
            return '\n'.join(pages)
    except Exception:
        return ''


def text_from(name, data):
    suffix = Path(name).suffix.lower()
    try:
        if suffix == '.pdf' and PdfReader:
            text = '\n'.join(page.extract_text() or '' for page in PdfReader(BytesIO(data)).pages)
            return text if len(re.sub(r'\s+', '', text)) >= 40 else ocr_pdf(data)
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
    documents=[]; all_text=''; filename_text=''; ledger_text=''; career_text=''; registration_text=''; report_text=''; contract_text=''
    for name, content in parts:
        text=text_from(name, content); all_text += '\n'+text; filename_text += '\n'+name
        kind=classify(name,text)
        if kind == '건축물대장': ledger_text += '\n'+text
        if kind == '경력수첩': career_text += '\n'+text
        if kind == '신고서': report_text += '\n'+text
        if '사업자등록' in name: registration_text += '\n'+text
        if '계약서' in name or '위탁' in text: contract_text += '\n'+text
        documents.append({'name':name, 'type':kind, 'read':bool(text)})
    compact_text = re.sub(r'(?<=[가-힣])[ \t]+(?=[가-힣])', '', all_text)
    source_text = all_text + '\n' + compact_text
    registration_source = registration_text + '\n' + re.sub(r'(?<=[가-힣])[ \t]+(?=[가-힣])', '', registration_text)
    career_source = career_text + '\n' + re.sub(r'(?<=[가-힣])[ \t]+(?=[가-힣])', '', career_text)
    fields={
        'area': first((r'연면적\s*[:：]?\s*([\d,]+(?:\.\d+)?)', r'([\d,]+(?:\.\d+)?)\s*㎡'), ledger_text + '\n' + source_text).replace(',',''),
        'address': first((r'도로명주소\s*(경기도\s*화성시[^\n]{3,100})', r'(경기도\s*화성시[^\n]{3,100})', r'(?:도로명)?주소\s*[:：]?\s*([^\n]{5,100})'), ledger_text + '\n' + source_text),
        'name': first((r'(?:성명|유지관리자)\s*[:：]?\s*([가-힣]{2,5})',), source_text),
        'use': first((r'(?:주)?용도\s*[:：]?\s*([^\n]{2,40})',), source_text),
        'ownerName': first((r'(?:상호\s*\(명칭\)|상호명|관리주체명|법인명\s*\(단체명\)|법인명)\s*[:：]?\s*([^\n]{2,80})',), registration_source),
        'ownerRepresentative': first((r'(?:대표자\s*성명|대표자명|대표자)\s*[:：]?\s*([가-힣]{2,12})',), source_text),
        'businessNumber': first((r'(?:사업자)?등록번호\s*[:：]?\s*([\d-]{10,14})',), registration_source),
        'ownerPhone': first((r'(?:전화번호|연락처)\s*[:：]?\s*(0\d{1,2}[- )]?\d{3,4}[- ]?\d{4})',), source_text),
        'managerBirth': first((r'(?:생년월일|주민등록번호)\s*[:：]?\s*((?:19|20)\d{2}[.\-/년]\s*\d{1,2}[.\-/월]\s*\d{1,2})',), career_text + source_text),
        'licenseNumber': first((r'(?:(?:경력수첩)?발급번호|수첩번호|기술자번호)\s*[:：]?\s*([A-Za-z0-9-]{4,40})',), career_text + source_text),
    }
    # The submitted report is commonly a scanned form.  Its OCR layout places
    # labels on the row above their values, so read those paired rows explicitly.
    fields['ownerName'] = first((r'상호\s*\(명칭\).*?\n([^\n]+?)\s+[가-힣]{2,5}\s+\d{3}-\d{2}-\d{5}',), report_text) or fields['ownerName']
    fields['ownerRepresentative'] = first((r'상호\s*\(명칭\).*?\n[^\n]+?\s+([가-힣]{2,5})\s+\d{3}-\d{2}-\d{5}',), report_text) or fields['ownerRepresentative']
    fields['businessNumber'] = first((r'상호\s*\(명칭\).*?\n[^\n]*?\s+(\d{3}-\d{2}-\d{5})',), report_text) or fields['businessNumber']
    fields['ownerAddress'] = first((r'주소\s+전화번호\s*\n([^\n]*?경기도\s*화성시[^\n]*?)\s+0\d{1,2}-\d{3,4}-\d{4}',), report_text) or fields['address']
    fields['ownerPhone'] = first((r'주소\s+전화번호\s*\n[^\n]*?\s+(0\d{1,2}-\d{3,4}-\d{4})',), report_text) or fields['ownerPhone']
    fields['name'] = first((r'성명\s+생년월일\s*\n([가-힣]{2,5})\s+(?:19|20)\d{2}',), report_text) or fields['name']
    fields['managerBirth'] = first((r'성명\s+생년월일\s*\n[가-힣]{2,5}\s+((?:19|20)\d{2}[-./]\d{1,2}[-./]\d{1,2})',), report_text) or fields['managerBirth']
    fields['managerAddress'] = first((r'선임\s+주소\s*\n[^\n]*?\n?([^\n]*부산광역시[^\n]+)',), report_text) or fields['managerAddress']
    fields['date'] = first((r'특급기술자\s+(?:\d{4}-\d{2}-\d{2}\s+)?((?:20)\d{2}-\d{2}-\d{2})',), report_text) or fields.get('date', '')
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
    filename_manager = re.search(r'(?:특급|고급|중급|초급)[_\-\s]*([가-힣]{2,4})', filename_text)
    if filename_manager:
        fields['name'] = filename_manager.group(1)
    elif not fields['name']:
        candidates=[x for x in re.findall(r'[가-힣]{2,4}', filename_text) if x not in ('교육이수증','건축물대장','재직증명서','경력수첩','관리자','신고서')]
        if candidates: fields['name']=candidates[-1]
    if not fields['ownerName']:
        registration = re.search(r'사업자등록증[_\-\s]*([^\n]+?)(?:\s*\([^\n]*\))?(?:\.[A-Za-z0-9]+)?$', filename_text, re.M)
        if registration:
            fields['ownerName'] = registration.group(1).strip(' _-')
    for grade in ('특급', '고급', '중급', '초급'):
        if grade in all_text + filename_text:
            fields['grade'] = grade; break
    date = re.search(r'(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})', all_text)
    if date:
        fields['date'] = f'{date.group(1)}-{int(date.group(2)):02d}-{int(date.group(3)):02d}'
    report_date = first((r'특급기술자\s+(?:\d{4}-\d{2}-\d{2}\s+)?((?:20)\d{2}-\d{2}-\d{2})',), report_text)
    if report_date:
        fields['date'] = report_date
    if fields.get('managerBirth'):
        birth = re.search(r'((?:19|20)\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})', fields['managerBirth'])
        if birth:
            fields['managerBirth'] = f'{birth.group(1)}-{int(birth.group(2)):02d}-{int(birth.group(3)):02d}'
    fields['ownerAddress'] = fields['ownerAddress'] or first((r'(?:사업장소재지|사업장\s*주소|본점소재지)\s*[:：]?\s*([^\n]{5,120})',), registration_source) or fields['address']
    # 신고서의 선임 주소가 가장 직접적인 근거입니다. 경력수첩의 다른 "주소"
    # 표기가 이 값을 덮어쓰지 않도록 신고서 값을 우선합니다.
    fields['managerAddress'] = fields['managerAddress'] or first((r'(?:유지관리자\s*주소|주소)\s*[:：]?\s*([^\n]{5,100})',), career_source) or fields['address']
    if '부산광역시' in fields['managerAddress']:
        fields['managerAddress'] = re.sub(r'^.*?(?=부산광역시)', '', fields['managerAddress']).strip()
    fields['appointmentType'] = '위탁 수행' if '위탁' in contract_text else '직접 선임'
    fields['certificateReason'] = '유지보수·관리자 선임신고증명서 발급'
    fields['certificateCopies'] = '1'
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
