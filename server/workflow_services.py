"""
app/services/curriculum.py  — ① 온톨로지 기반 동적 커리큘럼 퓨전
app/services/expression.py  — ② 수식 자동 생성기
app/services/workflow_build.py — ③ Parent-Child 코드 합성 + 최적화
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ProcessPoolExecutor
from typing import AsyncGenerator, Any

from config import settings
from session import SessionStore

log = logging.getLogger("nodi.services")

# BM25 연산 전용 ProcessPoolExecutor (CPU 바운드 격리)
_bm25_executor = ProcessPoolExecutor(max_workers=2)


def sse(event: str, data: dict | str) -> str:
    payload = json.dumps(data, ensure_ascii=False) if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


# =============================================================================
# ① 커리큘럼 퓨전 서비스
# =============================================================================

# ── 레벨 감지 패턴 ─────────────────────────────────────────────────────────────

_LEVEL_PATTERNS = {
    "beginner": re.compile(
        r"입문|초급|처음|기초|시작|beginner|basic|모르|아무것도|zero",
        re.IGNORECASE,
    ),
    "intermediate": re.compile(
        r"중급|어느\s*정도|좀\s*할\s*줄|intermediate|중간|배운|써봤|경험",
        re.IGNORECASE,
    ),
    "advanced": re.compile(
        r"고급|심화|전문|advanced|잘\s*함|능숙|프로|expert|깊게",
        re.IGNORECASE,
    ),
}

_LEVEL_TO_RAG_FILTER = {
    "beginner":     {"entry", "beginner", "official_docs", "book"},
    "intermediate": {"intermediate", "official_docs", "book", "spec"},
    "advanced":     {"advanced", "spec", "troubleshooting", "api_limits"},
}

_LEVEL_WEEKS = {
    "beginner":     4,
    "intermediate": 5,
    "advanced":     6,
}


def _detect_level(message: str, history: list | None = None) -> str:
    """
    유저 메시지(+대화 히스토리)에서 학습 수준을 추론한다.
    명시적 키워드 → 히스토리 첫 턴 → 기본값(beginner) 순서.
    """
    candidates = [message]
    if history:
        for turn in history[:3]:
            if isinstance(turn, dict):
                candidates.append(turn.get("content", ""))
            elif hasattr(turn, "content"):
                candidates.append(turn.content)

    combined = " ".join(candidates)
    for level, pattern in _LEVEL_PATTERNS.items():
        if pattern.search(combined):
            return level
    return "beginner"


_CURRICULUM_SYSTEM_PROMPT = """\
당신은 n8n 자동화 교육 전문가입니다.
아래 [RAG 컨텍스트]의 `level` 메타데이터(entry / intermediate / advanced)와
선행 노드 의존성 그래프를 기반으로 유저의 학습 수준 [{detected_level}]에 맞는
주차별 개인 맞춤 로드맵을 설계하십시오.

출력 규칙:
1. JSON 배열 형태로 커리큘럼 카드를 출력하십시오.
    각 카드 스키마: {{week, level, title, objectives: [], nodes: [], canvas_code_id, duration}}
2. canvas_code_id 는 해당 주차 실습용 parent_summary doc_id 를 기재하십시오.
3. 학습 수준 {detected_level}에 맞는 난이도와 진행 속도로 설계하십시오.
4. 한국어로 안내하되 노드명/파라미터명은 영문 원문 유지.
5. 모든 속성은 n8n_properties_spec 에 의거한 팩트여야 합니다. (LEG)

