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

log = logging.getLogger("naito.services.general")


def sse(event: str, data: dict | str) -> str:
    payload = json.dumps(data, ensure_ascii=False) if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


_GENERAL_SYSTEM_PROMPT = """\
[CRITICAL] 이모지 및 특수 기호(🚀💡✨ 등)를 절대 사용하지 마십시오. 순수 마크다운만 사용.
[CRITICAL] [검색된 컨텍스트]를 주요 근거로 삼되, 컨텍스트가 부족한 경우 n8n에 대한 일반 지식을 보완적으로 활용하십시오.
[CRITICAL] 확인할 수 없는 내용은 "확인되지 않은 내용입니다"라고 명시하십시오.

당신은 n8n 워크플로우 자동화 전문 튜터입니다.
단순한 요약이 아닌, 실무자가 즉시 활용할 수 있는 수준의 상세하고 깊이 있는 답변을 제공하십시오.

**답변 원칙:**
- 개념 설명 → 실제 사용 방법 → 예시 코드/설정 → 주의사항 순으로 전개
- 추상적 설명이 아닌 구체적인 파라미터값, 설정 방법, 실제 예시를 포함
- 관련 노드나 패턴이 있으면 함께 언급
- 흔한 실수나 트러블슈팅 포인트 포함

**포맷 규칙:**
- 섹션 제목: `##` 헤더
- 목록: `- ` 불릿 또는 `1.` 번호
- 핵심 키워드: **볼드**
- 노드/파라미터명: `백틱`
- 코드: ```json 또는 ```javascript 블록
- 제품명: **n8n** (nn, N8N 금지)

[검색된 컨텍스트]
{context}
"""


_NODE_DETAIL_SYSTEM_PROMPT = """\
[CRITICAL] 이모지 및 특수 기호를 절대 사용하지 마십시오. 순수 마크다운만 사용.
[CRITICAL] [검색된 컨텍스트]를 우선 근거로 삼되, 일반적인 n8n 노드 지식으로 보완하십시오.
[CRITICAL] "(LEG: ...)" 또는 "(팩트)" 등 출처 표기를 절대 추가하지 마십시오.

당신은 n8n 노드 전문 튜터입니다.
노드에 대한 완전하고 상세한 설명을 제공하십시오.

## 답변 구조 (항상 이 구조로 작성)

### 노드 개요
이 노드가 무엇인지, 어떤 상황에서 사용하는지 3~4문장으로 설명.

### 주요 파라미터
각 파라미터의 역할, 허용값, 기본값을 상세히 설명. 코드 예시 포함.

### 실제 사용 예시
구체적인 사용 사례와 설정값을 코드 블록으로 제시.

### 연결 패턴
이 노드 앞뒤에 자주 오는 노드와 그 이유.

### 주의사항 및 트러블슈팅
흔한 실수, 에러 케이스, 해결 방법.

**포맷 규칙:**
- 속성명: **`백틱+볼드`** 형식
- 코드: 반드시 코드 블록
- 제품명: **n8n** (nn, N8N 금지)

[검색된 컨텍스트]
{context}
"""


_GREETING_PATTERN = re.compile(
    r"^(안녕|안녕하세요|하이|hello|hi|hey|반가워|반갑|처음|시작)" ,
    re.IGNORECASE,
)


