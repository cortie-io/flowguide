"""
POST /api/workflow/inject, /api/workflow/rollback, /api/workflow/snapshot/status,
     /api/workflow/remote-inject
"""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from credential_filter import get_credential_filter, CredentialFilter
from session import get_session_store, SessionStore

log = logging.getLogger("naito.workflow")
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


class RemoteInjectRequest(BaseModel):
    n8n_url: str
    api_key: str | None = None
    workflow_json: dict


# n8n의 워크플로우 생성 API(POST /api/v1/workflows)는 ajv 스키마 검증이 엄격해서
# 노드 객체에 스키마에 없는 필드가 하나라도 있으면 전체 요청을 거부한다
# ("must NOT have additional properties"). LLM이 자유롭게 생성한 JSON에는
# webhookId, notes 같은 부가 필드가 종종 섞여 있어 그대로 보내면 항상 실패하므로,
# n8n이 실제로 허용하는 필드만 남기고 나머지는 제거한다.
_N8N_NODE_ALLOWED_FIELDS = {
    "id", "name", "type", "typeVersion", "position", "parameters",
    "credentials", "disabled", "notes", "notesInFlow", "continueOnFail",
    "alwaysOutputData", "retryOnFail", "maxTries", "waitBetweenTries", "onError",
}


def _sanitize_node(node: dict) -> dict:
    return {k: v for k, v in node.items() if k in _N8N_NODE_ALLOWED_FIELDS}


def _sanitize_connections(connections: dict) -> dict:
    """LLM이 `main` 래퍼나 `type` 필드를 빼먹은 축약형 connections를 n8n이
    요구하는 정식 형태({"Node": {"main": [[{"node","type","index"}]]}})로 보정한다."""
    fixed: dict = {}
    for src, outputs in (connections or {}).items():
        if isinstance(outputs, dict) and "main" in outputs:
            fixed[src] = outputs
            continue
        # 축약형: [[{"node": .., "index": ..}]] (main 래퍼/type 누락)
        branches = outputs if isinstance(outputs, list) else [outputs]
        main_branches = []
        for branch in branches:
            conns = branch if isinstance(branch, list) else [branch]
            main_branches.append([
                {"node": c.get("node"), "type": c.get("type", "main"), "index": c.get("index", 0)}
                for c in conns if isinstance(c, dict) and c.get("node")
            ])
        fixed[src] = {"main": main_branches}
    return fixed


@router.post("/remote-inject")
async def remote_inject_workflow(req: RemoteInjectRequest):
    """웹 유저가 자신의 n8n 인스턴스에 REST API로 워크플로우를 직접 생성.

    (이 엔드포인트는 원래 main.py에 연결되지 않은 죽은 파일에만 존재해서
    프론트엔드의 "n8n에 바로 생성" 버튼이 항상 404로 실패하고 있었음 —
    실제로 라우터에 등록되는 이 파일로 옮겨서 살림.)
    """
    url = req.n8n_url.rstrip("/") + "/api/v1/workflows"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if req.api_key:
        headers["X-N8N-API-KEY"] = req.api_key

    raw_nodes = req.workflow_json.get("nodes", [])
    payload = {
        "name": req.workflow_json.get("name", "Naito 생성 워크플로우"),
        "nodes": [_sanitize_node(n) for n in raw_nodes if isinstance(n, dict)],
        "connections": _sanitize_connections(req.workflow_json.get("connections", {})),
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