[RAG 컨텍스트 — 난이도 {detected_level} 필터 적용]
{{context}}
"""

class CurriculumService:
    def __init__(self, engine):
        self.engine = engine

    def _extract_json_array(self, text: str) -> list[dict] | None:
        if not text:
            return None
        m = re.search(r"```json\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        candidate = m.group(1).strip() if m else text.strip()
        try:
            arr = json.loads(candidate)
            return arr if isinstance(arr, list) else None
        except json.JSONDecodeError:
            return None

    def _default_cards(self) -> list[dict]:
        return [
            {
                "week": "Week 1",
                "level": "beginner",
                "title": "n8n 기초와 Trigger",
                "description": "Manual Trigger, Set 노드로 기본 데이터 흐름을 이해합니다.",
                "duration": "45m",
                "canvas_code_id": "curriculum_w1",
                "workflow_json": {
                    "nodes": [
                        {"name": "Start", "type": "n8n-nodes-base.manualTrigger", "parameters": {}, "position": [260, 280]},
                        {"name": "Sample Data", "type": "n8n-nodes-base.set", "parameters": {"values": {"string": [{"name": "message", "value": "hello"}]}}, "position": [520, 280]},
                    ],
                    "connections": {
                        "Start": {"main": [[{"node": "Sample Data", "type": "main", "index": 0}]]}
                    }
                }
            },
            {
                "week": "Week 2",
                "level": "intermediate",
                "title": "항목 분리와 반복 처리",
                "description": "Split Out + Code 노드로 item 단위 처리 패턴을 익힙니다.",
                "duration": "60m",
                "canvas_code_id": "curriculum_w2",
                "workflow_json": {
                    "nodes": [
                        {"name": "Start", "type": "n8n-nodes-base.manualTrigger", "parameters": {}, "position": [220, 260]},
                        {"name": "Users", "type": "n8n-nodes-base.set", "parameters": {"values": {"string": [{"name": "users", "value": "[{\"name\":\"A\"},{\"name\":\"B\"}]"}]}}, "position": [450, 260]},
                        {"name": "Split Out Users", "type": "n8n-nodes-base.splitOut", "parameters": {"fieldToSplitOut": "users"}, "position": [700, 260]},
                    ],
                    "connections": {
                        "Start": {"main": [[{"node": "Users", "type": "main", "index": 0}]]},
                        "Users": {"main": [[{"node": "Split Out Users", "type": "main", "index": 0}]]}
                    }
                }
            },
            {
                "week": "Week 3",
                "level": "advanced",
                "title": "외부 API 연동과 집계",
                "description": "Code 노드에서 API 호출/집계 패턴과 Rate Limit 대응 포인트를 학습합니다.",
                "duration": "90m",
                "canvas_code_id": "curriculum_w3",
                "workflow_json": {
                    "nodes": [
                        {"name": "Start", "type": "n8n-nodes-base.manualTrigger", "parameters": {}, "position": [220, 280]},
                        {"name": "Fetch External Data", "type": "n8n-nodes-base.code", "parameters": {"mode": "runOnceForEachItem", "jsCode": "return items;"}, "position": [500, 280]},
                        {"name": "Calculate Average", "type": "n8n-nodes-base.code", "parameters": {"jsCode": "return items;"}, "position": [780, 280]},
                    ],
                    "connections": {
                        "Start": {"main": [[{"node": "Fetch External Data", "type": "main", "index": 0}]]},
                        "Fetch External Data": {"main": [[{"node": "Calculate Average", "type": "main", "index": 0}]]}
                    }
                }
            },
        ]

    def _normalize_cards(self, raw_cards: list[dict] | None) -> list[dict]:
        if not raw_cards:
            return self._default_cards()

        cards: list[dict] = []
        for i, c in enumerate(raw_cards, start=1):
            if not isinstance(c, dict):
                continue
            objectives = c.get("objectives") if isinstance(c.get("objectives"), list) else []
            description = c.get("description") or (" / ".join(str(x) for x in objectives[:2]) if objectives else "학습 카드")
            level = str(c.get("level") or "beginner").lower()
            if level not in {"beginner", "intermediate", "advanced"}:
                level = "beginner"
            code_id = str(c.get("canvas_code_id") or f"curriculum_w{i}")
            cards.append(
                {
                    "week": c.get("week") or f"Week {i}",
                    "level": level,
                    "title": c.get("title") or f"학습 단계 {i}",
                    "description": description,
                    "duration": c.get("duration") or ("45m" if level == "beginner" else "60m" if level == "intermediate" else "90m"),
                    "canvas_code_id": code_id,
                    "workflow_json": c.get("workflow_json"),
                }
            )

        return cards or self._default_cards()

    async def stream(self, ctx: dict) -> AsyncGenerator[str, None]:
        # 레벨 감지 → 개인 맞춤 RAG 필터 적용
        level = _detect_level(ctx["message"], ctx.get("history"))
        rag_types = _LEVEL_TO_RAG_FILTER.get(level, {"official_docs", "book"})
        num_weeks = _LEVEL_WEEKS.get(level, 4)

        log.info("[Curriculum] 감지 레벨=%s, RAG 타입=%s, 주차=%d", level, rag_types, num_weeks)
        yield sse("intent", {"curriculum_level": level, "weeks": num_weeks})

        chunks = await _rag_with_filter(
            engine=self.engine,
            query=ctx["message"],
            filter_types=rag_types,
            top_n=12,
        )
        context_str = _build_context(chunks)
        level_prompt = _CURRICULUM_SYSTEM_PROMPT.replace(
            "{detected_level}", level
        ).replace("{{context}}", context_str)
        system = level_prompt
        user = (
            f"유저 학습 수준: {level}\n"
            f"총 {num_weeks}주 과정으로 n8n 커리큘럼을 설계해줘.\n"
            f"요청: {ctx['message']}"
        )

        # LLM 스트리밍 (토큰 emit 없음 - 구조화된 이벤트만 발행)
        full_text = ""
        async for token in _stream_llm(system, user, ctx["model"]):
            full_text += token

        parsed = self._extract_json_array(full_text)
        cards = self._normalize_cards(parsed)
        yield sse("curriculum", {
            "cards": cards,
            "description": "주차별 커리큘럼 카드 — 각 카드의 [실습 코드 주입] 버튼으로 바로 실행",
        })


# =============================================================================
# ② 수식 자동 생성 서비스
# =============================================================================

_EXPRESSION_SYSTEM_PROMPT = """\
당신은 n8n 표현식(Expression) 전문 튜터입니다.
[노드 실행 데이터]와 [RAG 스펙 컨텍스트]를 분석하여 정확한 표현식을 생성하십시오.
**반드시 마크다운 형식**으로 작성하십시오.

