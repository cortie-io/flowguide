from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

try:
    from rank_bm25 import BM25Okapi
except Exception:
    BM25Okapi = None

try:
    import httpx as _httpx
except Exception:
    _httpx = None  # type: ignore[assignment]

try:
    import chromadb as _chromadb
except Exception:
    _chromadb = None  # type: ignore[assignment]

log = logging.getLogger("naito.query_engine")

# ── Spec 섹션 파싱 ──────────────────────────────────────────────────────────────

_SECTION_SPLIT_RE = re.compile(
    r"={5,}\s*\n#\s*NODE DIRECTORY:\s*([^\n]+)\n#\s*FILE:\s*([^\n]+)\n={5,}",
)
_PROP_BLOCK_RE = re.compile(
    r"- displayName:\s*(.+?)\n- name:\s*(.+?)\n- type:\s*(.+?)(?:\n- default:\s*(.*?))?(?:\n- description:\s*([\s\S]*?))?(?=\n- displayName:|\Z)",
    re.DOTALL,
)


def _parse_spec_sections(raw_text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    parts = _SECTION_SPLIT_RE.split(raw_text)

    if len(parts) <= 1:
        return []

    i = 1
    while i + 2 <= len(parts):
        node_dir = parts[i].strip()
        file_name = parts[i + 1].strip()
        body = parts[i + 2].strip() if i + 2 < len(parts) else ""
        i += 3

        props = _extract_properties(body)
        sections.append({
            "node_name": node_dir,
            "file_name": file_name,
            "body": body,
            "properties": props,
        })

    return sections


def _extract_properties(body: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for m in _PROP_BLOCK_RE.finditer(body):
        results.append({
            "displayName": m.group(1).strip(),
            "name":        m.group(2).strip(),
            "type":        m.group(3).strip(),
            "default":     (m.group(4) or "").strip().strip("'"),
            "description": re.sub(r"\s+", " ", (m.group(5) or "").strip()),
        })
    return results


class HybridRetriever:
    def __init__(
        self,
        chunks_path: str | Path,
        chroma_db_path: str | Path | None = None,
        ollama_base_url: str = "http://localhost:11434",
        embed_model: str = "bge-m3:latest",
    ):
        self.chunks_path = Path(chunks_path)
        self.chunks = self._load_chunks(self.chunks_path)

        # base_id → 확장된 in-memory 청크 인덱스 목록 (spec 분리용)
        self._base_id_to_indices: dict[str, list[int]] = {}
        for i, c in enumerate(self.chunks):
            cid = str(c.get("chunk_global_id", ""))
            base_id = cid.split("::")[0]
            self._base_id_to_indices.setdefault(base_id, []).append(i)

        # BM25 전체 인덱스
        self._valid_idx: list[int] = []
        self._tokenized: list[list[str]] = []
        for i, c in enumerate(self.chunks):
            toks = self._tokenize(self._chunk_text(c))
            if toks:
                self._valid_idx.append(i)
                self._tokenized.append(toks)
        self._bm25 = BM25Okapi(self._tokenized) if BM25Okapi and self._tokenized else None

        # BM25 spec 전용 인덱스
        self._spec_idx: list[int] = []
        self._spec_tokenized: list[list[str]] = []
        for i, c in enumerate(self.chunks):
            if c.get("data_type") in ("spec", "official_docs", "book"):
                toks = self._tokenize(self._chunk_text(c))
                if toks:
                    self._spec_idx.append(i)
                    self._spec_tokenized.append(toks)
        self._bm25_spec = (
            BM25Okapi(self._spec_tokenized)
            if BM25Okapi and self._spec_tokenized else None
        )

        # ChromaDB 벡터 검색
        self._collection = None
        self._ollama_base_url = ollama_base_url.rstrip("/")
        self._embed_model = embed_model
        if chroma_db_path and _chromadb:
            try:
                client = _chromadb.PersistentClient(path=str(chroma_db_path))
                self._collection = client.get_collection("n8n_rag_v2")
                log.info(
                    "[HybridRetriever] ChromaDB 로드 완료: %d개 벡터",
                    self._collection.count(),
                )
            except Exception as e:
                log.warning("[HybridRetriever] ChromaDB 로드 실패 (BM25만 사용): %s", e)

    # ── 청크 로드 + 정규화 ──────────────────────────────────────────────────────

    def _load_chunks(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(f"Chunks JSONL not found: {path}")
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    rows.extend(self._expand_chunk(obj))
        return rows

    def _expand_chunk(self, chunk: dict[str, Any]) -> list[dict[str, Any]]:
        raw_text = str(chunk.get("page_content") or chunk.get("text") or "")
        dtype = str(chunk.get("data_type") or "")

        if dtype != "spec":
            return [self._normalize_chunk(chunk)]

        sections = _parse_spec_sections(raw_text)
        if not sections:
            return [self._normalize_chunk(chunk)]

        result: list[dict[str, Any]] = []
        base_id = str(chunk.get("chunk_global_id", "chunk"))
        for idx, sec in enumerate(sections):
            clone = dict(chunk)
            clone["chunk_global_id"] = f"{base_id}::{idx}"
            clone["node_name"]  = sec["node_name"]
            clone["title"]      = sec["node_name"]
            clone["file_name"]  = sec["file_name"]
            clone["properties"] = sec["properties"]
            clone["page_content"] = sec["body"]
            result.append(self._normalize_chunk(clone))

        return result

    def _normalize_chunk(self, chunk: dict[str, Any]) -> dict[str, Any]:
        clone = dict(chunk)
        page_content = str(
            clone.get("page_content") or clone.get("text") or
            clone.get("chunk") or clone.get("content") or
            clone.get("summary") or ""
        )
        node_name  = str(clone.get("node_name") or "")
        file_name  = str(clone.get("file_name") or clone.get("source_file") or "")
        source     = str(clone.get("source_path") or clone.get("source_file") or "")
        dtype      = str(clone.get("data_type") or "")

        if not node_name or node_name.lower() == "generic":
            m = re.search(r"#\s*NODE DIRECTORY:\s*([^\n]+)", page_content)
            if m:
                node_name = m.group(1).strip()
                clone["node_name"] = node_name

        title = (
            clone.get("title")
            or (node_name if node_name and node_name.lower() != "generic" else "")
            or file_name
            or source
            or "generic"
        )
        clone["title"]      = title
        clone["source"]     = source
        clone.setdefault("properties", [])

        props: list[dict] = clone.get("properties") or []
        prop_names = " ".join(p.get("name", "") for p in props[:20]) if props else ""
        prop_display = " ".join(p.get("displayName", "") for p in props[:20]) if props else ""

        header_parts = [
            f"Node: {node_name}"         if node_name and node_name.lower() != "generic" else "",
            f"File: {file_name}"          if file_name else "",
            f"Source: {source}"           if source else "",
            f"Type: {dtype}"              if dtype else "",
            f"Properties: {prop_names}"   if prop_names else "",
            f"Labels: {prop_display}"     if prop_display else "",
        ]
        header = "\n".join(p for p in header_parts if p)
        clone["text"] = f"{header}\n\n{page_content}".strip() if header else page_content
        return clone

    # ── 검색 ────────────────────────────────────────────────────────────────────

    def _chunk_text(self, chunk: dict[str, Any]) -> str:
        return str(
            chunk.get("text") or chunk.get("page_content") or
            chunk.get("chunk") or chunk.get("content") or
            chunk.get("summary") or ""
        )

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-z0-9_.-]+|[가-힣]+", text.lower())

    def _query_text(self, rewritten_query: dict[str, Any] | str) -> str:
        if isinstance(rewritten_query, dict):
            return str(
                rewritten_query.get("combined") or
                rewritten_query.get("ko_clean") or
                rewritten_query.get("en_expanded") or ""
            )
        return str(rewritten_query)

    def _rank_key(
        self,
        base_score: float,
        chunk: dict[str, Any],
        query_tokens: list[str],
    ) -> tuple[float, int, int, int]:
        haystack = " ".join([
            str(chunk.get("title") or ""),
            str(chunk.get("node_name") or ""),
            str(chunk.get("source") or ""),
            str(chunk.get("text") or ""),
        ]).lower()
        exact        = sum(1 for t in query_tokens if len(t) >= 2 and t in haystack)
        node_nm      = str(chunk.get("node_name") or "").lower()
        node_hit     = sum(1 for t in query_tokens if t in node_nm) * 3
        official_b   = 1 if chunk.get("data_type") == "official_docs" else 0
        spec_b       = 1 if chunk.get("data_type") == "spec" else 0
        return (base_score, exact + node_hit, official_b, spec_b)

    def _bm25_search(self, rewritten_query: dict[str, Any] | str, top_k: int = 20) -> list[int]:
        q = self._tokenize(self._query_text(rewritten_query))
        if not q or not self._valid_idx:
            return []

        if self._bm25 is not None:
            scores = self._bm25.get_scores(q)
            ranked_local = sorted(
                range(len(scores)),
                key=lambda i: self._rank_key(
                    float(scores[i]), self.chunks[self._valid_idx[i]], q
                ),
                reverse=True,
            )
            return [self._valid_idx[i] for i in ranked_local[:top_k]]

        qset = set(q)
        scored: list[tuple] = []
        for li, toks in enumerate(self._tokenized):
            sc = len(qset.intersection(toks))
            if sc > 0:
                scored.append((
                    self._rank_key(float(sc), self.chunks[self._valid_idx[li]], q),
                    self._valid_idx[li],
                ))
        scored.sort(reverse=True)
        return [i for _, i in scored[:top_k]]

    def _bm25_search_spec(self, rewritten_query: dict[str, Any] | str, top_k: int = 20) -> list[int]:
        q = self._tokenize(self._query_text(rewritten_query))
        if not q or not self._spec_idx:
            return []
        if self._bm25_spec is not None:
            scores = self._bm25_spec.get_scores(q)
            ranked = sorted(
                range(len(scores)),
                key=lambda i: self._rank_key(float(scores[i]), self.chunks[self._spec_idx[i]], q),
                reverse=True,
            )
            return [self._spec_idx[i] for i in ranked[:top_k]]
        qset = set(q)
        scored = []
        for li, toks in enumerate(self._spec_tokenized):
            sc = len(qset.intersection(toks))
            if sc > 0:
                scored.append((
                    self._rank_key(float(sc), self.chunks[self._spec_idx[li]], q),
                    self._spec_idx[li],
                ))
        scored.sort(reverse=True)
        return [i for _, i in scored[:top_k]]

    # ── 벡터 검색 ───────────────────────────────────────────────────────────────

    def _get_embedding(self, text: str) -> list[float] | None:
        if _httpx is None:
            return None
        try:
            resp = _httpx.post(
                f"{self._ollama_base_url}/api/embed",
                json={"model": self._embed_model, "input": [text]},
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.json()["embeddings"][0]
        except Exception as e:
            log.warning("[HybridRetriever] 임베딩 실패: %s", e)
            return None

    def _vector_search(self, query_text: str, top_k: int = 20) -> list[int]:
        """ChromaDB 벡터 검색 → in-memory chunk 인덱스 목록 반환."""
        if self._collection is None:
            return []

        embedding = self._get_embedding(query_text)
        if embedding is None:
            return []

        try:
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k, self._collection.count()),
                include=["metadatas", "distances"],
            )
        except Exception as e:
            log.warning("[HybridRetriever] ChromaDB 쿼리 실패: %s", e)
            return []

        indices: list[int] = []
        seen: set[int] = set()
        metadatas = results.get("metadatas", [[]])[0]
        for meta in metadatas:
            base_id = str(meta.get("chunk_global_id", ""))
            for idx in self._base_id_to_indices.get(base_id, []):
                if idx not in seen:
                    seen.add(idx)
                    indices.append(idx)
        return indices

    # ── RRF 결합 ────────────────────────────────────────────────────────────────

    @staticmethod
    def _rrf_merge(
        lists: list[list[int]],
        k: int = 60,
        top_k: int = 20,
    ) -> list[int]:
        scores: dict[int, float] = {}
        for ranked in lists:
            for rank, idx in enumerate(ranked):
                scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
        return sorted(scores, key=lambda x: scores[x], reverse=True)[:top_k]

    # ── 공개 API ────────────────────────────────────────────────────────────────

    def _make_result(self, c: dict[str, Any]) -> dict[str, Any]:
        return {
            "doc_id":     c.get("doc_id") or c.get("chunk_global_id"),
            "title":      c.get("title") or c.get("node_name") or c.get("source_file") or "",
            "node_name":  c.get("node_name") or "",
            "source":     c.get("source") or c.get("source_path") or c.get("source_file") or "",
            "data_type":  c.get("data_type") or c.get("type") or "official_docs",
            "text":       self._chunk_text(c),
            "properties": c.get("properties") or [],
            "metadata":   c.get("metadata") or {},
        }

    def retrieve(self, rewritten_query: dict[str, Any] | str, top_k: int = 20) -> list[dict[str, Any]]:
        query_text = self._query_text(rewritten_query)
        bm25_idx   = self._bm25_search(rewritten_query, top_k=top_k)
        vector_idx = self._vector_search(query_text, top_k=top_k)

        if vector_idx:
            merged = self._rrf_merge([bm25_idx, vector_idx], top_k=top_k)
            log.debug("[retrieve] BM25=%d, vector=%d → merged=%d", len(bm25_idx), len(vector_idx), len(merged))
        else:
            merged = bm25_idx[:top_k]

        return [self._make_result(self.chunks[i]) for i in merged]

    def retrieve_spec(self, rewritten_query: dict[str, Any] | str, top_k: int = 10) -> list[dict[str, Any]]:
        query_text = self._query_text(rewritten_query)
        bm25_idx   = self._bm25_search_spec(rewritten_query, top_k=top_k)
        vector_idx = self._vector_search(query_text, top_k=top_k)

        # spec 검색에서는 vector 결과를 spec/official_docs 타입으로만 필터
        if vector_idx:
            spec_types = {"spec", "official_docs", "book"}
            vector_idx = [i for i in vector_idx if self.chunks[i].get("data_type") in spec_types]
            merged = self._rrf_merge([bm25_idx, vector_idx], top_k=top_k)
        else:
            merged = bm25_idx[:top_k]

        return [self._make_result(self.chunks[i]) for i in merged]


class N8NQueryEngine:
    def __init__(
        self,
        chunks_path: str | Path,
        chroma_db_path: str | Path | None = None,
        ollama_base_url: str = "http://localhost:11434",
        embed_model: str = "bge-m3:latest",
    ):
        self.retriever = HybridRetriever(
            chunks_path=chunks_path,
            chroma_db_path=chroma_db_path,
            ollama_base_url=ollama_base_url,
            embed_model=embed_model,
        )
        self.all_chunks = self.retriever.chunks

    def query(self, user_input: str, model: str = "", enable_self_correction: bool = True) -> dict[str, Any]:
        return {
            "answer": "",
            "rewritten_query": {"combined": user_input, "ko_clean": user_input, "en_expanded": ""},
            "retrieved_chunks": self.retriever.retrieve({"combined": user_input}, top_k=8),
            "reg_result": {"valid": True, "flagged": [], "suggestions": {}},
            "self_corrected": False,
        }
