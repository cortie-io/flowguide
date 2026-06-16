"""
main.py
───────
n8n RAG 빌더 통합 진입점 (CLI)

사용 예시:
    # 전체 파이프라인 실행
    python main.py

    # 템플릿 + changelog 갱신 후 전처리
    python main.py --refresh-templates --refresh-changelog

    # 벡터 DB 빌드 및 검색 테스트
    python main.py --build-vector-db --test-query "HTTP 노드 사용법"

    # 전처리 건너뛰고 벡터 DB만 재빌드
    python main.py --skip-preprocess --build-vector-db --reset-collection
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
from pathlib import Path

from config import DEFAULT_CHROMA_DIR, OUTPUT_JSONL, OUTPUT_STATS


# ── CLI 파서 ──────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Unified n8n RAG builder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # ── 소스 갱신 옵션 ────────────────────────────────────────────────────────
    refresh = p.add_argument_group("source refresh")
    refresh.add_argument(
        "--refresh-templates",
        action="store_true",
        help="Rebuild final/workflow_templates_text from origin repositories",
    )
    refresh.add_argument(
        "--refresh-changelog",
        action="store_true",
        help="Refresh final/n8n_version_changelog.txt from GitHub releases",
    )

    # ── Ollama 설정 ───────────────────────────────────────────────────────────
    ollama = p.add_argument_group("ollama")
    ollama.add_argument(
        "--validate-ollama",
        action="store_true",
        help="Validate Ollama endpoint and run a sample generation",
    )
    ollama.add_argument(
        "--ollama-base-url",
        default=os.environ.get("OLLAMA_BASE_URL", "http://100.79.44.109:11434"),
        help="Ollama server base URL (env: OLLAMA_BASE_URL)",
    )
    ollama.add_argument(
        "--ollama-model",
        default=os.environ.get("OLLAMA_MODEL", "gemma4-e4b:latest"),
        help="Ollama LLM model name (env: OLLAMA_MODEL)",
    )

    # ── 벡터 DB 옵션 ──────────────────────────────────────────────────────────
    vdb = p.add_argument_group("vector db")
    vdb.add_argument(
        "--build-vector-db",
        action="store_true",
        help="Build local Chroma vector DB from final_rag_chunks_v2.jsonl",
    )
    vdb.add_argument(
        "--embedding-model",
        default=os.environ.get("OLLAMA_EMBEDDING_MODEL", "bge-m3:latest"),
        help="Ollama embedding model (env: OLLAMA_EMBEDDING_MODEL)",
    )
    vdb.add_argument(
        "--chroma-dir",
        default=str(DEFAULT_CHROMA_DIR),
        help="Chroma persistence directory",
    )
    vdb.add_argument(
        "--chroma-collection",
        default="n8n_rag_v2",
        help="Chroma collection name",
    )
    vdb.add_argument(
        "--embedding-batch-size",
        type=int,
        default=64,
        help="Embedding/indexing batch size",
    )
    vdb.add_argument(
        "--reset-collection",
        action="store_true",
        help="Delete and recreate Chroma collection before indexing",
    )
    vdb.add_argument(
        "--test-query",
        default="",
        metavar="QUERY",
        help="Optional retrieval test query after vector DB build",
    )
    vdb.add_argument(
        "--test-top-k",
        type=int,
        default=5,
        help="Top-k for retrieval test",
    )

    # ── 전처리 옵션 ───────────────────────────────────────────────────────────
    pp = p.add_argument_group("preprocessing")
    pp.add_argument(
        "--skip-preprocess",
        action="store_true",
        help="Skip Track A~E preprocessing and reuse existing JSONL",
    )

    return p


# ── 단계별 실행 함수 ──────────────────────────────────────────────────────────

def _phase_refresh(args: argparse.Namespace) -> None:
    """Phase 1: 소스 파일 갱신 (선택)."""
    if args.refresh_templates:
        from templates import convert_workflow_templates
        result = convert_workflow_templates()
        print(
            f"  templates: total={result.total_json}, "
            f"success={result.success}, failed={result.failed}"
        )

    if args.refresh_changelog:
        from changelog import refresh_changelog
        count = refresh_changelog()
        print(f"  changelog: {count} releases collected")

    if args.validate_ollama:
        from vector_db import validate_ollama
        try:
            info = validate_ollama(args.ollama_base_url, args.ollama_model)
            print("  ollama:", json.dumps(info, ensure_ascii=False))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            print(f"[ERROR] ollama validation failed: {exc}", file=sys.stderr)
            sys.exit(1)


def _phase_preprocess(args: argparse.Namespace) -> dict:
    """Phase 2: Track A~E 전처리."""
    if args.skip_preprocess:
        print("[Phase 2/4] preprocessing skipped (--skip-preprocess)")
        if not OUTPUT_JSONL.exists() or not OUTPUT_STATS.exists():
            print(
                "[ERROR] --skip-preprocess requires existing JSONL/STATS output",
                file=sys.stderr,
            )
            sys.exit(1)
        return json.loads(OUTPUT_STATS.read_text(encoding="utf-8"))

    print("[Phase 2/4] type-aware preprocessing")
    import pipeline
    return pipeline.run()


def _phase_vector_db(args: argparse.Namespace) -> None:
    """Phase 3: 벡터 DB 빌드 + 검색 테스트 (선택)."""
    if not args.build_vector_db:
        return

    from vector_db import build_vector_db, query_vector_db

    try:
        print("[Phase 3/4] building vector DB")
        report = build_vector_db(
            jsonl_path=OUTPUT_JSONL,
            base_url=args.ollama_base_url,
            embedding_model=args.embedding_model,
            chroma_dir=Path(args.chroma_dir),
            collection_name=args.chroma_collection,
            batch_size=max(1, args.embedding_batch_size),
            reset_collection=args.reset_collection,
        )
        print("  vector db:", json.dumps(report, ensure_ascii=False))

        if args.test_query.strip():
            test = query_vector_db(
                chroma_dir=Path(args.chroma_dir),
                collection_name=args.chroma_collection,
                query_text=args.test_query.strip(),
                n_results=max(1, args.test_top_k),
                base_url=args.ollama_base_url,
                embedding_model=args.embedding_model,
            )
            print("  retrieval test:", json.dumps(test, ensure_ascii=False))

    except Exception as exc:
        print(f"[ERROR] vector db build failed: {exc}", file=sys.stderr)
        sys.exit(1)


# ── 진입점 ────────────────────────────────────────────────────────────────────

def main() -> int:
    args = _build_parser().parse_args()

    print("[Phase 1/4] optional source refresh")
    _phase_refresh(args)

    stats = _phase_preprocess(args)
    _phase_vector_db(args)

    print("[Phase 4/4] done")
    print(f"  jsonl : {OUTPUT_JSONL}")
    print(f"  stats : {OUTPUT_STATS}")
    print(json.dumps(stats, ensure_ascii=False, indent=2))

    if not stats.get("template_parent_child_balanced", False):
        print("[WARN] template parent/child count is unbalanced", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