## 표현식 문법 절대 규칙 (RULE-04)
- 현재 노드 데이터: `{{ $json.fieldName }}`
- 이전 노드 데이터: `{{ $node["노드명"].json.fieldName }}`
- 배열 첫 번째: `{{ $json.items[0].field }}`
- **금지**: `$item()`, `.item.json` → n8n v1.x에서 폐기됨

## 출력 템플릿

```
## 생성된 표현식

### 표현식 1
```
{{ $json.fieldName }}
```
**설명**: 이 수식이 하는 일 (비전공자도 이해 가능하게)
**언제 사용**: 어떤 상황에서 이 수식이 필요한지

### 표현식 2 (있는 경우)
...

## 사용 방법
1. 위 표현식을 복사합니다
2. n8n 캔버스에서 해당 필드를 클릭합니다
3. 표현식 입력창에 붙여넣습니다

## 주의사항
주의해야 할 엣지케이스
```

(LEG: n8n_properties_spec 기반 팩트)

[노드 실행 데이터]
{node_data}

[RAG 스펙 컨텍스트]
{context}
"""

class ExpressionService:
    def __init__(self, engine):
        self.engine = engine

    async def stream(self, ctx: dict) -> AsyncGenerator[str, None]:
        node_data = ctx.get("node_data") or {}
        # 노드 타입 기반으로 spec 청크 타겟 검색
        node_type = node_data.get("type", "")
        query = f"{ctx['message']} {node_type} expression field access"

        chunks = await _rag_with_filter(
            engine=self.engine,
            query=query,
            filter_types={"spec", "cli_spec", "official_docs"},
            top_n=6,
        )
        context_str = _build_context(chunks)
        node_json   = json.dumps(node_data, ensure_ascii=False, indent=2)
        system = _EXPRESSION_SYSTEM_PROMPT.format(
            node_data=node_json, context=context_str
        )
        user = f"이 노드 데이터에서 다음을 추출하는 표현식을 만들어줘: {ctx['message']}"

        full_expr = ""
        async for token in _stream_llm(system, user, ctx["model"]):
            full_expr += token

        # 생성된 수식 인라인 피드백
        yield sse("expression", {
            "raw_expression": full_expr,
            "node_type": node_type,
            "insert_hint": "클릭하여 현재 노드 파라미터에 붙여넣기",
        })


# =============================================================================
# ③ 워크플로우 합성 + 최적화 서비스
# =============================================================================

_WORKFLOW_BUILD_SYSTEM_PROMPT = """\
당신은 n8n 워크플로우 아키텍트이자 튜터입니다.
[RAG 컨텍스트]의 검증된 코드 뼈대를 활용하여 워크플로우를 설계하십시오.
**반드시 마크다운 형식**으로 작성하십시오.

## 출력 템플릿 (이 구조를 반드시 따를 것)

```
## 워크플로우 설계 — [요청 제목]

## 전체 흐름
[1] 노드명 → [2] 노드명 → [3] 노드명

## 노드별 설명

### 1. [노드명] (`노드타입`)
- **역할**: 무엇을 하는 노드인지
- **핵심 설정**: `파라미터명`: 값

### 2. [노드명] (`노드타입`)
...

## n8n JSON 코드

```json
{{
  "nodes": [...],
  "connections": {{...}}
}}
```

## 최적화 권고 (해당 시)
- 대량 처리: `Split In Batches` 사용 필수 (RULE-01)
- API 제한: `Retry On Fail` + `Wait Between Tries` 설정 (RULE-03)

## 배포 체크리스트
- [ ] 각 노드 인증 정보 설정
- [ ] 에러 처리 노드 추가
```

