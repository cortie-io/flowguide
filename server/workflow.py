"""
POST /api/workflow/inject, /api/workflow/rollback, /api/workflow/snapshot/status
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from credential_filter import get_credential_filter, CredentialFilter
from session import get_session_store, SessionStore

log = logging.getLogger("nodi.workflow")
router = APIRouter()


class InjectRequest(BaseModel):
    session_id: str
    current_workflow: dict = Field(..., description="현재 캔버스 원본")
    inject_payload: dict = Field(..., description="주입할 신규 워크플로우")
    operation: str = Field("inject")


class InjectResponse(BaseModel):
    status: str
    snapshot_saved: bool
    message: str
    sanitized_payload: dict


class RollbackRequest(BaseModel):
    session_id: str


class RollbackResponse(BaseModel):
    status: str
    restored_workflow: dict | None
    message: str


def _curriculum_library() -> dict[str, dict]:
    return {
        "curriculum_w1": {
            "name": "Week 1 Starter",
            "nodes": [
                {"name": "Start", "type": "n8n-nodes-base.manualTrigger", "parameters": {}, "position": [280, 260]},
                {"name": "Set Greeting", "type": "n8n-nodes-base.set", "parameters": {"values": {"string": [{"name": "message", "value": "hello n8n"}]}}, "position": [520, 260]},
            ],
            "connections": {
                "Start": {"main": [[{"node": "Set Greeting", "type": "main", "index": 0}]]}
            },
        },
        "curriculum_w2": {
            "name": "Week 2 Split Out",
            "nodes": [
                {"name": "Start", "type": "n8n-nodes-base.manualTrigger", "parameters": {}, "position": [220, 260]},
                {"name": "Build Users", "type": "n8n-nodes-base.code", "parameters": {"jsCode": "return [{json:{users:[{name:'A'},{name:'B'},{name:'C'}]}}];"}, "position": [460, 260]},
                {"name": "Split Out Users", "type": "n8n-nodes-base.splitOut", "parameters": {"fieldToSplitOut": "users"}, "position": [740, 260]},
            ],
            "connections": {
                "Start": {"main": [[{"node": "Build Users", "type": "main", "index": 0}]]},
                "Build Users": {"main": [[{"node": "Split Out Users", "type": "main", "index": 0}]]}
            },
        },
        "curriculum_w3": {
            "name": "Week 3 API Aggregate",
            "nodes": [
                {"name": "Start", "type": "n8n-nodes-base.manualTrigger", "parameters": {}, "position": [220, 280]},
                {"name": "Fetch External Data", "type": "n8n-nodes-base.code", "parameters": {"jsCode": "return items;"}, "position": [500, 280]},
                {"name": "Calculate Average", "type": "n8n-nodes-base.code", "parameters": {"jsCode": "return items;"}, "position": [780, 280]},
            ],
            "connections": {
                "Start": {"main": [[{"node": "Fetch External Data", "type": "main", "index": 0}]]},
                "Fetch External Data": {"main": [[{"node": "Calculate Average", "type": "main", "index": 0}]]}
            },
        },
    }


@router.post("/inject", response_model=InjectResponse)
async def inject_workflow(
    req: InjectRequest,
    store: SessionStore = Depends(get_session_store),
    cf: CredentialFilter = Depends(get_credential_filter),
):
    store.save_snapshot(req.session_id, req.current_workflow, req.operation)
    sanitized = cf.filter_workflow(req.inject_payload)
    return InjectResponse(
        status="ready",
        snapshot_saved=True,
        message="스냅샷이 저장되었습니다. [↩️ Undo] 버튼으로 1초 내 롤백 가능.",
        sanitized_payload=sanitized,
    )


@router.post("/rollback", response_model=RollbackResponse)
async def rollback_workflow(
    req: RollbackRequest,
    store: SessionStore = Depends(get_session_store),
):
    snap = store.pop_snapshot(req.session_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="롤백 가능한 스냅샷이 없습니다.")
    return RollbackResponse(
        status="restored",
        restored_workflow=snap.workflow_json,
        message=f"'{snap.operation}' 작업 이전 상태로 롤백 완료.",
    )


@router.get("/snapshot/status")
async def snapshot_status(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
):
    return {"session_id": session_id, "has_snapshot": store.has_snapshot(session_id)}


@router.get("/curriculum/code/{code_id}")
async def curriculum_code(code_id: str):
    lib = _curriculum_library()
    wf = lib.get(code_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="해당 커리큘럼 코드를 찾을 수 없습니다.")
    return {"code_id": code_id, "workflow_json": wf}
