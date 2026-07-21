#!/bin/bash
# naito 배포 스크립트
# 사용법:
#   ./deploy.sh          — 변경 감지 후 필요한 것만 재시작
#   ./deploy.sh --full   — 강제 전체 빌드 + 재시작
set -e

FULL=${1:-""}
CHATBOT_DIR="/home/ubuntu/nodi/chatbot"
SERVER_DIR="/home/ubuntu/nodi/server"

# 마지막 배포 이후 변경된 파일 감지
CHATBOT_CHANGED=$(git diff --name-only HEAD~1 HEAD 2>/dev/null | grep "^chatbot/" | wc -l || echo "1")
SERVER_CHANGED=$(git diff --name-only HEAD~1 HEAD 2>/dev/null | grep "^server/" | wc -l || echo "1")

# --full 또는 .next/BUILD_ID 없으면 강제 빌드
if [ ! -f "$CHATBOT_DIR/.next/BUILD_ID" ]; then
  CHATBOT_CHANGED=1
fi

if [ "$FULL" = "--full" ]; then
  echo "[deploy] 강제 전체 빌드 모드"
  CHATBOT_CHANGED=1
  SERVER_CHANGED=1
fi

echo "[deploy] 변경 감지: chatbot=$CHATBOT_CHANGED, server=$SERVER_CHANGED"

# 서버(Python) 변경 → API 재시작만
if [ "$SERVER_CHANGED" -gt 0 ]; then
  echo "[deploy] naito-api 재시작..."
  pm2 restart naito-api
fi

# 프론트(Next.js) 변경 → 빌드 후 재시작
if [ "$CHATBOT_CHANGED" -gt 0 ]; then
  echo "[deploy] naito-web 중지 → 빌드 → 재시작..."
  pm2 stop naito-web
  cd "$CHATBOT_DIR"
  rm -f .next/lock
  NODE_OPTIONS="--max-old-space-size=4096" pnpm build
  pm2 start naito-web
fi

echo "[deploy] 완료"
pm2 list
