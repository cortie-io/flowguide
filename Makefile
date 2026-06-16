.PHONY: up down build rebuild logs ps setup migrate \
        shell-backend shell-chatbot shell-postgres reset

# ── 기본 명령 ────────────────────────────────────────────────

## 전체 서비스 시작 (백그라운드)
up:
	docker compose up -d

## 전체 서비스 종료
down:
	docker compose down

## 이미지 빌드 (변경사항 반영)
build:
	docker compose build

## 이미지 강제 재빌드 + 시작
rebuild:
	docker compose build --no-cache
	docker compose up -d

## 실시간 로그 출력
logs:
	docker compose logs -f

## 서비스 상태 확인
ps:
	docker compose ps

# ── 초기 설정 ────────────────────────────────────────────────

## 처음 설치: .env 생성 → 이미지 빌드 → 서비스 시작
setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo ""; \
		echo ">>> .env 파일이 생성됐습니다. 값을 채운 뒤 다시 실행하세요:"; \
		echo "    1. vi .env  (AUTH_SECRET, POSTGRES_PASSWORD 등 설정)"; \
		echo "    2. make up"; \
		echo ""; \
	else \
		echo ">>> .env 이미 존재합니다. 빌드를 시작합니다..."; \
		docker compose build; \
		docker compose up -d; \
	fi

# ── DB 작업 ──────────────────────────────────────────────────

## DB 마이그레이션 수동 실행 (chatbot 컨테이너 기동 중일 때)
migrate:
	docker compose exec chatbot sh -c "npx tsx lib/db/migrate.ts"

# ── 쉘 접속 ─────────────────────────────────────────────────

## FastAPI 백엔드 쉘
shell-backend:
	docker compose exec backend bash

## Next.js 챗봇 쉘
shell-chatbot:
	docker compose exec chatbot sh

## PostgreSQL 쉘
shell-postgres:
	docker compose exec postgres psql -U $${POSTGRES_USER:-n9n} -d $${POSTGRES_DB:-chatbot}

# ── 초기화 (주의) ────────────────────────────────────────────

## 모든 컨테이너 + 볼륨 삭제 (DB 데이터 초기화)
reset:
	@echo "경고: DB 데이터가 모두 삭제됩니다. 계속하려면 Enter..."
	@read _confirm
	docker compose down -v
