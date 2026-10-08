"""
app/core/config.py — 전역 환경 설정
app/core/intent_router.py — 유저 인풋 → 5대 기능 분기 라우터
"""

# ============================================================
# config.py
# ============================================================
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # OpenAI 인프라 — 환경변수 OPENAI_API_KEY / LLM_MODEL 등으로 오버라이드 가능
    openai_api_key:     str  = ""
    embed_model:        str  = "text-embedding-3-small"
    reranker_model:     str  = "bge-reranker-v2-m3"
    llm_model:          str  = "gpt-4o-mini"

    # Gemini 인프라(§4.4 H4 교차모델 검증용) — 환경변수 GEMINI_API_KEY로 오버라이드
    gemini_api_key:     str  = ""

    # Ollama 인프라 (레거시, 더 이상 기본 경로로 사용되지 않음)
    ollama_base_url:    str  = "http://localhost:11434"

    # RAG 인프라
    chunks_jsonl_path:  Path = Path("final_rag_chunks_v2.jsonl")
    chroma_persist_dir: Path = Path(".chroma_db_v2")
    chroma_collection:  str  = "n8n_rag_v2"

    # 검색 파라미터
    vector_top_k:  int   = 20
    bm25_top_k:    int   = 20
    rrf_k:         int   = 60
    rerank_top_n:  int   = 8
    weight_vector: float = 0.6
    weight_bm25:   float = 0.4

    # 세션
    snapshot_ttl_seconds: int = 3600   # 스냅샷 유효 시간

    class Config:
        env_file = ".env"


settings = Settings()
