"""
app/core/intent_router.py

Single Unified Workspace의 두뇌.
유저 메시지 + 첨부 컨텍스트(노드 JSON, 에러 로그, 코드 투척) 를 분석하여
5대 기능 Intent 중 하나로 분기한다.

Intent 열거:
  CURRICULUM      ① 커리큘럼 요청
  EXPRESSION      ② 수식 생성 (노드 인스펙션 데이터 동반)
  WORKFLOW_BUILD  ③ 노드 배치 / 워크플로우 최적화
  ERROR_PATCH     ④ 에러 로그 수신 → 원격 수술
  REVERSE         ⑤ 대형 n8n JSON 투척 → 리버스 엔지니어링
  GENERAL         일반 Q&A (RAG 기반 답변)
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

# ── Intent 정의 ────────────────────────────────────────────────────────────────

class Intent(str, Enum):
    CURRICULUM     = "CURRICULUM"
    EXPRESSION     = "EXPRESSION"
    WORKFLOW_BUILD = "WORKFLOW_BUILD"
    ERROR_PATCH    = "ERROR_PATCH"
    REVERSE        = "REVERSE"
    GENERAL        = "GENERAL"


# ── 분기 시그널 패턴 ─────────────────────────────────────────────────────────

_CURRICULUM_KW = re.compile(
    r"커리큘럼|로드맵|학습\s*계획|단계별\s*공부|입문|심화|마스터",
    re.IGNORECASE,
)
_EXPRESSION_KW = re.compile(
    r"수식|expression|표현식|\$json|\$node|필드\s*추출|값\s*가져오기|어떻게\s*접근",
    re.IGNORECASE,
)
_BUILD_KW = re.compile(
    r"노드\s*배치|만들어\s*줘|워크플로우\s*(만|짜|설계|구성)|자동화\s*만|플로우\s*(짜|구성)",
    re.IGNORECASE,
)
_OPTIMIZE_KW = re.compile(
    r"최적화|리팩터|리팩토링|느려|OOM|rate\s*limit|개선|효율|느린",
    re.IGNORECASE,
)
_REVERSE_KW = re.compile(
    r"분석해\s*줘|이\s*플로우\s*(어떻게|뭐하는)|설명해\s*줘|리버스|역분석",
    re.IGNORECASE,
)
# n8n JSON 구조 감지 (connections 키 존재)
_N8N_JSON_PATTERN = re.compile(r'"connections"\s*:\s*\{', re.DOTALL)
# 에러 토큰 패턴
_ERROR_PATTERN = re.compile(
    r"error|exception|failed|cannot|undefined|null.*is not|"
    r"에러|오류|실패|접근\s*불가|작동\s*(안|불)가",
    re.IGNORECASE,
)


class IntentRouter:
    """
    우선순위 기반 Intent 분류기.
    첨부 컨텍스트(node_data, error_log, raw_json)가 있으면
    텍스트 패턴보다 컨텍스트 타입을 우선한다.
    """

    def route(
        self,
        message: str,
        node_data:  dict | None = None,   # 익스텐션 → 노드 인스펙션 페이로드
        error_log:  str  | None = None,   # 익스텐션 → 에러 인터럽트 페이로드
        raw_json:   str  | None = None,   # 유저가 채팅에 붙여넣은 n8n JSON
    ) -> Intent:

        # 1순위: 에러 로그 첨부 → 무조건 ERROR_PATCH
        if error_log and _ERROR_PATTERN.search(error_log):
            return Intent.ERROR_PATCH

        # 2순위: 대형 n8n JSON 감지 (raw_json 또는 메시지 내 JSON 블록)
        json_candidate = raw_json or message
        if _N8N_JSON_PATTERN.search(json_candidate):
            return Intent.REVERSE

        # 3순위: 노드 인스펙션 데이터 첨부 + 수식 요청
        if node_data and _EXPRESSION_KW.search(message):
            return Intent.EXPRESSION

        # 4순위: 텍스트 패턴
        if _CURRICULUM_KW.search(message):
            return Intent.CURRICULUM
        if _BUILD_KW.search(message) or _OPTIMIZE_KW.search(message):
            return Intent.WORKFLOW_BUILD
        if _REVERSE_KW.search(message):
            return Intent.REVERSE
        if _EXPRESSION_KW.search(message):
            return Intent.EXPRESSION

        return Intent.GENERAL

    def describe(self, intent: Intent) -> str:
        """디버그/로깅용 설명 반환."""
        return {
            Intent.CURRICULUM:     "① 커리큘럼 퓨전 생성",
            Intent.EXPRESSION:     "② 수식 동적 생성 (노드 인스펙션)",
            Intent.WORKFLOW_BUILD: "③ 워크플로우 합성 / 최적화",
            Intent.ERROR_PATCH:    "④ 에러 원격 수술",
            Intent.REVERSE:        "⑤ 토폴로지 리버스 엔지니어링",
            Intent.GENERAL:        "General RAG Q&A",
        }[intent]
