"""
app/services/error_patch.py  — ④ 에러 토큰 대응 실시간 원격 수술
app/services/reverse.py      — ⑤ 토폴로지 그래프 분할 역추적 분석
"""

from __future__ import annotations

import json
import logging
import re
from typing import AsyncGenerator

from config import settings

log = logging.getLogger("nodi.services")


def sse(event: str, data: dict | str) -> str:
    payload = json.dumps(data, ensure_ascii=False) if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


# =============================================================================
# ④ 에러 인터럽트 수술 서비스
# =============================================================================

_ERROR_PATCH_SYSTEM_PROMPT = """\
당신은 n8n 에러 진단 전문 튜터입니다.
[에러 로그]를 분석하고 [RAG 처방 컨텍스트]에 근거하여 누구나 이해할 수 있게 해결 방법을 제시하십시오.
**반드시 마크다운 형식**으로 작성하십시오.

## 출력 템플릿 (반드시 이 구조 사용)

```
## 에러 진단

**에러 유형:** [에러 타입 한 줄]
**발생 원인:** [왜 이 에러가 났는지 비전공자도 이해할 수 있게]

## 원인 분석
- **무슨 일이 일어났나**: 쉬운 말로 설명
- **왜 발생했나**: 기술적 원인
- **어느 노드에서**: 문제 위치

## 해결 방법

### 방법 1: [제목]
1. 단계 설명
2. 단계 설명

### 방법 2: [제목] (있는 경우)
...

## 패치 코드 (있는 경우)
```json
{{ 수정된 코드 }}
```

## 즉시 캔버스 적용 가능: YES / NO
이유: ...

## 재발 방지
- 예방 방법 1
- 예방 방법 2
```

**규칙:** 속성명은 `백틱`, 영문 원문 유지, LEG 표기, 제품명은 **n8n**

[에러 로그]
{error_log}

[RAG 처방 컨텍스트]
{context}
"""

# 에러 메시지에서 핵심 예외 토큰 추출 패턴
_EXCEPTION_PATTERNS = [
    re.compile(r'(Error|Exception|TypeError|ReferenceError)[:\s]+(.{10,120})', re.IGNORECASE),
    re.compile(r'(Cannot read|is not defined|undefined|null pointer)(.{0,80})', re.IGNORECASE),
    re.compile(r'(HTTP \d{3}|ECONNREFUSED|ETIMEDOUT|rate limit)(.{0,80})', re.IGNORECASE),
    re.compile(r'(n8n.*node|workflow.*error)(.{0,80})', re.IGNORECASE),
]


def _extract_error_tokens(error_log: str) -> list[str]:
    """에러 로그에서 핵심 예외 토큰 추출."""
    tokens: list[str] = []
    for pattern in _EXCEPTION_PATTERNS:
        matches = pattern.findall(error_log)
        for m in matches:
            token = " ".join(m).strip()
            if token and len(token) > 5:
                tokens.append(token)
    # 중복 제거
    return list(dict.fromkeys(tokens))[:5]


class ErrorPatchService:
    def __init__(self, engine):
        self.engine = engine

    async def stream(self, ctx: dict) -> AsyncGenerator[str, None]:
        error_log = ctx.get("error_log", "")
        if not error_log:
            yield sse("error_alert", {"message": "에러 로그가 없습니다."})
            return

        # 에러 인터럽트 경고 즉시 발행
        tokens = _extract_error_tokens(error_log)
        yield sse("error_alert", {
            "type": "interrupt",
            "tokens": tokens,
            "message": f"에러 감지: {tokens[0] if tokens else error_log[:80]}",
        })

        # BM25 가중 검색: troubleshooting 타입 우선
        query = " ".join(tokens) if tokens else error_log[:200]

        from workflow_services import _sync_retrieve, _build_context, _stream_llm

        import asyncio
        from functools import partial
        loop = asyncio.get_event_loop()
        chunks = await loop.run_in_executor(
            None,
            partial(_sync_retrieve, self.engine, query,
                    {"troubleshooting", "api_limits", "spec"}, 8)
        )
        context_str = _build_context(chunks)
        system = _ERROR_PATCH_SYSTEM_PROMPT.format(
            error_log=error_log[:1000], context=context_str
        )
        user = f"이 에러를 진단하고 즉시 적용 가능한 패치 방법을 알려줘:\n{error_log[:500]}"

        patch_code = ""
        async for token in _stream_llm(system, user, ctx["model"]):
            patch_code += token

        # 원격 수술 버튼 카드 발행
        yield sse("card", {
            "type": "error_patch_apply",
            "label": "캔버스에 패치 적용",
            "description": "버튼 클릭 시 수정된 노드 설정이 현재 캔버스에 반영됩니다",
            "patch_payload": patch_code,
            "session_id": ctx["session_id"],
        })


