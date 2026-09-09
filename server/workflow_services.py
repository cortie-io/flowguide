"""
app/services/curriculum.py  — ① 온톨로지 기반 동적 커리큘럼 퓨전
app/services/expression.py  — ② 수식 자동 생성기
app/services/workflow_build.py — ③ Parent-Child 코드 합성 + 최적화
"""

from __future__ import annotations

import json
import logging
import re
import asyncio
import time
from typing import AsyncGenerator, Any

from config import settings
from session import SessionStore

log = logging.getLogger("naito.services")


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


_CURRICULUM_SEPARATOR = "---CURRICULUM-JSON---"

_CURRICULUM_SYSTEM_PROMPT = """\
[CRITICAL] 이모지 및 특수 기호를 절대 사용하지 마십시오. 순수 마크다운만 사용.
[CRITICAL] 노드명·파라미터명은 반드시 n8n 공식 명칭을 사용하십시오.

당신은 n8n 자동화 교육 전문가입니다.
[RAG 컨텍스트]를 참고하여 유저의 학습 수준 [{detected_level}]에 맞는
주차별 개인 맞춤 로드맵을 설계하십시오. RAG에 없는 내용도 n8n 지식을 활용해 풍부하게 구성하십시오.

## 출력 형식 (반드시 이 순서를 지킬 것)

**[파트 1 — 텍스트 소개]**
마크다운으로 커리큘럼 개요를 충분히 상세하게 작성하십시오:

- **대상 학습자**: 이 커리큘럼이 어떤 사람에게 적합한지 (현재 수준, 배경, 목표)
- **전체 구성**: 총 주차 수와 각 파트의 핵심 주제 흐름을 단계적으로 설명
- **학습 목표**: 이 과정을 마치면 독립적으로 할 수 있는 것 3~5가지를 구체적으로 나열
- **학습 방법**: 주당 권장 학습 시간, 실습 비율, 효과적인 학습 전략
- **선수 지식**: 이 커리큘럼 시작 전 알아야 할 것 (없으면 "없음"으로 명시)

**[구분자 — 반드시 이 줄을 그대로 출력할 것]**
---CURRICULUM-JSON---

**[파트 2 — JSON 배열]**
```json
[
  {{
    "week": "1주차",
    "level": "{detected_level}",
    "title": "카드 제목",
    "description": "이 주차에서 배우는 핵심 내용과 실습 목표를 2~3문장으로",
    "duration": "45m",
    "canvas_code_id": "curriculum_w1"
  }},
  ...
]
```

노드명은 n8n 공식 명칭만 사용. 한국어 안내, 노드명/파라미터명은 영문 원문 유지.

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
            query=ctx.get("rag_query") or ctx["message"],
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

        # LLM 전체 출력 수집 (텍스트 + JSON 혼합 포맷)
        full_text = ""
        async for token in _stream_llm(system, user, ctx["model"], history=ctx.get("history"), openai_api_key=ctx.get("openai_api_key"), image_urls=ctx.get("image_urls")):
            full_text += token

        # 구분자 기준으로 텍스트 소개와 JSON 분리
        if _CURRICULUM_SEPARATOR in full_text:
            text_part, json_part = full_text.split(_CURRICULUM_SEPARATOR, 1)
        else:
            text_part = ""
            json_part = full_text

        # 텍스트 소개를 토큰 스트림으로 발행 (마크다운 렌더링됨)
        intro = text_part.strip()
        if intro:
            # 단락 단위로 쪼개어 자연스럽게 스트리밍
            for chunk in re.split(r"(\n\n+)", intro):
                if chunk:
                    yield sse("token", chunk)

        # 커리큘럼 카드 이벤트 발행
        parsed = self._extract_json_array(json_part)
        cards = self._normalize_cards(parsed)
        yield sse("curriculum", {
            "cards": cards,
            "description": "주차별 커리큘럼 카드 — 각 카드의 [실습 코드 주입] 버튼으로 바로 실행",
        })
        if chunks:
            yield sse("rag_sources", {"sources": _build_rag_sources(chunks)})


# =============================================================================
# ② 수식 자동 생성 서비스
# =============================================================================

_EXPRESSION_SYSTEM_PROMPT = """\
[CRITICAL] 이모지 및 특수 기호를 절대 사용하지 마십시오. 순수 마크다운만 사용.
[CRITICAL] 표현식은 [노드 실행 데이터]에 존재하는 필드명을 우선 사용하되, 없으면 일반적인 패턴을 제시하십시오.
[CRITICAL] 필드가 확인되지 않을 때는 예시 패턴을 제시하고 "실제 필드명으로 교체 필요"라고 명시하십시오.

