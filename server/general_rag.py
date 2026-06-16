"""
app/services/general_rag.py

Intent.GENERAL 분기 처리 — 일반 n8n Q&A RAG 서비스.
5대 특수 기능에 해당하지 않는 모든 질의가 여기로 온다.
"""

from __future__ import annotations

import json
import logging
import re
from typing import AsyncGenerator

from config import settings

log = logging.getLogger("nodi.services.general")


def sse(event: str, data: dict | str) -> str:
    payload = json.dumps(data, ensure_ascii=False) if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


_GENERAL_SYSTEM_PROMPT = """\
당신은 n8n 워크플로우 자동화 전문 튜터입니다.
아래 [검색된 컨텍스트]에 근거하여 초보자부터 전문가까지 누구나 이해할 수 있도록 체계적으로 답변하십시오.

## 출력 형식 규칙 (반드시 마크다운으로 작성)

**구조 템플릿:**
```
## 핵심 요약
한 문장으로 핵심을 설명

## 상세 설명
개념과 원리를 단계별로 서술

## 실전 활용법
- 사용 시나리오 1
- 사용 시나리오 2

## 주의사항 (해당되는 경우)
중요한 주의점
```

**필수 포맷 규칙:**
- 섹션 제목은 `##` 헤더 사용
- 목록은 `- ` 불릿 또는 `1.` 번호 사용
- 핵심 키워드는 **볼드** 강조
- 파라미터/노드명은 `백틱` 코드 형식
- 코드 예시는 반드시 ```json 또는 ```javascript 블록
- 제품명은 반드시 **n8n** (nn, N8N 금지)
- 컨텍스트에 없는 내용은 "확인되지 않습니다"로 명시
- 한 문단은 최대 2~3문장으로 유지
- 서로 다른 주제는 반드시 빈 줄로 분리
- 목록이 2개 이상이면 문장으로 늘어놓지 말고 반드시 목록으로 정리

[검색된 컨텍스트]
{context}
"""


_NODE_DETAIL_SYSTEM_PROMPT = """\
당신은 n8n 노드 전문 튜터입니다.
아래 [검색된 컨텍스트]를 근거로 노드와 속성을 초보자도 이해할 수 있게 체계적으로 설명하십시오.

## 출력 형식 규칙 (반드시 마크다운으로 작성)

**노드 전체 설명 시 — 다음 순서를 반드시 지킬 것:**
```
## [노드명] 노드란?
한 줄 정의: 이 노드는 ___입니다.

## 언제 사용하나요?
- 상황 1
- 상황 2

## 동작 방식
단계별 흐름 설명 (1→2→3)

## 주요 속성
- **`속성명`** (`타입`): 설명. 기본값: `값`
- **`속성명`** (`타입`): 설명

## 유사 노드와 차이점 (해당되는 경우)
| 노드 | 특징 |
|------|------|
| Switch | 여러 분기 가능 |
| IF | 참/거짓 2개 분기만 |

## 주의사항
중요한 함정이나 제한사항
```

**특정 속성 질문 시:**
```
## `속성명` 속성
- **정의**: 무엇을 하는 속성인지
- **타입**: options / boolean / string 등
- **선택지**: 각 값의 의미
- **언제 쓰는지**: 실제 사용 시나리오
- **기본값**: 기본적으로 어떻게 설정되어 있는지
```

**필수 포맷 규칙:**
- 섹션 제목은 `##` 사용
- 속성명은 **`백틱+볼드`** 형식: **`operationMode`**
- 목록은 `- ` 불릿
- 코드는 반드시 코드 블록
- 제품명은 **n8n** (nn, N8N 금지)
- ※ 속성 설명 후: "(LEG: n8n_properties_spec 기반 팩트)"
- 한 문단은 최대 2~3문장으로 유지
- 서로 다른 설명 블록은 빈 줄로 분리

[검색된 컨텍스트]
{context}
"""


_GREETING_PATTERN = re.compile(
    r"^(안녕|안녕하세요|하이|hello|hi|hey|반가워|반갑|처음|시작)" ,
    re.IGNORECASE,
)


