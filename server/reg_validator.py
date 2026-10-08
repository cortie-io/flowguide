"""
server/reg_validator.py

EnhancedREGValidator — 출고 전 파라미터 오타 자동 수술기.

작동 원리:
  1. n8n_properties_spec.txt 에서 유효 속성명 세트를 로드한다.
  2. LLM 답변 스트림에서 {{ }} 표현식 및 JSON 키를 스캔한다.
  3. 스캔된 식별자가 valid_properties 에 없으면
     Levenshtein 편집 거리 ≤ 2 인 가장 유사한 올바른 속성명으로 치환한다.
  4. 치환이 발생한 경우 reg_warning SSE 이벤트를 발행한다.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Sequence

log = logging.getLogger("naito.reg_validator")

# ── 유효 속성명 세트 로드 ───────────────────────────────────────────────────

_SPEC_PATH_CANDIDATES = [
    Path(__file__).parent.parent / "RAG_dataset" / "n8n_properties_spec.txt",
    Path(__file__).parent / "n8n_properties_spec.txt",
]

_CORE_VALID_PROPERTIES: set[str] = {
    # 핵심 n8n 파라미터 (spec 파일이 없을 때 폴백 세트)
    "operation", "resource", "authentication", "credentials",
    "method", "url", "headers", "body", "qs", "responseFormat",
    "jsonParameters", "bodyParametersJson", "headerParametersJson",
    "queryParametersJson", "options", "additionalFields", "filters",
    "limit", "returnAll", "batchSize", "waitBetweenRequests",
    "retryOnFail", "maxTries", "waitBetweenTries", "continueOnFail",
    "onError", "alwaysOutputData", "executeOnce", "notesInFlow",
    "fieldToSplitOut", "include", "disableDotNotation",
    "mode", "jsCode", "pythonCode", "language",
    "values", "assignments", "mappingMode",
    "conditions", "combineOperation", "fallbackOutput",
    "sortFieldsUi", "operator", "value1", "value2",
    "fromEmail", "toEmail", "subject", "text", "html", "attachments",
    "webhookId", "path", "httpMethod", "responseMode", "responseData",
    "chatId", "text", "parseMode", "disableNotification",
    "sheetId", "sheetName", "range", "valueInputOption", "valueRenderOption",
    "documentId", "tableId", "databaseId", "boardId", "listId",
    "owner", "repo", "issueNumber", "pullRequestNumber",
    "channel", "username", "text", "iconEmoji", "iconUrl",
    "bucketName", "fileName", "region", "acl",
    "expression", "dataPropertyName", "outputFieldName",
    "triggerOn", "events", "includeHeaders", "rawBody",
    "workflowId", "executionId", "runData",
    "pollTimes", "interval", "unit",
    "type", "name", "position", "parameters", "typeVersion",
    "id", "connections", "nodes", "settings", "staticData",
    "pinData", "versionId", "meta",
}


def _load_spec_properties() -> set[str]:
    """n8n_properties_spec.txt 에서 camelCase 속성명을 파싱."""
    for path in _SPEC_PATH_CANDIDATES:
        if not path.exists():
            continue
        props: set[str] = set()
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("- name:"):
                        name = line[7:].strip().strip("'\"")
                        if name and re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
                            props.add(name)
        except OSError as e:
            log.warning("[REG] spec 파일 읽기 실패: %s", e)
            return _CORE_VALID_PROPERTIES
        if props:
            log.info("[REG] spec 로드 완료: %d 개 유효 속성명", len(props))
            return props | _CORE_VALID_PROPERTIES

    log.warning("[REG] spec 파일 없음 — 코어 세트(%d개)로 폴백", len(_CORE_VALID_PROPERTIES))
    return _CORE_VALID_PROPERTIES


# 모듈 로드 시 1회 초기화
_VALID_PROPERTIES: set[str] = _load_spec_properties()

# ── Levenshtein 거리 계산 ─────────────────────────────────────────────────────

def _levenshtein(s: str, t: str) -> int:
    """DP 기반 Levenshtein 편집 거리 계산 (O(mn))."""
    m, n = len(s), len(t)
    if m == 0: return n
    if n == 0: return m

    # 공간 절약: 두 행만 유지
    prev = list(range(n + 1))
    curr = [0] * (n + 1)

    for i in range(1, m + 1):
        curr[0] = i
        for j in range(1, n + 1):
            cost = 0 if s[i - 1] == t[j - 1] else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev, curr = curr, [0] * (n + 1)

    return prev[n]


def _best_match(token: str, candidates: Sequence[str], max_dist: int = 2) -> str | None:
    """candidates 중 편집 거리 ≤ max_dist 인 가장 유사한 항목 반환."""
    best_dist = max_dist + 1
    best_match = None
    for cand in candidates:
        # 길이 차이가 너무 나면 스킵 (속도 최적화)
        if abs(len(token) - len(cand)) > max_dist:
            continue
        d = _levenshtein(token, cand)
        if d < best_dist:
            best_dist = d
            best_match = cand
    return best_match if best_dist <= max_dist else None


# ── 스캔 패턴 ─────────────────────────────────────────────────────────────────

# n8n 표현식 내 필드명: {{ $json.fieldName }} 또는 {{ $node["X"].json.fieldName }}
_EXPR_FIELD_RE = re.compile(
    r'\{\{\s*\$(?:json|node\["[^"]+"\]\.json)\.([a-zA-Z_][a-zA-Z0-9_.]*)',
)

# JSON 키: "paramName": 형태
_JSON_KEY_RE = re.compile(r'"([a-zA-Z_][a-zA-Z0-9_]{2,})"(?:\s*:)')

# 무시 목록 (너무 짧거나 범용적)
_SKIP_TOKENS: set[str] = {
    "id", "type", "name", "text", "url", "key", "mode", "data", "body",
    "true", "false", "null", "json", "node", "item", "value", "field",
    # n8n 워크플로우 JSON의 구조적 래퍼 키 — 특정 노드의 파라미터가 아니라
    # connections/nodes 배열 자체의 스키마를 구성하는 고정 키이므로, 파라미터명
    # 오타 후보로 취급하면 안 된다. 발견 경위: 파일럿 평가 스크립트(eval/) 실행 중
    # connections 객체의 "main" 키가 valid_properties의 "mail"과 편집거리 1이라는
    # 이유로 오탐지되어 "main" → "mail"로 잘못 교정 제안된 사례를 실제로 확인함.
    "main", "index", "connections", "parameters", "position",
    "credentials", "settings", "staticdata", "pindata", "typeversion",
}


class EnhancedREGValidator:
    """
    LLM 답변 텍스트에서 n8n 속성명 오타를 감지하고 In-place 치환한다.
    """

    def __init__(self, valid_properties: set[str] | None = None):
        self.valid_properties: set[str] = valid_properties or _VALID_PROPERTIES
        self._sorted_props = sorted(self.valid_properties)

    def validate_and_fix(self, text: str) -> tuple[str, list[dict]]:
        """
        텍스트 내 잘못된 속성명을 감지하고 올바른 이름으로 치환한다.

        Returns:
            (fixed_text, corrections)
            corrections: [{"original": "...", "corrected": "...", "distance": int}, ...]
        """
        corrections: list[dict] = []
        fixed = text

        # 1. 표현식 내 필드명 검사
        for match in _EXPR_FIELD_RE.finditer(text):
            field = match.group(1).split(".")[0]  # 첫 번째 세그먼트만
            if field in _SKIP_TOKENS or field in self.valid_properties:
                continue
            if len(field) < 3:
                continue
            suggestion = _best_match(field, self._sorted_props)
            if suggestion:
                corrections.append({
                    "original": field,
                    "corrected": suggestion,
                    "distance": _levenshtein(field, suggestion),
                    "context": "expression",
                })
                fixed = fixed.replace(
                    f"$json.{field}", f"$json.{suggestion}", 1
                )
                log.debug("[REG] expr 치환: %s → %s", field, suggestion)

        # 2. JSON 파라미터 키 검사 (n8n 코드 블록 내)
        code_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        for block in code_blocks:
            for match in _JSON_KEY_RE.finditer(block):
                key = match.group(1)
                if key in _SKIP_TOKENS or key in self.valid_properties:
                    continue
                if len(key) < 4:
                    continue
                suggestion = _best_match(key, self._sorted_props)
                if suggestion and suggestion != key:
                    corrections.append({
                        "original": key,
                        "corrected": suggestion,
                        "distance": _levenshtein(key, suggestion),
                        "context": "json_key",
                    })
                    # 코드 블록 내에서만 치환 (오탐 방지)
                    old_frag = f'"{key}":'
                    new_frag = f'"{suggestion}":'
                    fixed = fixed.replace(old_frag, new_frag, 1)
                    log.debug("[REG] json_key 치환: %s → %s", key, suggestion)

        return fixed, corrections

    def build_warning_event(self, corrections: list[dict]) -> dict:
        """SSE reg_warning 이벤트 페이로드 생성."""
        return {
            "type": "reg_warning",
            "count": len(corrections),
            "corrections": corrections,
            "message": (
                f"REG 검증: {len(corrections)}개 속성명 자동 수정됨 "
                "(Levenshtein ≤ 2 In-place Repair)"
            ),
        }


# ── 싱글턴 ────────────────────────────────────────────────────────────────────

_reg_validator_instance: EnhancedREGValidator | None = None


def get_reg_validator() -> EnhancedREGValidator:
    global _reg_validator_instance
    if _reg_validator_instance is None:
        _reg_validator_instance = EnhancedREGValidator()
    return _reg_validator_instance
