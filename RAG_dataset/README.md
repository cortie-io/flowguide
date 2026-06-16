# final 폴더 정리

이 문서는 final 폴더 내부 산출물을 RAG 관점에서 빠르게 파악하기 위한 인덱스입니다.

## 1) 루트 핵심 파일

- n8n_properties_spec.txt
  - 목적: n8n 노드 속성(name, displayName, type, description, default 등) 추출본
  - 사용: 노드 파라미터 추천/설명 검색

- n8n_cli_spec.txt
  - 목적: n8n CLI 명령 명세(name, description, usage, flags) 추출본
  - 사용: CLI 질의응답, 명령어 예시 생성

- n8n_version_changelog.txt
  - 목적: n8n 공식 GitHub 릴리즈 노트(v1.0.0 이상 안정판) 통합본
  - 사용: 버전별 변경사항 기반 장애 진단, 업그레이드 영향도 파악

- n8n_code_node_snippets.txt
  - 목적: Code 노드(JavaScript/Python) 실전 패턴 스니펫 족보
  - 사용: 데이터 가공/변환 코드 자동 제안, 컨텍스트 문법 오류 감소

- troubleshooting_faq.txt
  - 목적: 자주 발생하는 운영/워크플로우 장애 Top 50 트러블슈팅 족보
  - 사용: 장애 원인 추론, 즉시 대응 가이드

- external_api_limits.txt
  - 목적: 외부 API별 제한 및 n8n 대응 패턴 정리
  - 사용: 429/쿼터 초과 예방, 배치/대기 전략 추천

- RAG_ARCHITECTURE_PROTOCOL_v1.md
  - 목적: 다른 AI/협업자에게 전달 가능한 마스터 RAG 설계 프로토콜
  - 사용: 아키텍처 리뷰, 청킹/메타데이터/다국어 인덱싱 피드백 요청

- RAG_ENGINEERING_REVIEW_v1.md
  - 목적: 7대 검증 항목 기반의 공학적 리뷰/디버깅 가이드
  - 사용: 빌드 직전 품질 점검 및 프로덕션 리스크 대응 체크리스트

- RAG_METHODOLOGY_FINAL_v2.md
  - 목적: 책 코퍼스까지 반영한 최종 RAG 방법론
  - 사용: 청킹/메타데이터/하이브리드 검색/운영 가드레일의 최종 기준 문서

## 2) 문서 코퍼스

- docs/
  - 성격: n8n 문서 마크다운 정제본
  - 규모: 약 1,291개 md 파일
  - 활용: 제품 기능 설명, 개념/설정/노드 사용법 검색

- book.md
  - 성격: n8n 실무서 정제본 (장문 도메인 지식)
  - 활용: 한국어 설명 보강, 실무형 예시/워크플로 맥락 보강

- etc/
  - 성격: nav, snippets, yaml 등 보조 메타데이터
  - 활용: 문서 구조 파악, 내비게이션/분류 힌트

## 3) 워크플로우 템플릿 코퍼스

- workflow_templates_text/
  - 성격: 템플릿 JSON을 텍스트로 변환한 RAG 주입본
  - 포함 정보: 템플릿 이름, 사용 노드 목록, 설명, JSON 원본
  - 규모: 2,348개 txt 파일 (요약/실패 로그 포함)
  - 하위 소스:
    - awesome-n8n-templates/
    - n8n-workflow-templates/

- workflow_template_sources/
  - 성격: 템플릿 소스 관련 보관용 폴더
  - 참고: 현재 생성 파이프라인은 origin/ 내 clone 저장소를 직접 사용함

## 4) 권장 RAG 인덱싱 우선순위

1. n8n_properties_spec.txt
2. n8n_cli_spec.txt
3. n8n_version_changelog.txt
4. n8n_code_node_snippets.txt
5. troubleshooting_faq.txt
6. external_api_limits.txt
7. book.md
8. docs/ (전체)
9. workflow_templates_text/ (전체)

## 5) 검색 품질 팁

- 템플릿 추천 정확도 향상:
  - workflow_templates_text/를 우선 검색 대상으로 두고,
  - 질의에서 사용 노드명(Webhook, HTTP Request, OpenAI 등)을 키워드로 함께 전달

- 운영 장애 대응 정확도 향상:
  - troubleshooting_faq.txt + external_api_limits.txt를 우선 참조,
  - 필요 시 docs/hosting 및 docs/api 하위 문서로 확장 검색

- 한국어 설명 품질 향상:
  - book.md를 보조 컨텍스트로 사용해 실무형 한국어 설명을 강화,
  - 단, 파라미터/노드명은 공식 영문 명세를 우선 기준으로 고정

## 6) 비고

- 원본 문서/원본 JSON은 보존하고, final 폴더에는 추출/가공 산출물만 누적하는 방식으로 운영 중.
- 대량 템플릿 변환 통계는 workflow_templates_text/conversion_summary.txt에서 확인 가능.
- 변환 실패 목록은 workflow_templates_text/conversion_failed_files.txt에서 확인 가능.
- 최종 전처리 기준 스크립트는 루트의 build_final_rag_v2.py를 사용.
