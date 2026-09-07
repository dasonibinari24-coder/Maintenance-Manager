(() => {
  const form = document.querySelector('#appointment-form');
  const wizard = document.querySelector('#wizard');
  if (!form || !wizard) return;
  const storageVersion = '20260904d';
  if (sessionStorage.getItem('appointmentParsedFieldsVersion') !== storageVersion) {
    sessionStorage.removeItem('appointmentParsedFields');
    sessionStorage.setItem('appointmentParsedFieldsVersion', storageVersion);
  }

  const mappings = {
    buildingName: 'buildingName', buildingAddress: 'address', buildingUse: 'use', buildingArea: 'area',
    ownerName: 'ownerName', ownerRepresentative: 'ownerRepresentative', businessNumber: 'businessNumber',
    ownerPhone: 'ownerPhone', ownerAddress: 'ownerAddress', managerName: 'name', managerGrade: 'grade',
    managerBirth: 'managerBirth', licenseNumber: 'licenseNumber', appointmentDate: 'date',
    managerAddress: 'managerAddress', appointmentType: 'appointmentType',
    certificateReason: 'certificateReason', certificateCopies: 'certificateCopies',
  };

  const fields = () => {
    if (window.__uploadedFields) return window.__uploadedFields;
    try { return JSON.parse(sessionStorage.getItem('appointmentParsedFields') || '{}'); } catch (_) { return {}; }
  };

  function applyParsedFields() {
    const parsed = fields();
    Object.entries(mappings).forEach(([formName, sourceName]) => {
      const input = form.elements[formName];
      if (input && parsed[sourceName]) input.value = parsed[sourceName];
    });
  }

  function lockGenerationUntilFinalStep() {
    const finalStep = wizard.querySelector('.wizard-step.active')?.dataset.step === '4';
    ['create-draft', 'create-certificate', 'open-original-preview'].forEach(id => {
      const button = document.getElementById(id);
      if (button) { button.hidden = !finalStep; button.disabled = !finalStep; }
    });
    if (!finalStep) document.querySelector('#doc24-link').hidden = true;
  }

  const originalStart = window.startWizard;
  if (originalStart) {
    window.startWizard = (kind, grade, area, options = {}) => {
      const fromUpload = options?.source === 'upload';
      // A calculator/manual start is a new application.  Never let a previous
      // document upload repopulate or overwrite the applicant's new entries.
      if (!fromUpload) {
        window.__uploadedFields = null;
        sessionStorage.removeItem('appointmentParsedFields');
        form.reset();
      }
      originalStart(kind, grade, area);
      setTimeout(() => {
        if (fromUpload) applyParsedFields();
        lockGenerationUntilFinalStep();
      }, 0);
    };
  }
  document.addEventListener('click', event => {
    if (event.target.closest('#next-step, #prev-step')) {
      // Values can be edited by the applicant on every step; only adjust the
      // button visibility here, never restore an old upload value.
      setTimeout(lockGenerationUntilFinalStep, 0);
    }
  });
  new MutationObserver(lockGenerationUntilFinalStep)
    .observe(wizard, {subtree: true, attributes: true, attributeFilter: ['class']});
  applyParsedFields();
  lockGenerationUntilFinalStep();
})();
