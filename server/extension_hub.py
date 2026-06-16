"""
app/ws/extension_hub.py

크롬 익스텐션 ↔ 백엔드 WebSocket 실시간 채널.
익스텐션이 보내는 이벤트 타입:
  node_selected   → ② 노드 인스펙션 트리거
  error_detected  → ④ 에러 인터럽트 트리거
  workflow_copy   → ⑤ 리버스 / ③ 최적화 트리거
  canvas_ready    → 캔버스 상태 동기화
  inject_confirm  → ⑥ 주입 확정 (스냅샷 저장 후 실행)
  rollback_req    → ⑥ Undo 요청

백엔드 → 익스텐션 이벤트:
  inject_workflow → 노드 주입 명령
  patch_node      → 특정 노드 파라미터 패치
  restore_canvas  → 롤백 복원 데이터
  ui_card         → 프론트엔드 카드 렌더링 데이터
"""

from __future__ import annotations

import json
import logging
from typing import Callable

from fastapi import WebSocket

log = logging.getLogger("nodi.ws")


class ExtensionHub:
    """
    세션별 WebSocket 연결 관리 + 이벤트 디스패처.
    프로덕션에서는 Redis Pub/Sub 로 수평 확장.
    """

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}
        self._handlers:    dict[str, Callable]  = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        self._handlers["node_selected"]  = self._handle_node_selected
        self._handlers["error_detected"] = self._handle_error_detected
        self._handlers["workflow_copy"]  = self._handle_workflow_copy
        self._handlers["inject_confirm"] = self._handle_inject_confirm
        self._handlers["rollback_req"]   = self._handle_rollback_req
        self._handlers["canvas_ready"]   = self._handle_canvas_ready

    # ── 연결 관리 ──────────────────────────────────────────────────────────
    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self._connections[session_id] = ws
        log.info("[ExtHub] 연결: %s (총 %d)", session_id, len(self._connections))
        await ws.send_json({"event": "connected", "session_id": session_id})

    def disconnect(self, session_id: str):
        self._connections.pop(session_id, None)
        log.info("[ExtHub] 연결 해제: %s", session_id)

    # ── 이벤트 디스패치 ────────────────────────────────────────────────────
    async def dispatch(self, session_id: str, data: dict):
        event_type = data.get("event", "unknown")
        handler    = self._handlers.get(event_type, self._handle_unknown)
        await handler(session_id, data)

    async def send(self, session_id: str, payload: dict):
        """백엔드 → 익스텐션 단방향 푸시."""
        ws = self._connections.get(session_id)
        if ws:
            try:
                await ws.send_json(payload)
            except Exception as e:
                log.warning("[ExtHub] 전송 실패 (%s): %s", session_id, e)

    async def broadcast(self, payload: dict):
        """모든 연결 세션에 브로드캐스트 (관리자/디버그용)."""
        for session_id, ws in self._connections.items():
            try:
                await ws.send_json(payload)
            except Exception:
                pass

    # ── 이벤트 핸들러 ──────────────────────────────────────────────────────

    async def _handle_node_selected(self, session_id: str, data: dict):
        """
        익스텐션이 노드 선택 시 자동 전송.
        → 백엔드가 노드 인스펙션 힌트를 즉시 반환.
        """
        node_data = data.get("payload", {})
        log.info("[ExtHub][%s] node_selected: %s", session_id, node_data.get("type"))

        # 즉각 수식 힌트 반환 (비동기 RAG 없이 필드 파싱만)
        exec_fields = list(node_data.get("inputData", {}).get("json", {}).keys())
        hints = [f"{{{{ $json.{f} }}}}" for f in exec_fields[:3]]
        await self.send(session_id, {
            "event":       "node_inspect_hint",
            "node_type":   node_data.get("type"),
            "field_hints": hints,
            "message":     "수식이 필요하면 채팅창에 '수식 만들어줘'라고 입력하세요.",
        })

    async def _handle_error_detected(self, session_id: str, data: dict):
        """
        MutationObserver가 에러 DOM을 감지하여 전송.
        → 대화창 상단에 에러 경고 컨텍스트 즉시 바인딩 트리거.
        """
        error_log = data.get("payload", {}).get("error_message", "")
        log.warning("[ExtHub][%s] error_detected: %s", session_id, error_log[:100])
        await self.send(session_id, {
            "event":     "error_alert_ui",
            "error_log": error_log,
            "message":   "에러가 감지되었습니다. 채팅창에서 자동 진단을 시작합니다.",
            "auto_prompt": f"다음 에러를 진단하고 수술해줘: {error_log[:200]}",
        })

    async def _handle_workflow_copy(self, session_id: str, data: dict):
        """유저가 캔버스 전체를 복사하여 전송 → 리버스 엔지니어링 안내."""
        workflow_json = data.get("payload", {})
        node_count = len(workflow_json.get("nodes", []))
        await self.send(session_id, {
            "event":       "workflow_received",
            "node_count":  node_count,
            "message":     f"{node_count}개 노드 워크플로우 수신. '분석해 줘'라고 입력하면 역분석합니다.",
            "raw_json":    json.dumps(workflow_json, ensure_ascii=False),
        })

    async def _handle_inject_confirm(self, session_id: str, data: dict):
        """⑥ 주입 확정 — 실제 n8n REST API 호출 위임."""
        payload  = data.get("payload", {})
        workflow = payload.get("workflow")
        if not workflow:
            await self.send(session_id, {"event": "error", "message": "주입 페이로드 없음"})
            return

        log.info("[ExtHub][%s] inject_confirm 수신 → n8n API 위임", session_id)
        # 실제 구현에서는 httpx 로 localhost:5678/api/v1/workflows 에 PUT/POST
        await self.send(session_id, {
            "event":   "inject_result",
            "status":  "queued",
            "message": "워크플로우가 캔버스에 주입 예약되었습니다.",
        })

    async def _handle_rollback_req(self, session_id: str, data: dict):
        """⑥ Undo 요청 → /api/workflow/rollback 내부 호출."""
        from session import get_session_store
        store = get_session_store()
        snap  = store.pop_snapshot(session_id)
        if snap:
            await self.send(session_id, {
                "event":             "restore_canvas",
                "restored_workflow": snap.workflow_json,
                "message":           "↩️ 이전 상태로 롤백 완료",
            })
        else:
            await self.send(session_id, {
                "event":   "rollback_failed",
                "message": "복원 가능한 스냅샷이 없습니다.",
            })

    async def _handle_canvas_ready(self, session_id: str, data: dict):
        await self.send(session_id, {
            "event": "ack", "message": "캔버스 동기화 완료"
        })

    async def _handle_unknown(self, session_id: str, data: dict):
        log.debug("[ExtHub][%s] 알 수 없는 이벤트: %s", session_id, data.get("event"))
