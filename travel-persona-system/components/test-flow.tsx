"use client"

import { useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { useSurvey } from "@/lib/survey/store"
import { useAuth } from "@/lib/auth/store"
import { answerKey } from "@/lib/survey/scoring"
import type { Question, Section } from "@/lib/survey/types"
import { QuestionField } from "@/components/question-field"
import { Button } from "@/components/ui/button"
import { ArrowLeft, ArrowRight, Check } from "lucide-react"
import { cn } from "@/lib/utils"

interface Step {
  section: Section
  questions: Question[]
}

export function TestFlow() {
  const router = useRouter()
  const { survey, answers, setAnswer, hydrated } = useSurvey()
  const { user } = useAuth()
  const [stepIndex, setStepIndex] = useState(0)

  const steps = useMemo<Step[]>(() => {
    return survey.sections
      .map((section) => ({
        section,
        questions: survey.questions.filter((q) => q.sectionId === section.id),
      }))
      .filter((s) => s.questions.length > 0)
  }, [survey])

  const totalQuestions = survey.questions.length
  const answeredCount = survey.questions.filter((q) => {
    const v = answers[answerKey(q)]
    return v !== null && v !== undefined && !(Array.isArray(v) && v.length === 0) && v !== ""
  }).length
  const progress = totalQuestions === 0 ? 0 : Math.round((answeredCount / totalQuestions) * 100)

  if (!hydrated) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-muted-foreground">불러오는 중…</div>
    )
  }

  if (steps.length === 0) {
    return (
      <div className="mx-auto max-w-lg px-5 py-24 text-center">
        <p className="text-muted-foreground">문항이 없습니다. 관리자 페이지에서 문항을 추가하세요.</p>
        {user?.isAdmin && (
          <Button render={<Link href="/admin" />} nativeButton={false} className="mt-4 rounded-full">
            테스트 편집으로 이동
          </Button>
        )}
      </div>
    )
  }

  const step = steps[stepIndex]
  const isFirst = stepIndex === 0
  const isLast = stepIndex === steps.length - 1

  // 현재 섹션 필수(part A likert 또는 required) 응답 여부
  const requiredUnanswered = step.questions.filter((q) => {
    const needed = q.required || q.part === "A"
    if (!needed) return false
    const v = answers[answerKey(q)]
    return v === null || v === undefined || v === "" || (Array.isArray(v) && v.length === 0)
  })
  const canProceed = requiredUnanswered.length === 0

  function goNext() {
    if (isLast) {
      router.push("/result")
      return
    }
    setStepIndex((i) => Math.min(i + 1, steps.length - 1))
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  function goPrev() {
    setStepIndex((i) => Math.max(i - 1, 0))
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  const partLabel: Record<string, string> = { A: "성향진단", B: "취향프로필", C: "이번여행" }

  return (
    <div className="mx-auto max-w-2xl px-5 pb-32 pt-8">
      {/* Progress bar */}
      <div className="sticky top-0 z-10 -mx-5 mb-8 bg-background/85 px-5 py-4 backdrop-blur">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="font-medium text-muted-foreground">
            {partLabel[step.section.part]} · {stepIndex + 1}/{steps.length} 섹션
          </span>
          <span className="font-mono text-muted-foreground">{progress}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
        {/* Step dots */}
        <div className="mt-3 flex flex-wrap gap-1.5">
          {steps.map((s, i) => (
            <button
              key={s.section.id}
              type="button"
              onClick={() => setStepIndex(i)}
              aria-label={`${s.section.title}로 이동`}
              className={cn(
                "h-1.5 flex-1 rounded-full transition-colors",
                i === stepIndex ? "bg-primary" : i < stepIndex ? "bg-primary/40" : "bg-muted",
              )}
            />
          ))}
        </div>
      </div>

      {/* Section header */}
      <div className="mb-8">
        <p className="font-mono text-xs uppercase tracking-wider text-primary">
          Part {step.section.part} · {partLabel[step.section.part]}
        </p>
        <h1 className="mt-1 text-balance font-serif text-3xl font-bold">{step.section.title}</h1>
        {step.section.description && (
          <p className="mt-2 text-pretty leading-relaxed text-muted-foreground">{step.section.description}</p>
        )}
      </div>

      {/* Questions */}
      <div className="flex flex-col gap-8">
        {step.questions.map((q, idx) => {
          const missing = requiredUnanswered.includes(q)
          return (
            <div key={q.id} className="scroll-mt-40">
              <div className="mb-3 flex items-start gap-3">
                <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-secondary font-mono text-xs font-bold text-secondary-foreground">
                  {idx + 1}
                </span>
                <div>
                  <p className="text-pretty text-lg font-medium leading-snug">
                    {q.text}
                    {(q.required || q.part === "A") && <span className="ml-1 text-primary">*</span>}
                  </p>
                  {q.helpText && <p className="mt-1 text-sm text-muted-foreground">{q.helpText}</p>}
                  {q.conditional && q.conditionNote && (
                    <p className="mt-1 text-xs text-accent">{q.conditionNote}</p>
                  )}
                </div>
              </div>
              <div className="pl-9">
                <QuestionField
                  question={q}
                  value={answers[answerKey(q)] ?? null}
                  onChange={(v) => setAnswer(answerKey(q), v)}
                />
                {missing && <p className="mt-2 text-xs text-destructive">이 문항에 응답해 주세요.</p>}
              </div>
            </div>
          )
        })}
      </div>

      {/* Nav */}
      <div className="fixed inset-x-0 bottom-0 z-10 border-t border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex max-w-2xl items-center justify-between gap-3 px-5 py-4">
          <Button variant="ghost" onClick={goPrev} disabled={isFirst} className="gap-2 rounded-full">
            <ArrowLeft className="size-4" aria-hidden="true" />
            이전
          </Button>
          <Button onClick={goNext} disabled={!canProceed} className="gap-2 rounded-full px-6">
            {isLast ? (
              <>
                결과 보기
                <Check className="size-4" aria-hidden="true" />
              </>
            ) : (
              <>
                다음
                <ArrowRight className="size-4" aria-hidden="true" />
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
