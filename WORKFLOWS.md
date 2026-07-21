# Naito 프로젝트 워크플로우 가이드

> 이 문서는 이 저장소에 존재하는 **3개의 독립된 워크플로우**를 실무 관점에서 정리합니다.
> 시스템의 이론적 설계·근거는 [ARCHITECTURE.md](ARCHITECTURE.md)와 [ONTOLOGY.md](ONTOLOGY.md)에 더 깊이 다뤄져 있으므로, 이 문서는 "지금 무엇이 어떤 순서로 실행되는지"에 집중합니다.

---

## 0. 3대 워크플로우 개요

```
┌─────────────────────────────────────────────────────────────────────┐
│  워크플로우 A — 런타임 채팅 요청 처리                                 │
│  (사용자가 메시지를 보낼 때마다 매번 실행)                            │
│  웹앱/Chrome 확장 → Next.js → FastAPI → RAG/LLM → 응답                │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ 검색 대상으로 사용
┌─────────────────────────────────────────────────────────────────────┐
│  워크플로우 B — RAG 데이터셋 구축 파이프라인                          │
│  (지식 소스가 바뀔 때만 수동 실행, 오프라인 배치 작업)                 │
│  RAG Builder/ 원본 문서 → 청킹 → JSONL → 임베딩 → ChromaDB            │
│  → RAG_dataset/ 로 반영                                              │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ 서버 프로세스로 구동
┌─────────────────────────────────────────────────────────────────────┐
│  워크플로우 C — 배포 & 운영                                          │
│  (코드 변경을 실제 서버에 반영할 때 실행)                             │
│  git push → deploy.sh(pm2) 또는 docker-compose(Makefile) → nginx     │
└─────────────────────────────────────────────────────────────────────┘
```

세 워크플로우는 서로 다른 트리거로 실행됩니다 — A는 사용자 요청마다, B는 지식이 갱신될 때, C는 코드가 배포될 때. B의 산출물이 A의 검색 대상이 되고, C가 A/B를 담을 프로세스를 띄운다는 관계입니다.

---

## 1. 워크플로우 A — 런타임 채팅 요청 처리

### 1.1 진입 경로 2가지

| 경로 | 진입점 | 용도 |
|---|---|---|
| 웹앱 직접 접속 | `naito.chat` (Next.js) | 일반 브라우저에서 바로 채팅 |
| Chrome 확장 사이드패널 | `nodi/` 확장 → `sidepanel.html` (iframe으로 `naito.chat` 로드) | n8n 에디터(`n8n.cortie.io`, `localhost:5678`) 작업 중 캔버스 데이터를 함께 첨부해 질문 |

**Chrome 확장 내부 흐름** ([nodi/manifest.json](nodi/manifest.json)):
```
n8n 에디터 페이지
   │  content_scripts: content.js (n8n 캔버스 노드/커넥션 DOM 파싱)
   ▼
background.js (service worker) — 사이드패널 오픈, 메시지 중계
   ▼
sidepanel.html → sidepanel.js / sidepanel-frame.js
   │  iframe으로 naito.chat 로드
   ▼
content-bridge.js (naito.chat 페이지에 주입)
   │  postMessage로 캔버스 데이터(node_data, raw_json)를 iframe 내부로 전달
   ▼
Next.js 웹앱이 일반 채팅과 동일한 /api/chat 경로로 처리
```
즉 확장은 **데이터 수집·전달 레이어**일 뿐이고, 실제 처리 로직은 웹앱/서버가 경로에 상관없이 동일하게 수행합니다.

### 1.2 전체 단계 (요청 1건 기준)

