"""
eval/benchmark_pilot.py — §4 평가 방법론 파일럿 벤치마크 (N=30)

범위: WORKFLOW_BUILD 인텐트만(§4.3의 워크플로우 설계/표현식/에러진단 3종 중
      PCR·EFR·SA가 가장 명확히 정의되는 유형). 표현식·에러진단 인텐트와
      Gemini 교차모델·DRR(k=3 반복)·HR(인간 판정)은 전체 330문항 본실험 범위로
      명시적으로 남겨둔다(사용자 확인 사항).
"""
from __future__ import annotations

TIER_LABEL = {
    "simple": "단순",
    "moderate": "보통",
    "complex": "복잡",
    "adversarial": "적대적/경계",
}

BENCHMARK: list[dict] = [
    # ── 단순 (10) ──────────────────────────────────────────────────
    {"id": "wb01", "tier": "simple", "query": "웹훅으로 데이터 받으면 그대로 응답 돌려주는 워크플로우 만들어줘"},
    {"id": "wb02", "tier": "simple", "query": "매일 아침 9시에 실행되는 스케줄 트리거 워크플로우 만들어줘"},
    {"id": "wb03", "tier": "simple", "query": "구글시트에 새 행 추가하는 워크플로우 만들어줘"},
    {"id": "wb04", "tier": "simple", "query": "Slack 채널에 메시지 보내는 간단한 워크플로우 만들어줘"},
    {"id": "wb05", "tier": "simple", "query": "HTTP GET 요청 보내고 결과를 Set 노드로 정리하는 워크플로우 만들어줘"},
    {"id": "wb06", "tier": "simple", "query": "텔레그램 봇으로 메시지 받으면 그대로 답장하는 워크플로우 만들어줘"},
    {"id": "wb07", "tier": "simple", "query": "이메일 발송하는 간단한 워크플로우 만들어줘"},
    {"id": "wb08", "tier": "simple", "query": "폼 제출받아서 구글시트에 저장하는 워크플로우 만들어줘"},
    {"id": "wb09", "tier": "simple", "query": "Github 이슈가 새로 생성되면 알림 받는 워크플로우 만들어줘"},
    {"id": "wb10", "tier": "simple", "query": "정해진 시간마다 API를 호출해서 상태를 확인하는 워크플로우 만들어줘"},
    # ── 보통 (10, WorkflowPatterns 기반) ─────────────────────────────
    {"id": "wb11", "tier": "moderate", "query": "매일 아침 외부 API에서 데이터 가져와서 조건에 따라 Slack으로 알림 보내는 워크플로우 만들어줘"},
    {"id": "wb12", "tier": "moderate", "query": "웹훅으로 주문 데이터 받아서 정제한 뒤 구글시트에 저장하고 응답을 돌려주는 워크플로우 만들어줘"},
    {"id": "wb13", "tier": "moderate", "query": "대량의 아이템을 배치로 나눠서 API 호출하고 결과를 집계하는 워크플로우 만들어줘"},
    {"id": "wb14", "tier": "moderate", "query": "매일 외부 API에서 데이터 수집해서 구글시트에 적재하는 ETL 파이프라인 만들어줘"},
    {"id": "wb15", "tier": "moderate", "query": "배열 데이터를 분리해서 각각 API 호출한 뒤 다시 병합하는 워크플로우 만들어줘"},
    {"id": "wb16", "tier": "moderate", "query": "텔레그램으로 명령어 받으면 조건에 따라 분기해서 답장하는 봇 워크플로우 만들어줘"},
    {"id": "wb17", "tier": "moderate", "query": "폼 제출 데이터를 구글시트에 저장하고 이메일로도 발송하는 워크플로우 만들어줘"},
    {"id": "wb18", "tier": "moderate", "query": "구글드라이브에 파일이 업로드되면 내용을 추출해서 구글시트에 정리하는 워크플로우 만들어줘"},
    {"id": "wb19", "tier": "moderate", "query": "Github에 PR이 생성되면 Slack과 Jira에 동시에 알리는 워크플로우 만들어줘"},
    {"id": "wb20", "tier": "moderate", "query": "서브 워크플로우를 호출해서 모듈화된 자동화를 구성하는 워크플로우 만들어줘"},
    # ── 복잡 (5) ──────────────────────────────────────────────────
    {"id": "wb21", "tier": "complex", "query": "에러 발생 시 Slack으로 알림 보내되, 에러 종류에 따라 다른 채널로 분기하는 에러 모니터링 워크플로우 만들어줘"},
    {"id": "wb22", "tier": "complex", "query": "AWS Lambda 함수를 호출해서 그 결과를 DynamoDB에 저장하고, 실패하면 SNS로 알림을 보내는 워크플로우 만들어줘"},
    {"id": "wb23", "tier": "complex", "query": "Perplexity API로 최신 뉴스를 검색해서 요약한 뒤 Confluence 페이지에 게시하는 워크플로우 만들어줘"},
    {"id": "wb24", "tier": "complex", "query": "여러 CRM(HubSpot, Salesforce)에서 데이터를 수집해서 BigQuery에 적재하는 ETL 워크플로우 만들어줘"},
    {"id": "wb25", "tier": "complex", "query": "웹훅으로 결제 이벤트를 받으면 금액에 따라 PayPal과 Stripe로 분기 처리하고, 결과를 이메일과 Slack 양쪽에 알리는 워크플로우 만들어줘"},
    # ── 적대적/경계 (5) ────────────────────────────────────────────
    {"id": "wb26", "tier": "adversarial", "query": "웹훅으로 데이터 받아서 retryOnFai 파라미터로 재시도 설정하고 실패하면 에러 처리하는 워크플로우 만들어줘"},
    {"id": "wb27", "tier": "adversarial", "query": "매일 메일로 리포트 보내는 자동화 만들어줘"},
    {"id": "wb28", "tier": "adversarial", "query": "Code 노드에서 구버전 Function 노드 문법(functionCode)으로 커스텀 코드 작성해서 데이터 변환하는 워크플로우 만들어줘"},
    {"id": "wb29", "tier": "adversarial", "query": "노드 실행을 한 번만 하도록 excecuteOnce 파라미터를 설정하는 워크플로우 만들어줘"},
    {"id": "wb30", "tier": "adversarial", "query": "$itmes[0] 같은 표현식으로 첫 번째 아이템 데이터를 처리하는 워크플로우 만들어줘"},
]

assert len(BENCHMARK) == 30
assert len({b["id"] for b in BENCHMARK}) == 30
