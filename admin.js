const $=id=>document.getElementById(id), required=['신고서','건축물대장','재직증명서','경력수첩','교육'];
let last={};
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
    const f=result.fields;if(f.area){$('ledgerArea').value=f.area;$('reportArea').value=f.area}if(f.address){$('ledgerAddr').value=f.address;$('reportAddr').value=f.address}if(f.use){$('ledgerUse').value=f.use;$('reportUse').value=f.use}if(f.name){['reportName','employmentName','careerName','educationName'].forEach(id=>$(id).value=f.name)}if(f.grade)$('grade').value=f.grade;if(f.date)$('appointmentDate').value=f.date;
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
 last={name:value('reportName'),addr:value('ledgerAddr'),area:value('ledgerArea'),use:value('ledgerUse'),grade,need}; $('result').classList.remove('hidden'); $('issues').innerHTML=issues.map(x=>`<li>${x}</li>`).join(''); $('verdict').className=issues.length?'bad':'ok'; $('verdict').textContent=issues.length?`보완 필요: ${issues.length}건을 확인해 주세요.`:'이상 없습니다. 온나라 기안문과 선임신고증명서를 생성할 수 있습니다.'; $('docs').classList.toggle('hidden',!!issues.length); $('result').scrollIntoView({behavior:'smooth'});};
function paper(type){const title=type==='draft'?'정보통신설비 유지보수 관리자 선임 신고서 수리 알림':type==='certificate'?'정보통신설비 유지보수 관리자 선임신고 증명서':'정보통신설비 유지보수·관리자 중복선임 여부 조회 요청';const body=type==='draft'?`문서24로 접수된 유지관리자 선임신고서를 검토한 결과, 건축물대장 및 첨부 증빙서류의 기재사항이 일치하고 선임 기준에 적합하여 수리하였음을 알려드립니다.`:type==='certificate'?`위 건축물의 유지관리자 선임신고가 접수·검토되었음을 증명합니다.`:`유지관리자 중복선임 여부 확인을 위하여 아래 대상자의 조회를 요청합니다.`;return `<p class="meta">화성시</p><h1>${title}</h1><p class="meta">시행일: ${new Date().toLocaleDateString('ko-KR')}</p><p>${body}</p><hr><p><b>건축물 주소</b> ${last.addr||'-'}</p><p><b>연면적 / 용도</b> ${last.area||'-'}㎡ / ${last.use||'-'}</p><p><b>유지관리자</b> ${last.name||'-'} (${last.grade||'-'})</p><p><b>검토 결과</b> 연면적 기준 ${last.need||'해당 없음'} 이상 충족</p><br><p style="text-align:right">화성시장 귀하</p>`}
document.querySelectorAll('[data-doc]').forEach(b=>b.onclick=()=>{$('paper').innerHTML=paper(b.dataset.doc);$('preview').showModal()});
$('download').onclick=()=>{const html=`<!doctype html><meta charset="utf-8"><title>선임신고 검토문서</title>${paper('draft')}<div style="page-break-before:always"></div>${paper('certificate')}<div style="page-break-before:always"></div>${paper('duplicate')}`;const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([html],{type:'text/html'}));a.download='유지관리자_선임신고_검토문서.html';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