# =============================================================================
# ⑤ 토폴로지 리버스 엔지니어링 서비스
# =============================================================================

_REVERSE_SYSTEM_PROMPT = """\
당신은 n8n 워크플로우 역분석 전문가입니다.
아래 [워크플로우 토폴로지]와 [RAG 노드 스펙]을 바탕으로
실무자가 즉시 이해할 수 있는 상세 분석 리포트를 JSON 배열로 출력하십시오.

=== 출력 규칙 (반드시 준수) ===

[layer: summary] — 전체 요약
- content 필드에 다음을 포함하십시오:
    1) 이 워크플로우가 수행하는 비즈니스 목적 (1~2문장)
    2) 전체 데이터 흐름 요약: 트리거 → 처리 → 결과
    3) 주목해야 할 특이 사항 (에러 처리, 대량 데이터, Rate Limit 등)

[layer: nodes] — 노드별 핵심 역할
- items 배열의 각 노드마다 반드시:
    * role: 이 노드가 이 워크플로우에서 구체적으로 무슨 일을 하는지 2~3문장으로 설명.
        단순히 노드 타입을 반복하지 말 것. Sticky Note는 내용 요약, Code 노드는 로직 요약 필수.
    * key_params: 해당 노드의 핵심 파라미터 값을 key:value 형식으로 최대 3개.
        예) url:"https://api.example.com", method:"POST", operation:"insert"
    * warning: 이 노드에서 발생할 수 있는 운영 위험 (없으면 null)

[layer: expressions] — 수식 해설
- 감지된 표현식이 없으면 items를 빈 배열로 출력하십시오.
- 있을 경우 각 수식이 어느 노드에서 어떤 값을 꺼내는지 설명하십시오.

출력 형식 (JSON 배열):
[
  {{
    "layer": "summary",
    "title": "전체 워크플로우 요약",
    "content": "..."
  }},
  {{
    "layer": "nodes",
    "title": "노드별 핵심 역할",
    "items": [
      {{
        "node_name": "노드명 (영문 원문)",
        "type": "n8n-nodes-base.XXX",
        "layer": "trigger|processing|sink",
        "role": "이 노드의 구체적 역할 설명 2~3문장",
        "key_params": [{{"k": "파라미터명", "v": "값"}}],
        "warning": "운영 주의사항 또는 null"
      }}
    ]
  }},
  {{
    "layer": "expressions",
    "title": "Expression 현미경 해설",
    "items": [
      {{"expression": "{{ $json.field }}", "node": "사용 노드명", "explanation": "이 수식이 꺼내는 값과 목적"}}
    ]
  }}
]

모든 노드명과 파라미터 식별자는 영문 원문 유지.
컨텍스트에 없는 내용은 추론으로 채우되, "추정:" 접두사를 붙이십시오.

[워크플로우 토폴로지]
{topology}

[RAG 노드 스펙 컨텍스트]
{context}
"""


