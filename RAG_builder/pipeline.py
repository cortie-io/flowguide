"""
pipeline.py
───────────
Track A~E 프로세서를 순서대로 실행해 JSONL과 통계 파일을 생성합니다.
main.py에서만 호출하며, 각 Track은 processors.py에 구현되어 있습니다.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from config import OUTPUT_JSONL, OUTPUT_STATS
from processors import process_book, process_core, process_docs, process_templates


def run() -> dict[str, Any]:
    """
    전체 전처리 파이프라인을 실행합니다.

    Returns:
        통계 딕셔너리 (total_ingested_chunks, distribution_by_data_type 등)
    """
    rows: list[dict[str, Any]] = []
    stats: defaultdict[str, int] = defaultdict(int)

    process_core(rows, stats)
    process_docs(rows, stats)
    process_templates(rows, stats)
    process_book(rows, stats)

    _write_jsonl(rows)

    total = len(rows)
    avg_size = sum(c["chunk_size"] for c in rows) / total if total else 0.0

    parent_count = stats.get("template_parent", 0)
    child_count = stats.get("template_child", 0)

    summary = {
        "total_ingested_chunks": total,
        "average_chunk_character_length": round(avg_size, 2),
        "distribution_by_data_type": dict(stats),
        "output_jsonl": str(OUTPUT_JSONL),
        "template_parent_count": parent_count,
        "template_child_count": child_count,
        "template_parent_child_balanced": parent_count == child_count,
    }
    OUTPUT_STATS.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def _write_jsonl(rows: list[dict[str, Any]]) -> None:
    with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
