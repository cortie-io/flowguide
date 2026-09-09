# Naito 도메인 온톨로지 상세 명세서

> **파일 기준:** `server/domain_ontology.py`  
> **작성 기준:** 2026년 6월 22일

---

## 목차

1. [온톨로지란 무엇인가 — 이 시스템에서의 정의](#1-온톨로지란-무엇인가)
2. [전체 온톨로지 구조 개요](#2-전체-온톨로지-구조-개요)
3. [온톨로지 1: NodeTaxonomy (노드 분류 계층)](#3-온톨로지-1-nodetaxonomy)
4. [온톨로지 2: RelationGraph (노드 간 상관관계 그래프)](#4-온톨로지-2-relationgraph)
5. [온톨로지 3: PropertyConstraints (속성 제약 규칙)](#5-온톨로지-3-propertyconstraints)
6. [온톨로지 4: WorkflowPatterns (워크플로우 패턴 라이브러리)](#6-온톨로지-4-workflowpatterns)
7. [온톨로지 5: LearningGraph (학습 선행 의존성 그래프)](#7-온톨로지-5-learninggraph)
8. [온톨로지 간 협력 흐름 — 실제 처리 추적](#8-온톨로지-간-협력-흐름)
9. [활용 컴포넌트별 온톨로지 사용 매핑](#9-활용-컴포넌트별-온톨로지-사용-매핑)
10. [온톨로지 확장 가이드](#10-온톨로지-확장-가이드)

---

## 1. 온톨로지란 무엇인가

### 1.1 일반적 정의

온톨로지(Ontology)는 철학 용어에서 출발했지만, 컴퓨터 과학에서는 **"특정 도메인의 개념(Concept)과 개념들 사이의 관계(Relation)를 형식적으로 명세한 지식 구조"**를 의미한다.

쉽게 말하면:
- **분류(Taxonomy):** 사물을 체계적으로 나누는 것
- **관계(Relation):** 분류된 개념들이 서로 어떻게 연결되는지
- **제약(Constraint):** 개념이나 관계가 지켜야 하는 규칙

이 세 가지를 합친 것이 온톨로지다.

### 1.2 이 시스템에서 온톨로지가 필요한 이유

**문제:** LLM은 "HTTP Request 노드 retry 설정 방법"을 물어보면 `retryOnFail`만 설명한다. 그러나 실제로 이 설정이 의미 있으려면 `maxTries`도 함께 설정해야 하고, `waitBetweenTries`도 고려해야 하며, 대량 처리라면 `Split In Batches`도 함께 써야 한다는 **연쇄 지식(Relational Knowledge)**을 LLM은 일관되게 제공하지 못한다.

**해결:** 이 연쇄 지식을 온톨로지에 형식적으로 명세하고, 모든 답변 생성 과정에 자동으로 주입한다.

```
온톨로지 없이:
  질문 → RAG(단순 키워드 검색) → LLM → 답변
  결과: retryOnFail 설명만 제공, maxTries 누락

온톨로지 있이:
  질문 → 온톨로지 탐색(관련 노드/제약/패턴 감지) → 확장된 RAG → LLM(힌트 포함) → 검증 → 답변
  결과: retryOnFail + maxTries + waitBetweenTries + Anti-pattern 경고까지 포함
```

### 1.3 우리 시스템의 온톨로지 5계층

```
domain_ontology.py
├── NodeTaxonomy      — "각 노드가 무엇인가" (분류)
├── RelationGraph     — "노드들이 서로 어떤 관계인가" (연결)
├── PropertyConstraints — "파라미터들 사이에 어떤 규칙이 있는가" (제약)
├── WorkflowPatterns  — "검증된 노드 조합이 무엇인가" (패턴)
└── LearningGraph     — "학습 순서가 어떻게 되는가" (의존성)
```

---

## 2. 전체 온톨로지 구조 개요

```
┌─────────────────────────────────────────────────────────────────────┐
│  N8N 도메인 온톨로지 (domain_ontology.py)                           │
│                                                                     │
│  ┌─────────────────────┐   ┌──────────────────────────────────────┐ │
│  │  Layer 1            │   │  Layer 2                             │ │
│  │  NodeTaxonomy       │   │  RelationGraph                       │ │
│  │                     │   │                                      │ │
│  │  NodeRole:          │   │  RelationType (7종):                 │ │
│  │  TRIGGER  (28개)    │   │  COMMONLY_USED_WITH                  │ │
│  │  PROCESSING(55개)   │   │  PREREQUISITE_FOR                    │ │
│  │  SINK     (88개)    │◄──│  COMPLEMENTED_BY                     │ │
│  │  UTILITY  (14개)    │   │  PATTERN_MEMBER                      │ │
│  │                     │   │  REQUIRES_MULTIPLE_IN                │ │
│  │  수동: 185개        │   │  ANTI_PATTERN_WITH                   │ │
│  │  자동: 268개        │   │  REPLACES                            │ │
│  │  합계: 453개        │   │                                      │ │
│  │  (RAG 커버: 93.7%)  │   │  수동 노드에만 적용                  │ │
│  └─────────────────────┘   └──────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────┐   ┌──────────────────────────────────────┐ │
│  │  Layer 3            │   │  Layer 4                             │ │
│  │  PropertyConstraints│   │  WorkflowPatterns                    │ │
│  │                     │   │                                      │ │
│  │  ConstraintType:    │   │  11개 패턴:                          │ │
│  │  REQUIRES           │   │  periodic_api_monitor                │ │
│  │  CONFLICTS          │   │  webhook_response                    │ │
│  │  CONDITIONAL        │   │  batch_api_processing + 8개          │ │
│  │  RECOMMENDED        │   │                                      │ │
│  │  FORBIDDEN          │   │  (node_types, connections,           │ │
│  │                     │   │   best_practices, anti_patterns)     │ │
│  │  30개 제약 규칙     │   │                                      │ │
│  │  (node + property)  │   │                                      │ │
│  └─────────────────────┘   └──────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Layer 5 — LearningGraph                                    │   │
│  │                                                             │   │
│  │  17개 LearningNode (concept + prerequisites + level)        │   │
│  │  선행 의존성 방향성 DAG (커리큘럼 순서 결정)                │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. 온톨로지 1: NodeTaxonomy

**목적:** n8n의 노드를 역할과 성질 기준으로 분류한다.

### 3.1 핵심 데이터 구조

```python
class NodeRole(str, Enum):
    TRIGGER    = "trigger"      # 워크플로우 시작점
    PROCESSING = "processing"   # 데이터 변환·제어
    SINK       = "sink"         # 외부 출력·저장
    UTILITY    = "utility"      # 흐름 제어 유틸리티

class OutputType(str, Enum):
    JSON   = "json"     # 항상 JSON 반환
    BINARY = "binary"   # 바이너리 데이터 반환
    BOTH   = "both"     # JSON + 바이너리 모두 가능
    NONE   = "none"     # 반환값 없음 (예: Respond to Webhook)

@dataclass
class N8NNodeDef:
    short_type:               str           # "httpRequest"
    full_type:                str           # "n8n-nodes-base.httpRequest"
    display_name:             str           # "HTTP Request"
    role:                     NodeRole
    output_type:              OutputType    # 기본값: JSON
    tags:                     FrozenSet[str]  # 검색용 키워드 집합
    relations:                List[NodeRelation]  # Layer 2 엣지
    requires_multiple_inputs: bool          # Merge 등 다중 입력 노드
```

### 3.2 하이브리드 노드 목록 (수동 185개 + 자동 268개 = 453개)

#### 3.2.1 하이브리드 전략 개요

n8n 전체 노드(453개)를 단순히 나열하는 대신 **품질 × 커버리지** 트레이드오프를 최적화하는 하이브리드 전략을 채택한다.

```
┌───────────────────────────────────────────────────────────────────┐
│  수동 정의 (Manual, 185개)             RAG 언급 93.7% 커버        │
│  ─────────────────────────────────────────────────────────────    │
│  • RelationGraph 완전 명세 (관계·가중치·설명)                     │
│  • PropertyConstraints 적용 가능                                  │
│  • WorkflowPattern 구성원으로 참여                               │
│  • 선정 기준: RAG 데이터셋 빈도 ≥ 5                               │
│                                                                   │
│  자동 생성 (Auto-Generated, 268개)     RAG 언급 추가 6.3% 커버   │
│  ─────────────────────────────────────────────────────────────    │
│  • display_name: camelCase → Title Case 변환                     │
│  • role: 접미사 규칙 기반 추론                                    │
│  • tags: camelCase 분절 + 카테고리 키워드 보강                    │
│  • relations: 없음 (빈도 낮아 영향 미미)                          │
└───────────────────────────────────────────────────────────────────┘
```

**병합 우선순위:** 수동 노드가 항상 우선 (`_ALL_NODE_DEFS = _NODE_DEFS + _AUTO_NODE_DEFS`)

#### 3.2.2 수동 정의 노드 — TRIGGER (28개, 주요 목록)

| short_type | display_name | 주요 RelationGraph 관계 |
|---|---|---|
| scheduleTrigger | Schedule Trigger | → httpRequest(0.90), → slack(0.75) |
| webhook | Webhook | ↔ respondToWebhook(0.98), → set(0.90) |
| manualTrigger | Manual Trigger | → set(0.80), → httpRequest(0.75) |
| telegramTrigger | Telegram Trigger | ↔ telegram(0.95), → if(0.85) |
| gmailTrigger | Gmail Trigger | ↔ gmail(0.95), → if(0.85) |
| googleDriveTrigger | Google Drive Trigger | ↔ googleDrive(0.90), → extractFromFile(0.85) |
| formTrigger | n8n Form Trigger | → set(0.90), → googleSheets(0.80) |
| githubTrigger | GitHub Trigger | → if(0.85), → slack(0.80) |
| errorTrigger | Error Trigger | → set(0.90), → slack(0.85) |
| executeWorkflowTrigger | Execute Workflow Trigger | ↔ executeWorkflow(0.95) |
| notionTrigger | Notion Trigger | ↔ notion(0.95), → set(0.85) |
| whatsAppTrigger | WhatsApp Trigger | ↔ whatsApp(0.95) |
| hubspotTrigger | HubSpot Trigger | ↔ hubspot(0.90), → slack(0.75) |
| googleSheetsTrigger | Google Sheets Trigger | ↔ googleSheets(0.90), → set(0.80) |
| typeformTrigger | Typeform Trigger | → set(0.90), → googleSheets(0.80) |
| localFileTrigger | Local File Trigger | → extractFromFile(0.90) |
| shopifyTrigger | Shopify Trigger | ↔ shopify(0.95), → set(0.85) |
| calendlyTrigger | Calendly Trigger | → googleCalendar(0.85), → emailSend(0.80) |
| facebookTrigger | Facebook Trigger | → set(0.85), → if(0.80) |
| twilioTrigger | Twilio Trigger | ↔ twilio(0.95), → if(0.85) |
| interval | Interval | ⇒ scheduleTrigger(REPLACES, 0.90) |
| wooCommerceTrigger | WooCommerce Trigger | ↔ wooCommerce(0.95), → emailSend(0.75) |
| pipedriveTrigger | Pipedrive Trigger | ↔ pipedrive(0.95), → slack(0.80) |
| linearTrigger | Linear Trigger | ↔ linear(0.95), → slack(0.80) |
| googleCalendarTrigger | Google Calendar Trigger | ↔ googleCalendar(0.95), → zoom(0.75) |
| microsoftOutlookTrigger | Microsoft Outlook Trigger | ↔ microsoftOutlook(0.90), → if(0.80) |
| slackTrigger | Slack Trigger | ↔ slack(0.95), → openAi(0.75) |
| cron | Cron | ↔ scheduleTrigger(COMMONLY_USED_WITH) |

#### 3.2.3 수동 정의 노드 — PROCESSING (55개, 주요 목록)

| short_type | display_name | 카테고리 |
|---|---|---|
| httpRequest | HTTP Request | API 통신 |
| set | Set | 데이터 변환 |
| if | IF | 조건 분기 |
| switch | Switch | 다중 분기 |
| code | Code | 커스텀 코드 |
| splitOut | Split Out | 배열 처리 |
| aggregate | Aggregate | 집계 |
| merge | Merge | 데이터 병합 |
| filter | Filter | 조건 필터링 |
| itemLists | Item Lists | 목록 조작 |
| summarize | Summarize | 집계·요약 |
| compareDatasets | Compare Datasets | 데이터셋 비교 |
| splitInBatches | Split In Batches | 배치 분할 |
| openAi | OpenAI | AI 생성 |
| html | HTML | HTML 변환 |
| markdown | Markdown | 마크다운 처리 |
| extractFromFile | Extract From File | 파일 내용 추출 |
| convertToFile | Convert to File | 파일 변환 |
| xml | XML | XML 파싱 |
| crypto | Crypto | 암호화 |
| spreadsheetFile | Spreadsheet File | 스프레드시트 처리 |
| graphql | GraphQL | GraphQL 쿼리 |
| editImage | Edit Image | 이미지 편집 |
| executeWorkflow | Execute Workflow | 서브 워크플로우 실행 |
| function | Function | 함수 실행 |
| readWriteFile | Read/Write Files from Disk | 디스크 파일 처리 |
| emailReadImap | Email (IMAP) | 이메일 수신 |
| rssFeedRead | RSS Feed Read | RSS 수집 |
| htmlExtract | HTML Extract | 웹 스크래핑 |
| ssh | SSH | 원격 서버 명령 |
| executeCommand | Execute Command | 로컬 명령 실행 |
| git | Git | 버전 관리 |
| facebookGraphApi | Facebook Graph API | SNS API |
| gmailTool | Gmail Tool | AI 에이전트용 Gmail |
| postgresTool | Postgres (Tool) | AI 에이전트용 Postgres |
| supabaseTool | Supabase (Tool) | AI 에이전트용 Supabase |
| googleDocsTool | Google Docs Tool | AI 에이전트용 Google Docs |
| discordTool | Discord Tool | AI 에이전트용 Discord |
| telegramTool | Telegram Tool | AI 에이전트용 Telegram |
| microsoftOutlookTool | Microsoft Outlook Tool | AI 에이전트용 Outlook |
| functionItem | Function Item | 구버전 Function (REPLACES→code) |
| compression | Compression | 파일 압축 |
| datatable | Datatable | 테이블 표시 |
| renameKeys | Rename Keys | 필드명 변경 |
| readBinaryFile | Read Binary File | 바이너리 읽기 (구버전) |
| writeBinaryFile | Write Binary File | 바이너리 저장 (구버전) |
| readPDF | Read PDF | PDF 텍스트 추출 |
| clearbit | Clearbit | 데이터 인리치먼트 |
| bannerbear | Bannerbear | 이미지 자동 생성 |
| googleCloudNaturalLanguage | Google Cloud NL | NLP 분석 |
| uproc | uProc | 데이터 룩업 |
| hackerNews | Hacker News | 뉴스 수집 |
| humanticAi | Humantic AI | 성격 분석 |
| hunter | Hunter | 이메일 발굴 |

#### 3.2.4 수동 정의 노드 — SINK (88개, 주요 목록)

| 카테고리 | 노드 목록 |
|---|---|
| 메신저·알림 | slack, telegram, discord, whatsApp, mattermost, microsoftTeams, matrix, rocketchat, signl4 |
| 이메일 | gmail, emailSend, mailchimp, sendGrid, mailjet, awsSes, twilio |
| 데이터베이스 | googleSheets, postgres, mySql, supabase, airtable, redis, mongoDb, snowflake, baserow, nocoDb, microsoftExcel |
| CRM | hubspot, salesforce, pipedrive, copper, zoho, intercom, zendesk, zammad |
| 파일·스토리지 | googleDrive, dropbox, awsS3, s3, microsoftOneDrive, nextCloud, ftp, box |
| 프로젝트 관리 | notion, jira, asana, trello, clickUp, todoist, linear, mondayCom, microsoftToDo, wrike |
| SNS | twitter, linkedIn, reddit, facebook, medium |
| 개발·코드 | github, gitLab, jira |
| 커머스 | shopify, wooCommerce, stripe, quickbooks, xero, wise |
| CMS·블로그 | wordpress, ghost, webflow, strapi, ghost |
| 화상회의 | zoom, googleCalendar, googleDocs, googleSlides |
| 마케팅 | mautic, lemlist, ghost, mailchimp |
| ERP·HR | odoo, erpNext, bambooHr, salesforce |
| IoT·인프라 | mqtt, kafka, rabbitmq, pagerDuty, theHive, theHiveProject |
| 기타 서비스 | spotify, youTube, googleAnalytics, strava, clockify, dropbox |

#### 3.2.5 수동 정의 노드 — UTILITY (14개)

| short_type | display_name | 설명 |
|---|---|---|
| wait | Wait | 지연·일시정지 |
| limit | Limit | 항목 수 제한 |
| sort | Sort | 항목 정렬 |
| dateTime | Date & Time | 날짜 변환·계산 |
| removeDuplicates | Remove Duplicates | 중복 제거 |
| stopAndError | Stop And Error | 워크플로우 강제 중단 |
| noOp | No Operation | 아무것도 하지 않음 |
| stickyNote | Sticky Note | 노트 (시각화 전용) |
| moveBinaryData | Move Binary Data | 바이너리 필드 이동 |
| executionData | Execution Data | 실행 메타데이터 접근 |
| form | n8n Form | 멀티스텝 폼 중간 페이지 |
| debugHelper | Debug Helper | 디버깅 보조 |
| splitInBatches | Split In Batches | 배치 분할 처리 |
| respondToWebhook | Respond to Webhook | Webhook 동기 응답 |

> **Note:** `form`은 `formTrigger`와 쌍을 이뤄 멀티스텝 폼을 구성하는 중간 페이지 노드다. `respondToWebhook`은 `webhook`의 `responseMode: responseNode` 설정 시에만 의미가 있다.

#### 3.2.6 자동 생성 노드 예시 (268개 중 발췌)

```python
# 자동 생성 파이프라인 예시
_raw = "actionNetwork"
N8NNodeDef(
    short_type   = "actionNetwork",
    full_type    = "n8n-nodes-base.actionNetwork",
    display_name = "Action Network",   # camelCase → Title Case
    role         = NodeRole.SINK,       # 접미사 규칙 기반 추론
    tags         = frozenset({"action", "network"}),  # 분절 + 보강
    relations    = [],                  # 자동 노드는 빈 리스트
)
```

| short_type | display_name | 자동 추론 role |
|---|---|---|
| actionNetwork | Action Network | sink |
| affinity | Affinity | sink |
| agilecrm | Agile Crm | sink |
| amqp | Amqp | sink |
| awsLambda | Aws Lambda | sink |
| calendly | Calendly | sink |
| chargebee | Chargebee | sink |
| cortex | Cortex | sink |
| discourse | Discourse | sink |
| … (총 268개) | … | … |

### 3.3 tags가 중요한 이유

`tags`는 `frozenset`으로 정의되어 있으며, OntologyEnhancer가 RAG 쿼리를 확장할 때 사용된다.

```python
# HTTP Request의 tags
tags = frozenset({"http", "api", "rest", "request", "integration"})

# 사용자가 "API 호출"을 물어보면:
# → OntologyEnhancer가 "http", "api", "rest" 등을 확장 쿼리에 추가
# → BM25가 이 키워드를 포함한 청크를 더 높은 점수로 검색
```

### 3.4 조회 API

```python
# 어떤 형태로도 노드 정의 조회 가능
get_node_def("httpRequest")                    # short_type
get_node_def("n8n-nodes-base.httpRequest")     # full_type
get_node_def("HTTP Request")                   # display_name

# 내부적으로는 소문자 정규화된 딕셔너리로 O(1) 조회
_NODE_BY_SHORT:   {"httprequest": N8NNodeDef, ...}
_NODE_BY_FULL:    {"n8n-nodes-base.httprequest": N8NNodeDef, ...}
_NODE_BY_DISPLAY: {"http request": N8NNodeDef, ...}
```

### 3.5 NodeTaxonomy가 각 서비스에서 쓰이는 방식

> **검증 참고 (실제 코드 기준):** 아래 두 항목은 이전 버전 문서에서 "NodeTaxonomy 활용"으로 서술되어 있었으나, `feature_services.py`와 `semantic_validator.py`는 `domain_ontology`를 사용하는 `_stage3_relation_pattern()` 외에는 domain_ontology를 import하지 않는다. 실제로 `domain_ontology`(NodeTaxonomy/RelationGraph/PropertyConstraints/WorkflowPatterns)를 import하는 파일은 `ontology_enhancer.py`와 `semantic_validator.py` 단 둘뿐이다.

```
ReverseService (feature_services.py)
  └─ _parse_topology(): domain_ontology를 전혀 import하지 않음
  └─ 자체 정의한 훨씬 작은 집합으로 trigger(5개)/sink(6개)를 하드코딩 분류
     (453개 노드 전체를 다루는 NodeTaxonomy와는 별개의 독립 구현)

SemanticValidator (semantic_validator.py)
  └─ _stage3_relation_pattern(): "merge"/"webhook" 문자열 포함 여부만 검사
  └─ get_node_def()나 NodeRole을 조회하지 않는 순수 문자열 매칭
     (이름은 "관계 패턴 검증"이지만 RelationGraph도 조회하지 않는다 — §9 참고)

OntologyEnhancer (ontology_enhancer.py)  ← NodeTaxonomy를 실제로 쓰는 유일한 곳
  └─ _detect_nodes(): get_node_def()로 조회해 tags와 display_name으로 노드 감지
  └─ _expand_related_terms(): 감지된 노드의 tags를 확장 쿼리에 추가
```

---

## 4. 온톨로지 2: RelationGraph

**목적:** 노드들 사이의 의미적 상관관계를 방향성 가중치 그래프로 명세한다. **이 시스템에서 가장 핵심적인 온톨로지**다.

### 4.1 핵심 데이터 구조

```python
class RelationType(str, Enum):
    COMMONLY_USED_WITH   = "commonly_used_with"   # 실무 co-occurrence
    PREREQUISITE_FOR     = "prerequisite_for"     # 개념적 선행 관계
    COMPLEMENTED_BY      = "complemented_by"      # 기능적 보완 관계
    PATTERN_MEMBER       = "pattern_member"       # 같은 패턴 구성원
    REQUIRES_MULTIPLE_IN = "requires_multiple_in" # 다중 입력 필요
    ANTI_PATTERN_WITH    = "anti_pattern_with"    # 위험한 조합
    REPLACES             = "replaces"             # 기능 대체 관계

@dataclass
class NodeRelation:
    target_type:   str           # 대상 노드 short_type (예: "set")
    relation_type: RelationType
    weight:        float         # 관계 강도: 0.0 ~ 1.0
    description:   str           # 사람이 읽을 수 있는 설명
```

### 4.2 weight(가중치)의 의미와 기준

| 구간 | 의미 | OntologyEnhancer 처리 |
|---|---|---|
| 0.90 ~ 1.00 | 거의 항상 함께 사용 | 쿼리 확장에 포함 (min_weight=0.75 기본) |
| 0.75 ~ 0.89 | 자주 함께 사용 | 쿼리 확장에 포함 |
| 0.60 ~ 0.74 | 상황에 따라 함께 사용 | 쿼리 확장에서 제외 (힌트는 생성) |
| 0.40 ~ 0.59 | 낮음 (주로 경고용) | 쿼리 확장 제외, ANTI-PATTERN 힌트 생성 |

### 4.3 전체 RelationGraph 엣지 목록

#### HTTP Request의 관계

```
httpRequest ──COMMONLY_USED_WITH(0.90)──────→ set
              "API 응답 필드 정제에 Set 노드 조합"

httpRequest ──COMMONLY_USED_WITH(0.85)──────→ if
              "HTTP 상태코드 또는 응답값 조건 분기"

httpRequest ──COMPLEMENTED_BY(0.70)─────────→ splitInBatches
              "대량 API 호출 시 Rate Limit 방지"

httpRequest ──COMPLEMENTED_BY(0.60)─────────→ merge
              "다수 병렬 API 결과 합산"

httpRequest ──ANTI_PATTERN_WITH(0.40)───────→ code
              "Code 노드 내 httpRequest 직접 호출 — 스트리밍/에러 처리 불가"
```

#### Webhook의 관계

```
webhook ──COMMONLY_USED_WITH(0.90)──→ set
           "Webhook 수신 데이터 정제에 Set 노드 필수"

webhook ──COMPLEMENTED_BY(0.95)─────→ respondToWebhook
           "동기 응답이 필요한 경우 반드시 함께 사용"

webhook ──COMMONLY_USED_WITH(0.75)──→ if
           "페이로드 유효성 검증 분기"
```

#### Schedule Trigger의 관계

```
scheduleTrigger ──COMMONLY_USED_WITH(0.95)──→ httpRequest
                   "주기적 API 폴링 패턴에서 가장 빈번하게 조합됨"

scheduleTrigger ──PATTERN_MEMBER(0.80)──────→ slack
                   "정기 보고/알림 패턴 구성원"

scheduleTrigger ──PATTERN_MEMBER(0.70)──────→ googleSheets
                   "주기적 스프레드시트 업데이트 패턴"
```

#### Set의 관계

```
set ──COMMONLY_USED_WITH(0.90)──→ httpRequest
      "API 응답 필드를 다음 노드를 위해 정제"

set ──PREREQUISITE_FOR(0.80)────→ code
      "Set의 assignments 개념 이해 후 Code로 심화"

set ──REPLACES(0.95)────────────→ editFields
      "n8n v1.x에서 editFields 노드가 Set을 대체"
```

#### Split In Batches의 관계

```
splitInBatches ──COMPLEMENTED_BY(0.90)──→ httpRequest
                  "API Rate Limit 대응 — 배치 단위 지연 처리"

splitInBatches ──PATTERN_MEMBER(0.85)───→ merge
                  "Split → 처리 → Merge 패턴"
```

#### Split Out의 관계

```
splitOut ──PATTERN_MEMBER(0.90)──→ merge
            "배열 분리 → 개별 처리 → Merge 패턴"

splitOut ──COMPLEMENTED_BY(0.80)─→ aggregate
            "Split Out 후 결과 집계에 Aggregate 사용"
```

#### Merge의 관계

```
merge ──REQUIRES_MULTIPLE_IN(0.90)──→ splitInBatches
         "Merge는 반드시 2개 이상 입력 필요"

merge ──PATTERN_MEMBER(0.90)────────→ splitOut
         "Split → 처리 → Merge 표준 패턴"
```

#### IF의 관계

```
if ──REPLACES(0.70)──────────→ switch
     "분기 3개 이상이면 Switch 노드가 IF보다 적합"

if ──COMPLEMENTED_BY(0.65)───→ merge
     "IF의 양쪽 분기 결과를 다시 합칠 때"
```

#### Code의 관계

```
code ──PREREQUISITE_FOR(0.80)───→ set (반대 방향)
       "Code 이해 전 Set으로 데이터 변환 개념 선습"

code ──ANTI_PATTERN_WITH(0.60)──→ httpRequest
       "Code 내 HTTP 직접 호출 — n8n 재시도/에러 처리 불가"
```

#### Slack의 관계

```
slack ──PATTERN_MEMBER(0.85)──→ scheduleTrigger
         "정기 보고 패턴 — 스케줄 → 데이터 → 슬랙"

slack ──COMMONLY_USED_WITH(0.80)──→ if
         "에러·임계값 초과 시에만 알림 분기"
```

#### Respond to Webhook의 관계

```
respondToWebhook ──COMPLEMENTED_BY(0.98)──→ webhook
                    "responseMode=responseNode 인 Webhook의 필수 파트너"
```

### 4.4 RelationType별 처리 방식

| RelationType | OntologyEnhancer 처리 | SemanticValidator 처리 |
|---|---|---|
| COMMONLY_USED_WITH | 관련 노드를 확장 쿼리에 추가 | 없음 |
| PREREQUISITE_FOR | LearningGraph와 연계 | 없음 |
| COMPLEMENTED_BY | [RECOMMEND] 힌트 생성 | 없음 |
| PATTERN_MEMBER | 패턴 감지 연계 | 없음 |
| REQUIRES_MULTIPLE_IN | [CONSTRAINT] 힌트 생성 | Merge 다중 입력 검증 |
| ANTI_PATTERN_WITH | [ANTI-PATTERN] 힌트 생성 | Code 내 fetch() 검증 |
| REPLACES | 없음 | 없음 (문서화 목적) |

### 4.5 RelationGraph 시각화

```
                    ┌─────────────────┐
              ┌────►│  Schedule Trigger│◄────────┐
              │     └────────┬────────┘         │
   0.95       │              │ 0.95              │ 0.80
              │              ▼                  │
   ┌──────────┴──┐     ┌─────────────┐   ┌──────┴──┐
   │ Google Sheets│     │ HTTP Request│   │  Slack   │
   └─────────────┘     └──┬──┬──┬───┘   └──────────┘
                    0.90  │  │  │  0.40             
                 ┌────────┘  │  └──────────────┐   
                 │      0.85 │ 0.70            │   
                 ▼           ▼       ▼         ▼   
              ┌──────┐   ┌──────┐  ┌────────┐ ┌──────┐
              │  Set │   │  IF  │  │Split In│ │ Code │
              └──────┘   └──┬───┘  │Batches │ └──────┘
                 ▲     0.70 │ 0.65 └───┬────┘ ← ANTI
                 │          │     0.85 │
                 │          ▼          ▼
                 │       ┌────────┐ ┌───────┐
                 │       │ Switch │ │ Merge │
                 │       └────────┘ └───┬───┘
       0.80      │         ← REPLACES   │ 0.90
                 │                      │
               ┌─┴──────────────────────┴─┐
               │       Split Out           │
               └───────────────────────────┘
```

### 4.6 get_related_display_terms() 함수

RAG 쿼리 확장에 직접 사용되는 함수:

```python
def get_related_display_terms(node_type: str,
                               min_weight: float = 0.75) -> List[str]:
    terms: List[str] = []
    for rel in get_relations(node_type):
        if rel.weight < min_weight:
            continue                    # weight 기준 미달 관계 제외
        related = get_node_def(rel.target_type)
        if related:
            terms.append(related.display_name)      # "Split In Batches"
            terms.extend(list(related.tags)[:3])    # "split", "loop", "batch"
    return list(dict.fromkeys(terms))   # 중복 제거, 순서 유지

# 예시 호출
get_related_display_terms("httpRequest", min_weight=0.75)
→ ["Set", "field", "transform", "mapping",
   "IF", "condition", "branch", "boolean"]
# (0.70인 Split In Batches, 0.40인 Code는 제외)
```

---

## 5. 온톨로지 3: PropertyConstraints

**목적:** 노드 파라미터들 사이의 의존·배제·조건 관계를 형식적 규칙으로 명세한다. LLM이 생성한 코드가 실제로 실행 가능한지 검증하는 데 사용된다.

### 5.1 핵심 데이터 구조

```python
class ConstraintType(str, Enum):
    REQUIRES    = "requires"     # A=설정 시 B도 반드시 설정해야 함
    CONFLICTS   = "conflicts"    # A와 B는 동시에 설정 불가
    CONDITIONAL = "conditional"  # A=특정값 시에만 B 필요
    RECOMMENDED = "recommended"  # 권고 사항 (경고, 오류 아님)
    FORBIDDEN   = "forbidden"    # 절대 사용 금지

class ValidationSeverity(str, Enum):
    ERROR   = "error"    # 즉시 수정 필요 (워크플로우 실행 실패)
    WARNING = "warning"  # 수정 권장 (실행되지만 불안정)
    INFO    = "info"     # 참고 사항 (모범 사례)

@dataclass
class PropertyConstraint:
    node_type:        str                  # "httpRequest"
    property_name:    str                  # "retryOnFail"
    constraint_type:  ConstraintType
    related_property: Optional[str]        # "maxTries"
    trigger_value:    Optional[str]        # "responseNode" (CONDITIONAL 때)
    severity:         ValidationSeverity
    message:          str                  # 사용자에게 보여줄 메시지
```

### 5.2 전체 제약 규칙 30개 상세

---

#### 규칙 1 — HTTP Request: retryOnFail → maxTries (REQUIRES)

```
노드:    httpRequest
속성:    retryOnFail
제약:    REQUIRES → maxTries
심각도:  WARNING
```

**배경:** `retryOnFail: true`로만 설정하면 n8n은 기본 3회 재시도를 한다. 하지만 `maxTries`를 명시하지 않으면 의도치 않은 재시도 횟수가 적용될 수 있다. 특히 API 제한이 엄격한 서비스에서 과도한 재시도는 IP 차단으로 이어진다.

```python
# 위반 예시
parameters = {
    "url": "https://api.example.com/data",
    "retryOnFail": True
    # maxTries가 없음 → WARNING
}

# 올바른 설정
parameters = {
    "url": "https://api.example.com/data",
    "retryOnFail": True,
    "maxTries": 3           # 반드시 명시
}
```

**검증 로직:**
```python
if params.get("retryOnFail") and not params.get("maxTries"):
    → ValidationIssue(WARNING)
```

---

#### 규칙 2 — HTTP Request: retryOnFail → waitBetweenTries (RECOMMENDED)

```
노드:    httpRequest
속성:    retryOnFail
제약:    RECOMMENDED → waitBetweenTries
심각도:  INFO
```

**배경:** 재시도 사이에 대기 없이 즉시 재시도하면 이미 과부하 상태인 서버에 연속 요청을 보내는 셈이다. `waitBetweenTries`(ms 단위)로 대기 시간을 두는 것이 안정적이다.

```python
# 권고 설정
parameters = {
    "retryOnFail": True,
    "maxTries": 3,
    "waitBetweenTries": 1000   # 1초 대기
}
```

---

#### 규칙 3 — HTTP Request: sendBody=true → bodyContentType (CONDITIONAL)

```
노드:    httpRequest
속성:    sendBody
제약:    CONDITIONAL (trigger_value="true") → bodyContentType
심각도:  WARNING
```

**배경:** `sendBody: true`로 요청 본문을 전송할 때 `bodyContentType`을 명시하지 않으면 n8n이 기본값(JSON)을 사용한다. 이는 Form Data나 Raw Binary를 전송해야 하는 API에서 오류를 유발한다.

```python
# 위반 예시
parameters = {
    "method": "POST",
    "sendBody": True,
    "bodyParameters": {"key": "value"}
    # bodyContentType 없음 → WARNING
}

# 올바른 설정
parameters = {
    "method": "POST",
    "sendBody": True,
    "bodyContentType": "json",   # 또는 "form", "raw", "multipartFormData"
    "bodyParameters": {"key": "value"}
}
```

---

#### 규칙 4 — Split In Batches: batchSize (RECOMMENDED)

```
노드:    splitInBatches
속성:    batchSize
제약:    RECOMMENDED
심각도:  INFO
```

**배경:** `batchSize` 기본값은 10이다. 하지만 Rate Limit이 엄격한 API는 더 작게, 내부 처리가 느린 노드가 뒤에 있으면 더 작은 배치를 권장한다. 반대로 API 제한이 없는 내부 데이터 처리는 더 크게 설정할 수 있다.

```python
# 기본값 사용 시 INFO 발생 (설정 검토 권고)
parameters = {}  # batchSize 미설정 → INFO

# 명시 권고
parameters = {
    "batchSize": 5   # API Rate Limit에 맞게 조정
}
```

---

#### 규칙 5 — IF: conditions (REQUIRES)

```
노드:    if
속성:    conditions
제약:    REQUIRES (최소 1개 이상)
심각도:  ERROR
```

**배경:** IF 노드에 `conditions`가 없으면 항상 true 또는 false로 분기되어 실제로 조건 분기 기능을 못한다. 이는 워크플로우 로직 오류다.

```python
# 위반 예시
parameters = {
    "combineOperation": "all"
    # conditions 없음 → ERROR
}

# 올바른 설정
parameters = {
    "combineOperation": "all",
    "conditions": {
        "options": {"leftValue": "={{ $json.status }}", "typeValidation": "strict"},
        "conditions": [{"id": "...", "leftValue": "", "rightValue": "active", "operator": {"type": "string", "operation": "equals"}}]
    }
}
```

---

#### 규칙 6 — Switch: rules (REQUIRES)

```
노드:    switch
속성:    rules
제약:    REQUIRES
심각도:  ERROR
```

**배경:** Switch 노드가 `mode: "rules"`일 때 `rules` 배열이 없으면 모든 항목이 fallback 출력으로 라우팅된다.

---

#### 규칙 7 — Code: jsCode에 fetch() (FORBIDDEN)

```
노드:    code
속성:    jsCode
제약:    FORBIDDEN (trigger_value="fetch(")
심각도:  WARNING
```

**배경:** Code 노드 내에서 `fetch()`로 직접 HTTP 요청을 하면 n8n의 에러 처리, 재시도, 타임아웃 관리를 전혀 받지 못한다. 또한 응답 스트리밍을 지원하지 않고, n8n 실행 로그에도 해당 HTTP 요청이 표시되지 않아 디버깅이 불가능하다.

```javascript
// 위반 예시 (Code 노드 내)
const response = await fetch("https://api.example.com/data");  // FORBIDDEN
const data = await response.json();
return [{ json: data }];

// 올바른 방법: HTTP Request 노드를 별도로 사용
// Code 노드는 이미 가져온 데이터를 가공하는 용도로만 사용
```

---

#### 규칙 8 — Code: jsCode에 $item() (FORBIDDEN)

```
노드:    code
속성:    jsCode
제약:    FORBIDDEN (trigger_value="$item(")
심각도:  ERROR
```

**배경:** `$item()`은 n8n v0.x 구문으로, v1.x에서 완전히 폐기되었다. 사용 시 `TypeError: $item is not a function` 오류가 발생한다. 대신 `$json.fieldName` 또는 `$input.all()` 등을 사용해야 한다.

```javascript
// 위반 예시 (n8n v0.x 구문)
const value = $item(0).$node["HTTP Request"].json.data;  // ERROR

// 올바른 구문 (n8n v1.x)
const value = $json.data;                                // 현재 아이템
const value = $input.all()[0].json.data;                 // 첫 번째 아이템
```

---

#### 규칙 9 — Webhook: responseMode=responseNode → respondToWebhook (CONDITIONAL)

```
노드:    webhook
속성:    responseMode
제약:    CONDITIONAL (trigger_value="responseNode") → respondToWebhook 노드 필요
심각도:  WARNING
```

**배경:** `responseMode: "responseNode"`로 설정하면 Webhook이 즉시 응답을 보내지 않고, 워크플로우 어딘가의 `Respond to Webhook` 노드가 응답을 보낼 때까지 대기한다. 이 노드가 없으면 요청이 타임아웃(30초)될 때까지 응답이 없어 클라이언트가 실패로 인식한다.

```
올바른 패턴:
Webhook (responseMode=responseNode) → ... 처리 ... → Respond to Webhook
                                                              ↑
                                                      이 노드가 반드시 있어야 함
```

**검증 방식 (SemanticValidator):**
```python
has_webhook = any("webhook" in t for t in short_types if t != "respondToWebhook")
has_respond = "respondToWebhook" in short_types
if has_webhook and not has_respond:
    for node in nodes:
        if "webhook" in node.type and node.parameters.responseMode == "responseNode":
            → ValidationIssue(WARNING)
```

---

#### 규칙 10 — Google Sheets: operation=getAll → limit/returnAll (CONDITIONAL)

```
노드:    googleSheets
속성:    operation
제약:    CONDITIONAL (trigger_value="getAll") → limit 또는 returnAll 명시
심각도:  WARNING
```

**배경:** `operation: "getAll"` 시 `returnAll: false`이고 `limit`도 없으면 n8n이 기본적으로 전체 시트를 메모리에 로드한다. 수십만 행의 시트라면 메모리 부족(OOM)이나 타임아웃을 유발한다.

```python
# 위반 예시
parameters = {
    "operation": "getAll"
    # limit/returnAll 없음 → WARNING
}

# 올바른 설정 (예: 상위 100개만)
parameters = {
    "operation": "getAll",
    "returnAll": False,
    "limit": 100
}
```

---

#### 규칙 11~30 — 추가 제약 규칙 요약

| # | 노드 | 속성 | 제약 타입 | 관련 속성/값 | 심각도 |
|---|------|------|---------|------------|------|
| 11 | telegram | chatId | REQUIRES | — | ERROR |
| 12 | telegram | text | REQUIRES | — | ERROR |
| 13 | notion | operation | CONDITIONAL (create) | databaseId | ERROR |
| 14 | notion | operation | CONDITIONAL (getAll) | databaseId | WARNING |
| 15 | airtable | table | REQUIRES | — | ERROR |
| 16 | airtable | base | REQUIRES | — | ERROR |
| 17 | mySql | operation | CONDITIONAL (executeQuery) | query | ERROR |
| 18 | mySql | operation | CONDITIONAL (insert) | table + columns | WARNING |
| 19 | openAi | model | RECOMMENDED | — | INFO |
| 20 | openAi | maxTokens | RECOMMENDED | — | INFO |
| 21 | github | owner | REQUIRES | — | ERROR |
| 22 | github | repository | REQUIRES | — | ERROR |
| 23 | wait | amount | REQUIRES | unit | WARNING |
| 24 | formTrigger | formFields | REQUIRES | — | WARNING |
| 25 | emailSend | toEmail | REQUIRES | — | ERROR |
| 26 | emailSend | fromEmail | RECOMMENDED | — | WARNING |
| 27 | splitInBatches | options.reset | RECOMMENDED | — | INFO |
| 28 | postgres | operation | CONDITIONAL (executeQuery) | query | ERROR |
| 29 | code | jsCode | FORBIDDEN ($items()) | — | ERROR |
| 30 | code | jsCode | FORBIDDEN (require()) | — | WARNING |

**규칙 11~30 배경 요약:**
- **telegram (11, 12):** chatId와 text는 Telegram 메시지 발송의 필수 파라미터. 누락 시 런타임 오류.
- **notion (13, 14):** create·getAll 작업은 대상 데이터베이스 없이 실행 불가.
- **airtable (15, 16):** Airtable은 Base ID와 Table명 모두 지정해야 레코드 조작 가능.
- **mySql (17, 18):** executeQuery 모드는 SQL 쿼리 필수; insert 모드는 테이블·컬럼 구조 필수.
- **openAi (19, 20):** 모델 미지정 시 기본값(gpt-3.5-turbo)이 적용되어 품질 저하 가능성.
- **github (21, 22):** GitHub API는 owner/repository 없이 호출 불가.
- **wait (23):** amount만 있고 unit(seconds/minutes/hours) 없으면 단위 해석 모호.
- **formTrigger (24):** formFields 없는 폼은 빈 폼 — 실질적으로 무의미.
- **emailSend (25, 26):** 수신자 없으면 발송 불가(ERROR); 발신자 미지정 시 기본값이 스팸으로 처리될 수 있음(WARN).
- **splitInBatches (27):** reset 미설정 시 루프 재시작이 작동 안 할 수 있음.
- **postgres (28):** executeQuery 작업은 SQL 없이 실행 불가.
- **code (29, 30):** `$items()`는 n8n v1.x에서 완전 폐기됨(ERROR); `require()`는 보안 정책 위반 가능(WARNING).

---

### 5.3 PropertyConstraints 조회 API

```python
def get_constraints_for_node(node_type: str) -> List[PropertyConstraint]:
    # full_type 또는 short_type 모두 허용
    short = node_type.split(".")[-1]   # "n8n-nodes-base.httpRequest" → "httpRequest"
    return _CONSTRAINTS_BY_NODE.get(short, [])

# 예시
get_constraints_for_node("httpRequest")
→ [
    PropertyConstraint(retryOnFail, REQUIRES, maxTries, WARNING),
    PropertyConstraint(retryOnFail, RECOMMENDED, waitBetweenTries, INFO),
    PropertyConstraint(sendBody, CONDITIONAL, bodyContentType, WARNING)
  ]
```

### 5.4 SemanticValidator에서의 처리 흐름

```
워크플로우 JSON 파싱
       │
       ▼ 각 노드 순회
for node in workflow["nodes"]:
    short_type = node["type"].split(".")[-1]  # "httpRequest"
    params     = node.get("parameters", {})
    constraints = get_constraints_for_node(short_type)
       │
       ▼ 각 제약 규칙 적용
    for c in constraints:
        if c.constraint_type == REQUIRES:
            if params.get(c.property_name) and not params.get(c.related_property):
                → ValidationIssue 생성
        elif c.constraint_type == CONDITIONAL:
            if str(params.get(c.property_name)) == c.trigger_value:
                if not params.get(c.related_property):
                    → ValidationIssue 생성
        elif c.constraint_type == FORBIDDEN:
            if c.trigger_value in str(params.get(c.property_name, "")):
                → ValidationIssue 생성
```

---

## 6. 온톨로지 4: WorkflowPatterns

**목적:** 실무에서 검증된 노드 조합 패턴을 명세하고, 해당 패턴의 모범 사례(best practices)와 안티패턴(anti-patterns)을 LLM에 자동 주입한다.

### 6.1 핵심 데이터 구조

```python
@dataclass
class WorkflowPattern:
    name:           str            # "periodic_api_monitor"
    description:    str            # 한 문장 설명
    node_types:     List[str]      # 패턴 구성 노드 (short_type)
    connections:    List[tuple]    # (source, target) 연결 엣지
    best_practices: List[str]      # 권고 사항 목록
    anti_patterns:  List[str]      # 피해야 할 조합 목록
    data_type_hints: List[str]     # 관련 RAG data_type 힌트
```

### 6.2 전체 11개 패턴 상세

---

#### 패턴 1: periodic_api_monitor (주기적 API 모니터링 알림)

```
노드 구성: scheduleTrigger → httpRequest → if → slack

흐름도:
  ┌─────────────┐     ┌─────────────┐     ┌──────┐     ┌──────┐
  │ Schedule    │────►│ HTTP Request│────►│  IF  │────►│Slack │
  │ Trigger     │     │ (API 폴링) │     │(분기)│     │(알림)│
  └─────────────┘     └─────────────┘     └──────┘     └──────┘
  매일/매시간                                true: 이상 감지
                                           false: 정상 (알림 없음)
```

**Best Practices:**
- `retryOnFail: true + maxTries: 3` on HTTP Request — API 일시 장애에 대응
- IF 노드로 정상(false branch)/이상(true branch) 응답 분기
- Slack 알림은 이상 시에만 발송 (false 분기) — 알림 피로 방지

**Anti-Patterns:**
- HTTP Request에 `retryOnFail` 미설정 — 일시 장애 시 워크플로우 실패
- 에러 응답(status ≥ 400)을 IF로 분기하지 않고 무시

**관련 RAG data_type:** `troubleshooting`, `api_limits`, `official_docs`

**패턴 감지 조건:** `{scheduleTrigger, slack}` 또는 `{scheduleTrigger, httpRequest}` 등 2개 이상 노드 매칭

---

#### 패턴 2: webhook_response (Webhook 동기 응답)

```
노드 구성: webhook → set → respondToWebhook

흐름도:
  ┌──────────┐     ┌─────┐     ┌──────────────────┐
  │ Webhook  │────►│ Set │────►│ Respond to       │
  │(수신)   │     │(정제)│     │ Webhook (응답)   │
  └──────────┘     └─────┘     └──────────────────┘
  HTTP 요청 수신          응답 데이터 구성    HTTP 응답 전송
```

**핵심 설정:**
```python
# Webhook 노드
parameters = {
    "httpMethod": "POST",
    "responseMode": "responseNode",   # 반드시 이 설정
    "path": "my-webhook"
}
```

**Best Practices:**
- `responseMode: "responseNode"` 설정 필수
- Set으로 응답 데이터 정제 후 respondToWebhook
- 처리 시간 < 30초 유지 (Webhook 타임아웃)

**Anti-Patterns:**
- `responseMode: "immediately"`로 빈 응답 반환 (클라이언트가 결과 수신 불가)
- Respond to Webhook 노드 누락 (요청 타임아웃)

---

#### 패턴 3: batch_api_processing (대량 항목 API 처리)

```
노드 구성: splitInBatches → httpRequest → aggregate

흐름도:
  ┌──────────────────┐     ┌─────────────┐     ┌───────────┐
  │ Split In Batches │────►│ HTTP Request│────►│ Aggregate │
  │ (배치 분할)      │     │ (API 호출) │     │ (결과 집계)│
  └──────────────────┘     └─────────────┘     └───────────┘
  10개씩 분할              각 배치마다 호출     전체 결과 수집
```

**Best Practices:**
- `batchSize`를 API Rate Limit에 맞게 설정 (초당 요청 수 제한 고려)
- `waitBetweenTries`로 요청 간격 조절
- Aggregate로 배치 결과 수집하여 단일 출력으로 합산

**Anti-Patterns:**
- `batchSize` 미설정으로 전체 항목을 한 번에 요청 → Rate Limit 초과

---

#### 패턴 4: etl_pipeline (데이터 수집 → 변환 → 저장)

```
노드 구성: scheduleTrigger → httpRequest → set → googleSheets

흐름도:
  ┌─────────────┐     ┌─────────────┐     ┌─────┐     ┌──────────────┐
  │ Schedule    │────►│ HTTP Request│────►│ Set │────►│Google Sheets │
  │ Trigger     │     │ (데이터 수집)│     │(변환)│     │ (저장)      │
  └─────────────┘     └─────────────┘     └─────┘     └──────────────┘
```

**Best Practices:**
- Set 노드로 스키마 정규화 후 Sheets 저장
- `operation: "appendOrUpdate"` + matchingColumns로 중복 방지
- 시트 최대 행 수 고려 → 정기 아카이빙 설계

---

#### 패턴 5: array_process_merge (배열 분리 → 처리 → 재합산)

```
노드 구성: splitOut → httpRequest → merge

흐름도:
  ┌──────────┐     ┌─────────────┐     ┌───────┐
  │ Split Out│────►│ HTTP Request│────►│ Merge │
  │ (분리)   │     │ (개별 처리) │     │ (합산)│
  └──────────┘     └─────────────┘     └───────┘
  배열 → 개별 아이템    아이템마다 API 호출    결과 모음
```

**Best Practices:**
- Merge의 `mode: "combineAll"` 또는 적절한 병합 전략 선택
- 대량 배열은 Split In Batches 후 Split Out 권장

**Anti-Patterns:**
- Merge 노드에 단일 입력만 연결 (구조 오류, 항상 에러)

---

#### 패턴 6: ai_data_transform (AI 기반 데이터 변환)

```
노드 구성: httpRequest → set → openAi → set

흐름도:
  ┌────────────┐   ┌─────┐   ┌────────┐   ┌─────┐
  │ HTTP       │──►│ Set │──►│ OpenAI │──►│ Set │──► 다음 처리
  │ Request    │   │(정제)│   │(변환)  │   │(저장)│
  └────────────┘   └─────┘   └────────┘   └─────┘
  외부 데이터 수집    전처리     AI 분석·변환   결과 정규화
```

**Best Practices:**
- 첫 번째 Set으로 AI에 넘길 텍스트 필드만 명시적으로 추출
- OpenAI 노드에 `model`, `maxTokens` 명시 (기본값 의존 금지)
- 두 번째 Set으로 AI 응답 파싱·정규화 후 다음 노드에 전달

**Anti-Patterns:**
- 전처리 없이 API 원시 응답을 OpenAI에 직접 전달 → 프롬프트 토큰 낭비

---

#### 패턴 7: telegram_bot (Telegram 챗봇)

```
노드 구성: telegramTrigger → if → telegram

흐름도:
  ┌──────────────┐   ┌──────┐   ┌──────────┐
  │ Telegram     │──►│  IF  │──►│ Telegram │
  │ Trigger      │   │(분류)│   │(응답)    │
  └──────────────┘   └──────┘   └──────────┘
  메시지 수신          명령어 분류   응답 발송
```

**Best Practices:**
- IF 노드로 `/start`, `/help` 등 명령어 분기
- Telegram 응답에 `chat_id: {{ $json.message.chat.id }}` 동적 참조

**Anti-Patterns:**
- 모든 메시지에 동일 응답 (IF 분기 없음) → 봇 UX 저하

---

#### 패턴 8: form_collect (폼 데이터 수집·알림)

```
노드 구성: formTrigger → set → googleSheets + emailSend

흐름도:
  ┌────────────┐   ┌─────┐   ┌─────────────┐
  │ Form       │──►│ Set │──►│ Google      │
  │ Trigger    │   │(정규화)│ │ Sheets (저장)│
  └────────────┘   └─────┘   └─────────────┘
                       │      ┌─────────────┐
                       └─────►│ emailSend   │
                              │ (확인 메일) │
                              └─────────────┘
```

**Best Practices:**
- Set으로 폼 필드 이름을 DB 컬럼 이름으로 정규화
- emailSend로 제출자에게 자동 확인 이메일 발송

---

#### 패턴 9: file_processing (파일 ETL)

```
노드 구성: googleDriveTrigger → extractFromFile → set → googleSheets

흐름도:
  ┌─────────────┐   ┌─────────────┐   ┌─────┐   ┌──────────────┐
  │ Google Drive│──►│ Extract     │──►│ Set │──►│ Google       │
  │ Trigger     │   │ From File   │   │(정제)│   │ Sheets (저장)│
  └─────────────┘   └─────────────┘   └─────┘   └──────────────┘
  새 파일 감지        CSV/Excel 파싱    필드 정규화   데이터베이스화
```

**Best Practices:**
- extractFromFile의 출력 구조에 맞게 Set 노드 필드 매핑
- 대량 행은 splitInBatches 추가 후 Sheets 배치 삽입

---

#### 패턴 10: github_cicd_notify (GitHub CI/CD 알림)

```
노드 구성: githubTrigger → if → slack + jira

흐름도:
  ┌────────────┐   ┌──────┐   ┌──────┐
  │ GitHub     │──►│  IF  │──►│Slack │ (성공 알림)
  │ Trigger    │   │(결과)│   └──────┘
  └────────────┘   └──────┘   ┌──────┐
                               │Jira  │ (실패 티켓 생성)
                               └──────┘
```

**Best Practices:**
- IF 조건을 `{{ $json.action }}` 또는 `{{ $json.conclusion }}` 기준으로 설정
- 성공 → Slack 알림 / 실패 → Jira 자동 티켓 생성

---

#### 패턴 11: error_monitoring (워크플로우 에러 감시)

```
노드 구성: errorTrigger → set → slack

흐름도:
  ┌──────────────┐   ┌─────────────────────────┐   ┌──────┐
  │ Error        │──►│ Set                     │──►│Slack │
  │ Trigger      │   │(에러 메시지 구성)         │   │(경보)│
  └──────────────┘   └─────────────────────────┘   └──────┘
  워크플로우 에러 감지   워크플로우명·에러내용 추출    팀 즉시 알림
```

**Best Practices:**
- Set 노드에서 `$workflow.name`, `$execution.id`, `$json.message` 추출
- Slack 알림에 n8n 실행 URL 포함으로 즉시 디버깅 가능하도록 구성

**사용법:** Workflow 설정 > Error Workflow에 이 워크플로우를 지정

---

### 6.3 패턴 감지 알고리즘

```python
def get_pattern_for_nodes(node_types: List[str]) -> Optional[WorkflowPattern]:
    shorts = set(t.split(".")[-1] for t in node_types)  # short_type으로 정규화
    
    best_match = None
    best_score = 0
    
    for pattern in WORKFLOW_PATTERNS:
        overlap = len(shorts & set(pattern.node_types))   # 교집합 크기
        if overlap > best_score:
            best_score = overlap
            best_match = pattern
    
    return best_match if best_score >= 2 else None   # 2개 이상 겹쳐야 패턴 인식

# 예시
get_pattern_for_nodes(["scheduleTrigger", "httpRequest", "if", "slack"])
→ periodic_api_monitor (overlap=4)

get_pattern_for_nodes(["webhook", "set"])
→ webhook_response (overlap=2)

get_pattern_for_nodes(["set"])
→ None (1개만 겹침, 패턴 인식 불가)
```

### 6.4 패턴 힌트가 LLM 프롬프트에 삽입되는 위치

```python
# workspace.py → WorkflowBuildService 전달
ctx["ontology_hints"] = eq.ontology_hints

# workflow_services.py — WorkflowBuildService.stream()
hint_block = "\n\n[온톨로지 관계 힌트]\n" + "\n".join(ontology_hints)
context_str = _build_context(chunks) + hint_block
system = _WORKFLOW_BUILD_SYSTEM_PROMPT.format(context=context_str)

# 실제 프롬프트에 추가되는 내용 예시:
"""
[온톨로지 관계 힌트]
[PATTERN] 'periodic_api_monitor': 주기적 API 폴링 → 조건 분기 → 알림 패턴
[BEST-PRACTICE] retryOnFail: true + maxTries: 3 on HTTP Request
[BEST-PRACTICE] IF 노드로 정상/이상 응답 분기
[BEST-PRACTICE] Slack 알림은 이상 시에만 발송 (false 분기)
[ANTI-PATTERN] HTTP Request에 retryOnFail 미설정
[ANTI-PATTERN] 에러 응답 무시
"""
```

---

## 7. 온톨로지 5: LearningGraph

**목적:** 학습 개념들 사이의 선행 의존성을 방향성 그래프로 명세하여, CurriculumService가 올바른 학습 순서의 커리큘럼을 생성하도록 지원한다.

### 7.1 핵심 데이터 구조

```python
@dataclass
class LearningNode:
    concept:       str         # 학습 개념 식별자 (예: "http_api")
    node_types:    List[str]   # 이 개념이 다루는 n8n 노드들
    prerequisites: List[str]  # 먼저 배워야 할 concept 목록
    level:         str         # "beginner" / "intermediate" / "advanced"
    est_minutes:   int         # 예상 학습 시간 (분)
```

### 7.2 전체 17개 학습 노드

| concept | 다루는 노드 (주요) | 선행 조건 | 레벨 | 시간 |
|---|---|---|---|---|
| n8n_basics | manualTrigger, set | 없음 | beginner | 30분 |
| triggers | scheduleTrigger, webhook, formTrigger | n8n_basics | beginner | 45분 |
| data_transformation | set, splitOut, aggregate, itemLists | n8n_basics | beginner | 60분 |
| conditional_logic | if, switch, filter | data_transformation | intermediate | 60분 |
| http_api | httpRequest | triggers + data_transformation | intermediate | 75분 |
| error_handling | httpRequest (retry/error), stopAndError | http_api | intermediate | 60분 |
| external_services | slack, gmail, googleSheets, postgres | http_api + data_transformation | intermediate | 90분 |
| batch_processing | splitInBatches, merge | http_api + conditional_logic | advanced | 90분 |
| webhook_integration | webhook, respondToWebhook | http_api + conditional_logic | advanced | 90분 |
| custom_code | code | data_transformation + http_api | advanced | 90분 |
| messaging_bots | telegramTrigger, telegram, whatsApp | triggers | intermediate | 60분 |
| file_operations | googleDrive, extractFromFile, convertToFile | data_transformation | intermediate | 60분 |
| form_handling | formTrigger, form, set | triggers | intermediate | 45분 |
| data_processing | summarize, compareDatasets, openAi | data_transformation | intermediate | 60분 |
| workflow_automation | executeWorkflow, executeWorkflowTrigger | conditional_logic + external_services | advanced | 90분 |
| crm_integration | hubspot, salesforce, notion, airtable | webhook_integration + data_transformation | advanced | 90분 |
| ai_integration | openAi, code, httpRequest | http_api + data_transformation | advanced | 90분 |

### 7.3 선행 의존성 그래프 전체

```
                         ┌─────────────────┐
                         │   n8n_basics    │ (beginner, 30분)
                         │  manualTrigger  │
                         │      set        │
                         └────────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   │
       ┌────────────┐    ┌─────────────────┐          │
       │  triggers  │    │data_transform   │          │
       │ schedule,  │    │set,splitOut,    │          │
       │ webhook,   │    │aggregate,items  │          │
       │ formTrigger│    └───────┬─────────┘          │
       └─────┬──────┘           │                     │
             │        ┌─────────┴──────────────┐      │
             │        │                        │      │
             ▼        ▼                        ▼      │
      ┌──────────┐ ┌────────────┐        ┌─────────┐  │
      │messaging │ │conditional │        │http_api │  │
      │_bots     │ │_logic      │        │HTTP     │  │
      │tg,wa     │ │if,switch   │        │Request  │  │
      └──────────┘ └────┬───────┘        └────┬────┘  │
                        │                     │        │
              ┌─────────┤             ┌───────┴──────┐ │
              │         │             │              │ │
              ▼         │             ▼              ▼ ▼
      ┌──────────┐       │    ┌──────────────┐ ┌──────────────┐
      │ form_    │       │    │error_handling│ │external      │
      │ handling │       │    │(retry,stop)  │ │services      │
      │formTrigger│      │    └──────────────┘ │slack,gmail,  │
      └──────────┘       │                     │sheets,pg     │
                         │                     └──────┬───────┘
                         │                            │
                    ┌────┴────────────────────────────┤
                    │                                 │
                    ▼                                 ▼
             ┌───────────┐                   ┌────────────────┐
             │batch_proc │                   │webhook_integrat│
             │splitBatch,│                   │Webhook +       │
             │merge      │                   │respondToWebhook│
             └───────────┘                   └───────┬────────┘
                                                     │
                                            ┌────────┴────────┐
                                            ▼                 ▼
                                     ┌─────────────┐  ┌──────────────┐
                                     │crm_integrat │  │workflow_auto │
                                     │hubspot,     │  │executeWorkfl,│
                                     │salesforce,  │  │subworkflow   │
                                     │notion       │  └──────────────┘
                                     └─────────────┘

  data_transformation ──────────────────────────────┐
  http_api           ──────────────────────────────►│ ai_integration
                                                     │ openAi, code
                                                     └─────────────
  data_transformation ──────────────────────────────┐
                                                     │ data_processing
                                                     │ summarize,
                                                     │ compareDatasets
                                                     └─────────────
  data_transformation ──────────────────────────────┐
                                                     │ file_operations
                                                     │ googleDrive,
                                                     │ extractFromFile
                                                     └─────────────
  http_api + data_transformation ───────────────────►  custom_code
                                                        Code Node
```

### 7.4 get_learning_prerequisites() 함수

특정 개념의 전체 선행 체인을 재귀적으로 반환한다:

```python
def get_learning_prerequisites(concept: str) -> List[LearningNode]:
    result: List[LearningNode] = []
    visited: Set[str] = set()

    def _dfs(c: str) -> None:
        if c in visited:
            return
        visited.add(c)
        node = _LEARNING_BY_CONCEPT.get(c)
        if not node:
            return
        for pre in node.prerequisites:
            _dfs(pre)            # 재귀: 선행의 선행도 포함
        result.append(node)

    node = _LEARNING_BY_CONCEPT.get(concept)
    if node:
        for pre in node.prerequisites:
            _dfs(pre)
    return result

# 예시: "custom_code"를 배우려면 무엇이 필요한가?
get_learning_prerequisites("custom_code")
→ [
    LearningNode("n8n_basics",          level="beginner",      est_minutes=45),
    LearningNode("triggers",            level="beginner",      est_minutes=45),
    LearningNode("data_transformation", level="beginner",      est_minutes=60),
    LearningNode("http_api",            level="intermediate",  est_minutes=60),
  ]
# 즉, custom_code 전에 이 4개 개념을 학습해야 함
```

### 7.5 CurriculumService와의 연계

현재 CurriculumService는 레벨별 RAG 필터를 결정할 때 LearningGraph를 간접적으로 활용한다:

```python
# workflow_services.py — CurriculumService
_LEVEL_TO_RAG_FILTER = {
    "beginner":     {"entry", "beginner", "official_docs", "book"},
    "intermediate": {"intermediate", "official_docs", "book", "spec"},
    "advanced":     {"advanced", "spec", "troubleshooting", "api_limits"},
}

# 예: "고급 학습자"가 batch_processing을 물어보면
# → LearningGraph에서 선행 조건: http_api + conditional_logic
# → advanced 레벨 RAG 필터 적용
# → spec + troubleshooting 청크 위주로 검색
```

---

## 8. 온톨로지 간 협력 흐름

### 8.1 실제 처리 추적 예시 1

**입력:** "슬랙으로 날씨 API 결과 매일 오전 9시에 보내는 워크플로우 만들어줘"

```
Step 1: OntologyEnhancer._detect_nodes()
  ──────────────────────────────────────
  "슬랙" → _KO_TO_SHORT["슬랙"] = "slack"
         → get_node_def("slack") → NodeTaxonomy 조회
         → N8NNodeDef(slack, SINK, tags={notification, message, ...})

  "API" → 직접 매칭 없음 (http_api는 쿼리 태그, 노드명 아님)

  "날씨" → 직접 매칭 없음

  "매일 오전 9시" → _KO_TO_SHORT["정기"] = "scheduleTrigger"
                 → N8NNodeDef(scheduleTrigger, TRIGGER, ...)

  감지된 노드: [Slack, Schedule Trigger]

Step 2: OntologyEnhancer._expand_related_terms()
  ──────────────────────────────────────────────
  Slack의 relations (weight≥0.75):
    → scheduleTrigger(0.85): "Schedule Trigger", "schedule", "cron", "automation"
    → if(0.80): "IF", "condition", "branch", "boolean"

  Schedule Trigger의 relations (weight≥0.75):
    → httpRequest(0.95): "HTTP Request", "http", "api", "rest", "request"
    → slack(0.80): 이미 감지됨, 중복 제외

  추가된 용어: [Schedule Trigger, schedule, cron, automation, IF, condition,
               HTTP Request, http, api, rest, request]

Step 3: OntologyEnhancer._detect_pattern()
  ────────────────────────────────────────
  detected = {slack, scheduleTrigger}
  periodic_api_monitor.node_types = {scheduleTrigger, httpRequest, if, slack}
  overlap = |{slack, scheduleTrigger} ∩ {scheduleTrigger, httpRequest, if, slack}|
          = |{slack, scheduleTrigger}| = 2
  2 ≥ 2 → 패턴 매칭!

Step 4: OntologyEnhancer._build_ontology_hints()
  ────────────────────────────────────────────────
  pattern = periodic_api_monitor
  →  [PATTERN] 'periodic_api_monitor': 주기적 API 폴링 → 조건 분기 → 알림 패턴
  →  [BEST-PRACTICE] retryOnFail: true + maxTries: 3 on HTTP Request
  →  [BEST-PRACTICE] IF 노드로 정상/이상 응답 분기
  →  [BEST-PRACTICE] Slack 알림은 이상 시에만 발송 (false 분기)
  →  [ANTI-PATTERN] HTTP Request에 retryOnFail 미설정
  →  [ANTI-PATTERN] 에러 응답 무시

Step 5: 확장된 RAG 쿼리 전송
  ─────────────────────────
  original: "슬랙으로 날씨 API 결과 매일 오전 9시에 보내는 워크플로우 만들어줘"
  expanded: "슬랙으로 날씨 API 결과 매일 오전 9시에 보내는 워크플로우 만들어줘
             Schedule Trigger schedule cron automation
             IF condition branch boolean
             HTTP Request http api rest request integration"

  → BM25: "schedule", "http", "api", "cron" 등 키워드 포함 청크 더 높은 점수
  → 벡터: 의미 확장된 쿼리로 더 광범위한 관련 청크 검색

Step 6: Ontology Reranking
  ─────────────────────────
  감지 노드: {slack, scheduleTrigger}
  관련 노드: {httpRequest, if} (RelationGraph에서 확장)

  각 청크에 boost 적용:
    청크 A: "HTTP Request retryOnFail 설정" → httpRequest 포함 → +0.15
    청크 B: "Schedule Trigger interval" → scheduleTrigger 포함 → +0.15
    청크 C: "Postgres 연결 설정" → 관련 없음 → boost 없음

Step 7: LLM 프롬프트 구성
  ────────────────────────
  system = _WORKFLOW_BUILD_SYSTEM_PROMPT.format(
      context = RAG_context + hint_block
  )

  hint_block =
    [온톨로지 관계 힌트]
    [PATTERN] 'periodic_api_monitor': ...
    [BEST-PRACTICE] retryOnFail: true + maxTries: 3 on HTTP Request
    [ANTI-PATTERN] HTTP Request에 retryOnFail 미설정

Step 8: LLM 생성 결과 (일부)
  ────────────────────────────
  ```json
  {
    "nodes": [
      {"name": "9시 스케줄", "type": "n8n-nodes-base.scheduleTrigger", ...},
      {"name": "날씨 API", "type": "n8n-nodes-base.httpRequest",
       "parameters": {"retryOnFail": true, "maxTries": 3}},    ← 힌트 반영
      {"name": "결과 확인", "type": "n8n-nodes-base.if", ...}, ← 힌트 반영
      {"name": "슬랙 알림", "type": "n8n-nodes-base.slack", ...}
    ],
    ...
  }
  ```

Step 9: SemanticValidator 검증
  ─────────────────────────────
  Stage 2 구조 검증: 통과 (nodes, connections 존재, 참조 무결성 OK)
  Stage 3 속성 제약:
    "날씨 API" 노드: retryOnFail=true, maxTries=3 → 제약 1 통과
  Stage 4 패턴 검증:
    periodic_api_monitor 패턴 감지 → best_practices 첨부
  Stage 4 표현식 검증:
    $item() 없음 → 통과

  result = ValidationReport(is_valid=True, issues=[], pattern=periodic_api_monitor)
  → 이슈 없으므로 validation_report 이벤트 미발행 (조용히 처리)
```

### 8.2 실제 처리 추적 예시 2

**입력:** 워크플로우 JSON 제출 (retryOnFail=true, maxTries 없음, MissingNode 참조)

```
Step 1: REG Stage 1
  → 파라미터 오타 없음 → reg_warning 미발행

Step 2: SemanticValidator Stage 2 (구조 검증)
  connections["Call API"]["main"][[{"node": "MissingNode"}]]
  → "MissingNode"가 nodes 배열에 없음
  → ValidationIssue(stage="structural", severity=ERROR,
      message="연결 대상 노드 'MissingNode'가 nodes 배열에 없습니다.")

Step 3: SemanticValidator Stage 3 (속성 제약)
  node "Call API": type=httpRequest, parameters={retryOnFail: true}
  → get_constraints_for_node("httpRequest")
    → PropertyConstraint(retryOnFail, REQUIRES, maxTries, WARNING)
    → params.retryOnFail=True, params.maxTries=None
  → ValidationIssue(stage="property", severity=WARNING,
      message="`retryOnFail: true` 설정 시 `maxTries`를 반드시 지정해야 합니다.")

  → PropertyConstraint(retryOnFail, RECOMMENDED, waitBetweenTries, INFO)
  → ValidationIssue(stage="property", severity=INFO,
      message="`waitBetweenTries` 설정으로 서버 과부하를 방지하세요.")

Step 4: SemanticValidator Stage 4 (관계·패턴)
  → Merge 없음, Webhook 없음, Code 없음 → 패턴 검증 이슈 없음
  → $item() 없음 → 표현식 검증 이슈 없음

결과:
  ValidationReport(
    is_valid=False,        ← ERROR가 있으므로
    issues=[
      ValidationIssue(structural, ERROR,   "MissingNode 없음"),
      ValidationIssue(property,   WARNING, "maxTries 필요"),
      ValidationIssue(property,   INFO,    "waitBetweenTries 권고"),
    ],
    pattern=periodic_api_monitor,
    best_practices=["retryOnFail: true + maxTries: 3 ...", ...]
  )

SSE 이벤트 발행:
  2:[{
    "type": "validation_report",
    "is_valid": false,
    "error_count": 1,
    "warning_count": 1,
    "issues": [
      {"stage": "structural", "severity": "error",
       "node": "MissingNode",
       "message": "연결 대상 노드 'MissingNode'가 nodes 배열에 없습니다.",
       "suggestion": "nodes에 'MissingNode'을 추가하거나 연결을 수정하세요."},
      {"stage": "property", "severity": "warning",
       "node": "Call API", "property": "retryOnFail",
       "message": "`retryOnFail: true` 설정 시 `maxTries`를 반드시 지정해야 합니다.",
       "suggestion": "`maxTries`를 parameters에 추가하세요."}
    ],
    "pattern": "periodic_api_monitor",
    "best_practices": ["retryOnFail: true + maxTries: 3 on HTTP Request", ...]
  }]
```

### 8.3 실제 처리 추적 예시 3 — 오타 입력 + 할루시네이션 차단

**입력:** "앱훅이 뭐야?" (웹훅의 오타 — ㅔ↔ㅐ 혼동)

```
Step 1: OntologyEnhancer._detect_nodes()
  ──────────────────────────────────────
  [Step 1~4 exact match 전부 실패]
  "앱훅이" → n8n-nodes-base 패턴 없음
           → camelCase 매칭 없음
           → display_name "앱훅이" 없음
           → _KO_TO_SHORT["앱훅이"] 없음

  [Step 5: 한국어 퍼지 매칭 실행]
  _tokenize_ko("앱훅이 뭐야?") → ["앱훅이", "뭐야", "앱훅이 뭐야"]

  token="앱훅이" → _strip_ko_particle → stripped="앱훅"
  _decompose_jamo("앱훅") → "ㅇㅐㅂㅎㅜㄱ" (6 jamo)
  _fuzzy_threshold(6) → thresh=1

  후보 비교:
    "웹훅" → "ㅇㅞㅂㅎㅜㄱ" → levenshtein("ㅇㅐㅂㅎㅜㄱ", "ㅇㅞㅂㅎㅜㄱ") = 1 ≤ 1 ✓
    → best_short="webhook", best_dist=1

  → 반환: ("webhook", "앱훅", dist=1)
  → dist > 0 → typo_corrections.append(("앱훅", "Webhook"))
  → found["webhook"] = N8NNodeDef(webhook, TRIGGER, ...)

  감지된 노드: [Webhook]
  typo_corrections: [("앱훅", "Webhook")]

Step 2: expand_related_terms()
  ──────────────────────────────
  Webhook relations (weight≥0.75):
    → set(0.90), respondToWebhook(0.95), if(0.75)
  expanded_query += "Set IF Respond to Webhook http trigger event"

Step 3: RAG 검색
  ──────────────────────────────
  expanded_query로 webhook 관련 청크 정상 검색
  (오타가 없었다면 놓쳤을 문서들을 포함)

Step 4: LLM 프롬프트 구성
  ──────────────────────────────
  system += """
  [⚠ 오타 자동 교정 — 매우 중요]
  사용자가 입력한 단어에 오타가 감지되어 아래와 같이 교정하였습니다.
    - '앱훅' → Webhook
  규칙:
  1. 오타 단어(교정 전)는 실제로 존재하지 않는 용어입니다.
     절대 별도 개념으로 설명하지 마십시오.
  2. '비공식 표현', '구어체', '약어' 등으로 정당화하지 마십시오.
  3. 교정된 공식 노드명만 기준으로 답변하십시오.
  """

Step 5: LLM 응답 (기대)
  ──────────────────────────────
  Good: "(입력하신 '앱훅'은 'Webhook'의 오타로 인식됩니다)
         Webhook 노드는 외부 서비스가 n8n으로 데이터를 전송할 때..."

  Bad (이전): "앱훅(App Hook)이란 특정 애플리케이션이 제공하는 이벤트 발생
               지점을 의미합니다..." ← 이 할루시네이션이 차단됨
```

---

## 9. 활용 컴포넌트별 온톨로지 사용 매핑

### 9.1 OntologyEnhancer (ontology_enhancer.py)

```
사용 온톨로지:
  ├─ NodeTaxonomy    → _detect_nodes() 6단계 파이프라인
  │    Step 1: full_type 패턴 (n8n-nodes-base.xxx)
  │    Step 2: camelCase short_type regex (453개 전체 동적 생성)
  │    Step 3: display_name / tag 정확 매칭 (453개, 최장 우선)
  │    Step 4: 한국어 키워드 정확 매칭 (80+개, 단어 경계 체크)
  │    Step 5: 한국어 퍼지 매칭 (자모 분해 + Levenshtein) ← 신규
  │    Step 6: 영어 퍼지 매칭 (문자 Levenshtein)          ← 신규
  ├─ RelationGraph   → _expand_related_terms() (관련 노드 용어 확장)
  ├─ RelationGraph   → _build_ontology_hints() (ANTI-PATTERN, RECOMMEND 힌트)
  └─ WorkflowPatterns → _detect_pattern() + best_practices 수집

출력:
  EnhancedQuery {
    expanded_query,      → HybridRetriever에 입력 (더 넓은 검색)
    detected_nodes,      → Ontology Reranking에 사용
    filter_types,        → Intent별 RAG data_type 필터
    pattern,             → validation_report의 pattern 필드
    ontology_hints,      → ctx["ontology_hints"] → LLM 프롬프트 삽입
    typo_corrections,    → ctx["typo_corrections"] → LLM 할루시네이션 차단 ← 신규
  }
```

**typo_corrections 동작 원리:**

```python
# 퍼지 매칭에서 edit_dist > 0 이면 교정 기록
# ("앱훅", "Webhook"), ("webhok", "Webhook") 형태로 수집

# 이후 LLM 시스템 프롬프트에 자동 주입:
"[⚠ 오타 자동 교정]
 '앱훅' → Webhook
 오타 단어는 실제로 존재하지 않는 용어입니다.
 절대 별도 개념으로 설명하거나 '비공식 표현'으로 정당화하지 마십시오."
```

→ LLM이 "앱훅(App Hook)"이라는 없는 개념을 창작하는 **할루시네이션 차단**

### 9.2 SemanticValidator (semantic_validator.py)

```
사용 온톨로지:
  ├─ NodeTaxonomy        → extract_node_short_types() (워크플로우 노드 파악)
  ├─ PropertyConstraints → _stage2_property_constraints() (10개 규칙 적용)
  ├─ RelationGraph       → _stage3_relation_pattern()
  │    (Merge REQUIRES_MULTIPLE_IN, Webhook+RespondToWebhook COMPLEMENTED_BY)
  └─ WorkflowPatterns    → get_pattern_for_nodes() (감지된 패턴의 best_practices)

출력:
  ValidationReport {
    is_valid,           → SSE "validation_report" 이벤트 is_valid 필드
    issues[],           → 에러/경고/info 목록
    pattern,            → 감지된 패턴명
    best_practices,     → 패턴의 모범 사례 목록
  }
```

### 9.3 WorkflowBuildService / GeneralRAGService / ExpressionService

```
사용 온톨로지 (ctx를 통해 간접 사용):
  ├─ ctx["ontology_hints"]    → hint_block → system 프롬프트에 삽입
  │    (RelationGraph + WorkflowPatterns 힌트: ANTI-PATTERN, BEST-PRACTICE)
  └─ ctx["typo_corrections"]  → system 프롬프트에 교정 주입 ← 신규
       ex) [("앱훅", "Webhook")] → LLM에게 오타 단어가
           실재 개념이 아님을 명시 → 할루시네이션 차단

직접 호출하지 않음 — workspace.py가 OntologyEnhancer를 실행하고
ctx에 결과를 담아 세 서비스 모두에 동일하게 전달
```

### 9.4 CurriculumService (workflow_services.py)

```
사용 온톨로지:
  └─ NodeTaxonomy (간접) → _detect_level()로 사용자 레벨 감지
  └─ LearningGraph (간접) → 레벨별 RAG 필터 결정에 반영

  _LEVEL_TO_RAG_FILTER = {
      "beginner":     {"entry", "beginner", "official_docs", "book"},
      "intermediate": {"intermediate", "official_docs", "book", "spec"},
      "advanced":     {"advanced", "spec", "troubleshooting", "api_limits"},
  }
  (이 필터 자체가 LearningGraph의 레벨 분류를 반영)
```

### 9.5 IntentRouter (intent_router.py)

```
사용 온톨로지:
  └─ NodeTaxonomy (간접) — _parse_topology()에서 노드 역할 분류
     (직접 import 없음, ReverseService가 유사 로직 독립 구현)

온톨로지 미사용 — IntentRouter는 순수 정규식 기반
(속도 우선, XAI 투명성을 위해 의도적으로 LLM/온톨로지 미사용)
```

### 9.6 컴포넌트-온톨로지 매핑 요약표

| 컴포넌트 | NodeTaxonomy | RelationGraph | PropertyConstraints | WorkflowPatterns | LearningGraph | TypoCorrection |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| OntologyEnhancer | O (6단계 감지) | O (확장/힌트) | — | O (패턴감지) | — | O (생성) |
| GeneralRAGService | — | — | — | — | — | O (주입) |
| WorkflowBuildService | — | — | — | — (힌트 수신) | — | O (주입) |
| ExpressionService | — | — | — | — (힌트 수신) | — | O (주입) |
| SemanticValidator | O (분류) | O (패턴검증) | O (규칙적용) | O (패턴매칭) | — | — |
| CurriculumService | — | — | — | — | O (간접) | — |
| ReverseService | O (3층분류) | — | — | — | — | — |

### 9.7 오타 내성 감지 메커니즘 (Typo-Tolerant Detection)

OntologyEnhancer의 노드 감지가 exact match에서 퍼지 매칭으로 확장된 배경과 구조.

#### 9.7.1 배경 — 이중 실패 패턴

```
사용자 입력: "앱훅이 뭐야?" (웹훅 오타)
                  │
    ┌─────────────┴────────────────┐
    │ 실패 1: RAG 검색             │ 실패 2: LLM 추론
    │ OntologyEnhancer 감지 실패   │ 오타 단어를 실재 개념으로 창작
    │ → webhook 문서 미검색        │ → "앱훅(App Hook) = 이벤트 발생 지점"
    └──────────────────────────────┘
              → 할루시네이션 답변 생성
```

#### 9.7.2 두 계층 방어 전략

**Layer 1 — 퍼지 감지 (RAG 품질)**

```
한국어 퍼지 매칭 파이프라인:
  1) _tokenize_ko():  공백/구두점 기준 분리, unigram + bigram 후보 생성
  2) _strip_ko_particle(): 이/가/은/는/을/를/에서/야 등 15개 조사 제거
  3) _decompose_jamo(): 완성형 한글 → 자모 분해
       "앱" (U+C571) → ㅇ+ㅐ+ㅂ
       "웹" (U+C6F9) → ㅇ+ㅞ+ㅂ
       → 자모 레벨에서 편집거리 계산 (IM 오타 패턴에 최적)
  4) _levenshtein(): DP 편집 거리 (순수 Python, ~2ms)
  5) _fuzzy_threshold(): 길이 기반 동적 임계값
       자모 5~9개: thresh=1, 10+개: thresh=2

한국어 IME 오타 유형 처리 예시:
  ㅐ↔ㅔ  (앱훅↔웹훅): dist=1 ✓
  ㄹ↔ㄴ  (슬렉↔슬랙): dist=1 ✓
  된소리  (쌔이트↔사이트): dist=1 ✓

영어 퍼지 매칭:
  문자 단위 Levenshtein
  webhok↔webhook: dist=1 ✓
  githob↔github: dist=1 ✓
```

**Layer 2 — 교정 주입 (LLM 인식)**

```python
# OntologyEnhancer가 dist>0 매칭을 기록
typo_corrections: List[Tuple[str, str]] = [("앱훅", "Webhook")]

# 각 서비스 LLM 시스템 프롬프트에 주입
system += """
[⚠ 오타 자동 교정 — 매우 중요]
  - '앱훅' → Webhook
규칙:
1. 오타 단어는 실제로 존재하지 않는 용어입니다.
2. '비공식 표현' / '구어체'로 정당화하지 마십시오.
3. 교정된 공식 노드명만 기준으로 답변하십시오.
"""
```

#### 9.7.3 설계 원칙

| 원칙 | 내용 |
|------|------|
| **LLM 미사용** | 오타 감지에 LLM 투입 시 300~800ms 추가 → 자모 Levenshtein으로 ~2ms |
| **레이어 분리** | 감지(OntologyEnhancer)와 교정 주입(서비스 프롬프트) 분리 |
| **오탐 방지** | dist>0만 교정 기록 + 길이 기반 임계값 + 단어 경계 체크 |
| **단방향 정보 흐름** | typo_corrections는 읽기 전용으로 ctx에 전달, 서비스가 LLM에 삽입 |

#### 9.7.4 적용 범위

```
_KO_TO_SHORT (80+개) + _DISPLAY_TO_SHORT (453개 동적)
  │
  └─ 퍼지 매칭 커버 범위:
       수동 Korean dict 80개 키 × 퍼지 ≈ 수백 개 변형 처리 가능
       display_name 453개 × 영어 퍼지 ≈ 1000+개 변형 처리 가능

비커버 영역 (벡터 검색이 보완):
  - 완전히 새로운 표현 ("자동화 게이트웨이" → webhook)
  - 다중 노드 맥락 의존 ("메시지 보내기" → slack? telegram? gmail?)
  → 이 경우는 RAG 벡터 유사도 검색이 관련 문서를 검색하고
    LLM이 문맥으로 판단 (온톨로지 미검출 자체가 오류는 아님)
```

---

## 10. 온톨로지 확장 가이드

### 10.1 새 노드 추가 (수동 vs 자동)

#### 자동 생성으로 충분한 경우

빈도가 낮거나(RAG 데이터셋 언급 < 5) 관계·제약이 단순한 노드는 `_RAW_ALL_NODES` 목록에 short_type만 추가하면 자동 생성된다.

```python
# domain_ontology.py — _RAW_ALL_NODES 리스트에 추가 (약 2530번째 줄)
_RAW_ALL_NODES: List[str] = [
    ...
    "newServiceNode",   # ← 이것만 추가하면 자동으로:
    # display_name = "New Service Node"
    # role = NodeRole.SINK (기본값)
    # tags = frozenset({"new", "service", "node"})
    # relations = []
]
```

#### 수동 정의가 필요한 경우

고빈도(RAG 언급 ≥ 5)이거나 관계·패턴이 중요한 노드는 `_NODE_DEFS`에 완전 명세한다.

```python
# domain_ontology.py — _NODE_DEFS 리스트에 추가 (역할별 섹션에 삽입)
N8NNodeDef(
    short_type   = "newService",
    full_type    = "n8n-nodes-base.newService",
    display_name = "New Service",
    role         = NodeRole.SINK,
    output_type  = OutputType.BOTH,
    tags         = frozenset({"new", "service", "api", "integration"}),
    relations    = [
        NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                     "New Service 필드 구성에 Set 필수"),
        NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.75,
                     "조건 기반 분기"),
    ],
),
```

추가 후 자동으로:
- `_NODE_BY_SHORT["newservice"]` 인덱스 생성
- OntologyEnhancer가 tags 기반 한국어 키워드로 감지 가능 (ko 매핑도 추가 권장)
- RelationGraph에 새 엣지 반영
- 수동 노드이므로 `_MANUAL_SHORT_SET`에 포함되어 자동 생성에서 제외됨

### 10.2 새 속성 제약 추가

```python
# domain_ontology.py — PROPERTY_CONSTRAINTS 리스트에 추가
PropertyConstraint(
    node_type        = "notion",
    property_name    = "operation",
    constraint_type  = ConstraintType.CONDITIONAL,
    related_property = "databaseId",
    trigger_value    = "appendToDatabase",
    severity         = ValidationSeverity.WARNING,
    message          = "`operation: appendToDatabase` 시 `databaseId`를 반드시 지정해야 합니다.",
),
```

추가 후 자동으로:
- `_CONSTRAINTS_BY_NODE["notion"]` 인덱스 업데이트
- SemanticValidator가 Notion 노드 파라미터 검증 시 적용

### 10.3 새 워크플로우 패턴 추가

```python
# domain_ontology.py — WORKFLOW_PATTERNS 리스트에 추가
WorkflowPattern(
    name        = "notion_etl",
    description = "데이터 수집 → Notion 데이터베이스 자동 저장 패턴",
    node_types  = ["scheduleTrigger", "httpRequest", "set", "notion"],
    connections = [("scheduleTrigger", "httpRequest"), ("httpRequest", "set"),
                   ("set", "notion")],
    best_practices = [
        "Set으로 Notion 속성 스키마에 맞게 필드 정규화",
        "operation: appendOrUpdate + 중복 방지 컬럼 설정",
    ],
    anti_patterns  = ["스키마 불일치 상태로 직접 Notion에 전송"],
    data_type_hints = ["official_docs", "book"],
),
```

### 10.4 새 학습 노드 추가

```python
# domain_ontology.py — LEARNING_NODES 리스트에 추가
LearningNode(
    concept       = "notion_integration",
    node_types    = ["notion"],
    prerequisites = ["http_api", "data_transformation"],  # 선행 필수
    level         = "intermediate",
    est_minutes   = 60,
),
```

### 10.5 한국어 키워드 매핑 추가

```python
# ontology_enhancer.py — _KO_TO_SHORT에 추가
_KO_TO_SHORT: Dict[str, str] = {
    ...
    "노션": "notion",            # 추가
    "노션 데이터베이스": "notion",  # 추가 (더 긴 패턴 우선 매칭)
}
```

**퍼지 매칭과의 관계:**
- `_KO_TO_SHORT`에 명시적 키가 있으면 **정확 매칭(Step 4)**으로 처리 (교정 기록 없음)
- 키가 없더라도 입력이 기존 키와 자모 편집 거리 ≤ thresh이면 **퍼지 매칭(Step 5)**으로 감지 + 교정 기록
- 따라서 흔한 정확 표현은 Step 4에, 오타 변형은 Step 5가 자동으로 커버
- 단, 아예 새로운 개념(사전에 없고 퍼지로도 안 잡힘)은 수동 추가 필요

**2글자 이하 키 주의사항:**
```python
# 2글자 이하 키는 단어 경계 엄격 적용
# "훅" → _KO_TO_SHORT에 추가하면 "앱훅이"에서 "훅"이 서브스트링 매칭됨
# → 오타 교정 우회, typo_corrections 미기록
# 따라서 짧은 키는 추가하지 말고 퍼지 매칭에 맡길 것
_KO_TO_SHORT["훅"] = "webhook"   # ← 금지 (서브스트링 오탐)
_KO_TO_SHORT["웹훅"] = "webhook"  # ← 권장 (충분히 고유한 패턴)
```

### 10.6 확장 시 주의 사항

1. **weight 결정 기준:** 실무에서 실제로 함께 사용되는 빈도를 기준으로 한다. "이론적으로 관련 있다"는 이유만으로 높은 weight를 주면 쿼리 확장이 너무 광범위해져 검색 품질이 저하된다.

2. **PropertyConstraints의 severity 기준:**
   - ERROR: 설정 없으면 워크플로우가 실행 실패하는 경우
   - WARNING: 실행은 되지만 불안정하거나 예상과 다른 동작
   - INFO: 모범 사례 권고, 무시해도 일반적으로 동작

3. **패턴 감지 임계값:** 현재 `overlap >= 2`이므로, 너무 일반적인 노드(Set, IF 등)만으로 구성된 패턴은 오탐이 많을 수 있다. 고유한 노드(Webhook, Split In Batches 등)를 최소 1개 포함시키는 것이 권장된다.

4. **LearningGraph 순환 참조 금지:** prerequisites에 순환이 생기면 `_dfs()`가 무한 루프에 빠진다. 추가 시 방향성을 반드시 확인한다.

---

*문서 끝 — Naito 도메인 온톨로지 명세서 v2.2*  
*하이브리드 온톨로지 (수동 185개 + 자동 268개 = 453노드, RAG 커버리지 93.7%) + 오타 내성 6단계 감지 + 할루시네이션 방지 파이프라인*  
*다음 파일 참조: `server/domain_ontology.py`, `server/ontology_enhancer.py`, `server/semantic_validator.py`*
