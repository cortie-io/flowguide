"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { useSurvey } from "@/lib/survey/store"
import { useAuth } from "@/lib/auth/store"
import {
  computeAxisScores,
  computeWeights,
  effectivePersonaCode,
  personaCode,
  findPersona,
  oppositeCode,
  partACompletion,
} from "@/lib/survey/scoring"
import type { AxisScore } from "@/lib/survey/scoring"
import { Button } from "@/components/ui/button"
import { RotateCcw, Home, SlidersHorizontal, BookOpen } from "lucide-react"
import { cn } from "@/lib/utils"

interface ResultHistoryItem {
  id: string
  personaCode: string
  createdAt: string
}

export function ResultView() {
  const { survey, answers, hydrated, clearAnswers } = useSurvey()
  const { user, hydrated: authHydrated } = useAuth()
  const searchParams = useSearchParams()
  const savedForCode = useRef<string | null>(null)
  const [history, setHistory] = useState<ResultHistoryItem[]>([])

  // 관리자는 ?type=SAEF 같은 코드로 실제 테스트 없이 특정 유형의 결과 화면을 미리볼 수 있다
  const previewParam = searchParams.get("type")?.toUpperCase() ?? null
  const previewPersona = previewParam ? findPersona(survey, previewParam) : undefined
  const isPreview = Boolean(user?.isAdmin && previewPersona)

  const data = useMemo(() => {
    if (isPreview && previewPersona) {
      const scores: AxisScore[] = survey.axes.map((axis, i) => {
        const letter = previewPersona.code[i]
        const effective = letter === axis.highCode ? 0.75 : 0.25
        return { axis, score: effective, effective, code: letter, overridden: false, answeredCount: 0 }
      })
      const weights = computeWeights(survey, scores, previewPersona)
      return {
        scores,
        baseCode: previewPersona.code,
        effCode: previewPersona.code,
        weights,
        persona: previewPersona,
        basePersona: previewPersona,
        opposite: findPersona(survey, oppositeCode(survey, scores)),
        completion: 1,
        overridden: false,
      }
    }
    const scores = computeAxisScores(survey, answers)
    const baseCode = personaCode(scores)
    const effCode = effectivePersonaCode(scores, survey)
    const persona = findPersona(survey, effCode)
    const weights = computeWeights(survey, scores, persona)
    return {
      scores,
      baseCode,
      effCode,
      weights,
      persona,
      basePersona: findPersona(survey, baseCode),
      opposite: findPersona(survey, oppositeCode(survey, scores)),
      completion: partACompletion(survey, answers),
      overridden: effCode !== baseCode,
    }
  }, [survey, answers, isPreview, previewPersona])

  // 결과가 나오면 한 번만 서버(DB)에 저장한다 (로그인 상태면 계정에 연결됨) — 미리보기는 저장하지 않는다
  useEffect(() => {
    if (isPreview) return
    if (!hydrated || !authHydrated) return
    if (data.completion === 0) return
    if (savedForCode.current === data.effCode) return
    savedForCode.current = data.effCode

    fetch("/api/results", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ personaCode: data.effCode, answers }),
    }).catch(() => {
      // ignore
    })
  }, [isPreview, hydrated, authHydrated, data.completion, data.effCode, answers])

  // 로그인 상태면 최근 결과 기록을 불러온다 (미리보기 중에는 불러오지 않는다)
  useEffect(() => {
    if (isPreview || !authHydrated || !user) {
      setHistory([])
      return
    }
    let cancelled = false
    fetch("/api/results")
      .then((res) => res.json())
      .then((res) => {
        if (!cancelled && Array.isArray(res.results)) setHistory(res.results)
      })
      .catch(() => {
        // ignore
      })
    return () => {
      cancelled = true
    }
  }, [isPreview, authHydrated, user, data.effCode])

  if (!hydrated) {
    return <div className="flex min-h-[60vh] items-center justify-center text-muted-foreground">불러오는 중…</div>
  }

  if (!isPreview && data.completion === 0) {
    return (
      <div className="mx-auto max-w-lg px-5 py-24 text-center">
        <h1 className="font-serif text-2xl font-bold">아직 결과가 없어요</h1>
        <p className="mt-2 text-muted-foreground">먼저 성향 테스트를 진행해 주세요.</p>
        <Button render={<Link href="/test" />} nativeButton={false} className="mt-6 rounded-full">
          테스트 시작하기
        </Button>
      </div>
    )
  }

  const maxWeight = Math.max(...data.weights.map((w) => w.value), 1)

  return (
    <div className="mx-auto max-w-3xl px-5 pb-24 pt-10">
      {isPreview && (
        <div className="mb-4 rounded-2xl border border-primary/30 bg-primary/5 px-4 py-3 text-center text-sm text-muted-foreground">
          미리보기 모드예요 — 실제 진단 결과가 아니라 <span className="font-medium text-foreground">{data.persona?.code}</span> 유형의
          결과 화면 예시입니다.
        </div>
      )}
      {/* Persona hero card */}
      <div className="overflow-hidden rounded-3xl border border-border bg-card shadow-sm">
        <div className="bg-primary px-6 py-10 text-center text-primary-foreground">
          <p className="font-mono text-sm tracking-widest opacity-90">{data.effCode}</p>
          <h1 className="mt-2 text-balance font-serif text-4xl font-bold md:text-5xl">
            {data.persona ? data.persona.name : "미확인 유형"}
          </h1>
          {data.persona && <p className="mt-3 text-pretty text-base opacity-95">{data.persona.tag}</p>}
          {data.persona?.motto && (
            <p className="mt-4 text-pretty font-serif text-lg italic opacity-90">&ldquo;{data.persona.motto}&rdquo;</p>
          )}
        </div>
        <div className="grid grid-cols-2 divide-x divide-border border-t border-border text-center">
          <div className="px-4 py-4">
            <p className="text-xs text-muted-foreground">완료율 (성향진단)</p>
            <p className="font-serif text-xl font-bold">{Math.round(data.completion * 100)}%</p>
          </div>
          <div className="px-4 py-4">
            <p className="text-xs text-muted-foreground">정반대 유형</p>
            <p className="font-serif text-xl font-bold">{data.opposite ? data.opposite.name : "-"}</p>
          </div>
        </div>
      </div>

      {data.overridden && data.basePersona && (
        <div className="mt-4 rounded-2xl border border-accent/40 bg-accent/10 px-4 py-3 text-sm">
          <span className="font-medium text-accent-foreground">이번 여행</span> 응답을 반영한 결과예요. 평소 유형은{" "}
          <span className="font-bold">{data.basePersona.name}</span> ({data.baseCode}) 입니다.
        </div>
      )}

      {/* Persona explanation */}
      {data.persona && (data.persona.description || data.persona.strengths?.length || data.persona.tips?.length) && (
        <section className="mt-6 rounded-3xl border border-border bg-card p-6">
          <div className="flex items-start justify-between gap-4">
            <h2 className="font-serif text-2xl font-bold">유형 해설</h2>
            {data.persona.docSlug && user?.isAdmin && (
              <Button
                render={<Link href={`/docs/${data.persona.docSlug}`} />}
                nativeButton={false}
                variant="outline"
                size="sm"
                className="shrink-0 gap-1.5 rounded-full bg-transparent"
              >
                <BookOpen className="size-3.5" aria-hidden="true" />이 유형 자세히 보기
              </Button>
            )}
          </div>
          {data.persona.description && (
            <div className="mt-3 flex flex-col gap-3">
              {data.persona.description.split("\n\n").map((para, i) => (
                <p key={i} className="text-pretty leading-relaxed text-muted-foreground">
                  {para}
                </p>
              ))}
            </div>
          )}
          {data.persona.strengths && data.persona.strengths.length > 0 && (
            <div className="mt-5">
              <p className="text-sm font-medium">이런 점이 강해요</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {data.persona.strengths.map((s, i) => (
                  <span
                    key={i}
                    className="rounded-full border border-border bg-secondary px-3 py-1 text-sm text-secondary-foreground"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
          {data.persona.tips && data.persona.tips.length > 0 && (
            <div className="mt-5">
              <p className="text-sm font-medium">여행 팁</p>
              <ul className="mt-2 flex flex-col gap-2">
                {data.persona.tips.map((t, i) => (
                  <li key={i} className="flex gap-2 text-sm leading-relaxed text-muted-foreground">
                    <span className="mt-0.5 select-none font-mono text-xs text-foreground">{String(i + 1).padStart(2, "0")}</span>
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {data.persona.companions && data.persona.companions.length > 0 && (
            <div className="mt-5">
              <p className="text-sm font-medium">동행자에 따라 달라지는 모습</p>
              <div className="mt-2 flex flex-col gap-2">
                {data.persona.companions.map((c, i) => (
                  <div key={i} className="rounded-xl bg-secondary/40 px-3 py-2 text-sm">
                    <span className="font-medium">{c.label}</span>
                    <span className="text-muted-foreground"> — {c.text}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {data.persona.catchphrases && data.persona.catchphrases.length > 0 && (
            <div className="mt-5">
              <p className="text-sm font-medium">이 유형이 자주 하는 말</p>
              <div className="mt-2 flex flex-col gap-1.5">
                {data.persona.catchphrases.map((c, i) => (
                  <p key={i} className="text-sm italic text-muted-foreground">
                    &ldquo;{c}&rdquo;
                  </p>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* Axis scores */}
      <section className="mt-10">
        <h2 className="font-serif text-2xl font-bold">4개 축 점수</h2>
        <div className="mt-5 flex flex-col gap-6">
          {data.scores.map((s) => {
            const pct = Math.round(s.effective * 100)
            const color = `var(${s.axis.colorVar})`
            return (
              <div key={s.axis.id}>
                <div className="mb-1.5 flex items-center justify-between text-sm">
                  <span className={cn(pct < 50 ? "font-bold" : "text-muted-foreground")}>
                    {s.axis.lowLabel} ({s.axis.lowCode})
                  </span>
                  <span className="font-serif text-base font-bold">{s.axis.name}</span>
                  <span className={cn(pct >= 50 ? "font-bold" : "text-muted-foreground")}>
                    {s.axis.highLabel} ({s.axis.highCode})
                  </span>
                </div>
                <div className="relative h-3 overflow-hidden rounded-full bg-muted">
                  <div className="absolute inset-y-0 left-1/2 w-px bg-border" />
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${pct}%`, backgroundColor: color }}
                  />
                </div>
                <div className="mt-1 flex justify-between text-xs text-muted-foreground">
                  <span>{100 - pct}%</span>
                  {s.overridden && <span className="text-accent">이번 여행 반영</span>}
                  <span>{pct}%</span>
                </div>
              </div>
            )
          })}
        </div>
      </section>

      {/* Weight profile */}
      {data.weights.length > 0 && (
        <section className="mt-10">
          <h2 className="font-serif text-2xl font-bold">추천 가중치 프로필</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            여행 추천에 사용되는 가중치예요. 공식: base + k × (축점수 − {(survey.scoring?.weightPivot ?? 0.5)})
          </p>
          <div className="mt-5 flex flex-col gap-4">
            {data.weights.map((w) => (
              <div key={w.id}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="font-medium">
                    {w.label}
                    {w.overridden && (
                      <span className="ml-2 rounded-full bg-foreground px-1.5 py-0.5 font-mono text-[10px] text-background">
                        유형 조정
                      </span>
                    )}
                  </span>
                  <span className="font-mono text-muted-foreground">{w.value.toFixed(2)}</span>
                </div>
                <div className="h-2.5 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-secondary-foreground/70 transition-all"
                    style={{ width: `${(w.value / maxWeight) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 최근 결과 기록 (로그인 시) */}
      {user && history.length > 0 && (
        <section className="mt-10">
          <h2 className="font-serif text-2xl font-bold">최근 결과 기록</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {user.name || user.email || user.username} 계정에 저장된 지난 결과예요.
          </p>
          <div className="mt-5 flex flex-col gap-2">
            {history.map((h) => {
              const p = findPersona(survey, h.personaCode)
              return (
                <div
                  key={h.id}
                  className="flex items-center justify-between rounded-xl border border-border bg-card px-4 py-3 text-sm"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs font-bold text-primary">{h.personaCode}</span>
                    <span className="font-medium">{p ? p.name : "미확인 유형"}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {new Date(h.createdAt).toLocaleString("ko-KR")}
                  </span>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* Actions */}
      <div className="mt-12 flex flex-wrap gap-3">
        <Button
          render={<Link href="/" />}
          nativeButton={false}
          variant="outline"
          className="gap-2 rounded-full bg-transparent"
        >
          <Home className="size-4" aria-hidden="true" />
          홈으로
        </Button>
        <Button
          render={<Link href="/test" />}
          nativeButton={false}
          variant="outline"
          className="gap-2 rounded-full bg-transparent"
          onClick={() => {
            if (!isPreview) clearAnswers()
          }}
        >
          <RotateCcw className="size-4" aria-hidden="true" />
          다시 하기
        </Button>
        {user?.isAdmin && (
          <Button render={<Link href="/admin" />} nativeButton={false} className="gap-2 rounded-full">
            <SlidersHorizontal className="size-4" aria-hidden="true" />
            테스트 편집
          </Button>
        )}
      </div>
    </div>
  )
}
