import Link from "next/link"
import { SiteHeader } from "@/components/site-header"
import { listDocs } from "@/lib/docs/repo"
import { getAdminUser } from "@/lib/auth/session"
import { Button } from "@/components/ui/button"
import { BookOpen, Compass, LogIn } from "lucide-react"

export const dynamic = "force-dynamic"

const CATEGORY_LABEL: Record<string, string> = {
  guide: "설계 가이드",
  type: "유형별 가이드",
}

export default async function DocsPage() {
  const admin = await getAdminUser()

  if (!admin) {
    return (
      <div className="min-h-screen">
        <SiteHeader active="docs" />
        <div className="mx-auto max-w-lg px-5 py-24 text-center">
          <h1 className="font-serif text-2xl font-bold">권한이 없어요</h1>
          <p className="mt-2 text-muted-foreground">문서는 관리자 계정만 볼 수 있어요.</p>
          <Button render={<Link href="/login" />} nativeButton={false} className="mt-6 gap-2 rounded-full">
            <LogIn className="size-4" aria-hidden="true" />
            로그인하러 가기
          </Button>
        </div>
      </div>
    )
  }

  const docs = await listDocs()
  const groups = new Map<string, typeof docs>()
  for (const doc of docs) {
    const list = groups.get(doc.category) ?? []
    list.push(doc)
    groups.set(doc.category, list)
  }

  return (
    <div className="min-h-screen">
      <SiteHeader active="docs" />
      <div className="mx-auto max-w-4xl px-5 pb-24 pt-10">
        <p className="font-mono text-xs uppercase tracking-wider text-primary">Docs</p>
        <h1 className="mt-1 font-serif text-3xl font-bold">문서</h1>
        <p className="mt-2 text-muted-foreground">설문 설계 문서와 16개 유형별 상세 가이드예요.</p>

        {docs.length === 0 && (
          <p className="mt-10 rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
            아직 등록된 문서가 없어요.
          </p>
        )}

        {["guide", "type"].map((category) => {
          const list = groups.get(category)
          if (!list || list.length === 0) return null
          return (
            <section key={category} className="mt-10">
              <div className="flex items-center gap-2">
                {category === "guide" ? (
                  <BookOpen className="size-5 text-primary" aria-hidden="true" />
                ) : (
                  <Compass className="size-5 text-primary" aria-hidden="true" />
                )}
                <h2 className="font-serif text-xl font-bold">{CATEGORY_LABEL[category] ?? category}</h2>
                <span className="rounded-full bg-muted px-2 py-0.5 font-mono text-xs text-muted-foreground">
                  {list.length}
                </span>
              </div>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {list.map((doc) => (
                  <Link
                    key={doc.slug}
                    href={`/docs/${doc.slug}`}
                    className="rounded-xl border border-border bg-card px-4 py-3 text-sm transition-colors hover:border-primary/50 hover:bg-secondary/40"
                  >
                    <p className="font-medium leading-snug">{doc.title}</p>
                  </Link>
                ))}
              </div>
            </section>
          )
        })}
      </div>
    </div>
  )
}
