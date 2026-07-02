"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useRef, useState } from "react"
import { LogOut, User as UserIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/lib/auth/store"
import { cn } from "@/lib/utils"

export function HeaderAuth() {
  const { user, hydrated, logout } = useAuth()
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", onClick)
    return () => document.removeEventListener("mousedown", onClick)
  }, [])

  // 하이드레이션 전에는 자리만 잡아 레이아웃 시프트를 방지
  if (!hydrated) {
    return <div className="h-9 w-20 rounded-full bg-muted/60" aria-hidden="true" />
  }

  if (!user) {
    return (
      <Button
        render={<Link href="/login" />}
        nativeButton={false}
        size="sm"
        className="rounded-full"
      >
        로그인
      </Button>
    )
  }

  const initial = user.name?.[0]?.toUpperCase() || user.email?.[0]?.toUpperCase() || user.username[0]?.toUpperCase() || "U"

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-full border border-border bg-card py-1 pl-1 pr-3 text-sm transition-colors hover:bg-muted"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <span className="flex size-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
          {initial}
        </span>
        <span className="hidden max-w-24 truncate font-medium sm:inline">{user.name || "사용자"}</span>
      </button>

      <div
        role="menu"
        className={cn(
          "absolute right-0 top-full z-50 mt-2 w-56 origin-top-right rounded-xl border border-border bg-popover p-1.5 shadow-lg transition-all",
          open ? "visible scale-100 opacity-100" : "invisible scale-95 opacity-0",
        )}
      >
        <div className="flex items-center gap-2 rounded-lg px-2.5 py-2">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
            {initial}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{user.name || "사용자"}</p>
            <p className="truncate text-xs text-muted-foreground">{user.email || `@${user.username}`}</p>
          </div>
        </div>
        <div className="my-1 h-px bg-border" />
        {user.isAdmin && (
          <Link
            href="/admin"
            role="menuitem"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm transition-colors hover:bg-muted"
          >
            <UserIcon className="size-4 text-muted-foreground" />
            테스트 관리
          </Link>
        )}
        <button
          type="button"
          role="menuitem"
          onClick={() => {
            logout()
            setOpen(false)
            router.push("/")
          }}
          className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm text-destructive transition-colors hover:bg-destructive/10"
        >
          <LogOut className="size-4" />
          로그아웃
        </button>
      </div>
    </div>
  )
}
