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
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.engine import get_engine          # N8NQueryEngine 싱글턴
from app.core.session import SessionStore       # 인메모리 세션/스냅샷
from app.routers import workspace, node, workflow, error_patch, reverse
from app.ws.extension_hub import ExtensionHub

log = logging.getLogger("naito.main")

# ── 앱 라이프사이클 ────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Naito 백엔드 기동 — RAG 엔진 워밍업 시작")
    await get_engine()          # Chroma + BM25 인덱스 로드 (최초 1회)
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
)

# ── 라우터 등록 ────────────────────────────────────────────────────────────────
app.include_router(workspace.router,   prefix="/api/workspace",  tags=["Workspace"])
app.include_router(node.router,        prefix="/api/node",        tags=["Node"])
app.include_router(workflow.router,    prefix="/api/workflow",    tags=["Workflow"])
app.include_router(error_patch.router, prefix="/api/error",       tags=["ErrorPatch"])
app.include_router(reverse.router,     prefix="/api/workflow",    tags=["Reverse"])

# ── 익스텐션 WebSocket 허브 ────────────────────────────────────────────────────
hub = ExtensionHub()

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
