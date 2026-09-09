"""
vector_db.py
────────────
Ollama 임베딩 모델을 사용해 ChromaDB에 RAG 청크를 인덱싱하고
의미 기반 검색을 제공합니다.

필수 패키지:
    pip install chromadb
Ollama:
    로컬 혹은 원격 서버에 embedding 모델이 Pull 되어 있어야 합니다.
"""

from __future__ import annotations

import json
import time
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from config import OUTPUT_VECTOR_STATS
from enrichment import sanitize_metadata


# ── Ollama 클라이언트 ─────────────────────────────────────────────────────────

class OllamaClient:
    """Ollama REST API와 통신하는 경량 클라이언트."""

    def __init__(self, base_url: str, model: str) -> None:
        self.base = base_url.rstrip("/")
        self.model = model
        self._dim: int | None = None

    # ── 모델 존재 확인 ────────────────────────────────────────────────────────

    def model_exists(self) -> bool:
        req = urllib.request.Request(f"{self.base}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
        names = [m.get("name", "") for m in payload.get("models", []) if isinstance(m, dict)]
        return self.model in names

    # ── 샘플 생성 (연결 검증용) ───────────────────────────────────────────────

    def generate_sample(self, prompt: str = "한 줄로 답해: 연결 확인") -> str:
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=40) as resp:
            body = json.loads(resp.read().decode("utf-8", errors="ignore"))
        return body.get("response", "").strip()

    # ── 임베딩 ────────────────────────────────────────────────────────────────

    def embed(self, texts: list[str]) -> list[list[float]]:
        """텍스트 목록을 임베딩 벡터로 변환합니다."""
        if not texts:
            return []
        try:
            return self._embed_batch(texts)
        except Exception:
            return [self._embed_single(t) for t in texts]

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload = json.dumps({"model": self.model, "input": texts}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8", errors="ignore"))
        vectors = body.get("embeddings", [])
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise ValueError("Unexpected response from /api/embed")
        if vectors and isinstance(vectors[0], list):
            self._dim = len(vectors[0])
        return vectors

    def _embed_single(self, text: str) -> list[float]:
        """단일 텍스트 임베딩 (배치 실패 시 폴백). 길이 초과 시 점진적 축소."""
        text = (text or "").strip() or "placeholder"
        for limit in (4000, 3000, 2000, 1200):
            payload = json.dumps(
                {"model": self.model, "prompt": text[:limit]}
            ).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base}/api/embeddings",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    body = json.loads(resp.read().decode("utf-8", errors="ignore"))
                vec = body.get("embedding")
                if isinstance(vec, list):
                    return vec
            except Exception:
                continue
        return self._zero_vector()

    def _zero_vector(self) -> list[float]:
        if self._dim is None:
            probe = self._embed_batch(["placeholder"])
            self._dim = len(probe[0])
        return [0.0] * self._dim


# ── JSONL 스트리밍 유틸리티 ───────────────────────────────────────────────────

def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if stripped := line.strip():
                yield json.loads(stripped)


def _count_jsonl(path: Path) -> int:
    return sum(1 for line in path.open("r", encoding="utf-8") if line.strip())


# ── ChromaDB 인덱싱 ───────────────────────────────────────────────────────────

def build_vector_db(
    *,
    jsonl_path: Path,
    base_url: str,
    embedding_model: str,
    chroma_dir: Path,
    collection_name: str,
    batch_size: int,
    reset_collection: bool,
) -> dict[str, Any]:
    """
    JSONL 청크를 Ollama로 임베딩하고 ChromaDB에 저장합니다.

    Args:
        jsonl_path: 입력 JSONL 파일 경로
        base_url: Ollama 서버 주소
        embedding_model: 임베딩 모델 이름
        chroma_dir: ChromaDB 영속 디렉터리
        collection_name: 컬렉션 이름
        batch_size: 한 번에 처리할 청크 수
        reset_collection: True이면 기존 컬렉션을 삭제 후 재생성

    Returns:
        인덱싱 결과 요약 딕셔너리
    """
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError(
            "chromadb is required. Install with: pip install chromadb"
        ) from exc

    if not jsonl_path.exists():
        raise ValueError(f"JSONL not found: {jsonl_path}")

    total = _count_jsonl(jsonl_path)
    if total == 0:
        raise ValueError(f"No rows found in {jsonl_path}")

    client_ollama = OllamaClient(base_url=base_url, model=embedding_model)
    if not client_ollama.model_exists():
        raise ValueError(f"Embedding model not found on Ollama: {embedding_model}")

    chroma_dir.mkdir(parents=True, exist_ok=True)
    client_chroma = chromadb.PersistentClient(path=str(chroma_dir))

    if reset_collection:
        try:
            client_chroma.delete_collection(collection_name)
        except Exception:
            pass

    collection = client_chroma.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    started_at = time.time()
    batch: list[dict[str, Any]] = []
    done = 0
    log_every = batch_size * 50

    def _flush(batch: list[dict[str, Any]]) -> None:
        nonlocal done
        ids = [str(r.get("chunk_global_id") or uuid.uuid4()) for r in batch]
        documents = [str(r.get("page_content", "")) for r in batch]
        embeddings = client_ollama.embed([d[:4000] for d in documents])
        metadatas = [
            sanitize_metadata({k: v for k, v in r.items() if k != "page_content"})
            for r in batch
        ]
        collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
        done += len(batch)
        if done % log_every == 0 or done == total:
            print(f"  indexing progress: {done}/{total}")

    for row in _iter_jsonl(jsonl_path):
        batch.append(row)
        if len(batch) >= batch_size:
            _flush(batch)
            batch = []

    if batch:
        _flush(batch)

    report = {
        "collection": collection_name,
        "persist_dir": str(chroma_dir),
        "embedding_model": embedding_model,
        "total_indexed": total,
        "batch_size": batch_size,
        "duration_sec": round(time.time() - started_at, 2),
        "indexed_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%SZ"),
    }
    OUTPUT_VECTOR_STATS.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


# ── 벡터 검색 ─────────────────────────────────────────────────────────────────

def query_vector_db(
    *,
    chroma_dir: Path,
    collection_name: str,
    query_text: str,
    n_results: int,
    base_url: str,
    embedding_model: str,
) -> dict[str, Any]:
    """
    쿼리 텍스트를 임베딩해 ChromaDB에서 유사 청크를 검색합니다.

    Returns:
        상위 결과 미리보기 딕셔너리
    """
    import chromadb

    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_collection(collection_name)

    client_ollama = OllamaClient(base_url=base_url, model=embedding_model)
    query_vec = client_ollama.embed([query_text[:4000]])[0]

    out = collection.query(query_embeddings=[query_vec], n_results=n_results)

    docs = (out.get("documents") or [[]])[0]
    metas = (out.get("metadatas") or [[]])[0]
    distances = (out.get("distances") or [[]])[0]

    return {
        "query": query_text,
        "n_results": n_results,
        "top_document_preview": str(docs[0])[:500] if docs else "",
        "top_metadata": dict(metas[0]) if metas else {},
        "distance": distances[0] if distances else None,
    }


# ── Ollama 연결 검증 ──────────────────────────────────────────────────────────

def validate_ollama(base_url: str, model: str) -> dict[str, Any]:
    """Ollama 서버 연결과 모델 사용 가능 여부를 검증합니다."""
    client = OllamaClient(base_url=base_url, model=model)
    return {
        "base_url": base_url,
        "model": model,
        "model_exists": client.model_exists(),
        "sample_response": client.generate_sample(),
    }
