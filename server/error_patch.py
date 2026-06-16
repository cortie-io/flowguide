"""
POST /api/error/patch — 에러 패치 전용 엔드포인트
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ErrorPatchRequest(BaseModel):
    session_id: str
    error_log: str
    node_name: str = ""


@router.post("/patch")
async def error_patch(req: ErrorPatchRequest):
    return {
        "status": "received",
        "message": "에러 로그가 수신되었습니다. 상세 진단은 /api/workspace/stream으로 요청하세요.",
        "error_preview": req.error_log[:100],
    }
