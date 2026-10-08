"""
POST /api/workflow/inject, /api/workflow/rollback, /api/workflow/snapshot/status,
     /api/workflow/remote-inject
"""
from __future__ import annotations

import asyncio
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from credential_filter import get_credential_filter, CredentialFilter
from session import get_session_store, SessionStore
from url_guard import PublicUrl

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
    n8n_url: PublicUrl
    api_key: str | None = None
    workflow_json: dict
    verify_execution: bool = Field(
        default=False,
        description=(
            "true면 생성 직후 실제 실행까지 검증한다(H_exec, 런타임 실행 하네스). "
            "웹훅 트리거 노드가 포함된 워크플로우만 지원하며, 실제로 트리거를 호출하므로 "
            "워크플로우 내 노드의 부수효과(메시지 발송 등)가 실제로 발생할 수 있다. "
            "기본값은 false로, 기존 스키마 검증까지만 수행하는 동작을 그대로 유지한다."
        ),
    )


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


_WEBHOOK_TRIGGER_TYPES = {"n8n-nodes-base.webhook"}
_PENDING_EXECUTION_STATUSES = {"new", "running", "waiting"}


def _find_webhook_trigger(nodes: list[dict]) -> dict | None:
    for n in nodes:
        if isinstance(n, dict) and n.get("type") in _WEBHOOK_TRIGGER_TYPES:
            return n
    return None


