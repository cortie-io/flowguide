"""
POST /api/workspace/stream
────────────────────────────────────────────────────────────────
Vercel AI SDK 데이터 스트림 프로토콜로 스트리밍.

스트림 포맷:
  0:"token"\n          → 텍스트 델타
  2:[{...}]\n          → 구조화 데이터 (intent, curriculum, card, ...)
  d:{"finishReason":"stop"}\n  → 스트림 종료
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import settings
from credential_filter import get_credential_filter, CredentialFilter
from engine import get_engine, N8NQueryEngine
from intent_router import IntentRouter, Intent
from url_guard import PublicUrl
from reg_validator import get_reg_validator
from session import get_session_store, SessionStore
from workflow_services import CurriculumService, ExpressionService, WorkflowBuildService
from feature_services import ErrorPatchService, ReverseService
from general_rag import GeneralRAGService
from ontology_enhancer import get_ontology_enhancer
from semantic_validator import get_semantic_validator, ValidationSeverity

log = logging.getLogger("naito.workspace")
router = APIRouter()
_intent_router = IntentRouter()

_REG_REQUIRED_INTENTS  = {Intent.WORKFLOW_BUILD, Intent.EXPRESSION, Intent.ERROR_PATCH}
_SEM_VALIDATE_INTENTS  = {Intent.WORKFLOW_BUILD, Intent.ERROR_PATCH}


# ── Request schema ─────────────────────────────────────────────────────────────

class AiMessage(BaseModel):
    """Vercel AI SDK 메시지 형식."""
    role: str
    content: str
    id: str | None = None


class WorkspaceRequest(BaseModel):
    # Vercel AI SDK useChat 형식 (interface/ 웹앱)
    messages: list[AiMessage] | None = None
    # 세션 및 추가 컨텍스트
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    # 크롬 익스텐션 레거시 필드
    message: str = Field(default="")
    node_data: dict | None = None
    error_log: str | None = None
    raw_json: str | None = None
    model: str = Field(default="")
    openai_api_key: str | None = None
    # 이미지 처리: Vercel Blob URL 또는 base64 data URL (vision 모델 전용)
    image_urls: list[str] | None = None
    # 웹 유저의 n8n 인스턴스 연결 정보 (자동 워크플로우 가져오기용)
    n8n_url: PublicUrl | None = None
    n8n_api_key: str | None = None


# ── AI SDK 스트림 헬퍼 ─────────────────────────────────────────────────────────

def ai_text(token: str) -> str:
    """텍스트 델타: 0:"token"\n"""
    return f'0:{json.dumps(token, ensure_ascii=False)}\n'


def ai_data(parts: list) -> str:
    """데이터 파트: 2:[...]\n"""
    return f'2:{json.dumps(parts, ensure_ascii=False)}\n'


def ai_done() -> str:
    """스트림 종료: d:{"finishReason":"stop"}\n"""
    return 'd:{"finishReason":"stop"}\n'


def _sse_to_ai(chunk: str) -> str | None:
    """서비스 레이어의 SSE 청크를 AI SDK 데이터 스트림 포맷으로 변환."""
    lines = chunk.splitlines()
    event_type: str | None = None
    data_raw: str | None = None

    for line in lines:
        if line.startswith("event: "):
            event_type = line[7:].strip()
        elif line.startswith("data: "):
            data_raw = line[6:]

    if event_type is None or data_raw is None:
        return None

    if event_type == "token":
        # 서비스가 yield sse("token", raw_string) 형태로 전송
        try:
            token_value = json.loads(data_raw)
            return ai_text(token_value if isinstance(token_value, str) else data_raw)
        except json.JSONDecodeError:
            return ai_text(data_raw)

    if event_type == "done":
        return ai_done()

    # 구조화 이벤트 (intent, curriculum, card, expression, error_alert, report, reg_warning)
    try:
        obj = json.loads(data_raw)
    except json.JSONDecodeError:
        obj = data_raw

    if isinstance(obj, dict):
        if "type" in obj:
            # obj가 자체 서브타입을 갖는 경우(예: card 이벤트의
            # workflow_inject/error_patch_apply) — 그대로 {"type": event_type, **obj}로
            # 병합하면 obj["type"]이 event_type을 덮어써서, 프론트엔드가 라우팅에
            # 쓰는 최상위 이벤트 종류(예: "card")가 사라지고 서브타입만 남는 문제가
            # 있었음. obj 고유의 서브타입은 "kind"로 옮겨서 둘 다 보존한다.
            merged = {"type": event_type}
            for k, v in obj.items():
                merged["kind" if k == "type" else k] = v
            parts = [merged]
        else:
            parts = [{"type": event_type, **obj}]
    else:
        parts = [{"type": event_type, "data": obj}]

    return ai_data(parts)


# ── 채팅 제목 생성 엔드포인트 ──────────────────────────────────────────────────

class TitleRequest(BaseModel):
    message: str = Field(default="")
    model: str = Field(default="")


@router.post("/generate-title")
async def generate_title(req: TitleRequest):
    """첫 메시지로 채팅 제목 생성 (LLM 단일 호출, 스트리밍 없음)."""
    model = req.model[len("openai:"):] if req.model.startswith("openai:") else settings.llm_model
    system = (
        "Summarize the user's message into a short chat title. "
        "3–6 words, no quotes, no punctuation at the end. "
        "Reply with the title only, in the same language as the message."
    )
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": req.message[:500]},
            ],
            max_tokens=30,
        )
        title = (resp.choices[0].message.content or "").strip()
        title = title.replace('"', "").replace("#", "").strip()
        return {"title": title or req.message[:60]}
    except Exception:
        return {"title": req.message[:60]}


# ── 경량 Intent 판별 엔드포인트 ────────────────────────────────────────────────

class IntentCheckRequest(BaseModel):
    message: str = Field(default="")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model: str = Field(default="")
    n8n_url: PublicUrl | None = Field(default=None)
    openai_api_key: str | None = Field(default=None)


@router.post("/check-intent")
async def check_intent(
    req: IntentCheckRequest,
    store: SessionStore = Depends(get_session_store),
):
    """LLM으로 Intent 판별. 클라이언트가 n8n prefetch 여부 결정에 사용."""
    history = store.get_history(req.session_id)
    route_result = await _intent_router.route(
        message=req.message,
        model=req.model or "",
        history=history,
        n8n_url=req.n8n_url or None,
        openai_api_key=req.openai_api_key or None,
    )
    intent = route_result.intent
    return {"intent": intent, "needs_canvas": intent == Intent.REVERSE}


# ── 메인 스트리밍 엔드포인트 ────────────────────────────────────────────────────

@router.post("/stream")
async def workspace_stream(
    req: WorkspaceRequest,
    engine: N8NQueryEngine = Depends(get_engine),
    store: SessionStore = Depends(get_session_store),
    cf: CredentialFilter = Depends(get_credential_filter),
):
    """
    Vercel AI SDK useChat 훅과 호환되는 통합 스트리밍 허브.
    """

    async def event_stream() -> AsyncGenerator[str, None]:
        # messages 배열(useChat 훅) 또는 message 필드(크롬 익스텐션) 에서 텍스트 추출
        message = req.message or ""
        if not message and req.messages:
            for msg in reversed(req.messages):
                if msg.role == "user":
                    message = msg.content
                    break

        if not message:
            yield ai_text("메시지를 입력해 주세요.")
            yield ai_done()
            return

        session_id = req.session_id

        # 자격증명 필터
        sanitized_raw_json = None
        if req.raw_json:
            try:
                wf_obj = json.loads(req.raw_json)
                sanitized_raw_json = json.dumps(
                    cf.filter_workflow(wf_obj), ensure_ascii=False
                )
            except json.JSONDecodeError:
                sanitized_raw_json = cf.filter_string(req.raw_json)

        sanitized_node_data = cf.filter_workflow(req.node_data) if req.node_data else None
        sanitized_error_log = cf.filter_string(req.error_log) if req.error_log else None

        # Intent 분기 (꼬리 물기 감지를 위해 history 먼저 로드)
        prior_history = store.get_history(session_id)
        route_result = await _intent_router.route(
            message=message,
            model=req.model or "",
            node_data=sanitized_node_data,
            error_log=sanitized_error_log,
            raw_json=sanitized_raw_json,
            history=prior_history,
            n8n_url=req.n8n_url or None,
            openai_api_key=req.openai_api_key or None,
        )
        intent = route_result.intent
        log.info(
            "[%s] Intent → %s (사전 확장 힌트: %r)",
            session_id, intent, route_result.expansion_hint,
        )

        # 크롬 확장 없이 웹 채팅에 에러 로그를 직접 붙여넣은 경우 대비:
        # req.error_log 구조화 필드(확장 프로그램 전용)가 비어 있어도, 의도
        # 분류기가 이미 메시지 본문을 보고 ERROR_PATCH로 판단했다면 메시지 자체를
        # 에러 로그로 사용한다. (없으면 ErrorPatchService가 "에러 로그가
        # 없습니다"로 즉시 종료돼, 채팅창에 에러를 붙여넣는 가장 자연스러운
        # 사용법이 항상 실패하는 문제가 있었음)
        if intent == Intent.ERROR_PATCH and not sanitized_error_log:
            sanitized_error_log = cf.filter_string(message)

        yield ai_data([{
            "type": "intent",
            "intent": str(intent),
            "label": _intent_router.describe(intent),
        }])

        store.add_turn(session_id, "user", message, intent=intent)
        full_history = store.get_history(session_id)

        # ── 꼬리 물기: 직전 user 메시지를 RAG 쿼리에 포함 ─────────────────
        rag_query = message
        if prior_history:
            last_user_content = next(
                (
                    (getattr(t, "content", None) or t.get("content", ""))
                    for t in reversed(prior_history)
                    if (getattr(t, "role", None) or t.get("role", "")) == "user"
                ),
                None,
            )
            if last_user_content and len(message) < 30:
                rag_query = f"{last_user_content[:120]} {message}"
                log.info("[%s] RAG 쿼리 강화: %s", session_id, rag_query[:80])

        # ── 온톨로지 기반 쿼리 확장 (OntologyEnhancer) ────────────────────
        # route_result.expansion_hint: 의도 분류와 같은 LLM 호출에서 함께 받은
        # 사전 맥락 확장 힌트. 원본 쿼리에 노드명이 없어도 목적 서술만으로
        # 필요 노드를 추정해 감지 범위를 넓힌다(§3.1).
        enhancer = get_ontology_enhancer()
        eq = enhancer.enhance(
            query=rag_query,
            intent=str(intent),
            expansion_hint=route_result.expansion_hint,
        )
        if eq.expanded_query != rag_query:
            log.info(
                "[%s] 온톨로지 확장: 노드=%s (힌트로 추가된 노드=%s), 용어+%d개",
                session_id,
                [n.short_type for n in eq.detected_nodes],
                [n.short_type for n in eq.expansion_detected_nodes],
                len(eq.related_node_terms),
            )

        # 온톨로지 감지 결과를 이벤트로 공개 (투명성)
        if eq.detected_nodes or eq.pattern:
            yield ai_data([{
                "type": "ontology_context",
                "detected_nodes": [n.display_name for n in eq.detected_nodes],
                "expansion_detected_nodes": [n.display_name for n in eq.expansion_detected_nodes],
                "pattern": eq.pattern.name if eq.pattern else None,
                "hints_count": len(eq.ontology_hints),
            }])

        ctx = {
            "session_id":      session_id,
            "message":         message,
            "rag_query":       eq.expanded_query,      # 확장된 쿼리 사용
            "node_data":       sanitized_node_data,
            "error_log":       sanitized_error_log,
            "raw_json":        sanitized_raw_json,
            "model":           req.model or settings.llm_model,
            "openai_api_key":  req.openai_api_key or None,
            "history":         full_history,
            "ontology_hints":    eq.ontology_hints,       # 서비스 프롬프트에 삽입
            "detected_nodes":    [n.short_type for n in eq.detected_nodes],
            "typo_corrections":  eq.typo_corrections,     # 오타 교정 정보
            "image_urls":        req.image_urls or [],     # 이미지 vision 처리
            "n8n_url":           req.n8n_url or "",
            "n8n_api_key":       req.n8n_api_key or "",
        }

        reg  = get_reg_validator()
        semv = get_semantic_validator()
        token_buffer: list[str] = []
        response_tokens: list[str] = []  # 세션 저장용 전체 텍스트 버퍼

        # 서비스 선택
        if intent == Intent.CURRICULUM:
            service_gen = CurriculumService(engine).stream(ctx)
        elif intent == Intent.EXPRESSION:
            service_gen = ExpressionService(engine).stream(ctx)
        elif intent == Intent.WORKFLOW_BUILD:
            service_gen = WorkflowBuildService(engine, store).stream(ctx)
        elif intent == Intent.ERROR_PATCH:
            service_gen = ErrorPatchService(engine).stream(ctx)
        elif intent == Intent.REVERSE:
            service_gen = ReverseService(engine).stream(ctx)
        else:
            service_gen = GeneralRAGService(engine).stream(ctx)

        # SSE → AI SDK 변환 스트리밍
        async for sse_chunk in service_gen:
            ai_chunk = _sse_to_ai(sse_chunk)
            if not ai_chunk:
                continue
            if ai_chunk.startswith("0:"):
                try:
                    token_text = json.loads(ai_chunk[2:])
                    if isinstance(token_text, str):
                        response_tokens.append(token_text)
                        if intent in _REG_REQUIRED_INTENTS:
                            token_buffer.append(token_text)
                except Exception:
                    pass
            yield ai_chunk

        # assistant 응답 세션 저장 (다음 턴에서 대화 맥락으로 활용)
        if response_tokens:
            store.add_turn(session_id, "assistant", "".join(response_tokens))

        full_text = "".join(token_buffer) if token_buffer else ""

        # ── REG 검증 Stage 1: 파라미터 오타 자동 수정 ─────────────────────
        if intent in _REG_REQUIRED_INTENTS and full_text:
            _, corrections = reg.validate_and_fix(full_text)
            if corrections:
                warning = reg.build_warning_event(corrections)
                log.info("[REG] %d개 파라미터 자동 수정", len(corrections))
                yield ai_data([{"type": "reg_warning", **warning}])

        # ── Semantic Validation Stage 2–4: 구조·속성·패턴·표현식 ──────────
        if intent in _SEM_VALIDATE_INTENTS and (full_text or response_tokens):
            sv_text = full_text or "".join(response_tokens)
            try:
                report = semv.validate(
                    workflow_json_str=sv_text,
                    response_text=sv_text,
                )
                # 에러·경고가 있을 때만 이벤트 발행 (info만 있으면 조용히)
                if report.errors or report.warnings:
                    log.info(
                        "[SemanticValidator] errors=%d warnings=%d",
                        len(report.errors), len(report.warnings),
                    )
                    yield ai_data([{"type": "validation_report",
                                    **report.to_sse_payload()}])
            except Exception as e:
                log.warning("[SemanticValidator] 검증 실패: %s", e)

        yield ai_done()

    return StreamingResponse(
        event_stream(),
        media_type="text/plain; charset=utf-8",
        headers={
            "X-Vercel-AI-Data-Stream": "v1",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        },
    )
