"""
server/domain_ontology.py
──────────────────────────────────────────────────────────────────────
Naito N8N 도메인 온톨로지 (N8N Domain Ontology)

n8n 도메인의 개념·노드·속성 간 상관관계를 형식적으로 명세한다.

구성:
  1. NodeTaxonomy     — 노드 유형 분류 계층 (역할, 태그, 출력 타입)
  2. RelationGraph    — 노드 간 의미적 관계 그래프 (7가지 관계 타입)
  3. PropertyConstraints — 속성 간 의존/배제 제약 규칙
  4. WorkflowPatterns — 검증된 워크플로우 조합 패턴
  5. LearningGraph    — 커리큘럼 선행 학습 의존성 그래프

활용처:
  OntologyEnhancer  (ontology_enhancer.py) — RAG 쿼리 자동 확장
  SemanticValidator (semantic_validator.py) — 생성 후 제약 검증
  CurriculumService (workflow_services.py)  — 선행 관계 기반 로드맵 정렬
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Set


# ══════════════════════════════════════════════════════════════════════
# 1. 기본 열거형
# ══════════════════════════════════════════════════════════════════════

class NodeRole(str, Enum):
    """노드의 워크플로우 내 역할."""
    TRIGGER    = "trigger"     # 워크플로우 시작점
    PROCESSING = "processing"  # 데이터 변환·제어
    SINK       = "sink"        # 외부 출력·저장
    UTILITY    = "utility"     # 흐름 제어 유틸리티


class OutputType(str, Enum):
    """노드 출력 데이터 타입."""
    JSON   = "json"
    BINARY = "binary"
    BOTH   = "both"
    NONE   = "none"


class RelationType(str, Enum):
    """노드 간 의미적 관계 타입 (7종)."""
    COMMONLY_USED_WITH   = "commonly_used_with"   # 실무 co-occurrence (조합 빈도 높음)
    PREREQUISITE_FOR     = "prerequisite_for"     # 개념적 선행 관계 (A 없이 B 이해 불가)
    COMPLEMENTED_BY      = "complemented_by"      # 기능적 보완 (A가 있으면 B를 고려해야 함)
    PATTERN_MEMBER       = "pattern_member"       # 같은 워크플로우 패턴 구성원
    REQUIRES_MULTIPLE_IN = "requires_multiple_in" # 다중 입력 필요 노드
    ANTI_PATTERN_WITH    = "anti_pattern_with"    # 함께 쓰면 위험한 조합
    REPLACES             = "replaces"             # 기능 대체 관계 (A가 B를 대체)


class ConstraintType(str, Enum):
    """속성 제약 타입."""
    REQUIRES      = "requires"       # A 설정 시 B도 반드시 설정
    CONFLICTS     = "conflicts"      # A와 B는 동시에 설정 불가
    CONDITIONAL   = "conditional"    # 특정 값일 때만 다른 속성 필요
    RECOMMENDED   = "recommended"    # 권고 (경고만, 오류 아님)
    FORBIDDEN     = "forbidden"      # 절대 사용 금지 (폐기된 파라미터)


class ValidationSeverity(str, Enum):
    ERROR   = "error"
    WARNING = "warning"
    INFO    = "info"


# ══════════════════════════════════════════════════════════════════════
# 2. 데이터 클래스
# ══════════════════════════════════════════════════════════════════════

@dataclass
class NodeRelation:
    """단방향 노드 관계 엣지."""
    target_type:   str           # 대상 노드 type 식별자 (short form, e.g. "httpRequest")
    relation_type: RelationType
    weight:        float = 1.0   # 관계 강도 (RAG 쿼리 확장 가중치)
    description:   str  = ""


@dataclass
class PropertyConstraint:
    """단일 속성 제약 규칙."""
    node_type:        str
    property_name:    str
    constraint_type:  ConstraintType
    related_property: Optional[str]   = None
    trigger_value:    Optional[str]   = None  # conditional 일 때 트리거 값
    severity:         ValidationSeverity = ValidationSeverity.WARNING
    message:          str = ""


@dataclass
class WorkflowPattern:
    """검증된 워크플로우 조합 패턴."""
    name:         str
    description:  str
    node_types:   List[str]           # 패턴 구성 노드 (short form)
    connections:  List[tuple]         # (source_short, target_short) 엣지
    best_practices: List[str] = field(default_factory=list)
    anti_patterns:  List[str] = field(default_factory=list)
    data_type_hints: List[str] = field(default_factory=list)  # 관련 RAG data_type


@dataclass
class LearningNode:
    """커리큘럼 학습 그래프의 노드."""
    concept:      str
    node_types:   List[str]           # 이 개념이 다루는 n8n 노드들
    prerequisites: List[str]          # 먼저 학습해야 할 concept
    level:        str                 # beginner / intermediate / advanced
    est_minutes:  int = 45


@dataclass
class N8NNodeDef:
    """온톨로지 내 n8n 노드 정의."""
    short_type:               str                  # "httpRequest" (타입 식별자 단축형)
    full_type:                str                  # "n8n-nodes-base.httpRequest"
    display_name:             str
    role:                     NodeRole
    output_type:              OutputType = OutputType.JSON
    tags:                     FrozenSet[str] = field(default_factory=frozenset)
    relations:                List[NodeRelation] = field(default_factory=list)
    requires_multiple_inputs: bool = False


# ══════════════════════════════════════════════════════════════════════
# 3. 온톨로지 데이터 정의
# ══════════════════════════════════════════════════════════════════════

# ── 3-A. 노드 분류 (NodeTaxonomy) ──────────────────────────────────────

_NODE_DEFS: List[N8NNodeDef] = [

    # ══════════════════════════════════════════════════════════════════
    # TRIGGERS
    # ══════════════════════════════════════════════════════════════════
    N8NNodeDef(
        short_type="scheduleTrigger",
        full_type="n8n-nodes-base.scheduleTrigger",
        display_name="Schedule Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"schedule", "cron", "automation", "periodic"}),
        relations=[
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.95,
                         "주기적 API 폴링 패턴에서 가장 빈번하게 조합됨"),
            NodeRelation("slack", RelationType.PATTERN_MEMBER, 0.8,
                         "정기 보고/알림 패턴 구성원"),
            NodeRelation("googleSheets", RelationType.PATTERN_MEMBER, 0.7,
                         "주기적 스프레드시트 업데이트 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="webhook",
        full_type="n8n-nodes-base.webhook",
        display_name="Webhook",
        role=NodeRole.TRIGGER,
        tags=frozenset({"webhook", "http", "event", "real-time", "trigger"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.9,
                         "Webhook 수신 데이터 정제에 Set 노드 필수"),
            NodeRelation("respondToWebhook", RelationType.COMPLEMENTED_BY, 0.95,
                         "동기 응답이 필요한 경우 반드시 함께 사용"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.75,
                         "페이로드 유효성 검증 분기"),
        ],
    ),
    N8NNodeDef(
        short_type="manualTrigger",
        full_type="n8n-nodes-base.manualTrigger",
        display_name="Manual Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"manual", "test", "debug", "trigger"}),
    ),
    N8NNodeDef(
        short_type="telegramTrigger",
        full_type="n8n-nodes-base.telegramTrigger",
        display_name="Telegram Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"telegram", "bot", "trigger", "messaging", "chat"}),
        relations=[
            NodeRelation("telegram", RelationType.COMPLEMENTED_BY, 0.95,
                         "봇 수신·발신 쌍 — Telegram Trigger로 받고 Telegram으로 보냄"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "수신 메시지 파싱·정제에 Set 노드 필수"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "명령어(커맨드) 기반 라우팅 분기"),
        ],
    ),
    N8NNodeDef(
        short_type="googleDriveTrigger",
        full_type="n8n-nodes-base.googleDriveTrigger",
        display_name="Google Drive Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"google", "drive", "file", "trigger", "watch", "upload"}),
        relations=[
            NodeRelation("googleDrive", RelationType.COMPLEMENTED_BY, 0.90,
                         "파일 변경 감지 → Drive 다운로드·처리 패턴"),
            NodeRelation("extractFromFile", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Drive 파일 변경 시 즉시 내용 추출"),
        ],
    ),
    N8NNodeDef(
        short_type="formTrigger",
        full_type="n8n-nodes-base.formTrigger",
        display_name="n8n Form Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"form", "webhook", "trigger", "input", "collect", "survey"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.90,
                         "폼 제출 데이터 정규화에 Set 필수"),
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.80,
                         "폼 응답 → 시트 행 추가 패턴"),
            NodeRelation("emailSend", RelationType.COMMONLY_USED_WITH, 0.75,
                         "폼 제출 시 확인 이메일 발송"),
        ],
    ),
    N8NNodeDef(
        short_type="gmailTrigger",
        full_type="n8n-nodes-base.gmailTrigger",
        display_name="Gmail Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"gmail", "email", "trigger", "watch", "receive", "inbox"}),
        relations=[
            NodeRelation("gmail", RelationType.COMPLEMENTED_BY, 0.90,
                         "이메일 수신 감지 → 답장 발송 쌍"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "이메일 제목·본문·발신자 필드 추출"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "발신자·제목 기반 이메일 필터링 분기"),
        ],
    ),
    N8NNodeDef(
        short_type="githubTrigger",
        full_type="n8n-nodes-base.githubTrigger",
        display_name="GitHub Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"github", "git", "trigger", "push", "pr", "issue", "webhook"}),
        relations=[
            NodeRelation("github", RelationType.COMPLEMENTED_BY, 0.90,
                         "이벤트 감지 → GitHub 액션 수행 쌍"),
            NodeRelation("slack", RelationType.COMMONLY_USED_WITH, 0.85,
                         "PR·Push 이벤트 → Slack 알림"),
            NodeRelation("jira", RelationType.COMMONLY_USED_WITH, 0.75,
                         "커밋·PR → Jira 티켓 업데이트"),
        ],
    ),
    N8NNodeDef(
        short_type="executeWorkflowTrigger",
        full_type="n8n-nodes-base.executeWorkflowTrigger",
        display_name="Execute Workflow Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"sub-workflow", "trigger", "execute", "modular", "reuse"}),
        relations=[
            NodeRelation("executeWorkflow", RelationType.COMPLEMENTED_BY, 0.95,
                         "서브 워크플로우 트리거·실행 쌍"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "상위 워크플로우에서 전달된 데이터 수신·정제"),
        ],
    ),
    N8NNodeDef(
        short_type="notionTrigger",
        full_type="n8n-nodes-base.notionTrigger",
        display_name="Notion Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"notion", "trigger", "database", "watch", "page"}),
        relations=[
            NodeRelation("notion", RelationType.COMPLEMENTED_BY, 0.90,
                         "Notion 변경 감지 → Notion 업데이트 쌍"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "Notion 페이지 속성 추출·정제"),
        ],
    ),
    N8NNodeDef(
        short_type="whatsAppTrigger",
        full_type="n8n-nodes-base.whatsAppTrigger",
        display_name="WhatsApp Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"whatsapp", "trigger", "messaging", "mobile", "business"}),
        relations=[
            NodeRelation("whatsApp", RelationType.COMPLEMENTED_BY, 0.95,
                         "WhatsApp 메시지 수신 → 발신 봇 쌍"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "메시지 내용 기반 조건 라우팅"),
        ],
    ),
    N8NNodeDef(
        short_type="errorTrigger",
        full_type="n8n-nodes-base.errorTrigger",
        display_name="Error Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"error", "trigger", "exception", "monitor", "alert"}),
        relations=[
            NodeRelation("slack", RelationType.COMMONLY_USED_WITH, 0.90,
                         "워크플로우 에러 발생 시 Slack 알림"),
            NodeRelation("emailSend", RelationType.COMMONLY_USED_WITH, 0.80,
                         "에러 발생 시 이메일 알림"),
        ],
    ),
    N8NNodeDef(
        short_type="cron",
        full_type="n8n-nodes-base.cron",
        display_name="Cron",
        role=NodeRole.TRIGGER,
        tags=frozenset({"cron", "schedule", "deprecated", "periodic", "trigger"}),
        relations=[
            NodeRelation("scheduleTrigger", RelationType.REPLACES, 0.95,
                         "n8n v1.x에서 Schedule Trigger로 완전 대체됨"),
        ],
    ),

    # ══════════════════════════════════════════════════════════════════
    # PROCESSING
    # ══════════════════════════════════════════════════════════════════
    N8NNodeDef(
        short_type="httpRequest",
        full_type="n8n-nodes-base.httpRequest",
        display_name="HTTP Request",
        role=NodeRole.PROCESSING,
        tags=frozenset({"http", "api", "rest", "request", "integration"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.9,
                         "API 응답 필드 정제에 Set 노드 조합"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.85,
                         "HTTP 상태코드 또는 응답값 조건 분기"),
            NodeRelation("splitInBatches", RelationType.COMPLEMENTED_BY, 0.7,
                         "대량 API 호출 시 Rate Limit 방지"),
            NodeRelation("merge", RelationType.COMPLEMENTED_BY, 0.6,
                         "다수 병렬 API 결과 합산"),
            NodeRelation("code", RelationType.ANTI_PATTERN_WITH, 0.4,
                         "Code 노드 내 httpRequest 직접 호출 — 스트리밍/에러 처리 불가"),
        ],
    ),
    N8NNodeDef(
        short_type="set",
        full_type="n8n-nodes-base.set",
        display_name="Set",
        role=NodeRole.PROCESSING,
        tags=frozenset({"set", "field", "transform", "mapping", "data"}),
        relations=[
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.9,
                         "API 응답 필드를 다음 노드를 위해 정제"),
            NodeRelation("code", RelationType.PREREQUISITE_FOR, 0.8,
                         "Set의 assignments 개념 이해 후 Code로 심화"),
            NodeRelation("editFields", RelationType.REPLACES, 0.95,
                         "n8n v1.x에서 editFields 노드가 Set을 대체"),
        ],
    ),
    N8NNodeDef(
        short_type="if",
        full_type="n8n-nodes-base.if",
        display_name="IF",
        role=NodeRole.PROCESSING,
        tags=frozenset({"condition", "branch", "if", "boolean", "filter"}),
        relations=[
            NodeRelation("switch", RelationType.REPLACES, 0.7,
                         "분기 3개 이상이면 Switch 노드가 IF보다 적합"),
            NodeRelation("merge", RelationType.COMPLEMENTED_BY, 0.65,
                         "IF의 양쪽 분기 결과를 다시 합칠 때"),
        ],
    ),
    N8NNodeDef(
        short_type="switch",
        full_type="n8n-nodes-base.switch",
        display_name="Switch",
        role=NodeRole.PROCESSING,
        tags=frozenset({"switch", "route", "condition", "multi-branch"}),
        relations=[
            NodeRelation("if", RelationType.REPLACES, 0.7,
                         "2분기면 IF가 더 단순; Switch는 3개 이상 분기에 적합"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.7,
                         "각 분기별 다른 값 설정 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="code",
        full_type="n8n-nodes-base.code",
        display_name="Code",
        role=NodeRole.PROCESSING,
        tags=frozenset({"code", "javascript", "python", "custom", "transform"}),
        relations=[
            NodeRelation("set", RelationType.PREREQUISITE_FOR, 0.8,
                         "Code 이해 전 Set으로 데이터 변환 개념 선습"),
            NodeRelation("httpRequest", RelationType.ANTI_PATTERN_WITH, 0.6,
                         "Code 내 HTTP 직접 호출 — n8n 재시도/에러 처리 불가"),
        ],
    ),
    N8NNodeDef(
        short_type="splitInBatches",
        full_type="n8n-nodes-base.splitInBatches",
        display_name="Split In Batches",
        role=NodeRole.UTILITY,
        tags=frozenset({"batch", "loop", "rate-limit", "large-data", "split"}),
        relations=[
            NodeRelation("httpRequest", RelationType.COMPLEMENTED_BY, 0.9,
                         "API Rate Limit 대응 — 배치 단위 지연 처리"),
            NodeRelation("merge", RelationType.PATTERN_MEMBER, 0.85,
                         "Split → 처리 → Merge 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="splitOut",
        full_type="n8n-nodes-base.splitOut",
        display_name="Split Out",
        role=NodeRole.UTILITY,
        tags=frozenset({"split", "array", "item", "iterate"}),
        relations=[
            NodeRelation("merge", RelationType.PATTERN_MEMBER, 0.9,
                         "배열 분리 → 개별 처리 → Merge 패턴"),
            NodeRelation("aggregate", RelationType.COMPLEMENTED_BY, 0.8,
                         "Split Out 후 결과 집계에 Aggregate 사용"),
        ],
    ),
    N8NNodeDef(
        short_type="merge",
        full_type="n8n-nodes-base.merge",
        display_name="Merge",
        role=NodeRole.UTILITY,
        requires_multiple_inputs=True,
        tags=frozenset({"merge", "combine", "join", "aggregate"}),
        relations=[
            NodeRelation("splitInBatches", RelationType.REQUIRES_MULTIPLE_IN, 0.9,
                         "Merge는 반드시 2개 이상 입력 필요"),
            NodeRelation("splitOut", RelationType.PATTERN_MEMBER, 0.9,
                         "Split → 처리 → Merge 표준 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="aggregate",
        full_type="n8n-nodes-base.aggregate",
        display_name="Aggregate",
        role=NodeRole.PROCESSING,
        tags=frozenset({"aggregate", "collect", "group", "summarize"}),
        relations=[
            NodeRelation("splitOut", RelationType.COMPLEMENTED_BY, 0.85,
                         "Split Out 후 결과를 집계/그룹화"),
        ],
    ),
    N8NNodeDef(
        short_type="filter",
        full_type="n8n-nodes-base.filter",
        display_name="Filter",
        role=NodeRole.PROCESSING,
        tags=frozenset({"filter", "condition", "data", "clean", "remove", "select"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "필터 후 필드 정제·매핑"),
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.75,
                         "API 응답 중 조건에 맞는 항목만 통과"),
            NodeRelation("if", RelationType.REPLACES, 0.65,
                         "단순 필드값 필터링에는 IF보다 Filter가 더 적합"),
        ],
    ),
    N8NNodeDef(
        short_type="extractFromFile",
        full_type="n8n-nodes-base.extractFromFile",
        display_name="Extract From File",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"file", "extract", "parse", "binary", "csv", "pdf", "excel"}),
        relations=[
            NodeRelation("googleDrive", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Drive에서 파일 다운로드 후 내용 추출"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "추출된 데이터 필드 정제"),
            NodeRelation("convertToFile", RelationType.COMPLEMENTED_BY, 0.75,
                         "추출 → 변환 → 재생성 파이프라인"),
        ],
    ),
    N8NNodeDef(
        short_type="convertToFile",
        full_type="n8n-nodes-base.convertToFile",
        display_name="Convert to File",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BINARY,
        tags=frozenset({"file", "convert", "binary", "csv", "excel", "generate", "export"}),
        relations=[
            NodeRelation("googleDrive", RelationType.COMMONLY_USED_WITH, 0.80,
                         "파일 생성 후 Drive에 업로드"),
            NodeRelation("extractFromFile", RelationType.COMPLEMENTED_BY, 0.75,
                         "추출 → 가공 → 재변환 사이클"),
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.70,
                         "시트 데이터를 파일로 내보내기"),
        ],
    ),
    N8NNodeDef(
        short_type="openAi",
        full_type="n8n-nodes-base.openAi",
        display_name="OpenAI",
        role=NodeRole.PROCESSING,
        tags=frozenset({"openai", "ai", "llm", "gpt", "completion", "embedding", "nlp"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "프롬프트 구성 및 AI 응답 필드 추출"),
            NodeRelation("httpRequest", RelationType.PATTERN_MEMBER, 0.75,
                         "외부 데이터 수집 → AI 분석 파이프라인"),
            NodeRelation("code", RelationType.COMPLEMENTED_BY, 0.70,
                         "AI 응답 파싱·후처리에 Code 노드 활용"),
        ],
    ),
    N8NNodeDef(
        short_type="html",
        full_type="n8n-nodes-base.html",
        display_name="HTML",
        role=NodeRole.PROCESSING,
        tags=frozenset({"html", "web", "template", "parse", "render", "extract"}),
        relations=[
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.80,
                         "HTTP로 HTML 가져온 후 파싱"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.75,
                         "HTML 추출 결과 필드 정제"),
            NodeRelation("emailSend", RelationType.COMMONLY_USED_WITH, 0.70,
                         "HTML 이메일 본문 생성"),
        ],
    ),
    N8NNodeDef(
        short_type="markdown",
        full_type="n8n-nodes-base.markdown",
        display_name="Markdown",
        role=NodeRole.PROCESSING,
        tags=frozenset({"markdown", "text", "format", "convert", "document", "html"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.75,
                         "Markdown 변환 후 필드 저장"),
            NodeRelation("emailSend", RelationType.COMMONLY_USED_WITH, 0.70,
                         "Markdown → HTML 변환 후 이메일 발송"),
            NodeRelation("notion", RelationType.COMMONLY_USED_WITH, 0.70,
                         "Markdown 콘텐츠를 Notion 페이지로 저장"),
        ],
    ),
    N8NNodeDef(
        short_type="itemLists",
        full_type="n8n-nodes-base.itemLists",
        display_name="Item Lists",
        role=NodeRole.PROCESSING,
        tags=frozenset({"list", "array", "item", "filter", "remove", "add", "modify"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.75,
                         "리스트 조작 후 필드 재매핑"),
            NodeRelation("splitOut", RelationType.COMMONLY_USED_WITH, 0.70,
                         "리스트 가공 후 개별 항목으로 분리"),
        ],
    ),
    N8NNodeDef(
        short_type="summarize",
        full_type="n8n-nodes-base.summarize",
        display_name="Summarize",
        role=NodeRole.PROCESSING,
        tags=frozenset({"summarize", "group", "count", "sum", "aggregate", "pivot"}),
        relations=[
            NodeRelation("splitOut", RelationType.COMMONLY_USED_WITH, 0.80,
                         "항목 분리 후 집계 요약"),
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.70,
                         "집계 결과를 시트에 저장"),
            NodeRelation("aggregate", RelationType.REPLACES, 0.60,
                         "단순 합산·카운트는 Summarize로 더 간단히 구현 가능"),
        ],
    ),
    N8NNodeDef(
        short_type="compareDatasets",
        full_type="n8n-nodes-base.compareDatasets",
        display_name="Compare Datasets",
        role=NodeRole.PROCESSING,
        requires_multiple_inputs=True,
        tags=frozenset({"compare", "diff", "dataset", "sync", "delta"}),
        relations=[
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.80,
                         "시트 데이터 변경분 감지 패턴"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.75,
                         "비교 결과 필드 정제"),
        ],
    ),
    N8NNodeDef(
        short_type="executeWorkflow",
        full_type="n8n-nodes-base.executeWorkflow",
        display_name="Execute Workflow",
        role=NodeRole.PROCESSING,
        tags=frozenset({"sub-workflow", "execute", "modular", "reuse", "call"}),
        relations=[
            NodeRelation("executeWorkflowTrigger", RelationType.COMPLEMENTED_BY, 0.95,
                         "상위 워크플로우 → 서브 워크플로우 실행 쌍"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.75,
                         "서브 워크플로우 호출 전 입력 데이터 준비"),
        ],
    ),
    N8NNodeDef(
        short_type="editImage",
        full_type="n8n-nodes-base.editImage",
        display_name="Edit Image",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BINARY,
        tags=frozenset({"image", "edit", "resize", "crop", "binary", "photo"}),
        relations=[
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.80,
                         "URL에서 이미지 다운로드 후 편집"),
            NodeRelation("googleDrive", RelationType.COMMONLY_USED_WITH, 0.75,
                         "이미지 편집 후 Drive에 저장"),
        ],
    ),
    N8NNodeDef(
        short_type="function",
        full_type="n8n-nodes-base.function",
        display_name="Function",
        role=NodeRole.PROCESSING,
        tags=frozenset({"function", "javascript", "deprecated", "code", "transform"}),
        relations=[
            NodeRelation("code", RelationType.REPLACES, 0.95,
                         "n8n v1.x에서 Code 노드로 완전 대체됨"),
        ],
    ),
    N8NNodeDef(
        short_type="xml",
        full_type="n8n-nodes-base.xml",
        display_name="XML",
        role=NodeRole.PROCESSING,
        tags=frozenset({"xml", "parse", "convert", "soap", "data"}),
        relations=[
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.80,
                         "SOAP API 응답 XML 파싱"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.75,
                         "XML 파싱 결과 필드 정제"),
        ],
    ),
    N8NNodeDef(
        short_type="crypto",
        full_type="n8n-nodes-base.crypto",
        display_name="Crypto",
        role=NodeRole.PROCESSING,
        tags=frozenset({"crypto", "hash", "encrypt", "hmac", "security", "sign"}),
        relations=[
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.80,
                         "API 요청 서명(HMAC) 생성에 자주 사용"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.75,
                         "서명값을 헤더 필드로 설정"),
        ],
    ),
    N8NNodeDef(
        short_type="spreadsheetFile",
        full_type="n8n-nodes-base.spreadsheetFile",
        display_name="Spreadsheet File",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"spreadsheet", "excel", "csv", "file", "convert"}),
        relations=[
            NodeRelation("googleDrive", RelationType.COMMONLY_USED_WITH, 0.80,
                         "스프레드시트 파일 Drive 저장"),
            NodeRelation("extractFromFile", RelationType.COMPLEMENTED_BY, 0.75,
                         "파일 읽기·쓰기 쌍"),
        ],
    ),
    N8NNodeDef(
        short_type="graphql",
        full_type="n8n-nodes-base.graphql",
        display_name="GraphQL",
        role=NodeRole.PROCESSING,
        tags=frozenset({"graphql", "api", "query", "schema", "integration"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "GraphQL 응답 필드 추출·정제"),
            NodeRelation("httpRequest", RelationType.REPLACES, 0.60,
                         "GraphQL 엔드포인트는 HTTP Request 대신 이 노드 권장"),
        ],
    ),

    # ══════════════════════════════════════════════════════════════════
    # SINKS
    # ══════════════════════════════════════════════════════════════════
    N8NNodeDef(
        short_type="slack",
        full_type="n8n-nodes-base.slack",
        display_name="Slack",
        role=NodeRole.SINK,
        tags=frozenset({"slack", "notification", "message", "team"}),
        relations=[
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.85,
                         "정기 보고 패턴 — 스케줄 → 데이터 → 슬랙"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.8,
                         "에러·임계값 초과 시에만 알림 분기"),
        ],
    ),
    N8NNodeDef(
        short_type="gmail",
        full_type="n8n-nodes-base.gmail",
        display_name="Gmail",
        role=NodeRole.SINK,
        tags=frozenset({"email", "gmail", "notification", "send"}),
    ),
    N8NNodeDef(
        short_type="googleSheets",
        full_type="n8n-nodes-base.googleSheets",
        display_name="Google Sheets",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"spreadsheet", "data", "storage", "google"}),
        relations=[
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.75,
                         "주기적 데이터 수집·저장 패턴"),
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.8,
                         "API 데이터를 시트에 기록"),
        ],
    ),
    N8NNodeDef(
        short_type="postgres",
        full_type="n8n-nodes-base.postgres",
        display_name="Postgres",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"database", "sql", "postgres", "storage"}),
    ),
    N8NNodeDef(
        short_type="respondToWebhook",
        full_type="n8n-nodes-base.respondToWebhook",
        display_name="Respond to Webhook",
        role=NodeRole.SINK,
        output_type=OutputType.NONE,
        tags=frozenset({"webhook", "response", "http", "sync"}),
        relations=[
            NodeRelation("webhook", RelationType.COMPLEMENTED_BY, 0.98,
                         "responseMode=responseNode 인 Webhook의 필수 파트너"),
        ],
    ),
    N8NNodeDef(
        short_type="telegram",
        full_type="n8n-nodes-base.telegram",
        display_name="Telegram",
        role=NodeRole.SINK,
        tags=frozenset({"telegram", "messaging", "chat", "bot", "notification"}),
        relations=[
            NodeRelation("telegramTrigger", RelationType.COMPLEMENTED_BY, 0.95,
                         "봇 수신(Trigger)·발신(Telegram) 쌍"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.75,
                         "정기 알림 패턴 — 스케줄 → 처리 → Telegram"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "조건 충족 시에만 메시지 발송"),
        ],
    ),
    N8NNodeDef(
        short_type="notion",
        full_type="n8n-nodes-base.notion",
        display_name="Notion",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"notion", "database", "knowledge", "docs", "storage", "page"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Notion 속성 스키마에 맞게 필드 정규화 필수"),
            NodeRelation("notionTrigger", RelationType.COMPLEMENTED_BY, 0.85,
                         "Notion 변경 감지 → 업데이트 쌍"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.70,
                         "주기적 Notion 데이터베이스 업데이트"),
        ],
    ),
    N8NNodeDef(
        short_type="googleDrive",
        full_type="n8n-nodes-base.googleDrive",
        display_name="Google Drive",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"google", "drive", "storage", "file", "cloud", "upload"}),
        relations=[
            NodeRelation("googleDriveTrigger", RelationType.COMPLEMENTED_BY, 0.85,
                         "Drive 파일 변경 감지 + 처리 쌍"),
            NodeRelation("extractFromFile", RelationType.COMMONLY_USED_WITH, 0.80,
                         "Drive 다운로드 후 내용 추출"),
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.70,
                         "Google 생태계 내 Drive + Sheets 조합"),
        ],
    ),
    N8NNodeDef(
        short_type="airtable",
        full_type="n8n-nodes-base.airtable",
        display_name="Airtable",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"airtable", "database", "spreadsheet", "storage", "no-code"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Airtable 필드 스키마에 맞게 데이터 정규화"),
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.75,
                         "API 데이터 → Airtable 저장 패턴"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.70,
                         "조건에 따른 레코드 분기 처리"),
        ],
    ),
    N8NNodeDef(
        short_type="discord",
        full_type="n8n-nodes-base.discord",
        display_name="Discord",
        role=NodeRole.SINK,
        tags=frozenset({"discord", "messaging", "gaming", "notification", "community"}),
        relations=[
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "조건 충족 시에만 Discord 메시지 발송"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.75,
                         "정기 Discord 알림 패턴"),
            NodeRelation("githubTrigger", RelationType.COMMONLY_USED_WITH, 0.70,
                         "GitHub 이벤트 → Discord 채널 알림"),
        ],
    ),
    N8NNodeDef(
        short_type="whatsApp",
        full_type="n8n-nodes-base.whatsApp",
        display_name="WhatsApp",
        role=NodeRole.SINK,
        tags=frozenset({"whatsapp", "messaging", "mobile", "business", "sms"}),
        relations=[
            NodeRelation("whatsAppTrigger", RelationType.COMPLEMENTED_BY, 0.95,
                         "WhatsApp 봇 수신·발신 쌍"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "조건 기반 메시지 발송"),
        ],
    ),
    N8NNodeDef(
        short_type="emailSend",
        full_type="n8n-nodes-base.emailSend",
        display_name="Send Email",
        role=NodeRole.SINK,
        tags=frozenset({"email", "smtp", "send", "notification", "mail"}),
        relations=[
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "조건 충족 시에만 이메일 발송"),
            NodeRelation("formTrigger", RelationType.COMMONLY_USED_WITH, 0.75,
                         "폼 제출 → 확인 이메일 발송 패턴"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.70,
                         "주기적 이메일 리포트 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="redis",
        full_type="n8n-nodes-base.redis",
        display_name="Redis",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"redis", "cache", "key-value", "storage", "fast", "session"}),
        relations=[
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.80,
                         "API 응답 캐싱으로 중복 호출 방지"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.75,
                         "캐시 키·값 구성에 Set 노드 활용"),
        ],
    ),
    N8NNodeDef(
        short_type="hubspot",
        full_type="n8n-nodes-base.hubspot",
        display_name="HubSpot",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"hubspot", "crm", "marketing", "sales", "contacts", "leads"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "HubSpot 속성 스키마에 맞게 필드 매핑"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.75,
                         "HubSpot 웹훅 이벤트 → CRM 업데이트"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.70,
                         "리드 점수·조건 기반 CRM 업데이트 분기"),
        ],
    ),
    N8NNodeDef(
        short_type="jira",
        full_type="n8n-nodes-base.jira",
        display_name="Jira",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"jira", "project", "issue", "task", "bug", "agile"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Jira 이슈 필드 구성에 Set 필수"),
            NodeRelation("github", RelationType.COMMONLY_USED_WITH, 0.75,
                         "GitHub 커밋·PR → Jira 티켓 자동 업데이트"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.70,
                         "우선순위·조건 기반 티켓 생성 분기"),
        ],
    ),
    N8NNodeDef(
        short_type="mySql",
        full_type="n8n-nodes-base.mySql",
        display_name="MySQL",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"mysql", "database", "sql", "query", "storage", "rdbms"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "쿼리 파라미터 구성에 Set 노드 활용"),
            NodeRelation("splitInBatches", RelationType.COMPLEMENTED_BY, 0.75,
                         "대량 INSERT/UPDATE 시 배치 분할 처리"),
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.70,
                         "API 수집 데이터 → MySQL 저장"),
        ],
    ),
    N8NNodeDef(
        short_type="supabase",
        full_type="n8n-nodes-base.supabase",
        display_name="Supabase",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"supabase", "database", "postgres", "storage", "realtime", "backend"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Supabase 테이블 스키마에 맞게 데이터 정제"),
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.75,
                         "외부 API 데이터 → Supabase 저장"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.70,
                         "Supabase Realtime 이벤트 수신"),
        ],
    ),
    N8NNodeDef(
        short_type="googleCalendar",
        full_type="n8n-nodes-base.googleCalendar",
        display_name="Google Calendar",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"google", "calendar", "event", "schedule", "meeting", "booking"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "캘린더 이벤트 데이터 필드 구성"),
            NodeRelation("scheduleTrigger", RelationType.COMMONLY_USED_WITH, 0.75,
                         "주기적 캘린더 동기화 패턴"),
            NodeRelation("googleCalendarTool", RelationType.REPLACES, 0.80,
                         "AI 에이전트 컨텍스트에서는 Tool 버전 사용"),
        ],
    ),
    N8NNodeDef(
        short_type="googleCalendarTool",
        full_type="n8n-nodes-base.googleCalendarTool",
        display_name="Google Calendar Tool",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"google", "calendar", "tool", "ai-agent", "meeting"}),
        relations=[
            NodeRelation("googleCalendar", RelationType.REPLACES, 0.80,
                         "AI 에이전트 툴 컨텍스트에서 googleCalendar 대체"),
        ],
    ),
    N8NNodeDef(
        short_type="github",
        full_type="n8n-nodes-base.github",
        display_name="GitHub",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"github", "git", "repository", "code", "pr", "issue", "ci"}),
        relations=[
            NodeRelation("githubTrigger", RelationType.COMPLEMENTED_BY, 0.85,
                         "GitHub 이벤트 트리거 + 액션 쌍"),
            NodeRelation("slack", RelationType.COMMONLY_USED_WITH, 0.80,
                         "GitHub 이벤트 → Slack 팀 알림"),
            NodeRelation("jira", RelationType.COMMONLY_USED_WITH, 0.75,
                         "GitHub 커밋 → Jira 티켓 자동 연동"),
        ],
    ),
    N8NNodeDef(
        short_type="microsoftOutlook",
        full_type="n8n-nodes-base.microsoftOutlook",
        display_name="Microsoft Outlook",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"outlook", "email", "microsoft", "send", "receive", "office365"}),
        relations=[
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "조건 기반 이메일 발송·분류"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "이메일 본문·수신자 필드 구성"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.70,
                         "주기적 Outlook 이메일 리포트"),
        ],
    ),
    N8NNodeDef(
        short_type="googleDocs",
        full_type="n8n-nodes-base.googleDocs",
        display_name="Google Docs",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"google", "docs", "document", "text", "write", "gdoc"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "문서 삽입 내용 필드 구성"),
            NodeRelation("googleDrive", RelationType.COMMONLY_USED_WITH, 0.75,
                         "Docs는 Drive에 저장 — 파일 접근 패턴 공유"),
        ],
    ),
    N8NNodeDef(
        short_type="mattermost",
        full_type="n8n-nodes-base.mattermost",
        display_name="Mattermost",
        role=NodeRole.SINK,
        tags=frozenset({"mattermost", "messaging", "team", "notification", "self-hosted"}),
        relations=[
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "조건 기반 메시지 발송"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.70,
                         "정기 Mattermost 알림 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="pipedrive",
        full_type="n8n-nodes-base.pipedrive",
        display_name="Pipedrive",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"pipedrive", "crm", "sales", "deal", "pipeline", "leads"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Pipedrive 딜·연락처 필드 정규화"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.75,
                         "Pipedrive 웹훅 → CRM 업데이트"),
        ],
    ),

    # ══════════════════════════════════════════════════════════════════
    # SINKS — 추가 외부 서비스
    # ══════════════════════════════════════════════════════════════════

    N8NNodeDef(
        short_type="wordpress",
        full_type="n8n-nodes-base.wordpress",
        display_name="WordPress",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"wordpress", "cms", "blog", "post", "web"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "WordPress 포스트·페이지 필드 구성에 Set 필수"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.75,
                         "정기 콘텐츠 자동 발행 패턴"),
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.70,
                         "외부 소스 콘텐츠 가져와 WordPress에 저장"),
        ],
    ),
    N8NNodeDef(
        short_type="twilio",
        full_type="n8n-nodes-base.twilio",
        display_name="Twilio",
        role=NodeRole.SINK,
        tags=frozenset({"twilio", "sms", "phone", "call", "messaging", "otp"}),
        relations=[
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.85,
                         "조건 충족 시에만 SMS 발송 — 비용 절감"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.80,
                         "수신 SMS 처리 (Twilio Webhook → n8n)"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.70,
                         "정기 SMS 알림 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="todoist",
        full_type="n8n-nodes-base.todoist",
        display_name="Todoist",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"todoist", "task", "todo", "productivity", "project"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "작업 제목·기한·우선순위 필드 구성"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.75,
                         "조건 기반 작업 생성/업데이트 분기"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.70,
                         "정기 작업 자동 생성 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="twitter",
        full_type="n8n-nodes-base.twitter",
        display_name="X (Twitter)",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"twitter", "x", "tweet", "social", "media", "post"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "트윗 내용·미디어 필드 구성"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.80,
                         "정기 자동 트윗 발행 패턴"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.70,
                         "특정 조건(키워드·감성) 기반 트윗 여부 결정"),
        ],
    ),
    N8NNodeDef(
        short_type="salesforce",
        full_type="n8n-nodes-base.salesforce",
        display_name="Salesforce",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"salesforce", "crm", "sales", "lead", "opportunity", "enterprise"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Salesforce 오브젝트 필드 매핑에 Set 필수"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.80,
                         "Salesforce 웹훅 이벤트 → n8n 처리"),
            NodeRelation("hubspot", RelationType.ANTI_PATTERN_WITH, 0.40,
                         "두 CRM에 동시 저장하면 데이터 불일치 위험"),
        ],
    ),
    N8NNodeDef(
        short_type="zendesk",
        full_type="n8n-nodes-base.zendesk",
        display_name="Zendesk",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"zendesk", "support", "ticket", "helpdesk", "customer"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "티켓 필드(제목·우선순위·태그) 구성"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "고객 유형·이슈 분류 기반 티켓 라우팅"),
            NodeRelation("slack", RelationType.COMMONLY_USED_WITH, 0.75,
                         "신규 Zendesk 티켓 → 슬랙 지원팀 알림"),
        ],
    ),
    N8NNodeDef(
        short_type="spotify",
        full_type="n8n-nodes-base.spotify",
        display_name="Spotify",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"spotify", "music", "playlist", "audio", "media"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "트랙·플레이리스트 데이터 필드 가공"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.70,
                         "정기 플레이리스트 업데이트 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="dropbox",
        full_type="n8n-nodes-base.dropbox",
        display_name="Dropbox",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"dropbox", "storage", "file", "cloud", "share"}),
        relations=[
            NodeRelation("extractFromFile", RelationType.COMMONLY_USED_WITH, 0.80,
                         "Dropbox 파일 다운로드 후 내용 추출"),
            NodeRelation("convertToFile", RelationType.COMMONLY_USED_WITH, 0.75,
                         "파일 생성 후 Dropbox 업로드"),
            NodeRelation("googleDrive", RelationType.ANTI_PATTERN_WITH, 0.35,
                         "두 스토리지에 동시 저장하면 동기화 불일치 발생 가능"),
        ],
    ),
    N8NNodeDef(
        short_type="baserow",
        full_type="n8n-nodes-base.baserow",
        display_name="Baserow",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"baserow", "database", "no-code", "table", "airtable-alternative"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Baserow 테이블 컬럼 스키마에 맞게 데이터 정규화"),
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.75,
                         "API 데이터 → Baserow 테이블 저장"),
        ],
    ),
    N8NNodeDef(
        short_type="linear",
        full_type="n8n-nodes-base.linear",
        display_name="Linear",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"linear", "project", "issue", "engineering", "agile"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Linear 이슈 필드 구성"),
            NodeRelation("githubTrigger", RelationType.COMMONLY_USED_WITH, 0.80,
                         "GitHub PR/커밋 → Linear 이슈 자동 업데이트"),
            NodeRelation("slack", RelationType.COMMONLY_USED_WITH, 0.70,
                         "Linear 이슈 생성/업데이트 → Slack 팀 알림"),
        ],
    ),
    N8NNodeDef(
        short_type="youTube",
        full_type="n8n-nodes-base.youTube",
        display_name="YouTube",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"youtube", "video", "google", "channel", "media", "upload"}),
        relations=[
            NodeRelation("convertToFile", RelationType.COMMONLY_USED_WITH, 0.80,
                         "파일 변환 후 YouTube 업로드"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "영상 제목·설명·태그 필드 구성"),
        ],
    ),
    N8NNodeDef(
        short_type="googleAnalytics",
        full_type="n8n-nodes-base.googleAnalytics",
        display_name="Google Analytics",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"google", "analytics", "tracking", "metrics", "report", "ga4"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Analytics 이벤트·파라미터 필드 구성"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.75,
                         "정기 GA4 리포트 수집 패턴"),
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.75,
                         "Analytics 데이터 → Sheets 대시보드 저장"),
        ],
    ),
    N8NNodeDef(
        short_type="microsoftTeams",
        full_type="n8n-nodes-base.microsoftTeams",
        display_name="Microsoft Teams",
        role=NodeRole.SINK,
        tags=frozenset({"microsoft", "teams", "messaging", "notification", "office365"}),
        relations=[
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "조건 충족 시에만 Teams 메시지 발송"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.75,
                         "정기 Teams 리포트/알림 패턴"),
            NodeRelation("slack", RelationType.ANTI_PATTERN_WITH, 0.35,
                         "동일 알림을 Slack·Teams 양쪽에 보내면 알림 중복 발생"),
        ],
    ),
    N8NNodeDef(
        short_type="linkedIn",
        full_type="n8n-nodes-base.linkedIn",
        display_name="LinkedIn",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"linkedin", "social", "professional", "post", "b2b"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "포스트 내용·미디어 필드 구성"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.80,
                         "정기 LinkedIn 콘텐츠 자동 발행 패턴"),
            NodeRelation("twitter", RelationType.PATTERN_MEMBER, 0.65,
                         "소셜 미디어 동시 발행 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="nocoDb",
        full_type="n8n-nodes-base.nocoDb",
        display_name="NocoDB",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"nocodb", "database", "no-code", "airtable-alternative", "table"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "NocoDB 테이블 스키마에 맞게 데이터 정규화"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.70,
                         "NocoDB 웹훅 이벤트 수신"),
        ],
    ),
    N8NNodeDef(
        short_type="snowflake",
        full_type="n8n-nodes-base.snowflake",
        display_name="Snowflake",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"snowflake", "database", "data-warehouse", "sql", "analytics"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Snowflake 테이블 스키마에 맞게 필드 정규화"),
            NodeRelation("splitInBatches", RelationType.COMPLEMENTED_BY, 0.75,
                         "대량 데이터 배치 INSERT 시 필수"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.70,
                         "정기 데이터 파이프라인 적재 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="rssFeedRead",
        full_type="n8n-nodes-base.rssFeedRead",
        display_name="RSS Feed Read",
        role=NodeRole.PROCESSING,
        tags=frozenset({"rss", "feed", "news", "content", "blog", "atom", "subscribe"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "RSS 항목 필드(제목·링크·날짜) 추출·정제"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.90,
                         "주기적 RSS 모니터링 패턴 — 스케줄 필수"),
            NodeRelation("slack", RelationType.COMMONLY_USED_WITH, 0.75,
                         "신규 RSS 항목 → Slack/메신저 알림"),
        ],
    ),
    N8NNodeDef(
        short_type="asana",
        full_type="n8n-nodes-base.asana",
        display_name="Asana",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"asana", "task", "project", "productivity", "team"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Asana 작업 필드 구성"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.75,
                         "조건 기반 작업 생성/업데이트 분기"),
            NodeRelation("formTrigger", RelationType.COMMONLY_USED_WITH, 0.70,
                         "폼 제출 → Asana 작업 자동 생성 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="trello",
        full_type="n8n-nodes-base.trello",
        display_name="Trello",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"trello", "kanban", "board", "card", "task", "project"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Trello 카드 필드 구성"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.75,
                         "조건 기반 보드·리스트 분기"),
            NodeRelation("formTrigger", RelationType.COMMONLY_USED_WITH, 0.70,
                         "폼 제출 → Trello 카드 자동 생성"),
        ],
    ),
    N8NNodeDef(
        short_type="shopify",
        full_type="n8n-nodes-base.shopify",
        display_name="Shopify",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"shopify", "ecommerce", "store", "product", "order", "customer"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Shopify 상품·주문 필드 구성"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.80,
                         "Shopify 주문·재고 웹훅 이벤트 처리"),
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.70,
                         "주문 데이터 → 스프레드시트 기록"),
        ],
    ),
    N8NNodeDef(
        short_type="hubspotTrigger",
        full_type="n8n-nodes-base.hubspotTrigger",
        display_name="HubSpot Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"hubspot", "crm", "trigger", "contact", "deal", "event"}),
        relations=[
            NodeRelation("hubspot", RelationType.COMPLEMENTED_BY, 0.90,
                         "HubSpot 이벤트 감지 → CRM 업데이트 쌍"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "HubSpot 이벤트 데이터 필드 추출"),
            NodeRelation("slack", RelationType.COMMONLY_USED_WITH, 0.75,
                         "HubSpot 딜 상태 변경 → Slack 영업팀 알림"),
        ],
    ),
    N8NNodeDef(
        short_type="googleSheetsTrigger",
        full_type="n8n-nodes-base.googleSheetsTrigger",
        display_name="Google Sheets Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"google", "sheets", "trigger", "spreadsheet", "watch", "row"}),
        relations=[
            NodeRelation("googleSheets", RelationType.COMPLEMENTED_BY, 0.90,
                         "시트 변경 감지 + 데이터 읽기/쓰기 쌍"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "변경된 행 데이터 필드 추출·정제"),
            NodeRelation("slack", RelationType.COMMONLY_USED_WITH, 0.70,
                         "시트 행 추가 → 팀 알림"),
        ],
    ),
    N8NNodeDef(
        short_type="typeformTrigger",
        full_type="n8n-nodes-base.typeformTrigger",
        display_name="Typeform Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"typeform", "form", "survey", "trigger", "webhook", "response"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.90,
                         "Typeform 응답 데이터 필드 추출·정규화"),
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.80,
                         "Typeform 응답 → 시트 자동 기록"),
            NodeRelation("emailSend", RelationType.COMMONLY_USED_WITH, 0.75,
                         "폼 제출 → 자동 확인 이메일 발송"),
            NodeRelation("notion", RelationType.COMMONLY_USED_WITH, 0.65,
                         "Typeform 응답 → Notion 데이터베이스 저장"),
        ],
    ),
    N8NNodeDef(
        short_type="localFileTrigger",
        full_type="n8n-nodes-base.localFileTrigger",
        display_name="Local File Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"file", "local", "trigger", "watch", "filesystem", "folder"}),
        relations=[
            NodeRelation("extractFromFile", RelationType.COMMONLY_USED_WITH, 0.90,
                         "파일 시스템 변경 감지 → 즉시 내용 추출"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "파일 메타데이터(경로·크기·타입) 추출"),
        ],
    ),
    N8NNodeDef(
        short_type="microsoftOutlookTrigger",
        full_type="n8n-nodes-base.microsoftOutlookTrigger",
        display_name="Microsoft Outlook Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"outlook", "email", "trigger", "microsoft", "office365", "inbox"}),
        relations=[
            NodeRelation("microsoftOutlook", RelationType.COMPLEMENTED_BY, 0.90,
                         "이메일 수신 → 처리·발신 쌍"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "이메일 제목·발신자·본문 필드 추출"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "발신자·키워드 기반 이메일 분류 분기"),
        ],
    ),
    N8NNodeDef(
        short_type="facebookTrigger",
        full_type="n8n-nodes-base.facebookTrigger",
        display_name="Facebook Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"facebook", "meta", "trigger", "social", "page", "lead"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Facebook 이벤트 페이로드 필드 추출"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "이벤트 유형(like/comment/lead) 분기"),
        ],
    ),
    N8NNodeDef(
        short_type="interval",
        full_type="n8n-nodes-base.interval",
        display_name="Interval",
        role=NodeRole.TRIGGER,
        tags=frozenset({"interval", "timer", "periodic", "schedule", "deprecated"}),
        relations=[
            NodeRelation("scheduleTrigger", RelationType.REPLACES, 0.90,
                         "n8n v1.x에서 Schedule Trigger로 대체 권장"),
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.80,
                         "주기적 API 폴링에 자주 사용 (Schedule Trigger 권장)"),
        ],
    ),
    N8NNodeDef(
        short_type="zoom",
        full_type="n8n-nodes-base.zoom",
        display_name="Zoom",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"zoom", "meeting", "video", "conference", "webinar"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "미팅 제목·시간·참가자 필드 구성"),
            NodeRelation("googleCalendar", RelationType.COMMONLY_USED_WITH, 0.80,
                         "캘린더 이벤트 → Zoom 미팅 자동 생성 패턴"),
            NodeRelation("slack", RelationType.COMMONLY_USED_WITH, 0.75,
                         "Zoom 링크를 Slack에 공유"),
        ],
    ),
    N8NNodeDef(
        short_type="nextCloud",
        full_type="n8n-nodes-base.nextCloud",
        display_name="Nextcloud",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"nextcloud", "storage", "file", "self-hosted", "cloud", "share"}),
        relations=[
            NodeRelation("extractFromFile", RelationType.COMMONLY_USED_WITH, 0.80,
                         "Nextcloud 파일 다운로드 후 내용 추출"),
            NodeRelation("convertToFile", RelationType.COMMONLY_USED_WITH, 0.75,
                         "파일 생성 후 Nextcloud 업로드"),
        ],
    ),
    N8NNodeDef(
        short_type="awsS3",
        full_type="n8n-nodes-base.awsS3",
        display_name="AWS S3",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"aws", "s3", "storage", "bucket", "cloud", "file", "object"}),
        relations=[
            NodeRelation("extractFromFile", RelationType.COMMONLY_USED_WITH, 0.80,
                         "S3 파일 다운로드 후 내용 추출"),
            NodeRelation("convertToFile", RelationType.COMMONLY_USED_WITH, 0.75,
                         "파일 생성 후 S3 업로드"),
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.70,
                         "Presigned URL 생성 후 HTTP 업로드"),
        ],
    ),
    N8NNodeDef(
        short_type="stripe",
        full_type="n8n-nodes-base.stripe",
        display_name="Stripe",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"stripe", "payment", "billing", "subscription", "fintech"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "결제 데이터 필드 구성"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Stripe 결제·구독 웹훅 이벤트 처리"),
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.70,
                         "결제 내역 스프레드시트 기록"),
        ],
    ),
    N8NNodeDef(
        short_type="mongoDb",
        full_type="n8n-nodes-base.mongoDb",
        display_name="MongoDB",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"mongodb", "database", "nosql", "document", "storage"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "MongoDB 도큐먼트 필드 구성"),
            NodeRelation("splitInBatches", RelationType.COMPLEMENTED_BY, 0.70,
                         "대량 도큐먼트 배치 삽입"),
        ],
    ),
    N8NNodeDef(
        short_type="emailReadImap",
        full_type="n8n-nodes-base.emailReadImap",
        display_name="Email (IMAP)",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"email", "imap", "inbox", "read", "receive", "smtp"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "이메일 제목·발신자·본문 필드 추출"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "발신자·제목 조건 기반 이메일 분류"),
            NodeRelation("emailSend", RelationType.COMMONLY_USED_WITH, 0.75,
                         "수신 이메일 분석 후 자동 회신 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="facebookGraphApi",
        full_type="n8n-nodes-base.facebookGraphApi",
        display_name="Facebook Graph API",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"facebook", "meta", "graph", "api", "social", "page", "ad"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Graph API 응답 필드 추출·정제"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.75,
                         "API 결과 기반 조건 분기"),
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.70,
                         "Facebook 광고 데이터 → 시트 기록"),
        ],
    ),
    N8NNodeDef(
        short_type="gmailTool",
        full_type="n8n-nodes-base.gmailTool",
        display_name="Gmail Tool",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"gmail", "tool", "ai-agent", "email", "google"}),
        relations=[
            NodeRelation("gmail", RelationType.REPLACES, 0.80,
                         "AI 에이전트 컨텍스트에서 Gmail 노드 대신 사용"),
            NodeRelation("openAi", RelationType.COMMONLY_USED_WITH, 0.85,
                         "AI 에이전트가 이메일을 처리할 때 조합"),
        ],
    ),
    N8NNodeDef(
        short_type="functionItem",
        full_type="n8n-nodes-base.functionItem",
        display_name="Function Item",
        role=NodeRole.PROCESSING,
        tags=frozenset({"function", "item", "javascript", "deprecated", "transform"}),
        relations=[
            NodeRelation("code", RelationType.REPLACES, 0.95,
                         "n8n v1.x에서 Code 노드(Run Once For Each Item)로 대체됨"),
        ],
    ),
    N8NNodeDef(
        short_type="executeCommand",
        full_type="n8n-nodes-base.executeCommand",
        display_name="Execute Command",
        role=NodeRole.PROCESSING,
        tags=frozenset({"command", "shell", "bash", "system", "execute", "cli"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "커맨드 실행 결과 필드 파싱·정제"),
            NodeRelation("ssh", RelationType.ANTI_PATTERN_WITH, 0.40,
                         "로컬 서버 작업은 SSH 대신 Execute Command 사용 권장"),
        ],
    ),
    N8NNodeDef(
        short_type="ssh",
        full_type="n8n-nodes-base.ssh",
        display_name="SSH",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"ssh", "remote", "server", "command", "linux", "sftp"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "SSH 실행 결과 파싱"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.75,
                         "명령 실행 성공/실패 분기"),
        ],
    ),
    N8NNodeDef(
        short_type="readWriteFile",
        full_type="n8n-nodes-base.readWriteFile",
        display_name="Read/Write Files from Disk",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"file", "read", "write", "disk", "local", "filesystem"}),
        relations=[
            NodeRelation("extractFromFile", RelationType.COMPLEMENTED_BY, 0.85,
                         "디스크 파일 읽기 → 내용 추출 패턴"),
            NodeRelation("convertToFile", RelationType.COMMONLY_USED_WITH, 0.80,
                         "데이터 → 파일 변환 → 디스크 저장"),
            NodeRelation("code", RelationType.COMMONLY_USED_WITH, 0.70,
                         "파일 경로·내용을 Code 노드에서 가공"),
        ],
    ),
    N8NNodeDef(
        short_type="postgresTool",
        full_type="n8n-nodes-base.postgresTool",
        display_name="Postgres (Tool)",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"postgres", "database", "tool", "ai-agent", "sql"}),
        relations=[
            NodeRelation("postgres", RelationType.REPLACES, 0.80,
                         "AI 에이전트 컨텍스트에서 Postgres 노드 대신 사용"),
            NodeRelation("openAi", RelationType.COMMONLY_USED_WITH, 0.85,
                         "AI 에이전트가 DB를 쿼리할 때 조합"),
        ],
    ),
    N8NNodeDef(
        short_type="supabaseTool",
        full_type="n8n-nodes-base.supabaseTool",
        display_name="Supabase (Tool)",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"supabase", "database", "tool", "ai-agent", "postgres"}),
        relations=[
            NodeRelation("supabase", RelationType.REPLACES, 0.80,
                         "AI 에이전트 컨텍스트에서 Supabase 노드 대신 사용"),
            NodeRelation("openAi", RelationType.COMMONLY_USED_WITH, 0.85,
                         "AI 에이전트 DB 쿼리 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="compression",
        full_type="n8n-nodes-base.compression",
        display_name="Compression",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BINARY,
        tags=frozenset({"compression", "zip", "gzip", "compress", "archive", "file"}),
        relations=[
            NodeRelation("readWriteFile", RelationType.COMMONLY_USED_WITH, 0.80,
                         "파일 읽기 → 압축 → 저장"),
            NodeRelation("awsS3", RelationType.COMMONLY_USED_WITH, 0.75,
                         "압축 후 S3 업로드로 스토리지 절약"),
        ],
    ),
    N8NNodeDef(
        short_type="ftp",
        full_type="n8n-nodes-base.ftp",
        display_name="FTP",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"ftp", "sftp", "file", "transfer", "server", "legacy"}),
        relations=[
            NodeRelation("extractFromFile", RelationType.COMMONLY_USED_WITH, 0.80,
                         "FTP 파일 다운로드 후 내용 추출"),
            NodeRelation("convertToFile", RelationType.COMMONLY_USED_WITH, 0.75,
                         "파일 생성 후 FTP 업로드"),
        ],
    ),
    N8NNodeDef(
        short_type="webflow",
        full_type="n8n-nodes-base.webflow",
        display_name="Webflow",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"webflow", "cms", "website", "no-code", "publish"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Webflow CMS 컬렉션 아이템 필드 구성"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.70,
                         "정기 콘텐츠 자동 발행 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="clockify",
        full_type="n8n-nodes-base.clockify",
        display_name="Clockify",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"clockify", "time-tracking", "project", "hours", "billing"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "시간 기록 필드(프로젝트·설명·시간) 구성"),
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.70,
                         "Clockify 타임 로그 → 시트 집계"),
        ],
    ),
    N8NNodeDef(
        short_type="googleSheetsTool",
        full_type="n8n-nodes-base.googleSheetsTool",
        display_name="Google Sheets Tool",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"google", "sheets", "tool", "ai-agent", "spreadsheet"}),
        relations=[
            NodeRelation("googleSheets", RelationType.REPLACES, 0.80,
                         "AI 에이전트 컨텍스트에서 Google Sheets 노드 대신 사용"),
            NodeRelation("openAi", RelationType.COMMONLY_USED_WITH, 0.85,
                         "AI 에이전트가 시트를 읽고 쓸 때 조합"),
        ],
    ),
    N8NNodeDef(
        short_type="form",
        full_type="n8n-nodes-base.form",
        display_name="n8n Form",
        role=NodeRole.UTILITY,
        tags=frozenset({"form", "ui", "multi-step", "page", "collect", "wizard"}),
        relations=[
            NodeRelation("formTrigger", RelationType.COMPLEMENTED_BY, 0.95,
                         "formTrigger로 시작하는 멀티스텝 폼의 중간 페이지 역할"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "폼 입력값 정규화·처리"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.75,
                         "폼 응답 기반 조건 분기"),
        ],
    ),
    N8NNodeDef(
        short_type="mautic",
        full_type="n8n-nodes-base.mautic",
        display_name="Mautic",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"mautic", "marketing", "email", "crm", "automation", "campaign"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Mautic 연락처·캠페인 필드 구성"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.75,
                         "Mautic 이벤트 웹훅 처리"),
            NodeRelation("emailSend", RelationType.ANTI_PATTERN_WITH, 0.35,
                         "Mautic 자체 이메일 기능과 별도 emailSend를 중복 사용 주의"),
        ],
    ),
    N8NNodeDef(
        short_type="htmlExtract",
        full_type="n8n-nodes-base.htmlExtract",
        display_name="HTML Extract",
        role=NodeRole.PROCESSING,
        tags=frozenset({"html", "extract", "scrape", "css", "selector", "parse", "web"}),
        relations=[
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.90,
                         "HTML 페이지 수집 후 CSS 셀렉터로 데이터 추출"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "추출된 텍스트·링크 필드 정제"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.75,
                         "정기 웹 스크래핑 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="datatable",
        full_type="n8n-nodes-base.datatable",
        display_name="Datatable",
        role=NodeRole.PROCESSING,
        tags=frozenset({"datatable", "table", "display", "ui", "html"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "데이터 정제 후 테이블 표시"),
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.70,
                         "시트 데이터 → HTML 테이블 렌더링"),
        ],
    ),
    N8NNodeDef(
        short_type="readBinaryFile",
        full_type="n8n-nodes-base.readBinaryFile",
        display_name="Read Binary File",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BINARY,
        tags=frozenset({"file", "binary", "read", "disk", "local", "deprecated"}),
        relations=[
            NodeRelation("readWriteFile", RelationType.REPLACES, 0.90,
                         "n8n v1.x에서 Read/Write Files 노드로 통합됨"),
            NodeRelation("extractFromFile", RelationType.COMPLEMENTED_BY, 0.80,
                         "바이너리 파일 읽기 → 내용 추출"),
        ],
    ),
    N8NNodeDef(
        short_type="writeBinaryFile",
        full_type="n8n-nodes-base.writeBinaryFile",
        display_name="Write Binary File",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BINARY,
        tags=frozenset({"file", "binary", "write", "disk", "local", "deprecated"}),
        relations=[
            NodeRelation("readWriteFile", RelationType.REPLACES, 0.90,
                         "n8n v1.x에서 Read/Write Files 노드로 통합됨"),
            NodeRelation("convertToFile", RelationType.COMPLEMENTED_BY, 0.80,
                         "데이터 → 바이너리 변환 후 파일 저장"),
        ],
    ),
    N8NNodeDef(
        short_type="strapi",
        full_type="n8n-nodes-base.strapi",
        display_name="Strapi",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"strapi", "cms", "headless", "api", "content", "backend"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Strapi 컬렉션 타입 스키마에 맞게 필드 구성"),
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.75,
                         "Strapi REST API 직접 호출 대안"),
        ],
    ),
    N8NNodeDef(
        short_type="zammad",
        full_type="n8n-nodes-base.zammad",
        display_name="Zammad",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"zammad", "helpdesk", "ticket", "support", "customer", "itsm"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Zammad 티켓 필드(제목·우선순위·그룹) 구성"),
            NodeRelation("emailReadImap", RelationType.COMMONLY_USED_WITH, 0.75,
                         "이메일 수신 → Zammad 티켓 자동 생성"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.70,
                         "이슈 유형·키워드 기반 티켓 라우팅"),
        ],
    ),
    N8NNodeDef(
        short_type="odoo",
        full_type="n8n-nodes-base.odoo",
        display_name="Odoo",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"odoo", "erp", "crm", "inventory", "accounting", "business"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Odoo 모듈(CRM·재고·구매) 필드 정규화"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.70,
                         "Odoo 이벤트 웹훅 처리"),
        ],
    ),
    N8NNodeDef(
        short_type="reddit",
        full_type="n8n-nodes-base.reddit",
        display_name="Reddit",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"reddit", "social", "community", "post", "subreddit", "monitor"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "Reddit 포스트·댓글 필드 구성"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.80,
                         "정기 Reddit 게시물 모니터링 패턴"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.75,
                         "키워드·점수 기반 포스트 필터링"),
        ],
    ),
    N8NNodeDef(
        short_type="lemlist",
        full_type="n8n-nodes-base.lemlist",
        display_name="Lemlist",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"lemlist", "email", "outreach", "cold-email", "sales", "campaign"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Lemlist 캠페인 수신자·개인화 필드 구성"),
            NodeRelation("hubspot", RelationType.COMMONLY_USED_WITH, 0.75,
                         "CRM 리드 → Lemlist 아웃리치 캠페인 추가"),
        ],
    ),
    N8NNodeDef(
        short_type="mondayCom",
        full_type="n8n-nodes-base.mondayCom",
        display_name="Monday.com",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"monday", "project", "board", "task", "team", "workflow"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Monday 아이템 컬럼 필드 구성"),
            NodeRelation("formTrigger", RelationType.COMMONLY_USED_WITH, 0.70,
                         "폼 제출 → Monday 아이템 자동 생성"),
        ],
    ),
    N8NNodeDef(
        short_type="wooCommerce",
        full_type="n8n-nodes-base.wooCommerce",
        display_name="WooCommerce",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"woocommerce", "ecommerce", "wordpress", "order", "product", "shop"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "WooCommerce 주문·상품 필드 구성"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.85,
                         "WooCommerce 주문 완료·결제 웹훅 처리"),
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.70,
                         "주문 데이터 → 시트 집계"),
        ],
    ),
    N8NNodeDef(
        short_type="gitLab",
        full_type="n8n-nodes-base.gitLab",
        display_name="GitLab",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"gitlab", "git", "repository", "ci-cd", "issue", "merge-request"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "GitLab 이슈·MR 필드 구성"),
            NodeRelation("slack", RelationType.COMMONLY_USED_WITH, 0.80,
                         "GitLab 이벤트 → Slack 팀 알림"),
            NodeRelation("jira", RelationType.COMMONLY_USED_WITH, 0.70,
                         "GitLab MR → Jira 티켓 자동 연동"),
        ],
    ),
    N8NNodeDef(
        short_type="openWeatherMap",
        full_type="n8n-nodes-base.openWeatherMap",
        display_name="OpenWeatherMap",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"weather", "openweathermap", "api", "forecast", "temperature"}),
        relations=[
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.90,
                         "정기 날씨 데이터 수집 패턴 — 스케줄 필수"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.85,
                         "기온·강수 임계값 초과 시 알림 분기"),
            NodeRelation("slack", RelationType.COMMONLY_USED_WITH, 0.75,
                         "기상 이상 감지 → Slack/메신저 경보"),
        ],
    ),
    N8NNodeDef(
        short_type="mqtt",
        full_type="n8n-nodes-base.mqtt",
        display_name="MQTT",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"mqtt", "iot", "sensor", "pub-sub", "message", "broker"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "IoT 센서 데이터 필드 정제 후 MQTT 발행"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.75,
                         "센서값 임계치 기반 경보 분기"),
        ],
    ),
    N8NNodeDef(
        short_type="microsoftOneDrive",
        full_type="n8n-nodes-base.microsoftOneDrive",
        display_name="Microsoft OneDrive",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"onedrive", "microsoft", "storage", "file", "office365", "cloud"}),
        relations=[
            NodeRelation("extractFromFile", RelationType.COMMONLY_USED_WITH, 0.80,
                         "OneDrive 파일 다운로드 → 내용 추출"),
            NodeRelation("convertToFile", RelationType.COMMONLY_USED_WITH, 0.75,
                         "파일 생성 → OneDrive 업로드"),
            NodeRelation("microsoftOutlook", RelationType.COMMONLY_USED_WITH, 0.70,
                         "Microsoft 생태계 내 OneDrive + Outlook 조합"),
        ],
    ),
    N8NNodeDef(
        short_type="mailchimp",
        full_type="n8n-nodes-base.mailchimp",
        display_name="Mailchimp",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"mailchimp", "email", "newsletter", "marketing", "campaign", "list"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Mailchimp 구독자 필드(이름·이메일·태그) 구성"),
            NodeRelation("formTrigger", RelationType.COMMONLY_USED_WITH, 0.80,
                         "폼 제출 → Mailchimp 구독자 자동 추가"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.70,
                         "Mailchimp 웹훅 이벤트(구독/취소) 처리"),
        ],
    ),
    N8NNodeDef(
        short_type="git",
        full_type="n8n-nodes-base.git",
        display_name="Git",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"git", "repository", "commit", "push", "pull", "version-control"}),
        relations=[
            NodeRelation("code", RelationType.COMMONLY_USED_WITH, 0.80,
                         "코드 생성 후 Git 커밋 자동화"),
            NodeRelation("github", RelationType.COMMONLY_USED_WITH, 0.75,
                         "로컬 Git 작업 후 GitHub 원격 동기화"),
            NodeRelation("gitLab", RelationType.COMMONLY_USED_WITH, 0.75,
                         "로컬 Git → GitLab 원격 동기화"),
        ],
    ),
    N8NNodeDef(
        short_type="twilioTrigger",
        full_type="n8n-nodes-base.twilioTrigger",
        display_name="Twilio Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"twilio", "sms", "trigger", "inbound", "phone", "webhook"}),
        relations=[
            NodeRelation("twilio", RelationType.COMPLEMENTED_BY, 0.95,
                         "SMS 수신(Trigger) → 처리 → SMS 발송(Twilio) 쌍"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.85,
                         "수신 메시지 내용 기반 자동 응답 분기"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "수신 SMS 발신자·내용 필드 추출"),
        ],
    ),
    N8NNodeDef(
        short_type="theHive",
        full_type="n8n-nodes-base.theHive",
        display_name="TheHive",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"thehive", "security", "incident", "soc", "alert", "case"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "보안 인시던트 케이스 필드 구성"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.80,
                         "외부 보안 이벤트 웹훅 → TheHive 케이스 생성"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.75,
                         "심각도 기반 케이스 우선순위 분기"),
        ],
    ),
    N8NNodeDef(
        short_type="quickbooks",
        full_type="n8n-nodes-base.quickbooks",
        display_name="QuickBooks",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"quickbooks", "accounting", "finance", "invoice", "billing"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "인보이스·고객 필드 구성"),
            NodeRelation("stripe", RelationType.COMMONLY_USED_WITH, 0.75,
                         "Stripe 결제 → QuickBooks 인보이스 자동 생성"),
        ],
    ),
    N8NNodeDef(
        short_type="clearbit",
        full_type="n8n-nodes-base.clearbit",
        display_name="Clearbit",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"clearbit", "enrichment", "company", "lead", "b2b", "data"}),
        relations=[
            NodeRelation("hubspot", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Clearbit 이메일 인리치먼트 후 HubSpot CRM 업데이트"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "인리치먼트 데이터 필드 추출"),
        ],
    ),
    N8NNodeDef(
        short_type="hunter",
        full_type="n8n-nodes-base.hunter",
        display_name="Hunter",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"hunter", "email", "find", "verify", "outreach", "b2b"}),
        relations=[
            NodeRelation("lemlist", RelationType.COMMONLY_USED_WITH, 0.80,
                         "Hunter로 이메일 발굴 → Lemlist 아웃리치 추가"),
            NodeRelation("hubspot", RelationType.COMMONLY_USED_WITH, 0.75,
                         "이메일 발굴 후 CRM에 리드 추가"),
        ],
    ),
    N8NNodeDef(
        short_type="bambooHr",
        full_type="n8n-nodes-base.bambooHr",
        display_name="BambooHR",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"bamboohr", "hr", "employee", "human-resources", "onboarding"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "직원 정보 필드 구성"),
            NodeRelation("emailSend", RelationType.COMMONLY_USED_WITH, 0.75,
                         "직원 온보딩 자동 이메일 발송"),
            NodeRelation("slack", RelationType.COMMONLY_USED_WITH, 0.70,
                         "신규 입사자 정보 Slack 팀 공유"),
        ],
    ),
    N8NNodeDef(
        short_type="copper",
        full_type="n8n-nodes-base.copper",
        display_name="Copper",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"copper", "crm", "google", "sales", "contact", "pipeline"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Copper CRM 연락처·딜 필드 구성"),
            NodeRelation("gmail", RelationType.COMMONLY_USED_WITH, 0.80,
                         "Google 생태계 — Gmail + Copper CRM 연동"),
        ],
    ),
    N8NNodeDef(
        short_type="signl4",
        full_type="n8n-nodes-base.signl4",
        display_name="SIGNL4",
        role=NodeRole.SINK,
        tags=frozenset({"signl4", "alert", "notification", "mobile", "oncall", "itsm"}),
        relations=[
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.85,
                         "임계값 초과·이상 감지 시에만 SIGNL4 경보"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.70,
                         "정기 상태 점검 → 이상 시 SIGNL4 알림"),
        ],
    ),
    N8NNodeDef(
        short_type="wise",
        full_type="n8n-nodes-base.wise",
        display_name="Wise",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"wise", "payment", "transfer", "fintech", "international", "currency"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "송금 금액·수신자 필드 구성"),
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.70,
                         "송금 내역 스프레드시트 기록"),
        ],
    ),
    N8NNodeDef(
        short_type="bannerbear",
        full_type="n8n-nodes-base.bannerbear",
        display_name="Bannerbear",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BINARY,
        tags=frozenset({"bannerbear", "image", "generate", "template", "automation", "social"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Bannerbear 템플릿 변수(텍스트·이미지 URL) 구성"),
            NodeRelation("googleDrive", RelationType.COMMONLY_USED_WITH, 0.75,
                         "생성된 이미지 → Drive 저장"),
            NodeRelation("twitter", RelationType.COMMONLY_USED_WITH, 0.70,
                         "자동 생성 이미지 → SNS 자동 발행"),
        ],
    ),
    N8NNodeDef(
        short_type="matrix",
        full_type="n8n-nodes-base.matrix",
        display_name="Matrix",
        role=NodeRole.SINK,
        tags=frozenset({"matrix", "messaging", "decentralized", "chat", "open-source"}),
        relations=[
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "조건 기반 Matrix 메시지 발송"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.70,
                         "정기 Matrix 알림 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="erpNext",
        full_type="n8n-nodes-base.erpNext",
        display_name="ERPNext",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"erpnext", "erp", "frappe", "accounting", "inventory", "hrm"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "ERPNext 도큐먼트 필드 구성"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.70,
                         "ERPNext 이벤트 웹훅 처리"),
        ],
    ),
    N8NNodeDef(
        short_type="googleCloudNaturalLanguage",
        full_type="n8n-nodes-base.googleCloudNaturalLanguage",
        display_name="Google Cloud Natural Language",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"google", "nlp", "sentiment", "entity", "language", "ai", "text"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "NLP 분석할 텍스트 필드 준비"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "감성 분석 결과 기반 분기 (긍정/부정/중립)"),
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.70,
                         "NLP 분석 결과 → 시트 기록"),
        ],
    ),
    N8NNodeDef(
        short_type="strava",
        full_type="n8n-nodes-base.strava",
        display_name="Strava",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"strava", "fitness", "sport", "activity", "running", "cycling"}),
        relations=[
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.80,
                         "운동 기록 → 시트 대시보드 저장"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.75,
                         "정기 운동 데이터 수집 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="googleDocsTool",
        full_type="n8n-nodes-base.googleDocsTool",
        display_name="Google Docs Tool",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"google", "docs", "tool", "ai-agent", "document"}),
        relations=[
            NodeRelation("googleDocs", RelationType.REPLACES, 0.80,
                         "AI 에이전트 컨텍스트에서 Google Docs 노드 대신 사용"),
            NodeRelation("openAi", RelationType.COMMONLY_USED_WITH, 0.85,
                         "AI 에이전트가 문서를 읽고 편집할 때 조합"),
        ],
    ),
    N8NNodeDef(
        short_type="discordTool",
        full_type="n8n-nodes-base.discordTool",
        display_name="Discord Tool",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"discord", "tool", "ai-agent", "messaging", "community"}),
        relations=[
            NodeRelation("discord", RelationType.REPLACES, 0.80,
                         "AI 에이전트 컨텍스트에서 Discord 노드 대신 사용"),
            NodeRelation("openAi", RelationType.COMMONLY_USED_WITH, 0.85,
                         "AI 에이전트가 Discord 메시지를 처리할 때 조합"),
        ],
    ),
    N8NNodeDef(
        short_type="shopifyTrigger",
        full_type="n8n-nodes-base.shopifyTrigger",
        display_name="Shopify Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"shopify", "ecommerce", "trigger", "order", "webhook", "product"}),
        relations=[
            NodeRelation("shopify", RelationType.COMPLEMENTED_BY, 0.95,
                         "Shopify 이벤트 감지 → Shopify 데이터 처리 쌍"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "주문·고객 이벤트 데이터 필드 추출"),
            NodeRelation("googleSheets", RelationType.COMMONLY_USED_WITH, 0.75,
                         "신규 주문 → 시트 자동 기록"),
        ],
    ),
    N8NNodeDef(
        short_type="calendlyTrigger",
        full_type="n8n-nodes-base.calendlyTrigger",
        display_name="Calendly Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"calendly", "scheduling", "meeting", "trigger", "booking", "calendar"}),
        relations=[
            NodeRelation("googleCalendar", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Calendly 예약 → Google Calendar 이벤트 자동 동기화"),
            NodeRelation("emailSend", RelationType.COMMONLY_USED_WITH, 0.80,
                         "예약 확인 자동 이메일 발송"),
            NodeRelation("zoom", RelationType.COMMONLY_USED_WITH, 0.75,
                         "Calendly 예약 → Zoom 미팅 자동 생성"),
        ],
    ),
    N8NNodeDef(
        short_type="ghost",
        full_type="n8n-nodes-base.ghost",
        display_name="Ghost",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"ghost", "blog", "cms", "newsletter", "publish", "headless"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Ghost 포스트·뉴스레터 필드(제목·슬러그·태그) 구성"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.75,
                         "정기 콘텐츠 자동 발행 패턴"),
            NodeRelation("rssFeedRead", RelationType.COMMONLY_USED_WITH, 0.65,
                         "RSS 뉴스 → Ghost 큐레이션 발행"),
        ],
    ),
    N8NNodeDef(
        short_type="uproc",
        full_type="n8n-nodes-base.uproc",
        display_name="uProc",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"uproc", "enrichment", "data", "email", "phone", "lookup"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "조회 결과 필드 추출·정제"),
            NodeRelation("hubspot", RelationType.COMMONLY_USED_WITH, 0.70,
                         "데이터 인리치먼트 후 CRM 업데이트"),
        ],
    ),
    N8NNodeDef(
        short_type="hackerNews",
        full_type="n8n-nodes-base.hackerNews",
        display_name="Hacker News",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"hackernews", "news", "tech", "community", "feed", "hn"}),
        relations=[
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.85,
                         "정기 HN 트렌딩 기사 수집 패턴"),
            NodeRelation("slack", RelationType.COMMONLY_USED_WITH, 0.80,
                         "HN 인기 글 → Slack 팀 채널 공유"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.75,
                         "HN 기사 제목·URL·점수 필드 추출"),
        ],
    ),
    N8NNodeDef(
        short_type="humanticAi",
        full_type="n8n-nodes-base.humanticAi",
        display_name="Humantic AI",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"humantic", "ai", "personality", "sales", "enrichment", "b2b"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "LinkedIn URL 등 입력 필드 구성"),
            NodeRelation("hubspot", RelationType.COMMONLY_USED_WITH, 0.75,
                         "성격 분석 결과 → CRM 리드 데이터 보강"),
        ],
    ),
    N8NNodeDef(
        short_type="theHiveProject",
        full_type="n8n-nodes-base.theHiveProject",
        display_name="TheHive 5",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"thehive", "security", "incident", "soc", "alert", "case", "v5"}),
        relations=[
            NodeRelation("theHive", RelationType.REPLACES, 0.90,
                         "TheHive 5.x API — theHive (v3/v4) 노드 대신 사용"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "심각도 기반 케이스 우선순위 분기"),
        ],
    ),
    N8NNodeDef(
        short_type="s3",
        full_type="n8n-nodes-base.s3",
        display_name="S3 (Generic)",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"s3", "storage", "bucket", "compatible", "object", "cloud"}),
        relations=[
            NodeRelation("awsS3", RelationType.COMMONLY_USED_WITH, 0.90,
                         "S3 호환 스토리지 (MinIO·Backblaze 등) — awsS3와 유사하나 엔드포인트 설정 필요"),
            NodeRelation("extractFromFile", RelationType.COMMONLY_USED_WITH, 0.80,
                         "S3 파일 다운로드 후 내용 추출"),
            NodeRelation("convertToFile", RelationType.COMMONLY_USED_WITH, 0.75,
                         "파일 생성 후 S3 업로드"),
        ],
    ),
    N8NNodeDef(
        short_type="renameKeys",
        full_type="n8n-nodes-base.renameKeys",
        display_name="Rename Keys",
        role=NodeRole.PROCESSING,
        tags=frozenset({"rename", "keys", "transform", "map", "field", "data"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "Set과 함께 필드명 변경·재구성에 자주 사용"),
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.70,
                         "API 응답 키 정규화에 사용"),
        ],
    ),
    N8NNodeDef(
        short_type="clickUp",
        full_type="n8n-nodes-base.clickUp",
        display_name="ClickUp",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"clickup", "project", "task", "productivity", "team", "agile"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "ClickUp 태스크 필드(이름·우선순위·담당자) 구성"),
            NodeRelation("formTrigger", RelationType.COMMONLY_USED_WITH, 0.70,
                         "폼 제출 → ClickUp 태스크 자동 생성"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.75,
                         "조건 기반 태스크 라우팅·우선순위 분기"),
        ],
    ),
    N8NNodeDef(
        short_type="sendGrid",
        full_type="n8n-nodes-base.sendGrid",
        display_name="SendGrid",
        role=NodeRole.SINK,
        tags=frozenset({"sendgrid", "email", "transactional", "marketing", "smtp"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "SendGrid 이메일 필드(수신자·제목·템플릿) 구성"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "조건 충족 시에만 이메일 발송"),
            NodeRelation("emailSend", RelationType.ANTI_PATTERN_WITH, 0.35,
                         "동일 트리거에 sendGrid + emailSend 중복 사용 주의"),
        ],
    ),
    N8NNodeDef(
        short_type="kafka",
        full_type="n8n-nodes-base.kafka",
        display_name="Kafka",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"kafka", "messaging", "streaming", "event", "queue", "enterprise"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "Kafka 메시지 페이로드 필드 구성"),
            NodeRelation("splitInBatches", RelationType.COMPLEMENTED_BY, 0.70,
                         "대량 이벤트 배치 발행 시 사용"),
            NodeRelation("rabbitmq", RelationType.ANTI_PATTERN_WITH, 0.40,
                         "두 메시지 큐에 동시 발행하면 중복 처리 위험"),
        ],
    ),
    N8NNodeDef(
        short_type="rabbitmq",
        full_type="n8n-nodes-base.rabbitmq",
        display_name="RabbitMQ",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"rabbitmq", "messaging", "queue", "amqp", "microservice"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "RabbitMQ 메시지 페이로드 구성"),
            NodeRelation("kafka", RelationType.ANTI_PATTERN_WITH, 0.40,
                         "두 메시지 큐 동시 사용 시 중복 처리 주의"),
        ],
    ),
    N8NNodeDef(
        short_type="microsoftExcel",
        full_type="n8n-nodes-base.microsoftExcel",
        display_name="Microsoft Excel",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"excel", "microsoft", "spreadsheet", "office365", "table"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Excel 워크시트 셀·행 데이터 구성"),
            NodeRelation("googleSheets", RelationType.ANTI_PATTERN_WITH, 0.35,
                         "동일 데이터를 Excel과 Sheets 양쪽에 쓰면 동기화 불일치"),
        ],
    ),
    N8NNodeDef(
        short_type="googleCalendarTrigger",
        full_type="n8n-nodes-base.googleCalendarTrigger",
        display_name="Google Calendar Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"google", "calendar", "trigger", "event", "schedule", "watch"}),
        relations=[
            NodeRelation("googleCalendar", RelationType.COMPLEMENTED_BY, 0.95,
                         "캘린더 이벤트 감지 → 이벤트 생성/수정 쌍"),
            NodeRelation("emailSend", RelationType.COMMONLY_USED_WITH, 0.80,
                         "캘린더 이벤트 → 참석자 리마인더 이메일"),
            NodeRelation("zoom", RelationType.COMMONLY_USED_WITH, 0.75,
                         "캘린더 이벤트 → Zoom 미팅 자동 생성"),
        ],
    ),
    N8NNodeDef(
        short_type="intercom",
        full_type="n8n-nodes-base.intercom",
        display_name="Intercom",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"intercom", "customer", "support", "chat", "crm", "messaging"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Intercom 연락처·대화 필드 구성"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.75,
                         "사용자 속성 기반 세그먼트 분기"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.70,
                         "Intercom 이벤트 웹훅 처리"),
        ],
    ),
    N8NNodeDef(
        short_type="mailjet",
        full_type="n8n-nodes-base.mailjet",
        display_name="Mailjet",
        role=NodeRole.SINK,
        tags=frozenset({"mailjet", "email", "transactional", "newsletter", "smtp"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Mailjet 이메일 필드(수신자·제목·변수) 구성"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.75,
                         "조건 충족 시에만 이메일 발송"),
        ],
    ),
    N8NNodeDef(
        short_type="microsoftOutlookTool",
        full_type="n8n-nodes-base.microsoftOutlookTool",
        display_name="Microsoft Outlook Tool",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"outlook", "microsoft", "tool", "ai-agent", "email", "office365"}),
        relations=[
            NodeRelation("microsoftOutlook", RelationType.REPLACES, 0.80,
                         "AI 에이전트 컨텍스트에서 Microsoft Outlook 노드 대신 사용"),
            NodeRelation("openAi", RelationType.COMMONLY_USED_WITH, 0.85,
                         "AI 에이전트가 이메일 처리할 때 조합"),
        ],
    ),
    N8NNodeDef(
        short_type="linearTrigger",
        full_type="n8n-nodes-base.linearTrigger",
        display_name="Linear Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"linear", "trigger", "issue", "engineering", "webhook", "agile"}),
        relations=[
            NodeRelation("linear", RelationType.COMPLEMENTED_BY, 0.95,
                         "Linear 이벤트 감지 → 이슈 처리 쌍"),
            NodeRelation("slack", RelationType.COMMONLY_USED_WITH, 0.80,
                         "Linear 이슈 상태 변경 → Slack 팀 알림"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.75,
                         "Linear 이벤트 페이로드 필드 추출"),
        ],
    ),
    N8NNodeDef(
        short_type="wooCommerceTrigger",
        full_type="n8n-nodes-base.wooCommerceTrigger",
        display_name="WooCommerce Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"woocommerce", "ecommerce", "trigger", "order", "webhook", "product"}),
        relations=[
            NodeRelation("wooCommerce", RelationType.COMPLEMENTED_BY, 0.95,
                         "WooCommerce 이벤트 감지 → 데이터 처리 쌍"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "주문·상품 이벤트 데이터 필드 추출"),
            NodeRelation("emailSend", RelationType.COMMONLY_USED_WITH, 0.75,
                         "신규 주문 → 고객 확인 이메일 발송"),
        ],
    ),
    N8NNodeDef(
        short_type="telegramTool",
        full_type="n8n-nodes-base.telegramTool",
        display_name="Telegram Tool",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"telegram", "tool", "ai-agent", "messaging", "bot"}),
        relations=[
            NodeRelation("telegram", RelationType.REPLACES, 0.80,
                         "AI 에이전트 컨텍스트에서 Telegram 노드 대신 사용"),
            NodeRelation("openAi", RelationType.COMMONLY_USED_WITH, 0.85,
                         "AI 에이전트가 Telegram 메시지 처리할 때 조합"),
        ],
    ),
    N8NNodeDef(
        short_type="pagerDuty",
        full_type="n8n-nodes-base.pagerDuty",
        display_name="PagerDuty",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"pagerduty", "alert", "incident", "oncall", "devops", "monitoring"}),
        relations=[
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.85,
                         "임계값 초과 시에만 PagerDuty 인시던트 생성"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.80,
                         "모니터링 시스템 웹훅 → PagerDuty 인시던트 자동 생성"),
            NodeRelation("slack", RelationType.COMMONLY_USED_WITH, 0.75,
                         "PagerDuty 인시던트 생성 → Slack 온콜 팀 알림"),
        ],
    ),
    N8NNodeDef(
        short_type="googleSlides",
        full_type="n8n-nodes-base.googleSlides",
        display_name="Google Slides",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"google", "slides", "presentation", "template", "document"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "슬라이드 텍스트·이미지 변수 필드 구성"),
            NodeRelation("googleDrive", RelationType.COMMONLY_USED_WITH, 0.75,
                         "슬라이드 템플릿 복사 후 Drive에 저장"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.65,
                         "정기 리포트 슬라이드 자동 생성 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="readPDF",
        full_type="n8n-nodes-base.readPDF",
        display_name="Read PDF",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"pdf", "read", "extract", "text", "document", "parse"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "PDF 추출 텍스트 필드 정제"),
            NodeRelation("openAi", RelationType.COMMONLY_USED_WITH, 0.80,
                         "PDF 텍스트 추출 → AI 요약/분석"),
            NodeRelation("googleDrive", RelationType.COMMONLY_USED_WITH, 0.75,
                         "Drive에서 PDF 다운로드 후 내용 추출"),
        ],
    ),
    N8NNodeDef(
        short_type="slackTrigger",
        full_type="n8n-nodes-base.slackTrigger",
        display_name="Slack Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"slack", "trigger", "message", "event", "bot", "webhook"}),
        relations=[
            NodeRelation("slack", RelationType.COMPLEMENTED_BY, 0.95,
                         "Slack 메시지 수신 → 처리 → Slack 발송 쌍"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.85,
                         "채널·키워드·사용자 기반 메시지 분류"),
            NodeRelation("openAi", RelationType.COMMONLY_USED_WITH, 0.75,
                         "Slack 메시지 → AI 처리 → 자동 답변"),
        ],
    ),
    N8NNodeDef(
        short_type="googleTasksTool",
        full_type="n8n-nodes-base.googleTasksTool",
        display_name="Google Tasks Tool",
        role=NodeRole.PROCESSING,
        output_type=OutputType.BOTH,
        tags=frozenset({"google", "tasks", "tool", "ai-agent", "todo"}),
        relations=[
            NodeRelation("googleCalendar", RelationType.COMMONLY_USED_WITH, 0.80,
                         "캘린더 이벤트 → Tasks 연동 패턴"),
            NodeRelation("openAi", RelationType.COMMONLY_USED_WITH, 0.85,
                         "AI 에이전트가 Tasks를 관리할 때 조합"),
        ],
    ),
    N8NNodeDef(
        short_type="xero",
        full_type="n8n-nodes-base.xero",
        display_name="Xero",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"xero", "accounting", "finance", "invoice", "bookkeeping"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Xero 인보이스·거래 필드 구성"),
            NodeRelation("stripe", RelationType.COMMONLY_USED_WITH, 0.75,
                         "Stripe 결제 → Xero 회계 자동 연동"),
        ],
    ),
    N8NNodeDef(
        short_type="awsSes",
        full_type="n8n-nodes-base.awsSes",
        display_name="AWS SES",
        role=NodeRole.SINK,
        tags=frozenset({"aws", "ses", "email", "transactional", "smtp", "cloud"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "SES 이메일 필드(수신자·제목·본문) 구성"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.75,
                         "조건 충족 시에만 이메일 발송"),
            NodeRelation("emailSend", RelationType.ANTI_PATTERN_WITH, 0.35,
                         "두 이메일 발송 노드 중복 사용 주의"),
        ],
    ),
    N8NNodeDef(
        short_type="microsoftToDo",
        full_type="n8n-nodes-base.microsoftToDo",
        display_name="Microsoft To Do",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"microsoft", "todo", "task", "productivity", "office365"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "To Do 항목 필드(제목·기한·중요도) 구성"),
            NodeRelation("microsoftOutlook", RelationType.COMMONLY_USED_WITH, 0.75,
                         "Microsoft 생태계 — Outlook 이메일 → To Do 항목 생성"),
        ],
    ),
    N8NNodeDef(
        short_type="medium",
        full_type="n8n-nodes-base.medium",
        display_name="Medium",
        role=NodeRole.SINK,
        output_type=OutputType.BOTH,
        tags=frozenset({"medium", "blog", "publish", "writing", "content"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.85,
                         "Medium 포스트 필드(제목·내용·태그) 구성"),
            NodeRelation("scheduleTrigger", RelationType.PATTERN_MEMBER, 0.75,
                         "정기 콘텐츠 자동 발행 패턴"),
        ],
    ),
    N8NNodeDef(
        short_type="rocketchat",
        full_type="n8n-nodes-base.rocketchat",
        display_name="Rocket.Chat",
        role=NodeRole.SINK,
        tags=frozenset({"rocketchat", "messaging", "self-hosted", "chat", "team"}),
        relations=[
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.80,
                         "조건 기반 메시지 라우팅"),
            NodeRelation("slack", RelationType.ANTI_PATTERN_WITH, 0.40,
                         "동일 알림을 Slack·Rocket.Chat 양쪽에 보내면 중복 발생"),
        ],
    ),
    N8NNodeDef(
        short_type="pipedriveTrigger",
        full_type="n8n-nodes-base.pipedriveTrigger",
        display_name="Pipedrive Trigger",
        role=NodeRole.TRIGGER,
        tags=frozenset({"pipedrive", "crm", "trigger", "sales", "deal", "webhook"}),
        relations=[
            NodeRelation("pipedrive", RelationType.COMPLEMENTED_BY, 0.95,
                         "Pipedrive 이벤트 감지 → CRM 데이터 처리 쌍"),
            NodeRelation("slack", RelationType.COMMONLY_USED_WITH, 0.80,
                         "딜 상태 변경 → Slack 영업팀 알림"),
            NodeRelation("emailSend", RelationType.COMMONLY_USED_WITH, 0.70,
                         "딜 단계 변경 → 고객 자동 이메일 발송"),
        ],
    ),

    # ══════════════════════════════════════════════════════════════════
    # UTILITIES
    # ══════════════════════════════════════════════════════════════════
    N8NNodeDef(
        short_type="wait",
        full_type="n8n-nodes-base.wait",
        display_name="Wait",
        role=NodeRole.UTILITY,
        tags=frozenset({"wait", "delay", "pause", "timing", "rate-limit", "sleep"}),
        relations=[
            NodeRelation("splitInBatches", RelationType.COMMONLY_USED_WITH, 0.90,
                         "배치 처리 간 Rate Limit 대기"),
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.80,
                         "폴링 패턴에서 요청 간격 확보"),
        ],
    ),
    N8NNodeDef(
        short_type="limit",
        full_type="n8n-nodes-base.limit",
        display_name="Limit",
        role=NodeRole.UTILITY,
        tags=frozenset({"limit", "count", "top", "slice", "pagination", "cap"}),
        relations=[
            NodeRelation("sort", RelationType.COMMONLY_USED_WITH, 0.85,
                         "정렬 후 상위 N개만 선택하는 Top-N 패턴"),
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.75,
                         "API 결과 건수 제한"),
        ],
    ),
    N8NNodeDef(
        short_type="sort",
        full_type="n8n-nodes-base.sort",
        display_name="Sort",
        role=NodeRole.UTILITY,
        tags=frozenset({"sort", "order", "rank", "ascending", "descending", "organize"}),
        relations=[
            NodeRelation("limit", RelationType.COMMONLY_USED_WITH, 0.85,
                         "정렬 → 상위 N개 선택 Top-N 패턴"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.70,
                         "정렬 기준 필드 생성 후 Sort"),
        ],
    ),
    N8NNodeDef(
        short_type="dateTime",
        full_type="n8n-nodes-base.dateTime",
        display_name="Date & Time",
        role=NodeRole.UTILITY,
        tags=frozenset({"datetime", "date", "time", "format", "parse", "convert", "timezone"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.80,
                         "변환된 날짜 값을 필드에 저장"),
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.75,
                         "날짜 범위 비교·조건 분기"),
        ],
    ),
    N8NNodeDef(
        short_type="removeDuplicates",
        full_type="n8n-nodes-base.removeDuplicates",
        display_name="Remove Duplicates",
        role=NodeRole.UTILITY,
        tags=frozenset({"dedupe", "unique", "duplicate", "filter", "clean", "distinct"}),
        relations=[
            NodeRelation("aggregate", RelationType.COMMONLY_USED_WITH, 0.75,
                         "중복 제거 후 집계"),
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.70,
                         "비교 키 필드 정규화 후 중복 제거"),
        ],
    ),
    N8NNodeDef(
        short_type="stopAndError",
        full_type="n8n-nodes-base.stopAndError",
        display_name="Stop and Error",
        role=NodeRole.UTILITY,
        output_type=OutputType.NONE,
        tags=frozenset({"error", "stop", "throw", "exception", "halt", "validation"}),
        relations=[
            NodeRelation("if", RelationType.COMMONLY_USED_WITH, 0.85,
                         "IF false 분기 → 워크플로우 중단"),
            NodeRelation("webhook", RelationType.COMMONLY_USED_WITH, 0.70,
                         "입력값 검증 실패 시 에러 종료"),
        ],
    ),
    N8NNodeDef(
        short_type="noOp",
        full_type="n8n-nodes-base.noOp",
        display_name="No Operation",
        role=NodeRole.UTILITY,
        tags=frozenset({"noop", "passthrough", "placeholder", "debug", "empty"}),
    ),
    N8NNodeDef(
        short_type="stickyNote",
        full_type="n8n-nodes-base.stickyNote",
        display_name="Sticky Note",
        role=NodeRole.UTILITY,
        tags=frozenset({"note", "comment", "documentation", "sticky", "label"}),
    ),
    N8NNodeDef(
        short_type="moveBinaryData",
        full_type="n8n-nodes-base.moveBinaryData",
        display_name="Move Binary Data",
        role=NodeRole.UTILITY,
        output_type=OutputType.BOTH,
        tags=frozenset({"binary", "move", "convert", "data", "file"}),
        relations=[
            NodeRelation("extractFromFile", RelationType.COMMONLY_USED_WITH, 0.75,
                         "바이너리 데이터 이동 후 내용 추출"),
        ],
    ),
    N8NNodeDef(
        short_type="executionData",
        full_type="n8n-nodes-base.executionData",
        display_name="Execution Data",
        role=NodeRole.UTILITY,
        tags=frozenset({"execution", "data", "save", "persist", "workflow"}),
    ),

    # ══════════════════════════════════════════════════════════════════
    # SINKS — 2026-09 노드 커버리지 보강 (수동 완전 명세)
    # 실제 n8n 인스턴스 카탈로그 전수조사로 발견된 273개 누락 노드 중, Tool/Trigger
    # 변형 관계로 반자동 연결되지 않는 217개 독립 서비스 노드 가운데 실사용 빈도가
    # 높다고 판단되는 노드를 선별하여, 기존 수동 노드와 동일한 수준(역할·태그·관계)
    # 으로 완전 명세하였다.
    # ══════════════════════════════════════════════════════════════════
    N8NNodeDef(
        short_type="awsLambda", full_type="n8n-nodes-base.awsLambda",
        display_name="AWS Lambda", role=NodeRole.SINK,
        tags=frozenset({"aws", "lambda", "serverless", "function", "cloud"}),
        relations=[
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.6,
                         "Lambda 함수 호출 결과를 후속 API 연동에 활용"),
            NodeRelation("code", RelationType.ANTI_PATTERN_WITH, 0.4,
                         "단순 로직은 Code 노드로 대체 가능 — Lambda는 별도 배포·긴 실행시간이 필요할 때만 권장"),
        ],
    ),
    N8NNodeDef(
        short_type="awsSns", full_type="n8n-nodes-base.awsSns",
        display_name="AWS SNS", role=NodeRole.SINK,
        tags=frozenset({"aws", "sns", "notification", "pubsub", "cloud"}),
        relations=[
            NodeRelation("awsSqs", RelationType.PATTERN_MEMBER, 0.7,
                         "SNS 팬아웃 → SQS 구독 패턴의 구성원"),
        ],
    ),
    N8NNodeDef(
        short_type="awsSqs", full_type="n8n-nodes-base.awsSqs",
        display_name="AWS SQS", role=NodeRole.SINK,
        tags=frozenset({"aws", "sqs", "queue", "cloud"}),
        relations=[
            NodeRelation("awsSns", RelationType.PATTERN_MEMBER, 0.7,
                         "SNS 팬아웃 → SQS 구독 패턴의 구성원"),
        ],
    ),
    N8NNodeDef(
        short_type="awsDynamodb", full_type="n8n-nodes-base.awsDynamodb",
        display_name="AWS DynamoDB", role=NodeRole.SINK,
        tags=frozenset({"aws", "dynamodb", "nosql", "database", "cloud"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.7,
                         "DynamoDB 아이템 스키마에 맞춘 필드 정제에 Set 필요"),
        ],
    ),
    N8NNodeDef(
        short_type="azureCosmosDb", full_type="n8n-nodes-base.azureCosmosDb",
        display_name="Azure Cosmos DB", role=NodeRole.SINK,
        tags=frozenset({"azure", "cosmosdb", "nosql", "database", "cloud"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.65,
                         "문서 스키마 정제에 Set 필요"),
        ],
    ),
    N8NNodeDef(
        short_type="azureStorage", full_type="n8n-nodes-base.azureStorage",
        display_name="Azure Storage", role=NodeRole.SINK,
        tags=frozenset({"azure", "storage", "blob", "file", "cloud"}),
    ),
    N8NNodeDef(
        short_type="elasticSearch", full_type="n8n-nodes-base.elasticSearch",
        display_name="Elasticsearch", role=NodeRole.SINK,
        tags=frozenset({"elasticsearch", "search", "index", "database", "logging"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.65,
                         "색인 전 문서 필드 정제에 Set 필요"),
        ],
    ),
    N8NNodeDef(
        short_type="questDb", full_type="n8n-nodes-base.questDb",
        display_name="QuestDB", role=NodeRole.SINK,
        tags=frozenset({"questdb", "timeseries", "database"}),
    ),
    N8NNodeDef(
        short_type="timescaleDb", full_type="n8n-nodes-base.timescaleDb",
        display_name="TimescaleDB", role=NodeRole.SINK,
        tags=frozenset({"timescaledb", "timeseries", "database", "postgres"}),
    ),
    N8NNodeDef(
        short_type="crateDb", full_type="n8n-nodes-base.crateDb",
        display_name="CrateDB", role=NodeRole.SINK,
        tags=frozenset({"cratedb", "database", "sql"}),
    ),
    N8NNodeDef(
        short_type="oracleDatabase", full_type="n8n-nodes-base.oracleDatabase",
        display_name="Oracle Database", role=NodeRole.SINK,
        tags=frozenset({"oracle", "database", "sql", "enterprise"}),
        relations=[
            NodeRelation("microsoftSql", RelationType.ANTI_PATTERN_WITH, 0.3,
                         "동일 워크플로우에서 이종 RDBMS 동시 연결은 드물고 유지보수 복잡도 증가"),
        ],
    ),
    N8NNodeDef(
        short_type="microsoftSql", full_type="n8n-nodes-base.microsoftSql",
        display_name="Microsoft SQL", role=NodeRole.SINK,
        tags=frozenset({"microsoft", "sql", "database", "mssql"}),
    ),
    N8NNodeDef(
        short_type="googleBigQuery", full_type="n8n-nodes-base.googleBigQuery",
        display_name="Google BigQuery", role=NodeRole.SINK,
        tags=frozenset({"google", "bigquery", "database", "analytics", "warehouse"}),
        relations=[
            NodeRelation("scheduleTrigger", RelationType.COMMONLY_USED_WITH, 0.7,
                         "정기 배치 집계·리포팅 패턴에서 자주 조합됨"),
        ],
    ),
    N8NNodeDef(
        short_type="googleAds", full_type="n8n-nodes-base.googleAds",
        display_name="Google Ads", role=NodeRole.SINK,
        tags=frozenset({"google", "ads", "marketing", "advertising"}),
    ),
    N8NNodeDef(
        short_type="googleTasks", full_type="n8n-nodes-base.googleTasks",
        display_name="Google Tasks", role=NodeRole.SINK,
        tags=frozenset({"google", "tasks", "productivity", "todo"}),
    ),
    N8NNodeDef(
        short_type="googleChat", full_type="n8n-nodes-base.googleChat",
        display_name="Google Chat", role=NodeRole.SINK,
        tags=frozenset({"google", "chat", "messaging", "collaboration"}),
        relations=[
            NodeRelation("slack", RelationType.ANTI_PATTERN_WITH, 0.3,
                         "동일 알림을 Slack과 Google Chat 양쪽에 중복 발송하는 것은 대개 불필요"),
        ],
    ),
    N8NNodeDef(
        short_type="googleCloudStorage", full_type="n8n-nodes-base.googleCloudStorage",
        display_name="Google Cloud Storage", role=NodeRole.SINK,
        tags=frozenset({"google", "storage", "file", "cloud", "bucket"}),
    ),
    N8NNodeDef(
        short_type="googleContacts", full_type="n8n-nodes-base.googleContacts",
        display_name="Google Contacts", role=NodeRole.SINK,
        tags=frozenset({"google", "contacts", "crm"}),
    ),
    N8NNodeDef(
        short_type="googleTranslate", full_type="n8n-nodes-base.googleTranslate",
        display_name="Google Translate", role=NodeRole.PROCESSING,
        tags=frozenset({"google", "translate", "language", "ai"}),
        relations=[
            NodeRelation("set", RelationType.COMMONLY_USED_WITH, 0.65,
                         "번역 결과를 원본 필드와 함께 재구성할 때 Set 필요"),
        ],
    ),
    N8NNodeDef(
        short_type="microsoftDynamicsCrm", full_type="n8n-nodes-base.microsoftDynamicsCrm",
        display_name="Microsoft Dynamics CRM", role=NodeRole.SINK,
        tags=frozenset({"microsoft", "crm", "dynamics", "sales"}),
    ),
    N8NNodeDef(
        short_type="microsoftSharePoint", full_type="n8n-nodes-base.microsoftSharePoint",
        display_name="Microsoft SharePoint", role=NodeRole.SINK,
        tags=frozenset({"microsoft", "sharepoint", "document", "collaboration"}),
    ),
    N8NNodeDef(
        short_type="activeCampaign", full_type="n8n-nodes-base.activeCampaign",
        display_name="ActiveCampaign", role=NodeRole.SINK,
        tags=frozenset({"activecampaign", "crm", "marketing", "email"}),
        relations=[
            NodeRelation("convertKit", RelationType.ANTI_PATTERN_WITH, 0.3,
                         "동일 목적의 이메일 마케팅 서비스 중복 연동은 대개 불필요"),
        ],
    ),
    N8NNodeDef(
        short_type="convertKit", full_type="n8n-nodes-base.convertKit",
        display_name="ConvertKit", role=NodeRole.SINK,
        tags=frozenset({"convertkit", "email", "marketing"}),
    ),
    N8NNodeDef(
        short_type="mailerLite", full_type="n8n-nodes-base.mailerLite",
        display_name="MailerLite", role=NodeRole.SINK,
        tags=frozenset({"mailerlite", "email", "marketing"}),
    ),
    N8NNodeDef(
        short_type="mailGun", full_type="n8n-nodes-base.mailGun",
        display_name="Mailgun", role=NodeRole.SINK,
        tags=frozenset({"mailgun", "email", "transactional"}),
        relations=[
            NodeRelation("emailSend", RelationType.REPLACES, 0.5,
                         "SMTP 직접 발송(Send Email) 대신 API 기반 발송 대행 서비스로 대체 가능"),
        ],
    ),
    N8NNodeDef(
        short_type="customerIo", full_type="n8n-nodes-base.customerIo",
        display_name="Customer.io", role=NodeRole.SINK,
        tags=frozenset({"customerio", "marketing", "automation", "crm"}),
    ),
    N8NNodeDef(
        short_type="zoHoCrm", full_type="n8n-nodes-base.zoHoCrm",
        display_name="Zoho CRM", role=NodeRole.SINK,
        tags=frozenset({"zoho", "crm", "sales"}),
    ),
    N8NNodeDef(
        short_type="freshworksCrm", full_type="n8n-nodes-base.freshworksCrm",
        display_name="Freshworks CRM", role=NodeRole.SINK,
        tags=frozenset({"freshworks", "crm", "sales"}),
    ),
    N8NNodeDef(
        short_type="monicaCrm", full_type="n8n-nodes-base.monicaCrm",
        display_name="Monica CRM", role=NodeRole.SINK,
        tags=frozenset({"monica", "crm", "personal"}),
    ),
    N8NNodeDef(
        short_type="freshdesk", full_type="n8n-nodes-base.freshdesk",
        display_name="Freshdesk", role=NodeRole.SINK,
        tags=frozenset({"freshdesk", "support", "helpdesk", "ticket"}),
        relations=[
            NodeRelation("freshservice", RelationType.ANTI_PATTERN_WITH, 0.3,
                         "같은 회사의 유사 헬프데스크 제품 — 동일 목적 중복 연동은 대개 불필요"),
        ],
    ),
    N8NNodeDef(
        short_type="freshservice", full_type="n8n-nodes-base.freshservice",
        display_name="Freshservice", role=NodeRole.SINK,
        tags=frozenset({"freshservice", "support", "itsm", "ticket"}),
    ),
    N8NNodeDef(
        short_type="helpScout", full_type="n8n-nodes-base.helpScout",
        display_name="Help Scout", role=NodeRole.SINK,
        tags=frozenset({"helpscout", "support", "helpdesk", "email"}),
    ),
    N8NNodeDef(
        short_type="serviceNow", full_type="n8n-nodes-base.serviceNow",
        display_name="ServiceNow", role=NodeRole.SINK,
        tags=frozenset({"servicenow", "itsm", "enterprise", "ticket"}),
    ),
    N8NNodeDef(
        short_type="circleci", full_type="n8n-nodes-base.circleci",
        display_name="CircleCI", role=NodeRole.SINK,
        tags=frozenset({"circleci", "ci", "cd", "devops"}),
        relations=[
            NodeRelation("gitLabTrigger", RelationType.COMMONLY_USED_WITH, 0.5,
                         "저장소 이벤트 트리거 이후 CI 파이프라인 상태 조회에 함께 사용"),
        ],
    ),
    N8NNodeDef(
        short_type="jenkins", full_type="n8n-nodes-base.jenkins",
        display_name="Jenkins", role=NodeRole.SINK,
        tags=frozenset({"jenkins", "ci", "cd", "devops"}),
    ),
    N8NNodeDef(
        short_type="travisci", full_type="n8n-nodes-base.travisci",
        display_name="Travis CI", role=NodeRole.SINK,
        tags=frozenset({"travisci", "ci", "cd", "devops"}),
    ),
    N8NNodeDef(
        short_type="bitbucketTrigger", full_type="n8n-nodes-base.bitbucketTrigger",
        display_name="Bitbucket Trigger", role=NodeRole.TRIGGER,
        tags=frozenset({"bitbucket", "trigger", "git", "devops"}),
        relations=[
            NodeRelation("gitLab", RelationType.ANTI_PATTERN_WITH, 0.3,
                         "동일 저장소를 여러 Git 호스팅 서비스 트리거로 중복 감시하는 것은 대개 불필요"),
        ],
    ),
    N8NNodeDef(
        short_type="netlify", full_type="n8n-nodes-base.netlify",
        display_name="Netlify", role=NodeRole.SINK,
        tags=frozenset({"netlify", "hosting", "deploy", "devops"}),
    ),
    N8NNodeDef(
        short_type="coda", full_type="n8n-nodes-base.coda",
        display_name="Coda", role=NodeRole.SINK,
        tags=frozenset({"coda", "productivity", "document", "database"}),
    ),
    N8NNodeDef(
        short_type="confluence", full_type="n8n-nodes-base.confluence",
        display_name="Confluence", role=NodeRole.SINK,
        tags=frozenset({"confluence", "atlassian", "document", "wiki", "collaboration"}),
        relations=[
            NodeRelation("jiraTool", RelationType.COMMONLY_USED_WITH, 0.6,
                         "동일 Atlassian 생태계(Jira) 연동과 함께 쓰이는 경우가 많음"),
        ],
    ),
    N8NNodeDef(
        short_type="grist", full_type="n8n-nodes-base.grist",
        display_name="Grist", role=NodeRole.SINK,
        tags=frozenset({"grist", "spreadsheet", "database", "productivity"}),
    ),
    N8NNodeDef(
        short_type="box", full_type="n8n-nodes-base.box",
        display_name="Box", role=NodeRole.SINK,
        tags=frozenset({"box", "storage", "file", "collaboration"}),
        relations=[
            NodeRelation("dropbox", RelationType.ANTI_PATTERN_WITH, 0.3,
                         "동일 목적의 파일 저장소 중복 연동은 대개 불필요"),
        ],
    ),
    N8NNodeDef(
        short_type="line", full_type="n8n-nodes-base.line",
        display_name="LINE", role=NodeRole.SINK,
        tags=frozenset({"line", "messaging", "chat", "notification"}),
    ),
    N8NNodeDef(
        short_type="gong", full_type="n8n-nodes-base.gong",
        display_name="Gong", role=NodeRole.SINK,
        tags=frozenset({"gong", "sales", "analytics", "call"}),
    ),
    N8NNodeDef(
        short_type="messagebird", full_type="n8n-nodes-base.messagebird",
        display_name="MessageBird", role=NodeRole.SINK,
        tags=frozenset({"messagebird", "sms", "messaging", "notification"}),
        relations=[
            NodeRelation("twilio", RelationType.ANTI_PATTERN_WITH, 0.3,
                         "동일 목적의 SMS 발송 서비스 중복 연동은 대개 불필요"),
        ],
    ),
    N8NNodeDef(
        short_type="mistralAi", full_type="n8n-nodes-base.mistralAi",
        display_name="Mistral AI", role=NodeRole.PROCESSING,
        tags=frozenset({"mistral", "ai", "llm", "language"}),
        relations=[
            NodeRelation("openai", RelationType.ANTI_PATTERN_WITH, 0.3,
                         "동일 워크플로우에서 복수 LLM 제공자 동시 연동은 특별한 이유(비교·폴백) 없이는 드묾"),
        ],
    ),
    N8NNodeDef(
        short_type="jinaAi", full_type="n8n-nodes-base.jinaAi",
        display_name="Jina AI", role=NodeRole.PROCESSING,
        tags=frozenset({"jina", "ai", "embedding", "search"}),
    ),
    N8NNodeDef(
        short_type="perplexity", full_type="n8n-nodes-base.perplexity",
        display_name="Perplexity", role=NodeRole.PROCESSING,
        tags=frozenset({"perplexity", "ai", "search", "llm"}),
        relations=[
            NodeRelation("httpRequest", RelationType.COMMONLY_USED_WITH, 0.5,
                         "검색 결과를 후속 API 연동으로 전달하는 패턴에서 함께 사용"),
        ],
    ),
    N8NNodeDef(
        short_type="segment", full_type="n8n-nodes-base.segment",
        display_name="Segment", role=NodeRole.SINK,
        tags=frozenset({"segment", "analytics", "cdp", "tracking"}),
    ),
    N8NNodeDef(
        short_type="splunk", full_type="n8n-nodes-base.splunk",
        display_name="Splunk", role=NodeRole.SINK,
        tags=frozenset({"splunk", "logging", "observability", "security"}),
    ),
    N8NNodeDef(
        short_type="grafana", full_type="n8n-nodes-base.grafana",
        display_name="Grafana", role=NodeRole.SINK,
        tags=frozenset({"grafana", "monitoring", "observability", "dashboard"}),
    ),
    N8NNodeDef(
        short_type="metabase", full_type="n8n-nodes-base.metabase",
        display_name="Metabase", role=NodeRole.SINK,
        tags=frozenset({"metabase", "analytics", "bi", "dashboard"}),
    ),
    N8NNodeDef(
        short_type="posthog", full_type="n8n-nodes-base.posthog",
        display_name="PostHog", role=NodeRole.SINK,
        tags=frozenset({"posthog", "analytics", "product", "tracking"}),
    ),
    N8NNodeDef(
        short_type="sentryIo", full_type="n8n-nodes-base.sentryIo",
        display_name="Sentry.io", role=NodeRole.SINK,
        tags=frozenset({"sentry", "error", "monitoring", "observability"}),
    ),
    N8NNodeDef(
        short_type="paypal", full_type="n8n-nodes-base.paypal",
        display_name="PayPal", role=NodeRole.SINK,
        tags=frozenset({"paypal", "payment", "billing"}),
        relations=[
            NodeRelation("stripe", RelationType.ANTI_PATTERN_WITH, 0.3,
                         "동일 결제 목적의 복수 PG사 동시 연동은 특별한 이유 없이는 드묾"),
        ],
    ),
    N8NNodeDef(
        short_type="paddle", full_type="n8n-nodes-base.paddle",
        display_name="Paddle", role=NodeRole.SINK,
        tags=frozenset({"paddle", "payment", "billing", "subscription"}),
    ),
    N8NNodeDef(
        short_type="workflowTrigger", full_type="n8n-nodes-base.workflowTrigger",
        display_name="Workflow Trigger", role=NodeRole.TRIGGER,
        tags=frozenset({"workflow", "trigger", "lifecycle", "meta"}),
        relations=[
            NodeRelation("executeWorkflow", RelationType.COMPLEMENTED_BY, 0.7,
                         "서브워크플로우 호출(Execute Workflow)과 짝을 이루는 생명주기 트리거"),
        ],
    ),
    N8NNodeDef(
        short_type="n8n", full_type="n8n-nodes-base.n8n",
        display_name="n8n", role=NodeRole.UTILITY,
        tags=frozenset({"n8n", "meta", "self", "workflow", "api"}),
        relations=[
            NodeRelation("workflowTrigger", RelationType.COMMONLY_USED_WITH, 0.5,
                         "n8n 자체 API로 워크플로우/실행 이력을 조회·관리하는 메타 자동화 패턴"),
        ],
    ),
]

# ══════════════════════════════════════════════════════════════════════
# 3-A-2. 자동 생성 노드 정의 (NodeTaxonomy 자동 확장)
#
# RAG에 존재하는 모든 노드를 커버하기 위해 수동 정의에 없는 노드들을
# 기본 NodeDef (role, tags, output_type) 만으로 자동 생성.
# RelationGraph·PropertyConstraints는 수동 정의 노드에만 적용됨.
# ══════════════════════════════════════════════════════════════════════

import re as _re

def _camel_to_display(s: str) -> str:
    """camelCase → Title Case (예: 'googleDrive' → 'Google Drive')"""
    result = _re.sub(r'([A-Z])', r' \1', s).strip()
    return result.title()

def _infer_role(short_type: str) -> NodeRole:
    st = short_type.lower()
    if st.endswith("trigger") or st in ("cron", "interval", "errortrigger"):
        return NodeRole.TRIGGER
    if st in ("respondtowebhook", "stopanderror", "noop", "stickynote",
              "wait", "limit", "sort", "datetime", "removeduplicates",
              "movebinarydata", "executiondata", "debughelper"):
        return NodeRole.UTILITY
    if st in ("set", "if", "switch", "code", "filter", "merge", "splitout",
              "splitinbatches", "aggregate", "summarize", "itemlists",
              "compareDatasets", "executeworkflow", "function", "functionitem",
              "html", "markdown", "xml", "crypto", "editimage", "openai",
              "extractfromfile", "converttofile", "spreadsheetfile", "graphql",
              "htmlextract", "comparedatasets", "aitransform", "totp", "jwt",
              "compression", "renamekeys", "datatable"):
        return NodeRole.PROCESSING
    return NodeRole.SINK

def _make_tags(short_type: str) -> FrozenSet[str]:
    words = [w.lower() for w in _re.sub(r'([A-Z])', r' \1', short_type).split() if w]
    tags = set(words)
    if "trigger" in words:
        tags.update({"trigger", "event"})
    if "tool" in words:
        tags.update({"tool", "ai-agent"})
    if any(w in words for w in ("mail", "email", "gmail", "outlook")):
        tags.add("email")
    if any(w in words for w in ("google",)):
        tags.add("google")
    if any(w in words for w in ("microsoft",)):
        tags.add("microsoft")
    if any(w in words for w in ("aws", "amazon")):
        tags.add("aws")
    return frozenset(tags)

# 수동 정의된 노드 short_type 집합 (소문자, 충돌 방지용)
_MANUAL_SHORT_SET: FrozenSet[str] = frozenset(n.short_type.lower() for n in _NODE_DEFS)

# RAG에서 추출된 전체 노드 short_type 목록 (camelCase, 빈도 3회 이상)
# 수동 정의된 노드 및 노이즈는 자동 생성에서 제외됨
_RAW_ALL_NODES: List[str] = [
    "actionNetwork","activeCampaign","activeCampaignTrigger","acuitySchedulingTrigger",
    "adalo","affinity","affinityTrigger","agilecrm","agileCrm",
    "aiTransform","amqp","amqpTrigger","apiTemplateIo","asana","asanaTrigger",
    "automizy","autopilot","autopilotTrigger","awsCertificateManager","awsCognito",
    "awsComprehend","awsDynamodb","awsElb","awsIam","awsLambda","awsRekognition",
    "awsS3","awsSes","awsSns","awsSnsTrigger","awsSqs","awsTextract","awsTranscribe",
    "azureCosmosDb","azureStorage","bambooHr","bannerbear","baserow","baserowTool",
    "beeminder","bitbucketTrigger","bitly","bitwarden","box","boxTrigger","brandfetch",
    "brevo","brevoTrigger","bubble","calendlyTrigger","calTrigger","chargebee",
    "chargebeeTrigger","circleci","ciscoWebex","ciscoWebexTrigger","clearbit",
    "clickUp","clickUpTrigger","clockify","clockifyTrigger","cloudflare","cockpit",
    "coda","coinGecko","compression","contentful","convertKit","convertKitTrigger",
    "copper","copperTrigger","cortex","crateDb","crowdDev","crowdDevTrigger",
    "customerIo","customerIoTrigger","datatable","databricks","debugHelper","deepl",
    "demio","dhl","discourse","discordTool","disqus","drift","dropbox","dropcontact",
    "egoi","elasticSearch","elasticSecurity","emailImap","emailReadImap","emelia",
    "emeliatrigger","erpNext","evaluation","evaluationTrigger","eventbriteTrigger",
    "executeCommand","executeCommandTool","facebookGraphApi","facebookLeadAdsTrigger",
    "facebookTrigger","figmaTrigger","filemaker","filesReadWrite","flow",
    "flowTrigger","formIoTrigger","formstackTrigger","freshdesk","freshservice",
    "freshworksCrm","ftp","functionItem","getResponse","getResponseTrigger",
    "ghost","git","gitLab","gitLabTrigger","gmailTool","gong","googleAds",
    "googleAnalytics","googleAnalyticsTool","googleBigQuery","googleBooks",
    "googleBusinessProfile","googleBusinessProfileTrigger","googleCalendarTrigger",
    "googleChat","googleCloudFirestore","googleCloudNaturalLanguage",
    "googleCloudRealtimeDatabase","googleCloudStorage","googleContacts",
    "googleDocsTool","googleDriveTool","googleFirebaseCloudFirestore",
    "googleFirebaseRealtimeDatabase","googlePerspective","googleSheetsTrigger",
    "googleSheetsTool","googleSlides","googleTasks","googleTasksTool",
    "googleTranslate","gotify","goToWebinar","grafana","grist","gSuiteAdmin",
    "gumroadTrigger","hackerNews","halopsa","harvest","helpScout","helpScoutTrigger",
    "highLevel","homeAssistant","htmlExtract","hubspotTrigger","humanticAi",
    "hunter","iCal","informationExtractor","intercom","interval","invoiceNinja",
    "invoiceNinjaTrigger","iterable","jenkins","jinaAi","jiraTool","jiraTrigger",
    "jotformTrigger","jwt","kafka","kafkaTrigger","keap","keapTrigger","kitemaker",
    "kobotoolbox","kobotoolboxTrigger","ldap","lemlist","lemlistTrigger","line",
    "linear","linearTrigger","lingvaNex","linkedIn","localFileTrigger","lonescale",
    "lonescaleTrigger","mailerLite","mailerLiteTrigger","mailchimp","mailchimpTrigger",
    "mailGun","mailjet","mailjetTrigger","mandrill","matrix","mautic","mauticTrigger",
    "medium","messagebird","metabase","microsoftDynamicsCrm","microsoftEntra",
    "microsoftExcel","microsoftGraphSecurity","microsoftOneDrive","microsoftOneDriveTrigger",
    "microsoftOutlookTrigger","microsoftOutlookTool","microsoftSharePoint",
    "microsoftSql","microsoftTeams","microsoftTeamsTrigger","microsoftToDo",
    "mindee","misp","mistralAi","mocean","mondayCom","mongoDb","mongoDbTool",
    "monicaCrm","mqtt","mqttTrigger","msg","nasa","netlify","netlifyTrigger",
    "netscalerAdc","nextCloud","nocoDb","notiontool","noOp","npm","odoo","okta",
    "oneSimpleApi","onfleet","onfleetTrigger","openThesaurus","openWeatherMap",
    "oracleDb","orbit","oura","paddle","pagerDuty","paypal","paypalTrigger",
    "peekalink","phantombuster","philipsHue","pipedriveTrigger","plivo","postBin",
    "postgresTool","postgresTrigger","postmarkTrigger","posthog","profitwell",
    "pushbullet","pushcut","pushcutTrigger","pushover","questDb","quickbase",
    "quickbooks","quickChart","rabbitmq","rabbitmqTrigger","raindrop",
    "readBinaryFile","readBinaryFiles","readPDF","readWriteFile","reddit",
    "redistool","redistrigger","renameKeys","rocketchat","rssFeedRead",
    "rssFeedReadTrigger","rundeck","s3","salesforce","salesforceTrigger",
    "salesmate","seatable","seatableTrigger","securityScorecard","segment",
    "sendEmail","sendGrid","sendInBlue","sendy","sentryIo","serviceNow",
    "shopify","shopifyTrigger","signl4","slack","slacktrigger","snowflake",
    "splunk","spontit","spotify","spreadsheetFile","sseTrigger","ssh",
    "stackby","start","storyblok","strapi","strava","stravaTrigger","stripe",
    "stripeTrigger","supabaseTool","surveyMonkeyTrigger","syncroMsp","taiga",
    "taigaTrigger","tapfiliate","telegramTool","theHive","theHiveProject",
    "theHiveProjectTrigger","theHiveTrigger","timescaleDb","todoist","togglTrigger",
    "totp","travisci","trello","trelloTrigger","twake","twilio","twilioTrigger",
    "twist","twitter","twitterTool","typeformTrigger","unleashedSoftware",
    "uplead","uproc","uptimeRobot","urlscanIo","venafiTlsProtectCloud",
    "venafiTlsProtectCloudTrigger","venafiTlsProtectDatacenter","vero","vonage",
    "webflow","webflowTrigger","wekan","wise","wiseTrigger","wooCommerce",
    "wooCommerceTool","wooCommerceTrigger","wordpress","wordpressTool",
    "workableTrigger","writeBinaryFile","wufooTrigger","xero","xml","yourls",
    "youTube","zammad","zendesk","zendeskTrigger","zoHoCrm","zoom","zulip",
    "googleAnalyticsTool","htmlExtract","datatable","form","functionItem",
]

# 실제 운영 중인 n8n 인스턴스의 노드 카탈로그(`n8n export:nodes`, n8n-nodes-base.* 706개)를
# 전수조사하여, 위 _RAW_ALL_NODES(RAG 코퍼스 언급 빈도 기준)에 없는 노드를 추가로 확보한 목록.
# 대부분 AI 에이전트용 Tool 변형 노드(예: slackTool)와 HITL(Human-in-the-loop) 노드,
# 그리고 RAG 코퍼스 구축 이후 n8n에 새로 추가된 노드(confluence, perplexity, airtop 등)이다.
# n8n 내부 테스트/트레이닝 전용 노드(e2eTestPollingTrigger, n8nTraining* 2종)는 실제
# 사용자 워크플로우에 등장하지 않으므로 제외하였다.
_RAW_CATALOG_EXTRA_NODES: List[str] = [
    "actionNetworkTool","activeCampaignTool","adaloTool","affinityTool","agileCrmTool",
    "airtableTool","airtableTrigger","airtop","airtopTool","amqpTool",
    "apiTemplateIoTool","asanaTool","autopilotTool","awsLambdaTool","awsS3Tool",
    "awsSesTool","awsSnsTool","awsTextractTool","awsTranscribeTool","bambooHrTool",
    "beeminderTool","bitlyTool","bitwardenTool","BrandfetchTool","bubbleTool",
    "chargebeeTool","circleCiTool","ciscoWebexTool","citrixAdc","clearbitTool",
    "clickUpTool","clockifyTool","cloudflareTool","cockpitTool","codaTool",
    "coinGeckoTool","compressionTool","confluence","contentfulTool","convertKitTool",
    "copperTool","crateDbTool","cryptoTool","currents","currentsTool","currentsTrigger",
    "customerIoTool","databricksTool","dataTableTool","dateTimeTool","deepLTool",
    "demioTool","dhlTool","discordHitlTool","discourseTool","driftTool","dropboxTool",
    "dropcontactTool","egoiTool","elasticsearchTool","elasticSecurityTool",
    "emailSendHitlTool","emailSendTool","emeliaTool","erpNextTool",
    "facebookGraphApiTool","filemakerTool","freshdeskTool","freshserviceTool",
    "freshworksCrmTool","getResponseTool","ghostTool","githubTool","gitlabTool",
    "gitTool","gmailHitlTool","gongTool","googleAdsTool","googleBigQueryTool",
    "googleBooksTool","googleBusinessProfileTool","googleChatHitlTool","googleChatTool",
    "googleCloudNaturalLanguageTool","googleCloudStorageTool","googleContactsTool",
    "googleFirebaseCloudFirestoreTool","googleFirebaseRealtimeDatabaseTool",
    "googlePerspectiveTool","googleSlidesTool","googleTranslateTool","gotifyTool",
    "goToWebinarTool","grafanaTool","graphqlTool","gristTool","gSuiteAdminTool",
    "hackerNewsTool","haloPSATool","harvestTool","helpScoutTool","highLevelTool",
    "homeAssistantTool","httpRequestTool","hubspotTool","humanticAiTool","hunterTool",
    "intercomTool","invoiceNinjaTool","iterableTool","jenkinsTool","jinaAiTool",
    "jwtTool","kafkaTool","keapTool","koBoToolboxTool","ldapTool","lemlistTool",
    "linearTool","lineTool","lingvaNexTool","linkedInTool","loneScaleTool","magento2",
    "magento2Tool","mailcheck","mailcheckTool","mailchimpTool","mailerLiteTool",
    "mailgunTool","mailjetTool","mandrillTool","marketstack","marketstackTool",
    "matrixTool","mattermostTool","mauticTool","mediumTool","messageAnAgent",
    "messageAnAgentTool","messageBirdTool","metabaseTool","microsoftDynamicsCrmTool",
    "microsoftEntraTool","microsoftExcelSharePoint","microsoftExcelSharePointTool",
    "microsoftExcelTool","microsoftGraphSecurityTool","microsoftOneDriveTool",
    "microsoftOutlookHitlTool","microsoftSharePointTool","microsoftSqlTool",
    "microsoftTeamsHitlTool","microsoftTeamsTool","microsoftToDoTool","mispTool",
    "mistralAiTool","moceanTool","mondayComTool","monicaCrmTool","mqttTool","msg91",
    "msg91Tool","mySqlTool","n8n","n8nTrigger","nasaTool","netlifyTool","nextCloudTool",
    "nocoDbTool","npmTool","odooTool","oktaTool","oneSimpleApiTool","onfleetTool",
    "openThesaurusTool","openWeatherMapTool","oracleDatabase","oracleDatabaseTool",
    "ouraTool","paddleTool","pagerDutyTool","peekalinkTool","perplexity",
    "perplexityTool","phantombusterTool","philipsHueTool","pipedriveTool","plivoTool",
    "postBinTool","postHogTool","profitWellTool","pushbulletTool","pushcutTool",
    "pushoverTool","questDbTool","quickbaseTool","quickbooksTool","quickChartTool",
    "rabbitmqTool","raindropTool","redditTool","rocketchatTool","rssFeedReadTool",
    "rundeckTool","s3Tool","salesforceTool","salesmateTool","seaTableTool",
    "securityScorecardTool","segmentTool","sendGridTool","sendInBlueTool",
    "sendInBlueTrigger","sendyTool","sentryIoTool","serviceNowTool","shopifyTool",
    "signl4Tool","simulate","simulateTrigger","slackHitlTool","slackTool","sms77",
    "sms77Tool","snowflakeTool","splunkTool","spotifyTool","stackbyTool",
    "storyblokTool","strapiTool","stravaTool","stripeTool","syncroMspTool","taigaTool",
    "tapfiliateTool","telegramHitlTool","theHiveProjectTool","theHiveTool","timeSaved",
    "timescaleDbTool","todoistTool","totpTool","travisCiTool","trelloTool","twakeTool",
    "twilioTool","twistTool","unleashedSoftwareTool","upleadTool","uprocTool",
    "uptimeRobotTool","urlScanIoTool","venafiTlsProtectCloudTool",
    "venafiTlsProtectDatacenterTool","veroTool","vonageTool","webflowTool","wekanTool",
    "whatsAppHitlTool","whatsAppTool","workflowTrigger","xeroTool","yourlsTool",
    "youTubeTool","zammadTool","zendeskTool","zohoCrmTool","zoomTool","zulipTool",
]

_AUTO_NODE_DEFS: List[N8NNodeDef] = []
_seen_auto: set = set()
for _raw in _RAW_ALL_NODES + _RAW_CATALOG_EXTRA_NODES:
    _key = _raw.lower()
    if _key in _MANUAL_SHORT_SET or _key in _seen_auto:
        continue
    _seen_auto.add(_key)
    _AUTO_NODE_DEFS.append(N8NNodeDef(
        short_type=_raw,
        full_type=f"n8n-nodes-base.{_raw}",
        display_name=_camel_to_display(_raw),
        role=_infer_role(_raw),
        tags=_make_tags(_raw),
    ))

# ── 3-A-보강. Tool/Trigger 변형 노드에 대한 반자동(semi-manual) 관계 부여 ──
# 자동 생성 노드 중 "XxxTool"/"XxxHitlTool"(AI 에이전트용 도구 래퍼) 또는
# "XxxTrigger" 형태의 short_type을 가지면서, 그 기반이 되는 "Xxx" 노드가 이미
# 온톨로지(수동 또는 자동)에 존재하는 경우가 있다. 이 둘은 "동일 서비스의 다른
# 호출 형태"라는 n8n 자체의 구조로 보장되는 관계이므로(예: slackTool은 slack과
# 동일한 Slack API를 AI 에이전트가 호출 가능한 형태로 감싼 것), 임의로 관계를
# 창작하는 것이 아니라 명칭 규칙으로 확정 가능한 사실만을 관계 그래프에 반영한다.
# 이러한 도출 규칙 없이 이름만으로 메타데이터가 생성되는 나머지 노드(레이어 1
# 표에서 "순수 자동"으로 분류)와 구분하기 위해 별도 함수로 분리하였다.
def _link_variant_relations(nodes: "List[N8NNodeDef]") -> int:
    by_short: Dict[str, N8NNodeDef] = {n.short_type.lower(): n for n in _NODE_DEFS + nodes}
    linked = 0
    for n in nodes:
        low = n.short_type.lower()
        base_key: Optional[str] = None
        suffix: Optional[str] = None
        for suf in ("hitltool", "tool", "trigger"):
            if low.endswith(suf) and len(low) > len(suf):
                base_key = low[: -len(suf)]
                suffix = suf
                break
        if base_key is None or base_key not in by_short or base_key == low:
            continue
        base_node = by_short[base_key]
        if n.relations:
            continue
        if suffix in ("tool", "hitltool"):
            n.relations.append(NodeRelation(
                base_node.short_type, RelationType.COMPLEMENTED_BY, 0.9,
                "동일 서비스의 AI 에이전트용 Tool 래퍼 — 표준 노드와 함께 고려됨"))
        else:  # trigger
            n.relations.append(NodeRelation(
                base_node.short_type, RelationType.COMMONLY_USED_WITH, 0.8,
                f"{base_node.display_name} 트리거-액션 쌍 — 같은 서비스 내에서 함께 사용되는 경우가 많음"))
        linked += 1
    return linked


_SEMI_MANUAL_LINKED_COUNT: int = _link_variant_relations(_AUTO_NODE_DEFS)

# 전체 노드 목록: 수동(우선) + 자동 생성(그중 일부는 위 반자동 관계 보강 포함)
_ALL_NODE_DEFS: List[N8NNodeDef] = _NODE_DEFS + _AUTO_NODE_DEFS

# 빠른 조회용 인덱스 (모두 소문자 키로 정규화, 수동 노드가 자동보다 우선)
_NODE_BY_SHORT:   Dict[str, N8NNodeDef] = {n.short_type.lower(): n for n in _ALL_NODE_DEFS}
_NODE_BY_FULL:    Dict[str, N8NNodeDef] = {n.full_type.lower():  n for n in _ALL_NODE_DEFS}
_NODE_BY_DISPLAY: Dict[str, N8NNodeDef] = {n.display_name.lower(): n for n in _ALL_NODE_DEFS}

# ── 3-B. 속성 제약 규칙 (PropertyConstraints) ─────────────────────────

PROPERTY_CONSTRAINTS: List[PropertyConstraint] = [

    # ── HTTP Request ──────────────────────────────────────────────────
    PropertyConstraint(
        node_type="httpRequest",
        property_name="retryOnFail",
        constraint_type=ConstraintType.REQUIRES,
        related_property="maxTries",
        severity=ValidationSeverity.WARNING,
        message="`retryOnFail: true` 설정 시 `maxTries`를 반드시 지정해야 합니다. (기본값 3 권고)",
    ),
    PropertyConstraint(
        node_type="httpRequest",
        property_name="retryOnFail",
        constraint_type=ConstraintType.RECOMMENDED,
        related_property="waitBetweenTries",
        severity=ValidationSeverity.INFO,
        message="`retryOnFail` 활성 시 `waitBetweenTries` 설정으로 서버 과부하를 방지하세요.",
    ),
    PropertyConstraint(
        node_type="httpRequest",
        property_name="sendBody",
        constraint_type=ConstraintType.CONDITIONAL,
        related_property="bodyContentType",
        trigger_value="true",
        severity=ValidationSeverity.WARNING,
        message="`sendBody: true` 시 `bodyContentType`을 명시해야 합니다.",
    ),

    # ── Split In Batches ────────────────────────────────────────────
    PropertyConstraint(
        node_type="splitInBatches",
        property_name="batchSize",
        constraint_type=ConstraintType.RECOMMENDED,
        severity=ValidationSeverity.INFO,
        message="`batchSize`를 API Rate Limit에 맞게 설정하세요. 기본값(10)이 과도할 수 있습니다.",
    ),

    # ── IF / Switch ─────────────────────────────────────────────────
    PropertyConstraint(
        node_type="if",
        property_name="conditions",
        constraint_type=ConstraintType.REQUIRES,
        severity=ValidationSeverity.ERROR,
        message="IF 노드에는 최소 1개 이상의 `conditions`이 필요합니다.",
    ),
    PropertyConstraint(
        node_type="switch",
        property_name="rules",
        constraint_type=ConstraintType.REQUIRES,
        severity=ValidationSeverity.ERROR,
        message="Switch 노드의 `mode: rules` 설정 시 `rules` 배열이 필요합니다.",
    ),

    # ── Code ────────────────────────────────────────────────────────
    PropertyConstraint(
        node_type="code",
        property_name="jsCode",
        constraint_type=ConstraintType.FORBIDDEN,
        trigger_value="fetch(",
        severity=ValidationSeverity.WARNING,
        message="Code 노드 내 `fetch()` 직접 호출은 Anti-pattern입니다. HTTP Request 노드를 사용하세요.",
    ),
    PropertyConstraint(
        node_type="code",
        property_name="jsCode",
        constraint_type=ConstraintType.FORBIDDEN,
        trigger_value="$item(",
        severity=ValidationSeverity.ERROR,
        message="`$item()` 은 n8n v1.x에서 폐기되었습니다. `$json` 을 사용하세요.",
    ),

    # ── Webhook ─────────────────────────────────────────────────────
    PropertyConstraint(
        node_type="webhook",
        property_name="responseMode",
        constraint_type=ConstraintType.CONDITIONAL,
        related_property="respondToWebhook",
        trigger_value="responseNode",
        severity=ValidationSeverity.WARNING,
        message="`responseMode: responseNode` 설정 시 워크플로우 끝에 `Respond to Webhook` 노드가 필요합니다.",
    ),

    # ── Google Sheets ────────────────────────────────────────────────
    PropertyConstraint(
        node_type="googleSheets",
        property_name="operation",
        constraint_type=ConstraintType.CONDITIONAL,
        related_property="limit",
        trigger_value="getAll",
        severity=ValidationSeverity.WARNING,
        message="`operation: getAll` 시 `returnAll` 또는 `limit`을 명시해야 합니다. 미설정 시 전체 시트 로드.",
    ),

    # ── Telegram ─────────────────────────────────────────────────────
    PropertyConstraint(
        node_type="telegram",
        property_name="chatId",
        constraint_type=ConstraintType.REQUIRES,
        severity=ValidationSeverity.ERROR,
        message="Telegram 노드는 `chatId`를 반드시 지정해야 합니다. {{ $json.chat.id }} 표현식 사용 권장.",
    ),
    PropertyConstraint(
        node_type="telegram",
        property_name="text",
        constraint_type=ConstraintType.REQUIRES,
        severity=ValidationSeverity.ERROR,
        message="Telegram sendMessage operation에는 `text` 파라미터가 필수입니다.",
    ),

    # ── Notion ───────────────────────────────────────────────────────
    PropertyConstraint(
        node_type="notion",
        property_name="operation",
        constraint_type=ConstraintType.CONDITIONAL,
        related_property="databaseId",
        trigger_value="create",
        severity=ValidationSeverity.ERROR,
        message="Notion `operation: create` 시 `databaseId`를 반드시 지정해야 합니다.",
    ),
    PropertyConstraint(
        node_type="notion",
        property_name="operation",
        constraint_type=ConstraintType.CONDITIONAL,
        related_property="databaseId",
        trigger_value="getAll",
        severity=ValidationSeverity.WARNING,
        message="Notion `operation: getAll` 시 `databaseId`와 `returnAll`/`limit` 설정을 확인하세요.",
    ),

    # ── Airtable ─────────────────────────────────────────────────────
    PropertyConstraint(
        node_type="airtable",
        property_name="table",
        constraint_type=ConstraintType.REQUIRES,
        severity=ValidationSeverity.ERROR,
        message="Airtable 노드는 `table`(테이블 이름 또는 ID)를 반드시 지정해야 합니다.",
    ),
    PropertyConstraint(
        node_type="airtable",
        property_name="base",
        constraint_type=ConstraintType.REQUIRES,
        severity=ValidationSeverity.ERROR,
        message="Airtable 노드는 `base`(Base ID)를 반드시 지정해야 합니다.",
    ),

    # ── MySQL ────────────────────────────────────────────────────────
    PropertyConstraint(
        node_type="mySql",
        property_name="operation",
        constraint_type=ConstraintType.CONDITIONAL,
        related_property="query",
        trigger_value="executeQuery",
        severity=ValidationSeverity.ERROR,
        message="MySQL `operation: executeQuery` 시 `query` 필드에 SQL문을 입력해야 합니다.",
    ),
    PropertyConstraint(
        node_type="mySql",
        property_name="table",
        constraint_type=ConstraintType.CONDITIONAL,
        related_property="columns",
        trigger_value="insert",
        severity=ValidationSeverity.WARNING,
        message="MySQL `operation: insert` 시 `columns` 파라미터로 삽입할 컬럼을 명시하세요.",
    ),

    # ── OpenAI ───────────────────────────────────────────────────────
    PropertyConstraint(
        node_type="openAi",
        property_name="model",
        constraint_type=ConstraintType.RECOMMENDED,
        severity=ValidationSeverity.INFO,
        message="OpenAI `model`을 명시적으로 지정하세요. 기본값이 변경될 경우 비용·성능이 달라집니다.",
    ),
    PropertyConstraint(
        node_type="openAi",
        property_name="maxTokens",
        constraint_type=ConstraintType.RECOMMENDED,
        severity=ValidationSeverity.INFO,
        message="`maxTokens`를 설정해 과도한 토큰 소비를 방지하세요.",
    ),

    # ── GitHub ───────────────────────────────────────────────────────
    PropertyConstraint(
        node_type="github",
        property_name="owner",
        constraint_type=ConstraintType.REQUIRES,
        severity=ValidationSeverity.ERROR,
        message="GitHub 노드는 `owner`(사용자명 또는 조직명)를 반드시 지정해야 합니다.",
    ),
    PropertyConstraint(
        node_type="github",
        property_name="repository",
        constraint_type=ConstraintType.REQUIRES,
        severity=ValidationSeverity.ERROR,
        message="GitHub 노드는 `repository`(저장소명)를 반드시 지정해야 합니다.",
    ),

    # ── Wait ─────────────────────────────────────────────────────────
    PropertyConstraint(
        node_type="wait",
        property_name="amount",
        constraint_type=ConstraintType.REQUIRES,
        related_property="unit",
        severity=ValidationSeverity.WARNING,
        message="Wait 노드 `amount` 설정 시 `unit`(seconds/minutes/hours)을 함께 명시하세요.",
    ),

    # ── Form Trigger ─────────────────────────────────────────────────
    PropertyConstraint(
        node_type="formTrigger",
        property_name="formFields",
        constraint_type=ConstraintType.REQUIRES,
        severity=ValidationSeverity.WARNING,
        message="n8n Form Trigger에는 최소 1개 이상의 `formFields`(폼 필드)가 필요합니다.",
    ),

    # ── Email Send ───────────────────────────────────────────────────
    PropertyConstraint(
        node_type="emailSend",
        property_name="toEmail",
        constraint_type=ConstraintType.REQUIRES,
        severity=ValidationSeverity.ERROR,
        message="Send Email 노드는 `toEmail`(수신자 이메일)을 반드시 지정해야 합니다.",
    ),
    PropertyConstraint(
        node_type="emailSend",
        property_name="fromEmail",
        constraint_type=ConstraintType.RECOMMENDED,
        severity=ValidationSeverity.WARNING,
        message="Send Email 노드에서 `fromEmail`을 명시하면 발신자를 정확히 지정할 수 있습니다.",
    ),

    # ── Split In Batches 추가 ─────────────────────────────────────────
    PropertyConstraint(
        node_type="splitInBatches",
        property_name="options.reset",
        constraint_type=ConstraintType.RECOMMENDED,
        severity=ValidationSeverity.INFO,
        message="루프 완료 후 재사용하려면 `options.reset: true`를 설정하세요.",
    ),

    # ── Postgres 추가 ────────────────────────────────────────────────
    PropertyConstraint(
        node_type="postgres",
        property_name="operation",
        constraint_type=ConstraintType.CONDITIONAL,
        related_property="query",
        trigger_value="executeQuery",
        severity=ValidationSeverity.ERROR,
        message="Postgres `operation: executeQuery` 시 `query` 필드에 SQL문을 입력해야 합니다.",
    ),

    # ── Code 추가 ────────────────────────────────────────────────────
    PropertyConstraint(
        node_type="code",
        property_name="jsCode",
        constraint_type=ConstraintType.FORBIDDEN,
        trigger_value="$items(",
        severity=ValidationSeverity.ERROR,
        message="`$items()` 은 n8n v1.x에서 폐기되었습니다. `$input.all()`을 사용하세요.",
    ),
    PropertyConstraint(
        node_type="code",
        property_name="jsCode",
        constraint_type=ConstraintType.FORBIDDEN,
        trigger_value="require(",
        severity=ValidationSeverity.WARNING,
        message="Code 노드에서 `require()`는 샌드박스 제한으로 대부분의 모듈을 로드할 수 없습니다.",
    ),
]

# 빠른 조회: {node_type: [PropertyConstraint]}
_CONSTRAINTS_BY_NODE: Dict[str, List[PropertyConstraint]] = {}
for _c in PROPERTY_CONSTRAINTS:
    _CONSTRAINTS_BY_NODE.setdefault(_c.node_type, []).append(_c)


# ── 3-C. 워크플로우 패턴 (WorkflowPatterns) ──────────────────────────

WORKFLOW_PATTERNS: List[WorkflowPattern] = [
    WorkflowPattern(
        name="periodic_api_monitor",
        description="주기적 API 폴링 → 조건 분기 → 알림 패턴",
        node_types=["scheduleTrigger", "httpRequest", "if", "slack"],
        connections=[("scheduleTrigger", "httpRequest"), ("httpRequest", "if"),
                     ("if", "slack")],
        best_practices=[
            "retryOnFail: true + maxTries: 3 on HTTP Request",
            "IF 노드로 정상/이상 응답 분기",
            "Slack 알림은 이상 시에만 발송 (false 분기)",
        ],
        anti_patterns=["HTTP Request에 retryOnFail 미설정", "에러 응답 무시"],
        data_type_hints=["troubleshooting", "api_limits", "official_docs"],
    ),
    WorkflowPattern(
        name="webhook_response",
        description="Webhook 수신 → 처리 → 동기 응답 패턴",
        node_types=["webhook", "set", "respondToWebhook"],
        connections=[("webhook", "set"), ("set", "respondToWebhook")],
        best_practices=[
            "Webhook.responseMode = 'responseNode' 설정",
            "Set으로 응답 데이터 정제 후 respondToWebhook",
            "처리 시간 < 30초 유지 (Webhook 타임아웃)",
        ],
        anti_patterns=["responseMode=immediately 로 빈 응답 반환", "Respond to Webhook 누락"],
        data_type_hints=["spec", "official_docs"],
    ),
    WorkflowPattern(
        name="batch_api_processing",
        description="대량 항목 → 배치 분할 → API 호출 → 집계 패턴",
        node_types=["splitInBatches", "httpRequest", "aggregate"],
        connections=[("splitInBatches", "httpRequest"), ("httpRequest", "aggregate")],
        best_practices=[
            "batchSize를 API Rate Limit에 맞게 설정",
            "waitBetweenTries로 요청 간격 조절",
            "Aggregate로 배치 결과 수집",
        ],
        anti_patterns=["batchSize 미설정으로 전체 항목 한 번에 요청"],
        data_type_hints=["api_limits", "spec"],
    ),
    WorkflowPattern(
        name="etl_pipeline",
        description="데이터 추출 → 변환 → 저장 ETL 패턴",
        node_types=["scheduleTrigger", "httpRequest", "set", "googleSheets"],
        connections=[("scheduleTrigger", "httpRequest"), ("httpRequest", "set"),
                     ("set", "googleSheets")],
        best_practices=[
            "Set 노드로 스키마 정규화 후 Sheets 저장",
            "operation: appendOrUpdate로 중복 방지",
        ],
        data_type_hints=["official_docs", "book"],
    ),
    WorkflowPattern(
        name="array_process_merge",
        description="배열 분리 → 개별 처리 → 재합산 패턴",
        node_types=["splitOut", "httpRequest", "merge"],
        connections=[("splitOut", "httpRequest"), ("httpRequest", "merge")],
        best_practices=[
            "Merge.mode = 'combineBySqlQuery' 또는 'combineAll' 선택",
            "대량 배열은 Split In Batches 후 Split Out 권장",
        ],
        data_type_hints=["spec", "official_docs"],
    ),
    WorkflowPattern(
        name="telegram_bot",
        description="Telegram 봇 수신 → 명령 라우팅 → 응답 패턴",
        node_types=["telegramTrigger", "if", "telegram"],
        connections=[("telegramTrigger", "if"), ("if", "telegram")],
        best_practices=[
            "telegramTrigger → IF로 /start /help 등 명령어 라우팅",
            "telegram 응답 시 chatId에 {{ $('Telegram Trigger').item.json.message.chat.id }} 사용",
            "Switch 노드로 다중 명령어 처리 권장",
        ],
        anti_patterns=[
            "chatId 하드코딩 — 다른 사용자 요청 처리 불가",
            "Telegram Trigger 없이 고정 chatId만으로 메시지 발송 (일방향 알림 전용 패턴과 혼동)",
        ],
        data_type_hints=["official_docs", "book"],
    ),
    WorkflowPattern(
        name="form_collect",
        description="폼 수집 → 데이터 정제 → 저장 + 확인 이메일 패턴",
        node_types=["formTrigger", "set", "googleSheets", "emailSend"],
        connections=[("formTrigger", "set"), ("set", "googleSheets"), ("set", "emailSend")],
        best_practices=[
            "Set 노드로 폼 데이터 스키마 정규화",
            "googleSheets.operation = 'append' 로 행 추가",
            "이메일 확인 발송에 formTrigger의 email 필드 활용",
        ],
        anti_patterns=[
            "폼 데이터를 Set 없이 직접 Sheets에 저장 — 스키마 불일치 위험",
        ],
        data_type_hints=["official_docs", "book"],
    ),
    WorkflowPattern(
        name="file_processing",
        description="Drive 파일 변경 감지 → 내용 추출 → 처리 패턴",
        node_types=["googleDriveTrigger", "extractFromFile", "set", "googleSheets"],
        connections=[("googleDriveTrigger", "extractFromFile"),
                     ("extractFromFile", "set"), ("set", "googleSheets")],
        best_practices=[
            "extractFromFile.operation을 파일 타입에 맞게 설정 (csv/xlsx/pdf)",
            "Set으로 추출 컬럼 선택 후 Sheets 저장",
            "에러 처리: 지원하지 않는 파일 형식 → IF → Stop and Error",
        ],
        anti_patterns=[
            "모든 파일 형식을 동일하게 처리 — PDF와 CSV는 추출 방식이 다름",
        ],
        data_type_hints=["official_docs", "spec"],
    ),
    WorkflowPattern(
        name="github_cicd_notify",
        description="GitHub 이벤트 → 조건 분기 → 팀 알림 패턴",
        node_types=["githubTrigger", "if", "slack", "jira"],
        connections=[("githubTrigger", "if"), ("if", "slack"), ("if", "jira")],
        best_practices=[
            "IF 노드로 push/PR/issue 이벤트 분기",
            "Slack 알림에 GitHub 링크·작성자 포함",
            "PR merge 시 Jira 티켓 자동 Done 처리",
        ],
        anti_patterns=[
            "모든 GitHub 이벤트에 무조건 알림 — 알림 피로 발생",
        ],
        data_type_hints=["official_docs", "book"],
    ),
    WorkflowPattern(
        name="sub_workflow_modular",
        description="메인 워크플로우 → 서브 워크플로우 분리 실행 패턴",
        node_types=["executeWorkflow", "executeWorkflowTrigger", "set"],
        connections=[("set", "executeWorkflow"), ("executeWorkflowTrigger", "set")],
        best_practices=[
            "executeWorkflowTrigger가 있는 워크플로우를 서브 워크플로우로 사용",
            "Set 노드로 입력 데이터를 명시적 스키마로 전달",
            "서브 워크플로우는 단일 책임 원칙 — 하나의 기능만 담당",
        ],
        anti_patterns=[
            "서브 워크플로우 내에서 다시 executeWorkflow 중첩 호출 — 무한 루프 위험",
        ],
        data_type_hints=["official_docs", "book"],
    ),
    WorkflowPattern(
        name="error_monitoring",
        description="에러 트리거 → 에러 정보 포맷 → 팀 알림 패턴",
        node_types=["errorTrigger", "set", "slack"],
        connections=[("errorTrigger", "set"), ("set", "slack")],
        best_practices=[
            "errorTrigger → Set으로 워크플로우명·에러 메시지·실행 ID 추출",
            "Slack 알림에 n8n 실행 URL 포함 (빠른 디버깅)",
            "이메일 알림 병행으로 중요 에러 이중 알림",
        ],
        anti_patterns=[
            "errorTrigger 없이 개별 워크플로우마다 에러 처리 중복 구현",
        ],
        data_type_hints=["troubleshooting", "official_docs"],
    ),
]

# ── 3-D. 학습 선행 의존성 그래프 (LearningGraph) ──────────────────────

LEARNING_NODES: List[LearningNode] = [
    LearningNode(
        concept="n8n_basics",
        node_types=["manualTrigger", "set"],
        prerequisites=[],
        level="beginner",
        est_minutes=45,
    ),
    LearningNode(
        concept="triggers",
        node_types=["scheduleTrigger", "webhook", "manualTrigger"],
        prerequisites=["n8n_basics"],
        level="beginner",
        est_minutes=45,
    ),
    LearningNode(
        concept="data_transformation",
        node_types=["set", "splitOut", "aggregate"],
        prerequisites=["n8n_basics"],
        level="beginner",
        est_minutes=60,
    ),
    LearningNode(
        concept="http_api",
        node_types=["httpRequest"],
        prerequisites=["triggers", "data_transformation"],
        level="intermediate",
        est_minutes=60,
    ),
    LearningNode(
        concept="conditional_logic",
        node_types=["if", "switch"],
        prerequisites=["data_transformation"],
        level="intermediate",
        est_minutes=60,
    ),
    LearningNode(
        concept="error_handling",
        node_types=["httpRequest"],
        prerequisites=["http_api"],
        level="intermediate",
        est_minutes=60,
    ),
    LearningNode(
        concept="batch_processing",
        node_types=["splitInBatches", "merge"],
        prerequisites=["http_api", "conditional_logic"],
        level="advanced",
        est_minutes=90,
    ),
    LearningNode(
        concept="custom_code",
        node_types=["code"],
        prerequisites=["data_transformation", "http_api"],
        level="advanced",
        est_minutes=90,
    ),
    LearningNode(
        concept="webhook_integration",
        node_types=["webhook", "respondToWebhook"],
        prerequisites=["http_api", "conditional_logic"],
        level="advanced",
        est_minutes=90,
    ),
    LearningNode(
        concept="external_services",
        node_types=["slack", "gmail", "googleSheets", "postgres"],
        prerequisites=["http_api", "data_transformation"],
        level="intermediate",
        est_minutes=60,
    ),
    LearningNode(
        concept="messaging_bots",
        node_types=["telegram", "telegramTrigger", "whatsApp", "whatsAppTrigger",
                    "discord", "slack"],
        prerequisites=["conditional_logic", "data_transformation"],
        level="intermediate",
        est_minutes=60,
    ),
    LearningNode(
        concept="file_operations",
        node_types=["googleDrive", "googleDriveTrigger", "extractFromFile",
                    "convertToFile", "readWriteFile", "moveBinaryData"],
        prerequisites=["http_api", "data_transformation"],
        level="intermediate",
        est_minutes=60,
    ),
    LearningNode(
        concept="workflow_automation",
        node_types=["executeWorkflow", "executeWorkflowTrigger", "wait", "errorTrigger"],
        prerequisites=["conditional_logic", "http_api"],
        level="advanced",
        est_minutes=90,
    ),
    LearningNode(
        concept="crm_integration",
        node_types=["hubspot", "jira", "github", "githubTrigger", "pipedrive",
                    "salesforce", "notion"],
        prerequisites=["http_api", "data_transformation", "external_services"],
        level="advanced",
        est_minutes=90,
    ),
    LearningNode(
        concept="data_processing",
        node_types=["filter", "sort", "limit", "summarize", "dateTime",
                    "removeDuplicates", "compareDatasets", "itemLists"],
        prerequisites=["data_transformation"],
        level="intermediate",
        est_minutes=60,
    ),
    LearningNode(
        concept="form_handling",
        node_types=["formTrigger", "form", "respondToWebhook"],
        prerequisites=["triggers", "data_transformation"],
        level="intermediate",
        est_minutes=45,
    ),
    LearningNode(
        concept="ai_integration",
        node_types=["openAi", "code", "extractFromFile", "convertToFile"],
        prerequisites=["http_api", "custom_code"],
        level="advanced",
        est_minutes=90,
    ),
]

# 빠른 조회: concept → LearningNode
_LEARNING_BY_CONCEPT: Dict[str, LearningNode] = {n.concept: n for n in LEARNING_NODES}


# ══════════════════════════════════════════════════════════════════════
# 4. 공개 조회 API
# ══════════════════════════════════════════════════════════════════════

def get_node_def(node_type_or_display: str) -> Optional[N8NNodeDef]:
    """short_type / full_type / display_name 어떤 형태로도 조회."""
    key = node_type_or_display.lower()
    if key in _NODE_BY_SHORT:
        return _NODE_BY_SHORT[key]
    if key in _NODE_BY_FULL:
        return _NODE_BY_FULL[key]
    # full_type의 마지막 세그먼트
    short = key.split(".")[-1]
    if short in _NODE_BY_SHORT:
        return _NODE_BY_SHORT[short]
    return _NODE_BY_DISPLAY.get(key)


def get_relations(node_type: str,
                  relation_filter: Optional[Set[RelationType]] = None) -> List[NodeRelation]:
    """노드의 관계 목록. relation_filter 로 특정 타입만 선택 가능."""
    node = get_node_def(node_type)
    if not node:
        return []
    if relation_filter is None:
        return node.relations
    return [r for r in node.relations if r.relation_type in relation_filter]


def get_related_display_terms(node_type: str,
                               min_weight: float = 0.7) -> List[str]:
    """
    RAG 쿼리 확장용: 관련 노드의 display_name 목록 반환.
    weight >= min_weight 인 관계만 포함.
    """
    terms: List[str] = []
    for rel in get_relations(node_type):
        if rel.weight < min_weight:
            continue
        related = get_node_def(rel.target_type)
        if related:
            terms.append(related.display_name)
            terms.extend(list(related.tags)[:3])
    return list(dict.fromkeys(terms))  # 중복 제거, 순서 유지


def get_constraints_for_node(node_type: str) -> List[PropertyConstraint]:
    """노드 타입의 모든 속성 제약 반환."""
    short = node_type.split(".")[-1]
    return _CONSTRAINTS_BY_NODE.get(short, [])


def get_learning_prerequisites(concept: str) -> List[LearningNode]:
    """특정 개념의 선행 학습 노드 목록 (재귀적으로 전체 선행 체인)."""
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
            _dfs(pre)
        result.append(node)

    node = _LEARNING_BY_CONCEPT.get(concept)
    if node:
        for pre in node.prerequisites:
            _dfs(pre)
    return result


def get_pattern_for_nodes(node_types: List[str]) -> Optional[WorkflowPattern]:
    """
    주어진 노드 집합이 속하는 패턴 반환.
    short_type 또는 full_type 모두 허용.
    """
    shorts = set()
    for t in node_types:
        shorts.add(t.split(".")[-1])

    best_match: Optional[WorkflowPattern] = None
    best_score = 0
    for pattern in WORKFLOW_PATTERNS:
        overlap = len(shorts & set(pattern.node_types))
        if overlap > best_score:
            best_score = overlap
            best_match = pattern
    return best_match if best_score >= 2 else None


def extract_node_short_types(workflow_json: dict) -> List[str]:
    """워크플로우 JSON에서 short_type 목록 추출."""
    types: List[str] = []
    for node in workflow_json.get("nodes", []):
        full = node.get("type", "")
        short = full.split(".")[-1]
        types.append(short)
    return types