당신은 n8n 표현식(Expression) 전문 튜터입니다.
[노드 실행 데이터]와 [RAG 스펙 컨텍스트]를 분석하여 정확하고 상세한 표현식 가이드를 제공하십시오.

## n8n v1.x 표현식 문법 규칙
- 현재 노드 데이터: `{{ $json.fieldName }}`
- 이전 노드 데이터: `{{ $node["노드명"].json.fieldName }}`
- 배열 첫 번째: `{{ $json.items[0].field }}`
- 배열 전체 길이: `{{ $json.items.length }}`
- 조건식: `{{ $json.status === "active" ? "활성" : "비활성" }}`
- 날짜 포맷: `{{ $now.format("YYYY-MM-DD") }}`
- **금지**: `$item()`, `.item.json` → n8n v1.x에서 폐기됨

## 출력 구조

### 요청 분석
사용자가 원하는 것이 무엇인지, 어떤 노드 데이터를 활용할지 설명하십시오.

### 정확한 표현식
```
{{ 표현식 }}
```
이 표현식이 어떻게 동작하는지 단계별로 설명하십시오.

### 응용 표현식
비슷하게 활용할 수 있는 표현식 변형 2~3개를 추가로 제시하십시오.

### 사용 위치 및 주의사항
- 이 표현식을 어느 노드의 어떤 파라미터에 넣어야 하는지
- 흔한 실수와 디버깅 방법
- 데이터가 없거나 null인 경우 대처법

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

        # 온톨로지 힌트 + 오타 교정 추가
        ontology_hints = ctx.get("ontology_hints") or []
        hint_block = ""
        if ontology_hints:
            hint_block = "\n\n[온톨로지 관계 힌트]\n" + "\n".join(ontology_hints)
        typo_corrections = ctx.get("typo_corrections") or []
        if typo_corrections:
            lines = "\n".join(f"  - '{o}' → {c}" for o, c in typo_corrections)
            hint_block += (
                "\n\n[⚠ 오타 자동 교정]\n오타 단어는 실제로 존재하지 않는 용어입니다. "
                "절대 별도 개념으로 설명하거나 '비공식 표현'으로 정당화하지 말 것.\n" + lines
            )

        context_str = _build_context(chunks) + hint_block
        node_json   = json.dumps(node_data, ensure_ascii=False, indent=2)
        system = _EXPRESSION_SYSTEM_PROMPT.format(
            node_data=node_json, context=context_str
        )
        user = f"이 노드 데이터에서 다음을 추출하는 표현식을 만들어줘: {ctx['message']}"

        full_expr = ""
        async for token in _stream_llm(system, user, ctx["model"], history=ctx.get("history"), openai_api_key=ctx.get("openai_api_key"), image_urls=ctx.get("image_urls")):
            yield sse("token", token)
            full_expr += token

        # 생성된 수식 인라인 피드백 (익스텐션 호환)
        yield sse("expression", {
            "raw_expression": full_expr,
            "node_type": node_type,
            "insert_hint": "클릭하여 현재 노드 파라미터에 붙여넣기",
        })
        if chunks:
            yield sse("rag_sources", {"sources": _build_rag_sources(chunks)})


# =============================================================================
# ③ 워크플로우 합성 + 최적화 서비스
# =============================================================================

# =============================================================================
# ③ 워크플로우 합성 — 3-Phase 추론 아키텍처
#    Phase 1: DECOMPOSE  — 요청을 구조화된 설계 플랜으로 분해
#    Phase 2: RESOLVE    — 플랜 각 단계별 노드 스펙 병렬 RAG 검색
#    Phase 3: ASSEMBLE   — 플랜 + 스펙 기반 완성 워크플로우 생성 (스트리밍)
# =============================================================================

_DECOMPOSE_SYSTEM = """\
[CRITICAL] JSON 객체만 출력하십시오. 설명, 마크다운, 코드 펜스 없음.
당신은 n8n 워크플로우 설계 분석가입니다.
사용자의 자동화 요청을 분석하여 아래 JSON 스키마를 정확히 출력하십시오.

{
  "goal": "한 문장: 이 워크플로우가 달성하는 목표",
  "trigger": {
    "type": "webhook | schedule | manual | email | database | file",
    "when": "언제/무엇이 워크플로우를 실행하는지 한 줄 설명"
  },
  "steps": [
    {
      "order": 1,
      "name": "단계명",
      "purpose": "이 단계가 하는 일",
      "node_keyword": "핵심 n8n 노드 키워드 (예: HTTP Request, Postgres, Code, If, Slack)"
    }
  ],
  "output": {
    "type": "API 응답 | DB 저장 | 이메일 | Slack | 파일 | 기타",
    "where": "결과가 어디로 가는지"
  },
  "complexity": "simple | moderate | complex"
}
"""

