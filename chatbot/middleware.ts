import { type NextRequest, NextResponse } from "next/server";

function hasSessionCookie(request: NextRequest) {
  return (
    request.cookies.has("__Secure-authjs.session-token") ||
    request.cookies.has("authjs.session-token")
  );
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/ping")) {
    return new Response("pong", { status: 200 });
  }

  // Some browser extensions inject a probe script at /c.js.
  // Return a harmless JS payload instead of redirecting/auth-gating this path.
  if (pathname === "/c.js") {
    return new Response(";", {
      status: 200,
      headers: {
        "Content-Type": "application/javascript; charset=utf-8",
        "Cache-Control": "public, max-age=600",
      },
    });
  }

  if (pathname.startsWith("/api/auth")) {
    return NextResponse.next();
  }

  const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  const isLoginPage = pathname === `${base}/login`;
  const isAuthPage =
    isLoginPage ||
    pathname === `${base}/register` ||
    pathname === `${base}/signup`;

  if (!hasSessionCookie(request)) {
    if (isAuthPage) {
      return NextResponse.next();
    }
    return NextResponse.redirect(new URL(`${base}/login`, request.url));
  }

  // 이미 로그인된 사용자가 auth 페이지 방문 → 홈으로
  if (isAuthPage) {
    return NextResponse.redirect(new URL(`${base}/`, request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/",
    "/chat/:id",
    "/api/:path*",
    "/login",
    "/register",
    "/signup",

    "/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
  ],
};