def _extract_key_params(node_type: str, params: dict) -> list[dict]:
    """LLM 분석 집중도를 위해 노드별 핵심 파라미터만 정제."""
    if not params:
        return []

    result: list[dict] = []
    priority_keys = [
        "url", "method", "operation", "resource", "authentication",
        "table", "schema", "query", "collection", "channel", "to",
        "subject", "workflowId", "functionCode", "mode", "conditions",
        "field", "value", "fields", "inputFieldName", "outputFieldName",
        "batchSize", "pollTimes", "interval",
    ]

    for key in priority_keys:
        if key in params:
            val = params[key]
            if isinstance(val, str) and len(val) > 120:
                val = val[:120] + "…"
            elif isinstance(val, dict):
                val = str(val)[:80] + "…"
            result.append({"k": key, "v": str(val)})

    if "code" in node_type.lower() or "function" in node_type.lower():
        for code_key in ("jsCode", "pythonCode", "functionCode"):
            if code_key in params:
                snippet = str(params[code_key])[:200].strip()
                result.append({"k": code_key, "v": snippet + "…"})
                break

    if "stickyNote" in node_type.lower():
        content_val = params.get("content", "")
        if content_val:
            result.append({"k": "content", "v": str(content_val)[:100]})

    if "httpRequest" in node_type.lower():
        for extra in ("bodyParameters", "headerParameters", "queryParameters"):
            if extra in params:
                val = params[extra]
                if isinstance(val, dict) and val.get("parameters"):
                    pairs = [f"{p.get('name')}={p.get('value', '')}" for p in val["parameters"][:3]]
                    result.append({"k": extra, "v": ", ".join(pairs)})

    return result[:6]


def _fallback_role_text(node: dict, layer_name: str) -> str:
    node_name = node.get("name", "Unknown")
    node_type = str(node.get("type", ""))
    type_short = node_type.split(".")[-1] if node_type else "unknown"

    if "stickynote" in type_short.lower():
        content = ""
        for p in node.get("key_params", []):
            if p.get("k") == "content":
                content = str(p.get("v", ""))
                break
        return (
            f"이 노드는 실행 로직 노드가 아니라 워크플로우 설명/가이드를 위한 주석 노드입니다. "
            f"{node_name}(stickyNote)에 작성된 안내를 통해 전체 흐름과 학습 포인트를 문서화합니다. "
            f"주석 내용: {content[:80] if content else '없음'}"
        )

    if layer_name == "trigger":
        return (
            f"이 노드는 워크플로우 실행을 시작시키는 트리거 단계입니다. "
            f"{node_name}({type_short})가 입력 이벤트를 받아 이후 처리 노드로 전달합니다. "
            f"실운영에서는 실행 주기/호출 빈도와 중복 실행 방지를 함께 점검하는 것이 좋습니다."
        )
    if layer_name == "sink":
        return (
            f"이 노드는 처리 결과를 외부 시스템에 반영하는 적재 단계입니다. "
            f"{node_name}({type_short})에서 최종 저장/전송이 수행됩니다. "
            f"재시도 정책, 중복 쓰기 방지, 실패 시 보상 로직을 반드시 설계해야 합니다."
        )
    return (
        f"이 노드는 워크플로우의 핵심 처리 단계입니다. "
        f"{node_name}({type_short})에서 데이터 변환·집계·비즈니스 로직이 수행됩니다. "
        f"입력 스키마 불일치와 대량 데이터 처리 시 성능 저하 가능성을 사전 점검해야 합니다."
    )


def _parse_topology(workflow_json_str: str) -> dict:
    """
    n8n 워크플로우 JSON의 connections 트리를 파싱하여
    [트리거 → 처리 → 적재] 3레이어로 분할한다.
    """
    try:
        wf = json.loads(workflow_json_str)
    except (json.JSONDecodeError, TypeError):
        return {"error": "JSON 파싱 실패", "raw": workflow_json_str[:200]}

    nodes       = wf.get("nodes", [])
    connections = wf.get("connections", {})

    # 노드 타입 기반 레이어 분류
    trigger_types = {
        "n8n-nodes-base.webhook", "n8n-nodes-base.scheduleTrigger",
        "n8n-nodes-base.emailReadImap", "n8n-nodes-base.manualTrigger",
        "n8n-nodes-base.httpRequest",
    }
    sink_types = {
        "n8n-nodes-base.postgres", "n8n-nodes-base.mysql",
        "n8n-nodes-base.googleSheets", "n8n-nodes-base.airtable",
        "n8n-nodes-base.s3", "n8n-nodes-base.emailSend",
    }
    note_types = {"n8n-nodes-base.stickyNote"}

    layers: dict[str, list[dict]] = {
        "trigger":   [],
        "processing":[],
        "sink":      [],
    }

    # 연결 그래프에서 실행 순서 추정 (source 노드명 집합)
    all_sources = set(connections.keys())
    all_targets: set[str] = set()
    for src_conns in connections.values():
        for output_conns in src_conns.values():
            for conn_list in output_conns:
                for conn in conn_list:
                    all_targets.add(conn.get("node", ""))

    for node in nodes:
        ntype = node.get("type", "")
        nname = node.get("name", "")
        raw_params = node.get("parameters", {})
        key_params = _extract_key_params(ntype, raw_params)
        entry = {
            "name":       nname,
            "type":       ntype,
            "key_params": key_params,
        }
        if ntype in note_types:
            layers["processing"].append(entry)
        elif ntype in trigger_types or nname not in all_targets:
            layers["trigger"].append(entry)
        elif ntype in sink_types:
            layers["sink"].append(entry)
        else:
            layers["processing"].append(entry)

    return {
        "layers":     layers,
        "total_nodes": len(nodes),
        "connections_count": sum(len(v) for v in connections.values()),
    }


