import { NextResponse } from "next/server"
import { listDocs, createDoc, getDoc } from "@/lib/docs/repo"
import { getAdminUser } from "@/lib/auth/session"

export async function GET() {
  const user = await getAdminUser()
  if (!user) {
    return NextResponse.json({ error: "관리자만 볼 수 있어요." }, { status: 403 })
  }

  const docs = await listDocs()
  return NextResponse.json({ docs })
}

export async function POST(req: Request) {
  const user = await getAdminUser()
  if (!user) {
    return NextResponse.json({ error: "관리자만 문서를 추가할 수 있어요." }, { status: 403 })
  }

  const body = await req.json().catch(() => null)
  const slug = typeof body?.slug === "string" ? body.slug.trim() : ""
  const title = typeof body?.title === "string" ? body.title.trim() : ""
  const category = typeof body?.category === "string" ? body.category.trim() : ""
  const content = typeof body?.content === "string" ? body.content : ""

  if (!slug || !title || !category) {
    return NextResponse.json({ error: "slug, title, category를 입력해 주세요." }, { status: 400 })
  }
  if (!/^[a-z0-9-]+$/.test(slug)) {
    return NextResponse.json({ error: "slug는 영문 소문자/숫자/하이픈만 사용할 수 있어요." }, { status: 400 })
  }

  const existing = await getDoc(slug)
  if (existing) {
    return NextResponse.json({ error: "이미 사용 중인 slug예요." }, { status: 409 })
  }

  const doc = await createDoc({ slug, title, category, content })
  return NextResponse.json({ doc })
}
