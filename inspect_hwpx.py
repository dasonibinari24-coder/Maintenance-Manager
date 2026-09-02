from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

NS = {'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph'}
for file in Path('.').glob('*선임신고증명서 발급신청서.hwpx'):
    with zipfile.ZipFile(file) as z:
        root = ET.fromstring(z.read('Contents/section0.xml'))
    print(file.name)
    for ti, table in enumerate(root.findall('.//hp:tbl', NS)):
        print('TABLE', ti)
        for cell in table.findall('.//hp:tc', NS):
            addr = cell.find('hp:cellAddr', NS)
            text = ''.join(cell.itertext()).strip().replace('\n', ' / ')
            if text:
                print(addr.attrib if addr is not None else {}, repr(text[:100]))
