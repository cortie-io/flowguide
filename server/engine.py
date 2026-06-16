"""
app/core/engine.py

N8NQueryEngine 싱글턴 래퍼.
query_engine.py 의 N8NQueryEngine 을 비동기 FastAPI 환경에서
최초 1회만 초기화하고 이후 모든 요청에서 재사용한다.

의존성:
  - query_engine.py 가 프로젝트 루트에 존재해야 함
  - final_rag_chunks_v2.jsonl 과 .chroma_db_v2/ 가 필요
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

log = logging.getLogger("nodi.engine")

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

_engine_instance: Optional["N8NQueryEngine"] = None
_engine_lock = asyncio.Lock()


async def get_engine() -> "N8NQueryEngine":
    """
    FastAPI Depends() 또는 lifespan 에서 호출.
    최초 1회 동기 초기화를 executor 에서 수행하고 이후 캐시 반환.
    """
    global _engine_instance

    if _engine_instance is not None:
        return _engine_instance

    async with _engine_lock:
        if _engine_instance is not None:
            return _engine_instance

        log.info("[Engine] N8NQueryEngine 초기화 시작 (최초 1회)...")
        loop = asyncio.get_event_loop()
        _engine_instance = await loop.run_in_executor(None, _init_engine)
        log.info("[Engine] N8NQueryEngine 초기화 완료")

    return _engine_instance


def _init_engine() -> "N8NQueryEngine":
    """동기 초기화 함수 — executor 스레드에서 실행."""
    from config import settings

    def _resolve_chunks_path() -> Path:
        raw = Path(settings.chunks_jsonl_path)
        candidates = [
            raw,
            Path.cwd() / raw,
            _root / raw,
            _root / "RAG_dataset" / "final_rag_chunks_v2.jsonl",
            _root / "RAG_dataset" / "final_rag_chunks_v2.jsonl",
        ]
        for p in candidates:
            if p.exists():
                return p
        return raw

    try:
        from query_engine import N8NQueryEngine
        chunks_path = _resolve_chunks_path()
        log.info("[Engine] chunks 경로: %s", chunks_path)
        engine = N8NQueryEngine(chunks_path=chunks_path)
        return engine

    except FileNotFoundError as e:
        log.error("[Engine] 청크 파일 없음: %s", e)
        log.warning("[Engine] RAG 없이 더미 엔진으로 폴백합니다.")
        return _DummyEngine()

    except ImportError as e:
        log.error("[Engine] query_engine.py import 실패: %s", e)
        log.warning("[Engine] RAG 없이 더미 엔진으로 폴백합니다.")
        return _DummyEngine()

    except Exception as e:
        log.error("[Engine] 초기화 예외: %s", e, exc_info=True)
        log.warning("[Engine] RAG 없이 더미 엔진으로 폴백합니다.")
        return _DummyEngine()


class _DummyRetriever:
    """청크 파일이 없을 때 빈 결과를 반환하는 더미 리트리버."""
    def retrieve(self, rewritten_query: dict, top_k: int | None = None) -> list:
        return []


class _DummyEngine:
    """
    청크 파일(final_rag_chunks_v2.jsonl)이 없을 때 서버 기동을 유지하기 위한
    폴백 엔진. RAG 없이 LLM 직접 답변 모드로 동작.
    """
    def __init__(self):
        self.retriever = _DummyRetriever()
        self.all_chunks: list = []
        log.warning("[DummyEngine] RAG 비활성 — LLM 직접 추론 모드")

    def query(self, user_input: str, model: str = "", enable_self_correction: bool = True) -> dict:
        return {
            "answer": (
                "RAG 엔진이 초기화되지 않았습니다.\n"
                "final_rag_chunks_v2.jsonl 파일과 Chroma DB가 준비되면 전체 기능이 활성화됩니다.\n\n"
                f"질의: {user_input}"
            ),
            "rewritten_query": {"ko_clean": user_input, "en_expanded": "", "combined": user_input},
            "retrieved_chunks": [],
            "reg_result": {"valid": True, "flagged": [], "suggestions": {}},
            "self_corrected": False,
        }


N8NQueryEngine = _DummyEngine
