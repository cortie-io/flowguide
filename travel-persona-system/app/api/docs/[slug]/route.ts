import { NextResponse } from "next/server"
import { getDoc, updateDoc, deleteDoc } from "@/lib/docs/repo"
import { getAdminUser } from "@/lib/auth/session"

export async function GET(_req: Request, { params }: { params: Promise<{ slug: string }> }) {
  const user = await getAdminUser()
  if (!user) {
    return NextResponse.json({ error: "관리자만 볼 수 있어요." }, { status: 403 })
  }

  const { slug } = await params
  const doc = await getDoc(slug)
  if (!doc) {
    return NextResponse.json({ error: "문서를 찾을 수 없어요." }, { status: 404 })
  }
  return NextResponse.json({ doc })
}

export async function PUT(req: Request, { params }: { params: Promise<{ slug: string }> }) {
  const user = await getAdminUser()
  if (!user) {
    return NextResponse.json({ error: "관리자만 수정할 수 있어요." }, { status: 403 })
  }

  const { slug } = await params
  const existing = await getDoc(slug)
  if (!existing) {
    return NextResponse.json({ error: "문서를 찾을 수 없어요." }, { status: 404 })
  }

  const body = await req.json().catch(() => null)
  const patch: Partial<{ title: string; content: string; category: string; order: number }> = {}
  if (typeof body?.title === "string") patch.title = body.title.trim()
  if (typeof body?.content === "string") patch.content = body.content
  if (typeof body?.category === "string") patch.category = body.category.trim()
  if (typeof body?.order === "number") patch.order = body.order

  const doc = await updateDoc(slug, patch)
  return NextResponse.json({ doc })
}

export async function DELETE(_req: Request, { params }: { params: Promise<{ slug: string }> }) {
  const user = await getAdminUser()
  if (!user) {
    return NextResponse.json({ error: "관리자만 삭제할 수 있어요." }, { status: 403 })
  }

  const { slug } = await params
  const existing = await getDoc(slug)
  if (!existing) {
    return NextResponse.json({ error: "문서를 찾을 수 없어요." }, { status: 404 })
  }

  await deleteDoc(slug)
  return NextResponse.json({ ok: true })
}
