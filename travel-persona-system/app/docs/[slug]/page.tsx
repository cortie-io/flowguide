"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import { SiteHeader } from "@/components/site-header"
import { MarkdownContent } from "@/components/docs/markdown"
import { Field, TextArea, TextInput } from "@/components/admin/fields"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/lib/auth/store"
import { ArrowLeft, LogIn, Pencil, Save, X } from "lucide-react"

interface Doc {
  slug: string
  title: string
  category: string
  content: string
  updatedAt: string
}

export default function DocDetailPage() {
  const params = useParams<{ slug: string }>()
  const router = useRouter()
  const { user, hydrated: authHydrated } = useAuth()

  const [doc, setDoc] = useState<Doc | null>(null)
  const [status, setStatus] = useState<"loading" | "ok" | "not-found" | "forbidden">("loading")
  const [editing, setEditing] = useState(false)
  const [draftTitle, setDraftTitle] = useState("")
  const [draftContent, setDraftContent] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setStatus("loading")
    fetch(`/api/docs/${params.slug}`)
      .then(async (res) => {
        const data = await res.json().catch(() => null)
        return { ok: res.ok, status: res.status, data }
      })
      .then(({ ok, status: httpStatus, data }) => {
        if (cancelled) return
        if (httpStatus === 403) {
          setStatus("forbidden")
          return
        }
        if (!ok || !data?.doc) {
          setStatus("not-found")
          return
        }
        setDoc(data.doc)
        setDraftTitle(data.doc.title)
        setDraftContent(data.doc.content)
        setStatus("ok")
      })
      .catch(() => {
        if (!cancelled) setStatus("not-found")
      })
    return () => {
      cancelled = true
    }
  }, [params.slug])

  function startEdit() {
    if (!doc) return
    setDraftTitle(doc.title)
    setDraftContent(doc.content)
    setError(null)
    setEditing(true)
  }

  async function save() {
    if (!doc) return
    setSaving(true)
    setError(null)
    try {
      const res = await fetch(`/api/docs/${doc.slug}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: draftTitle, content: draftContent }),
      })
      const data = await res.json().catch(() => null)
      if (!res.ok) {
        setError(data?.error ?? "저장에 실패했어요.")
        return
      }
      setDoc(data.doc)
      setEditing(false)
    } catch {
      setError("저장에 실패했어요.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen">
      <SiteHeader active="docs" />
      <div className="mx-auto max-w-3xl px-5 pb-24 pt-8">
        <Button
          render={<Link href="/docs" />}
          nativeButton={false}
          variant="ghost"
          size="sm"
          className="gap-1.5 rounded-full text-muted-foreground"
        >
          <ArrowLeft className="size-3.5" aria-hidden="true" />
          문서 목록
        </Button>

        {status === "loading" && (
          <div className="flex min-h-[40vh] items-center justify-center text-muted-foreground">불러오는 중…</div>
        )}

        {status === "not-found" && (
          <div className="mx-auto max-w-lg px-5 py-24 text-center">
            <h1 className="font-serif text-2xl font-bold">문서를 찾을 수 없어요</h1>
            <Button render={<Link href="/docs" />} nativeButton={false} className="mt-6 rounded-full">
              문서 목록으로
            </Button>
          </div>
        )}

        {status === "forbidden" && (
          <div className="mx-auto max-w-lg px-5 py-24 text-center">
            <h1 className="font-serif text-2xl font-bold">권한이 없어요</h1>
            <p className="mt-2 text-muted-foreground">문서는 관리자 계정만 볼 수 있어요.</p>
            <Button render={<Link href="/login" />} nativeButton={false} className="mt-6 gap-2 rounded-full">
              <LogIn className="size-4" aria-hidden="true" />
              로그인하러 가기
            </Button>
          </div>
        )}

        {status === "ok" && doc && (
          <div className="mt-4 rounded-3xl border border-border bg-card p-6 sm:p-8">
            {!editing ? (
              <>
                <div className="flex items-start justify-between gap-4">
                  <h1 className="text-balance font-serif text-3xl font-bold">{doc.title}</h1>
                  {authHydrated && user?.isAdmin && (
                    <Button
                      onClick={startEdit}
                      variant="outline"
                      size="sm"
                      className="shrink-0 gap-1.5 rounded-full bg-transparent"
                    >
                      <Pencil className="size-3.5" aria-hidden="true" />
                      편집
                    </Button>
                  )}
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  마지막 수정: {new Date(doc.updatedAt).toLocaleString("ko-KR")}
                </div>
                <div className="mt-6">
                  <MarkdownContent content={doc.content} />
                </div>
              </>
            ) : (
              <div className="flex flex-col gap-4">
                <Field label="제목">
                  <TextInput value={draftTitle} onChange={(e) => setDraftTitle(e.target.value)} />
                </Field>
                <Field label="본문 (Markdown)">
                  <TextArea
                    value={draftContent}
                    onChange={(e) => setDraftContent(e.target.value)}
                    rows={28}
                    className="font-mono text-xs leading-relaxed"
                  />
                </Field>
                {error && (
                  <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
                    {error}
                  </p>
                )}
                <div className="flex gap-2">
                  <Button onClick={save} disabled={saving} className="gap-1.5 rounded-full">
                    <Save className="size-3.5" aria-hidden="true" />
                    {saving ? "저장 중…" : "저장"}
                  </Button>
                  <Button
                    onClick={() => setEditing(false)}
                    variant="outline"
                    disabled={saving}
                    className="gap-1.5 rounded-full bg-transparent"
                  >
                    <X className="size-3.5" aria-hidden="true" />
                    취소
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