_GREETING_RESPONSE = """## Nodi에 오신 걸 환영합니다

안녕하세요. 저는 **n8n 자동화 튜터 Nodi**입니다.

도와드릴 수 있는 대표 영역은 아래와 같습니다.

## 바로 할 수 있는 것

- **워크플로우 설계**: 원하는 자동화를 단계별로 설계
- **노드 설명**: 특정 노드, 속성, 표현식을 쉬운 말로 설명
- **디버깅**: 에러 원인 분석과 수정 방법 정리
- **커리큘럼 제안**: 실습 중심 학습 로드맵 제공

## 이렇게 질문하면 좋습니다

1. `Webhook`과 `Schedule Trigger` 차이를 설명해줘
2. `HTTP Request` 노드로 외부 API 호출 예시 만들어줘
3. PostgreSQL과 n8n을 연동하는 실전 흐름 보여줘
4. 이 에러 로그를 보고 원인과 해결책을 정리해줘

## 답변 방식

- 문단을 나눠서 설명합니다.
- 여러 항목은 목록이나 표로 정리합니다.
- 노드명과 파라미터명은 영문 원문 그대로 유지합니다.

원하는 작업이나 막힌 지점을 바로 말씀해 주세요."""


def _is_greeting(message: str) -> bool:
    return bool(_GREETING_PATTERN.search(message.strip()))


_CORE_NODE_ALIASES = {
    "switch": "Switch n8n-nodes-base.switch route items rules expression",
    "if": "If n8n-nodes-base.if branch condition true false",
    "set": "Set n8n-nodes-base.set edit fields values",
    "code": "Code n8n-nodes-base.code javascript python",
    "webhook": "Webhook n8n-nodes-base.webhook trigger",
    "http request": "HTTP Request n8n-nodes-base.httpRequest api request",
    "schedule trigger": "Schedule Trigger n8n-nodes-base.scheduleTrigger cron",
    "manual trigger": "Manual Trigger n8n-nodes-base.manualTrigger",
}


def _looks_like_node_question(message: str) -> bool:
    lowered = message.lower()
    return (
        "노드" in message
        or "node" in lowered
        or "속성" in message
        or "파라미터" in message
        or "옵션" in message
        or any(alias in lowered for alias in _CORE_NODE_ALIASES)
    )


def _expand_query(message: str) -> str:
    lowered = message.lower()
    extras: list[str] = []

    for alias, expansion in _CORE_NODE_ALIASES.items():
        if alias in lowered:
            extras.append(expansion)

    english_node = re.search(r"([A-Za-z][A-Za-z0-9\s-]{1,40})노드", message)
    if english_node:
        token = " ".join(english_node.group(1).split())
        extras.append(f"{token} node")

    return " ".join(part for part in [message, *extras] if part).strip()


def _node_hints(message: str) -> list[str]:
    lowered = message.lower()
    hints: list[str] = []

    for alias, expansion in _CORE_NODE_ALIASES.items():
        if alias in lowered:
            hints.append(alias)
            hints.extend(expansion.lower().split())

    english_node = re.search(r"([A-Za-z][A-Za-z0-9\s-]{1,40})노드", message)
    if english_node:
        hints.extend(english_node.group(1).lower().split())

    return list(dict.fromkeys(h for h in hints if len(h) >= 2))


def _rerank_node_chunks(chunks: list[dict], message: str) -> list[dict]:
    hints = _node_hints(message)
    if not hints:
        return chunks

    def score(chunk: dict) -> tuple[int, int]:
        haystack = " ".join(
            str(chunk.get(k, "")) for k in ("title", "source", "text")
        ).lower()
        exact = sum(1 for hint in hints if hint in haystack)
        official_bonus = 1 if chunk.get("data_type") == "official_docs" else 0
        return (exact, official_bonus)

    return sorted(chunks, key=score, reverse=True)


_TYPE_COLOR = {
    "string":   "#60A5FA",
    "number":   "#34D399",
    "boolean":  "#FBBF24",
    "options":  "#A78BFA",
    "fixedCollection": "#F87171",
    "collection": "#F87171",
    "json":     "#FB923C",
    "dateTime": "#38BDF8",
}

