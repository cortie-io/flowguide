import { NextResponse } from "next/server"
import bcrypt from "bcryptjs"
import { prisma } from "@/lib/db"
import { createSession } from "@/lib/auth/session"

export async function POST(req: Request) {
  const body = await req.json().catch(() => null)
  const identifier = typeof body?.identifier === "string" ? body.identifier.trim().toLowerCase() : ""
  const password = typeof body?.password === "string" ? body.password : ""

  if (!identifier || !password) {
    return NextResponse.json({ error: "아이디(또는 이메일)와 비밀번호를 입력해 주세요." }, { status: 400 })
  }

  const user = await prisma.user.findFirst({
    where: { OR: [{ username: identifier }, { email: identifier }] },
  })
  if (!user) {
    return NextResponse.json({ error: "등록되지 않은 계정이에요." }, { status: 401 })
  }

  const valid = await bcrypt.compare(password, user.passwordHash)
  if (!valid) {
    return NextResponse.json({ error: "비밀번호가 일치하지 않아요." }, { status: 401 })
  }

  await createSession(user.id)
  return NextResponse.json({
    user: { name: user.name, username: user.username, email: user.email, isAdmin: user.isAdmin },
  })
}