**추가 규칙:**
- 노드명/파라미터명은 영문 원문 + `백틱` 형식 유지
- 코드는 반드시 ```json 블록으로 감쌀 것
- 제품명은 **n8n** (nn 금지)

[RAG 컨텍스트]
{context}
"""

class WorkflowBuildService:
    def __init__(self, engine, store: SessionStore):
        self.engine = engine
        self.store  = store

    async def stream(self, ctx: dict) -> AsyncGenerator[str, None]:
        # Parent-Child 체이닝 활성화하여 child_json 코드 확보
        chunks = await _rag_with_filter(
            engine=self.engine,
            query=ctx["message"],
            filter_types=None,   # 전체 대상 (parent/child 체이닝 포함)
            top_n=8,
        )
        context_str = _build_context(chunks)
        system = _WORKFLOW_BUILD_SYSTEM_PROMPT.format(context=context_str)
        user   = f"다음 요청에 맞는 n8n 워크플로우를 설계하고 최적화 진단을 수행해줘: {ctx['message']}"

        synthesized_json = ""
        async for token in _stream_llm(system, user, ctx["model"]):
            yield sse("token", token)
            synthesized_json += token

        # 캔버스 주입 버튼 카드 발행
        yield sse("card", {
            "type": "workflow_inject",
            "label": "캔버스에 바로 주입",
            "description": "버튼 클릭 시 현재 n8n 에디터에 워크플로우가 삽입됩니다",
            "workflow_payload": synthesized_json,
            "session_id": ctx["session_id"],
        })


# =============================================================================
# 공통 헬퍼
# =============================================================================

async def _rag_with_filter(engine, query: str,
                            filter_types: set | None,
                            top_n: int) -> list[dict]:
    """
    HybridRetriever(BM25)를 ProcessPoolExecutor에서 비동기 실행.
    CPU 바운드 BM25 연산을 메인 이벤트 루프와 격리한다.
    """
    import asyncio
    from functools import partial

    loop = asyncio.get_running_loop()
    try:
        result_chunks = await loop.run_in_executor(
            _bm25_executor,
            partial(_sync_retrieve, engine, query, filter_types, top_n),
        )
    except Exception as e:
        # ProcessPool 실패 시 일반 ThreadPoolExecutor로 폴백
        log.warning("[RAG] ProcessPool 실패(%s), ThreadPool 폴백", e)
        result_chunks = await loop.run_in_executor(
            None,
            partial(_sync_retrieve, engine, query, filter_types, top_n),
        )
    return result_chunks


def _sync_retrieve(engine, query: str,
                   filter_types: set | None, top_n: int) -> list[dict]:
    """동기 래퍼 — query_rewrite → HybridRetriever.retrieve() → 타입 필터."""
    from query_rewrite import rewrite_query
    rewritten = rewrite_query(query)
    chunks = engine.retriever.retrieve(rewritten)
    if filter_types:
        chunks = [c for c in chunks if c.get("data_type") in filter_types]
    return chunks[:top_n]


def _sync_retrieve_spec(engine, query: str, top_n: int) -> list[dict]:
    """spec/official_docs 전용 인덱스에서만 검색 — 노드/속성 질문 전용."""
    from query_rewrite import rewrite_query
    rewritten = rewrite_query(query)
    return engine.retriever.retrieve_spec(rewritten, top_k=top_n)


def _build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        dtype  = c.get("data_type", "?")
        title  = c.get("title", "")
        source = c.get("source", "")
        text   = c.get("text", "")[:1500]  # 토큰 절약
        parts.append(f"[{i}][{dtype.upper()}] {title} ({source})\n{text}")
    return "\n\n---\n\n".join(parts)


async def _stream_llm(
    system: str, user: str, model: str
) -> AsyncGenerator[str, None]:
    """
    Ollama /api/chat (stream=true) 비동기 스트리밍.
    각 청크에서 content 토큰을 yield.
    """
    import httpx
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "stream": True,
        "options": {"temperature": 0.1, "top_p": 0.9, "num_ctx": 8192},
    }
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST", f"{settings.ollama_base_url}/api/chat", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                    except json.JSONDecodeError:
                        continue
    except httpx.ReadTimeout:
        log.warning("[LLM] Ollama 응답 타임아웃(model=%s)", model)
        yield "모델 응답이 지연되어 기본 분석 결과로 계속 진행합니다."
    except httpx.HTTPError as e:
        log.warning("[LLM] Ollama HTTP 오류(model=%s): %s", model, e)
        yield "모델 응답에 일시적 문제가 있어 기본 분석 결과로 계속 진행합니다."
    except Exception as e:
        log.warning("[LLM] 예기치 못한 오류(model=%s): %s", model, e)
        yield "모델 연결 중 오류가 발생해 기본 분석 결과로 계속 진행합니다."