_ASSEMBLE_SYSTEM = """\
[CRITICAL] 이모지 및 특수 기호를 절대 사용하지 마십시오. 순수 마크다운만 사용.
[CRITICAL] 노드 타입은 반드시 공식 형식(n8n-nodes-base.XXX / @n8n/n8n-nodes-XXX)을 사용하십시오.
[CRITICAL] JSON 코드는 반드시 ```json 블록으로 감쌀 것.
[CRITICAL] RAG 컨텍스트에 없어도 자신의 n8n 지식을 적극 활용하여 완전한 워크플로우를 반드시 구현하십시오. 거절 금지.

당신은 n8n 워크플로우 구현 전문가입니다.
[설계 플랜]과 [노드 스펙 참고]를 바탕으로 즉시 실행 가능한 완전한 n8n 워크플로우를 구현하십시오.

출력 구조 (반드시 이 순서, 각 섹션을 충분히 상세하게 작성):

## 워크플로우 개요

이 워크플로우가 자동화하는 비즈니스 프로세스, 전체 동작 방식, 핵심 특징을 4~6문장으로 상세히 설명하십시오.
기술적 접근 방법과 사용자가 얻는 가치도 함께 서술하십시오.

## 전체 실행 흐름

트리거부터 최종 출력까지 각 단계를 번호로 나열하고, 각 단계에서 어떤 데이터가 어떻게 처리되는지 설명하십시오.

1. **[단계명]**: 상세 설명
2. **[단계명]**: 상세 설명
...

## 노드 구성

| 순서 | 노드명 | 타입 | 역할 | 주요 파라미터 |
|------|--------|------|------|--------------|
| ... | ... | `n8n-nodes-base.XXX` | ... | key: value |

## n8n JSON

```json
{{
  "name": "워크플로우 이름",
  "nodes": [...],
  "connections": {{...}},
  "settings": {{"executionOrder": "v1"}}
}}
```

## 주요 설정 가이드

각 핵심 노드의 설정 방법을 상세히 안내하십시오:

### [노드명] 설정
- **파라미터명**: 설정값과 이유
- 주의사항이나 대안 설정이 있으면 함께 안내

## 운영 고려사항 및 개선 포인트

1. **에러 처리**: 실패 케이스와 대응 방법
2. **성능 최적화**: 대량 데이터 처리 시 고려사항
3. **보안**: 자격증명, API 키 관리 방법
4. **확장 방향**: 추가로 구현할 수 있는 기능

포맷 규칙: 노드명·파라미터명은 영문 원문 + 백틱(`). 제품명은 **n8n**.

[설계 플랜]
{plan}

[노드 스펙 참고]
{context}
"""


