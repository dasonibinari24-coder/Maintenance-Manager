const wizard = document.querySelector('#wizard');
const form = document.querySelector('#appointment-form');
const steps = [...document.querySelectorAll('.wizard-step')];
const progress = [...document.querySelectorAll('.wizard-progress span')];
const prev = document.querySelector('#prev-step');
const next = document.querySelector('#next-step');
const draft = document.querySelector('#create-draft');
const doc24 = document.querySelector('#doc24-link');
let current = 1;

function certificateButton() { return document.querySelector('#create-certificate'); }

function focusActiveField() {
  const first = document.querySelector('.wizard-step.active input:not([type="hidden"]):not([disabled]), .wizard-step.active select:not([disabled]), .wizard-step.active textarea:not([disabled])');
  if (first) setTimeout(() => first.focus(), 60);
}

function addOfficialFields() {
  const grid = steps[2].querySelector('.field-grid');
  if (form.elements.reportDate) return;
  grid.insertAdjacentHTML('beforeend', '<label>신고일<input name="reportDate" required type="date"></label><label>증명서 발급 부수<input name="certificateCopies" required type="number" min="1" value="1"></label><label class="full">신청사유<input name="certificateReason" required value="선임신고증명서 발급" placeholder="예: 선임신고증명서 발급"></label>');
}

function startWizard(kind, grade, area) {
  addOfficialFields();
  wizard.classList.remove('hidden');
  document.querySelector('#facility-kind').value = kind;
  document.querySelector('#required-grade').value = grade;
  document.querySelector('#wizard-kind').textContent = `${kind} 선임신고`;
  form.elements.buildingArea.value = area || '';
  form.elements.managerGrade.value = grade;
  if (!form.elements.reportDate.value) form.elements.reportDate.value = new Date().toISOString().slice(0, 10);
  current = 1;
  renderWizard();
  wizard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  focusActiveField();
}

function renderWizard() {
  steps.forEach(step => step.classList.toggle('active', Number(step.dataset.step) === current));
  progress.forEach((item, index) => item.classList.toggle('active', index < current));
  prev.hidden = current === 1;
  next.hidden = current === 4;
  draft.hidden = current !== 4;
  const certificate = certificateButton();
  if (certificate) certificate.hidden = current !== 4;
  const preview = document.querySelector('#open-original-preview');
  if (preview) preview.hidden = current !== 4;
  doc24.hidden = true;
  if (current === 4) review();
}

function validStep() {
  const fields = [...steps[current - 1].querySelectorAll('[required]')];
  const invalid = fields.filter(field => !field.value.trim());
  invalid.forEach(field => field.classList.toggle('invalid', !field.value.trim()));
  if (invalid.length) {
    invalid[0].focus();
    return false;
  }
  return true;
}

function review() {
  const data = new FormData(form);
  const names = {
    buildingName: '건축물 명칭',
    buildingUse: '건축물 용도',
    buildingAddress: '건축물 주소',
    ownerName: '관리주체명',
    ownerRepresentative: '대표자',
    managerName: '유지관리자',
    managerGrade: '기술자 등급',
    appointmentDate: '선임일',
    reportDate: '신고일',
    certificateReason: '신청사유',
  };
  document.querySelector('#review-list').innerHTML = Object.entries(names)
    .map(([key, name]) => `<div><span>✓</span><b>${name}</b><em>${data.get(key) || '-'}</em></div>`)
    .join('');
}

next.addEventListener('click', () => {
  if (validStep()) {
    current++;
    renderWizard();
    focusActiveField();
  }
});

prev.addEventListener('click', () => {
  current--;
  renderWizard();
  focusActiveField();
});

window.startWizard = startWizard;