def _extract_expressions_from_workflow(workflow_json_str: str) -> list[str]:
    """워크플로우 JSON 내 모든 {{ }} 표현식 추출."""
    pattern = re.compile(r'\{\{[^}]+\}\}')
    return list(set(pattern.findall(workflow_json_str)))


def _parse_report_from_raw(raw_report: dict | str | None) -> dict | list | None:
    """raw_report(raw markdown 포함)에서 JSON 리포트를 재파싱."""
    if raw_report is None:
        return None

    if isinstance(raw_report, list):
        return raw_report

    if isinstance(raw_report, dict):
        if isinstance(raw_report.get("raw"), str):
            raw_text = raw_report["raw"].strip()
        else:
            return raw_report
    elif isinstance(raw_report, str):
        raw_text = raw_report.strip()
    else:
        return None

    if not raw_text:
        return None

    fenced = re.search(r"```json\s*([\s\S]*?)\s*```", raw_text, re.IGNORECASE)
    candidate = fenced.group(1).strip() if fenced else raw_text

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


class ReverseService:
    def __init__(self, engine):
        self.engine = engine

    async def stream(self, ctx: dict) -> AsyncGenerator[str, None]:
        raw_json = ctx.get("raw_json", "")
        if not raw_json:
            yield sse("token", "워크플로우 JSON 데이터가 없습니다.")
            return

        # 토폴로지 파싱
        topology = _parse_topology(raw_json)
        expressions = _extract_expressions_from_workflow(raw_json)
        topology["expressions_found"] = expressions

        # 노드 타입 목록으로 RAG 스펙 검색
        all_nodes = (
            topology.get("layers", {}).get("trigger", []) +
            topology.get("layers", {}).get("processing", []) +
            topology.get("layers", {}).get("sink", [])
        )
        node_types_query = " ".join(
            set(n.get("type", "").split(".")[-1] for n in all_nodes)
        )

        from workflow_services import _sync_retrieve, _build_context, _stream_llm
        import asyncio
        from functools import partial

        loop = asyncio.get_event_loop()
        chunks = await loop.run_in_executor(
            None,
            partial(_sync_retrieve, self.engine,
                    node_types_query, {"spec", "official_docs"}, 10)
        )
        context_str = _build_context(chunks)
        topology_str = json.dumps(topology, ensure_ascii=False, indent=2)
        system = _REVERSE_SYSTEM_PROMPT.format(
            topology=topology_str, context=context_str
        )
        user = "이 n8n 워크플로우 토폴로지를 3층 아코디언 리포트 형식으로 역분석해줘."

        report_json = ""
        async for token in _stream_llm(system, user, ctx["model"]):
            report_json += token

        # 구조화 리포트 이벤트 발행
        try:
            report_data = json.loads(report_json.strip())
        except json.JSONDecodeError:
            report_data = {"raw": report_json}

        if isinstance(report_data, list):
            normalized_report = {
                "summary": "",
                "node_roles": [],
                "expressions": [],
                "raw_report": report_data,
            }
            for item in report_data:
                layer = (item or {}).get("layer") if isinstance(item, dict) else None
                if layer == "summary":
                    normalized_report["summary"] = item.get("content", "")
                elif layer in {"nodes", "node_roles"}:
                    normalized_report["node_roles"] = item.get("items", [])
                elif layer == "expressions":
                    normalized_report["expressions"] = item.get("items", [])
        elif isinstance(report_data, dict):
            normalized_report = {
                "summary": report_data.get("summary")
                or report_data.get("topology_summary")
                or report_data.get("overview")
                or "",
                "node_roles": report_data.get("node_roles")
                or report_data.get("nodes")
                or report_data.get("items")
                or [],
                "expressions": report_data.get("expressions")
                or report_data.get("expressions_found")
                or [],
                "raw_report": report_data,
            }

            parsed_raw = _parse_report_from_raw(report_data.get("raw") or report_data.get("raw_report"))
            if isinstance(parsed_raw, list):
                for item in parsed_raw:
                    layer = (item or {}).get("layer") if isinstance(item, dict) else None
                    if layer == "summary" and not normalized_report.get("summary"):
                        normalized_report["summary"] = item.get("content", "")
                    elif layer in {"nodes", "node_roles"} and not normalized_report.get("node_roles"):
                        normalized_report["node_roles"] = item.get("items", [])
                    elif layer == "expressions" and not normalized_report.get("expressions"):
                        normalized_report["expressions"] = item.get("items", [])
            elif isinstance(parsed_raw, dict):
                if not normalized_report.get("summary"):
                    normalized_report["summary"] = parsed_raw.get("summary") or parsed_raw.get("overview") or ""
                if not normalized_report.get("node_roles"):
                    normalized_report["node_roles"] = (
                        parsed_raw.get("node_roles")
                        or parsed_raw.get("nodes")
                        or parsed_raw.get("items")
                        or []
                    )
                if not normalized_report.get("expressions"):
                    normalized_report["expressions"] = (
                        parsed_raw.get("expressions")
                        or parsed_raw.get("expressions_found")
                        or []
                    )
        else:
            normalized_report = {
                "summary": "",
                "node_roles": [],
                "expressions": [],
                "raw_report": report_data,
            }

        topology_summary = {
            "total_nodes": topology.get("total_nodes"),
            "layers": {k: len(v) for k, v in topology.get("layers", {}).items()},
            "expressions_count": len(expressions),
        }

        if not normalized_report.get("summary"):
            normalized_report["summary"] = (
                f"총 {topology_summary['total_nodes'] or 0}개 노드, "
                f"트리거 {topology_summary['layers'].get('trigger', 0)}개, "
                f"처리 {topology_summary['layers'].get('processing', 0)}개, "
                f"적재 {topology_summary['layers'].get('sink', 0)}개, "
                f"표현식 {topology_summary['expressions_count']}개"
            )

        if not normalized_report.get("node_roles"):
            fallback_items = []
            for node in all_nodes:
                if node in topology.get("layers", {}).get("trigger", []):
                    layer_name = "trigger"
                    warning = "이벤트 급증 시 중복 실행/과호출 가능성을 모니터링하세요."
                elif node in topology.get("layers", {}).get("sink", []):
                    layer_name = "sink"
                    warning = "외부 시스템 쓰기 실패 시 재시도/멱등성 전략이 필요합니다."
                else:
                    layer_name = "processing"
                    if "stickynote" in str(node.get("type", "")).lower():
                        warning = None
                    else:
                        warning = "입력 데이터 스키마 변동 시 런타임 오류가 발생할 수 있습니다."

                fallback_items.append({
                    "node_name": node.get("name", "Unknown"),
                    "type": node.get("type", ""),
                    "layer": layer_name,
                    "role": _fallback_role_text(node, layer_name),
                    "key_params": node.get("key_params", [])[:3],
                    "warning": warning,
                })

            normalized_report["node_roles"] = fallback_items

        if not normalized_report.get("expressions"):
            normalized_report["expressions"] = [
                {"expression": expr, "explanation": "워크플로우에서 감지된 표현식입니다."}
                for expr in expressions
            ]

        yield sse("report", {
            "type": "reverse_engineering",
            "topology_summary": topology_summary,
            # 구버전 사이드패널 호환: 최상위 필드도 함께 제공
            "summary": normalized_report.get("summary", ""),
            "node_roles": normalized_report.get("node_roles", []),
            "expressions": normalized_report.get("expressions", []),
            "report": normalized_report,
        })