```
[0] 사용자 입력 (텍스트 + 선택적 첨부: node_data / error_log / raw_json)
     │
     ▼
[1] POST /api/chat  (chatbot/app/(chat)/api/chat/route.ts)
     ├─ Zod 스키마 검증
     ├─ NextAuth 세션 검증 (또는 guest 세션 발급)
     ├─ DB: 신규 채팅이면 saveChat(), 이어서 saveMessages(user message)
     ├─ DB: getMessagesByChatId() — 히스토리 로드
     └─ FastAPI로 프록시: POST /api/workspace/stream
     ▼
[2] FastAPI 서비스 레이어 (server/workspace.py → server/main.py)
     ├─ CredentialFilter — API 키/토큰 등 자격증명 마스킹
     ├─ IntentRouter (server/intent_router.py) — LLM 우선 분류 + 규칙 3종 안전망
     │     CURRICULUM / EXPRESSION / WORKFLOW_BUILD /
     │     ERROR_PATCH / REVERSE / GENERAL
     ├─ OntologyEnhancer (server/ontology_enhancer.py) — 쿼리 확장
     │     노드 감지 → 관계 그래프 탐색 → 관련 용어/힌트/오타교정 생성
     ▼
[3] Intent별 서비스로 분기 (server/workflow_services.py, feature_services.py, general_rag.py)
     │  각 서비스가 HybridRetriever(server/query_engine.py)로 RAG 검색
     │  BM25(키워드) + ChromaDB 벡터(BGE-M3) 병렬 검색 → RRF 융합
     ▼
[4] 프롬프트 구성 — SOC 시스템 프롬프트 + RAG 컨텍스트 + 온톨로지 힌트 + 대화 히스토리
     ▼
[5] LLM 스트리밍 생성 — Ollama(자체 호스팅) 또는 OpenAI(사용자 BYOK 키)
     ▼
[6] REG 검증 (server/reg_validator.py) — Levenshtein 기반 파라미터 오타 자동 수정
     ▼
[6.5] SemanticValidator (WORKFLOW_BUILD/ERROR_PATCH만) — 구조/제약/패턴/표현식 검증
     ▼
[7] SSE 응답 스트림 → Next.js가 AI SDK Stream Protocol로 변환 → 브라우저 실시간 렌더링
     ▼
[8] 사후 처리 (route.ts의 finally 블록)
     ├─ DB: saveMessages(assistant message)
     ├─ 첫 메시지였다면 generateTitleFromUserMessage() + updateChatTitleById()
     ├─ writer.write({ type: "finish" }) — 반드시 제목 저장 이후에 호출
     └─ DB: saveRequestLog(intent, latencyMs, ...)
```

### 1.3 Intent 6분류 요약

| Intent | 트리거 | 서비스 | 비고 |
|---|---|---|---|
| CURRICULUM | 학습/로드맵 키워드 | CurriculumService | 대화 히스토리 포함해 레벨 감지 |
| EXPRESSION | node_data 첨부 + 수식 키워드 | ExpressionService | 실제 노드 데이터 기반 `$json` 등 표현식 생성 |
| WORKFLOW_BUILD | 워크플로우 설계/최적화 키워드 | WorkflowBuildService | 실행 가능 JSON 생성, SemanticValidator 적용 |
| ERROR_PATCH | error_log 첨부 + 에러 패턴 | ErrorPatchService | 진단 + 패치 코드 |
| REVERSE | n8n JSON(`"connections"` 키) 감지 | ReverseService | 워크플로우 역분석 리포트 |
| GENERAL | 위 5개 미해당 | GeneralRAGService | 기본 RAG Q&A |

분류 로직 전체와 정규식 패턴은 [ARCHITECTURE.md §6](ARCHITECTURE.md)에 상세 기재.

### 1.4 이 워크플로우가 참조하는 핵심 파일

| 레이어 | 파일 |
|---|---|
| 클라이언트 | `chatbot/hooks/use-active-chat.tsx`, `chatbot/components/chat/*.tsx` |
| 미들웨어 | `chatbot/app/(chat)/api/chat/route.ts` |
| 서비스 오케스트레이션 | `server/workspace.py`, `server/main.py` |
| 의도 분류 | `server/intent_router.py` |
| 온톨로지 | `server/domain_ontology.py`, `server/ontology_enhancer.py` |
| RAG 검색 | `server/query_engine.py`, `server/query_rewrite.py` |
| 사후 검증 | `server/reg_validator.py`, `server/semantic_validator.py` |
| 세션/보안 | `server/session.py`, `server/credential_filter.py` |

