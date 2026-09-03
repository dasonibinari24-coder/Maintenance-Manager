(() => {
  const privacy = document.querySelector('#privacy-check');
  const notice = document.querySelector('#notice-check');
  const button = document.querySelector('#analyze-file');
  const result = document.querySelector('#analysis-result');
  if (!privacy || !notice || !button || !result) return;

  let documentsPassed = false;
  const passesDocumentReview = () => {
    const text = result.textContent.replace(/\s+/g, ' ');
    return /모두 확인|생성 가능|판독 완료/.test(text) && !/보완 필요|분석에 실패|첨부되지 않았/.test(text);
  };
  const refresh = () => {
    documentsPassed = passesDocumentReview();
    const enabled = documentsPassed && privacy.checked && notice.checked;
    button.disabled = !enabled;
    button.setAttribute('aria-disabled', String(!enabled));
    button.title = enabled ? '최종 검토를 마쳤습니다. 문서 만들기를 진행할 수 있습니다.' : '서류 판독 완료 후 안내 두 항목을 모두 체크해 주세요.';
  };

  new MutationObserver(() => setTimeout(refresh, 0))
    .observe(result, { childList: true, subtree: true, characterData: true });
  [privacy, notice].forEach(box => box.addEventListener('change', () => setTimeout(refresh, 0)));
  refresh();
})();
