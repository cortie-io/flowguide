# FlowGuide AI (Naito)

**XAI(설명 가능한 AI) 기반 n8n 워크플로우 학습·자동화 지원 시스템**

n8n 자동화 워크플로우를 만들다 막히는 사람에게 "왜 이렇게 만들어야 하는지"까지 설명하는 AI 튜터입니다. 온톨로지(453개 노드 · 5계층 지식 그래프) + 하이브리드 RAG(BM25 + 벡터 검색) + REG(자동 오류 교정) + 4단계 시맨틱 검증을 파이프라인으로 엮어, 그냥 LLM에 물어봤을 때와 달리 **실제로 n8n에 반영되는 워크플로우**를 만들어냅니다.

- 서비스: [naito.chat](https://naito.chat)
- 팀: FlowGuide AI · 경복대학교 소프트웨어융합학과
- 대회: 2026 AI 해커톤대회 출품작

---

## 목차

1. [핵심 기능](#핵심-기능)
2. [왜 ChatGPT가 아니라 FlowGuide AI인가](#왜-chatgpt가-아니라-flowguide-ai인가)
3. [시스템 아키텍처](#시스템-아키텍처)
4. [온톨로지 — 453개 노드, 5계층 지식 그래프](#온톨로지--453개-노드-5계층-지식-그래프)
5. [성능 지표](#성능-지표)
6. [프로젝트 구조](#프로젝트-구조)
7. [시작하기 (설치 및 실행)](#시작하기-설치-및-실행)
8. [Chrome 확장 프로그램 — 설치부터 사용법까지](#chrome-확장-프로그램--설치부터-사용법까지)
9. [기술 스택](#기술-스택)
10. [문서 모음](#문서-모음)

---

## 핵심 기능

| 기능 | 설명 |
|---|---|
| **4D XAI 설명** | 워크플로우의 각 노드를 Why(왜 선택됐나) · How(어떻게 처리되나) · What-if(바꾸면 어떻게 되나) · Alternative(다른 방법은 없나) 4가지 관점에서 설명 |
| **자연어 → 워크플로우 생성** | 채팅으로 원하는 자동화를 설명하면 n8n 워크플로우 JSON을 생성하고, Chrome 확장을 통해 실제 n8n 인스턴스에 바로 반영 |
| **현재 워크플로우 분석** | n8n 편집 화면에서 지금 만들고 있는 워크플로우를 그대로 읽어와 개선점·오류를 진단 |
| **에러 진단** | 실행 에러 로그를 붙여넣으면 원인과 수정 방법을 근거와 함께 제시 |
| **RAG 근거 제시** | 모든 답변에 실제로 참고한 공식 문서·스펙 청크를 "근거"로 함께 제시(환각 여부를 사용자가 직접 검증 가능) |
| **REG 자동 교정** | LLM이 만든 워크플로우 JSON의 오타·잘못된 속성명을 Levenshtein 편집거리 기반으로 실제 n8n 스키마에 맞게 자동 교정 |
| **4단계 시맨틱 검증** | 구조 → 속성 제약 → 관계 패턴 → 표현식 의미, 4단계를 통과한 결과만 응답으로 내보내 환각을 차단 |
| **Chrome 확장 프로그램** | n8n 편집 화면 옆에 사이드 패널로 AI 튜터를 띄워, 캔버스를 읽고 워크플로우를 직접 생성 |

---

## 왜 ChatGPT가 아니라 FlowGuide AI인가

같은 모델(GPT-4o mini)·같은 15개 워크플로우 시나리오로, RAG·온톨로지·REG·검증을 모두 뺀 "순수 LLM"과 FlowGuide AI 전체 파이프라인을 정면 비교했습니다.

| 지표 | 일반 LLM만 사용 | FlowGuide AI |
|---|---|---|
| 그럴듯한 워크플로우 JSON 생성 | 100% | 100% |
| n8n에 표면적으로 주입 성공 | 86.7% | **100%** |
| **실제로 실행 가능한 워크플로우** | **66.7%** | **100%** |
| 존재하지 않는 노드를 지어낸 시나리오 | 26.7% (4/15) | **0%** |
| 스스로 고친 오류 건수 | 0건 (교정 기능 없음) | 평균 2.33건/워크플로우 |

> ChatGPT는 "워크플로우처럼 보이는 것"을 만들고, FlowGuide AI는 "실제로 n8n에서 동작하는 워크플로우"를 만듭니다.

두 시스템 모두 JSON 자체는 잘 만들어냅니다. 차이는 그 JSON이 실제로 n8n에서 살아남는지에서 드러납니다 — 일반 LLM은 존재하지 않는 노드 타입(`rssRead`, `telegramSendMessage`, `imap`, `inventoryGetAll` 등)을 자신 있게 지어내고, n8n은 생성 시점엔 이를 받아주더라도 실행 시점에 "노드를 찾을 수 없음" 오류로 깨집니다. FlowGuide AI는 453개 노드 온톨로지와의 대조 + 4단계 검증으로 이런 사례를 배포 전에 차단합니다.

자세한 비교 방법론과 실패 사례 원문은 [`docs/reports/[FlowGuide AI]_왜_ChatGPT_대신_FlowGuideAI인가.docx`](docs/reports/) 참고.

---

## 시스템 아키텍처

```
사용자 질문 (자연어 · 현재 워크플로우 · 캡처 이미지)
        │
        ▼
① 의도 분류 (Intent Classification)
   규칙 기반 정규식 3종 + AI 하이브리드 판단 (GPT-4o mini, temperature=0)
   → GENERAL · CURRICULUM · EXPRESSION · WORKFLOW_BUILD · ERROR_PATCH · REVERSE 6종 분기
        │
        ▼
② 하이브리드 RAG 검색
   BM25(키워드) + text-embedding-3-small(의미 벡터) → RRF(Reciprocal Rank Fusion) 결합
   지식베이스: 14,543개 청크 (ChromaDB, 1536차원)
        │
        ▼
③ 온톨로지 컨텍스트 주입
   453개 노드 5계층 그래프에서 관계 힌트(ANTI-PATTERN/RECOMMEND/BEST-PRACTICE) + 오타 교정 후보를 프롬프트에 삽입
        │
        ▼
④ LLM 생성 (GPT-4o mini, 스트리밍)
        │
        ▼
⑤ REG 자동 교정
   생성된 워크플로우 JSON의 속성명을 실제 n8n 스키마와 대조해 Levenshtein 거리 기반으로 자동 수정
        │
        ▼
⑥ 4단계 시맨틱 검증
   구조 검증 → 속성 제약 검증 → 관계 패턴 검증 → 표현식 의미 검증
   (통과하지 못하면 응답으로 내보내지 않음)
        │
        ▼
답변 (RAG 근거 + 온톨로지 컨텍스트와 함께 스트리밍)
   → (워크플로우 생성 시) Chrome 확장을 통해 n8n REST API로 실제 반영
```

**서비스 구성**

| 서비스 | 역할 | 포트 |
|---|---|---|
| `chatbot` (Next.js) | 웹 채팅 UI, 인증, 세션 관리 | 3010 → 3000 |
| `backend` (FastAPI) | 의도 분류·RAG·온톨로지·REG·검증 등 핵심 추론 엔진 | 8000 |
| `postgres` | 챗봇 인증/세션 DB | 5433 → 5432 |
| `n8n` | 실제 워크플로우가 반영되는 자동화 엔진 | 5678 |

기술적 세부사항(설계 철학, XAI 이론적 배경, 코드 레벨 분석)은 [`docs/technical/ARCHITECTURE.md`](docs/technical/ARCHITECTURE.md), 처리 로직 요약은 [`docs/technical/OVERVIEW.md`](docs/technical/OVERVIEW.md)에 정리돼 있습니다.

---

## 온톨로지 — 453개 노드, 5계층 지식 그래프

n8n 노드 453개에 대해 다섯 가지 질문에 답하는 지식 데이터베이스입니다(`server/domain_ontology.py`).

| 계층 | 이름 | 답하는 질문 |
|---|---|---|
| ① | **NodeTaxonomy** (노드 분류) | 이 노드는 어떤 종류인가? — 트리거·처리·출력·유틸리티 |
| ② | **RelationGraph** (관계 그래프) | 다른 노드와 어떻게 연결되는가? — 7가지 관계 타입 |
| ③ | **PropertyConstraints** (속성 제약) | 이 설정, 같이 써도 되는가? — 30개 제약 규칙 |
| ④ | **WorkflowPatterns** (모범 패턴) | 이렇게 조합하면 잘 동작하는가? — 검증된 패턴 11개 |
| ⑤ | **LearningGraph** (학습 순서) | 이걸 배우기 전에 뭘 알아야 하는가? — 17노드 선행 의존성 DAG |

자세한 스펙은 [`docs/technical/ONTOLOGY.md`](docs/technical/ONTOLOGY.md) 참고.

---

## 성능 지표

naito.chat 백엔드에 실제로 직접 요청해 측정했습니다(각 항목 3회씩 반복, Wilson 95% 신뢰구간 표기).

| 지표 | 결과 | 비고 |
|---|---|---|
| 의도 분류 정확도 | **97.9%** (95% CI 94.1–99.3%) | 144건 시행 (48개 질문 × 3회), 3회 반복 모두 동일 예측 100% |
| RAG 검색 적중률 | **91.7%** (95% CI 83.0–96.1%) | 72건 시행 (24개 질문 × 3회), 24개 중 22개는 3회 모두 적중 |
| 평균 응답 시간 | **7.35초** | 중앙값 7.03초 · 표준편차 2.92초, 첫 토큰까지는 평균 0.6초 |
| 워크플로우 생성 → n8n 실제 반영 성공률 | **100%** (95% CI 84.5–100%) | 21/21건, REG 자동 수정 평균 2.33건/건 |

측정 방법론과 통계 처리 상세는 [`docs/reports/[FlowGuide AI]_성능테스트_보고서.docx`](docs/reports/)에 정리돼 있습니다.

---

## 프로젝트 구조

```
flowguide/
├── chatbot/              # Next.js 프론트엔드 (웹 채팅 UI, 인증, DB)
├── server/                # FastAPI 백엔드 (의도 분류 · RAG · REG · 검증 등 핵심 엔진)
│   ├── domain_ontology.py    # 453개 노드 5계층 온톨로지
│   ├── engine.py              # N8NQueryEngine 초기화 및 RAG 경로 해석
│   ├── intent_router.py       # 6대 의도 분류
│   ├── reg_validator.py       # REG 자동 교정
│   ├── semantic_validator.py  # 4단계 시맨틱 검증
│   ├── general_rag.py         # 일반 질의응답 RAG 서비스
│   ├── workflow_services.py   # 워크플로우 생성 서비스
│   └── ...
├── query_engine.py       # 하이브리드 RAG 검색 엔진 (BM25 + 벡터 + RRF)
├── Chrome_extention/      # Chrome 확장 프로그램 (n8n 캔버스 연동, 사이드 패널)
├── RAG_dataset/           # RAG 지식베이스 원본 + 청크 + 벡터DB
├── RAG_builder/           # RAG_dataset을 만드는 데이터 파이프라인 도구
├── docs/
│   ├── technical/         # 아키텍처 · 온톨로지 · 처리 로직 · 워크플로우 상세 문서
│   ├── reports/           # 해커톤 제출 보고서 · 발표자료 · 성능/비교 보고서
│   │   └── templates/     # 대회 양식 및 참고 자료
│   ├── screenshots/        # 실제 서비스 화면 캡처
│   └── videos/             # 데모 영상
├── docker-compose.yml     # 전체 서비스 오케스트레이션
└── Makefile               # make up / make setup 등 운영 명령
```

---

## 시작하기 (설치 및 실행)

### 요구사항

- Docker & Docker Compose
- OpenAI API 키 (LLM 생성 + 임베딩)

### 1. 환경변수 설정

```bash
cp .env.example .env
```

`.env`에서 최소한 아래 값을 채워야 합니다.

| 변수 | 설명 |
|---|---|
| `OPENAI_API_KEY` | OpenAI API 키 (`sk-proj-...`) |
| `AUTH_SECRET` | `openssl rand -base64 32`로 생성 |
| `POSTGRES_PASSWORD` | 원하는 비밀번호로 변경 권장 |

`LLM_MODEL`(기본 `gpt-4o-mini`), `EMBED_MODEL`(기본 `text-embedding-3-small`)은 기본값 그대로 사용해도 됩니다.

### 2. 서비스 실행

```bash
make setup   # 최초 1회: .env 생성 안내 + 이미지 빌드 + 실행
make up      # 이후: 백그라운드로 전체 서비스 시작
```

또는 `make` 없이 직접:

```bash
docker compose build
docker compose up -d
```

### 3. 접속 확인

| 서비스 | 주소 |
|---|---|
| 웹 채팅 (Next.js) | http://localhost:3010 |
| FastAPI 백엔드 | http://localhost:8000 |
| n8n | http://localhost:5678 |

### 자주 쓰는 명령

```bash
make logs             # 전체 서비스 실시간 로그
make ps                # 서비스 상태 확인
make shell-backend     # FastAPI 컨테이너 쉘 접속
make down              # 전체 서비스 종료
```

RAG 지식베이스를 새로 빌드해야 한다면 [`RAG_builder/README.md`](RAG_builder/README.md)와 [`docs/technical/WORKFLOWS.md`](docs/technical/WORKFLOWS.md)를 참고하세요.

---

## Chrome 확장 프로그램 — 설치부터 사용법까지

`Chrome_extention/` 폴더의 확장 프로그램은 n8n 편집 화면 옆에 AI 튜터(FlowGuide AI)를 사이드 패널로 띄워, 지금 만들고 있는 워크플로우를 바로 분석하거나 채팅으로 새 워크플로우를 만들어 n8n에 직접 생성할 수 있게 해줍니다.

### 1. 설치 (개발자 모드)

아직 Chrome 웹 스토어에 배포되지 않았으므로, 압축해제된 확장 프로그램으로 직접 로드해야 합니다.

1. Chrome 주소창에 `chrome://extensions` 입력 후 이동
2. 우측 상단의 **개발자 모드** 토글을 켬
3. **압축해제된 확장 프로그램을 로드합니다** 클릭
4. 이 저장소의 `Chrome_extention/` 폴더를 선택
5. 목록에 확장 프로그램이 추가되고, 툴바에 아이콘이 표시되면 설치 완료

### 2. 시작하기

1. 툴바의 아이콘을 클릭하면 브라우저 오른쪽에 **사이드 패널**이 열립니다. (사이드 패널 안에는 naito.chat 웹 서비스가 그대로 표시됩니다.)
   - `localhost:5678`, `127.0.0.1:5678`, `n8n.cortie.io`, n8n Cloud(`*.n8n.cloud`) 중 하나로 이동하면 사이드 패널이 자동으로 열립니다.
2. 처음 사용한다면 사이드 패널 안에서 회원가입 → 로그인
3. 이후에는 로그인 상태가 유지되므로, 아이콘을 클릭하기만 하면 바로 대화창이 뜹니다.

### 3. n8n 인스턴스 연결하기 (워크플로우를 직접 생성하려면 필수)

채팅으로 만든 워크플로우를 버튼 한 번으로 n8n에 실제로 생성하려면, 먼저 내 n8n 인스턴스를 연결해야 합니다.

1. 사이드 패널 우측 상단의 **n8n 연결** 버튼 클릭
2. **n8n URL** 입력 (예: `http://localhost:5678`)
3. **API Key** 입력 — n8n 화면에서 **Settings → API → Create API Key**로 발급 (선택 사항이지만, 워크플로우 자동 생성 기능을 쓰려면 필요)
4. **저장** 클릭

연결되면 버튼 텍스트가 접속 중인 n8n 주소로 바뀌고, 앞에 초록색 점이 표시됩니다.

### 4. 지금 열려 있는 워크플로우 분석하기

1. Chrome에서 분석하고 싶은 n8n 워크플로우 편집 화면을 엽니다.
   - 자동으로 캔버스를 읽어오는 기능은 `localhost:5678`, `127.0.0.1:5678`, `n8n.cortie.io`, n8n Cloud(`*.n8n.cloud`)에서만 동작합니다. 그 외 도메인으로 직접 호스팅한(온프레미스) n8n은 현재 자동 인식되지 않습니다.
2. 사이드 패널에서 자연스럽게 질문만 하면 됩니다. 예:
   - "지금 열려있는 워크플로우 분석해줘"
   - "이 워크플로우에서 개선할 점 있어?"
3. 별도 버튼을 누를 필요 없이, 질문 의도를 자동으로 판단해서 현재 캔버스의 JSON을 읽어온 뒤 답변합니다.

### 5. 채팅으로 워크플로우 만들어서 n8n에 바로 생성하기

1. 사이드 패널에서 원하는 자동화를 자연어로 설명합니다. 예:
   - "새 주문이 들어오면 구글 시트에 기록하는 워크플로우 만들어줘"
2. AI가 워크플로우 JSON을 생성하면 답변 아래에 **"n8n에 바로 생성"** 카드가 나타납니다.
3. (3번 단계에서 n8n을 연결해두었다면) 버튼을 누르면 별도 복사/붙여넣기 없이 실제 내 n8n 인스턴스에 워크플로우가 바로 생성됩니다.
4. n8n을 연결하지 않은 상태라면, 버튼 대신 상단 **n8n 연결** 안내 문구가 표시됩니다 — 먼저 연결한 뒤 다시 시도하세요.

### 6. 화면 캡처해서 물어보기

사이드 패널 우측 하단의 카메라 아이콘(📷) 버튼을 누르면:

- n8n 탭이 열려 있으면 그 화면을, 없으면 현재 활성 탭을 캡처합니다.
- 캡처된 이미지가 채팅 입력창에 자동으로 첨부됩니다.
- 예를 들어 에러 팝업이나 복잡한 노드 설정 화면을 캡처한 뒤 "이 화면 무슨 뜻이야?"처럼 이어서 질문할 수 있습니다.

### 7. 현재 지원 범위

- **분석(읽기)**: `localhost:5678` / `127.0.0.1:5678` / `n8n.cortie.io` / n8n Cloud에서 실제로 동작 확인됨
- **생성(REST API 경유)**: n8n 연결 후 "n8n에 바로 생성" 버튼으로 실제 워크플로우 생성까지 동작 확인됨
- **생성(캔버스에 직접 붙여넣기)**: 내부적으로는 구현되어 있지만 현재 화면에 연결된 버튼이 없어 실제로는 위 REST API 경유 방식만 사용됩니다.

### 문제 해결

| 증상 | 확인할 것 |
|---|---|
| 사이드 패널에 "연결할 수 없습니다" | naito.chat 서비스 상태 확인 |
| "n8n에 바로 생성" 실패 | n8n URL/API Key가 올바른지, n8n이 실제로 그 주소에서 실행 중인지 확인 |
| 코드 수정이 반영 안 됨 | `chrome://extensions`에서 새로고침(⟳) 버튼 클릭 필요 |

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| LLM / 임베딩 | OpenAI GPT-4o mini, text-embedding-3-small |
| 검색 | 하이브리드 RAG (BM25 + 벡터 검색, RRF 결합), ChromaDB |
| 백엔드 | FastAPI, Python |
| 프론트엔드 | Next.js, TypeScript |
| DB | PostgreSQL |
| 자동화 엔진 | n8n |
| 배포 | Docker Compose |
| 확장 프로그램 | Chrome Extension (Manifest V3) |

---

## 문서 모음

| 문서 | 내용 |
|---|---|
| [`docs/technical/ARCHITECTURE.md`](docs/technical/ARCHITECTURE.md) | 설계 철학·이론적 배경·코드 레벨 아키텍처 상세 분석 |
| [`docs/technical/ONTOLOGY.md`](docs/technical/ONTOLOGY.md) | 453개 노드 5계층 온톨로지 전체 스펙 |
| [`docs/technical/OVERVIEW.md`](docs/technical/OVERVIEW.md) | 서버 처리 로직 요약 (의도 판단 → 온톨로지 → RAG → 검증) |
| [`docs/technical/WORKFLOWS.md`](docs/technical/WORKFLOWS.md) | RAG 데이터셋 빌드·갱신 운영 절차 |
| [`docs/reports/`](docs/reports/) | 최종결과보고서 · 중간보고서 · 발표자료 · 성능테스트 보고서 · ChatGPT 비교 보고서 |
| [`Chrome_extention/README.md`](Chrome_extention/README.md) | 확장 프로그램 사용법 (이 README의 확장 프로그램 섹션과 동일 내용) |
| [`RAG_builder/README.md`](RAG_builder/README.md) | RAG 지식베이스 빌드 파이프라인 사용법 |
