# n8n AI Tutor RAG 방법론 최종안 (v2)

이 문서는 책 코퍼스(book.md)까지 포함한 최종 RAG 방법론입니다.
핵심 목표는 "검색 정밀화"와 "운영 안정화"를 동시에 달성하는 것입니다.

## 1) 최종 코퍼스 레이어

### Core Layer (정답률 우선)
- n8n_properties_spec.txt
- n8n_cli_spec.txt
- n8n_version_changelog.txt
- n8n_code_node_snippets.txt
- troubleshooting_faq.txt
- external_api_limits.txt

### Corpus Layer (맥락 보강)
- docs/ (공식 문서)
- workflow_templates_text/ (템플릿 요약 + JSON 원문)
- book.md (실무서 기반 보강 지식)

### Meta Layer
- README.md
- RAG_ARCHITECTURE_PROTOCOL_v1.md
- RAG_ENGINEERING_REVIEW_v1.md

운영 원칙
- Meta 문서는 인덱싱 제외
- Core + Corpus만 벡터화

## 2) 청킹 전략 (Type-aware)

### Track A: docs markdown
- Header split(#, ##, ###) -> recursive split
- chunk_size=800, overlap=100
- 목적: 문서 계층 보존

### Track B: core text/spec
- 파일별 경계 분리자 우선
- chunk_size=900~1400, overlap=120~220
- 목적: 선언형 명세 파편화 방지

### Track C: changelog
- # Version: 경계 먼저 split
- chunk_size=1500, overlap=250
- 목적: 버전 혼합 방지

### Track D: templates (Parent-Child)
- Parent: 요약/노드목록
	- chunk_size=900, overlap=120
- Child: JSON 원문
	- chunk_size=2200, overlap=200
- 목적: 추천 품질과 JSON 회수율 동시 확보

### Track E: book.md
- 페이지 마커가 있으면 마커 우선
- 없으면 장/절 헤더(##, ###) 기반
- chunk_size=1500~1600, overlap=200~220

## 3) 메타데이터 최종 스키마

필수
- source_file
- source_path
- data_type
- language
- priority
- chunk_global_id
- chunk_index
- chunk_size

권장
- doc_id
- parent_id
- chunk_role
- product_area
- target_version
- node_name
- is_breaking_change
- source_repo

검색 품질 핵심
- changelog: target_version, is_breaking_change
- template: parent_id, chunk_role, node_name
- docs: product_area, section_path

## 4) Retrieval 아키텍처 최종안

1. Query Normalize
- 에러코드/버전/노드명 추출
- 한국어 조사 정리

2. Query Rewrite/Expansion
- ko 원문 유지
- en 키워드 보강 질의 추가

3. 1차 회수
- Vector Top-K
- BM25 Top-K

4. Hybrid Fusion
- RRF(k=60)
- 초기 가중치: Vector 0.6, BM25 0.4

5. Metadata 라우팅/필터
- 버전 질의 -> changelog boost
- 코드 질의 -> code_snippet boost
- 장애 질의 -> troubleshooting/docs-hosting boost
- 템플릿 질의 -> template_summary_parent boost

6. Reranking
- bge-reranker-v2-m3
- Top 40~80 후보 재정렬 후 최종 6~10 컨텍스트 선택

## 5) 다국어 전략 (KO 질문, EN 중심 소스)

- Cross-lingual embedding 유지
- 도메인 사전 기반 리라이트 추가
	- 예: 인증->authentication, 웹훅->webhook
- 답변 언어 규칙:
	- 설명은 한국어
	- 노드명/옵션명/파라미터명은 영어 유지

## 6) 템플릿 검색 전략 최종안

문제
- 요약 + JSON 결합 단일 청크는 임베딩 희석 위험

해법
- Parent(요약)로 먼저 매칭
- Parent의 parent_id로 Child(JSON) 회수
- 답변 시:
	- 먼저 요약 근거 제시
	- 이어서 JSON 핵심 스니펫 제공

## 7) 운영 가드레일

- 인덱싱은 파일 스트리밍 처리
- 중간 산출물(JSONL) 저장
- 실패 청크 재시도 및 실패 로그 저장
- 품질 회귀셋 최소 60문항 유지
	- 버전 20
	- 코드 20
	- 트러블슈팅 20

## 8) 실행 스크립트

v2 전처리 스크립트:
- build_final_rag_v2.py

산출물:
- final/final_rag_chunks_v2.jsonl
- final/final_rag_stats_v2.json

주의
- 이 스크립트는 벡터 DB를 생성하지 않습니다.
- 최종 임베딩/색인은 산출물 검증 후 별도 단계에서 수행합니다.

## 9) 최종 결론

현재 코퍼스는 "튜터형 RAG"에 매우 적합한 상태입니다.
이제 핵심은 다음 순서입니다.

1. v2 전처리로 청크+메타데이터 확정
2. Hybrid Retrieval + Reranking 적용
3. 회귀 테스트로 품질 수치화

이 3단계가 완료되면 n8n 전문 질의(버전/코드/운영장애/템플릿 추천)에서 실전 정확도를 안정적으로 확보할 수 있습니다.
