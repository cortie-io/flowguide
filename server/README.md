# Naito — Next-Gen Node Automation Tutor
# FastAPI 백엔드 프로젝트 구조

```
n9n_backend/
├── main.py                          # FastAPI 앱 엔트리포인트
├── requirements.txt
├── API_SPEC.yaml                    # 전체 API 엔드포인트 명세
├── .env                             # 환경변수 (OLLAMA_BASE_URL 등)
│
├── app/
│   ├── core/
│   │   ├── config.py                # 전역 설정 (Settings)
│   │   ├── engine.py                # N8NQueryEngine 싱글턴 래퍼
│   │   ├── intent_router.py         # ★ IntentRouter — 5대 기능 분기
│   │   ├── session.py               # ⑥ SessionStore + WorkflowSnapshot
│   │   ├── credential_filter.py     # ⑦ CredentialFilter 블랙홀 필터
│   │   └── query_rewrite.py         # 한국어 → 듀얼 확장 (query_engine.py 공유)
│   │
│   ├── routers/
│   │   ├── workspace.py             # POST /api/workspace/stream (메인 허브)
│   │   ├── node.py                  # POST /api/node/inspect
│   │   ├── workflow.py              # POST /api/workflow/inject|rollback
│   │   ├── error_patch.py           # POST /api/error/patch
│   │   └── reverse.py              # POST /api/workflow/reverse
│   │
│   ├── services/
│   │   ├── curriculum.py            # ① 커리큘럼 퓨전 서비스
│   │   ├── expression.py            # ② 수식 자동 생성 서비스
│   │   ├── workflow_build.py        # ③ 코드 합성 + 최적화 서비스
│   │   ├── error_patch.py           # ④ 에러 원격 수술 서비스
│   │   ├── reverse.py              # ⑤ 리버스 엔지니어링 서비스
│   │   └── general_rag.py           # 일반 RAG Q&A 서비스
│   │
│   └── ws/
│       └── extension_hub.py         # WS /ws/extension 크롬 익스텐션 허브
│
└── query_engine.py                  # (v1 공유) HybridRetriever + REGValidator
```

## 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경 변수 설정
cat > .env << 'EOF'
OLLAMA_BASE_URL=http://100.79.44.109:11434
LLM_MODEL=gemma4-e4b:latest
CHUNKS_JSONL_PATH=final_rag_chunks_v2.jsonl
EOF

# 3. 서버 기동
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 4. API 문서 확인
open http://localhost:8000/docs
```

## 크롬 익스텐션 연동

```javascript
// 익스텐션에서 WebSocket 연결
const ws = new WebSocket('ws://localhost:8000/ws/extension');
const sessionId = crypto.randomUUID();

ws.onopen = () => {
  // 노드 선택 이벤트 전송
  ws.send(JSON.stringify({
    event: 'node_selected',
    payload: {
      type: currentNode.type,
      parameters: currentNode.parameters,
      inputData: executionData
    }
  }));
};

// SSE 스트리밍 (대화창)
const stream = await fetch('http://localhost:8000/api/workspace/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: sessionId,
    message: '수식 만들어줘',
    node_data: currentNodeJson,
  })
});

const reader = stream.body.getReader();
// ... SSE 파싱 로직
```

## Intent 분기 로직 요약

| 조건                                          | Intent          | 서비스              |
|----------------------------------------------|-----------------|---------------------|
| error_log 첨부 + 에러 키워드                   | ERROR_PATCH ④   | ErrorPatchService   |
| raw_json 에 "connections" 키 존재             | REVERSE ⑤      | ReverseService      |
| node_data 첨부 + "수식/expression" 키워드      | EXPRESSION ②   | ExpressionService   |
| "커리큘럼/로드맵" 키워드                       | CURRICULUM ①   | CurriculumService   |
| "만들어줘/배치/최적화" 키워드                  | WORKFLOW_BUILD ③| WorkflowBuildService|
| 기타                                          | GENERAL        | GeneralRAGService   |
