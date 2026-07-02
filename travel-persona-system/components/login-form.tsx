"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { Compass, Eye, EyeOff } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Field, TextInput } from "@/components/admin/fields"
import { useAuth } from "@/lib/auth/store"
import { useSurvey } from "@/lib/survey/store"

type Mode = "login" | "signup"

export function LoginForm() {
  const router = useRouter()
  const { user, hydrated, login, signup } = useAuth()
  const { survey } = useSurvey()
  const [mode, setMode] = useState<Mode>("login")
  const [name, setName] = useState("")
  const [username, setUsername] = useState("")
  const [birthDate, setBirthDate] = useState("")
  const [identifier, setIdentifier] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // 이미 로그인된 경우 홈으로
  useEffect(() => {
    if (hydrated && user) router.replace("/")
  }, [hydrated, user, router])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (mode === "login") {
      if (!identifier.trim() || !password) {
        setError("아이디(또는 이메일)와 비밀번호를 입력해 주세요.")
        return
      }
    } else {
      if (!name.trim() || !username.trim() || !email.trim() || !birthDate || !password) {
        setError("이름, 생년월일, 이메일, 아이디, 비밀번호를 모두 입력해 주세요.")
        return
      }
      if (password.length < 4) {
        setError("비밀번호는 4자 이상이어야 해요.")
        return
      }
    }

    setSubmitting(true)
    const result =
      mode === "login"
        ? await login(identifier, password)
        : await signup({ name, username, email, birthDate, password })
    setSubmitting(false)
    if (!result.ok) {
      setError(result.error ?? "문제가 발생했어요.")
      return
    }
    router.push("/")
  }

  return (
    <div className="w-full max-w-md">
      <div className="mb-8 flex flex-col items-center text-center">
        <Link
          href="/"
          className="mb-5 flex size-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground"
          aria-label="홈으로"
        >
          <Compass className="size-6" />
        </Link>
        <h1 className="font-serif text-2xl font-bold tracking-tight text-balance">
          {mode === "login" ? "다시 오신 걸 환영해요" : "여행 성향 여정을 시작해요"}
        </h1>
        <p className="mt-2 text-sm text-pretty text-muted-foreground">
          {mode === "login"
            ? `${survey.title} 계정으로 로그인하세요.`
            : "간단히 가입하고 나의 여행 동물을 찾아보세요."}
        </p>
      </div>

      <div className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
        {/* 모드 전환 탭 */}
        <div className="mb-6 grid grid-cols-2 gap-1 rounded-full bg-muted p-1 text-sm">
          {(["login", "signup"] as Mode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => {
                setMode(m)
                setError(null)
              }}
              className={`rounded-full py-1.5 font-medium transition-colors ${
                mode === m ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {m === "login" ? "로그인" : "회원가입"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {mode === "signup" && (
            <>
              <Field label="이름">
                <TextInput
                  value={name}
                  autoComplete="name"
                  placeholder="홍길동"
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              <Field label="생년월일">
                <TextInput
                  type="date"
                  value={birthDate}
                  autoComplete="bday"
                  onChange={(e) => setBirthDate(e.target.value)}
                />
              </Field>
              <Field label="이메일">
                <TextInput
                  type="email"
                  value={email}
                  autoComplete="email"
                  placeholder="you@example.com"
                  onChange={(e) => setEmail(e.target.value)}
                />
              </Field>
              <Field label="아이디" hint="영문/숫자/밑줄 3~20자">
                <TextInput
                  value={username}
                  autoComplete="username"
                  placeholder="travel_lover"
                  onChange={(e) => setUsername(e.target.value)}
                />
              </Field>
            </>
          )}

          {mode === "login" && (
            <Field label="아이디 또는 이메일">
              <TextInput
                value={identifier}
                autoComplete="username"
                placeholder="아이디 또는 이메일"
                onChange={(e) => setIdentifier(e.target.value)}
              />
            </Field>
          )}

          <Field label="비밀번호">
            <div className="relative">
              <TextInput
                type={showPw ? "text" : "password"}
                value={password}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                placeholder="••••••••"
                className="pr-10"
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowPw((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-muted-foreground transition-colors hover:text-foreground"
                aria-label={showPw ? "비밀번호 숨기기" : "비밀번호 표시"}
              >
                {showPw ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          </Field>

          {error && (
            <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}

          <Button type="submit" size="lg" disabled={submitting} className="mt-1 w-full rounded-full">
            {submitting ? "처리 중…" : mode === "login" ? "로그인" : "가입하고 시작하기"}
          </Button>
        </form>
      </div>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        {mode === "login" ? "아직 계정이 없으신가요? " : "이미 계정이 있으신가요? "}
        <button
          type="button"
          onClick={() => {
            setMode(mode === "login" ? "signup" : "login")
            setError(null)
          }}
          className="font-medium text-foreground underline underline-offset-4 hover:opacity-70"
        >
          {mode === "login" ? "회원가입" : "로그인"}
        </button>
      </p>
    </div>
  )
}
