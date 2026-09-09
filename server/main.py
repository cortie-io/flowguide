"""
=============================================================================
Naito — Next-Gen Node Automation Tutor
main.py  |  FastAPI 백엔드 엔트리포인트

Single Unified Workspace 파이프라인:
  모든 유저 인풋은 /api/workspace/stream 하나로 진입,
  IntentRouter가 5대 기능 + 2대 가드레일로 내부 분기.

엔드포인트 맵:
  POST /api/workspace/stream          ← 통합 SSE 스트리밍 허브 (메인)
  POST /api/node/inspect              ← ② 노드 라이브 인스펙션
  POST /api/workflow/inject           ← ③ 캔버스 원격 주입 (⑥ Snapshot 선행)
  POST /api/workflow/rollback         ← ⑥ 1초 Undo 롤백
  POST /api/error/patch               ← ④ 에러 인터럽트 수술
  POST /api/workflow/reverse          ← ⑤ 리버스 엔지니어링
  WS   /ws/extension                  ← 크롬 익스텐션 실시간 채널
=============================================================================
"""

from __future__ import annotations

import asyncio
import logging
import uuid
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure local modules resolve even when launched as `uvicorn server.main:app` from repo root.
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import settings
from engine import get_engine          # N8NQueryEngine 싱글턴
from session import SessionStore       # 인메모리 세션/스냅샷
import workspace
import node
import workflow
import error_patch
import reverse
from extension_hub import ExtensionHub

log = logging.getLogger("naito.main")

async def _warmup_llm() -> None:
    """서버 기동 시 OpenAI API 키가 유효한지 가볍게 확인한다."""
    if not settings.openai_api_key:
        log.warning("[LLM] OPENAI_API_KEY가 설정되어 있지 않음")
        return
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        await client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
        )
        log.info("[LLM] OpenAI 연결 확인 완료: %s", settings.llm_model)
    except Exception as e:
        log.warning("[LLM] OpenAI 연결 확인 실패(무시): %s", e)


# ── 앱 라이프사이클 ────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Naito 백엔드 기동 — RAG 엔진 및 LLM 워밍업 시작")
    await get_engine()          # Chroma + BM25 인덱스 로드 (최초 1회)
    asyncio.create_task(_warmup_llm())   # LLM 백그라운드 프리로드
    yield
    log.info("Naito 백엔드 종료")

app = FastAPI(
    title="Naito Backend API",
    version="2.0.0",
    description="n8n 오토-아키텍트 RAG 추론 엔진 + 크롬 익스텐션 제어 허브",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 크롬 익스텐션 origin 허용
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Vercel-AI-Data-Stream"],
)

# ── 라우터 등록 ────────────────────────────────────────────────────────────────
app.include_router(workspace.router,   prefix="/api/workspace",  tags=["Workspace"])
app.include_router(node.router,        prefix="/api/node",        tags=["Node"])
app.include_router(workflow.router,    prefix="/api/workflow",    tags=["Workflow"])
app.include_router(error_patch.router, prefix="/api/error",       tags=["ErrorPatch"])
app.include_router(reverse.router,     prefix="/api/workflow",    tags=["Reverse"])

# ── 익스텐션 WebSocket 허브 ────────────────────────────────────────────────────
hub = ExtensionHub()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Naito"}

@app.websocket("/ws/extension")
async def extension_ws(websocket: WebSocket):
    session_id = str(uuid.uuid4())
    await hub.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await hub.dispatch(session_id, data)
    except WebSocketDisconnect:
        hub.disconnect(session_id)