> 각 컴포넌트의 설계 근거, 알고리즘(RRF, Levenshtein), 프롬프트 삽입 방식은 [ARCHITECTURE.md](ARCHITECTURE.md) 전체와 [ONTOLOGY.md](ONTOLOGY.md)에 예시 코드와 함께 기술되어 있습니다.

---

## 2. 워크플로우 B — RAG 데이터셋 구축 파이프라인

워크플로우 A가 검색하는 지식 베이스(`RAG_dataset/final_rag_chunks_v2.jsonl`, `RAG_dataset/chroma_db`)는 **자동으로 갱신되지 않습니다.** `RAG Builder/` 도구를 수동 실행해 새로 만들고, 결과물을 `RAG_dataset/`에 반영해야 서버가 사용합니다.

### 2.1 소스 → 산출물 데이터 흐름

```
origin/                                       ┐
  awesome-n8n-templates/                      │  templates.py ──→ final/workflow_templates_text/
  n8n-workflow-templates/                     ┘

GitHub Releases (API)  ──── changelog.py ──→ final/n8n_version_changelog.txt

final/
  docs/*.md                    ┐  (Track A, priority 2)
  *.txt (CORE_STRATEGY 6종)    │  (Track B/C, priority 1)  ─┬─ processors.py ─→ pipeline.py
  workflow_templates_text/     │  (Track D, priority 3)     │        │
  book *.md                    ┘  (Track E, priority 2)    ─┘        ▼
                                                          final_rag_chunks_v2.jsonl
                                                          final_rag_stats_v2.json
                                                                      │
                                                          vector_db.py (선택 단계)
                                                          Ollama 임베딩(bge-m3) + ChromaDB 색인
                                                                      ▼
                                                          final/chroma_db/
                                                                      │
                                              ══════════ 수동 반영 ══════════
                                                                      ▼
                                              RAG_dataset/final_rag_chunks_v2.jsonl
                                              RAG_dataset/chroma_db/
                                                                      │
                                              server/engine.py 가 기동 시 여기서 로드
```

**중요:** `RAG Builder/final/`은 빌더의 작업 디렉터리이고, 서버가 실제로 읽는 곳은 저장소 루트의 `RAG_dataset/`입니다(`server/engine.py`의 `_root / "RAG_dataset" / "final_rag_chunks_v2.jsonl"` 참조). 새 데이터셋을 반영하려면 빌드 후 파일을 `RAG_dataset/`로 옮기고 서버(`naito-api`)를 재시작해야 합니다.

### 2.2 청크 트랙 (Track A~E)

| 트랙 | 소스 | 우선순위 | data_type |
|---|---|---|---|
| A | `final/docs/*.md` | 2 | 문서 |
| B/C | `final/*.txt` — spec, cli_spec, changelog, code_snippet, troubleshooting, api_limits | 1 | `CORE_STRATEGY` 6종 (아래) |
| D | `final/workflow_templates_text/` | 3 | 템플릿(parent/child 쌍) |
| E | `final/book *.md` | 2 | 교재 |

`RAG Builder/config.py`의 `CORE_STRATEGY`:

| 원본 파일 | data_type | 청크 구분자 |
|---|---|---|
| `n8n_properties_spec.txt` | `spec` | `\nNode: `, `\n=====` |
| `n8n_cli_spec.txt` | `cli_spec` | `\n# ` |
| `n8n_version_changelog.txt` | `changelog` | `\n# Version:`, `\n## ` (청크 1500자, 오버랩 250) |
| `n8n_code_node_snippets.txt` | `code_snippet` | `\n# ` |
| `troubleshooting_faq.txt` | `troubleshooting` | `\n# ` |
| `external_api_limits.txt` | `api_limits` | `\n# ` |

