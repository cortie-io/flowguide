"""
processors.py
─────────────
Track A~E 각 데이터 소스를 청크로 변환하는 프로세서 함수 모음입니다.

Track A — 공식 문서 (docs/*.md)
Track B/C — 핵심 코퍼스 (CORE_STRATEGY 파일들)
Track D — 워크플로 템플릿 (workflow_templates_text/)
Track E — 책 코퍼스 (*.md book files)
"""

from __future__ import annotations

import os
import re
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

from config import (
    BASE_DIR,
    BOOK_CANDIDATES,
    BOOK_CHUNK_OVERLAP,
    BOOK_CHUNK_SIZE,
    BOOK_SEPS,
    CHUNK_OVERLAP_BY_TYPE,
    CHUNK_SIZE_BY_TYPE,
    CORE_STRATEGY,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    SKIP_TEXT_FILES,
)
from enrichment import build_chunk
from text_utils import infer_language, read_text, split_text

# 타입 별칭
ChunkList = list[dict[str, Any]]
Stats = defaultdict[str, int]


# ── Track B/C: 핵심 코퍼스 ───────────────────────────────────────────────────

def process_core(rows: ChunkList, stats: Stats) -> None:
    """CORE_STRATEGY에 정의된 파일을 청킹합니다."""
    print("[Track B/C] core corpus")

    for file_name, strategy in CORE_STRATEGY.items():
        file_path = BASE_DIR / file_name
        if not file_path.exists():
            continue

        data_type = strategy["type"]
        chunk_size = CHUNK_SIZE_BY_TYPE.get(data_type, DEFAULT_CHUNK_SIZE)
        chunk_overlap = CHUNK_OVERLAP_BY_TYPE.get(data_type, DEFAULT_CHUNK_OVERLAP)

        content = read_text(file_path)
        chunks = split_text(content, chunk_size, chunk_overlap, strategy["seps"])

        for idx, chunk_text in enumerate(chunks):
            rows.append(
                build_chunk(
                    source_file=file_name,
                    source_path=file_name,
                    data_type=data_type,
                    language=infer_language(chunk_text, strategy["lang"]),
                    priority=strategy["priority"],
                    chunk_index=idx,
                    chunk_text=chunk_text,
                )
            )
            stats[data_type] += 1


# ── Track A: 공식 문서 ────────────────────────────────────────────────────────

_DOC_SEPS = ["\n### ", "\n## ", "\n# ", "\n\n", "\n"]
_DOC_CHUNK_SIZE = 800
_DOC_CHUNK_OVERLAP = 100


def process_docs(rows: ChunkList, stats: Stats) -> None:
    """final/docs/ 하위 마크다운 파일을 청킹합니다."""
    docs_dir = BASE_DIR / "docs"
    if not docs_dir.exists():
        return

    print("[Track A] official docs")

    for root, _, files in os.walk(docs_dir):
        for file in files:
            if not file.endswith(".md"):
                continue

            file_path = Path(root) / file
            rel_path = str(file_path.relative_to(BASE_DIR))
            parts = rel_path.split(os.sep)
            product_area = parts[1] if len(parts) > 2 else "general"

            content = read_text(file_path)
            chunks = split_text(content, _DOC_CHUNK_SIZE, _DOC_CHUNK_OVERLAP, _DOC_SEPS)

            for idx, chunk_text in enumerate(chunks):
                chunk = build_chunk(
                    source_file=file,
                    source_path=rel_path,
                    data_type="official_docs",
                    language="en",
                    priority=2,
                    chunk_index=idx,
                    chunk_text=chunk_text,
                )
                chunk["product_area"] = product_area
                rows.append(chunk)
                stats["official_docs"] += 1


# ── Track D: 워크플로 템플릿 ─────────────────────────────────────────────────

_JSON_MARKER = "[JSON source]"


