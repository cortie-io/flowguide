# n8n RAG Builder

n8n 자동화 워크플로 관련 문서·코드·템플릿을 수집해
RAG(Retrieval-Augmented Generation) 파이프라인용 청크로 변환하는 도구입니다.

---

## 파일 구조

```
.
├── main.py          # CLI 진입점 — 단계 오케스트레이션
├── config.py        # 전역 상수, 경로, 청킹 전략
├── pipeline.py      # Track A~E 통합 실행 + JSONL/Stats 출력
├── processors.py    # Track별 프로세서 함수 (A: docs, B/C: core, D: templates, E: book)
├── enrichment.py    # 청크 메타데이터 생성 (node_name, version, breaking_change)
├── text_utils.py    # 텍스트 분할·언어 감지·마크다운 정제
├── templates.py     # JSON 워크플로 → 텍스트 블록 변환
├── changelog.py     # GitHub 릴리즈 수집 → changelog.txt 생성
└── vector_db.py     # Ollama 임베딩 + ChromaDB 인덱싱·검색
```

### 데이터 흐름

```
origin/
  awesome-n8n-templates/     ─┐
  n8n-workflow-templates/    ─┤─ templates.py ──→ final/workflow_templates_text/
                              │
GitHub releases               ─── changelog.py ──→ final/n8n_version_changelog.txt
                              │
final/
  docs/                      ─┐
  *.txt (CORE_STRATEGY)      ─┤─ processors.py ─→ pipeline.py ──→ final_rag_chunks_v2.jsonl
  workflow_templates_text/   ─┤
  book *.md                  ─┘
                                                                          │
                                                               vector_db.py (Ollama + ChromaDB)
```

---

## 사용법

```bash
# 전체 파이프라인 실행 (기본)
python main.py

# 소스 갱신 + 전처리
python main.py --refresh-templates --refresh-changelog

# Ollama 연결 검증
python main.py --validate-ollama --ollama-base-url http://localhost:11434

# 벡터 DB 빌드
python main.py --build-vector-db --embedding-model bge-m3:latest

# 검색 테스트 포함
python main.py --build-vector-db --test-query "HTTP 노드 사용법" --test-top-k 5

# 전처리 건너뛰고 벡터 DB 재빌드
python main.py --skip-preprocess --build-vector-db --reset-collection
```

### 환경 변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://100.79.44.109:11434` | Ollama 서버 주소 |
| `OLLAMA_MODEL` | `gemma4-e4b:latest` | LLM 모델 |
| `OLLAMA_EMBEDDING_MODEL` | `bge-m3:latest` | 임베딩 모델 |

---

## 청크 트랙

| 트랙 | 소스 | 우선순위 |
|---|---|---|
| A | `final/docs/*.md` | 2 |
| B/C | `final/*.txt` (CORE_STRATEGY) | 1 |
| D | `final/workflow_templates_text/` | 3 |
| E | `final/book *.md` | 2 |

---

## 의존성

```bash
pip install langchain-text-splitters   # 선택 (없으면 폴백 분할기 사용)
pip install chromadb                   # --build-vector-db 사용 시 필수
```
