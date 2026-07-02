import { NextResponse } from "next/server"
import { getSurvey, saveSurvey, isValidSurvey } from "@/lib/survey/repo"
import { getAdminUser } from "@/lib/auth/session"

export async function GET() {
  const survey = await getSurvey()
  return NextResponse.json({ survey })
}

export async function PUT(req: Request) {
  const user = await getAdminUser()
  if (!user) {
    return NextResponse.json({ error: "관리자만 수정할 수 있어요." }, { status: 403 })
  }

  const body = await req.json().catch(() => null)
  if (!isValidSurvey(body)) {
    return NextResponse.json({ error: "설문 데이터 형식이 올바르지 않아요." }, { status: 400 })
  }

  await saveSurvey(body)
  return NextResponse.json({ ok: true })
}
