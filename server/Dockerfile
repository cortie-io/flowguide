# ─────────────────────────────────────────────────────────────
# server/Dockerfile — nodi FastAPI 백엔드
#
# 빌드 컨텍스트: 프로젝트 루트 (docker compose에서 context: . 로 실행)
# 포함 항목:
#   server/          → /app/server/
#   query_engine.py  → /app/query_engine.py
#   RAG_dataset/     → 볼륨으로 마운트 (/app/RAG_dataset)
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 의존성 먼저 설치 (레이어 캐싱)
COPY server/requirements.txt server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

# 소스 코드 복사
COPY server/ server/
COPY query_engine.py .

# RAG_dataset은 docker-compose 볼륨으로 마운트됨
# (/app/RAG_dataset → ./RAG_dataset:/app/RAG_dataset:ro)

EXPOSE 8000

# server/ 디렉토리에서 실행 → engine.py의 _root가 /app으로 설정됨
WORKDIR /app/server
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
