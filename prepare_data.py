"""Convert the supplied Q&A PDF into the TXT corpus used by the chatbot."""
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).parent
SOURCE = ROOT / "정보통신설비 유지보수관리제도 질의응답 사례집.pdf"
TARGET = ROOT / "data" / "정보통신설비_유지보수관리제도_질의응답_사례집.txt"


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(f"원본 PDF를 찾을 수 없습니다: {SOURCE.name}")
    TARGET.parent.mkdir(exist_ok=True)
    reader = PdfReader(SOURCE)
    pages = [page.extract_text(extraction_mode="layout") or "" for page in reader.pages]
    text = "\n\n".join(f"[페이지 {index + 1}]\n{page.strip()}" for index, page in enumerate(pages) if page.strip())
    if not text:
        raise ValueError("PDF에서 추출한 텍스트가 없습니다.")
    TARGET.write_text(text, encoding="utf-8")
    print(f"{TARGET.name}: {len(reader.pages)}쪽, {len(text):,}자 저장 완료")


if __name__ == "__main__":
    main()
