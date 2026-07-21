import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  return NextResponse.redirect(new URL(`${base}/login`, request.url));
}
