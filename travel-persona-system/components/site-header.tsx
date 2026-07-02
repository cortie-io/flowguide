"use client"

import Link from "next/link"
import { useEffect } from "react"
import { Compass } from "lucide-react"
import { HeaderAuth } from "@/components/header-auth"
import { useSurvey } from "@/lib/survey/store"
import { useAuth } from "@/lib/auth/store"

export function SiteHeader({ active }: { active?: "home" | "test" | "docs" | "admin" }) {
  const { survey } = useSurvey()
  const { user } = useAuth()

  // 편집된 사이트 제목을 브라우저 문서 제목에 동기화 (모든 페이지 공통)
  useEffect(() => {
    document.title = `${survey.title} · ${survey.subtitle}`
  }, [survey.title, survey.subtitle])

  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-5">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <Compass className="size-4" />
          </span>
          <span className="font-serif text-lg font-bold tracking-tight">{survey.title}</span>
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          <Link
            href="/"
            className={`rounded-full px-3 py-1.5 transition-colors hover:bg-muted ${
              active === "home" ? "text-foreground font-medium" : "text-muted-foreground"
            }`}
          >
            소개
          </Link>
          <Link
            href="/test"
            className={`rounded-full px-3 py-1.5 transition-colors hover:bg-muted ${
              active === "test" ? "text-foreground font-medium" : "text-muted-foreground"
            }`}
          >
            테스트
          </Link>
          {user?.isAdmin && (
            <Link
              href="/docs"
              className={`rounded-full px-3 py-1.5 transition-colors hover:bg-muted ${
                active === "docs" ? "text-foreground font-medium" : "text-muted-foreground"
              }`}
            >
              문서
            </Link>
          )}
          {user?.isAdmin && (
            <Link
              href="/admin"
              className={`rounded-full px-3 py-1.5 transition-colors hover:bg-muted ${
                active === "admin" ? "text-foreground font-medium" : "text-muted-foreground"
              }`}
            >
              관리자
            </Link>
          )}
          <span className="mx-1 hidden h-5 w-px bg-border sm:block" aria-hidden="true" />
          <HeaderAuth />
        </nav>
      </div>
    </header>
  )
}