기본 청크 크기는 1100자/오버랩 170자(`DEFAULT_CHUNK_SIZE`, `DEFAULT_CHUNK_OVERLAP`), book만 1550/210으로 별도 설정됩니다.

### 2.3 실행 단계 (`RAG Builder/main.py` — 4 Phase)

```bash
cd "RAG Builder"

# Phase 1(선택) — 소스 갱신
python main.py --refresh-templates --refresh-changelog

# Ollama 연결 검증만
python main.py --validate-ollama --ollama-base-url http://100.79.44.109:11434

# Phase 2 — 전처리 (Track A~E) 만 실행 → JSONL 생성
python main.py

# Phase 3 — 벡터 DB까지 빌드 + 검색 테스트
python main.py --build-vector-db --embedding-model bge-m3:latest \
               --test-query "HTTP 노드 사용법" --test-top-k 5

# 전처리는 건너뛰고 기존 JSONL로 벡터 DB만 재빌드(재색인)
python main.py --skip-preprocess --build-vector-db --reset-collection
```

내부적으로 `main.py`는 `_phase_refresh → _phase_preprocess(pipeline.run()) → _phase_vector_db → 완료 리포트` 순으로 실행하며, `template_parent_child_balanced`가 `False`면 템플릿 parent/child 청크 수 불균형 경고를 출력합니다.

### 2.4 파일별 역할

| 파일 | 역할 |
|---|---|
| `config.py` | 경로, 청킹 전략(`CORE_STRATEGY`), 정규식 상수 |
| `pipeline.py` | Track A~E 프로세서를 순서대로 호출해 JSONL/통계 생성 |
| `processors.py` | 트랙별 프로세서(A: docs, B/C: core, D: templates, E: book) |
| `enrichment.py` | 청크 메타데이터 보강(node_name, version, breaking_change) |
| `text_utils.py` | 텍스트 분할·언어 감지·마크다운 정제 |
| `templates.py` | JSON 워크플로우 템플릿 → 텍스트 블록 변환 (parent/child 구조) |
| `changelog.py` | GitHub 릴리즈 API → changelog.txt 생성 |
| `vector_db.py` | Ollama 임베딩 호출 + ChromaDB 색인/검색 |

---

## 3. 워크플로우 C — 배포 & 운영

이 저장소에는 **두 가지 서로 다른 운영 경로**가 존재합니다. `logs/naito-api-*.log`, `logs/naito-web-*.log`와 `ecosystem.config.js`의 존재로 볼 때 **실제 운영은 pm2 방식**이고, `docker-compose.yml` + `Makefile`은 로컬/이식 가능한 셋업용으로 보입니다.

### 3.1 실제 운영 경로 — pm2 + deploy.sh + nginx

```
개발자가 git push (main 브랜치에 반영)
        │
        ▼
서버에서 ./deploy.sh [--full] 실행
        │
        ├─ git diff --name-only HEAD~1 HEAD 로 chatbot/, server/ 변경 여부 감지
        │
        ├─ server/ 변경 시 → pm2 restart naito-api        (재빌드 불필요, uvicorn 리로드)
        │
        └─ chatbot/ 변경 시 → pm2 stop naito-web
                              → pnpm build (NODE_OPTIONS --max-old-space-size=4096)
                              → pm2 start naito-web
        │
        ▼
pm2 list 로 상태 확인
```

`ecosystem.config.js`가 정의하는 두 프로세스:

| 프로세스 | 실행 명령 | 포트 | 비고 |
|---|---|---|---|
| `naito-api` | `.venv/bin/uvicorn main:app --workers 1` | 8000 | `PYTHONPATH=server`, 메모리 2G 초과 시 자동 재시작 |
| `naito-web` | `next dev --webpack -p 3000` | 3000 | `NODE_ENV=development`, `N9N_API=http://127.0.0.1:8000` |

