"""
server/semantic_validator.py
──────────────────────────────────────────────────────────────────────
다층 의미론적 검증기 (Multi-stage Semantic Validator)

REG(오타 수정) 이후의 2차·3차 검증 레이어.

검증 단계:
  Stage 1 — 구조 검증 (StructuralValidation)
    · JSON 스키마 준수 여부 (nodes, connections 필드 존재)
    · 연결 참조 무결성 (connections의 node name이 nodes에 존재하는지)
    · 다중 입력 필요 노드(Merge)에 실제로 복수 입력이 있는지

  Stage 2 — 속성 제약 검증 (PropertyConstraintValidation)
    · domain_ontology.PropertyConstraints 규칙 적용
    · retryOnFail → maxTries 필수 여부 등

  Stage 3 — 관계 패턴 검증 (RelationPatternValidation)
    · 감지된 워크플로우 패턴의 best_practices 위반 여부
    · anti_pattern 조합 감지

  Stage 4 — 표현식 의미 검증 (ExpressionSemanticValidation)
    · $item() 폐기 구문 감지
    · 참조 노드명이 워크플로우에 실제 존재하는지
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from domain_ontology import (
    ConstraintType,
    PropertyConstraint,
    ValidationSeverity,
    WorkflowPattern,
    extract_node_short_types,
    get_constraints_for_node,
    get_pattern_for_nodes,
)

log = logging.getLogger("naito.semantic_validator")


# ══════════════════════════════════════════════════════════════════════
# 검증 결과 데이터 클래스
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ValidationIssue:
    stage:       str                 # "structural" | "property" | "pattern" | "expression"
    severity:    ValidationSeverity
    node_name:   Optional[str]
    property:    Optional[str]
    message:     str
    suggestion:  str = ""


@dataclass
class ValidationReport:
    is_valid:   bool
    issues:     List[ValidationIssue] = field(default_factory=list)
    pattern:    Optional[WorkflowPattern] = None
    best_practices: List[str] = field(default_factory=list)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def infos(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.INFO]

    def to_sse_payload(self) -> dict:
        """SSE `validation_report` 이벤트 페이로드."""
        return {
            "is_valid": self.is_valid,
            "error_count":   len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [
                {
                    "stage":    i.stage,
                    "severity": i.severity.value,
                    "node":     i.node_name,
                    "property": i.property,
                    "message":  i.message,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
            "pattern":        self.pattern.name if self.pattern else None,
            "best_practices": self.best_practices,
        }


# ══════════════════════════════════════════════════════════════════════
# 표현식 감지 패턴
# ══════════════════════════════════════════════════════════════════════

_EXPR_ITEM_RE   = re.compile(r"\$item\(")              # 폐기된 $item()
_EXPR_NODE_REF  = re.compile(r'\$node\["([^"]+)"\]')   # $node["NodeName"]
_EXPR_ANY_RE    = re.compile(r'\{\{[^}]+\}\}')


# ══════════════════════════════════════════════════════════════════════
# SemanticValidator
# ══════════════════════════════════════════════════════════════════════

class SemanticValidator:
    """
    생성된 n8n 워크플로우 JSON 및 응답 텍스트에 대한 다층 의미 검증.

    사용 예:
        validator = SemanticValidator()
        report = validator.validate(workflow_json_str, response_text)
        if report.issues:
            yield sse("validation_report", report.to_sse_payload())
    """

    def validate(
        self,
        workflow_json_str: Optional[str],
        response_text:     str = "",
    ) -> ValidationReport:
        """
        전체 검증 파이프라인 실행.

        Args:
            workflow_json_str: LLM이 생성한 워크플로우 JSON 문자열 (없을 수 있음)
            response_text:     LLM 전체 응답 텍스트 (표현식 스캔용)
        """
        issues: List[ValidationIssue] = []
        workflow: Optional[dict] = None
        node_names: List[str] = []
        short_types: List[str] = []

        # ── 워크플로우 JSON 파싱 ────────────────────────────────────────
        if workflow_json_str:
            workflow = self._extract_workflow_json(workflow_json_str)
            if workflow:
                node_names  = [n.get("name", "") for n in workflow.get("nodes", [])]
                short_types = extract_node_short_types(workflow)

                # Stage 1: 구조 검증
                issues.extend(self._stage1_structural(workflow, node_names))

                # Stage 2: 속성 제약 검증
                issues.extend(self._stage2_property_constraints(workflow))

                # Stage 3: 관계 패턴 검증
                issues.extend(self._stage3_relation_pattern(workflow, short_types))

        # Stage 4: 표현식 의미 검증 (텍스트 레벨)
        issues.extend(self._stage4_expression_semantics(response_text, node_names))

        # 패턴 감지
        pattern = get_pattern_for_nodes(short_types) if short_types else None

        best_practices: List[str] = []
        if pattern:
            best_practices = pattern.best_practices

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)

        log.info(
            "[SemanticValidator] 검증 완료: errors=%d, warnings=%d, infos=%d",
            len([i for i in issues if i.severity == ValidationSeverity.ERROR]),
            len([i for i in issues if i.severity == ValidationSeverity.WARNING]),
            len([i for i in issues if i.severity == ValidationSeverity.INFO]),
        )

        return ValidationReport(
            is_valid=is_valid,
            issues=issues,
            pattern=pattern,
            best_practices=best_practices,
        )

    # ── Stage 1: 구조 검증 ─────────────────────────────────────────────

    def _stage1_structural(
        self,
        workflow:   dict,
        node_names: List[str],
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # 1-A: 필수 최상위 필드 확인
        if "nodes" not in workflow:
            issues.append(ValidationIssue(
                stage="structural", severity=ValidationSeverity.ERROR,
                node_name=None, property="nodes",
                message="워크플로우에 `nodes` 배열이 없습니다.",
                suggestion='"nodes": [] 필드를 추가하세요.',
            ))
        if "connections" not in workflow:
            issues.append(ValidationIssue(
                stage="structural", severity=ValidationSeverity.ERROR,
                node_name=None, property="connections",
                message="워크플로우에 `connections` 객체가 없습니다.",
                suggestion='"connections": {} 필드를 추가하세요.',
            ))

        nodes = workflow.get("nodes", [])
        connections = workflow.get("connections", {})

        # 1-B: connections 참조 무결성
        name_set = set(node_names)
        for src, conn_data in connections.items():
            if src not in name_set:
                issues.append(ValidationIssue(
                    stage="structural", severity=ValidationSeverity.ERROR,
                    node_name=src, property="connections",
                    message=f"연결 소스 노드 '{src}'가 nodes 배열에 없습니다.",
                    suggestion=f"nodes 배열에 '{src}' 노드를 추가하거나 connections에서 제거하세요.",
                ))
            if isinstance(conn_data, dict):
                for port, targets_list in conn_data.items():
                    for targets in targets_list:
                        if not isinstance(targets, list):
                            continue
                        for tgt in targets:
                            tgt_name = tgt.get("node", "") if isinstance(tgt, dict) else ""
                            if tgt_name and tgt_name not in name_set:
                                issues.append(ValidationIssue(
                                    stage="structural", severity=ValidationSeverity.ERROR,
                                    node_name=tgt_name, property="connections",
                                    message=f"연결 대상 노드 '{tgt_name}'가 nodes 배열에 없습니다.",
                                    suggestion=f"nodes에 '{tgt_name}'을 추가하거나 연결을 수정하세요.",
                                ))

        # 1-C: 각 노드 필수 필드
        for node in nodes:
            nname = node.get("name", "(unnamed)")
            if not node.get("type"):
                issues.append(ValidationIssue(
                    stage="structural", severity=ValidationSeverity.ERROR,
                    node_name=nname, property="type",
                    message=f"노드 '{nname}'에 `type` 필드가 없습니다.",
                    suggestion="예: \"type\": \"n8n-nodes-base.httpRequest\"",
                ))
            if node.get("position") is None:
                issues.append(ValidationIssue(
                    stage="structural", severity=ValidationSeverity.INFO,
                    node_name=nname, property="position",
                    message=f"노드 '{nname}'에 `position`이 없습니다 (캔버스 렌더링에 필요).",
                    suggestion="예: \"position\": [250, 300]",
                ))

        return issues

    # ── Stage 2: 속성 제약 검증 ─────────────────────────────────────────

    def _stage2_property_constraints(self, workflow: dict) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        for node in workflow.get("nodes", []):
            nname  = node.get("name", "(unnamed)")
            ntype  = node.get("type", "")
            short  = ntype.split(".")[-1]
            params = node.get("parameters", {})

            constraints = get_constraints_for_node(short)
            for c in constraints:
                pval = params.get(c.property_name)

                if c.constraint_type == ConstraintType.REQUIRES:
                    if pval and c.related_property and not params.get(c.related_property):
                        issues.append(ValidationIssue(
                            stage="property",
                            severity=c.severity,
                            node_name=nname,
                            property=c.property_name,
                            message=c.message,
                            suggestion=f"`{c.related_property}`를 parameters에 추가하세요.",
                        ))

                elif c.constraint_type == ConstraintType.CONDITIONAL:
                    if str(pval) == str(c.trigger_value) and c.related_property:
                        if not params.get(c.related_property):
                            issues.append(ValidationIssue(
                                stage="property",
                                severity=c.severity,
                                node_name=nname,
                                property=c.property_name,
                                message=c.message,
                                suggestion=f"`{c.related_property}`를 설정하세요.",
                            ))

                elif c.constraint_type == ConstraintType.RECOMMENDED:
                    if pval and c.related_property and not params.get(c.related_property):
                        issues.append(ValidationIssue(
                            stage="property",
                            severity=ValidationSeverity.INFO,
                            node_name=nname,
                            property=c.property_name,
                            message=c.message,
                            suggestion=f"`{c.related_property}` 설정을 고려하세요.",
                        ))

                elif c.constraint_type == ConstraintType.FORBIDDEN:
                    if c.trigger_value and isinstance(pval, str) and c.trigger_value in pval:
                        issues.append(ValidationIssue(
                            stage="property",
                            severity=c.severity,
                            node_name=nname,
                            property=c.property_name,
                            message=c.message,
                            suggestion="n8n 전용 노드를 사용하거나 폐기된 구문을 제거하세요.",
                        ))

        return issues

    # ── Stage 3: 관계·패턴 검증 ─────────────────────────────────────────

    def _stage3_relation_pattern(
        self,
        workflow:    dict,
        short_types: List[str],
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        nodes = workflow.get("nodes", [])
        connections = workflow.get("connections", {})
        name_set = {n.get("name", "") for n in nodes}

        # 3-A: Merge 노드 다중 입력 확인
        for node in nodes:
            if "merge" in node.get("type", "").lower():
                nname = node.get("name", "Merge")
                incoming = sum(
                    1 for src_data in connections.values()
                    if isinstance(src_data, dict)
                    for targets_list in src_data.values()
                    for targets in targets_list
                    if isinstance(targets, list)
                    for tgt in targets
                    if isinstance(tgt, dict) and tgt.get("node") == nname
                )
                if incoming < 2:
                    issues.append(ValidationIssue(
                        stage="pattern",
                        severity=ValidationSeverity.ERROR,
                        node_name=nname,
                        property=None,
                        message=f"Merge 노드 '{nname}'의 입력 연결이 {incoming}개입니다. 최소 2개 필요합니다.",
                        suggestion="두 개 이상의 노드에서 Merge 노드로 연결을 추가하세요.",
                    ))

        # 3-B: Webhook + Respond to Webhook 패턴 검증
        has_webhook = any("webhook" in t for t in short_types if t != "respondToWebhook")
        has_respond = "respondToWebhook" in short_types
        if has_webhook and not has_respond:
            # responseMode 확인
            for node in nodes:
                if "webhook" in node.get("type", "").lower() and "respondToWebhook" not in node.get("type", ""):
                    rm = node.get("parameters", {}).get("responseMode", "")
                    if rm == "responseNode":
                        issues.append(ValidationIssue(
                            stage="pattern",
                            severity=ValidationSeverity.WARNING,
                            node_name=node.get("name", "Webhook"),
                            property="responseMode",
                            message="`responseMode: responseNode` 설정이지만 `Respond to Webhook` 노드가 없습니다.",
                            suggestion="`Respond to Webhook` 노드를 워크플로우 끝에 추가하세요.",
                        ))

        # 3-C: Code 노드 내 HTTP 직접 호출 감지 (anti-pattern)
        for node in nodes:
            if "code" in node.get("type", "").lower():
                code_content = (
                    node.get("parameters", {}).get("jsCode", "")
                    or node.get("parameters", {}).get("pythonCode", "")
                )
                if "fetch(" in str(code_content) or "axios" in str(code_content):
                    issues.append(ValidationIssue(
                        stage="pattern",
                        severity=ValidationSeverity.WARNING,
                        node_name=node.get("name", "Code"),
                        property="jsCode",
                        message="Code 노드 내 HTTP 직접 호출이 감지되었습니다 (Anti-pattern).",
                        suggestion="별도의 `HTTP Request` 노드를 사용하면 n8n의 에러 처리/재시도 기능을 활용할 수 있습니다.",
                    ))

        return issues

    # ── Stage 4: 표현식 의미 검증 ───────────────────────────────────────

    def _stage4_expression_semantics(
        self,
        text:       str,
        node_names: List[str],
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # 4-A: $item() 폐기 구문
        for m in _EXPR_ITEM_RE.finditer(text):
            issues.append(ValidationIssue(
                stage="expression",
                severity=ValidationSeverity.ERROR,
                node_name=None,
                property="expression",
                message="`$item()` 은 n8n v1.x에서 완전히 폐기되었습니다.",
                suggestion="`$json.fieldName` 형식을 사용하세요.",
            ))

        # 4-B: $node["NodeName"] 참조 무결성
        if node_names:
            name_set = set(node_names)
            for m in _EXPR_NODE_REF.finditer(text):
                ref_name = m.group(1)
                if ref_name not in name_set:
                    issues.append(ValidationIssue(
                        stage="expression",
                        severity=ValidationSeverity.WARNING,
                        node_name=ref_name,
                        property="expression",
                        message=f"`$node[\"{ref_name}\"]` 참조 — 워크플로우에 '{ref_name}' 노드가 없습니다.",
                        suggestion=f"노드명을 확인하거나 '{ref_name}' 노드를 워크플로우에 추가하세요.",
                    ))

        return issues

    # ── 내부 유틸 ───────────────────────────────────────────────────────

    @staticmethod
    def _extract_workflow_json(text: str) -> Optional[dict]:
        """텍스트에서 첫 번째 유효한 n8n 워크플로우 JSON 추출."""
        # ```json 블록 우선
        fenced = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        candidates = fenced + [text]
        for candidate in candidates:
            c = candidate.strip()
            if not c.startswith("{"):
                # 중괄호 시작점 탐색
                idx = c.find("{")
                if idx < 0:
                    continue
                c = c[idx:]
            try:
                obj = json.loads(c)
                if "nodes" in obj or "connections" in obj:
                    return obj
            except (json.JSONDecodeError, ValueError):
                continue
        return None


# ── 싱글턴 ────────────────────────────────────────────────────────────

_validator: Optional[SemanticValidator] = None

def get_semantic_validator() -> SemanticValidator:
    global _validator
    if _validator is None:
        _validator = SemanticValidator()
    return _validator
