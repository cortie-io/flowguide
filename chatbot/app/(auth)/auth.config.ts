import type { NextAuthConfig } from "next-auth";

const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

// prod(https)에서만 SameSite=None 적용 — Secure 없이 None을 쓰면 브라우저가
// 쿠키 자체를 버리기 때문에, http 로컬 개발 환경에서는 기본값(lax)을 유지해야 함.
const useCrossSiteCookies = process.env.NODE_ENV === "production";

export const authConfig = {
  basePath: "/api/auth",
  trustHost: true,
  pages: {
    signIn: `${base}/login`,
    newUser: `${base}/`,
  },
  providers: [],
  callbacks: {},
  // Naito 브라우저 확장(사이드패널)이 naito.chat을 iframe으로 띄우는데,
  // 이건 브라우저 기준 크로스사이트 컨텍스트라 기본 SameSite=Lax 쿠키는
  // 전송되지 않아 iframe 안에서 로그인 세션이 안 잡히는 문제가 있었음.
  cookies: useCrossSiteCookies
    ? {
        sessionToken: { options: { sameSite: "none", secure: true } },
        csrfToken: { options: { sameSite: "none", secure: true } },
        callbackUrl: { options: { sameSite: "none", secure: true } },
      }
    : undefined,
} satisfies NextAuthConfig;
