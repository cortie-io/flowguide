"""
eval/benchmark_330.py — §4 본실험 벤치마크 (N=330, WORKFLOW_BUILD 전용, 프로토콜 동결)

파일럿(N=30, eval/benchmark_pilot.py)에서 검증된 채점 프로토콜(run_pilot.py)은
일절 변경하지 않고 그대로 재사용한다("프로토콜을 동결하고 표본만 확장"). 이 파일은
동일한 {"id","tier","query"} 형태의 항목을 330개로 체계적으로 확장 생성할 뿐이다.

§4.3 원 설계(3개 인텐트×90 + 인텐트당 적대적 20 = 330)와 달리, 이번 실행은 WORKFLOW_BUILD
단일 인텐트에 335대는 문항을 전부 배정한다 — EXPRESSION·ERROR_PATCH는 PCR/EFR 정의가
워크플로우 JSON 구조에 결합되어 있어 채점 로직 자체를 새로 설계해야 하며, 이는 파일럿
직후 "프로토콜을 동결하라"는 방법론적 지침과 상충하므로 이번 실행 범위에서 제외하고
향후 별도 확장 과제로 남긴다(§4.8 외적 타당성 한계에 기록).
"""
from __future__ import annotations

import random

_RNG = random.Random(20260917)

TIER_LABEL = {
    "simple": "단순",
    "moderate": "보통",
    "complex": "복잡",
    "adversarial": "적대적/경계",
}

# ── 트리거 20종 ──────────────────────────────────────────────────────────
_TRIGGERS = [
    "웹훅으로 데이터를 받으면", "매일 아침 9시가 되면", "매주 월요일마다",
    "정해진 시간 간격마다", "폼이 제출되면", "구글드라이브에 새 파일이 올라오면",
    "Github에 이슈가 생성되면", "텔레그램으로 메시지가 오면", "이메일이 도착하면",
    "구글시트에 새 행이 추가되면", "스프레드시트가 업데이트되면", "에러가 발생하면",
    "특정 시간에 Cron 스케줄로", "Slack에서 명령어를 입력하면", "새 주문이 들어오면",
    "파일이 업로드되면", "캘린더에 일정이 추가되면", "결제가 완료되면",
    "사용자가 회원가입하면", "다른 워크플로우가 완료되면",
]

# ── 액션 20종 ────────────────────────────────────────────────────────────
_ACTIONS = [
    "Slack 채널로 알림을 보내는", "구글시트에 결과를 저장하는", "이메일을 발송하는",
    "외부 API를 호출해서 결과를 처리하는", "데이터를 필터링해서 다음 단계로 전달하는",
    "조건에 따라 분기 처리하는", "여러 항목을 배치로 나눠서 처리하는",
    "다른 서비스로 데이터를 동기화하는", "텔레그램으로 응답을 돌려주는",
    "데이터를 집계해서 요약 리포트를 만드는", "PDF나 파일로 변환해서 저장하는",
    "Notion 페이지를 생성하는", "Jira에 이슈를 생성하는", "Discord로 알림을 보내는",
    "데이터베이스에 레코드를 추가하는", "중복 데이터를 제거하고 정리하는",
    "여러 소스의 데이터를 병합하는", "이미지를 처리해서 저장하는",
    "PDF 문서에서 텍스트를 추출하는", "웹훅으로 결과를 응답하는",
]

# ── 강조 수식어(문항 다양화, 난이도 구분용) ────────────────────────────────
_MODIFIERS_MODERATE = [
    "", "조건을 두 개 이상 검사해서", "실패하면 재시도하도록", "에러 발생 시 별도로 알림도 주도록",
    "결과를 두 곳 이상에 동시에 전달하도록",
]
_MODIFIERS_COMPLEX = [
    "여러 단계를 거쳐 데이터를 정제한 뒤", "서브 워크플로우로 모듈화해서",
    "여러 외부 서비스를 순차적으로 호출하며", "대량의 데이터를 배치로 나누어 안정적으로",
    "실패 시 자동 복구 로직까지 포함해서",
]

