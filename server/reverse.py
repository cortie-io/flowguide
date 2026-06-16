"""
POST /api/workflow/reverse — 리버스 엔지니어링 전용 엔드포인트
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ReverseRequest(BaseModel):
    session_id: str
    workflow_json: str


@router.post("/reverse")
async def reverse_workflow(req: ReverseRequest):
    return {
        "status": "received",
        "message": "워크플로우가 수신되었습니다. 스트리밍 분석은 /api/workspace/stream으로 요청하세요.",
    }
