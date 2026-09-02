(() => {
  const form = document.querySelector('#appointment-form');
  const report = document.querySelector('#create-draft');
  report.innerHTML = '원본 별지 제10호서식 생성 <span>↓</span>';
  let certificate = document.querySelector('#create-certificate');
  if (!certificate) {
    certificate = document.createElement('button');
    certificate.id = 'create-certificate'; certificate.type = 'button';
    certificate.className = 'button ghost'; certificate.hidden = true;
    certificate.innerHTML = '원본 별지 제12호서식 생성 <span>↓</span>';
    report.after(certificate);
  }
  const preview = document.createElement('button');
  preview.type = 'button'; preview.className = 'button ghost'; preview.hidden = true;
  preview.id = 'open-original-preview'; preview.textContent = '원본 서식 미리보기';
  certificate.after(preview);

  async function download(path, filename) {
    const response = await fetch(`http://127.0.0.1:8091${path}`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(Object.fromEntries(new FormData(form)))
    });
    if (!response.ok) throw new Error(await response.text());
    const link = document.createElement('a');
    link.href = URL.createObjectURL(await response.blob()); link.download = filename; link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }
  function isInformation() { return document.querySelector('#facility-kind').value.includes('정보통신'); }

  preview.addEventListener('click', () => {
    if (!isInformation()) { alert('기계설비 원본 미리보기는 별도로 연결 중입니다.'); return; }
    const dialog = document.createElement('dialog');
    dialog.innerHTML = `<form method="dialog" style="padding:18px;min-width:min(94vw,900px)"><button aria-label="닫기" style="float:right;border:0;background:none;font-size:24px">×</button><h3>제공된 원본 별지서식 미리보기</h3><p>제10호·제12호 HWPX에 포함된 원본 서식 화면입니다. 입력값은 생성한 HWPX 파일에서 확인해 주세요.</p><h4>별지 제10호서식</h4><img alt="별지 제10호서식 원본" src="http://127.0.0.1:8091/preview/form10" style="width:100%;height:auto;border:1px solid #ccd5e4"><h4>별지 제12호서식</h4><img alt="별지 제12호서식 원본" src="http://127.0.0.1:8091/preview/form12" style="width:100%;height:auto;border:1px solid #ccd5e4"></form>`;
    document.body.append(dialog); dialog.addEventListener('close', () => dialog.remove()); dialog.showModal();
  });

  report.addEventListener('click', async event => {
    event.preventDefault(); event.stopImmediatePropagation();
    if (!isInformation()) { alert('기계설비 원본 양식 연결을 준비 중입니다.'); return; }
    try { await download('/generate/form10', '별지제10호서식_선임해임신고서.hwpx'); document.querySelector('#doc24-link').hidden = false; }
    catch (error) { alert(`원본 제10호서식 생성에 실패했습니다. ${error.message}`); }
  }, true);
  certificate.addEventListener('click', async event => {
    event.preventDefault(); event.stopImmediatePropagation();
    if (!isInformation()) { alert('별지 제12호서식은 정보통신설비 증명서 발급신청서입니다.'); return; }
    try { await download('/generate/form12', '별지제12호서식_증명서발급신청서.hwpx'); document.querySelector('#doc24-link').hidden = false; }
    catch (error) { alert(`원본 제12호서식 생성에 실패했습니다. ${error.message}`); }
  }, true);
})();