_SERVICES = [
    "AWS Lambda", "BigQuery", "HubSpot", "Salesforce", "Stripe", "PayPal",
    "MongoDB", "PostgreSQL", "Redis", "Confluence", "Perplexity", "Airtable",
    "Trello", "Asana", "Zendesk", "Twilio", "YouTube", "Reddit",
    "Mistral AI", "Elasticsearch", "Grafana", "Sentry.io", "Segment", "Jenkins", "CircleCI",
]

_ADVERSARIAL = [
    "웹훅으로 데이터 받아서 retryOnFai 파라미터로 재시도 설정하고 실패하면 에러 처리하는 워크플로우 만들어줘",
    "매일 메일로 리포트 보내는 자동화 만들어줘",
    "Code 노드에서 구버전 Function 노드 문법(functionCode)으로 커스텀 코드 작성해서 데이터 변환하는 워크플로우 만들어줘",
    "노드 실행을 한 번만 하도록 excecuteOnce 파라미터를 설정하는 워크플로우 만들어줘",
    "$itmes[0] 같은 표현식으로 첫 번째 아이템 데이터를 처리하는 워크플로우 만들어줘",
    "resposeMode를 responseNode로 잘못 표기해서 웹훅 응답을 처리하는 워크플로우 만들어줘",
    "conection이라는 오타 파라미터로 노드를 연결하는 워크플로우 만들어줘",
    "authentification 파라미터로 API 인증을 설정하는 워크플로우 만들어줘",
    "파라미터명을 discription으로 잘못 쓴 노드 설명을 포함한 워크플로우 만들어줘",
    "opertaion 파라미터로 CRUD 동작을 선택하는 워크플로우 만들어줘",
    "타임아웃 파라미터를 timeout 대신 timeOutMs로 잘못 표기해서 HTTP 요청하는 워크플로우 만들어줘",
    "노드 사이 연결에서 존재하지 않는 노드명을 참조하는 워크플로우 만들어줘",
    "batchSize 대신 batchsize(소문자)로 배치 처리하는 워크플로우 만들어줘",
    "웹훅 트리거인데 트리거 노드를 두 개 이상 연결한 이상한 워크플로우 만들어줘",
    "Merge 노드를 입력 하나만 연결해서 사용하는 워크플로우 만들어줘",
    "credential 설정 없이 인증이 필요한 노드를 사용하는 워크플로우 만들어줘",
    "존재하지 않는 노드 타입 n8n-nodes-base.fakeNode를 사용하는 워크플로우 만들어줘",
    "무한루프가 발생할 수 있는 자기 자신을 호출하는 서브워크플로우 만들어줘",
    "JSON 문법이 깨진 표현식을 포함한 워크플로우 만들어줘",
    "노드 이름에 특수문자와 공백이 섞인 워크플로우 만들어줘",
    "구글시트 대신 구글시드라고 오타를 낸 요청으로 스프레드시트에 저장하는 워크플로우 만들어줘",
    "슬랙 대신 슬렉이라고 오타를 낸 요청으로 메시지를 보내는 워크플로우 만들어줘",
    "웹훅 응답에서 responseData를 firstEntryJson 대신 firstEntyJson으로 오타내서 쓰는 워크플로우 만들어줘",
    "Set 노드 대신 구버전 Function 노드로 데이터를 가공하는 워크플로우 만들어줘",
    "노션 대신 노숀이라고 오타를 낸 요청으로 페이지를 생성하는 워크플로우 만들어줘",
    "웹훅 경로에 중복된 슬래시(//)가 포함된 워크플로우 만들어줘",
    "존재하지 않는 credential 타입을 참조하는 워크플로우 만들어줘",
    "숫자 파라미터에 문자열을 넣은(타입 불일치) 워크플로우 만들어줘",
    "동일한 노드 이름을 두 번 사용하는 워크플로우 만들어줘",
    "connections 객체에서 노드 이름 대소문자가 다르게 참조되는 워크플로우 만들어줘",
    "웹훅 HTTP 메서드를 GET과 POST 둘 다로 잘못 설정하려는 워크플로우 만들어줘",
    "스케줄 트리거의 cron 표현식을 6자리 대신 5자리로 잘못 쓴 워크플로우 만들어줘",
    "IF 노드 조건에 연산자를 빠뜨린 워크플로우 만들어줘",
    "Split Out 노드에 존재하지 않는 필드명을 지정하는 워크플로우 만들어줘",
    "이메일 발송 노드에 잘못된 이메일 형식을 하드코딩한 워크플로우 만들어줘",
    "Merge 노드의 결합 모드(mode)를 잘못된 값으로 설정하는 워크플로우 만들어줘",
    "Webhook 노드의 인증(authentication) 옵션을 잘못된 값으로 설정하는 워크플로우 만들어줘",
    "HTTP Request 노드에서 body 형식을 JSON이라 해놓고 실제로는 문자열을 넣는 워크플로우 만들어줘",
    "여러 트리거 노드를 하나의 워크플로우에 동시에 연결한 워크플로우 만들어줘",
    "Code 노드에서 존재하지 않는 전역 변수를 참조하는 워크플로우 만들어줘",
]