def _extract_workflow_json(text: str) -> dict | None:
    """LLM 마크다운 출력에서 n8n 워크플로우 JSON 객체를 추출."""
    m = re.search(r"```json\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if not m:
        return None
    try:
        obj = json.loads(m.group(1).strip())
        if isinstance(obj, dict) and ("nodes" in obj or "connections" in obj):
            return obj
    except json.JSONDecodeError:
        pass
    return None


class WorkflowBuildService:
    def __init__(self, engine, store: SessionStore):
        self.engine = engine
        self.store  = store

    # ── Phase 1: 요청 분해 ────────────────────────────────────────
    async def _decompose(self, ctx: dict) -> dict:
        user = f"다음 자동화 요청을 분석해줘: {ctx['message']}"
        raw = ""
        async for token in _stream_llm(
            _DECOMPOSE_SYSTEM, user, ctx["model"],
            openai_api_key=ctx.get("openai_api_key"),
        ):
            raw += token
        try:
            clean = re.sub(r"```json?\s*|\s*```", "", raw).strip()
            return json.loads(clean)
        except (json.JSONDecodeError, ValueError):
            return {
                "goal": ctx["message"],
                "trigger": {"type": "manual", "when": "수동 실행"},
                "steps": [{"order": 1, "name": "처리", "purpose": ctx["message"], "node_keyword": "Code"}],
                "output": {"type": "기타", "where": "결과 반환"},
                "complexity": "simple",
            }

    # ── Phase 2: 노드별 RAG 병렬 검색 ────────────────────────────
    async def _resolve_nodes(self, plan: dict) -> dict[str, list[dict]]:
        import asyncio as _asyncio
        queries: list[tuple[str, str]] = []  # (label, query)

        trigger_type = plan.get("trigger", {}).get("type", "")
        if trigger_type:
            queries.append(("trigger", f"{trigger_type} trigger n8n node"))

        for step in plan.get("steps", []):
            kw = step.get("node_keyword") or step.get("name") or ""
            if kw:
                queries.append((f"step_{step.get('order', 0)}", f"{kw} n8n node parameters spec"))

        output_type = plan.get("output", {}).get("type", "")
        if output_type and output_type != "기타":
            queries.append(("output", f"{output_type} n8n node"))

        tasks = [
            _rag_with_filter(self.engine, q, {"spec", "official_docs"}, 4)
            for _, q in queries
        ]
        results = await _asyncio.gather(*tasks)
        return {label: chunks for (label, _), chunks in zip(queries, results)}

    def _build_assembly_context(self, ctx: dict, node_chunks: dict[str, list[dict]]) -> str:
        parts = []
        for label, chunks in node_chunks.items():
            if chunks:
                parts.append(f"[{label}]\n" + _build_context(chunks[:3]))
        hints = ctx.get("ontology_hints") or []
        if hints:
            parts.append("[온톨로지 힌트]\n" + "\n".join(hints))
        typos = ctx.get("typo_corrections") or []
        if typos:
            lines = "\n".join(f"  - '{o}' → {c}" for o, c in typos)
            parts.append("[오타 교정]\n" + lines)
        return "\n\n---\n\n".join(parts) if parts else "(컨텍스트 없음)"

    @staticmethod
    def _format_plan_summary(plan: dict) -> str:
        lines: list[str] = []
        if plan.get("goal"):
            lines.append(f"**목표:** {plan['goal']}")
        t = plan.get("trigger", {})
        if t:
            lines.append(f"**트리거:** `{t.get('type', '?')}` — {t.get('when', '')}")
        steps = plan.get("steps", [])
        if steps:
            lines.append("**처리 단계:**")
            for s in steps:
                lines.append(f"  {s.get('order')}. **{s.get('name')}** — {s.get('purpose')} (`{s.get('node_keyword')}`)")
        o = plan.get("output", {})
        if o:
            lines.append(f"**출력:** {o.get('type')} → {o.get('where')}")
        c = plan.get("complexity", "")
        if c:
            _labels = {"simple": "단순", "moderate": "보통", "complex": "복잡"}
            lines.append(f"**복잡도:** {_labels.get(c, c)}")
        return "\n".join(lines)

    # ── 메인 스트림 ───────────────────────────────────────────────
    async def stream(self, ctx: dict) -> AsyncGenerator[str, None]:
        # Phase 1: 분해
        yield sse("token", "**요청 분석 중...**\n\n")
        plan = await self._decompose(ctx)
        yield sse("token", self._format_plan_summary(plan))
        yield sse("token", "\n\n---\n\n")

        # Phase 2: 노드 스펙 병렬 검색
        node_chunks = await self._resolve_nodes(plan)

        # Phase 3: 어셈블 (스트리밍)
        context_str = self._build_assembly_context(ctx, node_chunks)
        plan_str    = json.dumps(plan, ensure_ascii=False, indent=2)
        system = _ASSEMBLE_SYSTEM.format(plan=plan_str, context=context_str)
        user   = (
            f"요청: {ctx['message']}\n\n"
            "위 설계 플랜을 구현하는 완성된 n8n 워크플로우를 작성해줘."
        )

        assembled = ""
        async for token in _stream_llm(
            system, user, ctx["model"],
            history=ctx.get("history"),
            openai_api_key=ctx.get("openai_api_key"),
            image_urls=ctx.get("image_urls"),
        ):
            yield sse("token", token)
            assembled += token

        # JSON 추출 후 카드 발행
        wf_json = _extract_workflow_json(assembled)
        yield sse("card", {
            "type": "workflow_inject",
            "workflow_json": wf_json,
            "workflow_payload": assembled,
            "session_id": ctx["session_id"],
        })

        all_chunks = [c for ch in node_chunks.values() for c in ch]
        if all_chunks:
            yield sse("rag_sources", {"sources": _build_rag_sources(all_chunks)})


# =============================================================================
# 공통 헬퍼
# =============================================================================

async def _rag_with_filter(engine, query: str,
                            filter_types: set | None,
                            top_n: int) -> list[dict]:
    """
    HybridRetriever(BM25)를 스레드풀에서 비동기 실행해 메인 이벤트 루프와 격리한다.

    별도 프로세스(ProcessPoolExecutor)로 격리하는 방안도 시도했었으나, engine이
    들고 있는 ChromaDB/토크나이저 네이티브 바인딩(`builtins.Bindings`)이 원천적으로
    피클링이 불가능해 매 호출마다 100% 실패하고 스레드풀로 재시도하는 구조였음 —
    항상 실패하는 시도를 매번 반복하며 지연만 유발했으므로 제거하고 스레드풀만 사용.
    """
    import asyncio
    from functools import partial

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        partial(_sync_retrieve, engine, query, filter_types, top_n),
    )


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