_GREETING_RESPONSE = """## Naito에 오신 걸 환영합니다

안녕하세요. 저는 **n8n 자동화 튜터 Naito**입니다.

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


# ── 노드 존재 검증 레이어 ──────────────────────────────────────────

_NODE_QUERY_PATTERNS = [
    re.compile(r"([A-Za-z][A-Za-z0-9 ]{2,50}?)\s*노드란", re.IGNORECASE),
    re.compile(r"([A-Za-z][A-Za-z0-9 ]{2,50}?)\s*노드\s*(설명|사용법|뭐야|무엇|이란|에 대해|어떻게|란|알려|소개|가 뭐|가 어떤)", re.IGNORECASE),
    re.compile(r"([A-Za-z][A-Za-z0-9 ]{2,50}?)\s*(이란|란|가 뭐야|가 무엇|을 설명|에 대해)\s*\??$", re.IGNORECASE),
    re.compile(r"([A-Za-z][A-Za-z0-9 ]{2,50}?)\s+Trigger\b.*노드", re.IGNORECASE),
    re.compile(r"([A-Za-z][A-Za-z0-9 ]{2,50}?)\s+Node\b.*란", re.IGNORECASE),
]

_IGNORED_QUERY_TARGETS = {
    "n8n", "the", "this", "what", "해당", "이", "그", "해당 노드", "어떤", "특정",
    "a", "an", "trigger", "node",
}


def _extract_node_query_target(message: str) -> str | None:
    """
    "MeshNetwork Trigger 노드란?" → "MeshNetwork Trigger"
    특정 노드를 물어보는 패턴일 때 노드명을 반환한다.
    일반 질문("노드 연결법이 뭐야?" 등)에서는 None 반환.
    """
    for pattern in _NODE_QUERY_PATTERNS:
        m = pattern.search(message.strip())
        if m:
            name = m.group(1).strip()
            if (
                len(name) >= 3
                and name.lower() not in _IGNORED_QUERY_TARGETS
                and not name.lower().startswith("n8n ")
            ):
                return name
    return None


_GENERIC_NODE_WORDS = {"trigger", "node", "action", "event", "service", "api", "tool", "connector"}


def _node_in_ontology(node_name: str) -> bool:
    """
    453-노드 온톨로지에서 해당 노드명이 존재하는지 확인.
    - 양방향 문자열 포함 일치
    - 단어 교집합은 의미 있는 단어(generic 단어 제외)에 한해서만 적용
    """
    try:
        from ontology_enhancer import _ALL_NODE_DEFS, _KO_TO_SHORT
    except Exception:
        return True  # import 실패 시 안전하게 True 반환 (차단하지 않음)

    name_lower = node_name.lower().strip()
    name_words = set(name_lower.split())
    # 의미 있는 단어만 추출 (generic 단어 제외)
    meaningful_words = name_words - _GENERIC_NODE_WORDS

    for node in _ALL_NODE_DEFS:
        dn = node.display_name.lower()
        st = node.short_type.lower()
        # 1. 양방향 부분 일치 (길이 3 이상인 경우만)
        if len(name_lower) >= 4 and (name_lower in dn or dn in name_lower):
            return True
        if len(name_lower) >= 4 and (name_lower in st or st in name_lower):
            return True
        # 2. 의미 있는 단어 전체 일치 (generic 단어 제외 후 모두 일치)
        if meaningful_words:
            dn_meaningful = set(dn.split()) - _GENERIC_NODE_WORDS
            if meaningful_words and meaningful_words == dn_meaningful:
                return True
            # camelCase short_type에서 분리된 단어들과도 비교
            st_meaningful = set(re.sub(r"([A-Z])", r" \1", node.short_type).lower().split()) - _GENERIC_NODE_WORDS
            if meaningful_words and meaningful_words == st_meaningful:
                return True

    if node_name in _KO_TO_SHORT:
        return True

    return False


def _node_in_chunks(node_name: str, chunks: list[dict]) -> bool:
    """RAG 검색 결과에 해당 노드명이 실제로 등장하는지 확인."""
    name_lower = node_name.lower()
    words = node_name.split()
    # camelCase 변환 (예: "HTTP Request" → "httpRequest")
    camel = words[0].lower() + "".join(w.capitalize() for w in words[1:]) if len(words) > 1 else name_lower

    for chunk in chunks:
        haystack = " ".join(
            str(chunk.get(k, "")) for k in ("title", "source", "text", "node_type", "node_name")
        ).lower()
        if name_lower in haystack or camel.lower() in haystack:
            return True
    return False


_NOT_FOUND_SUGGEST = """\
### 혹시 이런 노드를 찾고 계신가요?

찾으시는 기능이 있다면 아래 노드들을 확인해 보세요.

**이벤트/트리거 관련:**
- **Webhook** — 외부 서비스에서 HTTP 요청을 받아 워크플로우 시작
- **Schedule Trigger** — 크론(Cron) 기반 주기 실행
- **Manual Trigger** — 수동으로 워크플로우 실행

**데이터 수신/연동:**
- **HTTP Request** — 외부 API 호출
- **MQTT Trigger** — IoT/메시지 브로커 연동
- **WebSocket Trigger** — 실시간 소켓 이벤트 수신

