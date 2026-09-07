const $=id=>document.getElementById(id), required=['신고서','건축물대장','재직증명서','경력수첩','교육'];
let last={}, documentFields={};
document.querySelector('#educationName').insertAdjacentHTML('afterend','<input id="appointmentDate" type="date" aria-label="선임일">');
document.querySelector('#review').addEventListener('click',()=>{last.date=document.querySelector('#appointmentDate').value});
$('files').addEventListener('change', event => readAndReview(event.target.files));
const dropZone=document.querySelector('.drop');
['dragenter','dragover'].forEach(type=>dropZone.addEventListener(type,event=>{event.preventDefault();dropZone.classList.add('dragging')}));
['dragleave','drop'].forEach(type=>dropZone.addEventListener(type,event=>{event.preventDefault();dropZone.classList.remove('dragging')}));
dropZone.addEventListener('drop',event=>{const transfer=new DataTransfer();[...event.dataTransfer.files].forEach(file=>transfer.items.add(file));$('files').files=transfer.files;readAndReview(transfer.files)});
async function readAndReview(files){
  if(!files.length)return;
  $('filelist').innerHTML='<li>문서를 읽고 있습니다…</li>';
  const data=new FormData();[...files].forEach(file=>data.append('files',file));
  try{const response=await fetch('http://127.0.0.1:8093/analyze',{method:'POST',body:data});if(!response.ok)throw Error('분석 서비스 응답 오류');const result=await response.json();
    $('filelist').innerHTML=result.documents.map(doc=>`<li><b>${doc.type}</b> · ${doc.name}${doc.read?' (내용 확인)':' (파일명으로 분류)'}</li>`).join('');
    const f=result.fields;documentFields=f;if(f.area){$('ledgerArea').value=f.area;$('reportArea').value=f.area}if(f.address){$('ledgerAddr').value=f.address;$('reportAddr').value=f.address}if(f.use){$('ledgerUse').value=f.use;$('reportUse').value=f.use}if(f.name){['reportName','employmentName','careerName','educationName'].forEach(id=>$(id).value=f.name)}if(f.grade)$('grade').value=f.grade;if(f.date)$('appointmentDate').value=f.date;
    $('review').click();
  }catch(error){$('filelist').innerHTML=`<li>자동 판독에 실패했습니다: ${error.message}</li>`}
}
$('files').addEventListener('change',e=>{$('filelist').innerHTML=[...e.target.files].map(f=>`<li>${f.name}</li>`).join('')||'<li>선택된 파일이 없습니다.</li>'});
function value(id){return $(id).value.trim()} function rank(g){return ['초급','중급','고급','특급'].indexOf(g)}
function needed(area){return area>=60000?'특급':area>=30000?'고급':area>=15000?'중급':area>=5000?'초급':null}
$('review').onclick=()=>{const files=[...$('files').files].map(f=>f.name); const issues=[]; const has=n=>files.some(x=>x.includes(n));
 required.forEach(n=>{if(!has(n))issues.push(`${n}이(가) 첨부되지 않았습니다.`)});
 const pairs=[['주소','ledgerAddr','reportAddr'],['연면적','ledgerArea','reportArea'],['용도','ledgerUse','reportUse']]; pairs.forEach(([label,a,b])=>{if(!value(a)||!value(b))issues.push(`건축물 ${label} 대조값을 모두 입력해 주세요.`);else if(value(a)!==value(b))issues.push(`건축물대장과 신고서의 ${label}이(가) 일치하지 않습니다.`)});
 const names=['reportName','employmentName','careerName','educationName']; if(names.some(id=>!value(id))) issues.push('유지관리자 동일인 확인값을 모두 입력해 주세요.'); else if(new Set(names.map(value)).size!==1)issues.push('신고서·재직증명서·경력수첩·교육증의 유지관리자 성명이 일치하지 않습니다.');
 const need=needed(Number(value('ledgerArea'))), grade=value('grade'); if(need&&!grade)issues.push(`연면적 ${value('ledgerArea')}㎡에는 ${need} 이상 기술자 확인이 필요합니다.`); else if(need&&rank(grade)<rank(need))issues.push(`연면적 기준 ${need} 이상이 필요하나 신고 기술자 등급은 ${grade}입니다.`);
 last={...documentFields,ownerAddress:documentFields.ownerAddress||value('ledgerAddr'),buildingAddress:value('ledgerAddr'),buildingArea:value('ledgerArea'),buildingUse:value('ledgerUse'),buildingName:documentFields.buildingName||value('ledgerUse'),managerName:value('reportName'),managerGrade:grade,appointmentDate:value('appointmentDate'),need}; $('result').classList.remove('hidden'); $('issues').innerHTML=issues.map(x=>`<li>${x}</li>`).join(''); $('verdict').className=issues.length?'bad':'ok'; $('verdict').textContent=issues.length?`보완 필요: ${issues.length}건을 확인해 주세요.`:'이상 없습니다. 온나라 기안문과 선임신고증명서를 생성할 수 있습니다.'; $('docs').classList.toggle('hidden',!!issues.length); $('result').scrollIntoView({behavior:'smooth'});};
async function adminDocument(kind,preview=false){const base=['127.0.0.1','localhost'].includes(location.hostname)?'http://127.0.0.1:8091':'/api';const response=await fetch(`${base}/admin/${preview?'preview':'document'}/${kind}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(last)});if(!response.ok)throw Error('문서 생성에 실패했습니다.');return response.blob()}
document.querySelectorAll('[data-download]').forEach(button=>button.onclick=async()=>{try{const blob=await adminDocument(button.dataset.download);const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download=button.dataset.download==='draft'?'수리알림-결재전.hwpx':'선임신고증명서-발급신청서.hwpx';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000)}catch(error){alert(error.message)}});
document.querySelectorAll('[data-preview]').forEach(button=>button.onclick=async()=>{try{const blob=await adminDocument(button.dataset.preview,true),dialog=$('preview');$('preview-frame').src=URL.createObjectURL(blob);dialog.showModal()}catch(error){alert(error.message)}});
$('close-preview').onclick=()=>{$('preview-frame').src='about:blank';$('preview').close()};
async function loadRegistry(){try{
  const query=$('registry-query').value.trim().toLowerCase();
  const registryUrl=['127.0.0.1','localhost'].includes(location.hostname)
    ? `http://127.0.0.1:8091/admin/duplicate-registry?q=${encodeURIComponent(query)}`
    : './duplicate-registry.json';
  const response=await fetch(registryUrl);
  if(!response.ok)throw Error(`HTTP ${response.status}`);
  const data=await response.json();
  if(query && !['127.0.0.1','localhost'].includes(location.hostname)) data.rows=data.rows.filter(row=>Object.values(row).join(' ').toLowerCase().includes(query));
  $('registry-status').textContent=data.message || '';
  const table=data.rows?.length?`<div style="overflow:auto"><table><thead><tr>${data.fields.map(field=>`<th>${field}</th>`).join('')}</tr></thead><tbody>${data.rows.map(row=>`<tr>${data.fields.map(field=>`<td>${row[field]||''}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:'<p class="registry-results-note">조건에 맞는 대상자가 없습니다.</p>';
  $('registry-results').innerHTML=table;$('registry-search').disabled=!!data.locked;
}catch(error){$('registry-status').textContent=`조회명단을 불러오지 못했습니다: ${error.message}`}}
$('registry-search').onclick=()=>loadRegistry();
loadRegistry();