def _build_rag_sources(chunks: list[dict]) -> list[dict]:
    """청크 메타데이터를 rag_sources SSE 이벤트용 소스 목록으로 변환."""
    sources = []
    seen: set[str] = set()
    for c in chunks:
        title     = c.get("title") or c.get("node_name") or "문서"
        source    = c.get("source") or c.get("file") or ""
        data_type = c.get("data_type") or "docs"
        text      = c.get("text") or ""
        preview   = text[:120].replace("\n", " ").strip()
        key = f"{title}::{source}"
        if key in seen:
            continue
        seen.add(key)
        sources.append({"title": title, "data_type": data_type,
                        "source": source, "preview": preview})
        if len(sources) >= 8:
            break
    return sources


async def _stream_openai(
    system: str,
    user: str,
    model_name: str,
    history: list | None,
    api_key: str,
    image_urls: list[str] | None = None,
) -> AsyncGenerator[str, None]:
    """OpenAI Chat Completions 스트리밍 (사용자 BYOK). 이미지 URL/base64 vision 지원."""
    try:
        from openai import AsyncOpenAI
    except ImportError:
        yield "OpenAI 패키지가 설치되지 않았습니다. 관리자에게 문의해 주세요."
        return

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    if history:
        for turn in history:
            role = getattr(turn, "role", None) or (turn.get("role") if isinstance(turn, dict) else "")
            content = getattr(turn, "content", None) or (turn.get("content") if isinstance(turn, dict) else "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": str(content)})

    # 이미지가 있으면 vision 형식으로 user content 구성
    if image_urls:
        user_content: str | list = [{"type": "text", "text": user}]
        for url in image_urls:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": url, "detail": "high"},
            })
        messages.append({"role": "user", "content": user_content})
    else:
        messages.append({"role": "user", "content": user})

    try:
        client = AsyncOpenAI(api_key=api_key)
        stream = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=True,
            temperature=0.1,
            max_tokens=4096,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta
    except Exception as e:
        log.error("[OpenAI] 스트리밍 오류: %s", e)
        err_msg = str(e)
        if "401" in err_msg or "Incorrect API key" in err_msg:
            yield "OpenAI API 키가 올바르지 않습니다. 설정에서 키를 확인해 주세요."
        elif "429" in err_msg:
            yield "OpenAI 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
        else:
            yield f"OpenAI 오류: {err_msg[:200]}"


async def _stream_llm(
    system: str, user: str, model: str, history: list | None = None,
    openai_api_key: str | None = None, image_urls: list[str] | None = None,
) -> AsyncGenerator[str, None]:
    """
    OpenAI Chat Completions (stream=true) 비동기 스트리밍.
    model 이 'openai:'로 시작하면 그 모델명을, 아니면 서버 기본 모델(settings.llm_model)을 사용.
    openai_api_key 가 없으면 서버 기본 키(settings.openai_api_key, BYOK 미지정 시)를 사용.
    history 가 있으면 multi-turn messages 배열로 전달.
    image_urls 가 있으면 OpenAI vision API 로 이미지 포함 전송.
    """
    model_name = model[len("openai:"):] if model.startswith("openai:") else settings.llm_model
    api_key = openai_api_key or settings.openai_api_key

    if not api_key:
        yield "OpenAI API 키가 설정되어 있지 않습니다. 관리자에게 문의해 주세요."
        return

    async for token in _stream_openai(system, user, model_name, history, api_key, image_urls):
        yield token
