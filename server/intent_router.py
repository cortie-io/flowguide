"""
intent_router.py

LLM 기반 Intent 분류기.
명백한 컨텍스트 시그널(에러 로그, n8n JSON 첨부)은 규칙으로 즉시 처리.
나머지 모든 경우는 LLM이 문맥을 읽고 판단.

Intent 열거:
  CURRICULUM      ① 커리큘럼 요청
  EXPRESSION      ② 수식 생성 (노드 인스펙션 데이터 동반)
  WORKFLOW_BUILD  ③ 노드 배치 / 워크플로우 최적화
  ERROR_PATCH     ④ 에러 로그 수신 → 원격 수술
  REVERSE         ⑤ 특정 워크플로우 분석/설명/해석
  GENERAL         일반 Q&A (RAG 기반 답변)
"""

from __future__ import annotations

import re
import json
import logging
from enum import Enum
from typing import Any

log = logging.getLogger(__name__)

# ── Intent 정의 ────────────────────────────────────────────────────────────────

class Intent(str, Enum):
    CURRICULUM     = "CURRICULUM"
    EXPRESSION     = "EXPRESSION"
    WORKFLOW_BUILD = "WORKFLOW_BUILD"
    ERROR_PATCH    = "ERROR_PATCH"
    REVERSE        = "REVERSE"
    GENERAL        = "GENERAL"


# ── 명백한 컨텍스트 시그널 (규칙 처리) ─────────────────────────────────────────

_N8N_JSON_PATTERN = re.compile(r'"connections"\s*:\s*\{', re.DOTALL)
_ERROR_PATTERN = re.compile(
    r"error|exception|failed|cannot|undefined|null.*is not|"
    r"에러|오류|실패|접근\s*불가|작동\s*(안|불)가",
    re.IGNORECASE,
)

# ── LLM 분류 프롬프트 ──────────────────────────────────────────────────────────

_CLASSIFY_SYSTEM = """\
당신은 n8n 자동화 어시스턴트의 인텐트 분류기입니다.
사용자 메시지를 읽고 아래 6가지 인텐트 중 하나만 출력하십시오.
다른 말은 절대 출력하지 말고 인텐트 이름 하나만 출력하십시오.

인텐트 정의:
- CURRICULUM: n8n 학습 계획, 로드맵, 커리큘럼, 단계별 학습 요청
- EXPRESSION: $json, $node 수식/표현식 생성, 필드 접근 방법 질문
- WORKFLOW_BUILD: 새 워크플로우 만들기, 자동화 설계/구현/짜줘 요청
- ERROR_PATCH: 에러 메시지/로그 분석, 오류 해결 요청
- REVERSE: 특정 워크플로우/플로우를 분석/설명/해석/이해 요청, 또는 n8n에 있는 워크플로우 JSON을 가져오기/불러오기/조회 요청 (이름 있든 없든 "이 플로우", "그 워크플로우" 등 특정 대상 지칭 시)
- GENERAL: n8n 개념 설명, 노드 사용법, 일반 질문

판단 기준 — 헷갈리는 케이스:
- "XXX 플로우 설명해줘" → REVERSE (특정 플로우 대상)
- "Webhook 노드 설명해줘" → GENERAL (개념/노드 설명)
- "워크플로우 어떻게 만들어?" → GENERAL (방법론 질문)
- "이 워크플로우 어떻게 동작해?" → REVERSE (특정 대상)
- "n8n에서 json 코드 가져와줘" / "워크플로우 불러와줘" / "JSON 가져오기" → REVERSE (워크플로우 가져오기 요청)
- "슬랙 알림 자동화 만들어줘" → WORKFLOW_BUILD
- "$json.name 어떻게 써?" → EXPRESSION
- n8n_connected=true + "플로우 설명/분석/봐줘/가져와" → REVERSE

컨텍스트:
{context_block}

사용자 메시지: {message}"""


async def _call_llm_classify(message: str, context_block: str, model: str, openai_api_key: str | None) -> str:
    """Ollama 또는 OpenAI로 인텐트 분류 요청 (non-streaming)."""
    from config import settings

    system = _CLASSIFY_SYSTEM.format(context_block=context_block, message=message)

    # OpenAI 경로
    if model.startswith("openai:") and openai_api_key:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=openai_api_key)
            resp = await client.chat.completions.create(
                model=model[len("openai:"):],
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": message},
                ],
                max_tokens=10,
                temperature=0,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            log.warning("[IntentRouter] OpenAI 분류 실패: %s", e)
            return ""

    # Ollama 경로
    import httpx
    target_model = model if model and not model.startswith("openai:") else settings.llm_model
    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
        "stream": False,
        "options": {"temperature": 0, "num_predict": 10},
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()
    except Exception as e:
        log.warning("[IntentRouter] Ollama 분류 실패: %s", e)
        return ""


def _parse_intent(raw: str) -> Intent | None:
    """LLM 출력에서 Intent 추출."""
    raw = raw.strip().upper()
    for intent in Intent:
        if intent.value in raw:
            return intent
    return None


# ── 꼬리 물기 감지 (빠른 규칙) ────────────────────────────────────────────────

