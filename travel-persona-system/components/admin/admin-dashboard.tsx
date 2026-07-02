"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { useSurvey } from "@/lib/survey/store"
import { useAuth } from "@/lib/auth/store"
import type { Question, PartId, Section, Axis, Persona, WeightFeature, Survey } from "@/lib/survey/types"
import { QuestionEditor } from "./question-editor"
import { PersonaEditor } from "./persona-editor"
import { Field, Select, TextInput, NumberInput } from "./fields"
import { Button } from "@/components/ui/button"
import { Plus, RotateCcw, Trash2, Download, Upload, Eye, LogIn } from "lucide-react"
import { cn } from "@/lib/utils"

type Tab = "questions" | "axes" | "personas" | "weights" | "scoring" | "meta"

const PART_LABEL: Record<PartId, string> = { A: "성향진단", B: "취향프로필", C: "이번여행" }

function uid(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1000)}`
}

export function AdminDashboard() {
  const { survey, setSurvey, resetSurvey, hydrated, saving, saveError } = useSurvey()
  const { user, hydrated: authHydrated } = useAuth()
  const [tab, setTab] = useState<Tab>("questions")
  const [activePart, setActivePart] = useState<PartId>("A")

  function update(patch: Partial<Survey>) {
    setSurvey({ ...survey, ...patch })
  }

  if (!hydrated || !authHydrated) {
    return <div className="flex min-h-[60vh] items-center justify-center text-muted-foreground">불러오는 중…</div>
  }

  if (!user) {
    return (
      <div className="mx-auto max-w-lg px-5 py-24 text-center">
        <h1 className="font-serif text-2xl font-bold">로그인이 필요해요</h1>
        <p className="mt-2 text-muted-foreground">테스트 편집기는 관리자 계정만 사용할 수 있어요.</p>
        <Button render={<Link href="/login" />} nativeButton={false} className="mt-6 gap-2 rounded-full">
          <LogIn className="size-4" aria-hidden="true" />
          로그인하러 가기
        </Button>
      </div>
    )
  }

  if (!user.isAdmin) {
    return (
      <div className="mx-auto max-w-lg px-5 py-24 text-center">
        <h1 className="font-serif text-2xl font-bold">권한이 없어요</h1>
        <p className="mt-2 text-muted-foreground">테스트 편집기는 관리자 계정만 사용할 수 있어요.</p>
        <Button render={<Link href="/" />} nativeButton={false} variant="outline" className="mt-6 rounded-full bg-transparent">
          홈으로
        </Button>
      </div>
    )
  }

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: "questions", label: "문항", count: survey.questions.length },
    { id: "axes", label: "축", count: survey.axes.length },
    { id: "personas", label: "유형", count: survey.personas.length },
    { id: "weights", label: "가중치", count: survey.weightFeatures.length },
    { id: "scoring", label: "계산 방식" },
    { id: "meta", label: "정보/데이터" },
  ]

  return (
    <div className="mx-auto max-w-5xl px-5 pb-24 pt-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-primary">Admin</p>
          <h1 className="mt-1 font-serif text-3xl font-bold">테스트 편집기</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            문항, 응답 방식, 선택 항목, 가중치, 축, 유형까지 모두 수정할 수 있어요.
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {saveError ? (
              <span className="text-destructive">{saveError}</span>
            ) : saving ? (
              "저장 중…"
            ) : (
              "모든 변경사항이 자동 저장돼요."
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            render={<Link href="/test" />}
            nativeButton={false}
            variant="outline"
            className="gap-2 rounded-full bg-transparent"
          >
            <Eye className="size-4" aria-hidden="true" />
            테스트 미리보기
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="mt-6 flex flex-wrap gap-1.5 border-b border-border">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={cn(
              "-mb-px flex items-center gap-1.5 rounded-t-lg border-b-2 px-4 py-2.5 text-sm font-medium transition-colors",
              tab === t.id
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {t.label}
            {typeof t.count === "number" && (
              <span className="rounded-full bg-muted px-1.5 py-0.5 font-mono text-[10px]">{t.count}</span>
            )}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === "questions" && (
          <QuestionsTab
            survey={survey}
            update={update}
            activePart={activePart}
            setActivePart={setActivePart}
          />
        )}
        {tab === "axes" && <AxesTab survey={survey} update={update} />}
        {tab === "personas" && <PersonasTab survey={survey} update={update} />}
        {tab === "weights" && <WeightsTab survey={survey} update={update} />}
        {tab === "scoring" && <ScoringTab survey={survey} update={update} />}
        {tab === "meta" && <MetaTab survey={survey} update={update} setSurvey={setSurvey} resetSurvey={resetSurvey} />}
      </div>
    </div>
  )
}

/* ---------------- Questions Tab ---------------- */
function QuestionsTab({
  survey,
  update,
  activePart,
  setActivePart,
}: {
  survey: Survey
  update: (p: Partial<Survey>) => void
  activePart: PartId
  setActivePart: (p: PartId) => void
}) {
  const parts: PartId[] = ["A", "B", "C"]
  const sections = survey.sections.filter((s) => s.part === activePart)

  // 필드명(데이터 키) 중복 감지: field 가 지정된 경우 id 대신 그것을 키로 사용
  const keyCounts = new Map<string, number>()
  for (const q of survey.questions) {
    const key = q.field?.trim() || q.id
    keyCounts.set(key, (keyCounts.get(key) ?? 0) + 1)
  }
  const isDuplicateField = (q: Question) => (keyCounts.get(q.field?.trim() || q.id) ?? 0) > 1

  function setQuestions(qs: Question[]) {
    update({ questions: qs })
  }

  function changeQuestion(updated: Question) {
    setQuestions(survey.questions.map((q) => (q.id === updated.id ? updated : q)))
  }

  function deleteQuestion(id: string) {
    setQuestions(survey.questions.filter((q) => q.id !== id))
  }

  function duplicateQuestion(q: Question) {
    const copy: Question = { ...q, id: uid("q"), text: q.text + " (복사본)" }
    const idx = survey.questions.findIndex((x) => x.id === q.id)
    const next = [...survey.questions]
    next.splice(idx + 1, 0, copy)
    setQuestions(next)
  }

  function moveQuestion(sectionId: string, id: string, dir: -1 | 1) {
    const inSection = survey.questions.filter((q) => q.sectionId === sectionId)
    const idx = inSection.findIndex((q) => q.id === id)
    const targetIdx = idx + dir
    if (targetIdx < 0 || targetIdx >= inSection.length) return
    const a = inSection[idx]
    const b = inSection[targetIdx]
    const globalA = survey.questions.findIndex((q) => q.id === a.id)
    const globalB = survey.questions.findIndex((q) => q.id === b.id)
    const next = [...survey.questions]
    ;[next[globalA], next[globalB]] = [next[globalB], next[globalA]]
    setQuestions(next)
  }

  function addQuestion(sectionId: string) {
    const q: Question = {
      id: uid("q"),
      part: activePart,
      sectionId,
      text: "새 질문",
      type: activePart === "A" ? "likert" : "single",
      options: activePart === "A" ? undefined : [{ id: uid("opt"), label: "선택지 1" }],
      points: activePart === "A" ? 5 : undefined,
      axisId: activePart === "A" ? survey.axes[0]?.id : undefined,
      direction: activePart === "A" ? "forward" : undefined,
    }
    setQuestions([...survey.questions, q])
  }

  function addSection() {
    const section: Section = {
      id: uid("sec"),
      part: activePart,
      title: "새 섹션",
      description: "",
    }
    update({ sections: [...survey.sections, section] })
  }

  function changeSection(id: string, patch: Partial<Section>) {
    update({ sections: survey.sections.map((s) => (s.id === id ? { ...s, ...patch } : s)) })
  }

  function deleteSection(id: string) {
    update({
      sections: survey.sections.filter((s) => s.id !== id),
      questions: survey.questions.filter((q) => q.sectionId !== id),
    })
  }

  return (
    <div>
      {/* Part selector */}
      <div className="mb-5 flex flex-wrap gap-2">
        {parts.map((p) => {
          const count = survey.questions.filter((q) => q.part === p).length
          return (
            <button
              key={p}
              type="button"
              onClick={() => setActivePart(p)}
              className={cn(
                "rounded-full border px-4 py-2 text-sm font-medium transition-colors",
                activePart === p
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-card hover:border-primary/50",
              )}
            >
              Part {p} · {PART_LABEL[p]} <span className="opacity-70">({count})</span>
            </button>
          )
        })}
      </div>

      {sections.length === 0 && (
        <p className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
          섹션이 없습니다. 아래에서 섹션을 추가하세요.
        </p>
      )}

      <div className="flex flex-col gap-6">
        {sections.map((section) => {
          const qs = survey.questions.filter((q) => q.sectionId === section.id)
          return (
            <div key={section.id} className="rounded-2xl border border-border bg-secondary/30 p-4">
              <div className="mb-3 grid gap-2 sm:grid-cols-2">
                <Field label="섹션 제목">
                  <TextInput value={section.title} onChange={(e) => changeSection(section.id, { title: e.target.value })} />
                </Field>
                <Field label="섹션 설명">
                  <TextInput
                    value={section.description ?? ""}
                    onChange={(e) => changeSection(section.id, { description: e.target.value })}
                  />
                </Field>
              </div>

              <div className="flex flex-col gap-2">
                {qs.map((q, i) => (
                  <QuestionEditor
                    key={q.id}
                    question={q}
                    index={i}
                    axes={survey.axes}
                    onChange={changeQuestion}
                    onDelete={() => deleteQuestion(q.id)}
                    onDuplicate={() => duplicateQuestion(q)}
                    onMove={(dir) => moveQuestion(section.id, q.id, dir)}
                    canMoveUp={i > 0}
                    canMoveDown={i < qs.length - 1}
                    duplicateField={isDuplicateField(q)}
                  />
                ))}
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => addQuestion(section.id)}
                  className="gap-1.5 rounded-full bg-transparent"
                >
                  <Plus className="size-3.5" aria-hidden="true" />
                  문항 추가
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => deleteSection(section.id)}
                  className="gap-1.5 rounded-full text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="size-3.5" aria-hidden="true" />
                  섹션 삭제
                </Button>
              </div>
            </div>
          )
        })}
      </div>

      <Button variant="outline" onClick={addSection} className="mt-5 gap-2 rounded-full bg-transparent">
        <Plus className="size-4" aria-hidden="true" />섹션 추가 (Part {activePart})
      </Button>
    </div>
  )
}

/* ---------------- Axes Tab ---------------- */
function AxesTab({ survey, update }: { survey: Survey; update: (p: Partial<Survey>) => void }) {
  const colorVars = ["--chart-1", "--chart-2", "--chart-3", "--chart-4", "--chart-5"]

  function change(id: string, patch: Partial<Axis>) {
    update({ axes: survey.axes.map((a) => (a.id === id ? { ...a, ...patch } : a)) })
  }
  function add() {
    update({
      axes: [
        ...survey.axes,
        {
          id: uid("axis"),
          name: "새 축",
          field: "new_score",
          lowLabel: "낮음",
          highLabel: "높음",
          lowCode: "X",
          highCode: "Y",
          colorVar: colorVars[survey.axes.length % colorVars.length],
        },
      ],
    })
  }
  function remove(id: string) {
    update({ axes: survey.axes.filter((a) => a.id !== id) })
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        각 축은 유형 코드의 ��� 글자를 결정해요. 코드 순서는 축 순서를 따릅니다.
      </p>
      {survey.axes.map((axis) => (
        <div key={axis.id} className="rounded-2xl border border-border bg-card p-4">
          <div className="grid gap-3 md:grid-cols-3">
            <Field label="축 이름">
              <TextInput value={axis.name} onChange={(e) => change(axis.id, { name: e.target.value })} />
            </Field>
            <Field label="데이터 필드">
              <TextInput value={axis.field} onChange={(e) => change(axis.id, { field: e.target.value })} />
            </Field>
            <Field label="색상 토큰">
              <Select value={axis.colorVar} onChange={(e) => change(axis.id, { colorVar: e.target.value })}>
                {colorVars.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="낮은 ��� 라벨">
              <TextInput value={axis.lowLabel} onChange={(e) => change(axis.id, { lowLabel: e.target.value })} />
            </Field>
            <Field label="낮은 쪽 코드" hint="1글자 권장">
              <TextInput value={axis.lowCode} maxLength={2} onChange={(e) => change(axis.id, { lowCode: e.target.value })} />
            </Field>
            <Field label="분기 임계값" hint={`비우면 전역값(${survey.scoring?.axisThreshold ?? 0.5}) 사용`}>
              <NumberInput
                step="0.05"
                min={0}
                max={1}
                value={typeof axis.threshold === "number" ? axis.threshold : ""}
                placeholder={String(survey.scoring?.axisThreshold ?? 0.5)}
                onChange={(e) =>
                  change(axis.id, { threshold: e.target.value === "" ? undefined : Number(e.target.value) })
                }
              />
            </Field>
            <Field label="높은 쪽 라벨">
              <TextInput value={axis.highLabel} onChange={(e) => change(axis.id, { highLabel: e.target.value })} />
            </Field>
            <Field label="높은 쪽 코드" hint="1글자 권장">
              <TextInput value={axis.highCode} maxLength={2} onChange={(e) => change(axis.id, { highCode: e.target.value })} />
            </Field>
            <div className="flex items-end justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => remove(axis.id)}
                className="gap-1.5 rounded-full text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="size-3.5" aria-hidden="true" />
                삭제
              </Button>
            </div>
          </div>
          <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
            <span className="size-3 rounded-full" style={{ backgroundColor: `var(${axis.colorVar})` }} />
            미리보기: {axis.lowCode} ← {axis.name} → {axis.highCode} (임계값{" "}
            {typeof axis.threshold === "number" ? axis.threshold : (survey.scoring?.axisThreshold ?? 0.5)} 이상이면{" "}
            {axis.highCode})
          </div>
        </div>
      ))}
      <Button variant="outline" onClick={add} className="gap-2 self-start rounded-full bg-transparent">
        <Plus className="size-4" aria-hidden="true" />축 추가
      </Button>
    </div>
  )
}

/* ---------------- Personas Tab ---------------- */
function PersonasTab({ survey, update }: { survey: Survey; update: (p: Partial<Survey>) => void }) {
  function change(idx: number, patch: Partial<Persona>) {
    update({ personas: survey.personas.map((p, i) => (i === idx ? { ...p, ...patch } : p)) })
  }
  function add() {
    update({ personas: [...survey.personas, { code: "", name: "새 유형", tag: "" }] })
  }
  function remove(idx: number) {
    update({ personas: survey.personas.filter((_, i) => i !== idx) })
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        코드는 축 코드의 조합이에요 (예: {survey.axes.map((a) => a.highCode).join("")}). 각 유형의 해설, 강점, 팁,
        그리고 유형별 가중치까지 수정할 수 있어요.
      </p>
      <div className="flex flex-col gap-3">
        {survey.personas.map((p, i) => (
          <PersonaEditor
            key={i}
            persona={p}
            weightFeatures={survey.weightFeatures}
            onChange={(patch) => change(i, patch)}
            onDelete={() => remove(i)}
          />
        ))}
      </div>
      <Button variant="outline" onClick={add} className="gap-2 self-start rounded-full bg-transparent">
        <Plus className="size-4" aria-hidden="true" />유형 추가
      </Button>
    </div>
  )
}

/* ---------------- Weights Tab ---------------- */
function WeightsTab({ survey, update }: { survey: Survey; update: (p: Partial<Survey>) => void }) {
  function change(id: string, patch: Partial<WeightFeature>) {
    update({ weightFeatures: survey.weightFeatures.map((w) => (w.id === id ? { ...w, ...patch } : w)) })
  }
  function add() {
    update({
      weightFeatures: [
        ...survey.weightFeatures,
        { id: uid("w"), label: "새 가중치", base: 1, k: 0.5, axisId: survey.axes[0]?.id ?? "" },
      ],
    })
  }
  function remove(id: string) {
    update({ weightFeatures: survey.weightFeatures.filter((w) => w.id !== id) })
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-xl border border-border bg-secondary/40 p-4 text-sm">
        <p className="font-medium">가중치 공식</p>
        <p className="mt-1 font-mono text-muted-foreground">weight = base + k × (연동 축 점수 − 0.5)</p>
        <p className="mt-1 text-muted-foreground">축 점수는 0~1로 정규화되며, k가 클수록 성향에 민감하게 반응해요.</p>
      </div>
      {survey.weightFeatures.map((w) => (
        <div key={w.id} className="rounded-2xl border border-border bg-card p-4">
          <div className="grid gap-3 md:grid-cols-4">
            <Field label="가중치 이름" className="md:col-span-2">
              <TextInput value={w.label} onChange={(e) => change(w.id, { label: e.target.value })} />
            </Field>
            <Field label="연동 축">
              <Select value={w.axisId ?? ""} onChange={(e) => change(w.id, { axisId: e.target.value })}>
                <option value="">(없음)</option>
                {survey.axes.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </Select>
            </Field>
            <div className="flex items-end justify-end md:justify-start">
              <button
                type="button"
                onClick={() => remove(w.id)}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="size-3.5" aria-hidden="true" />
                삭제
              </button>
            </div>
            <Field label="base (기본값)">
              <NumberInput step="0.1" value={w.base} onChange={(e) => change(w.id, { base: Number(e.target.value) })} />
            </Field>
            <Field label="k (민감도)">
              <NumberInput step="0.1" value={w.k} onChange={(e) => change(w.id, { k: Number(e.target.value) })} />
            </Field>
          </div>
        </div>
      ))}
      <Button variant="outline" onClick={add} className="gap-2 self-start rounded-full bg-transparent">
        <Plus className="size-4" aria-hidden="true" />가중치 추가
      </Button>
    </div>
  )
}

/* ---------------- Scoring (계산 방식) Tab ---------------- */
const SCORING_DEFAULTS = { axisThreshold: 0.5, neutralScore: 0.5, weightPivot: 0.5, weightClampMin: 0 }

function ScoringTab({ survey, update }: { survey: Survey; update: (p: Partial<Survey>) => void }) {
  const cfg = { ...SCORING_DEFAULTS, ...(survey.scoring ?? {}) }
  function set(patch: Partial<typeof cfg>) {
    update({ scoring: { ...cfg, ...patch } })
  }

  const fields: { key: keyof typeof cfg; label: string; hint: string; step: string }[] = [
    {
      key: "axisThreshold",
      label: "축 분기 임계값",
      hint: "축 점수(0~1)가 이 값 이상이면 높은 쪽 코드로 분류돼요. (기본 0.5)",
      step: "0.05",
    },
    {
      key: "neutralScore",
      label: "미응답 기본 점수",
      hint: "해당 축에 응답이 하나도 없을 때 사용하는 중립 점수예요. (기본 0.5)",
      step: "0.05",
    },
    {
      key: "weightPivot",
      label: "가중치 기준점 (pivot)",
      hint: "가중치 공식 base + k × (축점수 − pivot) 의 기준점이에요. (기본 0.5)",
      step: "0.05",
    },
    {
      key: "weightClampMin",
      label: "가중치 하한값",
      hint: "계산된 가중치가 이 값보다 작아지지 않도록 제한해요. (기본 0)",
      step: "0.05",
    },
  ]

  return (
    <div className="flex flex-col gap-5">
      {/* 계산 흐름 설명 */}
      <div className="rounded-2xl border border-border bg-secondary/40 p-5 text-sm leading-relaxed">
        <p className="font-medium">유형은 이렇게 계산돼요</p>
        <ol className="mt-3 flex flex-col gap-2 text-muted-foreground">
          <li>
            <span className="mr-2 font-mono text-xs text-foreground">1</span>
            성향진단(Part A)의 리커트 응답을 축별로 0~1로 정규화해 평균 → <b>축 점수</b>
          </li>
          <li>
            <span className="mr-2 font-mono text-xs text-foreground">2</span>
            축 점수가 <b>임계값({cfg.axisThreshold})</b> 이상이면 높은 쪽 코드, 미만이면 낮은 쪽 코드
          </li>
          <li>
            <span className="mr-2 font-mono text-xs text-foreground">3</span>
            4개 축 코드를 순서대로 이어 붙여 <b>유형 코드</b> 생성 (예: {survey.axes.map((a) => a.highCode).join("")})
          </li>
          <li>
            <span className="mr-2 font-mono text-xs text-foreground">4</span>
            이번 여행(Part C) 슬라이더가 있으면 해당 축 점수를 덮어써 <b>최종 유형</b> 결정
          </li>
          <li>
            <span className="mr-2 font-mono text-xs text-foreground">5</span>
            각 가중치 = <span className="font-mono">base + k × (축점수 − {cfg.weightPivot})</span>, 하한{" "}
            {cfg.weightClampMin}
          </li>
        </ol>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {fields.map((f) => (
          <div key={f.key} className="rounded-2xl border border-border bg-card p-4">
            <Field label={f.label} hint={f.hint}>
              <NumberInput
                step={f.step}
                value={cfg[f.key]}
                onChange={(e) => set({ [f.key]: Number(e.target.value) } as Partial<typeof cfg>)}
              />
            </Field>
          </div>
        ))}
      </div>

      <Button
        variant="outline"
        onClick={() => update({ scoring: { ...SCORING_DEFAULTS } })}
        className="gap-2 self-start rounded-full bg-transparent"
      >
        <RotateCcw className="size-4" aria-hidden="true" />계산 기본값으로 되돌리기
      </Button>
    </div>
  )
}

/* ---------------- Meta / Data Tab ---------------- */
function MetaTab({
  survey,
  update,
  setSurvey,
  resetSurvey,
}: {
  survey: Survey
  update: (p: Partial<Survey>) => void
  setSurvey: (s: Survey) => void
  resetSurvey: () => void
}) {
  const [importError, setImportError] = useState<string | null>(null)

  function exportJson() {
    const blob = new Blob([JSON.stringify(survey, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "travel-animal-16-survey.json"
    a.click()
    URL.revokeObjectURL(url)
  }

  function importJson(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result)) as Survey
        if (!parsed.questions || !parsed.axes) throw new Error("형식이 올바르지 않습니다.")
        setSurvey(parsed)
        setImportError(null)
      } catch (err) {
        setImportError(err instanceof Error ? err.message : "가져오기에 실패했습니다.")
      }
    }
    reader.readAsText(file)
    e.target.value = ""
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-3 md:grid-cols-2">
        <Field label="테스트 제목">
          <TextInput value={survey.title} onChange={(e) => update({ title: e.target.value })} />
        </Field>
        <Field label="버전">
          <TextInput value={survey.version} onChange={(e) => update({ version: e.target.value })} />
        </Field>
        <Field label="부제 / 설명" className="md:col-span-2">
          <TextInput value={survey.subtitle} onChange={(e) => update({ subtitle: e.target.value })} />
        </Field>
      </div>

      <div className="rounded-2xl border border-border bg-card p-4">
        <p className="text-sm font-medium">데이터 관리</p>
        <p className="mt-1 text-sm text-muted-foreground">
          편집 내용은 브라우저에 자동 저장돼요. 백업하거나 다른 기기로 옮기려면 내보내기/가져오기를 사용하세요.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button variant="outline" onClick={exportJson} className="gap-2 rounded-full bg-transparent">
            <Download className="size-4" aria-hidden="true" />
            JSON 내보내기
          </Button>
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-input bg-transparent px-4 py-2 text-sm font-medium transition-colors hover:bg-muted">
            <Upload className="size-4" aria-hidden="true" />
            JSON 가져오기
            <input type="file" accept="application/json" onChange={importJson} className="hidden" />
          </label>
          <Button
            variant="ghost"
            onClick={() => {
              if (confirm("기본 문항으로 되돌릴까요? 편집 내용이 사라집니다.")) resetSurvey()
            }}
            className="gap-2 rounded-full text-muted-foreground hover:text-destructive"
          >
            <RotateCcw className="size-4" aria-hidden="true" />
            기본값으로 초기화
          </Button>
        </div>
        {importError && <p className="mt-2 text-sm text-destructive">{importError}</p>}
      </div>
    </div>
  )
}
