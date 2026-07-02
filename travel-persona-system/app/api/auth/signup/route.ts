import { NextResponse } from "next/server"
import bcrypt from "bcryptjs"
import { prisma } from "@/lib/db"
import { createSession } from "@/lib/auth/session"

const USERNAME_RE = /^[a-zA-Z0-9_]{3,20}$/

export async function POST(req: Request) {
  const body = await req.json().catch(() => null)
  const name = typeof body?.name === "string" ? body.name.trim() : ""
  const username = typeof body?.username === "string" ? body.username.trim().toLowerCase() : ""
  const email = typeof body?.email === "string" ? body.email.trim().toLowerCase() : ""
  const password = typeof body?.password === "string" ? body.password : ""
  const birthDateRaw = typeof body?.birthDate === "string" ? body.birthDate.trim() : ""

  if (!name || !username || !email || !password || !birthDateRaw) {
    return NextResponse.json(
      { error: "이름, 생년월일, 이메일, 아이디, 비밀번호를 모두 입력해 주세요." },
      { status: 400 },
    )
  }
  if (!USERNAME_RE.test(username)) {
    return NextResponse.json(
      { error: "아이디는 영문/숫자/밑줄로 3~20자여야 해요." },
      { status: 400 },
    )
  }
  if (password.length < 4) {
    return NextResponse.json({ error: "비밀번호는 4자 이상이어야 해요." }, { status: 400 })
  }
  const birthDate = new Date(birthDateRaw)
  if (Number.isNaN(birthDate.getTime())) {
    return NextResponse.json({ error: "생년월일 형식이 올바르지 않아요." }, { status: 400 })
  }

  const existing = await prisma.user.findFirst({ where: { OR: [{ email }, { username }] } })
  if (existing) {
    return NextResponse.json(
      { error: existing.username === username ? "이미 사용 중인 아이디예요." : "이미 가입된 이메일이에요." },
      { status: 409 },
    )
  }

  const passwordHash = await bcrypt.hash(password, 10)
  const user = await prisma.user.create({
    data: { name, username, email, birthDate, passwordHash },
  })
  await createSession(user.id)

  return NextResponse.json({
    user: { name: user.name, username: user.username, email: user.email, isAdmin: user.isAdmin },
  })
}
