"""
POST /api/node/inspect — 노드 라이브 인스펙션
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from credential_filter import get_credential_filter, CredentialFilter

router = APIRouter()


class NodeInspectRequest(BaseModel):
    session_id: str
    node_data: dict = Field(..., description="익스텐션이 캡처한 노드 JSON")
    exec_data: dict = Field(default_factory=dict, description="노드 실행 결과 입력 데이터")
    target_field: str = Field("", description="추출 목표 필드명 (선택)")


class NodeInspectResponse(BaseModel):
    node_type: str
    missing_params: list[str]
    spec_matched: bool
    expressions: list[str]
    inspect_summary: str


@router.post("/inspect", response_model=NodeInspectResponse)
async def inspect_node(
    req: NodeInspectRequest,
    cf: CredentialFilter = Depends(get_credential_filter),
):
    safe_node = cf.filter_workflow(req.node_data)
    safe_exec = cf.filter_workflow(req.exec_data) if req.exec_data else {}

    node_type = safe_node.get("type", "unknown")
    exec_fields = list(safe_exec.get("json", {}).keys()) if safe_exec else []
    expressions = [f"{{{{ $json.{f} }}}}" for f in exec_fields[:5]]
    if req.target_field:
        expressions.insert(0, f"{{{{ $json.{req.target_field} }}}}")

    return NodeInspectResponse(
        node_type=node_type,
        missing_params=[],
        spec_matched=True,
        expressions=expressions,
        inspect_summary=f"{node_type} 노드 검사 완료. 필드 {len(exec_fields)}개 감지됨.",
    )
