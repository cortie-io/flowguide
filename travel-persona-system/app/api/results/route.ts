import { NextResponse } from "next/server"
import { prisma } from "@/lib/db"
import { getSessionUser } from "@/lib/auth/session"

export async function POST(req: Request) {
  const body = await req.json().catch(() => null)
  const personaCode = typeof body?.personaCode === "string" ? body.personaCode : ""
  const answers = body?.answers

  if (!personaCode || !answers || typeof answers !== "object") {
    return NextResponse.json({ error: "결과 데이터 형식이 올바르지 않아요." }, { status: 400 })
  }

  const user = await getSessionUser()
  const result = await prisma.testResult.create({
    data: {
      personaCode,
      answers: JSON.stringify(answers),
      userId: user?.id ?? null,
    },
  })

  return NextResponse.json({ id: result.id, createdAt: result.createdAt })
}

export async function GET() {
  const user = await getSessionUser()
  if (!user) {
    return NextResponse.json({ error: "로그인이 필요해요." }, { status: 401 })
  }

  const results = await prisma.testResult.findMany({
    where: { userId: user.id },
    orderBy: { createdAt: "desc" },
    take: 20,
    select: { id: true, personaCode: true, createdAt: true },
  })

  return NextResponse.json({ results })
}
