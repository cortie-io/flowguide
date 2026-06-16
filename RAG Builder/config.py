"""
config.py
─────────
전역 경로, 청킹 전략, 공통 정규식 패턴을 한 곳에서 관리합니다.
설정 변경이 필요할 때 이 파일만 수정하면 됩니다.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

# ── 디렉터리 레이아웃 ─────────────────────────────────────────────────────────

ROOT: Path = Path(__file__).resolve().parent
BASE_DIR: Path = ROOT / "final"
ORIGIN_DIR: Path = ROOT / "origin"

BASE_DIR.mkdir(parents=True, exist_ok=True)

# ── 출력 파일 경로 ────────────────────────────────────────────────────────────

OUTPUT_JSONL = BASE_DIR / "final_rag_chunks_v2.jsonl"
OUTPUT_STATS = BASE_DIR / "final_rag_stats_v2.json"
OUTPUT_VECTOR_STATS = BASE_DIR / "final_vector_db_stats_v2.json"
DEFAULT_CHROMA_DIR = BASE_DIR / "chroma_db"

# ── 청킹 전략 타입 ────────────────────────────────────────────────────────────

class ChunkStrategy(TypedDict):
    type: str
    priority: int
    lang: str
    seps: list[str]


# ── 핵심 코퍼스 전략 (Track B / C) ───────────────────────────────────────────

CORE_STRATEGY: dict[str, ChunkStrategy] = {
    "n8n_properties_spec.txt": {
        "type": "spec",
        "priority": 1,
        "lang": "en",
        "seps": ["\nNode: ", "\n=====", "\n\n", "\n"],
    },
    "n8n_cli_spec.txt": {
        "type": "cli_spec",
        "priority": 1,
        "lang": "en",
        "seps": ["\n# ", "\n\n", "\n"],
    },
    "n8n_version_changelog.txt": {
        "type": "changelog",
        "priority": 1,
        "lang": "en",
        "seps": ["\n# Version:", "\n## ", "\n\n", "\n"],
    },
    "n8n_code_node_snippets.txt": {
        "type": "code_snippet",
        "priority": 1,
        "lang": "mixed",
        "seps": ["\n# ", "\n\n", "\n"],
    },
    "troubleshooting_faq.txt": {
        "type": "troubleshooting",
        "priority": 1,
        "lang": "ko",
        "seps": ["\n# ", "\n\n", "\n"],
    },
    "external_api_limits.txt": {
        "type": "api_limits",
        "priority": 1,
        "lang": "ko",
        "seps": ["\n# ", "\n\n", "\n"],
    },
}

# changelog 타입만 더 큰 청크 사용
CHUNK_SIZE_BY_TYPE: dict[str, int] = {"changelog": 1500}
CHUNK_OVERLAP_BY_TYPE: dict[str, int] = {"changelog": 250}
DEFAULT_CHUNK_SIZE = 1100
DEFAULT_CHUNK_OVERLAP = 170

# ── 변환 시 건너뛸 파일 ───────────────────────────────────────────────────────

SKIP_TEXT_FILES: frozenset[str] = frozenset(
    {"conversion_summary.txt", "conversion_failed_files.txt"}
)

# ── 책(Book) 코퍼스 후보 경로 (Track E) ──────────────────────────────────────

BOOK_CANDIDATES: list[Path] = [
    BASE_DIR / "n8n_업무자동화_일잘러되기.md",
    BASE_DIR / "n8n_업무자동화_일잘러되기_part2.md",
    BASE_DIR / "book.md",
]

BOOK_SEPS = ["\n# --- BOOK PAGE:", "\n### ", "\n## ", "\n\n", "\n"]
BOOK_CHUNK_SIZE = 1550
BOOK_CHUNK_OVERLAP = 210

# ── 원본 저장소 목록 ──────────────────────────────────────────────────────────

TEMPLATE_SOURCE_REPOS: list[Path] = [
    ORIGIN_DIR / "awesome-n8n-templates",
    ORIGIN_DIR / "n8n-workflow-templates",
]

# ── 정규식 패턴 ───────────────────────────────────────────────────────────────

SEMVER_PATTERN = re.compile(r"(?:n8n@|v)?(\d+)\.(\d+)\.(\d+)$")
BULLET_PATTERN = re.compile(r"^\s*[*-]\s+")
ISSUE_REF_PATTERN = re.compile(r"\s*\(\[#\d+\]\([^)]*\)\)\s*")
COMMIT_REF_PATTERN = re.compile(r"\s*\(\[[0-9a-f]{7,}\]\([^)]*\)\)\s*$", re.IGNORECASE)
KOREAN_PATTERN = re.compile(r"[가-힣]")
ASCII_PATTERN = re.compile(r"[A-Za-z]")