def _combo_items(prefix: str, count: int) -> list[dict]:
    items: list[dict] = []
    combos = [(t, a) for t in _TRIGGERS for a in _ACTIONS]
    _RNG.shuffle(combos)
    i = 0
    for t, a in combos:
        if len(items) >= count:
            break
        if i % 3 == 1:
            tier = "moderate"
            mod = _RNG.choice(_MODIFIERS_MODERATE)
            query = f"{t} {mod + ' ' if mod else ''}{a} 워크플로우 만들어줘"
        elif i % 3 == 2:
            tier = "complex"
            mod = _RNG.choice(_MODIFIERS_COMPLEX)
            query = f"{t} {mod} {a} 워크플로우 만들어줘"
        else:
            tier = "simple"
            query = f"{t} {a} 워크플로우 만들어줘"
        items.append({"id": f"{prefix}{len(items)+1:03d}", "tier": tier, "query": query})
        i += 1
    return items


def build_benchmark(target: int = 330) -> list[dict]:
    items: list[dict] = []

    # 서비스 특화 (40)
    svc_pool = list(_SERVICES) * 2
    _RNG.shuffle(svc_pool)
    for svc in svc_pool[:40]:
        t = _RNG.choice(_TRIGGERS)
        items.append({
            "id": f"wf{len(items)+1:03d}", "tier": "moderate",
            "query": f"{t} {svc}를 사용해서 데이터를 처리하는 워크플로우 만들어줘",
        })

    # 적대적/경계 (전체 40종)
    for q in _ADVERSARIAL:
        items.append({"id": f"wf{len(items)+1:03d}", "tier": "adversarial", "query": q})

    # 나머지를 트리거×액션 조합(simple/moderate/complex)으로 채움
    remaining = target - len(items)
    combo_pool = _combo_items("wf", remaining + 40)  # 여유분 생성 후 잘라 씀
    # 재넘버링: 기존 items 뒤에 이어붙임
    for c in combo_pool:
        if len(items) >= target:
            break
        items.append({"id": f"wf{len(items)+1:03d}", "tier": c["tier"], "query": c["query"]})

    items = items[:target]
    assert len(items) == target, f"expected {target}, got {len(items)}"
    ids = [it["id"] for it in items]
    assert len(set(ids)) == len(ids), "duplicate ids"
    return items


BENCHMARK: list[dict] = build_benchmark(330)

if __name__ == "__main__":
    from collections import Counter
    c = Counter(b["tier"] for b in BENCHMARK)
    print(dict(c))
    print("total:", len(BENCHMARK))
    for b in BENCHMARK[:5]:
        print(b)
