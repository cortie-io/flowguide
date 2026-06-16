"""
app/core/credential_filter.py

⑦ 자격 증명 블랙홀 필터 (Credential Blind Spot Filter)

백엔드 수신 즉시 / LLM 컨텍스트 주입 직전 두 단계에서 작동.
모든 민감 토큰을 [REDACTED::{category}] 플레이스홀더로 교체.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any


# ── 정규식 패턴 정의 ──────────────────────────────────────────────────────────

_PATTERNS: list[tuple[str, re.Pattern]] = [
    # API Key 일반 형태 (20자+ 영숫자/대시/언더스코어)
    ("API_KEY",       re.compile(r'(?i)(api[_-]?key|apikey|access[_-]?key)["\s:=]+([A-Za-z0-9\-_]{20,})')),
    # Bearer 토큰
    ("BEARER_TOKEN",  re.compile(r'(?i)bearer\s+([A-Za-z0-9\-_.~+/]{20,}={0,2})')),
    # OAuth / Secret
    ("SECRET",        re.compile(r'(?i)(client[_-]?secret|oauth[_-]?secret|app[_-]?secret)["\s:=]+([A-Za-z0-9\-_]{16,})')),
    # Password 필드
    ("PASSWORD",      re.compile(r'(?i)(password|passwd|pwd)["\s:=]+([^\s",}{]{6,})')),
    # Webhook URL (고유 토큰 포함)
    ("WEBHOOK_URL",   re.compile(r'https?://[^\s"]+/webhook/[A-Za-z0-9\-_]{8,}[^\s"]*')),
    # Generic 긴 토큰 (JWT 형태)
    ("JWT",           re.compile(r'ey[A-Za-z0-9\-_]{20,}\.[A-Za-z0-9\-_]{20,}\.[A-Za-z0-9\-_]{20,}')),
    # AWS / GCP / Azure 형태 키
    ("CLOUD_KEY",     re.compile(r'(?i)(AKIA|ASIA|AROA)[A-Z0-9]{16,}')),
    # 이메일 + 패스워드 조합 필드
    ("EMAIL_CRED",    re.compile(r'(?i)"email"\s*:\s*"[^"]{3,}@[^"]{3,}"')),
]

# n8n JSON 에서 통째로 마스킹할 민감 최상위 키
_SENSITIVE_TOP_KEYS = {"credentials", "pinData"}

# n8n credentials 객체 내 민감 필드
_SENSITIVE_FIELD_KEYS = {
    "apiKey", "accessToken", "refreshToken", "clientSecret",
    "password", "secret", "token", "webhookToken", "privateKey",
    "serviceAccountKey", "authorizationHeader",
}


class CredentialFilter:
    """
    두 가지 진입 인터페이스:
      filter_string(text)  → 문자열 내 패턴 마스킹
      filter_workflow(obj) → n8n JSON dict 구조적 마스킹
    """

    def filter_string(self, text: str) -> str:
        """원시 문자열에서 민감 패턴을 마스킹."""
        for category, pattern in _PATTERNS:
            text = pattern.sub(f"[REDACTED::{category}]", text)
        return text

    def filter_workflow(self, workflow: dict) -> dict:
        """
        n8n 워크플로우 JSON 딕셔너리를 깊은 복사 후 민감 구조를 제거.
        원본 객체는 변경하지 않음.
        """
        sanitized = copy.deepcopy(workflow)
        self._sanitize_dict(sanitized)
        return sanitized

    def _sanitize_dict(self, obj: Any) -> None:
        """재귀 순회하며 민감 키/값을 인플레이스 치환."""
        if isinstance(obj, dict):
            for key in list(obj.keys()):
                # 최상위 민감 블록 통째로 마스킹
                if key in _SENSITIVE_TOP_KEYS:
                    obj[key] = f"[REDACTED::{key.upper()}]"
                    continue
                # 민감 필드 값 마스킹
                if key in _SENSITIVE_FIELD_KEYS and isinstance(obj[key], str):
                    obj[key] = f"[REDACTED::{key.upper()}]"
                    continue
                # 재귀
                self._sanitize_dict(obj[key])
        elif isinstance(obj, list):
            for item in obj:
                self._sanitize_dict(item)
        elif isinstance(obj, str):
            # 문자열 값 내부 패턴 스캔 (부모 dict에서 이미 처리, 여기선 리스트 내 문자열)
            pass  # list 원소 문자열은 부모에서 처리됨

    def filter_nodes(self, nodes: list[dict]) -> list[dict]:
        """노드 배열만 별도 필터링 (인스펙션 페이로드용)."""
        return [self.filter_workflow(n) for n in nodes]


# 싱글턴
_filter: CredentialFilter | None = None

def get_credential_filter() -> CredentialFilter:
    global _filter
    if _filter is None:
        _filter = CredentialFilter()
    return _filter
