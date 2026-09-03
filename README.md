# 화성시 정보통신설비 유지보수·관리제도 민원챗봇

기존 **시설관리 안내** 사이트의 `질의응답` 카테고리에서 여는 Streamlit 챗봇입니다. `data` 폴더의 TXT 질의응답 자료를 OpenAI 임베딩으로 벡터화해 ChromaDB에 저장하고, 질문과 가장 관련 있는 자료만 근거로 답변합니다. 근거가 없으면 **"자료에서 확인할 수 없습니다"**라고 답합니다. 모든 답변에는 검색에 사용된 출처 파일명이 표시됩니다.

## 구성

- `app.py`: 별도 Streamlit 검토 화면
- `qa_service.py`: 기존 시설관리 안내 페이지에 삽입되는 질의응답 API
- `data/`: 색인할 UTF-8 TXT 문서 폴더 (하위 폴더 사용 가능)
- `prepare_data.py`: 제공된 `정보통신설비 유지보수관리제도 질의응답 사례집.pdf`를 `data` TXT로 변환
- `chroma_db/`: 실행 중 생성되는 로컬 ChromaDB (Git 제외)
- `requirements.txt`: 필요한 Python 패키지

## 설치

Python 3.10 이상을 권장합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## API 키 설정

API 키를 코드나 Git에 저장하지 마세요. OpenAI SDK는 `OPENAI_API_KEY` 환경변수를 사용합니다.

현재 PowerShell 창에서만 설정하려면:

```powershell
$env:OPENAI_API_KEY = "your_api_key_here"
```

새 PowerShell 창에서도 유지하려면:

```powershell
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "your_api_key_here", "User")
```

`.env.example`은 설정값 예시이며, 실제 키가 들어간 `.env` 파일은 `.gitignore`로 제외됩니다.

## 실행

1. 제공된 사례집 PDF는 아래 명령으로 TXT 자료로 변환합니다. 다른 TXT 자료는 `data` 폴더에 추가하면 됩니다.

```powershell
python prepare_data.py
```

2. 기존 시설관리 안내 화면에서 바로 질문하려면 아래 명령으로 질의응답 서비스를 실행합니다.

```powershell
.\.venv\Scripts\python qa_service.py
```

3. 별도 Streamlit 검토 화면이 필요한 경우에는 아래 명령을 실행합니다.

```powershell
streamlit run app.py
```

4. 기존 시설관리 안내 화면의 **질의응답** 메뉴에서 바로 질문합니다. 별도 챗봇 주소로 이동하지 않습니다.
5. 자료를 바꾸면 `chroma_db` 폴더를 삭제한 뒤 다시 실행하면 새 자료를 색인합니다.

## 동작 원칙

- 임베딩: `text-embedding-3-small` (환경변수로 변경 가능)
- 답변 모델: `gpt-4.1-mini` (환경변수로 변경 가능)
- 검색 결과의 최고 코사인 거리가 `RAG_MAX_DISTANCE`(기본 `0.42`)보다 크면 답변하지 않습니다.
- 답변 모델에는 검색된 TXT 조각만 전달하며, 근거가 부족하면 지정 문구만 반환하도록 지시합니다.

OpenAI 임베딩 API는 하나 또는 여러 입력 텍스트의 벡터를 생성합니다. API 키는 환경변수로 전달하는 방식을 따릅니다. 자세한 사항은 [OpenAI 임베딩 API 문서](https://developers.openai.com/api/reference/ruby/resources/embeddings/methods/create)와 [OpenAI 공식 빠른 시작 가이드](https://platform.openai.com/docs/quickstart)를 참고하세요.
