"""
app/core/query_rewrite.py

query_engine.py 의 rewrite_query() 를 서비스 레이어에서
import 할 수 있도록 re-export 하는 어댑터 모듈.

query_engine.py 가 없을 때는 간이 버전으로 폴백.
"""

from __future__ import annotations

import logging
import re

log = logging.getLogger("naito.query_rewrite")


def rewrite_query(user_query: str) -> dict[str, str]:
    """
    query_engine.py 의 rewrite_query() 를 우선 사용.
    없을 경우 간이 버전으로 폴백.
    """
    try:
        from query_engine import rewrite_query as _rewrite
        return _rewrite(user_query)
    except ImportError:
        return _simple_rewrite(user_query)


_KO_STOPWORDS = {
    "을", "를", "이", "가", "은", "는", "에서", "으로", "로", "에",
    "의", "과", "와", "도", "만", "하다", "합니다", "해줘", "알려줘",
    "방법", "어떻게", "무엇", "어떤", "왜", "주세요", "해주세요", "좀",
}

_DOMAIN_MAP = {
    "웹훅": "webhook trigger",
    "트리거": "trigger",
    "인증": "authentication credential",
    "에러": "error handling",
    "오류": "error handling",
    "수식": "expression $json",
    "루프": "loop over items split in batches",
    "반복": "loop split in batches",
    "워크플로우": "workflow",
    "노드": "node",
    "속성": "property parameter option field",
    "파라미터": "parameter option field",
    "옵션": "option parameter",
    "분기": "switch branch condition rule",
    "조건": "condition rule compare",
}


def _simple_rewrite(user_query: str) -> dict[str, str]:
    cleaned = re.sub(r"[^\w\s가-힣${}.]", " ", user_query).strip()
    tokens = [t for t in cleaned.split() if t not in _KO_STOPWORDS]
    ko_clean = " ".join(tokens)

    en_tokens: list[str] = []
    for ko, en in _DOMAIN_MAP.items():
        if ko in user_query:
            en_tokens.extend(en.split())
    en_tokens.extend(t for t in tokens if re.match(r"[A-Za-z$]", t))
    en_expanded = " ".join(dict.fromkeys(en_tokens))

    return {
        "ko_clean": ko_clean,
        "en_expanded": en_expanded,
        "combined": f"{ko_clean} {en_expanded}".strip(),
    }