_FOLLOWUP_KW = re.compile(
    r"^.{0,60}(더\s*(자세|설명|알려)|예시|계속|그\s*(거|노드|기능|방식|부분)|이\s*(거|노드|부분)|방금|앞에서|위에서|아까|좀\s*더|구체적)",
    re.IGNORECASE,
)


class IntentRouter:
    """
    LLM + 키워드 하이브리드 Intent 분류기.
    명백한 시그널은 규칙으로 즉시 처리.
    나머지는 키워드 시그널을 항상 함께 계산해두고, LLM 결과를 기본으로 쓰되
    LLM이 실패하거나 확신 없이 GENERAL로 도망갈 때 키워드 시그널로 구제한다.
    """

    async def route(
        self,
        message: str,
        model: str = "",
        node_data:  dict | None = None,
        error_log:  str  | None = None,
        raw_json:   str  | None = None,
        history:    list | None = None,
        n8n_url:    str  | None = None,
        openai_api_key: str | None = None,
    ) -> Intent:

        # ── 규칙 1: 에러 로그 첨부 → 무조건 ERROR_PATCH
        if error_log and _ERROR_PATTERN.search(error_log):
            return Intent.ERROR_PATCH

        # ── 규칙 2: n8n JSON 첨부 (raw_json 또는 메시지 내 JSON) → REVERSE
        json_candidate = raw_json or message
        if _N8N_JSON_PATTERN.search(json_candidate):
            return Intent.REVERSE

        # ── 규칙 3: 꼬리 물기 → 이전 intent 유지
        if history and _FOLLOWUP_KW.search(message):
            prev = self._last_intent(history)
            if prev is not None:
                return prev

        # 키워드 시그널은 LLM 호출 성패와 무관하게 항상 먼저 계산해둔다.
        keyword_guess = self._keyword_guess(message, node_data)

        # ── LLM 분류
        context_lines = []
        if n8n_url:
            context_lines.append(f"n8n_connected=true (URL: {n8n_url})")
        if node_data:
            context_lines.append(f"node_data_attached=true (type: {node_data.get('type', '?')})")
        if raw_json:
            context_lines.append("raw_json_attached=true")
        context_block = "\n".join(context_lines) if context_lines else "없음"

        raw_result = await _call_llm_classify(message, context_block, model, openai_api_key)
        llm_intent = _parse_intent(raw_result)

        if llm_intent:
            # LLM이 확신 없어 GENERAL로 답했는데 키워드는 구체적 의도를 가리키면
            # 키워드 쪽을 채택 (LLM의 "모르겠음" 회피를 구제).
            if llm_intent is Intent.GENERAL and keyword_guess and keyword_guess is not Intent.GENERAL:
                log.info(
                    "[IntentRouter] LLM=GENERAL 이지만 키워드 시그널=%s 로 구제: %r",
                    keyword_guess, message,
                )
                return keyword_guess
            log.info("[IntentRouter] LLM 분류 결과: %r → %s", raw_result, llm_intent)
            return llm_intent

        # ── LLM 호출 자체가 실패했을 때만 키워드로 완전 폴백
        log.warning("[IntentRouter] LLM 분류 실패, 키워드 폴백 사용")
        return keyword_guess or Intent.GENERAL

    def _keyword_guess(self, message: str, node_data: dict | None) -> Intent | None:
        """키워드 기반 의도 시그널. 매칭 없으면 None (GENERAL로 단정하지 않음)."""
        m = message.lower()
        if any(k in m for k in ["커리큘럼", "로드맵", "학습 계획"]):
            return Intent.CURRICULUM
        if any(k in m for k in ["만들어줘", "짜줘", "구현해줘", "설계해줘"]) and "워크플로우" in m:
            return Intent.WORKFLOW_BUILD
        if any(k in m for k in [
            "분석해줘", "역분석", "리버스",
            "가져와", "가져오", "불러와", "불러오", "임포트", "import",
        ]):
            return Intent.REVERSE
        if node_data and any(k in m for k in ["수식", "expression", "$json"]):
            return Intent.EXPRESSION
        return None

    def _last_intent(self, history: list) -> "Intent | None":
        """history에서 가장 최근 user 턴의 intent를 추출."""
        for turn in reversed(history):
            intent_val = getattr(turn, "intent", None) or (turn.get("intent") if isinstance(turn, dict) else None)
            if intent_val:
                try:
                    return Intent(str(intent_val).replace("Intent.", ""))
                except ValueError:
                    pass
        return None

    def describe(self, intent: Intent) -> str:
        return {
            Intent.CURRICULUM:     "① 커리큘럼 퓨전 생성",
            Intent.EXPRESSION:     "② 수식 동적 생성 (노드 인스펙션)",
            Intent.WORKFLOW_BUILD: "③ 워크플로우 합성 / 최적화",
            Intent.ERROR_PATCH:    "④ 에러 원격 수술",
            Intent.REVERSE:        "⑤ 토폴로지 리버스 엔지니어링",
            Intent.GENERAL:        "General RAG Q&A",
        }[intent]
