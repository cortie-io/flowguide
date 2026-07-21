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

log = logging.getLogger("naito.services")


def sse(event: str, data: dict | str) -> str:
    payload = json.dumps(data, ensure_ascii=False) if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


# =============================================================================
# ④ 에러 인터럽트 수술 서비스
# =============================================================================

_ERROR_PATCH_SYSTEM_PROMPT = """\
[STRICT RULE] 이모지 및 특수 기호를 절대 사용하지 마십시오. 순수 마크다운만 사용.
당신은 n8n 에러 진단 전문 튜터입니다.
[에러 로그]를 분석하고 [RAG 처방 컨텍스트]와 n8n 지식을 활용하여 완전하고 상세한 해결 가이드를 제공하십시오.

## 출력 구조 (반드시 이 순서로, 각 섹션을 충분히 상세하게)

## 에러 진단

**에러 유형:** [에러 타입]
**발생 원인:** 비전공자도 이해할 수 있게 쉽게 설명 (2~3문장)

## 상세 원인 분석

에러가 발생한 기술적 원인을 깊이 있게 분석하십시오:
- **무슨 일이 일어났나**: 데이터 흐름 관점에서 설명
- **왜 발생했나**: 기술적 근본 원인 (n8n 내부 동작 포함)
- **어느 노드/단계에서**: 에러 발생 위치와 맥락
- **관련된 n8n 메커니즘**: 이 에러와 관련된 n8n 동작 방식 설명

## 해결 방법

### 방법 1: [가장 권장하는 방법 제목]
이 방법을 권장하는 이유를 먼저 설명하고, 단계별로 상세하게 안내:
1. 구체적인 단계 (어떤 노드, 어떤 파라미터, 어떤 값)
2. 다음 단계
...

### 방법 2: [대안 방법] (해당하는 경우)
언제 이 방법을 선택하는지 설명:
1. ...

## 수정 코드

```json
수정된 노드 설정 또는 코드 (적용 가능한 경우 반드시 포함)
```

수정 코드의 어떤 부분이 어떻게 달라졌는지 설명하십시오.

## 즉시 캔버스 적용 가능 여부

**가능 여부**: YES / NO
**이유**: 구체적인 이유
**적용 방법**: 단계별 안내

## 재발 방지 및 모범 사례

이 에러를 예방하기 위한 구체적인 방법과 n8n 베스트 프랙티스:
1. **예방 방법**: 구체적인 설정 또는 패턴
2. **모니터링**: 조기에 감지하는 방법
3. **관련 패턴**: 비슷한 에러로 이어질 수 있는 다른 상황

**규칙:** 속성명은 `백틱`, 영문 원문 유지, 제품명은 **n8n**

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

        from workflow_services import _sync_retrieve, _build_context, _stream_llm, _build_rag_sources

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
        async for token in _stream_llm(system, user, ctx["model"], history=ctx.get("history"), openai_api_key=ctx.get("openai_api_key")):
            patch_code += token

        # 원격 수술 버튼 카드 발행
        yield sse("card", {
            "type": "error_patch_apply",
            "label": "캔버스에 패치 적용",
            "description": "버튼 클릭 시 수정된 노드 설정이 현재 캔버스에 반영됩니다",
            "patch_payload": patch_code,
            "session_id": ctx["session_id"],
        })
        if chunks:
            yield sse("rag_sources", {"sources": _build_rag_sources(chunks)})


# =============================================================================
# ⑤ 토폴로지 리버스 엔지니어링 서비스
# =============================================================================

_REVERSE_SYSTEM_PROMPT = """\
[CRITICAL] 이모지 및 특수 기호를 절대 사용하지 마십시오. 순수 마크다운만 사용.
[CRITICAL] 아래 [워크플로우 데이터]에 실제로 존재하는 노드·파라미터·설정값만 분석하십시오.
[CRITICAL] 데이터에 없는 내용을 추측·창작·추정하는 것은 엄금. 확인 불가 항목은 "확인 불가"로 표기.
[CRITICAL] 각 노드의 실제 파라미터 값을 인라인 코드(`)로 명시하십시오.

당신은 n8n 워크플로우 역분석 전문가입니다.
아래 [워크플로우 데이터]와 [RAG 노드 스펙]을 바탕으로 실무자가 즉시 이해할 수 있는
상세 분석 리포트를 마크다운으로 작성하십시오.
반드시 아래 6개 섹션을 모두 포함하고 각 섹션을 충분한 깊이로 채우십시오.

---

## 1. 워크플로우 전체 목적

이 워크플로우가 자동화하는 비즈니스 프로세스와 목적을 3~5문장으로 구체적으로 설명하십시오.
노드 이름 나열이 아닌, 이 자동화가 해결하는 문제와 최종 결과물을 중심으로 서술하십시오.

---

## 2. 전체 데이터 흐름

트리거에서 최종 출력까지 단계별로 어떤 데이터가 어떻게 변환·전달되는지 설명하십시오.
아래 형식으로 흐름도를 먼저 표시하고, 각 단계를 2~3줄로 설명하십시오:

```
[노드명] → [노드명] → [노드명] → ...
```

---

## 3. 노드별 상세 분석

각 노드를 아래 형식으로 분석하십시오. stickyNote는 제외하고 실행 노드만 분석하십시오.

### [노드명] (`노드_타입_이름`)

**이 노드의 역할**: 이 워크플로우 안에서 이 노드가 구체적으로 수행하는 작업을 2~3문장으로 서술. 타입명 반복 금지.

**주요 파라미터 설정**:

| 파라미터 | 설정값 | 의미 |
|---|---|---|
| `파라미터명` | `실제 값` | 이 값이 워크플로우에서 하는 역할 |

데이터에서 확인된 파라미터만 기입. 비어 있으면 "파라미터 정보 없음"으로 기재.

**입출력**:
- 입력: 이 노드가 받는 데이터
- 출력: 다음 노드로 넘기는 데이터

**운영 주의사항**: 이 노드에서 발생할 수 있는 장애·에러·성능 이슈 (없으면 생략)

---

## 4. 중요 설정값 일람

이 워크플로우 전체에서 운영 환경 변경 시 수정이 필요한 하드코딩 값, 자격증명, URL, 조건값 등을 표로 정리:

| 노드명 | 설정 항목 | 현재 값 | 비고 |
|---|---|---|---|

---

## 5. Expression 해설

감지된 `{{{{ $json.xxx }}}}` 형태의 동적 표현식을 각각 설명하십시오.

- `{{{{ 수식 }}}}` — [사용 노드명] — [꺼내는 값과 목적]

감지된 수식이 없으면: "이 워크플로우에는 동적 표현식이 사용되지 않습니다."

---

## 6. 개선 제안

이 워크플로우에서 발견된 문제점과 개선 방향을 구체적으로 최소 3개 제시하십시오:

1. **[개선 항목명]**: 현재 상태 → 권장 개선 방법
2. ...

---

[워크플로우 데이터]
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


def _build_rich_topology(workflow_json_str: str) -> dict:
    """LLM에게 전달할 풍부한 워크플로우 데이터 (모든 파라미터 포함)."""
    try:
        wf = json.loads(workflow_json_str)
    except (json.JSONDecodeError, TypeError):
        return {"error": "JSON 파싱 실패"}

    nodes = wf.get("nodes", [])
    connections = wf.get("connections", {})

    # 연결 순서 맵 구성
    connection_map: dict[str, list[str]] = {}
    for src, src_conns in connections.items():
        targets: list[str] = []
        for output_conns in src_conns.values():
            for conn_list in output_conns:
                for conn in conn_list:
                    t = conn.get("node", "")
                    if t:
                        targets.append(t)
        connection_map[src] = targets

    node_data = []
    for node in nodes:
        ntype = node.get("type", "")
        nname = node.get("name", "")
        raw_params = node.get("parameters", {})

        # 파라미터 정제 — 긴 값은 300자로 트리밍, 단 code 노드는 400자
        max_val = 400 if ("code" in ntype.lower() or "function" in ntype.lower()) else 300
        trimmed: dict = {}
        for k, v in raw_params.items():
            if isinstance(v, str):
                trimmed[k] = v[:max_val] + "…" if len(v) > max_val else v
            elif isinstance(v, (dict, list)):
                s = json.dumps(v, ensure_ascii=False)
                trimmed[k] = json.loads(s) if len(s) <= 250 else s[:250] + "…"
            else:
                trimmed[k] = v

        node_data.append({
            "name": nname,
            "type": ntype,
            "parameters": trimmed,
            "connects_to": connection_map.get(nname, []),
        })

    return {
        "workflow_name": wf.get("name", "Unknown"),
        "nodes": node_data,
        "total_nodes": len(nodes),
    }


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

    @staticmethod
    def _find_balanced_json_object(text: str) -> str:
        """텍스트 어디에 섞여 있든 첫 번째로 균형 잡힌 { ... } 객체를 추출.
        문자열 리터럴 내부의 중괄호/이스케이프는 깊이 계산에서 제외한다."""
        start = text.find("{")
        while start != -1:
            depth = 0
            in_string = False
            escape = False
            for i in range(start, len(text)):
                ch = text[i]
                if in_string:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == '"':
                        in_string = False
                    continue
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start : i + 1]
            start = text.find("{", start + 1)
        return ""

    @staticmethod
    def _extract_json_from_message(message: str) -> str:
        """사용자 메시지에 붙여넣은 워크플로우 JSON 추출.
        코드 펜스(언어 태그 유무 무관) / 메시지 전체 JSON / 설명 문구에 섞인 JSON
        순서로 후보를 모아 첫 번째로 유효한 n8n 워크플로우 JSON을 채택한다."""
        candidates: list[str] = []

        fenced = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", message, re.IGNORECASE)
        if fenced:
            candidates.append(fenced.group(1).strip())

        candidates.append(message.strip())

        embedded = ReverseService._find_balanced_json_object(message)
        if embedded:
            candidates.append(embedded)

        for candidate in candidates:
            if not candidate.startswith("{"):
                continue
            try:
                obj = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and ("nodes" in obj or "connections" in obj):
                return candidate
        return ""

    @staticmethod
    async def _fetch_from_n8n(ctx: dict) -> str:
        """n8n REST API에서 워크플로우 JSON 자동 가져오기."""
        import httpx as _httpx
        n8n_url = (ctx.get("n8n_url") or "").rstrip("/")
        api_key = ctx.get("n8n_api_key") or ""
        if not n8n_url:
            return ""
        headers: dict[str, str] = {}
        if api_key:
            headers["X-N8N-API-KEY"] = api_key
        try:
            async with _httpx.AsyncClient(timeout=8.0) as client:
                # 워크플로우 목록 조회
                list_resp = await client.get(f"{n8n_url}/api/v1/workflows", headers=headers)
                if not list_resp.is_success:
                    return ""
                workflows = list_resp.json().get("data", [])
                if not workflows:
                    return ""
                # 메시지에서 워크플로우 이름 매칭
                message_lower = ctx.get("message", "").lower()
                target = None
                for wf in workflows:
                    name = (wf.get("name") or "").lower()
                    if name and name in message_lower:
                        target = wf
                        break
                # 이름 매칭 실패 → 가장 최근 수정된 워크플로우
                if not target:
                    target = max(
                        workflows,
                        key=lambda w: w.get("updatedAt") or w.get("createdAt") or "",
                        default=None,
                    )
                if not target or not target.get("id"):
                    return ""
                # 상세 워크플로우 조회
                detail_resp = await client.get(
                    f"{n8n_url}/api/v1/workflows/{target['id']}", headers=headers
                )
                if detail_resp.is_success:
                    log.info("[ReverseService] n8n에서 워크플로우 자동 로드: '%s'", target.get("name"))
                    return json.dumps(detail_resp.json(), ensure_ascii=False)
        except Exception as e:
            log.warning("[ReverseService] n8n 자동 로드 실패: %s", e)
        return ""

    async def stream(self, ctx: dict) -> AsyncGenerator[str, None]:
        from_extension = bool(ctx.get("raw_json", ""))
        raw_json = (
            ctx.get("raw_json", "")
            or self._extract_json_from_message(ctx.get("message", ""))
        )
        fetched_name: str = ""
        if not raw_json and ctx.get("n8n_url"):
            fetched = await self._fetch_from_n8n(ctx)
            if fetched:
                try:
                    fetched_name = json.loads(fetched).get("name", "")
                except Exception:
                    pass
                raw_json = fetched
        if not raw_json:
            guide = (
                "워크플로우 JSON이 전달되지 않았습니다.\n\n"
                "역분석 기능을 사용하는 방법:\n\n"
                "**방법 1 — 브라우저 확장 프로그램 사용 (권장)**\n"
                "Naito 확장 프로그램을 설치하면 n8n 캔버스를 열어두고 "
                "\"분석해줘\"라고 입력하는 것만으로 자동으로 워크플로우를 가져옵니다.\n\n"
                "**방법 2 — JSON 직접 붙여넣기**\n"
                "n8n 에디터에서 워크플로우를 열고 `...` 메뉴 → `Download` → JSON 파일을 열어 내용을 복사한 뒤 "
                "아래처럼 메시지에 붙여넣으세요:\n\n"
                "```\n"
                "이 워크플로우 분석해줘\n\n"
                "```json\n"
                "{ \"nodes\": [...], \"connections\": {...} }\n"
                "```\n"
                "```"
            )
            for chunk in re.split(r"(\n\n+)", guide):
                if chunk:
                    yield sse("token", chunk)
            return

        # n8n에서 자동 로드한 경우 알림
        if fetched_name:
            yield sse("token", f"n8n에서 **{fetched_name}** 워크플로우를 불러왔습니다.\n\n")

        # 풍부한 토폴로지 구성 (모든 파라미터 포함)
        rich_topology = _build_rich_topology(raw_json)
        expressions = _extract_expressions_from_workflow(raw_json)
        rich_topology["expressions_found"] = expressions

        # RAG 스펙 검색 — 노드 타입 쿼리
        node_types_query = " ".join(
            set(n.get("type", "").split(".")[-1] for n in rich_topology.get("nodes", []))
        )

        from workflow_services import _sync_retrieve, _build_context, _stream_llm, _build_rag_sources
        import asyncio
        from functools import partial

        loop = asyncio.get_event_loop()
        chunks = await loop.run_in_executor(
            None,
            partial(_sync_retrieve, self.engine,
                    node_types_query, {"spec", "official_docs"}, 10)
        )
        context_str = _build_context(chunks)
        topology_str = json.dumps(rich_topology, ensure_ascii=False, indent=2)
        system = _REVERSE_SYSTEM_PROMPT.format(
            topology=topology_str, context=context_str
        )
        user = "위 워크플로우 데이터를 6개 섹션으로 상세하게 역분석해줘."

        # 토큰을 실시간 스트리밍
        async for token in _stream_llm(system, user, ctx["model"], history=ctx.get("history"), openai_api_key=ctx.get("openai_api_key")):
            yield sse("token", token)

        if chunks:
            yield sse("rag_sources", {"sources": _build_rag_sources(chunks)})
