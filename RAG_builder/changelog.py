"""
changelog.py
────────────
n8n GitHub 릴리즈 페이지에서 안정 버전(v1.0.0+) 릴리즈 노트를 수집해
final/n8n_version_changelog.txt로 저장합니다.

외부 의존성: curl (subprocess 경유)
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config import BASE_DIR, BULLET_PATTERN, COMMIT_REF_PATTERN, ISSUE_REF_PATTERN, SEMVER_PATTERN

SemVer = tuple[int, int, int]

# ── GitHub API 호출 ───────────────────────────────────────────────────────────

_RELEASES_URL = "https://api.github.com/repos/n8n-io/n8n/releases"
_CURL_HEADERS = [
    "-H", "Accept: application/vnd.github+json",
    "-H", "User-Agent: n8n-rag-builder",
]
_MIN_VERSION: SemVer = (1, 0, 0)


def _fetch_release_page(page: int) -> list[dict[str, Any]]:
    url = f"{_RELEASES_URL}?per_page=100&page={page}"
    result = subprocess.run(
        ["curl", "-sL", *_CURL_HEADERS, url],
        capture_output=True, text=True, check=True,
    )
    payload = result.stdout.strip()
    if not payload:
        return []
    data = json.loads(payload)
    return data if isinstance(data, list) else []


def _parse_semver(tag: str) -> SemVer | None:
    m = SEMVER_PATTERN.search(tag.strip())
    return tuple(int(x) for x in m.groups()) if m else None  # type: ignore[return-value]


# ── 릴리즈 노트 파싱 ──────────────────────────────────────────────────────────

def _classify_section(title: str) -> str:
    lower = title.lower()
    if "breaking" in lower:
        return "breaking"
    if "feature" in lower:
        return "features"
    if "fix" in lower or "bug" in lower:
        return "bug_fixes"
    return "other"


def _clean_bullet(text: str) -> str:
    text = ISSUE_REF_PATTERN.sub("", text)
    text = COMMIT_REF_PATTERN.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_release_body(body: str) -> dict[str, list[str]]:
    """릴리즈 노트 본문을 섹션별로 분류합니다."""
    sections: dict[str, list[str]] = {
        "breaking": [], "features": [], "bug_fixes": [], "other": []
    }
    current_key = "other"
    current_bullet = ""

    for raw_line in body.splitlines():
        line = raw_line.strip()

        if not line:
            if current_bullet:
                if cleaned := _clean_bullet(current_bullet):
                    sections[current_key].append(cleaned)
                current_bullet = ""
            continue

        if line.startswith("### "):
            if current_bullet:
                if cleaned := _clean_bullet(current_bullet):
                    sections[current_key].append(cleaned)
                current_bullet = ""
            current_key = _classify_section(line[4:].strip())
            continue

        if line.startswith("## "):
            continue

        if BULLET_PATTERN.match(line):
            if current_bullet:
                if cleaned := _clean_bullet(current_bullet):
                    sections[current_key].append(cleaned)
            current_bullet = BULLET_PATTERN.sub("", line)
            continue

        if current_bullet:
            current_bullet = f"{current_bullet} {line}"

    if current_bullet:
        if cleaned := _clean_bullet(current_bullet):
            sections[current_key].append(cleaned)

    # features 섹션이 비어있으면 other에서 노드 관련 항목으로 채움
    if not sections["features"]:
        sections["features"] = [
            item for item in sections["other"]
            if " node" in item.lower() or item.lower().startswith("**")
        ][:8]

    return sections


# ── changelog 텍스트 생성 ─────────────────────────────────────────────────────

def _format_release(version: SemVer, meta: dict[str, Any]) -> list[str]:
    """단일 릴리즈를 텍스트 줄 목록으로 포맷합니다."""
    sections = _parse_release_body(meta.get("body", ""))
    ver_str = ".".join(str(x) for x in version)
    date_str = (meta.get("published_at") or "")[:10] or "(unknown)"

    def _bullet_lines(items: list[str], limit: int, fallback: str) -> list[str]:
        if items:
            return [f"  * {item}" for item in items[:limit]]
        return [f"  * {fallback}"]

    return [
        f"# Version: v{ver_str}",
        f"- Release Date: {date_str}",
        f"- Release URL: {meta.get('url', '')}",
        "- Breaking Changes:",
        *_bullet_lines(sections["breaking"], 20, "(none noted in this release)"),
        "- New Nodes & Features:",
        *_bullet_lines(sections["features"], 30, "(no explicit feature section in release notes)"),
        "- Bug Fixes & Adjustments:",
        *_bullet_lines(sections["bug_fixes"], 40, "(none listed)"),
        *(
            ["- Other Changes:", *[f"  * {item}" for item in sections["other"][:20]]]
            if sections["other"]
            else []
        ),
        "",
    ]


# ── 공개 API ──────────────────────────────────────────────────────────────────

def refresh_changelog() -> int:
    """
    GitHub에서 모든 안정 릴리즈를 수집해 changelog 파일을 갱신합니다.

    Returns:
        수집된 릴리즈 수
    """
    releases: list[dict[str, Any]] = []
    page = 1

    while True:
        items = _fetch_release_page(page)
        if not items:
            break

        for item in items:
            version = _parse_semver(item.get("tag_name", ""))
            if version is None or version < _MIN_VERSION:
                continue
            if item.get("draft") or item.get("prerelease"):
                continue

            releases.append({
                "version": version,
                "published_at": item.get("published_at") or item.get("created_at") or "",
                "url": item.get("html_url") or "",
                "body": (item.get("body") or "").strip(),
            })

        page += 1

    releases.sort(key=lambda x: x["version"], reverse=True)

    lines: list[str] = [
        "n8n Version Changelog (v1.0.0+ Stable Releases)",
        "================================================",
        f"Generated at: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%SZ')}",
        "Source: https://github.com/n8n-io/n8n/releases",
        "Filter: draft=false, prerelease=false, version>=1.0.0",
        f"Total releases collected: {len(releases)}",
        "",
    ]

    for rel in releases:
        lines.extend(_format_release(rel["version"], rel))

    out_path = BASE_DIR / "n8n_version_changelog.txt"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return len(releases)
