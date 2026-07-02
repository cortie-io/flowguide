"use client"

import Link from "next/link"
import Image from "next/image"
import { SiteHeader } from "@/components/site-header"
import { Button } from "@/components/ui/button"
import { useSurvey } from "@/lib/survey/store"
import { useAuth } from "@/lib/auth/store"
import { ArrowRight, Compass, Sparkles, SlidersHorizontal, PenLine } from "lucide-react"

export default function Page() {
  const { survey } = useSurvey()
  const { user } = useAuth()
  const partA = survey.questions.filter((q) => q.part === "A").length
  const partB = survey.questions.filter((q) => q.part === "B").length
  const partC = survey.questions.filter((q) => q.part === "C").length

  return (
    <div className="min-h-screen">
      <SiteHeader active="home" />

      {/* Hero */}
      <section className="mx-auto grid max-w-6xl items-center gap-10 px-5 pb-16 pt-10 md:grid-cols-2 md:gap-12 md:pb-24 md:pt-16">
        <div className="flex flex-col items-start gap-6">
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-sm font-medium text-muted-foreground">
            <Sparkles className="size-4 text-primary" aria-hidden="true" />
            여행자를 위한 성향 진단
          </span>
          <h1 className="text-balance font-serif text-4xl font-bold leading-tight tracking-tight md:text-6xl">
            {survey.subtitle}
          </h1>
          <p className="max-w-md text-pretty text-base leading-relaxed text-muted-foreground md:text-lg">
            {survey.axes.length}개의 축으로 나의 여행 스타일을 진단하고, {survey.personas.length}가지 여행 동물 중 나의
            페르소나를 찾아보세요.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Button render={<Link href="/test" />} nativeButton={false} size="lg" className="gap-2 rounded-full">
              테스트 시작하기
              <ArrowRight className="size-4" aria-hidden="true" />
            </Button>
            {user?.isAdmin && (
              <Button
                render={<Link href="/admin" />}
                nativeButton={false}
                size="lg"
                variant="outline"
                className="gap-2 rounded-full bg-transparent"
              >
                <SlidersHorizontal className="size-4" aria-hidden="true" />
                테스트 편집
              </Button>
            )}
          </div>
          <dl className="mt-2 flex flex-wrap gap-6 text-sm">
            <div>
              <dt className="text-muted-foreground">성향진단</dt>
              <dd className="font-serif text-2xl font-bold">{partA}문항</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">취향프로필</dt>
              <dd className="font-serif text-2xl font-bold">{partB}문항</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">이번여행</dt>
              <dd className="font-serif text-2xl font-bold">{partC}문항</dd>
            </div>
          </dl>
        </div>

        <div className="relative">
          <div className="overflow-hidden rounded-3xl border border-border bg-card shadow-sm">
            <Image
              src="/hero-travel.png"
              alt="언덕과 굽이진 길, 여행 가방과 지도가 있는 따뜻한 여행 일러스트"
              width={720}
              height={720}
              className="h-full w-full object-cover"
              priority
            />
          </div>
        </div>
      </section>

      {/* Axes */}
      <section className="border-t border-border bg-card/50">
        <div className="mx-auto max-w-6xl px-5 py-16">
          <h2 className="font-serif text-2xl font-bold md:text-3xl">{survey.axes.length}개의 여행 축</h2>
          <p className="mt-2 max-w-lg text-pretty text-muted-foreground">
            각 축의 양 끝 사이에서 당신의 위치를 찾아, {survey.axes.length}글자 코드로 이루어진 유형을 만들어요.
          </p>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {survey.axes.map((axis) => (
              <div
                key={axis.id}
                className="rounded-2xl border border-border bg-background p-5"
                style={{ borderTopColor: `var(${axis.colorVar})`, borderTopWidth: 3 }}
              >
                <p className="font-serif text-lg font-bold">{axis.name}</p>
                <div className="mt-3 flex items-center justify-between text-sm text-muted-foreground">
                  <span>{axis.lowLabel}</span>
                  <span>{axis.highLabel}</span>
                </div>
                <div className="mt-2 flex items-center justify-between font-mono text-xs">
                  <span
                    className="rounded-md px-2 py-0.5 font-bold text-primary-foreground"
                    style={{ backgroundColor: `var(${axis.colorVar})` }}
                  >
                    {axis.lowCode}
                  </span>
                  <span
                    className="rounded-md px-2 py-0.5 font-bold text-primary-foreground"
                    style={{ backgroundColor: `var(${axis.colorVar})` }}
                  >
                    {axis.highCode}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Personas preview */}
      <section className="mx-auto max-w-6xl px-5 py-16">
        <h2 className="font-serif text-2xl font-bold md:text-3xl">{survey.personas.length}가지 여행 동물</h2>
        <p className="mt-2 max-w-lg text-pretty text-muted-foreground">
          진단이 끝나면 이 중 하나가 당신의 여행 페르소나가 돼요.
        </p>
        <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {survey.personas.map((p) => (
            <div key={p.code} className="rounded-2xl border border-border bg-card p-4">
              <span className="font-mono text-xs font-bold text-primary">{p.code}</span>
              <p className="mt-1 font-serif text-lg font-bold">{p.name}</p>
              <p className="text-pretty text-sm text-muted-foreground">{p.tag}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Edit callout */}
      {user?.isAdmin && (
        <section className="border-t border-border bg-card/50">
          <div className="mx-auto flex max-w-6xl flex-col items-start gap-6 px-5 py-16 md:flex-row md:items-center md:justify-between">
            <div className="flex items-start gap-4">
              <div className="rounded-2xl bg-primary/10 p-3 text-primary">
                <PenLine className="size-6" aria-hidden="true" />
              </div>
              <div>
                <h2 className="font-serif text-2xl font-bold">모든 걸 직접 수정하세요</h2>
                <p className="mt-1 max-w-xl text-pretty text-muted-foreground">
                  문항, 응답 방식, 선택 항목, 가중치, 축, 유형까지. 관리자 페이지에서 테스트의 모든 요소를 자유롭게 편집할 수
                  있어요.
                </p>
              </div>
            </div>
            <Button render={<Link href="/admin" />} nativeButton={false} size="lg" className="shrink-0 gap-2 rounded-full">
              <Compass className="size-4" aria-hidden="true" />
              편집 시작
            </Button>
          </div>
        </section>
      )}

      <footer className="border-t border-border">
        <div className="mx-auto max-w-6xl px-5 py-8 text-sm text-muted-foreground">
          {survey.title} · {survey.version} · 여행 성향 진단 시스템
        </div>
      </footer>
    </div>
  )
}