async def _verify_execution(
    client: httpx.AsyncClient,
    n8n_url: str,
    headers: dict[str, str],
    workflow_id: str,
    webhook_node: dict,
) -> dict:
    """H_exec(런타임 실행 하네스): 생성된 워크플로우를 실제로 트리거하여 실행 결과를 확인한다.

    n8n Public API는 임의 트리거 타입의 워크플로우를 API 키만으로 즉시 실행하는
    엔드포인트를 제공하지 않는다(발행/평가용 test-run만 존재하며, 후자는 전용
    Evaluation Trigger 노드가 필요해 일반 생성 워크플로우에는 적용할 수 없다).
    따라서 API 키만으로 실제 실행 결과까지 확인 가능한 유일한 경로는, 웹훅 트리거
    워크플로우를 발행(publish)한 뒤 그 웹훅을 직접 호출하고 실행 목록을 폴링하는
    것이며, 본 함수는 이 경로에 한해 실행을 검증한다.
    """
    params = webhook_node.get("parameters", {}) or {}
    path = (params.get("path") or webhook_node.get("webhookId") or "").lstrip("/")
    method = (params.get("httpMethod") or "GET").upper()

    publish_resp = await client.post(f"{n8n_url}/api/v1/workflows/{workflow_id}/publish", headers=headers)
    if publish_resp.status_code >= 400:
        # 스키마 검증(생성 단계)은 통과했지만, 발행 단계에서만 드러나는 노드 설정 문제
        # (예: 자격 증명 미설정)가 있을 수 있어 원문 오류를 그대로 노출한다.
        return {
            "execution_verified": False,
            "execution_note": (
                f"워크플로우 발행 실패로 실행 검증을 생략했습니다 (HTTP {publish_resp.status_code}): "
                f"{publish_resp.text[:300]}"
            ),
        }

    try:
        trigger_url = f"{n8n_url}/webhook/{path}"
        # 본문이 필요한 메서드에 빈 요청을 보내면 워크플로우가 기대하는 필드가 전부
        # undefined가 되어, 워크플로우 구조와 무관한 실패(예: 존재하지 않는 필드 참조)가
        # 섞여 들어간다. 실제 페이로드 스키마는 알 수 없으므로 최소한 유효한 빈 JSON
        # 객체({})는 항상 채워 넣어, "본문을 아예 안 보냄"으로 인한 거짓 실패를 줄인다.
        request_kwargs: dict = {"timeout": 15.0}
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            request_kwargs["json"] = {}
        try:
            await client.request(method, trigger_url, **request_kwargs)
        except httpx.RequestError as e:
            return {
                "execution_verified": False,
                "execution_note": f"웹훅 호출에 실패해 실행 검증을 생략했습니다: {str(e)}",
            }

        # 폴링 간격: 처음엔 촘촘히(빠른 워크플로우는 곧바로 잡힘), n8n이 부하 상태거나
        # 실행 큐가 밀려 있을 때를 대비해 뒤로 갈수록 간격을 늘려 총 대기시간을 확보한다.
        # (파일럿 평가 중 다수의 동시다발적 publish/trigger/poll 반복으로 n8n이 부하
        # 상태에 놓였을 때, 고정 8초 폴링으로는 실제로 성공한 실행조차 "타임아웃"으로
        # 오판정되는 사례가 실측되어 늘림 — 최대 약 28초.)
        execution: dict | None = None
        for wait_s in (0.5, 0.5, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0):
            await asyncio.sleep(wait_s)
            list_resp = await client.get(
                f"{n8n_url}/api/v1/executions",
                params={"workflowId": workflow_id, "limit": 1},
                headers=headers,
            )
            if list_resp.status_code == 200:
                items = list_resp.json().get("data", [])
                if items and items[0].get("status") not in _PENDING_EXECUTION_STATUSES:
                    execution = items[0]
                    break
                elif items:
                    execution = items[0]

        if execution is None:
            return {
                "execution_verified": False,
                "execution_note": "웹훅 호출 후 실행 기록을 확인하지 못했습니다(타임아웃).",
            }

        status = execution.get("status")
        error_detail = None
        if status in ("error", "crashed"):
            detail_resp = await client.get(
                f"{n8n_url}/api/v1/executions/{execution['id']}",
                params={"includeData": "true"},
                headers=headers,
            )
            if detail_resp.status_code == 200:
                exec_data = (detail_resp.json().get("data") or {})
                result_data = exec_data.get("resultData")
                if isinstance(result_data, dict):
                    error_detail = (result_data.get("error") or {}).get("message")

        return {
            "execution_verified": True,
            "execution_status": status,
            "execution_error": error_detail,
        }
    finally:
        # 테스트 목적의 발행 상태를 실제 운영 상태로 남겨두지 않도록 정리한다.
        await client.post(f"{n8n_url}/api/v1/workflows/{workflow_id}/unpublish", headers=headers)


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
    sanitized_nodes = [_sanitize_node(n) for n in raw_nodes if isinstance(n, dict)]
    payload = {
        "name": req.workflow_json.get("name", "Naito 생성 워크플로우"),
        "nodes": sanitized_nodes,
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

            result: dict = {
                "status": "ok",
                "workflow_id": workflow_id,
                "message": f"워크플로우가 n8n에 생성되었습니다 (ID: {workflow_id})",
                "execution_verified": False,
                "execution_status": None,
                "execution_error": None,
                "execution_note": None,
            }

            if req.verify_execution:
                n8n_base = req.n8n_url.rstrip("/")
                webhook_node = _find_webhook_trigger(sanitized_nodes)
                if webhook_node is None:
                    result["execution_note"] = (
                        "이 워크플로우의 트리거 타입은 API 키만으로는 즉시 실행을 지원하지 않아 "
                        "스키마 검증까지만 확인되었습니다(웹훅 트리거 워크플로우만 실행 검증을 지원)."
                    )
                else:
                    exec_result = await _verify_execution(client, n8n_base, headers, workflow_id, webhook_node)
                    result.update(exec_result)
                    if exec_result.get("execution_verified"):
                        ok = exec_result.get("execution_status") == "success"
                        result["message"] = (
                            f"워크플로우가 n8n에 생성되고 실제로 실행되어 "
                            f"{'성공' if ok else '실패'}했습니다 (ID: {workflow_id})"
                        )

            return result
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"n8n API 오류: {e.response.text[:300]}",
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"n8n 연결 실패: {str(e)}")
