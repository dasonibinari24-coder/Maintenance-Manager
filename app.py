"""화성시 정보통신설비 유지보수·관리제도 민원 챗봇."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import chromadb
import streamlit as st
from openai import OpenAI


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "hwaseong_ict_maintenance_qa"
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini")
TOP_K = 3
# Chroma cosine distance: 0 is identical and larger values are less similar.
MAX_DISTANCE = float(os.getenv("RAG_MAX_DISTANCE", "0.42"))
NOT_FOUND_MESSAGE = "자료에서 확인할 수 없습니다"


def read_text_file(path: Path) -> str:
    """Read UTF-8 text first, then common Korean encodings."""
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return path.read_text(encoding=encoding).strip()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"읽을 수 없는 인코딩입니다: {path.name}")


def source_files() -> list[Path]:
    DATA_DIR.mkdir(exist_ok=True)
    return sorted(path for path in DATA_DIR.rglob("*.txt") if path.is_file())


def corpus_signature(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        digest.update(str(path.relative_to(DATA_DIR)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def chunk_text(text: str, size: int = 900, overlap: int = 150) -> list[str]:
    """Create overlapping character chunks, preferring a natural line break."""
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind("\n", start + size // 2, end)
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


@st.cache_resource
def openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다.")
    return OpenAI(api_key=api_key)


@st.cache_resource
def chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=str(DB_DIR))


def embeddings(texts: list[str]) -> list[list[float]]:
    client = openai_client()
    result: list[list[float]] = []
    for start in range(0, len(texts), 64):
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts[start : start + 64])
        result.extend(item.embedding for item in response.data)
    return result


def collection() -> chromadb.Collection:
    return chroma_client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def index_documents() -> int:
    files = source_files()
    if not files:
        return 0

    client = chroma_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except ValueError:
        pass
    target = collection()

    documents: list[str] = []
    ids: list[str] = []
    metadatas: list[dict[str, Any]] = []
    for path in files:
        relative_path = path.relative_to(DATA_DIR).as_posix()
        for number, text in enumerate(chunk_text(read_text_file(path))):
            documents.append(text)
            ids.append(hashlib.sha256(f"{relative_path}:{number}".encode()).hexdigest())
            metadatas.append({"source": relative_path, "chunk": number})

    if documents:
        target.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings(documents))
    return len(documents)


def index_is_current() -> bool:
    return bool(source_files()) and collection().count() > 0


def retrieve(question: str) -> tuple[list[str], list[dict[str, Any]], list[float]]:
    result = collection().query(
        query_embeddings=embeddings([question]),
        n_results=min(TOP_K, collection().count()),
        include=["documents", "metadatas", "distances"],
    )
    return result["documents"][0], result["metadatas"][0], result["distances"][0]


def answer_question(question: str) -> tuple[str, list[str]]:
    if not source_files() or not index_is_current():
        return NOT_FOUND_MESSAGE, []

    documents, metadatas, distances = retrieve(question)
    if not documents or distances[0] > MAX_DISTANCE:
        return NOT_FOUND_MESSAGE, []

    context = "\n\n---\n\n".join(documents)
    prompt = f"""당신은 화성시 정보통신설비 유지보수·관리제도 민원 안내 챗봇입니다.
아래 [검색된 자료]에 명시된 내용만 사용해 한국어로 답하세요.
자료에 답의 근거가 없거나 확실하지 않으면 정확히 '{NOT_FOUND_MESSAGE}'만 답하세요.
추측, 일반 지식, 법령의 최신성 판단, 검색된 자료에 없는 절차나 수치는 절대 덧붙이지 마세요.
답변은 간결하게 작성하세요.

[질문]
{question}

[검색된 자료]
{context}
"""
    response = openai_client().responses.create(model=CHAT_MODEL, input=prompt)
    answer = response.output_text.strip()
    if not answer:
        return NOT_FOUND_MESSAGE, []
    sources = list(dict.fromkeys(metadata["source"] for metadata in metadatas))
    return answer, sources


def render() -> None:
    st.set_page_config(page_title="시설관리 안내 | 질의응답", page_icon="💬", layout="centered")
    st.caption("시설관리 안내  ›  정보통신설비  ›  질의응답")
    st.title("화성시 정보통신설비 유지보수·관리제도 민원챗봇")
    st.caption("등록된 질의응답 자료만 검색하여 답변합니다.")

    with st.sidebar:
        st.header("질의응답 자료 관리")
        files = source_files()
        st.write(f"TXT 자료: {len(files)}개")
        if st.button("자료 다시 색인", use_container_width=True):
            if not files:
                st.warning("data 폴더에 TXT 문서를 추가해 주세요.")
            else:
                try:
                    with st.spinner("임베딩 및 벡터 DB 저장 중..."):
                        count = index_documents()
                    st.success(f"{count}개 문서 조각을 색인했습니다.")
                except Exception as error:
                    st.error(f"색인에 실패했습니다: {error}")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message.get("sources"):
                st.caption("출처: " + ", ".join(message["sources"]))

    question = st.chat_input("예: 유지관리자 선임 대상은 어떻게 되나요?")
    if not question:
        return
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("자료를 검색하고 있습니다..."):
                answer, sources = answer_question(question)
            st.write(answer)
            if sources:
                st.caption("출처: " + ", ".join(sources))
            st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
        except RuntimeError as error:
            st.error(str(error))
        except Exception as error:
            st.error(f"답변 처리 중 오류가 발생했습니다: {error}")


if __name__ == "__main__":
    render()
