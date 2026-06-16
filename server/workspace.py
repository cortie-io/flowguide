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
from reg_validator import get_reg_validator
from session import get_session_store, SessionStore
from workflow_services import CurriculumService, ExpressionService, WorkflowBuildService
from feature_services import ErrorPatchService, ReverseService
from general_rag import GeneralRAGService

log = logging.getLogger("nodi.workspace")
router = APIRouter()
_intent_router = IntentRouter()

_REG_REQUIRED_INTENTS = {Intent.WORKFLOW_BUILD, Intent.EXPRESSION, Intent.ERROR_PATCH}


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
        parts = [{"type": event_type, **obj}]
    else:
        parts = [{"type": event_type, "data": obj}]

    return ai_data(parts)


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

        # Intent 분기
        intent = _intent_router.route(
            message=message,
            node_data=sanitized_node_data,
            error_log=sanitized_error_log,
            raw_json=sanitized_raw_json,
        )
        log.info("[%s] Intent → %s", session_id, intent)
        yield ai_data([{
            "type": "intent",
            "intent": str(intent),
            "label": _intent_router.describe(intent),
        }])

        store.add_turn(session_id, "user", message, intent=intent)

        ctx = {
            "session_id":   session_id,
            "message":      message,
            "node_data":    sanitized_node_data,
            "error_log":    sanitized_error_log,
            "raw_json":     sanitized_raw_json,
            "model":        req.model or settings.llm_model,
            "history":      store.get_history(session_id),
        }

        reg = get_reg_validator()
        token_buffer: list[str] = []

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
            # 토큰 버퍼 누적 (REG 검증용)
            if ai_chunk.startswith("0:") and intent in _REG_REQUIRED_INTENTS:
                try:
                    token_text = json.loads(ai_chunk[2:])
                    if isinstance(token_text, str):
                        token_buffer.append(token_text)
                except Exception:
                    pass
            yield ai_chunk

        # REG 검증 (코드 생성 Intent)
        if intent in _REG_REQUIRED_INTENTS and token_buffer:
            full_text = "".join(token_buffer)
            _, corrections = reg.validate_and_fix(full_text)
            if corrections:
                warning = reg.build_warning_event(corrections)
                log.info("[REG] %d개 파라미터 자동 수정", len(corrections))
                yield ai_data([{"type": "reg_warning", **warning}])

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
