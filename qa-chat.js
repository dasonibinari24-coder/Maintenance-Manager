const qaForm = document.querySelector('#qa-form');
const qaQuestion = document.querySelector('#qa-question');
const qaMessages = document.querySelector('#qa-messages');

function appendQaMessage(content, role, sources = []) {
  const message = document.createElement('div');
  message.className = `qa-message ${role}`;
  message.textContent = content;
  qaMessages.append(message);
  if (sources.length) {
    const source = document.createElement('p');
    source.className = 'qa-sources';
    source.textContent = `출처: ${sources.join(', ')}`;
    qaMessages.append(source);
  }
  qaMessages.scrollTop = qaMessages.scrollHeight;
  return message;
}

if (qaForm) {
  qaForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const question = qaQuestion.value.trim();
    if (!question) return;
    appendQaMessage(question, 'user');
    qaQuestion.value = '';
    qaQuestion.disabled = true;
    const pending = appendQaMessage('자료를 확인하고 있습니다…', 'assistant pending');
    try {
      const response = await fetch('http://127.0.0.1:8092/qa/ask', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({question})
      });
      const data = await response.json();
      pending.remove();
      if (!response.ok) throw new Error(data.error || '답변을 불러오지 못했습니다.');
      appendQaMessage(data.answer, 'assistant', data.sources || []);
    } catch (error) {
      pending.remove();
      appendQaMessage(error.message || '답변 처리 중 오류가 발생했습니다.', 'assistant error');
    } finally {
      qaQuestion.disabled = false;
      qaQuestion.focus();
    }
  });
}
