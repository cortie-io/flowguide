"""
server/ontology_enhancer.py
──────────────────────────────────────────────────────────────────────
온톨로지 기반 RAG 쿼리 확장기 (OntologyEnhancer)

domain_ontology의 관계 그래프를 활용하여 RAG 검색 쿼리를 확장한다.

역할:
  1. 쿼리에서 언급된 노드를 감지 (N8N entity recognition)
     - 정확 매칭 (full_type / camelCase / display_name / 한국어 키워드)
     - 퍼지 매칭 (한국어 자모 Levenshtein / 영어 문자 Levenshtein)
  2. RelationGraph에서 관련 노드·개념을 탐색
  3. 관련 용어를 쿼리에 추가 → BM25/벡터 recall 향상
  4. Intent별 최적 RAG 필터 전략 결정
  5. 검색 결과에 온톨로지 관련성 점수 부여 (Ontology Reranking)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field as dc_field
from typing import Dict, List, Optional, Set, Tuple

from domain_ontology import (
    N8NNodeDef,
    RelationType,
    WorkflowPattern,
    _ALL_NODE_DEFS,
    get_node_def,
    get_pattern_for_nodes,
    get_related_display_terms,
    get_relations,
)

log = logging.getLogger("naito.ontology_enhancer")


# ══════════════════════════════════════════════════════════════════════
# 1. 한국어 자모 분해 + Levenshtein 퍼지 매칭
# ══════════════════════════════════════════════════════════════════════

_JAMO_ONSET = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
_JAMO_VOWEL = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
_JAMO_CODA  = " ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"

# 어미·조사: 길이 내림차순 정렬 (긴 것 먼저 제거해야 오탈자 방지)
_KO_PARTICLES = sorted([
    "에서", "으로", "이란", "이라", "이야", "이가", "이란", "이라면",
    "로", "은", "는", "이", "가", "을", "를", "의", "에", "도", "만", "야",
    "란", "이야", "뭐야", "뭔", "이야기", "관련",
], key=len, reverse=True)


def _decompose_jamo(text: str) -> str:
    """완성형 한글을 자모 단위로 분해. 비한글 문자는 그대로."""
    result = []
    for ch in text:
        code = ord(ch) - 0xAC00
        if 0 <= code <= 11171:
            onset = code // 588
            vowel = (code % 588) // 28
            coda  = code % 28
            result.append(_JAMO_ONSET[onset])
            result.append(_JAMO_VOWEL[vowel])
            if coda:
                result.append(_JAMO_CODA[coda])
        else:
            result.append(ch)
    return "".join(result)


def _levenshtein(a: str, b: str) -> int:
    """편집 거리 (삽입·삭제·교체). 조기 종료 최적화 포함."""
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for c1 in a:
        curr = [prev[0] + 1]
        for j, c2 in enumerate(b):
            curr.append(min(prev[j] + (c1 != c2), curr[-1] + 1, prev[j + 1] + 1))
        prev = curr
    return prev[-1]


def _fuzzy_threshold(length: int) -> int:
    """자모 분해 후 길이 기반 허용 편집 거리."""
    if length <= 4:
        return 0   # 너무 짧으면 오탐 위험 → 정확 매칭만
    if length <= 9:
        return 1
    return 2


# 짧은 사전 키(예: "메일", 5자모)는 threshold=1에서 무관한 실제 단어와도
# 편집거리 1 안에 들어와 오탐을 낸다. 실사용 중 발견된 구체적 충돌 사례를
# 화이트리스트 방식이 아닌 블록리스트로 관리한다 — 전체 임계값을 올리면
# "노션"/"수식" 같은 다른 5자모 키의 정상 오타 교정까지 막히기 때문이다.
# 실제 발견 사례: "매일"(every day) → 자모 편집거리 1로 "메일"(mail, emailSend)에
# 오매칭되어, "매일 아침 스케줄" 류의 질의에서 엉뚱한 Send Email 노드가 감지됨.
_KO_FUZZY_STOPWORDS = frozenset({"매일"})


def _strip_ko_particle(word: str) -> str:
    """단어 끝 조사/어미 제거 (최장 우선)."""
    for p in _KO_PARTICLES:
        if word.endswith(p) and len(word) > len(p) + 1:
            return word[: -len(p)]
    return word


# ══════════════════════════════════════════════════════════════════════
# 2. 동적 어휘 테이블 (온톨로지 전체 453개에서 자동 구축)
# ══════════════════════════════════════════════════════════════════════

# display_name.lower() → short_type  (453개 전체)
_DISPLAY_TO_SHORT: Dict[str, str] = {}
# tag → short_type  (길이 4 이상 태그만)
_TAG_TO_SHORT: Dict[str, str] = {}
# short_type.lower() 집합
_ALL_SHORT_LOWER: Set[str] = set()

for _node in _ALL_NODE_DEFS:
    _dn = _node.display_name.lower()
    _DISPLAY_TO_SHORT[_dn] = _node.short_type
    _ALL_SHORT_LOWER.add(_node.short_type.lower())
    for _t in _node.tags:
        if len(_t) >= 4:
            _TAG_TO_SHORT.setdefault(_t.lower(), _node.short_type)

# 퍼지 매칭용: 자모 분해된 display_name 캐시 (런타임 반복 계산 방지)
_DISPLAY_JAMO_CACHE: Dict[str, str] = {
    k: _decompose_jamo(k) for k in _DISPLAY_TO_SHORT
}

# n8n full_type 패턴
_FULL_TYPE_RE = re.compile(r"n8n-nodes-base\.([a-zA-Z][a-zA-Z0-9]*)", re.IGNORECASE)

# short_type 직접 regex (전체 453개 중 길이 4+ 만)
_short_type_patterns = sorted(
    [n.short_type for n in _ALL_NODE_DEFS if len(n.short_type) >= 4],
    key=len, reverse=True,
)
_SHORT_TYPE_RE = re.compile(
    r"\b(" + "|".join(re.escape(s) for s in _short_type_patterns) + r")\b",
    re.IGNORECASE,
)


# ══════════════════════════════════════════════════════════════════════
# 3. 한국어 키워드 사전 (수동 매핑 — 퍼지 매칭의 앵커 역할)
# ══════════════════════════════════════════════════════════════════════

_KO_TO_SHORT: Dict[str, str] = {
    # 트리거
    "웹훅":          "webhook",
    "스케줄":        "scheduleTrigger",
    "정기":          "scheduleTrigger",
    "크론":          "scheduleTrigger",
    "폼 트리거":     "formTrigger",
    "폼트리거":      "formTrigger",
    "텔레그램 트리거": "telegramTrigger",
    "지메일 트리거":  "gmailTrigger",
    "깃헙 트리거":    "githubTrigger",
    "구글 드라이브 트리거": "googleDriveTrigger",
    "에러 트리거":   "errorTrigger",
    "오류 트리거":   "errorTrigger",
    "인터벌":        "interval",
    # 처리
    "http 요청":     "httpRequest",
    "api 호출":      "httpRequest",
    "api호출":       "httpRequest",
    "http":          "httpRequest",
    "세트":          "set",
    "필드 설정":     "set",
    "조건":          "if",
    "분기":          "if",
    "스위치":        "switch",
    "코드":          "code",
    "코드 노드":     "code",
    "자바스크립트":  "code",
    "파이썬":        "code",
    "배치":          "splitInBatches",
    "배치 분할":     "splitInBatches",
    "분리":          "splitOut",
    "병합":          "merge",
    "합치기":        "merge",
    "집계":          "aggregate",
    "필터":          "filter",
    "아이템 리스트": "itemLists",
    "요약":          "summarize",
    "비교":          "compareDatasets",
    "서브워크플로우": "executeWorkflow",
    "파일 추출":     "extractFromFile",
    "파일 변환":     "convertToFile",
    "파일 읽기":     "readWriteFile",
    "파일 쓰기":     "readWriteFile",
    "이미지 편집":   "editImage",
    "rss":           "rssFeedRead",
    "pdf":           "readPDF",
    "pdf 읽기":      "readPDF",
    "html 추출":     "htmlExtract",
    "ssh":           "ssh",
    "명령어":        "executeCommand",
    "압축":          "compression",
    "오픈ai":        "openAi",
    "챗gpt":         "openAi",
    "gpt":           "openAi",
    "ai":            "openAi",
    # 메신저·알림
    "슬랙":          "slack",
    "디스코드":      "discord",
    "텔레그램":      "telegram",
    "왓츠앱":        "whatsApp",
    "카카오":        "telegram",   # kakao 노드 없음 → telegram 최근사
    "이메일":        "emailSend",
    "메일":          "emailSend",
    "지메일":        "gmail",
    "아웃룩":        "microsoftOutlook",
    "팀즈":          "microsoftTeams",
    "매터모스트":    "mattermost",
    "트윌리오":      "twilio",
    "sms":           "twilio",
    # 데이터베이스
    "구글 시트":     "googleSheets",
    "스프레드시트":  "googleSheets",
    "시트":          "googleSheets",
    "포스트그레스":  "postgres",
    "포스트그레스ql": "postgres",
    "수파베이스":    "supabase",
    "마이에스큐엘":  "mySql",
    "mysql":         "mySql",
    "레디스":        "redis",
    "에어테이블":    "airtable",
    "노션":          "notion",
    "스노우플레이크": "snowflake",
    "몽고디비":      "mongoDb",
    "mongodb":       "mongoDb",
    # 파일·스토리지
    "구글 드라이브": "googleDrive",
    "드라이브":      "googleDrive",
    "드롭박스":      "dropbox",
    "원드라이브":    "microsoftOneDrive",
    "넥스트클라우드": "nextCloud",
    "s3":            "awsS3",
    "에스쓰리":      "awsS3",
    "ftp":           "ftp",
    # 프로젝트 관리
    "지라":          "jira",
    "깃헙":          "github",
    "깃허브":        "github",
    "깃랩":          "gitLab",
    "깃":            "git",
    "리니어":        "linear",
    "아사나":        "asana",
    "트렐로":        "trello",
    "클릭업":        "clickUp",
    "투두이스트":    "todoist",
    "먼데이":        "mondayCom",
    # CRM·마케팅
    "허브스팟":      "hubspot",
    "세일즈포스":    "salesforce",
    "파이프드라이브": "pipedrive",
    "젠데스크":      "zendesk",
    "메일침프":      "mailchimp",
    "센드그리드":    "sendGrid",
    # 소셜·콘텐츠
    "트위터":        "twitter",
    "링크드인":      "linkedIn",
    "레딧":          "reddit",
    "유튜브":        "youTube",
    "스포티파이":    "spotify",
    "워드프레스":    "wordpress",
    # 결제·커머스
    "쇼피파이":      "shopify",
    "스트라이프":    "stripe",
    "줌":            "zoom",
    "캘린더":        "googleCalendar",
    "구글 캘린더":   "googleCalendar",
    # 유틸리티
    "대기":          "wait",
    "딜레이":        "wait",
    "정렬":          "sort",
    "날짜":          "dateTime",
    "시간":          "dateTime",
    "중복 제거":     "removeDuplicates",
    "웹훅 응답":     "respondToWebhook",
    "중지":          "stopAndError",
    "에러 중지":     "stopAndError",
    "카프카":        "kafka",
    "래빗엠큐":      "rabbitmq",
    "mqtt":          "mqtt",
    "페이저듀티":    "pagerDuty",
}

# 퍼지 매칭용: 자모 분해된 KO 키 캐시
_KO_JAMO_CACHE: Dict[str, str] = {
    k: _decompose_jamo(k) for k in _KO_TO_SHORT
}


# ══════════════════════════════════════════════════════════════════════
# 4. OntologyEnhancer
# ══════════════════════════════════════════════════════════════════════

class OntologyEnhancer:
    """
    온톨로지 기반 RAG 쿼리 강화기.

    노드 감지 우선순위:
      Step 1 — n8n-nodes-base.xxx 패턴 (정확)
      Step 2 — camelCase short_type regex (정확)
      Step 3 — display_name / tag 영어 정확 매칭 (453개 전체)
      Step 4 — 한국어 키워드 정확 매칭
      Step 5 — 한국어 퍼지 매칭 (자모 Levenshtein, 조사 제거 포함)
      Step 6 — 영어 퍼지 매칭 (문자 Levenshtein)
    """

    def enhance(
        self, query: str, intent: str = "GENERAL", expansion_hint: str = ""
    ) -> "EnhancedQuery":
        """쿼리를 온톨로지 기반으로 확장한다.

        expansion_hint: IntentRouter의 LLM 분류 호출에서 함께 받아온 사전 맥락
        확장 힌트(예: "Schedule Trigger, HTTP Request, Slack"). 사용자가 노드명을
        직접 언급하지 않고 목적만 서술한 질의에서, 원본 쿼리 텍스트만으로는
        놓칠 노드를 추가로 감지하기 위한 보조 신호다(HyDE, Gao et al. 2022의
        가상 문서 확장을 노드 탐지에 응용). 힌트에 실재하지 않는 노드가
        섞여 있어도 get_node_def() 조회에서 자연히 걸러지므로 무해하다.
        """
        detected_nodes, typo_corrections = self._detect_nodes(query)

        expansion_detected: List[N8NNodeDef] = []
        if expansion_hint:
            hint_nodes, _hint_corrections = self._detect_nodes(expansion_hint)
            existing_shorts = {n.short_type for n in detected_nodes}
            expansion_detected = [n for n in hint_nodes if n.short_type not in existing_shorts]
            if expansion_detected:
                detected_nodes = detected_nodes + expansion_detected
                log.info(
                    "[OntologyEnhancer] 사전 확장 힌트로 추가 감지: %s "
                    "(원본 쿼리엔 미언급, 힌트=%r)",
                    [n.short_type for n in expansion_detected], expansion_hint,
                )

        related_terms  = self._expand_related_terms(detected_nodes)
        filter_types   = self._decide_filter_strategy(intent, detected_nodes)
        pattern        = self._detect_pattern(detected_nodes)
        ontology_hints = self._build_ontology_hints(detected_nodes, pattern)

        extra    = " ".join(t for t in related_terms if t.lower() not in query.lower())
        expanded = f"{query} {extra}".strip() if extra else query

        if detected_nodes:
            log.debug(
                "[OntologyEnhancer] 감지=%s 퍼지포함 → 확장 용어=%d개 교정=%s",
                [n.short_type for n in detected_nodes], len(related_terms), typo_corrections,
            )

        return EnhancedQuery(
            original_query=query,
            expanded_query=expanded,
            detected_nodes=detected_nodes,
            related_node_terms=related_terms,
            filter_types=filter_types,
            pattern=pattern,
            ontology_hints=ontology_hints,
            typo_corrections=typo_corrections,
            expansion_detected_nodes=expansion_detected,
        )

    def rerank_chunks(
        self,
        chunks: List[dict],
        detected_nodes: List[N8NNodeDef],
        boost: float = 0.15,
    ) -> List[dict]:
        if not detected_nodes:
            return chunks

        related_short: Set[str] = set()
        related_display: Set[str] = set()
        for node in detected_nodes:
            related_short.add(node.short_type)
            related_display.add(node.display_name.lower())
            for rel in node.relations:
                related_short.add(rel.target_type)
                related = get_node_def(rel.target_type)
                if related:
                    related_display.add(related.display_name.lower())

        def _score(chunk: dict, base_rank: int) -> float:
            score = 1.0 / (base_rank + 1)
            haystack = " ".join([
                str(chunk.get("title", "")),
                str(chunk.get("node_name", "")),
                str(chunk.get("text", ""))[:500],
            ]).lower()
            for short in related_short:
                if short.lower() in haystack:
                    score += boost
            for display in related_display:
                if display in haystack:
                    score += boost * 0.5
            return score

        scored = [(_score(c, i), i, c) for i, c in enumerate(chunks)]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, _, c in scored]

    # ── 내부 ─────────────────────────────────────────────────────────

    def _detect_nodes(
        self, query: str
    ) -> Tuple[List[N8NNodeDef], List[Tuple[str, str]]]:
        """노드 감지 + 오타 교정 목록 반환.
        Returns: (detected_nodes, typo_corrections)
          typo_corrections — [(user_typed, canonical_display_name), ...]
        """
        found: Dict[str, N8NNodeDef] = {}
        corrections: List[Tuple[str, str]] = []
        q_lower = query.lower()

        # Step 1: full_type 패턴
        for m in _FULL_TYPE_RE.finditer(query):
            node = get_node_def(m.group(1))
            if node:
                found[node.short_type] = node

        # Step 2: camelCase short_type regex (전체 453개)
        for m in _SHORT_TYPE_RE.finditer(query):
            node = get_node_def(m.group(1))
            if node and node.short_type not in found:
                found[node.short_type] = node

        # Step 3: 영어 display_name / tag 정확 매칭 (최장 우선)
        for key in sorted(_DISPLAY_TO_SHORT, key=len, reverse=True):
            if key in q_lower:
                node = get_node_def(_DISPLAY_TO_SHORT[key])
                if node and node.short_type not in found:
                    found[node.short_type] = node

        # Step 4: 한국어 키워드 정확 매칭 (최장 우선)
        # 단어 단위로만 매칭 — 짧은 키(≤2자)가 다른 단어의 서브스트링이 되는 문제 방지
        ko_words = set(re.split(r"[\s,\.!?]+", query))
        for ko in sorted(_KO_TO_SHORT, key=len, reverse=True):
            # 짧은 키는 단어 경계 체크, 긴 키는 서브스트링 허용
            if len(ko) <= 2:
                matched = ko in ko_words
            else:
                matched = ko in query
            if matched:
                node = get_node_def(_KO_TO_SHORT[ko])
                if node and node.short_type not in found:
                    found[node.short_type] = node

        # Step 5: 한국어 퍼지 매칭 (Step 1~4 에서 아무것도 못 잡았을 때 또는 보완)
        if len(found) == 0 or self._has_ko(query):
            for short, raw_token, dist in self._fuzzy_ko(query):
                if short not in found:
                    node = get_node_def(short)
                    if node:
                        found[node.short_type] = node
                        if dist > 0:  # 진짜 오타 교정이 일어난 경우만
                            corrections.append((raw_token, node.display_name))

        # Step 6: 영어 퍼지 매칭 (Step 1~4 에서 못 잡은 경우에만)
        if len(found) == 0:
            for short, raw_word, dist in self._fuzzy_en(query):
                if short not in found:
                    node = get_node_def(short)
                    if node:
                        found[node.short_type] = node
                        if dist > 0:
                            corrections.append((raw_word, node.display_name))

        return list(found.values()), corrections

    # ── 퍼지 매칭 ────────────────────────────────────────────────────

    @staticmethod
    def _has_ko(text: str) -> bool:
        """한글 포함 여부."""
        return any(0xAC00 <= ord(c) <= 0xD7A3 or 0x3130 <= ord(c) <= 0x318F
                   for c in text)

    @staticmethod
    def _tokenize_ko(text: str) -> List[str]:
        """쿼리를 공백 기준 분리 후 unigram + bigram 후보 생성."""
        words = [w.strip() for w in re.split(r"[\s,\.!?]+", text) if w.strip()]
        candidates = list(words)
        for i in range(len(words) - 1):
            candidates.append(words[i] + " " + words[i + 1])
        return candidates

    def _fuzzy_ko(self, query: str) -> List[Tuple[str, str, int]]:
        """한국어 퍼지 매칭. 자모 분해 + 조사 제거 + Levenshtein.
        Returns: [(short_type, raw_token_stripped, jamo_edit_dist), ...]
        """
        results: List[Tuple[str, str, int]] = []
        seen_shorts: Set[str] = set()
        candidates = self._tokenize_ko(query)

        for cand in candidates:
            stripped = _strip_ko_particle(cand)
            for token in dict.fromkeys([cand, stripped]):
                if token in _KO_FUZZY_STOPWORDS:
                    continue
                token_jamo = _decompose_jamo(token)
                thresh = _fuzzy_threshold(len(token_jamo))
                if thresh == 0:
                    continue

                best_dist = thresh + 1
                best_short: Optional[str] = None

                for ko_key, short in _KO_TO_SHORT.items():
                    key_jamo = _KO_JAMO_CACHE[ko_key]
                    if abs(len(token_jamo) - len(key_jamo)) > thresh + 1:
                        continue
                    dist = _levenshtein(token_jamo, key_jamo)
                    if dist < best_dist:
                        best_dist = dist
                        best_short = short

                if best_short and best_short not in seen_shorts:
                    seen_shorts.add(best_short)
                    log.debug("[FuzzyKO] '%s' → '%s' (jamo_dist=%d)", token, best_short, best_dist)
                    results.append((best_short, stripped, best_dist))

        return results

    def _fuzzy_en(self, query: str) -> List[Tuple[str, str, int]]:
        """영어 퍼지 매칭. 단어 토큰 × display_name 문자 Levenshtein.
        Returns: [(short_type, original_word, char_edit_dist), ...]
        """
        results: List[Tuple[str, str, int]] = []
        seen_shorts: Set[str] = set()
        words = re.findall(r"[a-zA-Z]{3,}", query)
        if not words:
            return results

        for word in words:
            w_lower = word.lower()
            thresh = _fuzzy_threshold(len(w_lower) + 2)
            if thresh == 0:
                continue

            best_dist = thresh + 1
            best_short: Optional[str] = None

            for dn, short in _DISPLAY_TO_SHORT.items():
                if " " in dn:
                    continue
                if abs(len(w_lower) - len(dn)) > thresh + 1:
                    continue
                dist = _levenshtein(w_lower, dn)
                if dist < best_dist:
                    best_dist = dist
                    best_short = short

            if best_short and best_short not in seen_shorts:
                seen_shorts.add(best_short)
                log.debug("[FuzzyEN] '%s' → '%s' (dist=%d)", word, best_short, best_dist)
                results.append((best_short, word, best_dist))

        return results

    # ── 기존 메서드 ───────────────────────────────────────────────────

    def _expand_related_terms(self, nodes: List[N8NNodeDef]) -> List[str]:
        terms: List[str] = []
        for node in nodes:
            terms.extend(node.tags)
            terms.extend(get_related_display_terms(node.short_type, min_weight=0.75))
        return list(dict.fromkeys(terms))

    def _decide_filter_strategy(
        self, intent: str, nodes: List[N8NNodeDef],
    ) -> Optional[Set[str]]:
        base: Dict[str, Optional[Set[str]]] = {
            "CURRICULUM":     None,
            "EXPRESSION":     {"spec", "cli_spec", "official_docs"},
            "WORKFLOW_BUILD": None,
            "ERROR_PATCH":    {"troubleshooting", "api_limits", "spec"},
            "REVERSE":        {"spec", "official_docs"},
            "GENERAL":        None,
        }
        filters = base.get(intent)
        if nodes and intent == "GENERAL":
            filters = {"spec", "official_docs"}
        return filters

    def _detect_pattern(self, nodes: List[N8NNodeDef]) -> Optional[WorkflowPattern]:
        if not nodes:
            return None
        return get_pattern_for_nodes([n.short_type for n in nodes])

    def _build_ontology_hints(
        self,
        nodes: List[N8NNodeDef],
        pattern: Optional[WorkflowPattern],
    ) -> List[str]:
        hints: List[str] = []
        for node in nodes:
            for rel in node.relations:
                if rel.relation_type == RelationType.ANTI_PATTERN_WITH:
                    hints.append(f"[ANTI-PATTERN] {rel.description}")
                elif rel.relation_type == RelationType.COMPLEMENTED_BY:
                    hints.append(f"[RECOMMEND] {rel.description}")
                elif rel.relation_type == RelationType.REQUIRES_MULTIPLE_IN:
                    hints.append(f"[CONSTRAINT] {rel.description}")
        if pattern:
            hints.append(f"[PATTERN] '{pattern.name}': {pattern.description}")
            hints.extend(f"[BEST-PRACTICE] {bp}" for bp in pattern.best_practices[:3])
            hints.extend(f"[ANTI-PATTERN] {ap}" for ap in pattern.anti_patterns[:2])
        return hints


# ══════════════════════════════════════════════════════════════════════
# 5. 결과 데이터 클래스
# ══════════════════════════════════════════════════════════════════════

@dataclass
class EnhancedQuery:
    original_query:     str
    expanded_query:     str
    detected_nodes:     List[N8NNodeDef]          = dc_field(default_factory=list)
    related_node_terms: List[str]                 = dc_field(default_factory=list)
    filter_types:       Optional[Set[str]]        = None
    pattern:            Optional[WorkflowPattern] = None
    ontology_hints:     List[str]                 = dc_field(default_factory=list)
    # 퍼지 매칭으로 오타가 교정된 경우: [(user_typed, canonical_display_name), ...]
    typo_corrections:   List[Tuple[str, str]]     = dc_field(default_factory=list)
    # 원본 쿼리에는 없었지만 LLM 사전 확장 힌트(§3.1)에서 추가로 감지된 노드.
    # detected_nodes에도 합산 포함되어 있으며, 이 필드는 출처 구분을 위한 투명성 기록용.
    expansion_detected_nodes: List[N8NNodeDef]    = dc_field(default_factory=list)

    @property
    def has_pattern(self) -> bool:
        return self.pattern is not None

    @property
    def anti_patterns(self) -> List[str]:
        return [h for h in self.ontology_hints if h.startswith("[ANTI-PATTERN]")]

    @property
    def best_practices(self) -> List[str]:
        return [h for h in self.ontology_hints if h.startswith("[BEST-PRACTICE]")]


# 싱글턴
_enhancer: Optional[OntologyEnhancer] = None

def get_ontology_enhancer() -> OntologyEnhancer:
    global _enhancer
    if _enhancer is None:
        _enhancer = OntologyEnhancer()
    return _enhancer
