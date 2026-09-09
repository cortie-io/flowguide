"""
text_utils.py
─────────────
텍스트 분할·언어 감지·정제 관련 순수 함수 모음입니다.
외부 상태에 의존하지 않으므로 단독 테스트가 가능합니다.
"""

from __future__ import annotations

import re
from pathlib import Path

from config import ASCII_PATTERN, KOREAN_PATTERN

# langchain이 없을 때 사용할 폴백 여부를 한 번만 확인
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore
    _HAS_LANGCHAIN = True
except Exception:
    _HAS_LANGCHAIN = False


# ── 파일 I/O ──────────────────────────────────────────────────────────────────

def read_text(path: Path) -> str:
    """UTF-8로 파일을 읽습니다. 인코딩 오류는 무시합니다."""
    return path.read_text(encoding="utf-8", errors="ignore")


# ── 텍스트 분할 ───────────────────────────────────────────────────────────────

def _split_fallback(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: list[str],
) -> list[str]:
    """langchain 없이도 동작하는 단순 재귀 분할기."""
    if not text:
        return []

    # 첫 번째로 매칭되는 구분자로 분할
    parts: list[str] = [text]
    for sep in separators:
        next_parts: list[str] = []
        changed = False
        for part in parts:
            if sep not in part:
                next_parts.append(part)
                continue
            changed = True
            chunks = part.split(sep)
            for i, c in enumerate(chunks):
                if c:
                    next_parts.append(c if i == 0 else sep + c)
        parts = next_parts
        if changed:
            break

    # chunk_size 초과 조각은 슬라이딩 윈도우로 재분할
    step = max(1, chunk_size - chunk_overlap)
    result: list[str] = []
    for part in parts:
        s = part.strip()
        if not s:
            continue
        if len(s) <= chunk_size:
            result.append(s)
        else:
            for start in range(0, len(s), step):
                result.append(s[start : start + chunk_size])
    return result


def split_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: list[str],
) -> list[str]:
    """텍스트를 청크 단위로 분할합니다. langchain 유무에 따라 구현이 선택됩니다."""
    if not text:
        return []
    if not _HAS_LANGCHAIN:
        return _split_fallback(text, chunk_size, chunk_overlap, separators)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
    )
    return splitter.split_text(text)


# ── 언어 감지 ─────────────────────────────────────────────────────────────────

def infer_language(text: str, default_lang: str) -> str:
    """
    default_lang이 'auto'일 때만 텍스트를 샘플링해 언어를 추정합니다.
    그 외에는 default_lang을 그대로 반환합니다.
    """
    if default_lang != "auto":
        return default_lang

    sample = text[:2000]
    if not sample:
        return "unknown"

    has_korean = bool(KOREAN_PATTERN.search(sample))
    has_ascii = bool(ASCII_PATTERN.search(sample))

    if has_korean and has_ascii:
        return "mixed"
    return "ko" if has_korean else "en"


# ── 텍스트 정제 ───────────────────────────────────────────────────────────────

def clean_markdown(text: str) -> str:
    """마크다운 기호와 코드블록을 제거하고 공백을 정규화합니다."""
    text = text.replace("\r", "\n")
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"[#>*_`\-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
