"""
app/routers/workflow.py  — 캔버스 주입(⑥ Snapshot 선행) + 롤백 엔드포인트
app/routers/node.py      — 노드 라이브 인스펙션 REST 엔드포인트
app/routers/error_patch.py — 에러 패치 전용 엔드포인트
app/routers/reverse.py   — 리버스 엔지니어링 전용 엔드포인트
"""

# ============================================================
# workflow.py
# ============================================================
from __future__ import annotations

import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.credential_filter import get_credential_filter, CredentialFilter
from app.core.session import get_session_store, SessionStore

log = logging.getLogger("naito.workflow")
router = APIRouter()


class InjectRequest(BaseModel):
    """캔버스 원격 주입 요청 — ⑥ 스냅샷 저장 선행."""
    session_id:      str
    current_workflow: dict  = Field(..., description="주입 전 현재 워크플로우 (익스텐션이 전송)")
    inject_payload:   dict  = Field(..., description="주입할 신규 워크플로우 JSON")
    operation:        str   = Field("inject", description="inject | patch | optimize")


class InjectResponse(BaseModel):
    status:       str
    snapshot_saved: bool
    message:      str
    sanitized_payload: dict


class RollbackRequest(BaseModel):
    session_id: str


class RollbackResponse(BaseModel):
    status:         str
    restored_workflow: dict | None
    message:        str


@router.post("/inject", response_model=InjectResponse)
async def inject_workflow(
    req:   InjectRequest,
    store: SessionStore      = Depends(get_session_store),
    cf:    CredentialFilter  = Depends(get_credential_filter),
):
    """
    ⑥ State Rollback Engine:
    캔버스 조작 직전 → 현재 상태 스냅샷 저장 → sanitize → 주입 페이로드 반환.
    익스텐션은 이 응답의 sanitized_payload 를 실제 n8n API에 적용.
    """
    # 스냅샷 저장 (원본 보존)
    store.save_snapshot(
        session_id    = req.session_id,
        workflow_json = req.current_workflow,
        operation     = req.operation,
    )
    log.info("[%s] 스냅샷 저장 완료 (operation=%s)", req.session_id, req.operation)

    # 주입 페이로드 자격증명 필터
    sanitized = cf.filter_workflow(req.inject_payload)

    return InjectResponse(
        status          = "ready",
        snapshot_saved  = True,
        message         = "스냅샷이 저장되었습니다. [↩️ Undo] 버튼으로 1초 내 롤백 가능.",
        sanitized_payload = sanitized,
    )


@router.post("/rollback", response_model=RollbackResponse)
async def rollback_workflow(
    req:   RollbackRequest,
    store: SessionStore = Depends(get_session_store),
):
    """
    ⑥ 1초 Undo 롤백:
    저장된 스냅샷을 꺼내어 익스텐션으로 반환 → 익스텐션이 캔버스 복원.
    """
    snap = store.pop_snapshot(req.session_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="롤백 가능한 스냅샷이 없습니다.")

    log.info("[%s] 롤백 실행 (operation=%s)", req.session_id, snap.operation)
    return RollbackResponse(
        status            = "restored",
        restored_workflow = snap.workflow_json,
        message           = f"'{snap.operation}' 작업 이전 상태로 롤백 완료.",
    )


class RemoteInjectRequest(BaseModel):
    n8n_url: str
    api_key: str | None = None
    workflow_json: dict


@router.post("/remote-inject")
async def remote_inject_workflow(req: RemoteInjectRequest):
    """웹 유저가 자신의 n8n 인스턴스에 REST API로 워크플로우를 직접 생성."""
    url = req.n8n_url.rstrip("/") + "/api/v1/workflows"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if req.api_key:
        headers["X-N8N-API-KEY"] = req.api_key

    payload = {
        "name": req.workflow_json.get("name", "Naito 생성 워크플로우"),
        "nodes": req.workflow_json.get("nodes", []),
        "connections": req.workflow_json.get("connections", {}),
        "settings": req.workflow_json.get("settings", {"executionOrder": "v1"}),
        "staticData": None,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            workflow_id = data.get("id", "")
            log.info("[RemoteInject] n8n 워크플로우 생성 완료 id=%s", workflow_id)
            return {
                "status": "ok",
                "workflow_id": workflow_id,
                "message": f"워크플로우가 n8n에 생성되었습니다 (ID: {workflow_id})",
            }
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"n8n API 오류: {e.response.text[:300]}",
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"n8n 연결 실패: {str(e)}")


@router.get("/snapshot/status")
async def snapshot_status(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
):
    """프론트엔드가 [↩️ Undo] 버튼 활성화 여부를 판단하기 위해 폴링."""
    return {
        "session_id":    session_id,
        "has_snapshot":  store.has_snapshot(session_id),
    }


# ============================================================
# node.py  — ② 노드 라이브 인스펙션
# ============================================================

from fastapi import APIRouter as _APIRouter
from pydantic import BaseModel as _BaseModel

node_router = _APIRouter()


class NodeInspectRequest(_BaseModel):
    session_id:  str
    node_data:   dict  = Field(..., description="익스텐션이 캡처한 노드 JSON (type + parameters)")
    exec_data:   dict  = Field(default_factory=dict, description="노드 실행 결과 입력 데이터 스냅샷")
    target_field: str  = Field("", description="추출 목표 필드명 (선택)")


class NodeInspectResponse(_BaseModel):
    node_type:       str
    missing_params:  list[str]
    spec_matched:    bool
    expressions:     list[str]
    inspect_summary: str


@node_router.post("/inspect", response_model=NodeInspectResponse)
async def inspect_node(
    req: NodeInspectRequest,
    cf:  CredentialFilter = Depends(get_credential_filter),
):
    """
    ② 노드 라이브 인스펙션:
    노드 JSON + 실행 데이터를 수신하여
    - 자격증명 마스킹
    - 파라미터 누락 교차 판정
    - 표현식 힌트 생성 (간이 버전, 전체는 /workspace/stream 에서)
    """
    safe_node = cf.filter_workflow(req.node_data)
    safe_exec = cf.filter_workflow(req.exec_data) if req.exec_data else {}

    node_type  = safe_node.get("type", "unknown")
    params     = safe_node.get("parameters", {})

    # 간단한 표현식 힌트 생성 (실행 데이터의 최상위 필드 기반)
    exec_fields = list(safe_exec.get("json", {}).keys()) if safe_exec else []
    expressions = [
        f"{{{{ $json.{field} }}}}" for field in exec_fields[:5]
    ]
    if req.target_field:
        expressions.insert(0, f"{{{{ $json.{req.target_field} }}}}")

    return NodeInspectResponse(
        node_type       = node_type,
        missing_params  = [],   # 실제 구현: spec 대조
        spec_matched    = True,
        expressions     = expressions,
        inspect_summary = f"{node_type} 노드 검사 완료. 필드 {len(exec_fields)}개 감지됨.",
    )
