(() => {
  const zone=document.querySelector('#drop-zone'), result=document.querySelector('#analysis-result'), selected=document.querySelector('#selected-file'), button=document.querySelector('#analyze-file');
  if(!zone||!result)return;
  const legacyInput=document.querySelector('#file-input');
  const privacy=document.querySelector('#privacy-check'), notice=document.querySelector('#notice-check');
  const input=document.createElement('input'); input.id='file-input'; input.type='file'; input.multiple=true; input.accept='.pdf,.jpg,.jpeg,.png,.hwpx,.xlsx'; input.hidden=true;
  legacyInput.replaceWith(input);
  const addButton=document.createElement('button'); addButton.type='button'; addButton.className='button ghost'; addButton.textContent='파일 추가하기 · 여러 파일 가능'; addButton.style.marginTop='12px'; zone.after(addButton);
  const needed=['신고서','건축물대장','재직증명서','경력수첩','유지보수교육'];
  let latest=[], latestResult=null;
  function refreshFinalReview(){
    const complete=button.dataset.reviewReady === 'true';
    button.disabled=!(complete&&privacy.checked&&notice.checked);
    button.setAttribute('aria-disabled', String(button.disabled));
  }
  function show(files){
    const incoming=[...files]; if(!incoming.length)return;
    latest=[...latest,...incoming.filter(file=>!latest.some(saved=>saved.name===file.name&&saved.size===file.size))];
    selected.innerHTML=`<span class="file-dot">✓</span><span><b>${latest.length}개 접수서류가 추가되었습니다.</b><small>${latest.map(file=>file.name).join(' · ')}</small></span>`;
    analyze();
  }
  async function analyze(){
    result.innerHTML='<span>⌛</span><div><b>접수서류를 읽고 있습니다.</b><p>파일별 내용과 누락 서류를 확인합니다.</p></div>';
    const data=new FormData(); latest.forEach(file=>data.append('files',file));
    try { const response=await fetch('http://127.0.0.1:8093/analyze',{method:'POST',body:data}); if(!response.ok)throw Error('판독 서비스에 연결할 수 없습니다.'); const parsed=await response.json(); latestResult=parsed; window.__uploadedFields=parsed.fields; sessionStorage.setItem('appointmentParsedFields', JSON.stringify(parsed.fields));
      const missing=needed.filter(type=>!parsed.found.includes(type)); parsed.readyForReview=!missing.length; button.dataset.reviewReady=String(parsed.readyForReview); const fields=parsed.fields;
      const values=[fields.address&&`주소: ${fields.address}`,fields.area&&`연면적: ${fields.area}㎡`,fields.use&&`용도: ${fields.use}`,fields.name&&`유지관리자: ${fields.name}`,fields.grade&&`기술자 등급: ${fields.grade}`,fields.date&&`선임일: ${fields.date}`].filter(Boolean);
      result.innerHTML=`<span>✓</span><div><b>접수서류 ${parsed.documents.length}건 자동 판독 완료</b><p>${parsed.documents.map(doc=>`<strong>${doc.type}</strong> · ${doc.name}`).join('<br>')}</p><p>${values.join(' / ')||'문서에서 추출 가능한 항목이 없습니다.'}</p><p>${missing.length?`보완 필요: ${missing.join(', ')} 첨부 여부를 확인해 주세요.`:'필수 첨부서류가 모두 확인되었습니다. 최종 검토 후 문서 생성이 가능합니다.'}</p></div>`;
      button.textContent='최종 검토 후 문서 만들기 →'; refreshFinalReview();
    } catch(error) { result.innerHTML=`<span>!</span><div><b>자동 판독에 실패했습니다.</b><p>${error.message}</p></div>`; }
  }
  zone.onclick=event=>{event.preventDefault();event.stopPropagation();input.click();return false};
  zone.addEventListener('click',event=>{event.preventDefault(); event.stopImmediatePropagation(); input.click()},true);
  input.addEventListener('change',event=>show(event.target.files));
  [privacy,notice].forEach(check=>check.addEventListener('change',()=>setTimeout(refreshFinalReview,0)));
  document.addEventListener('change',event=>{if(event.target===privacy||event.target===notice)setTimeout(refreshFinalReview,0)},true);
  // script.js also contains the legacy one-file upload handler.  Keep this
  // multi-file review state authoritative if that handler changes the button.
  setInterval(refreshFinalReview, 150);
  addButton.addEventListener('click',()=>input.click());
  ['dragenter','dragover'].forEach(type=>zone.addEventListener(type,event=>{event.preventDefault();zone.classList.add('dragging')}));
  ['dragleave','drop'].forEach(type=>zone.addEventListener(type,event=>{event.preventDefault();zone.classList.remove('dragging')}));
  zone.addEventListener('drop',event=>show(event.dataTransfer.files));
  button.addEventListener('click',event=>{if(!latestResult)return;event.preventDefault();event.stopImmediatePropagation();if(!latestResult.readyForReview||!privacy.checked||!notice.checked){alert('필수 첨부서류와 안내 확인 두 항목을 모두 확인한 뒤 진행해 주세요.');refreshFinalReview();return}const f=latestResult.fields;window.startWizard?.('정보통신설비',f.grade||'',f.area||'',{source:'upload'});setTimeout(()=>{const form=document.querySelector('#appointment-form');if(!form)return;const mapped={buildingName:'buildingName',buildingAddress:'address',buildingUse:'use',buildingArea:'area',ownerName:'ownerName',ownerRepresentative:'ownerRepresentative',businessNumber:'businessNumber',ownerPhone:'ownerPhone',ownerAddress:'ownerAddress',managerName:'name',managerGrade:'grade',managerBirth:'managerBirth',licenseNumber:'licenseNumber',appointmentDate:'date',managerAddress:'managerAddress',reportDate:'date',appointmentType:'appointmentType',certificateReason:'certificateReason',certificateCopies:'certificateCopies'};Object.entries(mapped).forEach(([formName,fieldName])=>{if(f[fieldName]&&form.elements[formName])form.elements[formName].value=f[fieldName]});document.querySelector('#wizard').scrollIntoView({behavior:'smooth'})},200)},true);
})();
