import { NextResponse } from "next/server"
import { resetSurvey } from "@/lib/survey/repo"
import { getAdminUser } from "@/lib/auth/session"

export async function POST() {
  const user = await getAdminUser()
  if (!user) {
    return NextResponse.json({ error: "관리자만 초기화할 수 있어요." }, { status: 403 })
  }

  const survey = await resetSurvey()
  return NextResponse.json({ survey })
}
