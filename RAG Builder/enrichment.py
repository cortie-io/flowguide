"""
enrichment.py
─────────────
RAG 청크에 공통 메타데이터를 추가하는 함수를 제공합니다.
node_name·version·breaking-change 여부를 텍스트에서 자동 추출합니다.
"""

from __future__ import annotations

import re
import uuid
from typing import Any


# ── 메타데이터 추출 패턴 ──────────────────────────────────────────────────────

_NODE_PATTERN = re.compile(
    r"(?:Node|Service|케이스|API\s*[0-9]+|Used nodes):\s*([A-Za-z0-9_\-\., ]+)"
)
_VERSION_PATTERN = re.compile(
    r"(?:Version|v|버전):\s*([0-9]+(?:\.[0-9]+){1,2})"
)
_BREAKING_PATTERN = re.compile(
    r"Breaking Changes|파괴적 변경", flags=re.IGNORECASE
)


# ── 공통 청크 스키마 생성 ─────────────────────────────────────────────────────

def build_chunk(
    *,
    source_file: str,
    source_path: str,
    data_type: str,
    language: str,
    priority: int,
    chunk_index: int,
    chunk_text: str,
) -> dict[str, Any]:
    """
    RAG 청크 딕셔너리를 생성합니다.

    텍스트 상단 5줄에서 노드명·버전을 추출하고,
    전체 텍스트에서 Breaking Change 여부를 판단합니다.
    """
    top_lines = "\n".join(chunk_text.split("\n")[:5])

    node_match = _NODE_PATTERN.search(top_lines)
    version_match = _VERSION_PATTERN.search(top_lines)
    is_breaking = bool(_BREAKING_PATTERN.search(chunk_text))

    node_name = node_match.group(1).strip().lower() if node_match else "generic"

    return {
        "chunk_global_id": str(uuid.uuid4()),
        "source_file": source_file,
        "source_path": source_path,
        "data_type": data_type,
        "language": language,
        "priority": priority,
        "chunk_index": chunk_index,
        "chunk_size": len(chunk_text),
        "chunk_role": "standalone",
        "node_name": node_name or "generic",
        "target_version": version_match.group(1) if version_match else "all",
        "is_breaking_change": is_breaking,
        "page_content": chunk_text,
    }


def sanitize_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """
    ChromaDB에 저장할 수 없는 타입(list, dict 등)을 JSON 문자열로 변환합니다.
    None은 그대로 유지합니다.
    """
    import json

    return {
        k: v if isinstance(v, (str, int, float, bool)) or v is None
        else json.dumps(v, ensure_ascii=False)
        for k, v in meta.items()
    }
