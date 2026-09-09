"""
templates.py
────────────
n8n 워크플로 JSON 파일을 RAG용 텍스트 블록으로 변환합니다.

주요 흐름:
    origin/{repo}/**/*.json
        → convert_workflow_templates()
        → final/workflow_templates_text/{repo}/**/*.txt
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import BASE_DIR, TEMPLATE_SOURCE_REPOS
from text_utils import clean_markdown

# ── 내부 상수 ─────────────────────────────────────────────────────────────────

_SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._\- ]+")
_MAX_FILENAME_LEN = 180


# ── 결과 집계 데이터클래스 ────────────────────────────────────────────────────

@dataclass
class ConversionResult:
    total_json: int = 0
    success: int = 0
    failed: int = 0
    by_repo: dict[str, int] = field(default_factory=dict)
    failures: list[tuple[str, str]] = field(default_factory=list)


# ── 노드 정보 추출 헬퍼 ───────────────────────────────────────────────────────

def _node_label(node_type: str) -> str:
    """'n8n-nodes-base.httpRequest' → 'httpRequest'"""
    if not isinstance(node_type, str):
        return "UnknownNode"
    return node_type.split(".")[-1] if "." in node_type else node_type


def _unique_node_labels(nodes: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    labels: list[str] = []
    for node in nodes:
        label = _node_label(node.get("type", "UnknownNode"))
        if label not in seen:
            seen.add(label)
            labels.append(label)
    return labels


def _extract_description(
    data: dict[str, Any],
    nodes: list[dict[str, Any]],
    node_labels: list[str],
) -> str:
    """
    설명 후보를 우선순위대로 탐색합니다.
    1. stickyNote 노드의 content (가장 긴 것)
    2. 노드의 notes 필드 (최대 8개 합산)
    3. 워크플로 name 기반 자동 생성
    4. 노드 목록 기반 자동 생성
    """
    sticky_notes: list[str] = []
    node_notes: list[str] = []

    for node in nodes:
        if not isinstance(node, dict):
            continue

        notes = node.get("notes", "")
        if isinstance(notes, str) and notes.strip():
            node_notes.append(notes)

        params = node.get("parameters", {})
        if (
            isinstance(params, dict)
            and str(node.get("type", "")).endswith(".stickyNote")
        ):
            content = params.get("content", "")
            if isinstance(content, str) and content.strip():
                sticky_notes.append(content)

    if sticky_notes:
        return clean_markdown(max(sticky_notes, key=len))[:1200]

    if node_notes:
        return clean_markdown(" ".join(node_notes[:8]))[:800]

    name = data.get("name", "")
    if isinstance(name, str) and name.strip():
        if node_labels:
            nodes_preview = ", ".join(node_labels[:10])
            return (
                f"Workflow '{name.strip()}' uses nodes such as "
                f"{nodes_preview} to automate a multi-step process."
            )
        return f"Workflow '{name.strip()}' automates a multi-step process in n8n."

    if node_labels:
        return (
            "This n8n workflow automates a multi-step process using nodes such as "
            + ", ".join(node_labels[:10])
            + "."
        )

    return "This n8n workflow JSON includes automation logic and node configuration."


# ── JSON → 텍스트 블록 변환 ───────────────────────────────────────────────────

def _to_text_block(repo_name: str, rel_path: str, data: dict[str, Any]) -> str:
    """단일 워크플로 JSON 데이터를 RAG 텍스트 블록으로 직렬화합니다."""
    name = data.get("name") or Path(rel_path).stem
    if not isinstance(name, str) or not name.strip():
        name = Path(rel_path).stem

    nodes: list[dict[str, Any]] = (
        data.get("nodes") if isinstance(data.get("nodes"), list) else []
    )
    node_labels = _unique_node_labels(nodes)
    description = _extract_description(data, nodes, node_labels)

    lines = [
        f"Template name: {name.strip()}",
        f"Source repository: {repo_name}",
        f"Source path: {rel_path}",
        "Used nodes: " + (", ".join(node_labels) if node_labels else "(unknown)"),
        "Description: " + description,
        "",
        "[JSON source]",
        json.dumps(data, ensure_ascii=False, indent=2),
        "",
    ]
    return "\n".join(lines)


def _safe_filename(name: str) -> str:
    """파일시스템에 안전한 이름으로 정규화합니다."""
    cleaned = _SAFE_NAME_PATTERN.sub("_", name).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:_MAX_FILENAME_LEN] if cleaned else "workflow"


# ── 메인 변환 함수 ────────────────────────────────────────────────────────────

def convert_workflow_templates() -> ConversionResult:
    """
    TEMPLATE_SOURCE_REPOS의 모든 JSON 파일을 텍스트로 변환해
    final/workflow_templates_text/ 아래에 저장합니다.
    변환 결과 요약을 conversion_summary.txt에 기록합니다.
    """
    output_dir = BASE_DIR / "workflow_templates_text"
    output_dir.mkdir(parents=True, exist_ok=True)

    result = ConversionResult()

    for source in TEMPLATE_SOURCE_REPOS:
        if not source.exists():
            print(f"[WARN] missing source repository: {source}")
            continue

        repo_name = source.name
        result.by_repo.setdefault(repo_name, 0)

        for json_path in source.rglob("*.json"):
            # 숨김 디렉터리 건너뜀
            if any(part.startswith(".") for part in json_path.parts):
                continue

            result.total_json += 1
            rel_path = str(json_path.relative_to(source))

            try:
                data = json.loads(json_path.read_text(encoding="utf-8", errors="ignore"))
                if not isinstance(data, dict):
                    raise ValueError("JSON root is not an object")

                text_content = _to_text_block(repo_name, rel_path, data)

                out_dir = output_dir / repo_name / Path(rel_path).parent
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / (_safe_filename(Path(rel_path).stem) + ".txt")
                out_path.write_text(text_content, encoding="utf-8")

                result.success += 1
                result.by_repo[repo_name] += 1

            except Exception as exc:
                result.failed += 1
                result.failures.append((f"{repo_name}/{rel_path}", str(exc)))

    _write_conversion_summary(output_dir, result)
    return result


def _write_conversion_summary(output_dir: Path, result: ConversionResult) -> None:
    lines = [
        "Workflow template text conversion summary",
        "======================================",
        f"Total JSON discovered: {result.total_json}",
        f"Successful conversions: {result.success}",
        f"Failed conversions: {result.failed}",
        "",
        "Per repository:",
        *[f"- {repo}: {count}" for repo, count in sorted(result.by_repo.items())],
    ]
    (output_dir / "conversion_summary.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    if result.failures:
        with (output_dir / "conversion_failed_files.txt").open("w", encoding="utf-8") as f:
            for path, reason in result.failures:
                f.write(f"{path}\t{reason}\n")