def _extract_nodes_used(summary: str) -> str:
    """summary 블록에서 'Used nodes:' 행을 찾아 노드 목록 문자열을 반환합니다."""
    for line in summary.splitlines():
        lower = line.lower()
        if lower.startswith("used nodes:") or lower.startswith("사용된 노드 목록:"):
            return line.split(":", 1)[-1].strip().lower() or "generic"
    return "generic"


def _split_template_text(full_text: str) -> tuple[str, str]:
    """템플릿 텍스트를 summary 부분과 JSON 부분으로 나눕니다."""
    if _JSON_MARKER in full_text:
        left, right = full_text.split(_JSON_MARKER, 1)
        return left.strip(), right.strip()

    json_start = full_text.find("{\n")
    if json_start != -1:
        return full_text[:json_start].strip(), full_text[json_start:].strip()

    return full_text.strip(), ""


def process_templates(rows: ChunkList, stats: Stats) -> None:
    """workflow_templates_text/ 하위 .txt 파일을 parent-child 구조로 청킹합니다."""
    template_dir = BASE_DIR / "workflow_templates_text"
    if not template_dir.exists():
        return

    print("[Track D] workflow templates (parent-child)")

    for root, _, files in os.walk(template_dir):
        for file in files:
            if not file.endswith(".txt") or file in SKIP_TEXT_FILES:
                continue

            file_path = Path(root) / file
            rel_path = str(file_path.relative_to(BASE_DIR))
            full_text = read_text(file_path)

            summary_part, json_part = _split_template_text(full_text)
            nodes_used = _extract_nodes_used(summary_part)
            parent_id = str(uuid.uuid4())

            # 부모: summary
            rows.append({
                "chunk_global_id": parent_id,
                "doc_id": parent_id,
                "source_file": file,
                "source_path": rel_path,
                "data_type": "workflow_template",
                "language": infer_language(summary_part, "en"),
                "priority": 3,
                "chunk_index": 0,
                "chunk_size": len(summary_part),
                "chunk_role": "parent_summary",
                "node_name": nodes_used,
                "target_version": "all",
                "is_breaking_change": False,
                "page_content": summary_part,
            })
            stats["template_parent"] += 1

            # 자식: JSON (있을 때만)
            if json_part:
                rows.append({
                    "chunk_global_id": str(uuid.uuid4()),
                    "parent_id": parent_id,
                    "source_file": file,
                    "source_path": rel_path,
                    "data_type": "workflow_template",
                    "language": "en",
                    "priority": 3,
                    "chunk_index": 1,
                    "chunk_size": len(json_part),
                    "chunk_role": "child_json",
                    "node_name": nodes_used,
                    "target_version": "all",
                    "is_breaking_change": False,
                    "page_content": json_part,
                })
                stats["template_child"] += 1


# ── Track E: 책 코퍼스 ───────────────────────────────────────────────────────

_PAGE_PATTERN = re.compile(r"---\s*PAGE:\s*([0-9]+)\s*---")


def process_book(rows: ChunkList, stats: Stats) -> None:
    """BOOK_CANDIDATES 목록의 마크다운 파일을 청킹합니다."""
    print("[Track E] book corpus")

    for book_path in BOOK_CANDIDATES:
        if not book_path.exists():
            continue

        content = read_text(book_path)
        chunks = split_text(content, BOOK_CHUNK_SIZE, BOOK_CHUNK_OVERLAP, BOOK_SEPS)

        for idx, chunk_text in enumerate(chunks):
            chunk = build_chunk(
                source_file=book_path.name,
                source_path=str(book_path.relative_to(BASE_DIR)),
                data_type="book",
                language="ko",
                priority=2,
                chunk_index=idx,
                chunk_text=chunk_text,
            )
            page_match = _PAGE_PATTERN.search(chunk_text)
            chunk["product_area"] = (
                f"page_{page_match.group(1)}" if page_match else "general_theory"
            )
            rows.append(chunk)
            stats["book"] += 1