**nginx 리버스 프록시** (`naito.chat.nginx.conf` / `naito.chat.runtime.conf`, 도메인 `naito.chat`):

| 경로 | 대상 | 비고 |
|---|---|---|
| `/naito/api/*` → `/api/*` | `127.0.0.1:8000` | REST |
| `/naito/ws/*` → `/ws/*` | `127.0.0.1:8000` | WebSocket, 타임아웃 3600s |
| `/naito/health` → `/health` | `127.0.0.1:8000` | 헬스체크 |
| `/*` | `127.0.0.1:3000` | Next.js, `proxy_buffering off`로 SSE 스트리밍 보장 |

80 포트는 Let's Encrypt ACME 챌린지 처리 후 443으로 리다이렉트되는 구조이며, `runtime.conf`가 `proxy_send_timeout`/`proxy_buffering off` 등 스트리밍 안정화 옵션이 추가된 최신 버전입니다.

### 3.2 로컬/이식형 경로 — Docker Compose + Makefile

```
cp .env.example .env  →  값 채우기  →  make up
```

`docker-compose.yml`이 정의하는 4개 서비스:

| 서비스 | 이미지/빌드 | 포트 | 의존성 |
|---|---|---|---|
| `postgres` | `postgres:16-alpine` | 5432 | — |
| `n8n` | `n8nio/n8n:latest` | 5678 | — (별도 자동화 도구, RAG 지식 원천이 아닌 실제 n8n 인스턴스) |
| `backend` | `server/Dockerfile` (컨텍스트: 루트, `query_engine.py` 포함) | 8000 | `RAG_dataset/`를 읽기전용 마운트 |
| `chatbot` | `chatbot/Dockerfile` | 3000 | postgres·backend `healthy` 대기 |

`Makefile` 주요 타깃: `make up`(백그라운드 기동), `make build`/`make rebuild`(이미지 빌드), `make migrate`(Drizzle 마이그레이션), `make shell-backend`/`shell-chatbot`/`shell-postgres`(컨테이너 쉘 진입), `make reset`(볼륨까지 전부 삭제 — 확인 프롬프트 있음).

### 3.3 두 경로 비교

| | pm2 (운영) | docker-compose (로컬/이식) |
|---|---|---|
| 목적 | 실서버(naito.chat) 상시 운영 | 로컬 개발/신규 환경 셋업 |
| 재시작 단위 | 변경분만 선택적 재시작 (`deploy.sh`) | 전체 컨테이너 재빌드 |
| Ollama | 외부 서버(`100.79.44.109:11434`) 직접 호출 | `host.docker.internal` 경유 |
| DB | 별도 관리 (compose 밖) | `postgres` 컨테이너 포함 |
| n8n 자체 | 별도 인스턴스(`n8n.cortie.io`) | `n8n` 컨테이너로 함께 기동 |

---

## 4. 워크플로우 간 연결 요약

```
[워크플로우 B로 지식 갱신]
     RAG Builder/ 실행 → RAG_dataset/ 반영
             │
             ▼
[워크플로우 C로 서버 기동/재시작]
     deploy.sh(pm2) 또는 make up(docker) → naito-api, naito-web 프로세스 구동
             │
             ▼
[워크플로우 A가 매 요청마다 실행]
     사용자 메시지 → Intent 분류 → RAG_dataset/ 검색 → LLM → 검증 → 응답
```

- 지식 소스만 바꾼 경우: **B 실행 → C에서 `naito-api`만 재시작**하면 충분합니다(`pm2 restart naito-api`).
- 서버 로직(Intent 라우팅, 서비스, 검증기 등)을 바꾼 경우: **C의 `deploy.sh`가 `server/` 변경을 감지해 자동으로 `naito-api`를 재시작**합니다.
- 프론트엔드(UI, API route)를 바꾼 경우: **C의 `deploy.sh`가 `chatbot/` 변경을 감지해 빌드 후 `naito-web`을 재시작**합니다.
