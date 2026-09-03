"""Document-grounded Q&A service used by the facility portal."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import chromadb
from openai import OpenAI

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DB_DIR = ROOT / "chroma_db"
COLLECTION_NAME = "hwaseong_ict_maintenance_qa"
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini")
MAX_DISTANCE = float(os.getenv("RAG_MAX_DISTANCE", "0.42"))
NOT_FOUND_MESSAGE = "자료에서 확인할 수 없습니다"
_openai: OpenAI | None = None
_chroma: chromadb.PersistentClient | None = None


class QAConfigurationError(RuntimeError):
    pass


def source_files() -> list[Path]:
    DATA_DIR.mkdir(exist_ok=True)
    return sorted(path for path in DATA_DIR.rglob("*.txt") if path.is_file())


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return path.read_text(encoding=encoding).strip()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"읽을 수 없는 인코딩입니다: {path.name}")


def split_text(text: str, size: int = 900, overlap: int = 150) -> list[str]:
    cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + size, len(cleaned))
        if end < len(cleaned):
            natural_break = cleaned.rfind("\n", start + size // 2, end)
            end = natural_break if natural_break > start else end
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return chunks


def openai_client() -> OpenAI:
    global _openai
    if _openai is None:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise QAConfigurationError("서버에 OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다.")
        _openai = OpenAI(api_key=key)
    return _openai


def chroma_client() -> chromadb.PersistentClient:
    global _chroma
    if _chroma is None:
        _chroma = chromadb.PersistentClient(path=str(DB_DIR))
    return _chroma


def collection() -> chromadb.Collection:
    return chroma_client().get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


def embed(texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), 64):
        response = openai_client().embeddings.create(model=EMBEDDING_MODEL, input=texts[start : start + 64])
        vectors.extend(item.embedding for item in response.data)
    return vectors


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
        name = path.relative_to(DATA_DIR).as_posix()
        for number, text in enumerate(split_text(read_text(path))):
            documents.append(text)
            ids.append(hashlib.sha256(f"{name}:{number}".encode()).hexdigest())
            metadatas.append({"source": name, "chunk": number})
    if documents:
        target.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embed(documents))
    return len(documents)


def ask(question: str) -> tuple[str, list[str]]:
    if not question.strip() or not source_files():
        return NOT_FOUND_MESSAGE, []
    if collection().count() == 0:
        index_documents()
    result = collection().query(
        query_embeddings=embed([question]), n_results=min(3, collection().count()),
        include=["documents", "metadatas", "distances"],
    )
    documents, metadatas, distances = result["documents"][0], result["metadatas"][0], result["distances"][0]
    if not documents or distances[0] > MAX_DISTANCE:
        return NOT_FOUND_MESSAGE, []
    context = "\n\n---\n\n".join(documents)
    prompt = f"""당신은 화성시 정보통신설비 유지보수·관리제도 민원 안내 챗봇입니다.
아래 [검색된 자료]에 명시된 내용만 사용해 한국어로 간결하게 답하세요.
자료에 답의 근거가 없거나 확실하지 않으면 정확히 '{NOT_FOUND_MESSAGE}'만 답하세요.
추측, 일반 지식, 자료에 없는 절차·수치·법령 정보는 덧붙이지 마세요.

[질문]\n{question}\n\n[검색된 자료]\n{context}"""
    answer = openai_client().responses.create(model=CHAT_MODEL, input=prompt).output_text.strip()
    if not answer:
        return NOT_FOUND_MESSAGE, []
    return answer, list(dict.fromkeys(item["source"] for item in metadatas))