_CORE_NODE_PROP_HINTS: dict[str, list[dict]] = {
    "switch": [
        {"name": "mode", "displayName": "Mode", "type": "options", "description": "Expression 또는 Rules 기반 분기 방식 선택"},
        {"name": "fallbackOutput", "displayName": "Fallback Output", "type": "options", "description": "매칭 규칙 없을 때 출력: None / Extra Output / Output 0"},
        {"name": "rules", "displayName": "Rules", "type": "fixedCollection", "description": "각 규칙: 값 비교 조건 → 특정 출력 포트로 라우팅"},
        {"name": "allMatchingOutputs", "displayName": "Output All Matching Outputs", "type": "boolean", "description": "true면 여러 규칙에 매칭 시 모든 포트로 출력"},
        {"name": "ignoreCase", "displayName": "Ignore Case", "type": "boolean", "description": "문자열 비교 시 대소문자 무시 여부"},
    ],
    "if": [
        {"name": "conditions", "displayName": "Conditions", "type": "fixedCollection", "description": "AND/OR 조건 그룹 — 참이면 true 포트, 거짓이면 false 포트"},
        {"name": "combineOperation", "displayName": "Combine Conditions", "type": "options", "description": "ALL (AND) 또는 ANY (OR)"},
        {"name": "operator", "displayName": "Operator", "type": "options", "description": "equals / notEquals / contains / gt / lt 등"},
    ],
    "set": [
        {"name": "mode", "displayName": "Mode", "type": "options", "description": "Manual 또는 JSON으로 필드 지정 방식 선택"},
        {"name": "assignments", "displayName": "Assignments", "type": "fixedCollection", "description": "필드명 + 값 + 타입을 직접 지정"},
        {"name": "include", "displayName": "Include", "type": "options", "description": "All / Selected / None — 기존 필드 포함 범위"},
    ],
    "code": [
        {"name": "mode", "displayName": "Mode", "type": "options", "description": "Run Once For All Items / Run Once For Each Item"},
        {"name": "language", "displayName": "Language", "type": "options", "description": "JavaScript 또는 Python"},
        {"name": "jsCode", "displayName": "JavaScript Code", "type": "string", "description": "items 배열을 받아 가공 후 return items 형태로 반환"},
    ],
    "webhook": [
        {"name": "path", "displayName": "Path", "type": "string", "description": "URL 경로 — https://yourn8n.com/webhook/{path}"},
        {"name": "httpMethod", "displayName": "HTTP Method", "type": "options", "description": "GET / POST / PUT / PATCH / DELETE"},
        {"name": "responseMode", "displayName": "Respond", "type": "options", "description": "Immediately / Using Respond to Webhook Node"},
        {"name": "responseData", "displayName": "Response Data", "type": "options", "description": "All Entries / First Entry JSON / Binary"},
    ],
    "httprequest": [
        {"name": "method", "displayName": "Method", "type": "options", "description": "GET / POST / PUT / PATCH / DELETE / HEAD"},
        {"name": "url", "displayName": "URL", "type": "string", "description": "요청 대상 URL (표현식 사용 가능)"},
        {"name": "authentication", "displayName": "Authentication", "type": "options", "description": "None / Generic Credential Type / n8n Custom Auth"},
        {"name": "sendBody", "displayName": "Send Body", "type": "boolean", "description": "요청 바디 포함 여부 (POST/PUT 등)"},
        {"name": "sendHeaders", "displayName": "Send Headers", "type": "boolean", "description": "커스텀 헤더 추가 여부"},
        {"name": "retryOnFail", "displayName": "Retry On Fail", "type": "boolean", "description": "실패 시 자동 재시도 활성화"},
    ],
}


