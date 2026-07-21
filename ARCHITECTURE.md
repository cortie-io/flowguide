# Naito: 온톨로지·RAG·REG 기반 설명 가능 n8n 자동화 튜터 시스템

> **논문 수준 아키텍처 설계 보고서**  
> 작성 기준: 2026년 6월 22일 | 코드베이스 기준

---

## 목차

1. [개요 및 연구 동기](#1-개요-및-연구-동기)
2. [기존 AI 튜터의 한계와 차별화 전략](#2-기존-ai-튜터의-한계와-차별화-전략)
3. [이론적 배경](#3-이론적-배경)
4. [시스템 전체 아키텍처](#4-시스템-전체-아키텍처)
5. [계층별 구조 분석](#5-계층별-구조-분석)
6. [핵심 컴포넌트: Intent 분류기](#6-핵심-컴포넌트-intent-분류기)
7. [핵심 컴포넌트: 도메인 온톨로지 및 관계 그래프 (하이브리드 453노드)](#7-핵심-컴포넌트-도메인-온톨로지-및-관계-그래프)
8. [핵심 컴포넌트: 온톨로지 기반 RAG 쿼리 확장기](#8-핵심-컴포넌트-온톨로지-기반-rag-쿼리-확장기)
9. [핵심 컴포넌트: 하이브리드 RAG 파이프라인](#9-핵심-컴포넌트-하이브리드-rag-파이프라인)
10. [핵심 컴포넌트: 온톨로지 기반 커리큘럼 엔진](#10-핵심-컴포넌트-온톨로지-기반-커리큘럼-엔진)
11. [핵심 컴포넌트: 다층 사후 검증 파이프라인](#11-핵심-컴포넌트-다층-사후-검증-파이프라인)
12. [핵심 컴포넌트: 구조화 출력 계약 (SOC)](#12-핵심-컴포넌트-구조화-출력-계약-soc)
13. [다층 환각 억제 프레임워크](#13-다층-환각-억제-프레임워크)
14. [설명 가능성(XAI) 설계 원칙](#14-설명-가능성xai-설계-원칙)
15. [세션 컨텍스트 관리와 꼬리 물기 추론](#15-세션-컨텍스트-관리와-꼬리-물기-추론)
16. [LLM 라우팅 아키텍처 (BYOK 포함)](#16-llm-라우팅-아키텍처-byok-포함)
17. [응답 스트리밍 프로토콜](#17-응답-스트리밍-프로토콜)
18. [의도별 처리 흐름 전체 추적 (7가지 예시)](#18-의도별-처리-흐름-전체-추적-7가지-예시)
19. [기존 시스템과의 차별성 비교](#19-기존-시스템과의-차별성-비교)
20. [설계 결정 기록 (Architecture Decision Records)](#20-설계-결정-기록)

---

## 1. 개요 및 연구 동기

### 1.1 문제 정의

대규모 언어 모델(LLM)은 범용 질의응답에서 뛰어난 성능을 보이지만, 특정 소프트웨어 도메인의 기술 교육에 적용할 때 세 가지 근본적 결함이 드러난다.

**결함 1 — 사실 환각(Factual Hallucination)**  
LLM은 n8n 노드의 파라미터명(`retryOnFail`, `batchSize`), API 스펙, 표현식 문법(`$json`, `$node`)을 자신감 있게 그러나 잘못 생성하는 경향이 있다. n8n은 500개 이상의 노드와 수천 개의 파라미터를 가지므로, LLM 학습 데이터에 충분히 포함되지 않은 세부 스펙은 특히 취약하다.

**결함 2 — 출처 불명확성(Source Opacity)**  
"왜 이 파라미터를 이렇게 설정해야 하는가?"에 대한 근거를 제시할 수 없다. 전통적 LLM은 답변의 출처를 명시하지 못하므로 학습자가 정보를 검증할 수 없고, 교사 역할로서의 신뢰성이 낮다.

**결함 3 — 맥락 비일관성(Context Inconsistency)**  
사용자의 학습 수준이나 현재 워크플로우 상태에 대한 컨텍스트를 지속적으로 추적하지 못한다. 매 턴마다 동일한 설명 수준으로 응답하거나, 이전 대화의 맥락을 망각한다.

### 1.2 Naito의 목표

Naito는 이 세 결함을 각각 다른 아키텍처 레이어로 해결하는 **설명 가능한(Explainable) n8n 자동화 튜터**다.

| 결함 | 해결 메커니즘 | 담당 컴포넌트 |
|------|-------------|-------------|
| 사실 환각 | 검색 증강 생성(RAG) + 사후 검증(REG) | HybridRetriever, EnhancedREGValidator |
| 출처 불명확성 | 청크 소스 귀속 + 의도 결정 공개 | IntentRouter, RAG 컨텍스트 |
| 맥락 비일관성 | 온톨로지 기반 레벨 감지 + 세션 히스토리 | CurriculumService, SessionStore |

### 1.3 핵심 설계 철학

```
"LLM은 표현(Expression)을 생성하되, 지식(Knowledge)은 검색에서 온다."
"모든 결정은 추적 가능하고, 모든 출력은 검증 가능해야 한다."
```

---

## 2. 기존 AI 튜터의 한계와 차별화 전략

### 2.1 기존 접근법 유형

**유형 A — Raw LLM 기반 (ChatGPT, Claude 직접 사용)**
- 모델 지식에만 의존 → 환각 발생
- 출력 비결정론적 → 동일 질문에 다른 답
- 도메인 특화 안 됨 → n8n 스펙 오류 빈번

**유형 B — Fine-tuned 모델**
- 고비용 파인튜닝 필요
- n8n 버전 업에 따른 재훈련 필요
- 내부 추론 과정 불투명

**유형 C — 단순 RAG 기반**
- 검색은 하지만 출력 검증 없음
- 단일 벡터 검색만 사용 → recall 한계
- 사용자 컨텍스트 미반영

### 2.2 Naito의 차별화 축

```
차별화 축 1: 검색 — 이중 인덱스(BM25 + 벡터) + RRF 융합
차별화 축 2: 생성 — 의도별 특화 서비스 + 구조화 출력 계약
차별화 축 3: 검증 — REG 사후 검증으로 파라미터 오타 자동 수정
차별화 축 4: 투명성 — 모든 결정(의도/수정/출처)을 실시간 이벤트로 공개
차별화 축 5: 개인화 — 온톨로지 기반 학습 수준 감지 + 세션 맥락 유지
차별화 축 6: 실행 가능성 — 생성된 코드를 n8n 캔버스에 직접 주입
```

---

## 3. 이론적 배경

### 3.1 설명 가능한 AI (Explainable AI, XAI)

XAI는 AI 시스템의 결정 과정을 인간이 이해할 수 있도록 설계하는 분야다. Naito는 다음 XAI 원칙을 적용한다.

**투명성(Transparency):** IntentRouter는 최종 분류 결과를 `intent` 이벤트로 즉시 클라이언트에 노출한다. 에러 로그·n8n JSON 첨부·꼬리 물기 3가지 명백한 신호는 100% 규칙 기반이라 "왜 이 경로로 갔는지"를 코드로 완전히 설명할 수 있고, 그 외 자연어 질문은 LLM이 판단하되 LLM이 GENERAL로 회피하는 경우를 키워드 안전망으로 감지·보정한다(§6 참고).

**사후 해석 가능성(Post-hoc Interpretability):** `intent` 이벤트, `reg_warning` 이벤트가 의사결정 결과를 실시간으로 클라이언트에 전달한다.

**신뢰성(Faithfulness):** RAG가 제공한 실제 문서 청크를 프롬프트에 삽입하므로, 답변의 근거가 시스템에 실제로 존재한다.

### 3.2 온톨로지 기반 지식 표현 (Ontology-based Knowledge Representation)

온톨로지는 도메인의 개념과 그 관계를 형식적으로 명세한다. Naito는 n8n 도메인 지식을 다음 온톨로지로 구조화한다.

**지식 소스 온톨로지 (Knowledge Source Ontology)**

```
n8n_Knowledge
 ├── Normative (기준이 되는 지식)
 │    ├── spec          — 파라미터 공식 스펙
 │    ├── cli_spec      — CLI 레벨 스펙
 │    └── official_docs — n8n 공식 문서
 │
 ├── Educational (학습 목적 지식)
 │    ├── entry         — 입문 레벨
 │    ├── beginner      — 초급 레벨
 │    ├── intermediate  — 중급 레벨
 │    ├── advanced      — 고급 레벨
 │    └── book          — 교재
 │
 └── Operational (운영 경험 지식)
      ├── troubleshooting — 에러 해결 사례
      ├── api_limits      — API 제한 대응
      ├── parent_summary  — 워크플로우 설계 요약
      └── child_json      — 실행 가능 워크플로우 JSON
```

**노드 구조 온톨로지 (Node Structure Ontology)**

```
n8n_Node
 ├── role
 │    ├── trigger   — 워크플로우 시작 (Schedule, Webhook, Manual)
 │    ├── processing — 데이터 처리 (IF, Set, Code, HTTP Request)
 │    └── sink      — 데이터 출력 (Slack, Gmail, Google Sheets)
 │
 ├── property
 │    ├── displayName (사용자 표시명)
 │    ├── name        (API 파라미터명 — REG 검증 대상)
 │    ├── type        (string | number | boolean | options | fixedCollection)
 │    └── default     (기본값)
 │
 └── connection
      ├── source_node
      ├── target_node
      └── connection_type (main | error)
```

이 온톨로지는 세 가지 방식으로 시스템에 활용된다:
1. RAG 검색 시 `data_type` 필터로 관련 지식 소스만 선택
2. CurriculumService에서 학습 수준 → 지식 소스 매핑
3. ReverseService에서 노드를 trigger/processing/sink로 분류

**학습 수준 온톨로지 (Learning Level Ontology)**

```
UserLevel
 ├── beginner
 │    └── sources: {entry, beginner, official_docs, book}
 │    └── weeks: 4, duration: 45m
 │
 ├── intermediate
 │    └── sources: {intermediate, official_docs, book, spec}
 │    └── weeks: 5, duration: 60m
 │
 └── advanced
      └── sources: {advanced, spec, troubleshooting, api_limits}
      └── weeks: 6, duration: 90m
```

### 3.3 검색 증강 생성 (Retrieval-Augmented Generation, RAG)

RAG는 생성 전에 외부 지식 베이스에서 관련 문서를 검색하여 LLM의 입력 컨텍스트로 제공하는 패러다임이다 (Lewis et al., 2020).

Naito는 **하이브리드 RAG**를 구현한다. 단일 검색 방법의 한계를 극복하기 위해 두 종류의 검색을 병렬 실행한다:

**희소 검색(Sparse Retrieval) — BM25**  
TF-IDF 기반의 BM25(Robertson & Zaragoza, 2009)는 정확한 키워드 매칭에 강하다. `retryOnFail`과 같은 정확한 파라미터명이나 `Schedule Trigger`와 같은 노드 이름의 완전 일치 검색에 유리하다.

**밀집 검색(Dense Retrieval) — 벡터 유사도**  
BGE-M3 임베딩 모델(Chen et al., 2024)로 생성된 1024차원 벡터를 ChromaDB에서 코사인 유사도로 검색한다. "자동으로 반복 처리"와 "Loop Over Items" 같은 의미적으로 동일하지만 표면적으로 다른 표현을 연결한다.

**순위 융합(Rank Fusion) — RRF**  
두 검색 결과를 Reciprocal Rank Fusion(Cormack et al., 2009)으로 결합한다:

```
RRF_score(d) = Σ_{r ∈ R} 1 / (k + rank_r(d))
```
여기서 k=60, R={BM25_rank, vector_rank}. 어느 한 방법에서만 높게 나와도 최종 순위에 반영된다.

### 3.4 규칙 기반 출력 검증 (REG: Rule-based & Embedding-Grounded Validation)

Naito가 독자적으로 설계한 REG(Rule-based & Embedding-Grounded Validation) 레이어는 LLM 생성 출력을 공식 n8n 스펙에 대조하여 검증한다.

REG의 핵심 알고리즘은 Levenshtein 편집 거리(Levenshtein, 1966)다:

```
d(s, t) = min edit operations to transform s into t
where operations = {insert, delete, substitute}
```

LLM이 생성한 `retryOnFai`(오타)와 스펙의 `retryOnFail` 사이의 거리가 1이므로 자동 수정된다. 수정 가능 임계값은 편집 거리 ≤ 2이다.

### 3.5 구조화 출력 계약 (SOC: Structured Output Contract)

LLM 출력의 형식을 시스템 프롬프트로 엄격히 지정하여, 출력이 기계 파싱 가능하고 사전 정의된 스키마를 따르도록 강제한다. 이는 LLM을 단순 텍스트 생성기가 아닌 **구조화 데이터 생성기**로 활용하는 패러다임이다.

```
LLM → [SOC 적용] → 스키마 준수 JSON/Markdown → 파서 → UI 렌더러
```

---

## 4. 시스템 전체 아키텍처

### 4.1 아키텍처 다이어그램

```
╔══════════════════════════════════════════════════════════════════════╗
║  CLIENT LAYER                                                        ║
║                                                                      ║
║  ┌─────────────────────────────┐   ┌──────────────────────────────┐  ║
║  │  Next.js Web App (Port 3000)│   │  Chrome Extension (n8n 에디터)│  ║
║  │                             │   │                              │  ║
║  │  ┌────────┐  ┌───────────┐  │   │  ┌──────────┐ ┌──────────┐  │  ║
║  │  │useChat │  │OpenAI Key │  │   │  │content.js│ │sidepanel │  │  ║
║  │  │(AI SDK)│  │Input (UI) │  │   │  │(캔버스   │ │.js       │  │  ║
║  │  └───┬────┘  └───────────┘  │   │  │데이터 추출│ │(사이드   │  │  ║
║  │      │ POST /api/chat       │   │  └────┬─────┘ │패널 UI)  │  │  ║
║  └──────┼──────────────────────┘   └───────┼────────┴──────────┘  ║
║         │ AI SDK Stream Protocol   HTTP/WS │                       ║
╚═════════╪═══════════════════════════════════╪═══════════════════════╝
          │                                   │
╔═════════▼═══════════════════════════════════▼═══════════════════════╗
║  MIDDLEWARE LAYER (Next.js API Routes)                              ║
║                                                                      ║
║  ┌──────────────────────────────────────────────────────────────┐   ║
║  │  /api/chat (route.ts)                                        │   ║
║  │                                                              │   ║
║  │  Auth Check → DB Save(user msg) → FastAPI Proxy → Stream    │   ║
║  │  → DB Save(assistant msg) → Title Gen → Finish Signal       │   ║
║  └──────────────────────────┬───────────────────────────────────┘   ║
╚════════════════════════════ ┼ ═══════════════════════════════════════╝
                              │ HTTP POST (SSE Response)
╔═════════════════════════════▼═══════════════════════════════════════╗
║  SERVICE LAYER (FastAPI, Port 8000)                                 ║
║                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐    ║
║  │  /api/workspace/stream  (workspace.py)                      │    ║
║  │                                                             │    ║
║  │  ┌───────────────┐   ┌──────────────────────────────────┐  │    ║
║  │  │CredentialFilter│   │        IntentRouter              │  │    ║
║  │  │(전처리:자격증명│   │  (LLM 우선 분류 + 규칙 3종 안전망) │  │    ║
║  │  │ 마스킹)       │   │  → CURRICULUM/EXPRESSION/        │  │    ║
║  │  └───────────────┘   │    WORKFLOW_BUILD/ERROR_PATCH/    │  │    ║
║  │                       │    REVERSE/GENERAL               │  │    ║
║  │                       └────────────────┬─────────────────┘  │    ║
║  │                                        │                     │    ║
║  │          ┌─────────────────────────────┼──────────────────┐ │    ║
║  │          ▼         ▼          ▼        ▼       ▼         ▼  │    ║
║  │  ┌──────────┐ ┌────────┐ ┌───────┐ ┌──────┐ ┌──────┐ ┌───┐ │    ║
║  │  │Curriculum│ │Express-│ │Work-  │ │Error │ │Revers│ │Gen│ │    ║
║  │  │Service   │ │ion     │ │flow   │ │Patch │ │e     │ │RAG│ │    ║
║  │  │          │ │Service │ │Build  │ │Svc   │ │Svc   │ │Svc│ │    ║
║  │  └──────────┘ └────────┘ └───────┘ └──────┘ └──────┘ └───┘ │    ║
║  │          │         │          │        │         │        │  │    ║
║  │          └─────────────────────────────────────────────────┘  │    ║
║  │                         │ _stream_llm()                        │    ║
║  │  ┌─────────────────────────────────────────────────────────┐  │    ║
║  │  │  REG Validator (Post-generation verification)           │  │    ║
║  │  │  Levenshtein fuzzy match → n8n_properties_spec.txt      │  │    ║
║  │  └─────────────────────────────────────────────────────────┘  │    ║
║  └──────────────────────────┬──────────────────────────────────┘    ║
║                              │                                        ║
║  ┌───────────────────────────┼──────────────────────────────────┐    ║
║  │  RAG ENGINE                │                                  │    ║
║  │                            ▼                                  │    ║
║  │  ┌─────────────────────────────────────────────────────────┐ │    ║
║  │  │  HybridRetriever (query_engine.py)                      │ │    ║
║  │  │                                                         │ │    ║
║  │  │  Query Rewrite → BM25 (ProcessPool) │ ChromaDB Vector   │ │    ║
║  │  │                                     │ (BGE-M3 1024-dim) │ │    ║
║  │  │                     RRF Fusion (k=60)                   │ │    ║
║  │  │                     Intent-based Type Filter             │ │    ║
║  │  │                     _rank_key() Re-ranking               │ │    ║
║  │  └─────────────────────────────────────────────────────────┘ │    ║
║  │                                                               │    ║
║  │  ┌──────────────────┐   ┌─────────────────────────────────┐  │    ║
║  │  │  chunks.jsonl     │   │  ChromaDB                        │  │    ║
║  │  │  14,543 chunks    │   │  (n8n_rag_v2 collection)        │  │    ║
║  │  │  BM25 Index       │   │  BGE-M3 1024-dim vectors        │  │    ║
║  │  │  (in-memory)      │   │                                 │  │    ║
║  │  └──────────────────┘   └─────────────────────────────────┘  │    ║
║  └──────────────────────────────────────────────────────────────┘    ║
╚═════════════════════════════╪═══════════════════════════════════════╝
                              │
         ┌────────────────────┴──────────────────────┐
         │                                            │
╔════════▼═══════════╗                   ╔════════════▼══════════════╗
║  Ollama Server      ║                   ║  OpenAI API               ║
║  100.79.44.109:11434║                   ║  (사용자 BYOK)            ║
║                     ║                   ║  gpt-4o / gpt-4o-mini /  ║
║  gemma4-e4b:latest  ║                   ║  gpt-4.1                 ║
║  qwen3.6:35b-a3b    ║                   ║                          ║
║  bge-m3:latest      ║                   ╚══════════════════════════╝
╚═════════════════════╝
```

### 4.2 데이터 흐름 요약

```
User Input
   │
   ▼
[1. 전처리]    자격증명 마스킹, 메시지 추출
   │
   ▼
[2. 의도 분류] IntentRouter (LLM 우선 분류 + 규칙 3종 안전망)
   │
   ▼
[2.5. 온톨로지 확장] OntologyEnhancer
              노드 감지 → 관련 용어 확장 → 패턴 매칭 → 힌트 생성
   │
   ▼
[3. RAG 검색]  의도별 필터 → BM25 + 벡터 병렬 → RRF 융합 (확장 쿼리 사용)
   │
   ▼
[4. 프롬프트 구성] SOC 시스템 프롬프트 + RAG 컨텍스트 + 온톨로지 힌트 + 히스토리
   │
   ▼
[5. LLM 생성]  Ollama 또는 OpenAI BYOK 스트리밍
   │
   ▼
[6. REG 검증]  파라미터 오타 감지 → Levenshtein 수정 → reg_warning 이벤트
   │
   ▼
[6.5. 의미 검증] SemanticValidator (WORKFLOW_BUILD/ERROR_PATCH만)
               구조·속성 제약·패턴·표현식 4단계 검증
   │
   ▼
[7. 응답 전송]  SSE → AI SDK Stream Protocol → 브라우저 실시간 렌더링
   │
   ▼
[8. 사후 처리]  세션 히스토리 저장, DB 저장, 제목 생성
```

---

## 5. 계층별 구조 분석

### 5.1 클라이언트 레이어 (Next.js, Port 3000)

**목적:** 사용자 인터페이스 제공, 스트림 수신 및 렌더링, 클라이언트 사이드 상태 관리

| 컴포넌트 | 파일 | 역할 |
|----------|------|------|
| 채팅 훅 | `hooks/use-active-chat.tsx` | useChat 래퍼, 모델 선택, OpenAI 키 전달 |
| 채팅 API | `app/(chat)/api/chat/route.ts` | FastAPI 프록시, 스트림 변환, DB 저장 |
| 입력 UI | `components/chat/multimodal-input.tsx` | 텍스트 입력, OpenAI 키 입력 |
| 메시지 렌더러 | `components/chat/message.tsx` | 텍스트 + 구조화 데이터 렌더링 |
| 사이드바 | `components/chat/sidebar-history.tsx` | 채팅 목록, 인라인 제목 편집 |
| 모델 목록 | `lib/ai/models.ts` | Ollama/OpenAI 모델 정의 |
| DB 쿼리 | `lib/db/queries.ts` | PostgreSQL CRUD (Drizzle ORM) |

**XAI 적용점:** 클라이언트는 `intent` 이벤트를 수신하여 "현재 어떤 서비스가 처리 중인지"를 사용자에게 표시한다. `reg_warning` 이벤트는 "무엇이 자동 수정되었는가"를 즉시 알린다.

### 5.2 미들웨어 레이어 (Next.js API Route)

**목적:** 인증 게이트키핑, FastAPI 프록시, SSE → AI SDK 변환, 데이터 영속성

`route.ts`는 단일 파일이지만 여러 책임을 순차적으로 수행한다:

```
POST /api/chat
│
├─ 1) Zod 스키마 검증 (입력 타입 보장)
├─ 2) NextAuth 세션 검증 (인증)
├─ 3) DB: 신규 채팅이면 saveChat() — isFirstMessage 캡처
├─ 4) DB: saveMessages(user message)
├─ 5) DB: getMessagesByChatId() — 히스토리 로드
├─ 6) FastAPI POST /api/workspace/stream — 스트리밍 시작
├─ 7) createUIMessageStream: SSE 파싱 및 AI SDK 포맷 변환
│    ├─ "0:" 토큰 → text-delta 이벤트
│    ├─ "2:" 구조화 데이터 → data-{type} 이벤트 (thinking/intermediate 필터링)
│    └─ "d:" 종료 신호
└─ 8) [finally] 스트리밍 완료 후:
     ├─ DB: saveMessages(assistant message)
     ├─ IF isFirstMessage: generateTitleFromUserMessage() + updateChatTitleById()
     ├─ writer.write({ type: "finish" }) — 제목 저장 완료 후 전송
     └─ DB: saveRequestLog(intent, latencyMs, structuredPayloads, ...)
```

**설계 결정:** `writer.write({ type: "finish" })`를 제목 저장 이후에 호출하는 것이 핵심이다. Vercel AI SDK의 `useChat`은 `finish` 이벤트를 받아 SWR 캐시를 무효화하므로, 이 순서를 지켜야 브라우저의 사이드바가 정확한 제목을 즉시 표시한다.

### 5.3 서비스 레이어 (FastAPI, Port 8000)

**목적:** Intent 분류, RAG 검색, LLM 스트리밍, REG 검증

핵심 파일:

| 파일 | 역할 | 이론적 분류 |
|------|------|------------|
| `workspace.py` | 통합 스트리밍 허브, SSE↔AI SDK 변환 | 오케스트레이터 |
| `intent_router.py` | 6가지 Intent 분류 | LLM 우선 + 규칙 안전망 하이브리드 분류기 |
| `workflow_services.py` | CURRICULUM/EXPRESSION/WORKFLOW_BUILD | 서비스 클래스 |
| `feature_services.py` | ERROR_PATCH/REVERSE | 서비스 클래스 |
| `general_rag.py` | GENERAL RAG Q&A | 서비스 클래스 |
| `query_engine.py` | HybridRetriever (BM25 + ChromaDB) | RAG 엔진 |
| `reg_validator.py` | 파라미터 오타 검증기 | REG 레이어 |
| `query_rewrite.py` | 쿼리 재작성 (한영 정규화) | 전처리 |
| `session.py` | 인메모리 세션 스토어 | 상태 관리 |
| `credential_filter.py` | 자격증명 마스킹 | 보안 전처리 |

### 5.4 데이터 레이어

**RAG 지식 베이스:**
- `RAG_dataset/chunks.jsonl` — 14,543개 구조화 청크
- ChromaDB `n8n_rag_v2` — 벡터 인덱스 (BGE-M3 1024차원)
- BM25 인덱스 — 런타임 메모리 로드

**관계형 DB (PostgreSQL, Drizzle ORM):**

```
user          ─┐
               ├── chat (title, visibility)
               │      └── message (role, parts, createdAt)
               │      └── requestLog (intent, latencyMs, model, ...)
               │      └── vote
               └── stream
```

---

## 6. 핵심 컴포넌트: Intent 분류기

**파일:** `server/intent_router.py`  
**이론적 분류:** LLM 우선 하이브리드 분류기, 규칙 기반 고속 경로 포함 (LLM-primary Hybrid Classifier with Rule-based Fast Path)

> **개정 이력:** 초기 버전은 정규식만으로 6개 Intent를 전부 분류하는 순수 규칙 기반 설계였다(§20 ADR-001 참고). 이후 "Webhook 노드 설명해줘"(GENERAL)와 "이 워크플로우 어떻게 동작해?"(REVERSE)처럼 표면적으로 비슷하지만 의미가 다른 문장의 오분류가 반복되어, 애매한 자연어 판단은 LLM에 위임하고 규칙은 텍스트 의미 이해가 필요 없는 3가지 명백한 신호로 범위를 좁혔다.

### 6.1 설계 철학

IntentRouter는 신호의 성격에 따라 두 갈래로 판단을 나눈다.

1. **명백한 신호는 규칙으로 즉시 처리:** 에러 로그 첨부, n8n JSON(`"connections"` 키) 첨부, 꼬리 물기 후속 질문은 문장의 의미를 이해할 필요가 없다 — 데이터가 "있냐 없냐"만 보면 되므로 정규식으로 수 ms 내에 확정하고 LLM을 아예 호출하지 않는다.
2. **애매한 자연어는 LLM으로:** 위 3가지에 해당하지 않는 대부분의 질문은 few-shot 프롬프트를 포함한 LLM 호출로 분류한다. 문맥과 의도를 함께 봐야 하는 경계 케이스는 정규식보다 LLM이 훨씬 정확하다.
3. **키워드는 LLM의 안전망:** LLM이 애매해서 GENERAL로 회피하거나 호출 자체가 실패했을 때만 가벼운 키워드 추정이 개입해 구제한다. LLM이 정상적으로 구체적인 Intent를 반환하면 키워드 추정 결과는 버려진다.

### 6.2 6가지 Intent와 역할

| Intent | 트리거 조건 | 담당 서비스 | 주 역할 |
|--------|-----------|-----------|--------|
| CURRICULUM | 학습 관련 질문 (LLM 판단) | CurriculumService | 온톨로지 기반 개인 맞춤 로드맵 생성 |
| EXPRESSION | node_data + 수식 관련 질문 (LLM 판단) | ExpressionService | 실제 노드 데이터 기반 표현식 생성 |
| WORKFLOW_BUILD | 워크플로우 설계/구현 요청 (LLM 판단) | WorkflowBuildService | 실행 가능 워크플로우 JSON 생성 |
| ERROR_PATCH | error_log 첨부 + 에러 패턴 (규칙, 즉시 확정) | ErrorPatchService | 에러 진단 + 패치 코드 생성 |
| REVERSE | n8n JSON `"connections"` 감지 (규칙, 즉시 확정) 또는 특정 워크플로우 지칭 (LLM 판단) | ReverseService | 토폴로지 역분석 3층 리포트 |
| GENERAL | 위 5개 해당 없음 | GeneralRAGService | RAG 기반 일반 Q&A |

### 6.3 분류 로직 (전체, 실제 코드 기준)

```python
async def route(
    self, message, model="",
    node_data=None, error_log=None, raw_json=None,
    history=None, n8n_url=None, openai_api_key=None,
) -> Intent:

    # ── 규칙 1: 에러 로그 첨부 → 무조건 ERROR_PATCH (LLM 미호출) ──────
    if error_log and _ERROR_PATTERN.search(error_log):
        return Intent.ERROR_PATCH

    # ── 규칙 2: n8n JSON 첨부("connections" 키) → REVERSE (LLM 미호출) ─
    json_candidate = raw_json or message
    if _N8N_JSON_PATTERN.search(json_candidate):
        return Intent.REVERSE

    # ── 규칙 3: 꼬리 물기 짧은 후속 질문 → 이전 intent 재사용 (LLM 미호출) ─
    if history and _FOLLOWUP_KW.search(message):
        prev = self._last_intent(history)
        if prev is not None:
            return prev

    # ── 그 외: 키워드 추정을 항상 먼저 계산해두고(성패 무관 안전망), LLM 호출 ──
    keyword_guess = self._keyword_guess(message, node_data)

    raw_result = await _call_llm_classify(message, context_block, model, openai_api_key)
    llm_intent = _parse_intent(raw_result)

    if llm_intent:
        # LLM이 확신 없어 GENERAL로 답했는데 키워드는 구체적 의도를 가리키면
        # 키워드 쪽을 채택 (LLM의 "모르겠음" 회피를 구제)
        if llm_intent is Intent.GENERAL and keyword_guess and keyword_guess is not Intent.GENERAL:
            return keyword_guess
        return llm_intent

    # LLM 호출 자체가 실패했을 때만 키워드로 완전 폴백
    return keyword_guess or Intent.GENERAL
```

### 6.4 LLM 분류 프롬프트 — 경계 케이스를 few-shot으로 명시

규칙만으로 가르기 어려웠던 케이스들이 그대로 판단 기준 예시로 프롬프트에 박혀 있다:

```python
_CLASSIFY_SYSTEM = """\
당신은 n8n 자동화 어시스턴트의 인텐트 분류기입니다.
사용자 메시지를 읽고 아래 6가지 인텐트 중 하나만 출력하십시오.

인텐트 정의:
- CURRICULUM: n8n 학습 계획, 로드맵, 커리큘럼, 단계별 학습 요청
- EXPRESSION: $json, $node 수식/표현식 생성, 필드 접근 방법 질문
- WORKFLOW_BUILD: 새 워크플로우 만들기, 자동화 설계/구현/짜줘 요청
- ERROR_PATCH: 에러 메시지/로그 분석, 오류 해결 요청
- REVERSE: 특정 워크플로우/플로우를 분석/설명/해석/이해 요청, 또는
  n8n에 있는 워크플로우 JSON을 가져오기/불러오기/조회 요청
- GENERAL: n8n 개념 설명, 노드 사용법, 일반 질문

판단 기준 — 헷갈리는 케이스:
- "XXX 플로우 설명해줘" → REVERSE (특정 플로우 대상)
- "Webhook 노드 설명해줘" → GENERAL (개념/노드 설명)
- "워크플로우 어떻게 만들어?" → GENERAL (방법론 질문)
- "이 워크플로우 어떻게 동작해?" → REVERSE (특정 대상)
- "슬랙 알림 자동화 만들어줘" → WORKFLOW_BUILD
- "$json.name 어떻게 써?" → EXPRESSION

컨텍스트:
{context_block}

사용자 메시지: {message}"""
```

`context_block`에는 `n8n_connected`, `node_data_attached`, `raw_json_attached` 같은 첨부 데이터 존재 여부가 담겨 LLM 판단을 보조한다. Ollama(`/api/chat`, temperature=0) 또는 사용자 BYOK OpenAI 키로 호출하며, `max_tokens`/`num_predict`를 10 내외로 제한해 인텐트 이름 하나만 짧게 받는다.

### 6.5 키워드 안전망 (`_keyword_guess`)

```python
def _keyword_guess(self, message: str, node_data: dict | None) -> Intent | None:
    """키워드 기반 의도 시그널. 매칭 없으면 None (GENERAL로 단정하지 않음)."""
    m = message.lower()
    if any(k in m for k in ["커리큘럼", "로드맵", "학습 계획"]):
        return Intent.CURRICULUM
    if any(k in m for k in ["만들어줘", "짜줘", "구현해줘", "설계해줘"]) and "워크플로우" in m:
        return Intent.WORKFLOW_BUILD
    if any(k in m for k in [
        "분석해줘", "역분석", "리버스",
        "가져와", "가져오", "불러와", "불러오", "임포트", "import",
    ]):
        return Intent.REVERSE
    if node_data and any(k in m for k in ["수식", "expression", "$json"]):
        return Intent.EXPRESSION
    return None
```

매칭이 없으면 `GENERAL`이 아니라 `None`을 반환한다는 점이 중요하다 — "이 메시지는 명백히 GENERAL"과 "키워드로는 판단 불가"를 구분해야, LLM의 정상적인 GENERAL 판정을 키워드가 함부로 덮어쓰지 않는다.

### 6.6 규칙 3종 정규식 (여전히 순수 규칙 기반)

```python
_N8N_JSON_PATTERN = re.compile(r'"connections"\s*:\s*\{', re.DOTALL)
_ERROR_PATTERN = re.compile(
    r"error|exception|failed|cannot|undefined|null.*is not|"
    r"에러|오류|실패|접근\s*불가|작동\s*(안|불)가",
    re.IGNORECASE,
)
_FOLLOWUP_KW = re.compile(
    r"^.{0,60}(더\s*(자세|설명|알려)|예시|계속|그\s*(거|노드|기능|방식|부분)|"
    r"이\s*(거|노드|부분)|방금|앞에서|위에서|아까|좀\s*더|구체적)",
    re.IGNORECASE,
)
```

---

## 7. 핵심 컴포넌트: 도메인 온톨로지 및 관계 그래프

**파일:** `server/domain_ontology.py`  
**이론적 분류:** 형식 온톨로지 (Formal Ontology) — 개념 간 상관관계 명세

### 7.1 설계 목적

기존 RAG 시스템은 쿼리와 청크의 표면적 유사도만을 기반으로 검색한다. 그러나 n8n 도메인에서는 **"HTTP Request 노드를 물어보는 사람은 Set 노드, 에러 처리, Rate Limit에 대한 정보도 필요하다"**는 암묵적 관계가 존재한다. 이 상관관계를 형식적으로 명세한 것이 N8N 도메인 온톨로지다.

n8n은 공식적으로 500개 이상의 노드를 지원한다. RAG 데이터셋 분석 결과, `final_rag_chunks_v2.jsonl`(14,543 청크) 내에서 453개의 고유 노드가 빈도 ≥ 3 기준으로 확인되었다. 이 전체 노드 공간을 커버하면서도 **논문 수준의 답변 품질**을 달성하기 위해 **하이브리드 온톨로지** 전략을 채택했다.

온톨로지는 세 가지 방식으로 시스템에 기여한다:

```
하이브리드 온톨로지 (185개 수동 + 268개 자동 = 453개 노드)
 ├→ OntologyEnhancer: RAG 쿼리에 관련 노드 용어 자동 추가
 ├→ SemanticValidator: 생성된 워크플로우의 제약 위반 감지
 └→ CurriculumService: 선행 학습 의존성 그래프 기반 로드맵
```

### 7.2 하이브리드 온톨로지 전략

n8n 노드 전체(453개)를 커버하면서도 품질을 유지하기 위해 두 계층으로 노드를 분리 관리한다.

```
┌─────────────────────────────────────────────────────────────────┐
│  수동 정의 노드 (Manual) — 185개                                  │
│  RAG 데이터셋 언급 빈도 상위 노드 수작업 정의                       │
│                                                                   │
│  • RelationGraph: 노드 간 7종 관계 + 가중치 + 설명 완전 명세       │
│  • PropertyConstraints: 속성 제약 규칙 (30개)                     │
│  • WorkflowPatterns: 검증된 패턴 라이브러리 (11개)                │
│  • LearningGraph: 선행 학습 의존성 (17개 노드)                    │
│                                                                   │
│  RAG 언급 커버리지: 93.7% (32,555건 중 30,492건)                  │
├─────────────────────────────────────────────────────────────────┤
│  자동 생성 노드 (Auto-Generated) — 268개                          │
│  camelCase 파싱 기반 기본 메타데이터만 자동 생성                    │
│                                                                   │
│  • display_name: camelCase → Title Case 변환                     │
│  • role: 접미사 규칙 기반 추론 (Trigger/Tool/Processing/Sink)      │
│  • tags: camelCase 분절 + 카테고리 키워드 보강                     │
│  • relations/constraints: 없음 (빈도 낮아 품질 영향 미미)           │
│                                                                   │
│  RAG 언급 커버리지 추가분: 6.3%                                    │
└─────────────────────────────────────────────────────────────────┘
```

**병합 전략:** `_ALL_NODE_DEFS = _NODE_DEFS + _AUTO_NODE_DEFS`  
수동 노드가 우선 삽입되므로 동일 short_type이 충돌할 경우 수동 정의가 항상 우선한다.

```python
_MANUAL_SHORT_SET = frozenset(n.short_type.lower() for n in _NODE_DEFS)
_AUTO_NODE_DEFS   = [make_auto(raw) for raw in _RAW_ALL_NODES
                     if raw.lower() not in _MANUAL_SHORT_SET]
_NODE_BY_SHORT    = {n.short_type.lower(): n for n in _ALL_NODE_DEFS}
```

### 7.3 온톨로지 5계층 구조

```
N8N 도메인 온톨로지 (domain_ontology.py)
│
├─ Layer 1: NodeTaxonomy (노드 분류 계층)
│    ├─ N8NNodeDef: 노드 정의 (short_type, full_type, role, tags, ...)
│    ├─ NodeRole: TRIGGER / PROCESSING / SINK / UTILITY
│    └─ OutputType: JSON / BINARY / BOTH / NONE
│    ※ 수동 185개 + 자동 268개 = 453개 노드 전체 커버
│
├─ Layer 2: RelationGraph (상관관계 그래프)
│    ├─ NodeRelation: (target_type, relation_type, weight, description)
│    └─ RelationType 7종:
│         ├─ COMMONLY_USED_WITH    — 실무 co-occurrence
│         ├─ PREREQUISITE_FOR      — 개념적 선행 관계
│         ├─ COMPLEMENTED_BY       — 기능적 보완 관계
│         ├─ PATTERN_MEMBER        — 워크플로우 패턴 구성원
│         ├─ REQUIRES_MULTIPLE_IN  — 다중 입력 필요
│         ├─ ANTI_PATTERN_WITH     — 위험한 조합
│         └─ REPLACES              — 기능 대체 관계
│    ※ 수동 노드(185개)에만 적용, 자동 노드는 빈 리스트
│
├─ Layer 3: PropertyConstraints (속성 제약 규칙) — 30개
│    ├─ ConstraintType: REQUIRES / CONFLICTS / CONDITIONAL / RECOMMENDED / FORBIDDEN
│    ├─ 예: retryOnFail=true → maxTries REQUIRED
│    ├─ 예: telegram.chatId → REQUIRES (ERROR)
│    └─ 예: code.$item() → FORBIDDEN (ERROR, v1.x 폐기)
│
├─ Layer 4: WorkflowPatterns (검증된 패턴 라이브러리) — 11개
│    ├─ WorkflowPattern: name, node_types, connections, best_practices, anti_patterns
│    ├─ 예: periodic_api_monitor (scheduleTrigger→httpRequest→if→slack)
│    ├─ 예: telegram_bot (telegramTrigger→if→telegram)
│    └─ 예: error_monitoring (errorTrigger→set→slack)
│
└─ Layer 5: LearningGraph (학습 선행 의존성 DAG) — 17노드
     ├─ LearningNode: concept, node_types, prerequisites, level, est_minutes
     ├─ 예: "ai_integration" → prerequisites: ["http_api", "data_transformation"]
     └─ 예: "crm_integration" → prerequisites: ["webhook_integration", "data_transformation"]
```

### 7.4 RelationGraph 주요 엣지

| 소스 노드 | 관계 타입 | 대상 노드 | 가중치 | 의미 |
|----------|---------|---------|------|-----|
| httpRequest | COMMONLY_USED_WITH | set | 0.90 | API 응답 필드 정제 |
| httpRequest | COMMONLY_USED_WITH | if | 0.85 | 상태코드 조건 분기 |
| httpRequest | ANTI_PATTERN_WITH | code | 0.40 | Code 내 HTTP 직접 호출 위험 |
| webhook | COMPLEMENTED_BY | respondToWebhook | 0.98 | responseNode 모드 필수 파트너 |
| splitInBatches | PATTERN_MEMBER | merge | 0.85 | Split→처리→Merge 표준 패턴 |
| if | REPLACES | switch | 0.70 | 3분기 이상이면 Switch 적합 |
| telegramTrigger | COMPLEMENTED_BY | telegram | 0.95 | 봇 수신→발송 필수 쌍 |
| functionItem | REPLACES | code | 0.95 | v1.x에서 Code 노드로 대체됨 |
| interval | REPLACES | scheduleTrigger | 0.90 | v1.x에서 Schedule Trigger로 대체 |
| salesforce | ANTI_PATTERN_WITH | hubspot | 0.40 | 두 CRM 동시 저장 → 데이터 불일치 |
| googleDocsTool | REPLACES | googleDocs | 0.80 | AI 에이전트 컨텍스트에서 Tool 버전 사용 |
| kafka | ANTI_PATTERN_WITH | rabbitmq | 0.40 | 두 메시지 큐 동시 발행 → 중복 처리 위험 |

### 7.5 PropertyConstraints 상세 (30개)

```python
# 예시: retryOnFail 제약 체인
PropertyConstraint(
    node_type="httpRequest",
    property_name="retryOnFail",
    constraint_type=ConstraintType.REQUIRES,
    related_property="maxTries",
    severity=ValidationSeverity.WARNING,
    message="`retryOnFail: true` 설정 시 `maxTries`를 반드시 지정해야 합니다.",
)

# 예시: Telegram 필수 파라미터
PropertyConstraint(
    node_type="telegram",
    property_name="chatId",
    constraint_type=ConstraintType.REQUIRES,
    severity=ValidationSeverity.ERROR,
    message="Telegram 노드에 chatId는 필수입니다.",
)
```

**제약 규칙 분류 (총 30개):**

| 노드 그룹 | 규칙 수 | 주요 제약 |
|----------|--------|---------|
| httpRequest | 3 | retryOnFail→maxTries(WARN), sendBody→bodyContentType(WARN) |
| webhook / respondToWebhook | 2 | responseMode=responseNode→respondToWebhook(WARN) |
| googleSheets / postgres | 3 | getAll→limit(WARN), executeQuery→query(ERROR) |
| telegram / notion / airtable | 5 | chatId(ERROR), text(ERROR), operation+databaseId(ERROR) |
| github / wait / formTrigger | 4 | owner(ERROR), repository(ERROR), amount+unit(WARN) |
| emailSend / splitInBatches | 3 | toEmail(ERROR), fromEmail(WARN), options.reset(INFO) |
| mySql / openAi | 5 | operation+query(ERROR), model(INFO), maxTokens(INFO) |
| code | 2 | $items()(FORBIDDEN·ERROR), require()(FORBIDDEN·WARN) |

### 7.6 WorkflowPatterns — 검증된 패턴 라이브러리 (11개)

```python
WorkflowPattern(
    name="periodic_api_monitor",
    description="주기적 API 폴링 → 조건 분기 → 알림 패턴",
    node_types=["scheduleTrigger", "httpRequest", "if", "slack"],
    ...
)
```

**전체 패턴 목록:**

| 패턴명 | 핵심 노드 흐름 | 용도 |
|--------|-------------|------|
| periodic_api_monitor | scheduleTrigger→httpRequest→if→slack | 주기적 API 상태 모니터링 |
| webhook_data_pipeline | webhook→set→googleSheets→slack | 웹훅 데이터 수집·저장 |
| batch_api_processing | scheduleTrigger→httpRequest→splitInBatches→set→merge | 대량 API 배치 처리 |
| form_to_sheet | formTrigger→set→googleSheets | 폼 데이터 수집 |
| error_retry_pattern | httpRequest→if→wait→httpRequest | 재시도 백오프 패턴 |
| ai_data_transform | httpRequest→set→openAi→set | AI 기반 데이터 변환 |
| telegram_bot | telegramTrigger→if→telegram | Telegram 챗봇 |
| form_collect | formTrigger→set→googleSheets+emailSend | 폼 제출·이메일 확인 |
| file_processing | googleDriveTrigger→extractFromFile→set→googleSheets | 파일 ETL |
| github_cicd_notify | githubTrigger→if→slack+jira | CI/CD 알림 |
| error_monitoring | errorTrigger→set→slack | 워크플로우 에러 감시 |

패턴 구성 노드 2개 이상이 쿼리에서 감지되면 `get_pattern_for_nodes()`가 매칭 패턴을 반환하고, best_practices/anti_patterns이 LLM 프롬프트에 삽입된다.

### 7.7 LearningGraph — 선행 의존성 DAG (17노드)

```
n8n_basics (beginner, 30m)
 └─→ triggers (beginner, 45m)
      └─→ form_handling (intermediate, 45m)
      └─→ messaging_bots (intermediate, 60m)
 └─→ data_transformation (beginner, 60m)
      └─→ file_operations (intermediate, 60m)
      └─→ data_processing (intermediate, 60m)
      └─→ conditional_logic (intermediate, 60m)
      └─→ http_api (intermediate, 75m)
           └─→ error_handling (intermediate, 60m)
           └─→ external_services (intermediate, 90m)
                └─→ crm_integration (advanced, 90m)
           └─→ batch_processing (advanced, 90m)
           └─→ webhook_integration (advanced, 90m)
 └─→ ai_integration (advanced, 90m)
      (requires: http_api + data_transformation)
 └─→ workflow_automation (advanced, 90m)
      (requires: conditional_logic + external_services)
 └─→ custom_code (advanced, 90m)
      (requires: data_transformation + http_api)
```

> **검증 참고 (실제 코드 기준):** 이 LearningGraph는 위처럼 정의는 되어 있으나, `get_learning_prerequisites()`를 호출하는 코드가 서버 전체에 없다 — `workflow_services.py`는 `domain_ontology`를 아예 import하지 않는다. CurriculumService는 이 DAG를 참조하지 않고, 독자적인 정규식 레벨 감지(`_LEVEL_PATTERNS`)와 레벨별 RAG 필터 딕셔너리(`_LEVEL_TO_RAG_FILTER`)만으로 로드맵을 생성한다. 즉 LearningGraph는 현재 미사용(dead code) 상태다. 상세 실행 경로는 `OVERVIEW.md` §5 참고.

---

## 8. 핵심 컴포넌트: 온톨로지 기반 RAG 쿼리 확장기

**파일:** `server/ontology_enhancer.py`  
**이론적 분류:** 쿼리 확장 (Query Expansion) + 온톨로지 기반 재랭킹

### 8.1 설계 목적

단순 키워드 검색의 한계: "HTTP Request retry 설정"을 검색하면 `retryOnFail` 스펙 청크는 잘 찾지만, 함께 알아야 할 `maxTries`, `waitBetweenTries`, Rate Limit 패턴은 놓친다. OntologyEnhancer는 쿼리에서 언급된 노드를 감지하고 관계 그래프를 탐색하여 이 누락된 컨텍스트를 자동으로 추가한다.

### 8.2 처리 파이프라인

```
입력 쿼리
   │
   ▼
[1. N8N 엔티티 인식 — 6단계 계층적 감지]
   │
   ├─ Step 1: full_type 패턴
   │    "n8n-nodes-base.httpRequest" → httpRequest 확정
   │
   ├─ Step 2: camelCase short_type regex (453개 전체 동적 생성)
   │    "httpRequest", "splitInBatches" 직접 감지
   │
   ├─ Step 3: 영어 display_name / tag 정확 매칭 (최장 일치)
   │    "HTTP Request", "Split In Batches" → 453개 전부 커버
   │
   ├─ Step 4: 한국어 키워드 정확 매칭 (80+ 엔트리, 단어 경계 체크)
   │    "웹훅"→webhook, "슬랙"→slack, "노션"→notion
   │    ※ 2글자 이하 키는 단어 경계 엄격 적용 (서브스트링 오탐 방지)
   │
   ├─ Step 5: 한국어 퍼지 매칭 (자모 분해 + Levenshtein)  ← 신규
   │    "앱훅이" → 조사 제거 "앱훅" → 자모 분해 "ㅇㅐㅂㅎㅜㄱ"
   │              ↔ "웹훅" 자모 "ㅇㅞㅂㅎㅜㄱ" : dist=1 ≤ thresh=1 → MATCH
   │    오타 교정 기록: ("앱훅", "Webhook") → typo_corrections
   │
   └─ Step 6: 영어 퍼지 매칭 (문자 Levenshtein)            ← 신규
        "webhok" ↔ "webhook" : dist=1 ≤ thresh=1 → MATCH
        오타 교정 기록: ("webhok", "Webhook") → typo_corrections
   │
   ▼
[2. RelationGraph 탐색 (weight ≥ 0.75)]
   │  감지 노드의 모든 관계 엣지 순회
   │  → 관련 노드의 display_name + tags 수집
   ▼
[3. 쿼리 확장]
   │  expanded_query = original_query + 관련 용어
   │  (중복 제거, 이미 포함된 용어 제외)
   ▼
[4. 필터 전략 결정]
   │  Intent + 감지 노드 기반으로 filter_types 결정
   │  (예: EXPRESSION → {spec, cli_spec, official_docs})
   ▼
[5. 온톨로지 힌트 생성]
   │  ANTI_PATTERN, RECOMMEND, CONSTRAINT, PATTERN, BEST-PRACTICE
   │  → ctx["ontology_hints"]로 서비스 프롬프트에 삽입
   ▼
[6. 오타 교정 정보 전파]                                    ← 신규
   │  typo_corrections → ctx["typo_corrections"]
   │  → 각 서비스의 LLM 시스템 프롬프트에 직접 주입
   │  → LLM이 오타를 실재 개념으로 오인하는 할루시네이션 차단
   ▼
[7. Ontology Reranking]
   │  RAG 검색 결과에 관련 노드 포함 여부로 boost (+0.15)
   └─ 재정렬된 chunks 반환
```

**퍼지 매칭 임계값 전략:**

| 자모/문자 길이 | 허용 편집 거리 | 근거 |
|:---:|:---:|---|
| ≤ 4 | 0 (정확 매칭만) | 너무 짧으면 오탐 위험 |
| 5 ~ 9 | 1 | 1글자 오타 허용 (ㅐ↔ㅔ, 된소리 혼동 등) |
| ≥ 10 | 2 | 긴 단어는 2글자 오타까지 허용 |

**추가 지연 시간:** 全 처리가 in-process Python 연산 (DB/HTTP 없음)  
→ 평균 쿼리 기준 ~2ms 추가 (453노드 × 80 KO키 × Levenshtein)

### 8.3 실제 확장 예시

```
입력: "슬랙으로 날씨 알림 보내는 HTTP Request 워크플로우 만들어줘"

감지 노드:
  - HTTP Request (weight=0.90 → Set, IF, Split In Batches)
  - Slack       (weight=0.85 → Schedule Trigger, IF)

관련 용어 추가:
  http, api, rest, request, integration, Set, IF,
  notification, message, team, schedule, cron

확장 쿼리:
  "슬랙으로 날씨 알림 보내는 HTTP Request 워크플로우 만들어줘
   http api rest request integration Set IF notification
   message team schedule cron automation"

패턴 감지: periodic_api_monitor
온톨로지 힌트:
  [PATTERN] 'periodic_api_monitor': 주기적 API 폴링 → 조건 분기 → 알림 패턴
  [BEST-PRACTICE] retryOnFail: true + maxTries: 3 on HTTP Request
  [BEST-PRACTICE] IF 노드로 정상/이상 응답 분기
  [ANTI-PATTERN] HTTP Request에 retryOnFail 미설정
```

### 8.4 온톨로지 힌트 + 오타 교정이 LLM 프롬프트에 삽입되는 방식

```python
# general_rag.py — GeneralRAGService.stream()
system = base_prompt.format(context=context_str)

# ① 온톨로지 관계 힌트 (ANTI-PATTERN / RECOMMEND / BEST-PRACTICE)
ontology_hints = ctx.get("ontology_hints") or []
if ontology_hints:
    system += "\n\n[온톨로지 힌트 — 답변 시 반드시 참고]\n" \
              + "\n".join(f"- {h}" for h in ontology_hints)

# ② 오타 교정 주입 — LLM 할루시네이션 차단
typo_corrections = ctx.get("typo_corrections") or []
if typo_corrections:
    lines = "\n".join(f"  - '{orig}' → {canon}" for orig, canon in typo_corrections)
    system += (
        "\n\n[⚠ 오타 자동 교정 — 매우 중요]\n"
        "사용자가 입력한 단어에 오타가 감지되어 아래와 같이 교정하였습니다.\n"
        + lines + "\n"
        "규칙:\n"
        "1. 오타 단어(교정 전)는 실제로 존재하지 않는 용어입니다. "
           "절대 별도 개념으로 설명하지 마십시오.\n"
        "2. '비공식 표현', '구어체', '약어' 등으로 정당화하지 마십시오.\n"
        "3. 교정된 공식 노드명만 기준으로 답변하십시오.\n"
        "4. 필요하다면 답변 첫 줄에 오타 인식을 한 줄 언급 후 본론으로 넘어가십시오."
    )
```

**주입 대상 서비스:** `GeneralRAGService`, `WorkflowBuildService`, `ExpressionService` — 세 서비스 모두 동일한 패턴으로 typo_corrections를 시스템 프롬프트에 주입한다.

### 8.5 ontology_context 이벤트 (XAI 투명성)

```
2:[{
  "type": "ontology_context",
  "detected_nodes": ["HTTP Request", "Slack"],
  "pattern": "periodic_api_monitor",
  "hints_count": 4
}]
```

사용자는 "어떤 노드가 감지되었고 어떤 패턴으로 처리 중인지"를 실시간으로 확인할 수 있다.

### 8.6 할루시네이션 방지 메커니즘 (Typo Correction Pipeline)

**문제 상황:** 사용자가 "앱훅이 뭐야?"(웹훅 오타)를 입력하면:
1. OntologyEnhancer가 오타를 감지 못함 → 잘못된 RAG 컨텍스트 검색
2. LLM이 원본 쿼리 "앱훅이"를 그대로 보고 "앱훅(App Hook)"이라는 존재하지 않는 개념을 창작

**이 이중 실패를 방지하는 두 계층의 방어:**

```
Layer 1 — RAG 검색 품질 (OntologyEnhancer Step 5/6)
  "앱훅이" → 자모 퍼지 매칭 → "webhook" 감지
  expanded_query에 webhook 관련 용어 추가 → 올바른 RAG 청크 검색

Layer 2 — LLM 인식 교정 (Typo Correction Injection)
  typo_corrections = [("앱훅", "Webhook")]
  → 시스템 프롬프트에 주입:
    "[⚠ 오타 자동 교정]
     '앱훅' → Webhook
     오타 단어는 실제로 존재하지 않는 용어입니다.
     절대 별도 개념으로 설명하거나 '비공식 표현'으로 정당화하지 마십시오."
  → LLM이 Webhook 기준으로 답변, 오타를 새 개념으로 오해하지 않음
```

**설계 원칙:**
- **LLM 미사용:** 오타 감지에 LLM을 투입하면 수백 ms 지연 발생 → 자모 Levenshtein으로 ~2ms
- **교정 정보 전파:** 감지(OntologyEnhancer)와 교정 주입(LLM 프롬프트)을 분리 — 각 레이어가 자신의 역할만 담당
- **오탐 방지:** edit_dist > 0인 경우만 교정으로 기록 (정확 매칭은 교정 아님)

**EnhancedQuery 데이터 구조:**

```python
@dataclass
class EnhancedQuery:
    original_query:    str
    expanded_query:    str                    # RAG 검색에 사용
    detected_nodes:    List[N8NNodeDef]       # Ontology Reranking에 사용
    related_node_terms: List[str]             # 쿼리 확장 용어
    filter_types:      Optional[Set[str]]     # RAG 필터
    pattern:           Optional[WorkflowPattern]
    ontology_hints:    List[str]              # LLM 프롬프트 힌트
    typo_corrections:  List[Tuple[str, str]]  # [(오타, 정식명)] ← 신규
```

---

## 9. 핵심 컴포넌트: 하이브리드 RAG 파이프라인

**파일:** `server/query_engine.py`, `server/workflow_services.py`

### 7.1 지식 베이스 구성

**청크 단위 설계**

모든 n8n 지식은 청크(Chunk) 단위로 분할·저장된다. 각 청크는 다음 메타데이터를 갖는다:

```json
{
  "chunk_global_id": "doc_001::0",
  "data_type": "spec",
  "title": "HTTP Request",
  "node_name": "HTTP Request",
  "source": "n8n_properties_spec.txt",
  "page_content": "# NODE DIRECTORY: HTTP Request\n...",
  "properties": [
    { "displayName": "URL", "name": "url", "type": "string", "default": "" },
    { "displayName": "Method", "name": "method", "type": "options", ... }
  ]
}
```

**Spec 청크 특수 처리**

`data_type: "spec"` 청크는 여러 노드 스펙을 포함하므로, 로드 시 `_expand_chunk()`가 노드별로 분리한다:

```
원본 spec 청크 (10개 노드 포함)
   → _parse_spec_sections() — NODE DIRECTORY 섹션 파싱
   → 10개 개별 청크 생성 (chunk_global_id: "base::0" ~ "base::9")
   → 각 청크에 properties 배열 포함
```

이는 BM25와 벡터 검색이 노드 단위로 정밀하게 동작하게 하기 위한 온톨로지 기반 분할 전략이다.

### 7.2 쿼리 재작성 (Query Rewriting)

한국어 질문을 영어 도메인 용어로 확장한다:

```python
사용자: "수식으로 루프 처리할 때 반복 멈추는 방법"

_DOMAIN_MAP 적용:
  "수식"  → "expression $json"
  "루프"  → "loop over items split in batches"
  "반복"  → "loop split in batches"

결과:
  ko_clean: "수식 루프 처리 반복 멈추는 방법"
  en_expanded: "expression $json loop over items split in batches"
  combined: "수식 루프 처리 반복 멈추는 방법 expression $json loop over items split in batches"
```

이 combined 쿼리가 BM25와 벡터 검색 모두에 입력된다.

### 7.3 BM25 검색 상세

```python
# 토크나이저: 한글 + 영문/숫자 분리
def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_.-]+|[가-힣]+", text.lower())

# 청크당 처리된 토큰 예시:
# "HTTP Request URL 파라미터 설정" → ["http", "request", "url", "파라미터", "설정"]

# BM25 점수 계산 (BM25Okapi)
scores = self._bm25.get_scores(query_tokens)

# 추가 정렬 기준 (_rank_key):
def _rank_key(base_score, chunk, query_tokens):
    exact     = Σ(t in haystack for t in query_tokens if len(t)≥2)
    node_hit  = Σ(t in node_name for t in query_tokens) × 3  # 노드명 3배 가중
    official  = 1 if data_type == "official_docs" else 0
    spec_b    = 1 if data_type == "spec" else 0
    return (base_score, exact + node_hit, official, spec_b)
```

**두 개의 BM25 인덱스:**
- 전체 인덱스 (`_bm25`): 모든 14,543개 청크
- Spec 전용 인덱스 (`_bm25_spec`): spec + official_docs + book 타입만

### 7.4 벡터 검색 상세

```python
# BGE-M3 임베딩 생성 (Ollama API)
embedding = httpx.post(
    f"{ollama_url}/api/embed",
    json={"model": "bge-m3:latest", "input": [query_text]}
).json()["embeddings"][0]  # 1024차원 벡터

# ChromaDB 쿼리
results = collection.query(
    query_embeddings=[embedding],
    n_results=20,
    include=["metadatas", "distances"]
)

# chunk_global_id → 인메모리 인덱스 매핑
# (spec 분리 시 생성된 청크가 메모리에는 있지만 ChromaDB에는 base_id만 있음)
for meta in results["metadatas"][0]:
    base_id = meta["chunk_global_id"]
    indices.extend(self._base_id_to_indices[base_id])
```

### 7.5 RRF 융합

```python
@staticmethod
def _rrf_merge(lists: list[list[int]], k: int = 60, top_k: int = 20) -> list[int]:
    scores: dict[int, float] = {}
    for ranked in lists:
        for rank, idx in enumerate(ranked):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda x: scores[x], reverse=True)[:top_k]

# 예시:
# BM25:   [42, 7, 103, ...]  (인덱스 순서)
# 벡터:   [7, 42, 88, ...]
#
# RRF score(7)  = 1/(60+1+1) + 1/(60+0+1) = 0.0161 + 0.0164 = 0.0325  ← 양쪽 상위
# RRF score(42) = 1/(60+0+1) + 1/(60+1+1) = 0.0164 + 0.0161 = 0.0325
# RRF score(103)= 1/(60+2+1) + 0           = 0.0157           ← BM25만
```

### 7.6 Intent별 RAG 필터 전략

| Intent | filter_types | top_n | 이유 |
|--------|-------------|-------|------|
| CURRICULUM(beginner) | {entry, beginner, official_docs, book} | 12 | 입문 수준 지식 소스만 |
| CURRICULUM(advanced) | {advanced, spec, troubleshooting, api_limits} | 12 | 고급 소스만 |
| EXPRESSION | {spec, cli_spec, official_docs} | 6 | 파라미터 스펙 정밀 검색 |
| WORKFLOW_BUILD | None (전체) | 8 | parent/child 체이닝 포함 |
| ERROR_PATCH | {troubleshooting, api_limits, spec} | 8 | 에러 해결 사례 우선 |
| REVERSE | {spec, official_docs} | 10 | 노드 스펙 참조 |
| GENERAL | None (전체) | 8 | 광범위 검색 |

### 7.7 CPU 격리 전략 (ProcessPoolExecutor)

BM25 연산은 CPU 바운드이므로, FastAPI의 asyncio 이벤트 루프를 차단하지 않도록 분리 실행된다:

```python
_bm25_executor = ProcessPoolExecutor(max_workers=2)

async def _rag_with_filter(...):
    loop = asyncio.get_running_loop()
    try:
        chunks = await loop.run_in_executor(
            _bm25_executor,           # CPU 격리 프로세스
            partial(_sync_retrieve, engine, query, filter_types, top_n)
        )
    except Exception:
        chunks = await loop.run_in_executor(
            None,                     # 스레드풀 폴백
            partial(_sync_retrieve, ...)
        )
```

이 설계로 BM25 연산 중에도 다른 요청을 처리할 수 있다.

---

## 10. 핵심 컴포넌트: 온톨로지 기반 커리큘럼 엔진

**파일:** `server/workflow_services.py` — `CurriculumService`

### 8.1 동적 레벨 감지 알고리즘

학습 수준 감지는 단일 메시지가 아니라 **최근 대화 히스토리를 포함**한 복합 입력으로 수행된다:

```python
def _detect_level(message: str, history: list | None = None) -> str:
    candidates = [message]
    if history:
        for turn in history[:3]:  # 최근 3턴 포함
            candidates.append(turn.content)
    
    combined = " ".join(candidates)
    
    # 패턴 우선순위: 명시적 > 암묵적
    for level, pattern in _LEVEL_PATTERNS.items():
        if pattern.search(combined):
            return level
    
    return "beginner"  # 기본값 (안전한 방향)

_LEVEL_PATTERNS = {
    "beginner":     r"입문|초급|처음|기초|시작|beginner|basic|모르|아무것도|zero",
    "intermediate": r"중급|어느\s*정도|좀\s*할\s*줄|intermediate|배운|써봤|경험",
    "advanced":     r"고급|심화|전문|advanced|잘\s*함|능숙|프로|expert|깊게",
}
```

### 8.2 온톨로지 기반 RAG 필터링

감지된 레벨이 학습 수준 온톨로지를 통해 지식 소스 타입으로 매핑된다:

```python
_LEVEL_TO_RAG_FILTER = {
    "beginner":     {"entry", "beginner", "official_docs", "book"},
    "intermediate": {"intermediate", "official_docs", "book", "spec"},
    "advanced":     {"advanced", "spec", "troubleshooting", "api_limits"},
}
```

이 매핑의 설계 근거:
- **beginner**: 어려운 스펙(spec)을 피하고 공식 문서와 교재 위주
- **intermediate**: 스펙 일부 포함하여 파라미터 이해 심화
- **advanced**: 스펙 + troubleshooting으로 실전 문제 해결 중심

### 8.3 커리큘럼 JSON 파싱 및 폴백 전략

LLM이 JSON 배열을 생성 실패할 경우를 대비한 3단계 파싱:

```python
def _extract_json_array(self, text: str) -> list[dict] | None:
    # 1차: ```json ... ``` 블록 추출
    m = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    candidate = m.group(1).strip() if m else text.strip()
    
    try:
        arr = json.loads(candidate)
        return arr if isinstance(arr, list) else None
    except json.JSONDecodeError:
        return None

def _normalize_cards(self, raw_cards) -> list[dict]:
    if not raw_cards:
        return self._default_cards()  # 3개 기본 카드 폴백
    # 정상 파싱 시 카드 정규화
```

폴백 카드는 코드에 하드코딩된 beginner/intermediate/advanced 각 1주차 카드로, 시스템이 절대 빈 응답을 반환하지 않도록 보장한다.

---

## 11. 핵심 컴포넌트: 다층 사후 검증 파이프라인

**파일:** `server/reg_validator.py` (Stage 1) + `server/semantic_validator.py` (Stage 2-4)  
**이론적 분류:** 다단계 사후 생성 검증 (Multi-stage Post-Generation Verification)

### 11.0 파이프라인 개요

LLM이 생성한 출력은 4단계 검증 파이프라인을 통과한다:

```
LLM 생성 출력 (raw text)
        │
  Stage 1: REG (reg_validator.py)
        │  파라미터 오타 Levenshtein 수정
        │  $json.retryOnFai → $json.retryOnFail
        │
  Stage 2: Structural Validation (semantic_validator.py)
        │  JSON 스키마 준수 (nodes, connections 존재)
        │  connections 참조 무결성 (노드명 유효)
        │  필수 필드 검사 (type, position)
        │
  Stage 3: Property Constraint Validation
        │  온톨로지 PropertyConstraints 적용
        │  retryOnFail → maxTries REQUIRED 검사
        │  code jsCode 내 $item() FORBIDDEN 검사
        │
  Stage 4: Relation Pattern Validation + Expression Semantics
           Merge 노드 다중 입력 검사
           Webhook responseNode → Respond to Webhook 존재 검사
           Code 노드 내 직접 HTTP 호출 Anti-pattern 감지
           $node["NodeName"] 참조 무결성

결과: ValidationReport → validation_report SSE 이벤트
```

### 11.1 Stage 1: REG (Rule-based & Embedding-Grounded Validation)

**파일:** `server/reg_validator.py`  
**이론적 분류:** 사후 생성 검증 (Post-Generation Verification)

### 9.1 REG의 필요성

LLM은 n8n 파라미터명을 다음과 같이 잘못 생성하는 경향이 있다:

| LLM 생성 (오류) | 올바른 값 | 편집 거리 | 원인 |
|----------------|---------|---------|------|
| `retryOnFai` | `retryOnFail` | 1 | 마지막 문자 누락 |
| `batchsize` | `batchSize` | 1 | 대소문자 오류 |
| `responseformat` | `responseFormat` | 1 | camelCase 오류 |
| `waitBetweenRequest` | `waitBetweenRequests` | 1 | 복수형 누락 |
| `jsonParams` | `jsonParameters` | 5 | 축약형 혼용 |

이런 오류가 n8n 캔버스에 주입되면 실행 실패로 이어진다.

### 9.2 REG 활성화 조건

```python
# workspace.py
_REG_REQUIRED_INTENTS = {Intent.WORKFLOW_BUILD, Intent.EXPRESSION, Intent.ERROR_PATCH}

if intent in _REG_REQUIRED_INTENTS and token_buffer:
    full_text = "".join(token_buffer)
    fixed_text, corrections = reg.validate_and_fix(full_text)
    if corrections:
        yield ai_data([{"type": "reg_warning", **warning}])
```

GENERAL과 CURRICULUM, REVERSE는 REG를 적용하지 않는다. 코드를 생성하지 않는 서비스이기 때문이다.

### 9.3 검증 알고리즘 상세

```python
# 1단계: 표현식 내 필드명 스캔
_EXPR_FIELD_RE = re.compile(
    r'\{\{\s*\$(?:json|node\["[^"]+"\]\.json)\.([a-zA-Z_][a-zA-Z0-9_.]*)'
)
# 예: {{ $json.retryOnFai }} → "retryOnFai" 추출

# 2단계: JSON 코드 블록 내 키 스캔
_JSON_KEY_RE = re.compile(r'"([a-zA-Z_][a-zA-Z0-9_]{2,})"(?:\s*:)')
# 예: "retryOnFai": true → "retryOnFai" 추출

# 3단계: 유효 속성 세트와 대조
if field not in valid_properties and len(field) >= 3:
    suggestion = _best_match(field, sorted_props, max_dist=2)

# 4단계: Levenshtein 거리 계산
def _levenshtein(s, t) -> int:
    # DP, O(mn), 공간 절약형 두 행 버퍼
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        curr[0] = i
        for j in range(1, n + 1):
            cost = 0 if s[i-1] == t[j-1] else 1
            curr[j] = min(prev[j]+1, curr[j-1]+1, prev[j-1]+cost)
        prev, curr = curr, [0]*(n+1)
    return prev[n]

# 5단계: In-place 치환
fixed = text.replace(f"$json.{field}", f"$json.{suggestion}", 1)
```

### 9.4 유효 속성 세트 로드 전략

```
1차: n8n_properties_spec.txt 파싱 → "- name: parameterName" 추출
  └→ 성공 시: 파싱된 세트 ∪ 하드코딩 코어 세트
  └→ 실패 시:
2차: 하드코딩된 _CORE_VALID_PROPERTIES 폴백 (~60개 핵심 파라미터)
```

모듈 임포트 시 1회만 로드하므로 매 요청마다 파일 I/O가 발생하지 않는다.

### 11.2 Stage 2: 구조적 검증 (StructuralValidation)

**파일:** `server/semantic_validator.py` — `_stage1_structural()`

```
검증 항목:
  ① nodes, connections 최상위 필드 존재 여부
  ② connections 소스 노드명이 nodes에 존재하는지
  ③ connections 대상 노드명이 nodes에 존재하는지
  ④ 각 노드에 type 필드 존재 여부
  ⑤ position 필드 존재 여부 (INFO 수준)
```

**예시 발견 케이스:**
```json
{
  "nodes": [{"name": "HTTP Request", "type": "..."}],
  "connections": {"Schedule Trigger": {"main": [[{"node": "HTTP Request"}]]}}
}
```
→ "Schedule Trigger" 소스 노드가 nodes에 없음 → ERROR

### 11.3 Stage 3: 속성 제약 검증 (PropertyConstraintValidation)

**파일:** `server/semantic_validator.py` — `_stage2_property_constraints()`

domain_ontology.PropertyConstraints 11개 규칙을 각 노드 parameters에 대조:

```python
# 실제 실행 예:
node = {"name": "Call API", "type": "n8n-nodes-base.httpRequest",
        "parameters": {"retryOnFail": True}}  # maxTries 없음

constraints = get_constraints_for_node("httpRequest")
# → PropertyConstraint(retryOnFail, REQUIRES, maxTries, WARNING)
# → pval=True, related_property="maxTries" not in params
# → ValidationIssue(stage="property", severity=WARNING,
#     message="`retryOnFail: true` 설정 시 `maxTries`를 반드시 지정해야 합니다.")
```

### 11.4 Stage 4: 관계·패턴·표현식 검증 (RelationPatternValidation)

**파일:** `server/semantic_validator.py` — `_stage3_relation_pattern()`, `_stage4_expression_semantics()`

**Stage 3 검증 항목:**
```
① Merge 노드: connections에서 해당 노드로의 입력이 2개 이상인지
② Webhook responseMode=responseNode: Respond to Webhook 노드 존재 여부
③ Code 노드 jsCode에 fetch() / axios 포함 (Anti-pattern)
```

**Stage 4 표현식 검증:**
```
① $item() 패턴 감지 → ERROR (n8n v1.x 폐기 구문)
② $node["NodeName"] 참조에서 NodeName이 nodes에 존재하는지
```

### 11.5 ValidationReport → validation_report 이벤트

```python
@dataclass
class ValidationReport:
    is_valid:   bool
    issues:     List[ValidationIssue]  # errors + warnings + infos
    pattern:    Optional[WorkflowPattern]  # 감지된 패턴
    best_practices: List[str]

    def to_sse_payload(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "error_count":   len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [...],
            "pattern":        self.pattern.name if self.pattern else None,
            "best_practices": self.best_practices,
        }
```

**SSE 이벤트 (에러·경고 존재 시에만 발행):**
```
2:[{
  "type": "validation_report",
  "is_valid": false,
  "error_count": 1,
  "warning_count": 2,
  "issues": [
    {"stage": "property", "severity": "warning", "node": "Call API",
     "property": "retryOnFail",
     "message": "`retryOnFail: true` 설정 시 `maxTries`를 반드시 지정해야 합니다.",
     "suggestion": "`maxTries`를 parameters에 추가하세요."},
    {"stage": "pattern",  "severity": "error",   "node": "Merge",
     "message": "Merge 노드의 입력 연결이 1개입니다. 최소 2개 필요합니다."}
  ],
  "pattern": "periodic_api_monitor",
  "best_practices": [
    "retryOnFail: true + maxTries: 3 on HTTP Request",
    "IF 노드로 정상/이상 응답 분기"
  ]
}]
```

### 11.6 4단계 검증 활성화 조건

```python
_REG_REQUIRED_INTENTS  = {WORKFLOW_BUILD, EXPRESSION, ERROR_PATCH}   # Stage 1
_SEM_VALIDATE_INTENTS  = {WORKFLOW_BUILD, ERROR_PATCH}               # Stage 2-4
```

| Intent | Stage 1 (REG) | Stage 2-4 (Semantic) | 이유 |
|--------|-------------|---------------------|-----|
| WORKFLOW_BUILD | O | O | 코드 생성 + 워크플로우 JSON |
| EXPRESSION | O | X | 코드 생성하지만 구조 JSON 없음 |
| ERROR_PATCH | O | O | 코드 생성 + 패치 JSON |
| GENERAL | X | X | 코드 생성 없음 |
| CURRICULUM | X | X | JSON 배열만 생성 |
| REVERSE | X | X | 입력 JSON 분석, 생성 아님 |

---

## 12. 핵심 컴포넌트: 구조화 출력 계약 (SOC)

**이론적 분류:** 프롬프트 엔지니어링 기반 출력 형식 강제

### 10.1 SOC의 개념

구조화 출력 계약(Structured Output Contract, SOC)은 LLM에게 시스템 프롬프트를 통해 엄격한 출력 형식을 지정하는 기법이다. LLM을 단순 텍스트 생성기가 아니라 **구조화 데이터 생성 API**로 활용한다.

### 10.2 서비스별 SOC 정의

**CURRICULUM SOC — JSON 배열**

```
[STRICT RULE] 반드시 JSON 배열을 출력할 것.
각 카드 스키마:
{
  "week": "Week N",
  "level": "beginner|intermediate|advanced",
  "title": "학습 단계 제목",
  "objectives": ["목표1", "목표2"],
  "nodes": ["사용 노드 목록"],
  "canvas_code_id": "실습 코드 ID",
  "duration": "45m|60m|90m"
}
```

**EXPRESSION SOC — 정형 마크다운**

```
## 생성된 표현식
### 표현식 1
```{{ $json.fieldName }}```
**설명**: ...
**언제 사용**: ...
## 사용 방법
1. ...
## 주의사항
```

**WORKFLOW_BUILD SOC — 정형 마크다운 + JSON 코드 블록**

```
## 워크플로우 설계 — [제목]
## 전체 흐름
[1] 노드명 → [2] 노드명 → [3] 노드명
## 노드별 설명
### 1. [노드명] (`타입`)
...
## n8n JSON 코드
```json
{ "nodes": [...], "connections": {...} }
```
## 최적화 권고
## 배포 체크리스트
```

**REVERSE SOC — JSON 배열 (3층 아코디언)**

```json
[
  { "layer": "summary", "title": "전체 요약", "content": "..." },
  { "layer": "nodes", "title": "노드별 역할", "items": [
      { "node_name": "...", "type": "...", "layer": "trigger|processing|sink",
        "role": "...", "key_params": [...], "warning": "..." }
  ]},
  { "layer": "expressions", "title": "Expression 해설", "items": [...] }
]
```

**ERROR_PATCH SOC — 정형 마크다운 + 코드 블록**

```
## 에러 진단
**에러 유형:** ...
**발생 원인:** ...
## 원인 분석
## 해결 방법
### 방법 1: ...
## 패치 코드
```json { ... } ```
## 즉시 캔버스 적용 가능: YES/NO
## 재발 방지
```

### 10.3 공통 SOC 규칙 (모든 서비스 적용)

```
[STRICT RULE] Do NOT use any emoji or unicode decorative symbols.
- 이모지 절대 금지 (🚀💡✨ 등)
- 순수 마크다운만 사용
- 노드명/파라미터명: 영문 원문 + 백틱 형식 (e.g., `retryOnFail`)
- 제품명: 반드시 **n8n** (nn, N8N 금지)
- 컨텍스트 외 내용: "확인되지 않습니다" 명시 (LEG 원칙)
- 코드: 반드시 ```json 또는 ```javascript 블록
```

**LEG(Lexical Evidence Grounding) 원칙:** 모든 기술적 사실은 RAG가 제공한 청크에 근거해야 한다. LLM이 자신의 파라미터 기억에만 의존하는 것을 프롬프트 수준에서 금지한다.

---

## 13. 다층 환각 억제 프레임워크

Naito는 **5단계**에서 LLM 환각을 억제한다.

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 0: Pre-Retrieval (검색 전 지식 구조화)                    │
│                                                                 │
│  0-A. 도메인 온톨로지 — 노드 관계·제약·패턴 형식 명세            │
│  0-B. OntologyEnhancer — 쿼리에서 노드 감지 + 관련 용어 확장     │
│  0-C. 패턴 감지 — 워크플로우 패턴 매칭 → best_practices 수집     │
│  0-D. 온톨로지 힌트 → ctx["ontology_hints"]로 하위 레이어 전달   │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: Pre-Generation (생성 전 그라운딩)                      │
│                                                                 │
│  1-A. 쿼리 재작성 — 한국어 → 영어 도메인 용어 확장               │
│  1-B. 하이브리드 RAG — 14,543개 청크에서 검증된 사실 추출         │
│  1-C. 의도별 필터 — 관련 지식 소스 타입만 선택                   │
│  1-D. Ontology Reranking — 관련 노드 포함 청크 boost 재정렬      │
│  1-E. RAG + 온톨로지 힌트 삽입 — 검증된 지식 + 관계 패턴 주입    │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: In-Generation (생성 중 제약)                          │
│                                                                 │
│  2-A. SOC 시스템 프롬프트 — 출력 형식 강제                       │
│  2-B. LEG 원칙 — "컨텍스트 외 내용 금지" 명시                   │
│  2-C. RULE 태그 — 표현식 문법 규칙 ($item() 사용 금지 등)        │
│  2-D. 멀티턴 히스토리 — 이전 응답 맥락으로 일관성 유지            │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: Post-Generation Stage 1 — REG (어휘 수준 수정)        │
│                                                                 │
│  3-A. 파라미터 오타 감지 — $json.xxx, JSON 키 스캔               │
│  3-B. Levenshtein(dist≤2) 자동 수정 — n8n_properties_spec 대조  │
│  3-C. reg_warning 이벤트 — 수정 내역 즉시 공개 (XAI)            │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 4: Post-Generation Stage 2-4 — Semantic (의미 수준 검증) │
│                                                                 │
│  4-A. 구조 검증 — JSON 스키마, connections 참조 무결성           │
│  4-B. 속성 제약 검증 — 11개 PropertyConstraints 규칙 적용        │
│  4-C. 관계·패턴 검증 — Merge 다중입력, Webhook 응답노드 등        │
│  4-D. 표현식 의미 검증 — $item() 폐기 구문, 노드명 참조 무결성    │
│  4-E. validation_report 이벤트 — 모든 이슈 공개 (XAI)           │
└─────────────────────────────────────────────────────────────────┘
```

### 13.0 Layer 0 → Layer 4 데이터 흐름

```
사용자 쿼리
    │
    ▼ [Layer 0] OntologyEnhancer.enhance()
    │   expanded_query, detected_nodes, ontology_hints, pattern
    │
    ▼ [Layer 1] HybridRetriever (확장된 쿼리)
    │   + Ontology Reranking (감지 노드 기반 boost)
    │   chunks (RAG) + hint_block (온톨로지 힌트)
    │
    ▼ [Layer 2] LLM (SOC + LEG + RAG컨텍스트 + 온톨로지 힌트)
    │   raw_output
    │
    ▼ [Layer 3] REG validate_and_fix()
    │   fixed_text, corrections → reg_warning 이벤트
    │
    ▼ [Layer 4] SemanticValidator.validate()
        ValidationReport → validation_report 이벤트
```

### 13.1 Layer 1 상세: RAG 컨텍스트 삽입

```python
# 검색된 청크를 프롬프트용 텍스트로 변환
def _build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        dtype  = c.get("data_type", "?")
        title  = c.get("title", "")
        source = c.get("source", "")
        text   = c.get("text", "")[:1500]  # 토큰 절약
        parts.append(f"[{i}][{dtype.upper()}] {title} ({source})\n{text}")
    return "\n\n---\n\n".join(parts)
```

출력 예시:
```
[1][SPEC] HTTP Request (n8n_properties_spec.txt)
- displayName: URL
- name: url
- type: string
...

---

[2][OFFICIAL_DOCS] HTTP Request — Error Handling (docs.n8n.io)
Use `retryOnFail` to automatically retry failed requests...
```

### 11.2 Layer 2 상세: RULE 태그

`_EXPRESSION_SYSTEM_PROMPT`의 문법 규칙:

```
## 표현식 문법 절대 규칙 (RULE-04)
- 현재 노드: {{ $json.fieldName }}
- 이전 노드: {{ $node["노드명"].json.fieldName }}
- 배열 첫 번째: {{ $json.items[0].field }}
- 금지: $item(), .item.json → n8n v1.x에서 폐기됨
```

`_WORKFLOW_BUILD_SYSTEM_PROMPT`의 최적화 규칙:

```
## 최적화 권고 (해당 시)
- 대량 처리: `Split In Batches` 사용 필수 (RULE-01)
- API 제한: `Retry On Fail` + `Wait Between Tries` 설정 (RULE-03)
```

### 11.3 Layer 3 상세: 오류 처리 사례

**케이스 1: 표현식 오타**
```
LLM 생성: "{{ $json.retryOnFai }}"
REG 감지: "retryOnFai" 가 valid_properties 에 없음
Levenshtein("retryOnFai", "retryOnFail") = 1 ≤ 2
수정 결과: "{{ $json.retryOnFail }}"
이벤트: reg_warning { original: "retryOnFai", corrected: "retryOnFail", distance: 1 }
```

**케이스 2: JSON 키 오타**
```
LLM 생성: { "batchsize": 10 }
REG 감지: "batchsize" 가 valid_properties 에 없음
Levenshtein("batchsize", "batchSize") = 1 ≤ 2
수정 결과: { "batchSize": 10 }
```

**케이스 3: 폴백 (편집 거리 초과)**
```
LLM 생성: { "maximumRetryCount": 3 }
Levenshtein("maximumRetryCount", "maxTries") = 9 > 2
→ 수정 불가, 경고 없이 원문 유지
```

### 11.4 환각 억제 효과 비교

| 입력 시나리오 | Raw LLM | Naito (3-Layer) |
|-------------|---------|----------------|
| n8n 파라미터명 정확도 | 낮음 (훈련 데이터 의존) | 높음 (spec 기반 + REG 수정) |
| 표현식 문법 정확도 | 중간 (문법 기억 불안정) | 높음 (RULE-04 강제) |
| 워크플로우 구조 타당성 | 중간 (임의 생성) | 높음 (RAG 코드 뼈대 + SOC) |
| 출처 명시 | 없음 | 있음 (data_type, source 포함) |
| 오타 자동 수정 | 없음 | 있음 (REG Levenshtein) |

---

## 14. 설명 가능성(XAI) 설계 원칙

### 12.1 의사결정 추적 가능성

모든 주요 의사결정이 이벤트로 클라이언트에 전달된다:

| 결정 | 이벤트 타입 | 내용 |
|------|-----------|------|
| 의도 분류 결과 | `intent` | `{ intent: "WORKFLOW_BUILD", label: "워크플로우 설계/최적화" }` |
| 학습 수준 감지 | `intent` (curriculum) | `{ curriculum_level: "beginner", weeks: 4 }` |
| 에러 감지 | `error_alert` | `{ tokens: ["HTTP 404", ...], message: "에러 감지: ..." }` |
| REG 자동 수정 | `reg_warning` | `{ corrections: [{ original: "...", corrected: "..." }] }` |

### 12.2 소스 귀속성 (Source Attribution)

RAG 컨텍스트에는 소스 정보가 포함되어 있고, 이는 프롬프트를 통해 LLM에 전달된다:

```
[2][OFFICIAL_DOCS] HTTP Request Error Handling (docs.n8n.io/...)
...
```

LEG 원칙에 의해 LLM은 "이 내용은 [검색된 컨텍스트]에 근거합니다"라고 표시하도록 유도된다.

### 12.3 결정 경로 감사 (Decision Audit Trail)

매 요청마다 `requestLog` 테이블에 다음이 저장된다:

```sql
requestLog {
  intent          -- 어떤 경로로 처리됐는가
  intentLabel     -- 사람이 읽을 수 있는 레이블
  model           -- 어떤 LLM이 사용됐는가
  latencyMs       -- 얼마나 걸렸는가
  priorMessageCount -- 컨텍스트에 몇 번의 대화가 있었는가
  hasStructuredPayload -- 구조화 이벤트가 있었는가
  structuredPayloads -- 어떤 구조화 데이터가 생성됐는가
  responseLength  -- 응답이 얼마나 길었는가
}
```

이 로그로 "어떤 질문이 어떤 경로로 처리되어 어떤 응답을 생성했는가"를 사후에 완전히 재현할 수 있다.

### 12.4 실시간 투명성 이벤트 시퀀스

```
사용자 메시지 전송
      │
  t=0ms  2:[{"type":"intent","intent":"WORKFLOW_BUILD"}]
      │         ← 사용자가 즉시 "무슨 처리 중"인지 안다
      │
  t=600ms  0:"## 워크플로우 설계..."  (스트리밍 시작)
      │         ← 사용자가 LLM 생성 과정을 실시간으로 본다
      │
  t=5000ms  2:[{"type":"card","type":"workflow_inject",...}]
      │         ← 구조화 데이터 도착 알림
      │
  t=5001ms  2:[{"type":"reg_warning","corrections":[...]}]
      │         ← "이 파라미터가 자동 수정되었습니다"
      │
  t=5002ms  d:{"finishReason":"stop"}
```

---

## 15. 세션 컨텍스트 관리와 꼬리 물기 추론

**파일:** `server/session.py`

### 13.1 세션 데이터 구조

```python
class ConversationTurn:
    role: str         # "user" | "assistant"
    content: str      # 메시지 본문
    intent: str | None  # 해당 턴의 Intent (user 턴만)
    meta: dict        # 추가 메타 (확장용)

class WorkflowSnapshot:
    session_id: str
    workflow_json: str   # 마지막 처리된 워크플로우 JSON
    operation: str       # 수행 작업명
    timestamp: float     # Unix timestamp (TTL 계산용)
```

### 13.2 히스토리 관리 정책

| 항목 | 값 | 이유 |
|------|-----|------|
| 최대 세션 보관 턴 | 20턴 | 메모리 사용량 제한 |
| LLM에 전달하는 최근 턴 | 10턴 | 컨텍스트 창 효율 |
| user 턴 최대 길이 | 400자 | 불필요한 토큰 절약 |
| assistant 턴 최대 길이 | 4000자 | 이전 답변 최대한 보존 |
| 마지막 assistant 턴 | 무제한 | 직전 답변은 완전 보존 |
| Snapshot TTL | 3600초 | 메모리 자동 정리 |

### 13.3 꼬리 물기 추론 메커니즘

단일 메시지만으로 정확한 처리가 불가능한 후속 질문을 감지하고 보강한다:

**① Intent 이어받기**

```python
# history에서 가장 최근 user 턴의 intent 추출
def _last_intent(self, history) -> Intent | None:
    for turn in reversed(history):
        intent_val = turn.intent
        if intent_val:
            return Intent(intent_val)
    return None
```

"더 자세히 알려줘" → 이전 WORKFLOW_BUILD → WORKFLOW_BUILD 서비스로 다시 라우팅

**② RAG 쿼리 강화**

```python
# 짧은 후속 질문(30자 미만)에 이전 user 메시지를 앞에 붙임
if prior_history and len(message) < 30:
    last_user = get_last_user_content(prior_history)[:120]
    rag_query = f"{last_user} {message}"
```

"그 노드 예시 보여줘" → "HTTP Request 노드로 외부 API 호출 예시 보여줘" (강화됨)

**③ 멀티턴 LLM 컨텍스트**

```python
messages = [
    { "role": "system",    "content": system_prompt },
    { "role": "user",      "content": "이전 질문..." },     # history[-2]
    { "role": "assistant", "content": "이전 응답..." },     # history[-1]
    { "role": "user",      "content": "더 자세히 알려줘" }, # 현재
]
```

LLM이 "더 자세히"가 무엇을 가리키는지 대화 맥락에서 이해할 수 있다.

---

## 16. LLM 라우팅 아키텍처 (BYOK 포함)

**파일:** `server/workflow_services.py` — `_stream_llm()`

### 14.1 라우팅 결정 트리

```
_stream_llm(model, openai_api_key, ...) 호출
      │
      ├─ model.startswith("openai:") ?
      │      │
      │      ├─ AND openai_api_key 있음
      │      │         → _stream_openai() 호출 (OpenAI API 직접)
      │      │
      │      └─ AND openai_api_key 없음
      │                → "API 키를 입력해 주세요" 메시지 반환
      │
      └─ Ollama 경로
             │
             ├─ /api/tags 확인 → 설치된 모델 목록 조회
             ├─ 사용자 선택 모델 있으면 → 해당 모델 사용
             └─ 없으면 → settings.llm_model 폴백
```

### 14.2 Ollama 스트리밍 설정

```python
async with httpx.AsyncClient() as client:
    async with client.stream("POST", f"{ollama_url}/api/chat", json={
        "model":      model,
        "messages":   _build_messages(system, history, user),
        "stream":     True,
        "keep_alive": "1h",       # 모델 메모리 유지 (콜드 스타트 방지)
        "options": {
            "num_predict": 8192,  # 최대 생성 토큰
        }
    }) as resp:
        async for line in resp.aiter_lines():
            if not line.strip():
                continue
            data = json.loads(line)
            token = data.get("message", {}).get("content", "")
            if token:
                yield token
            if data.get("done"):
                break
```

**타임아웃 전략:**
- per-attempt: 180초
- 전체 deadline: 300초 (5분)
- max attempts: 2

### 14.3 OpenAI BYOK 흐름

```
① 브라우저: useLocalStorage("openai_api_key") 저장
   (usehooks-ts가 JSON 직렬화: "sk-proj-..." → '"sk-proj-..."')

② 메시지 전송 시:
   localStorage.getItem("openai_api_key")  → '"sk-proj-..."' (이중 직렬화)
   JSON.parse(raw)                          → "sk-proj-..." (정상 값)

③ Next.js → FastAPI:
   body: { openai_api_key: "sk-proj-..." }

④ FastAPI → OpenAI:
   AsyncOpenAI(api_key="sk-proj-...")
   client.chat.completions.create(model="gpt-4o", stream=True, ...)
```

**보안 설계:**
- API 키는 클라이언트 localStorage에만 보관
- 서버 DB에 절대 저장하지 않음
- 매 요청마다 클라이언트가 직접 전송

### 14.4 모델 목록

```typescript
// lib/ai/models.ts

// Ollama (서버 내장, 무료)
{ id: "gemma4-e4b:latest", name: "gemma4-e4b", provider: "ollama" }
{ id: "qwen3.6:35b-a3b",   name: "qwen3.6:35b", provider: "ollama" }

// OpenAI BYOK (사용자 부담)
{ id: "openai:gpt-4o",      name: "GPT-4o",      provider: "openai" }
{ id: "openai:gpt-4o-mini", name: "GPT-4o mini", provider: "openai" }
{ id: "openai:gpt-4.1",     name: "GPT-4.1",     provider: "openai" }
```

---

## 17. 응답 스트리밍 프로토콜

### 15.1 3단계 변환 체계

```
FastAPI Service Layer          workspace.py          Next.js route.ts          Browser
      │                            │                       │                      │
  SSE 포맷                   AI SDK Stream              UI 청크               React State
      │                            │                       │                      │
event: token              →    0:"텍스트"\n      →   text-delta         →   messages[]
data: "텍스트"                                                                    업데이트
                                                                                  │
event: curriculum         →    2:[{type:"curriculum"  text-start/end    →   커리큘럼 카드
data: {cards:[...]}              cards:[...]}]\n    data-curriculum         UI 렌더링
                                                                                  │
event: done               →    d:{"finishReason"   finish-step/finish  →   SWR mutate()
                                  :"stop"}\n                                채팅 목록 갱신
```

### 15.2 AI SDK 스트림 포맷 명세

| 줄 접두사 | 형식 | 의미 |
|----------|------|------|
| `0:` | `0:"텍스트"\n` | 텍스트 델타 (JSON 인코딩된 문자열) |
| `2:` | `2:[{...}, ...]\n` | 구조화 데이터 배열 |
| `d:` | `d:{"finishReason":"stop"}\n` | 스트림 종료 |

### 15.3 구조화 이벤트 타입 전체 목록

| type | 발신 시점 | 데이터 내용 | 브라우저 처리 |
|------|---------|-----------|-------------|
| `intent` | Intent 분류 직후 | `{ intent, label }` | 의도 레이블 표시 |
| `curriculum` | 커리큘럼 생성 완료 | `{ cards: [...] }` | 주차별 카드 그리드 렌더링 |
| `expression` | 수식 생성 완료 | `{ raw_expression, node_type, insert_hint }` | 수식 카드 + 복사 버튼 |
| `card` | 워크플로우/패치 생성 완료 | `{ type: "workflow_inject"\|"error_patch_apply", ... }` | 액션 버튼 카드 |
| `error_alert` | 에러 토큰 추출 직후 | `{ type: "interrupt", tokens: [...] }` | 즉시 에러 배너 표시 |
| `report` | 역분석 완료 | `{ summary, node_roles, expressions }` | 3층 아코디언 UI |
| `reg_warning` | REG 검증 완료 | `{ corrections: [...] }` | 수정 내역 알림 |

### 15.4 필터링 정책 (의도적으로 숨기는 타입)

```typescript
// route.ts - toStructuredUiChunks()
if (
  type === "thinking"         ||  // 내부 추론 (사용자에게 불필요)
  type === "node_property"    ||  // 노드 속성 내부 메타
  type === "node_property_card" ||
  type === "intermediate"         // 중간 처리 결과
) {
  return [];  // 브라우저로 전달하지 않음
}
```

---

## 18. 의도별 처리 흐름 전체 추적 (7가지 예시)

---

### 예시 1 — GENERAL: "보통 사람들이 잘 모르는 유용한 n8n 노드 알려줘"

**Intent 분류:**
```
규칙 1(에러 로그)·2(JSON)·3(꼬리 물기, 첫 메시지라 history 없음) 모두 미해당
→ 키워드 추정: 매칭 없음 (None)
→ LLM 분류 호출 → "GENERAL" 반환
→ 키워드 추정도 None이라 구제할 대상 없음 → GENERAL 그대로 채택
```

**RAG 검색:**
```
_expand_query("...n8n 노드"):
  "노드" → NODE, "n8n" → n8n
  영어 노드명 패턴: r"([A-Za-z]+)노드" 미매칭
  → combined: "잘 모르는 유용한 n8n 노드"

_looks_like_node_question(): "노드" 포함 → True
  → _NODE_DETAIL_SYSTEM_PROMPT 사용
  → retrieve_spec() 호출 (spec 전용 인덱스)

BM25: "유용한", "n8n", "노드" 토큰 검색
  → 관련 spec/official_docs 청크 상위 반환
벡터: "hidden useful n8n nodes" 유사 임베딩
  → 사용 빈도 낮지만 강력한 노드 문서 반환
RRF → top-10 리랭킹
_rerank_node_chunks(): 노드명 매칭 청크 상위
```

**LLM (Ollama, 스트리밍):**
```
system: _NODE_DETAIL_SYSTEM_PROMPT + RAG 컨텍스트
user: "보통 사람들이 잘 모르는 유용한 n8n 노드를 설명해줘"
history: (없음)

→ 토큰 단위 스트리밍
→ yield sse("token", token) 반복
```

**출력 이벤트 시퀀스:**
```
2:[{"type":"intent","intent":"GENERAL","label":"일반 RAG Q&A"}]
0:"## " → 0:"Split" → 0:" Out" → 0:" 노드" ...  (스트리밍)
d:{"finishReason":"stop"}
```

**소요 시간:** ~600ms (RAG) + ~15초 (LLM 스트리밍)

---

### 예시 2 — WORKFLOW_BUILD: "슬랙으로 매일 오전 9시에 날씨 알림 보내는 워크플로우 만들어줘"

**Intent 분류:**
```
규칙 1~3 모두 미해당
→ 키워드 추정: "만들어줘" + "워크플로우" 동시 포함 → WORKFLOW_BUILD (안전망 대기)
→ LLM 분류 호출 → "WORKFLOW_BUILD" 반환
  (few-shot 예시 "슬랙 알림 자동화 만들어줘 → WORKFLOW_BUILD"와 같은 패턴)
→ LLM 결과가 GENERAL이 아니므로 그대로 채택 → WORKFLOW_BUILD
```

**RAG 검색 (filter=None, 전체 대상):**
```
쿼리: "슬랙 날씨 알림 워크플로우 오전 9시 slack weather notification schedule"

검색 결과 상위:
  [1][SPEC]          Schedule Trigger (pollTimes, interval, unit)
  [2][SPEC]          Slack Node (channel, text, blocks)
  [3][OFFICIAL_DOCS] HTTP Request weather API 예시
  [4][PARENT_SUMMARY] 슬랙 알림 자동화 워크플로우 설계
  [5][CHILD_JSON]    실행 가능한 슬랙 알림 JSON 코드
```

**WorkflowBuildService — 유일하게 토큰 실시간 스트리밍:**
```python
async for token in _stream_llm(system, user, model, history):
    yield sse("token", token)          # ← 즉시 전송 (다른 서비스는 수집 후 발행)
    synthesized_json += token
```

**LLM 생성 내용 (SOC 강제):**
```markdown
## 워크플로우 설계 — 날씨 슬랙 알림
## 전체 흐름
[1] Schedule Trigger → [2] HTTP Request (날씨 API) → [3] Set → [4] Slack

## 노드별 설명
### 1. Schedule Trigger (`n8n-nodes-base.scheduleTrigger`)
- **역할**: 매일 오전 9시 워크플로우 자동 실행
- **핵심 설정**: `rule.interval`: 1, `rule.unit`: "days"

...

## n8n JSON 코드
```json
{
  "nodes": [
    {"name":"Schedule","type":"n8n-nodes-base.scheduleTrigger",...},
    {"name":"Get Weather","type":"n8n-nodes-base.httpRequest",...},
    {"name":"Format","type":"n8n-nodes-base.set",...},
    {"name":"Slack Alert","type":"n8n-nodes-base.slack",...}
  ],
  "connections": {...}
}
```
```

**카드 이벤트 및 REG 검증:**
```
스트리밍 완료 후:
  yield sse("card", { type: "workflow_inject", workflow_payload: synthesized_json })

REG 검증 (WORKFLOW_BUILD는 활성):
  "ruleInterval" → Levenshtein → "rule.interval"? distance=2 → 수정
  또는 수정 없으면 reg_warning 미발행
```

**최종 이벤트 순서:**
```
t=0     2:[{"type":"intent","intent":"WORKFLOW_BUILD"}]
t=5ms   0:"## " → 0:"워크플로우" → ...  (스트리밍 시작)
t=12s   2:[{"type":"card","type":"workflow_inject",...}]
t=12s   2:[{"type":"reg_warning",...}]  (있는 경우)
t=12s   d:{"finishReason":"stop"}
```

---

### 예시 3 — ERROR_PATCH: 크롬 익스텐션이 에러 로그 전송

**입력 페이로드:**
```json
{
  "message": "이 에러 어떻게 고쳐?",
  "error_log": "NodeOperationError: The resource you are requesting could not be found\n[HTTP 404]\nat HTTP Request > Execute > runNode",
  "session_id": "ext-abc"
}
```

**Intent 분류 (1순위 즉시 결정):**
```
error_log 있음 + _ERROR_PATTERN.search(error_log): "Error" 매칭
→ ERROR_PATCH (나머지 우선순위 평가 없이 즉시 반환)
```

**에러 토큰 추출:**
```python
_extract_error_tokens(error_log):
  패턴1 (Error/Exception): "NodeOperationError: The resource..."
  패턴3 (HTTP NNN):        "HTTP 404"
  → tokens = ["NodeOperationError: The resource...", "HTTP 404"]

yield sse("error_alert", {
    "type": "interrupt",
    "tokens": tokens,
    "message": "에러 감지: NodeOperationError: The resource..."
})
```
→ **클라이언트가 이 이벤트를 즉시 수신하여 에러 배너 표시 (LLM 호출 전)**

**RAG 검색 (troubleshooting 우선):**
```
query = "NodeOperationError: The resource HTTP 404"
filter_types = {"troubleshooting", "api_limits", "spec"}

결과:
  [1][TROUBLESHOOTING] HTTP 404 해결 사례 — URL 경로 확인
  [2][API_LIMITS]       REST API 요청 제한 및 에러 응답 처리
  [3][SPEC]             HTTP Request retryOnFail, onError 파라미터
```

**LLM 호출 (SOC: ERROR_PATCH 템플릿):**
```
## 에러 진단
**에러 유형:** HTTP 404 — 리소스 없음
**발생 원인:** 요청한 URL이 서버에 존재하지 않거나 경로가 변경됨

## 원인 분석
- **무슨 일이 일어났나**: HTTP Request 노드가 날씨 API를 호출했으나 404 응답
- **왜 발생했나**: URL 경로가 잘못됨 (`/v1/current` → `/v2/current`)
- **어느 노드에서**: HTTP Request 노드

## 해결 방법
### 방법 1: URL 경로 수정
1. HTTP Request 노드 클릭
2. URL 필드를 `/v2/current`로 수정

## 패치 코드
```json
{ "url": "https://api.weather.example.com/v2/current" }
```

## 즉시 캔버스 적용 가능: YES
## 재발 방지
- `onError`: `continueErrorOutput` 설정으로 에러 분기 처리
- `retryOnFail`: true + maxTries: 3 설정
```

**이벤트 시퀀스:**
```
t=0ms   2:[{"type":"intent","intent":"ERROR_PATCH"}]
t=2ms   2:[{"type":"error_alert","type":"interrupt","tokens":[...]}]  ← 즉시!
t=600ms (RAG) + LLM 처리
t=5s    2:[{"type":"card","type":"error_patch_apply","patch_payload":"..."}]
t=5s    d:{"finishReason":"stop"}
```

---

### 예시 4 — CURRICULUM: "n8n 완전 처음인데 어디서 시작해야 해?"

**Intent 분류:**
```
규칙 1~3 모두 미해당
→ 키워드 추정: "커리큘럼"/"로드맵"/"학습 계획" 미포함 → None
→ LLM 분류 호출 — "완전 처음", "어디서 시작" 등 문맥 종합 판단 → "CURRICULUM" 반환
→ LLM 결과 그대로 채택 → CURRICULUM
```

**레벨 감지 (온톨로지 기반):**
```python
combined = "n8n 완전 처음인데 어디서 시작해야 해?"
_LEVEL_PATTERNS["beginner"].search(combined): "처음" → 매칭
→ level = "beginner"

rag_types = {"entry", "beginner", "official_docs", "book"}
num_weeks = 4, duration = "45m"

yield sse("intent", {"curriculum_level": "beginner", "weeks": 4})
```

**RAG 검색 (beginner 필터):**
```
검색 결과:
  [1][ENTRY]        n8n 소개 및 설치 가이드
  [2][BEGINNER]     첫 워크플로우: Hello World
  [3][OFFICIAL_DOCS] 핵심 개념: Nodes, Connections, Workflows
  [4][BOOK]         3장: Schedule Trigger로 첫 자동화
  ...12개
```

**LLM 호출 (전체 수집 후 JSON 파싱):**
```python
# 스트리밍 없음 — 전체를 모아서 JSON 파싱
full_text = ""
async for token in _stream_llm(system, user, model):
    full_text += token

parsed = _extract_json_array(full_text)
cards = _normalize_cards(parsed)
yield sse("curriculum", { "cards": cards, "description": "..." })
```

**LLM 생성 JSON:**
```json
[
  { "week": "Week 1", "level": "beginner", "title": "n8n 소개와 첫 워크플로우",
    "objectives": ["n8n 인터페이스 탐색", "Manual Trigger 사용법"],
    "nodes": ["Manual Trigger", "Set"], "duration": "45m" },
  { "week": "Week 2", "level": "beginner", "title": "자동화 트리거",
    "objectives": ["Schedule Trigger", "Webhook 기초"],
    "nodes": ["Schedule Trigger", "Webhook"], "duration": "45m" },
  { "week": "Week 3", ... },
  { "week": "Week 4", ... }
]
```

**특징:** CURRICULUM은 텍스트 스트리밍 없음. `fullText`가 비어있으므로 route.ts의 `fallbackStructuredText`가 cards를 마크다운으로 변환하여 DB 저장 텍스트를 만든다.

---

### 예시 5 — EXPRESSION: node_data + "$json으로 어떻게 접근해?"

**크롬 익스텐션 페이로드:**
```json
{
  "message": "이 HTTP Request 결과에서 $json으로 user.email 어떻게 접근해?",
  "node_data": {
    "type": "n8n-nodes-base.httpRequest",
    "name": "Get User Info",
    "output": { "json": { "user": { "id": 42, "email": "test@example.com", "roles": ["admin"] } } }
  }
}
```

**Intent 분류:**
```
규칙 1~3 모두 미해당
→ 키워드 추정: node_data 있음 + "$json" 포함 → EXPRESSION (안전망 대기)
→ LLM 분류 호출 — context_block에 "node_data_attached=true
  (type: n8n-nodes-base.httpRequest)" 포함되어 판단 보조
→ LLM 분류 결과 → "EXPRESSION" 반환
→ LLM 결과가 GENERAL이 아니므로 그대로 채택 → EXPRESSION
```

**RAG 검색 (spec/cli_spec/official_docs):**
```
query = "n8n-nodes-base.httpRequest expression field access user.email $json"

결과:
  [1][SPEC]          HTTP Request Node 파라미터 스펙
  [2][OFFICIAL_DOCS] n8n Expression 문법 — $json, $node 사용법
  [3][CLI_SPEC]      표현식 접근 패턴 예시
```

**LLM 프롬프트 (실제 노드 데이터 포함):**
```
[노드 실행 데이터]
{
  "type": "n8n-nodes-base.httpRequest",
  "output": {
    "json": {
      "user": { "id": 42, "email": "test@example.com", "roles": ["admin"] }
    }
  }
}

[RAG 스펙 컨텍스트]
[1][SPEC] HTTP Request...
```

**LLM 생성 (전체 수집 → expression 이벤트):**
```
## 생성된 표현식

### 표현식 1 — 이메일 직접 접근
{{ $json.user.email }}
**설명**: 현재 HTTP Request 노드 응답의 user.email 을 꺼냅니다.
**언제 사용**: 바로 다음 노드에서 이메일이 필요할 때

### 표현식 2 — 이전 노드에서 참조
{{ $node["Get User Info"].json.user.email }}
**언제 사용**: 거리가 있는 노드에서 참조할 때

### 표현식 3 — roles 배열 첫 번째
{{ $json.user.roles[0] }}
**설명**: roles[0] = "admin"

## 주의사항
- $item() 은 n8n v1.x에서 폐기됨 — 절대 사용 금지 (RULE-04)
```

**REG 검증 (EXPRESSION 활성):**
```
텍스트 스캔 → $json.user.email, $json.user.roles[0] 추출
"user", "email", "roles" → _SKIP_TOKENS에 해당 또는 유효
→ 수정 없음
```

---

### 예시 6 — REVERSE: 워크플로우 JSON 붙여넣기

**사용자 입력:**
```
"이 워크플로우 분석해줘

{"nodes":[{"name":"Schedule Trigger","type":"n8n-nodes-base.scheduleTrigger",...},
{"name":"HTTP Request","type":"n8n-nodes-base.httpRequest",...},
{"name":"IF","type":"n8n-nodes-base.if",...},
{"name":"Slack","type":"n8n-nodes-base.slack",...}],
"connections":{"Schedule Trigger":{"main":[[{"node":"HTTP Request",...}]]},...}}"
```

**Intent 분류:**
```
2순위: "connections" 키 감지
_N8N_JSON_PATTERN.search(message): '"connections"\s*:\s*\{' → 매칭!
→ REVERSE (메시지 본문에서 직접 감지)
```

**토폴로지 파싱 (_parse_topology):**
```python
nodes = [Schedule Trigger, HTTP Request, IF, Slack]
connections = { "Schedule Trigger": [[HTTP Request]], "HTTP Request": [[IF]], ... }

# 노드 레이어 분류 (n8n 노드 유형 온톨로지 적용)
trigger_types = {"scheduleTrigger", "manualTrigger", "webhookTrigger", ...}
sink_types    = {"slack", "gmail", "googleSheets", "postgres", ...}

layers = {
  "trigger":    [Schedule Trigger],
  "processing": [HTTP Request, IF],
  "sink":       [Slack]
}

# 표현식 추출
expressions_found = ["{{ $json.data.status }}", "{{ $json.user.id }}"]
```

**RAG 검색 (노드 타입 기반):**
```
node_types_query = "scheduleTrigger httpRequest if slack"
filter = {"spec", "official_docs"}

→ [1][SPEC] Schedule Trigger 파라미터
→ [2][SPEC] IF Node 파라미터
→ [3][OFFICIAL_DOCS] Slack 통합 가이드
```

**LLM 호출 (토폴로지 JSON + 스펙 컨텍스트):**
```python
topology_str = json.dumps(topology, ensure_ascii=False, indent=2)
system = _REVERSE_SYSTEM_PROMPT.format(topology=topology_str, context=context_str)
```

**LLM 생성 JSON (SOC 강제):**
```json
[
  {
    "layer": "summary",
    "content": "이 워크플로우는 정기적으로 외부 데이터를 확인하여 조건에 따라 슬랙 알림을 발송하는 모니터링 자동화입니다."
  },
  {
    "layer": "nodes",
    "items": [
      {
        "node_name": "Schedule Trigger",
        "type": "n8n-nodes-base.scheduleTrigger",
        "layer": "trigger",
        "role": "설정된 주기마다 워크플로우를 자동 시작합니다.",
        "key_params": [{"k": "interval", "v": "1"}, {"k": "unit", "v": "hours"}],
        "warning": null
      },
      {
        "node_name": "HTTP Request",
        "layer": "processing",
        "role": "외부 API를 호출하여 데이터를 가져옵니다.",
        "warning": "API 인증 토큰 만료 가능 — retryOnFail 설정 권고"
      },
      ...
    ]
  },
  {
    "layer": "expressions",
    "items": [
      { "expression": "{{ $json.data.status }}", "node": "IF", "explanation": "API 응답의 status 필드로 분기 판단" }
    ]
  }
]
```

**정규화 및 이벤트:**
```python
normalized = {
    "summary": "이 워크플로우는...",
    "node_roles": [...],
    "expressions": [...],
    "raw_report": report_data
}
yield sse("report", normalized)
```

---

### 예시 7 — 꼬리 물기: "그 IF 노드 더 자세히 알려줘"

**전제:** 이전 턴에서 IF 노드 관련 GENERAL 답변이 있었음.

**세션 상태:**
```python
history = [
    ConversationTurn(role="user", content="IF 노드와 Switch 노드 차이가 뭐야?", intent="GENERAL"),
    ConversationTurn(role="assistant", content="IF 노드는 참/거짓 2분기, Switch는 다중 분기..."),
]
```

**Intent 분류 — 꼬리 물기 감지:**
```
4순위: history 있음 + _FOLLOWUP_KW.search("그 IF 노드 더 자세히 알려줘"):
  "더 자세" → "더\s*(자세|설명|알려)" 매칭!
  메시지 길이 16자 < 60자 제한 통과
  → _last_intent(history) = GENERAL
  → GENERAL 이어받기
```

**RAG 쿼리 강화:**
```python
prior_user = "IF 노드와 Switch 노드 차이가 뭐야?"  # 이전 user 메시지 (120자 이내)
rag_query = "IF 노드와 Switch 노드 차이가 뭐야? 그 IF 노드 더 자세히 알려줘"
# ← 짧은 후속 질문을 이전 컨텍스트로 보강
```

**RAG 검색 (보강된 쿼리로):**
```
"IF 노드 Switch 조건 비교 차이 상세"

결과 (보강 없이는 "그 IF" 만으로는 검색 품질 저하):
  [1][SPEC]          IF Node — conditions, combineOperation 파라미터
  [2][OFFICIAL_DOCS] IF vs Switch 노드 비교
  [3][SPEC]          Switch Node — rules, fallbackOutput
```

**멀티턴 LLM 호출:**
```python
_build_messages(system, history=full_history, user="그 IF 노드 더 자세히 알려줘"):

messages = [
    {"role": "system",    "content": _NODE_DETAIL_SYSTEM_PROMPT + context},
    {"role": "user",      "content": "IF 노드와 Switch 노드 차이가 뭐야?"},   # 이전 질문
    {"role": "assistant", "content": "IF 노드는 참/거짓 2분기, Switch는..."},  # 이전 답변
    {"role": "user",      "content": "그 IF 노드 더 자세히 알려줘"}            # 현재
]
# LLM이 "그 IF 노드"가 방금 설명한 IF 노드임을 대화 맥락에서 정확히 이해
```

**효과:**
- 쿼리 강화로 정확한 RAG 검색 달성
- 멀티턴 히스토리로 LLM의 맥락 이해
- 이전 답변보다 더 심화된 내용 생성 (중복 없음)

---

## 19. 기존 시스템과의 차별성 비교

### 19.1 기능 비교표

| 기능 | Raw LLM (ChatGPT 등) | 단순 RAG 챗봇 | **Naito** |
|------|---------------------|-------------|-----------|
| n8n 파라미터 정확도 | 낮음 | 중간 | **높음 (REG Stage1 자동 수정)** |
| 출처 추적 | 없음 | 부분적 | **완전 (data_type + source)** |
| 의도 분류 투명성 | 없음 | 없음 | **결과 실시간 공개 + 명백한 신호 3종은 규칙으로 100% 설명 가능** |
| 학습 수준 개인화 | 없음 | 없음 | **온톨로지 학습그래프 기반 자동 감지** |
| 워크플로우 실행 | 없음 | 없음 | **캔버스 직접 주입** |
| 에러 실시간 처리 | 없음 | 없음 | **크롬 익스텐션 연동, 즉시 패치** |
| 역분석 | 없음 | 없음 | **3층 아코디언 토폴로지 리포트** |
| 커리큘럼 생성 | 제한적 | 없음 | **레벨 온톨로지 필터 RAG + 선행 그래프** |
| 파라미터 오타 수정 | 없음 | 없음 | **REG Levenshtein ≤2 자동 수정** |
| 속성 제약 검증 | 없음 | 없음 | **Semantic Stage2: 11개 PropertyConstraints** |
| 구조 무결성 검증 | 없음 | 없음 | **Semantic Stage2: connections 참조 무결성** |
| 패턴·관계 검증 | 없음 | 없음 | **Semantic Stage3: Anti-pattern 감지** |
| 표현식 의미 검증 | 없음 | 없음 | **Semantic Stage4: $item() 폐기 감지** |
| 쿼리 관계 확장 | 없음 | 없음 | **OntologyEnhancer RelationGraph 탐색** |
| 꼬리 물기 지원 | 부분적 | 없음 | **쿼리 강화 + Intent 이어받기** |
| 결정 감사 로그 | 없음 | 없음 | **requestLog (intent, latency, ...)** |

### 19.2 아키텍처 원칙 비교

```
[Raw LLM]
User → LLM → Answer
  단순하지만 검증 불가, 환각 통제 불가

[단순 RAG]
User → Retriever → LLM → Answer
  검색은 하지만 출력 검증 없음

[Naito: Ontology + RAG + REG + SemanticValidator + XAI]
User
  │
  ▼ [의도 분류 (LLM 우선 + 규칙 3종 안전망)]
  ▼ [온톨로지 엔티티 인식 → RelationGraph 탐색 → 쿼리 확장 + 패턴 감지]
  ▼ [하이브리드 RAG (확장 쿼리) + Ontology Reranking]
  ▼ [SOC 프롬프트 + RAG 컨텍스트 + 온톨로지 힌트 → LLM]
  ▼ [REG Stage1: 파라미터 오타 자동 수정]
  ▼ [SemanticValidator Stage2-4: 구조·제약·패턴·표현식 검증]
  ▼ Answer + (ontology_context, reg_warning, validation_report) 이벤트
  
  + 5단계 모든 결정 실시간 이벤트로 공개 (XAI)
  + 소스 귀속 및 관계 근거 명시
  + 속성 제약 자동 검증으로 런타임 오류 예방
  + 관계 온톨로지로 누락 컨텍스트 자동 보완
```

---

## 20. 설계 결정 기록

### ADR-001: IntentRouter — 규칙 기반에서 LLM 우선 하이브리드로 전환 (개정)

**최초 결정 (deprecated):** 정규식 + 우선순위 규칙만으로 6개 Intent 전부를 분류.

**현재 결정:** 에러 로그 첨부·n8n JSON 첨부·꼬리 물기 3가지 명백한 신호만 규칙으로 즉시 처리하고, 나머지 자연어 질문은 few-shot 프롬프트를 포함한 LLM이 분류한다. 키워드 추정(`_keyword_guess`)은 LLM이 GENERAL로 회피하거나 호출이 실패했을 때만 개입하는 안전망으로 격하되었다.

**전환 이유:**
1. 순수 정규식으로는 "Webhook 노드 설명해줘"(GENERAL)와 "이 워크플로우 어떻게 동작해?"(REVERSE)처럼 표면적으로 비슷하지만 의미가 다른 문장을 안정적으로 구분하기 어려웠다.
2. LLM은 few-shot 예시로 이런 경계 케이스를 문맥까지 고려해 훨씬 정확히 판단한다.
3. 텍스트 의미 이해가 필요 없는 신호(에러 로그, JSON 구조)는 여전히 규칙으로 즉시(수 ms) 처리해 불필요한 LLM 호출을 피한다.

**트레이드오프:**
- 규칙 3종에 해당하지 않는 대부분의 요청에 LLM 호출 1회(약 수백 ms)가 추가된다.
- 완전한 결정론성은 포기했다 — 대신 키워드 안전망으로 최소 품질을 보장한다.
- 새 Intent 추가 시 few-shot 프롬프트에 예시만 추가하면 되어, 오히려 유지보수는 쉬워졌다.

---

### ADR-002: BM25 + 벡터 하이브리드 RAG (단일 검색 방식 거부)

**결정:** BM25 + ChromaDB 병렬 + RRF 융합

**이유:**
- BM25: 정확한 파라미터명(`retryOnFail`) 검색에 우수
- 벡터: 의미 기반 검색 ("자동 재시도" = `retryOnFail`) 우수
- RRF: 어느 한 방법만으로는 recall 불충분, 결합 시 보완

**구현 복잡도:** BM25는 CPU 바운드이므로 ProcessPoolExecutor 격리 필요

---

### ADR-003: REG 검증 범위를 WORKFLOW_BUILD/EXPRESSION/ERROR_PATCH로 제한

**결정:** GENERAL, CURRICULUM, REVERSE는 REG 미적용

**이유:**
- GENERAL/CURRICULUM: 파라미터 코드 생성 없음 → 검증 불필요
- REVERSE: 입력 JSON을 분석하는 것이므로 LLM이 파라미터를 창작하지 않음
- 불필요한 REG 검증은 오탐(false positive) 증가 위험

---

### ADR-004: 채팅 제목 생성 타이밍 (writer.write finish 이전에 실행)

**결정:** `writer.write({ type: "finish" })`는 반드시 `updateChatTitleById()` 이후

**이유:**
- Vercel AI SDK의 `finish` 이벤트가 SWR 캐시 무효화를 트리거
- SWR이 먼저 실행되면 DB에 아직 업데이트되지 않은 "New chat" 제목을 읽음
- 제목 저장 완료 후 finish를 전송해야 사이드바가 즉시 올바른 제목을 표시

---

### ADR-005: OpenAI 키 서버 미보관 (클라이언트 BYOK)

**결정:** API 키를 localStorage에만 보관, 매 요청마다 클라이언트가 전송

**이유:**
- 서버 DB에 보관 시 키 유출 리스크
- 사용자별 과금이 사용자 책임
- 서버는 키를 전달만 하고 저장하지 않음

**트레이드오프:** 키 분실 시 사용자가 재입력해야 함

---

### ADR-006: 세션 히스토리를 인메모리로 관리

**결정:** SessionStore를 Redis/DB가 아닌 Python dict로 구현

**이유:**
- 히스토리는 영속성이 낮음 (프로세스 재시작 시 초기화 허용)
- Redis 의존성 추가 없이 구현 단순화
- FastAPI 단일 프로세스 내에서는 충분

**트레이드오프:** 서버 재시작 시 대화 컨텍스트 초기화

---

### ADR-007: 도메인 온톨로지를 코드 레벨 데이터 구조로 구현

**결정:** OWL/RDF 외부 온톨로지 파일 대신 Python 데이터클래스로 직접 정의

**대안:** Protégé 등 온톨로지 편집기 + rdflib 파싱

**이유:**
1. Python 데이터클래스는 IDE 자동완성·타입 체크 가능
2. 외부 온톨로지 파일은 FastAPI 부팅 시 파싱 지연 발생
3. n8n 453개 노드에 대한 하이브리드(수동+자동) 전략을 코드에서 직접 표현 가능
4. 새 노드 추가 시 PR 리뷰로 온톨로지 변경 추적 가능

**현재 규모:** 수동 노드 185개 + 자동 노드 268개 = 453개 노드, PropertyConstraints 30개, WorkflowPatterns 11개, LearningNodes 17개

**트레이드오프:** OWL 추론 엔진(사용 가능성 추론 등)을 사용 불가

---

### ADR-008: SemanticValidator 활성화 범위를 WORKFLOW_BUILD + ERROR_PATCH로 제한

**결정:** `_SEM_VALIDATE_INTENTS = {WORKFLOW_BUILD, ERROR_PATCH}`

**이유:**
- EXPRESSION: 표현식 텍스트만 생성 — 파싱 가능한 워크플로우 JSON 없음
- GENERAL/CURRICULUM: 설명 텍스트만 — 코드 검증 불필요
- REVERSE: 입력 JSON 분석 — LLM이 JSON을 창작하지 않음
- 불필요한 검증 실행은 지연 증가 + false positive 위험

**트레이드오프:** ERROR_PATCH에서 생성된 JSON도 완전한 워크플로우가 아닐 수 있어 일부 구조 검증이 오탐할 수 있음 → SemanticValidator가 graceful fallback으로 처리

---

### ADR-009: OntologyEnhancer를 RAG 이전이 아닌 쿼리 레벨에서만 실행

**결정:** OntologyEnhancer는 쿼리 확장과 힌트 생성만 수행; RAG 내부 인덱싱은 변경 없음

**대안:** ChromaDB 인덱싱 시점에 관계 메타데이터 삽입

**이유:**
1. 인덱스 재구성 없이 온톨로지 적용 가능
2. 쿼리 시점 확장은 온톨로지 업데이트를 인덱스 재생성 없이 반영
3. OntologyReranking으로 청크 순서 후처리 — 검색 자체는 HybridRetriever 결과 유지

**트레이드오프:** ChromaDB 내 metadata 필터링과 온톨로지 지식을 결합하지 못함

---

### ADR-010: 하이브리드 온톨로지 전략 (수동 정의 + 자동 생성 병행)

**결정:** 빈도 높은 상위 노드는 수동으로 관계·제약 완전 명세; 나머지는 camelCase 파싱으로 기본 메타데이터만 자동 생성

**배경:**
- 초기 설계에서는 핵심 노드 17개만 수동 정의 → RAG 데이터셋의 96%를 온톨로지가 처리하지 못하는 커버리지 공백 발생
- 전체 453개를 모두 수동 정의하는 방식은 품질은 높지만 유지보수 비용이 선형적으로 증가
- 자동 생성만으로는 관계·패턴 정보가 없어 쿼리 확장 품질이 낮음

**결정 근거:**
1. RAG 데이터셋에서 빈도 ≥ 5인 노드를 분석하면 상위 185개가 전체 언급의 93.7%를 차지 (롱테일 분포)
2. 상위 185개를 수동 정의하면 사실상 대부분의 실사용 쿼리에서 온톨로지 혜택이 적용됨
3. 하위 268개는 자동 생성으로 기본 노드 탐지(display_name, role, tags)만 제공 — 탐지 실패 방지

**결과:**
- 수동 노드: 185개 (TRIGGER 28개, PROCESSING 55개, SINK 88개, UTILITY 14개)
- 자동 노드: 268개 (기본 메타데이터만)
- RAG 언급 커버리지: 93.7% (32,555건 중 30,492건)
- PropertyConstraints: 30개, WorkflowPatterns: 11개, LearningNodes: 17개

**트레이드오프:** 자동 노드에서는 RelationGraph 기반 쿼리 확장이 작동하지 않음; 빈도 < 5 노드에서의 품질 개선 불가 (전체 RAG 언급의 6.3%)

### ADR-011: 오타 처리 전략 — LLM 없이 자모 Levenshtein + 프롬프트 교정 주입

**결정:** OntologyEnhancer에 LLM을 투입하지 않고, 한국어 자모 분해 + Levenshtein 편집 거리로 오타를 감지한 뒤, 교정 정보를 LLM 시스템 프롬프트에 주입하여 할루시네이션을 차단한다.

**배경:**
- 사용자가 "앱훅이 뭐야?"(웹훅의 오타)를 입력했을 때 시스템이 두 단계로 실패함:
  1. OntologyEnhancer가 exact match 실패 → 웹훅 관련 RAG 문서 미검색
  2. LLM이 "앱훅(App Hook)"이라는 존재하지 않는 개념을 창작하여 설명 → 심각한 할루시네이션
- 당시 OntologyEnhancer는 ~15개 항목의 한국어 exact match 사전만 보유, 퍼지 매칭 없음

**대안 평가:**

| 방법 | 오타 내성 | 추가 지연 | 결정 |
|------|----------|----------|------|
| LLM 오타 교정 (GPT 호출) | 매우 높음 | 300~800ms | 거부 — 사용자 체감 지연 과대 |
| 사전 확장 (수동) | 낮음 | 0ms | 거부 — 무한 확장 불가 |
| rapidfuzz 라이브러리 | 높음 | ~1ms | 검토 — 이미 설치됨 |
| 자모 분해 + 순수 Python Levenshtein | 높음 | ~2ms | **채택** |

**채택 근거:**
1. OntologyEnhancer의 역할은 **"어떤 문서를 검색할지"** 결정이지 의미 이해가 아님 → entity recognition에 LLM 불필요
2. 의미 이해는 답변 LLM이 이미 담당 → 교정 정보를 프롬프트로 전달하면 충분
3. 자모 분해 Levenshtein이 Korean IME 오타(ㅔ↔ㅐ, 된소리 혼동 등) 패턴을 정확히 처리
4. dict 80개 × Levenshtein O(n×m) = 전체 연산량이 수천 회 이하 → 2ms 미만

**구현 상세:**
- `_decompose_jamo()`: 완성형 한글 → 자모 분해 (Unicode 0xAC00 기반 공식)
- `_levenshtein()`: 순수 Python DP, 조기 종료 최적화
- `_strip_ko_particle()`: 이/가/은/는/을/를 등 15개 조사 제거 (최장 우선)
- `_fuzzy_threshold(len)`: 4이하=0, 5~9=1, 10+=2
- `typo_corrections: List[Tuple[str,str]]`: dist>0인 경우만 기록
- 주입 대상: GeneralRAGService, WorkflowBuildService, ExpressionService 시스템 프롬프트

**추가 개선 (ADR-010에서 연속):**
- `_DISPLAY_TO_SHORT`: 하드코딩 ~20개 → 453개 전체 온톨로지에서 동적 생성
- `_SHORT_TYPE_RE`: 15개 하드코딩 → 453개 동적 regex
- `_KO_TO_SHORT`: 15개 → 80+개 (주요 노드 전체 한국어 매핑)
- Step 4 단어 경계: 2글자 이하 키는 단어 경계 검사 추가 (서브스트링 오탐 방지)

---

*보고서 끝 — Naito 아키텍처 v2.2 (오타 내성 + 할루시네이션 방지 파이프라인)*