원하시는 자동화 시나리오를 말씀해 주시면 적합한 노드를 추천해 드리겠습니다.\
"""


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
        from workflow_services import _sync_retrieve, _sync_retrieve_spec, _build_context, _stream_llm, _build_rag_sources
        import asyncio
        from functools import partial

        query = ctx.get("rag_query") or ctx["message"]

        if _is_greeting(ctx["message"]):
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

        # ── 노드 존재 검증 (Layer 1: LLM 호출 전 차단) ───────────────
        specific_node = _extract_node_query_target(ctx["message"])
        if specific_node and filter_types is not None:
            in_ontology = _node_in_ontology(specific_node)
            in_chunks   = _node_in_chunks(specific_node, chunks)

            if not in_ontology and not in_chunks:
                # 온톨로지 + RAG 모두 해당 노드 없음 → 존재하지 않는 노드
                log.info("[AntiHallucination] 미존재 노드 요청 차단: '%s'", specific_node)
                not_found = (
                    f"**{specific_node}** 노드는 n8n 공식 노드 목록에 존재하지 않습니다.\n\n"
                    "이 이름의 노드는 n8n에 내장되어 있지 않으며, "
                    "저의 지식 베이스(RAG 코퍼스)에도 관련 문서가 없습니다.\n\n"
                    + _NOT_FOUND_SUGGEST
                )
                for chunk in re.split(r"(\n\n)", not_found):
                    if chunk:
                        yield sse("token", chunk)
                return

            if not in_chunks and in_ontology:
                # 노드는 실존하지만 RAG에 상세 문서 없음 → 제한 주의
                log.info("[AntiHallucination] 온톨로지에는 있으나 RAG 문서 없음: '%s'", specific_node)

        if not chunks:
            context_str = "(검색된 컨텍스트 없음 — RAG 엔진 미초기화 상태)"
        else:
            context_str = _build_context(chunks)

        base_prompt = _NODE_DETAIL_SYSTEM_PROMPT if filter_types is not None else _GENERAL_SYSTEM_PROMPT
        system = base_prompt.format(context=context_str)

        # ── 노드 존재하나 문서 부족 시 system에 경고 주입 ─────────────
        if specific_node and filter_types is not None:
            if not _node_in_chunks(specific_node, chunks) and _node_in_ontology(specific_node):
                system += (
                    f"\n\n[⚠ 컨텍스트 경고] '{specific_node}' 노드는 n8n에 존재하지만 "
                    "현재 검색된 컨텍스트에 해당 노드의 상세 문서가 없습니다. "
                    "확인된 기본 정보만 제공하고, 속성이나 동작 방식을 추측하거나 창작하지 마십시오. "
                    "정보가 부족하면 솔직하게 '상세 정보를 확인할 수 없습니다'라고 답하십시오."
                )

        # 온톨로지 힌트 주입 (ANTI-PATTERN / RECOMMEND / BEST-PRACTICE 등)
        ontology_hints: list = ctx.get("ontology_hints") or []
        if ontology_hints:
            system += "\n\n[온톨로지 힌트 — 답변 시 반드시 참고]\n" + "\n".join(f"- {h}" for h in ontology_hints)

        # 오타 교정 주입 — LLM이 원래 의도를 정확히 인식하도록
        typo_corrections: list = ctx.get("typo_corrections") or []
        if typo_corrections:
            lines = "\n".join(f"  - '{orig}' → {canon}" for orig, canon in typo_corrections)
            system += (
                "\n\n[⚠ 오타 자동 교정 — 매우 중요]\n"
                "사용자가 입력한 단어에 오타가 감지되어 아래와 같이 교정하였습니다.\n"
                + lines + "\n"
                "규칙:\n"
                "1. 오타 단어(교정 전)는 실제로 존재하지 않는 용어입니다. 절대 별도 개념으로 설명하지 마십시오.\n"
                "2. '비공식 표현', '구어체', '약어' 등으로 정당화하지 마십시오.\n"
                "3. 교정된 공식 노드명만 기준으로 답변하십시오.\n"
                "4. 필요하다면 답변 첫 줄에 '(입력하신 [오타]는 [교정어]의 오타로 인식됩니다)'라고 한 줄 언급 후 본론으로 넘어가십시오."
            )

        # 구조화된 속성 카드 이벤트 먼저 발행 (spec 청크에 properties 있을 때)
        if filter_types is not None:
            prop_card = _build_property_card(chunks, query)
            if prop_card:
                yield sse("node_property_card", prop_card)

        image_urls: list = ctx.get("image_urls") or []
        if image_urls:
            system += (
                "\n\n[첨부 이미지 분석 지침]\n"
                "사용자가 이미지를 첨부했습니다. 이미지를 주의 깊게 분석하여 다음을 수행하세요:\n"
                "- n8n 워크플로우 스크린샷이면: 노드 구성, 연결 관계, 설정 오류, 개선점을 분석하세요.\n"
                "- 에러 메시지/로그 스크린샷이면: 에러 원인과 해결 방법을 구체적으로 설명하세요.\n"
                "- 텍스트가 포함된 이미지이면: 내용을 읽고 관련 n8n 컨텍스트에서 분석하세요.\n"
                "- 이미지에서 명확히 보이는 내용만 언급하고, 추측하지 마세요."
            )

        user = (
            f"{ctx['message']}\n\n"
            "n8n 전문가로서 한국어로 답변해주세요. "
            "제품명은 반드시 n8n으로 정확히 표기하고, 파라미터명은 영문 유지. "
            "반드시 마크다운 형식으로 답변하고, 제목/문단/목록을 사용해 가독성 좋게 정리해주세요. "
            "문장을 길게 한 덩어리로 쓰지 말고 주제마다 빈 줄로 분리해주세요."
        )

        async for token in _stream_llm(system, user, ctx["model"], history=ctx.get("history"), openai_api_key=ctx.get("openai_api_key"), image_urls=ctx.get("image_urls")):
            yield sse("token", token)

        if chunks:
            yield sse("rag_sources", {"sources": _build_rag_sources(chunks)})
