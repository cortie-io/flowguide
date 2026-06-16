# ─────────────────────────────────────────────────────────────
# chatbot/Dockerfile — nodi Next.js 프론트엔드
#
# 3단계 멀티스테이지 빌드:
#   deps    → pnpm install (레이어 캐싱)
#   builder → next build
#   runner  → 프로덕션 실행 + DB 마이그레이션
# ─────────────────────────────────────────────────────────────

# ── 1단계: 의존성 설치 ────────────────────────────────────────
FROM node:22-alpine AS deps
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@10.32.1 --activate

WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# ── 2단계: 빌드 ───────────────────────────────────────────────
FROM node:22-alpine AS builder
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@10.32.1 --activate

WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
# DB 마이그레이션은 컨테이너 시작 시 실행 — 빌드 단계에서 제외
RUN pnpm exec next build

# ── 3단계: 프로덕션 런타임 ────────────────────────────────────
FROM node:22-alpine AS runner
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@10.32.1 --activate

WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs \
 && adduser  --system --uid 1001 nextjs

# 실행에 필요한 파일만 복사
COPY --from=deps    /app/node_modules          ./node_modules
COPY --from=builder --chown=nextjs:nodejs /app/.next          ./.next
COPY --from=builder --chown=nextjs:nodejs /app/public         ./public
COPY --chown=nextjs:nodejs package.json ./
# DB 마이그레이션 스크립트
COPY --chown=nextjs:nodejs lib/db ./lib/db

USER nextjs
EXPOSE 3000

# 컨테이너 기동 시: 마이그레이션 → Next.js 서버 시작
CMD ["sh", "-c", "npx tsx lib/db/migrate.ts && pnpm next start -p 3000"]
