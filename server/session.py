"""
app/core/session.py

세션 인메모리 스토어:
  - 유저별 대화 히스토리 관리
  - ⑥ 워크플로우 스냅샷 저장 / 롤백 (State Rollback Engine)
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from config import settings


@dataclass
class WorkflowSnapshot:
    """캔버스 원격 주입 직전에 저장하는 워크플로우 원본 스냅샷."""
    session_id:    str
    workflow_json: dict
    operation:     str        # 어떤 작업 직전이었는지 (inject / patch / optimize)
    timestamp:     float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > settings.snapshot_ttl_seconds


@dataclass
class ConversationTurn:
    role:    str    # "user" | "assistant"
    content: str
    intent:  str = ""
    meta:    dict = field(default_factory=dict)


class SessionStore:
    """
    싱글턴 인메모리 세션 스토어.
    프로덕션에서는 Redis로 교체 가능하도록 인터페이스를 단순화.
    """

    def __init__(self):
        # session_id → list[ConversationTurn]
        self._history:   dict[str, list[ConversationTurn]] = defaultdict(list)
        # session_id → WorkflowSnapshot (최신 1개만 보존)
        self._snapshots: dict[str, WorkflowSnapshot]       = {}

    # ── 대화 히스토리 ──────────────────────────────────────────────────────
    def add_turn(self, session_id: str, role: str, content: str,
                 intent: str = "", meta: dict | None = None):
        self._history[session_id].append(
            ConversationTurn(role=role, content=content,
                             intent=intent, meta=meta or {})
        )
        # 최근 20턴만 유지 (컨텍스트 오버플로 방지)
        if len(self._history[session_id]) > 20:
            self._history[session_id] = self._history[session_id][-20:]

    def get_history(self, session_id: str) -> list[ConversationTurn]:
        return list(self._history.get(session_id, []))

    def clear_history(self, session_id: str):
        self._history[session_id] = []

    # ── ⑥ 스냅샷 저장 / 롤백 ─────────────────────────────────────────────
    def save_snapshot(self, session_id: str,
                      workflow_json: dict, operation: str) -> str:
        """
        캔버스 조작 직전에 호출.
        기존 스냅샷이 만료되었거나 없으면 신규 저장, 있으면 덮어씀.
        Returns snapshot_id (session_id 와 동일하게 단순화).
        """
        self._snapshots[session_id] = WorkflowSnapshot(
            session_id=session_id,
            workflow_json=workflow_json,
            operation=operation,
        )
        return session_id

    def get_snapshot(self, session_id: str) -> WorkflowSnapshot | None:
        snap = self._snapshots.get(session_id)
        if snap and snap.is_expired():
            del self._snapshots[session_id]
            return None
        return snap

    def pop_snapshot(self, session_id: str) -> WorkflowSnapshot | None:
        """롤백 후 스냅샷을 소비(삭제)하여 재롤백 방지."""
        snap = self._snapshots.pop(session_id, None)
        if snap and snap.is_expired():
            return None
        return snap

    def has_snapshot(self, session_id: str) -> bool:
        return session_id in self._snapshots and not self._snapshots[session_id].is_expired()


# 싱글턴
_store: SessionStore | None = None

def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore()
    return _store
