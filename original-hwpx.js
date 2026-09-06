(() => {
  const form = document.querySelector('#appointment-form');
  const report = document.querySelector('#create-draft');
  report.innerHTML = '신고서 생성 <span>↓</span>';
  // 신고증명서는 시군구청 관리자 모드에서만 발급합니다.
  document.querySelector('#create-certificate')?.remove();
  const preview = document.createElement('button');
  preview.type = 'button'; preview.className = 'button primary'; preview.hidden = true;
  preview.id = 'open-original-preview'; preview.textContent = '생성된 서식 미리보기';
  preview.setAttribute('aria-label', '생성될 신고서 미리보기 열기');
  report.after(preview);

  async function download(path, filename) {
    const missing = [...form.querySelectorAll('[required]')]
      .filter(field => !String(field.value || '').trim())
      .map(field => field.closest('label')?.childNodes[0]?.textContent?.trim() || field.name);
    if (missing.length) throw new Error(`빈칸이 있어 문서를 생성하지 않았습니다: ${missing.join(', ')}`);
    const response = await fetch(`http://127.0.0.1:8091${path}`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(Object.fromEntries(new FormData(form)))
    });
    if (!response.ok) throw new Error(await response.text());
    const link = document.createElement('a');
    link.href = URL.createObjectURL(await response.blob()); link.download = filename; link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }
  function missingFields() {
    return [...form.querySelectorAll('[required]')]
      .filter(field => !String(field.value || '').trim())
      .map(field => field.closest('label')?.childNodes[0]?.textContent?.trim() || field.name);
  }
  function isInformation() { return document.querySelector('#facility-kind').value.includes('정보통신'); }

  preview.addEventListener('click', async () => {
    if (!isInformation()) { alert('기계설비 생성 서식 미리보기는 별도로 연결 중입니다.'); return; }
    const missing = missingFields();
    if (missing.length) { alert(`필수 입력값을 채운 뒤 생성 파일을 미리볼 수 있습니다. ${missing.join(', ')}`); return; }
    let form10Url;
    try {
      const data = JSON.stringify(Object.fromEntries(new FormData(form)));
      const form10 = await fetch('http://127.0.0.1:8091/preview/generated/form10', {method:'POST', headers:{'Content-Type':'application/json'}, body:data});
      if (!form10.ok) throw new Error('생성 파일 미리보기를 만들지 못했습니다.');
      form10Url = URL.createObjectURL(await form10.blob());
    } catch (error) { alert(`생성 파일 미리보기에 실패했습니다. ${error.message}`); return; }
    const dialog = document.createElement('dialog');
    dialog.innerHTML = `<div style="padding:18px;min-width:min(94vw,900px)"><h3>생성된 서식 미리보기</h3><p>현재 입력값을 채운 뒤 다운로드될 신고서입니다.</p><h4>별지 제10호서식 · 선임·해임 신고서</h4><img alt="값이 입력된 별지 제10호서식" src="${form10Url}" style="width:100%;height:auto;border:1px solid #ccd5e4"><div style="position:sticky;bottom:0;z-index:2;background:white;padding:12px 0;text-align:center"><button type="button" id="close-generated-preview" class="button primary">미리보기 닫기</button></div></div>`;
    document.body.append(dialog); dialog.querySelector('#close-generated-preview').addEventListener('click', () => dialog.close()); dialog.addEventListener('close', () => { URL.revokeObjectURL(form10Url); dialog.remove(); }); dialog.showModal();
  });

  report.addEventListener('click', async event => {
    event.preventDefault(); event.stopImmediatePropagation();
    if (!isInformation()) { alert('기계설비 신고서 양식 연결을 준비 중입니다.'); return; }
    try { await download('/generate/form10', '별지제10호서식_선임해임신고서.hwpx'); document.querySelector('#doc24-link').hidden = false; }
    catch (error) { alert(`신고서 생성에 실패했습니다. ${error.message}`); }
  }, true);
})();