def _build_property_card(chunks: list[dict], query: str) -> dict | None:
    """
    검색된 청크에서 노드 속성 카드 데이터를 구성한다.
    spec 청크에 properties가 있거나, 코어 노드 힌트가 있을 때 반환.
    """
    # 어떤 노드가 질문됐는지 추론
    q_lower = query.lower()
    detected_node: str | None = None
    for alias in _CORE_NODE_PROP_HINTS:
        if alias in q_lower:
            detected_node = alias
            break

    # 특정 속성 질문인지 확인
    prop_query: str | None = None
    prop_kw_match = re.search(
        r"(?:속성|파라미터|옵션|property|parameter|option)\s*[:\-]?\s*([A-Za-z][A-Za-z0-9\s]{2,30})",
        query, re.IGNORECASE
    )
    if prop_kw_match:
        prop_query = prop_kw_match.group(1).strip().lower()

    # spec 청크에서 properties 수집
    all_props: list[dict] = []
    node_name_from_chunk: str = ""
    for c in chunks:
        if c.get("data_type") == "spec" and c.get("properties"):
            all_props.extend(c["properties"][:12])
            if not node_name_from_chunk and c.get("node_name") and c["node_name"] != "generic":
                node_name_from_chunk = c["node_name"]

    # 특정 속성 필터링
    if prop_query and all_props:
        filtered = [p for p in all_props if prop_query in p.get("name","").lower() or prop_query in p.get("displayName","").lower()]
        if filtered:
            all_props = filtered

    # 코어 노드 힌트 사용
    hint_props = _CORE_NODE_PROP_HINTS.get(detected_node, []) if detected_node else []
    if not all_props and hint_props:
        all_props = hint_props

    if not all_props:
        return None

    # 카드 데이터 구성
    node_display = node_name_from_chunk or (detected_node.title() if detected_node else "Node")
    return {
        "node_name":   node_display,
        "prop_filter": prop_query,
        "properties":  [
            {
                "name":        p.get("name", ""),
                "displayName": p.get("displayName", p.get("name", "")),
                "type":        p.get("type", "string"),
                "default":     p.get("default", ""),
                "description": p.get("description", ""),
                "color":       _TYPE_COLOR.get(p.get("type", "string"), "#94A3B8"),
            }
            for p in all_props[:10]
        ],
    }


class GeneralRAGService:
    def __init__(self, engine):
        self.engine = engine

    async def stream(self, ctx: dict) -> AsyncGenerator[str, None]:
        from workflow_services import _sync_retrieve, _sync_retrieve_spec, _build_context, _stream_llm
        import asyncio
        from functools import partial

        query = ctx["message"]

        if _is_greeting(query):
            for chunk in re.split(r"(\n\n)", _GREETING_RESPONSE):
                if chunk:
                    yield sse("token", chunk)
            return

        expanded_query = _expand_query(query)
        filter_types = {"spec", "official_docs"} if _looks_like_node_question(query) else None

        loop = asyncio.get_event_loop()

        if filter_types is not None:
            # 노드/속성 질문 → spec 전용 인덱스 사용
            chunks = await loop.run_in_executor(
                None,
                partial(_sync_retrieve_spec, self.engine, expanded_query, 8)
            )
            if chunks:
                chunks = _rerank_node_chunks(chunks, query)
            # spec 결과 없으면 일반 검색으로 폴백
            if not chunks:
                chunks = await loop.run_in_executor(
                    None,
                    partial(_sync_retrieve, self.engine, expanded_query, None, 8)
                )
        else:
            chunks = await loop.run_in_executor(
                None,
                partial(_sync_retrieve, self.engine, expanded_query, None, 8)
            )

        if not chunks:
            system = (
                _NODE_DETAIL_SYSTEM_PROMPT if filter_types is not None else _GENERAL_SYSTEM_PROMPT
            ).format(context="(검색된 컨텍스트 없음 — RAG 엔진 미초기화 상태)")
        else:
            context_str = _build_context(chunks)
            system = (
                _NODE_DETAIL_SYSTEM_PROMPT if filter_types is not None else _GENERAL_SYSTEM_PROMPT
            ).format(context=context_str)

        # 구조화된 속성 카드 이벤트 먼저 발행 (spec 청크에 properties 있을 때)
        if filter_types is not None:
            prop_card = _build_property_card(chunks, query)
            if prop_card:
                yield sse("node_property_card", prop_card)

        user = (
            f"{ctx['message']}\n\n"
            "n8n 전문가로서 한국어로 답변해주세요. "
            "제품명은 반드시 n8n으로 정확히 표기하고, 파라미터명은 영문 유지. "
            "반드시 마크다운 형식으로 답변하고, 제목/문단/목록을 사용해 가독성 좋게 정리해주세요. "
            "문장을 길게 한 덩어리로 쓰지 말고 주제마다 빈 줄로 분리해주세요."
        )

        async for token in _stream_llm(system, user, ctx["model"]):
            yield sse("token", token)
