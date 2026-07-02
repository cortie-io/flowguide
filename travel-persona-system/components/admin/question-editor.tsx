"use client"

import { useState } from "react"
import type { Question, QuestionType, Axis, QuestionOption, AnswerValue } from "@/lib/survey/types"
import { Field, Select, TextInput, TextArea, NumberInput, Toggle } from "./fields"
import { QuestionField } from "@/components/question-field"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronUp, Copy, GripVertical, Plus, Trash2, X } from "lucide-react"
import { cn } from "@/lib/utils"

const TYPE_LABELS: Record<QuestionType, string> = {
  likert: "리커트 5점 (채점)",
  scale: "척도 (원값)",
  single: "단일 선택",
  multi: "다중 선택",
  text: "자유 입력",
  number: "숫자 입력",
  date: "날짜 입력",
  slider: "축 오버라이드 슬라이더",
}

interface Props {
  question: Question
  index: number
  axes: Axis[]
  onChange: (q: Question) => void
  onDelete: () => void
  onDuplicate: () => void
  onMove: (dir: -1 | 1) => void
  canMoveUp: boolean
  canMoveDown: boolean
  duplicateField?: boolean
}

export function QuestionEditor({
  question: q,
  index,
  axes,
  onChange,
  onDelete,
  onDuplicate,
  onMove,
  canMoveUp,
  canMoveDown,
  duplicateField,
}: Props) {
  const [open, setOpen] = useState(false)

  function set<K extends keyof Question>(key: K, value: Question[K]) {
    onChange({ ...q, [key]: value })
  }

  function updateOption(id: string, label: string) {
    set(
      "options",
      (q.options ?? []).map((o) => (o.id === id ? { ...o, label } : o)),
    )
  }

  function addOption() {
    const opt: QuestionOption = { id: `${q.id}-opt-${Date.now()}`, label: "새 선택지" }
    set("options", [...(q.options ?? []), opt])
  }

  function removeOption(id: string) {
    set("options", (q.options ?? []).filter((o) => o.id !== id))
  }

  const hasOptions = q.type === "single" || q.type === "multi"
  const isLikert = q.type === "likert"
  const isScaleLike = q.type === "likert" || q.type === "scale" || q.type === "slider"

  return (
    <div className="rounded-2xl border border-border bg-card">
      {/* Header row */}
      <div className="flex items-center gap-2 px-3 py-2.5">
        <GripVertical className="size-4 shrink-0 text-muted-foreground/50" aria-hidden="true" />
        <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-secondary font-mono text-xs font-bold text-secondary-foreground">
          {index + 1}
        </span>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex flex-1 items-center gap-2 text-left"
        >
          <span className="line-clamp-1 flex-1 text-sm font-medium">{q.text || "(제목 없음)"}</span>
          <span
            className={cn(
              "hidden shrink-0 rounded-md px-2 py-0.5 font-mono text-[10px] sm:inline",
              duplicateField ? "bg-destructive/10 text-destructive" : "bg-secondary text-secondary-foreground",
            )}
            title="필드명 (데이터 키)"
          >
            {q.field?.trim() || q.id}
          </span>
          <span className="hidden shrink-0 rounded-md bg-muted px-2 py-0.5 font-mono text-[10px] text-muted-foreground sm:inline">
            {TYPE_LABELS[q.type]}
          </span>
        </button>
        <div className="flex shrink-0 items-center">
          <IconBtn label="위로" onClick={() => onMove(-1)} disabled={!canMoveUp}>
            <ChevronUp className="size-4" />
          </IconBtn>
          <IconBtn label="아래로" onClick={() => onMove(1)} disabled={!canMoveDown}>
            <ChevronDown className="size-4" />
          </IconBtn>
          <IconBtn label="복제" onClick={onDuplicate}>
            <Copy className="size-4" />
          </IconBtn>
          <IconBtn label="삭제" onClick={onDelete} danger>
            <Trash2 className="size-4" />
          </IconBtn>
          <IconBtn label={open ? "접기" : "펼치기"} onClick={() => setOpen((o) => !o)}>
            <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
          </IconBtn>
        </div>
      </div>

      {open && (
        <div className="border-t border-border px-4 py-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="질문 문구" className="md:col-span-2">
              <TextArea value={q.text} rows={2} onChange={(e) => set("text", e.target.value)} />
            </Field>

            <Field
              label="필드명 (데이터 키)"
              className="md:col-span-2"
              hint={
                duplicateField
                  ? "⚠ 다른 문항과 필드명이 중복됩니다. 응답이 덮어써질 수 있어요."
                  : "응답 데이터에 저장될 키. 비우면 자동 ID를 사용해요."
              }
            >
              <TextInput
                value={q.field ?? ""}
                placeholder={q.id}
                className={cn(
                  "font-mono",
                  duplicateField && "border-destructive text-destructive focus-visible:ring-destructive/40",
                )}
                onChange={(e) => set("field", e.target.value || undefined)}
              />
            </Field>

            <Field label="응답 방식">
              <Select value={q.type} onChange={(e) => set("type", e.target.value as QuestionType)}>
                {Object.entries(TYPE_LABELS).map(([val, label]) => (
                  <option key={val} value={val}>
                    {label}
                  </option>
                ))}
              </Select>
            </Field>

            <Field label="도움말 (선택)">
              <TextInput value={q.helpText ?? ""} onChange={(e) => set("helpText", e.target.value || undefined)} />
            </Field>

            {/* 채점 설정 */}
            {isLikert && (
              <>
                <Field label="연동 축" hint="이 문항이 채점하는 성향 축">
                  <Select value={q.axisId ?? ""} onChange={(e) => set("axisId", e.target.value || undefined)}>
                    <option value="">(없음)</option>
                    {axes.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name} ({a.lowCode}/{a.highCode})
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="채점 방향" hint="정채점: 높을수록 High / 역채점: 반대">
                  <Select
                    value={q.direction ?? "forward"}
                    onChange={(e) => set("direction", e.target.value as "forward" | "reverse")}
                  >
                    <option value="forward">정채점 (forward)</option>
                    <option value="reverse">역채점 (reverse)</option>
                  </Select>
                </Field>
              </>
            )}

            {q.type === "slider" && (
              <Field label="오버라이드 축" hint="이번 여행에서 재조정할 축">
                <Select
                  value={q.overrideAxisId ?? ""}
                  onChange={(e) => set("overrideAxisId", e.target.value || undefined)}
                >
                  <option value="">(없음)</option>
                  {axes.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </Select>
              </Field>
            )}

            {isScaleLike && (
              <>
                <Field label="점수 개수" hint="예: 5점 척도">
                  <NumberInput
                    min={2}
                    max={10}
                    value={q.points ?? 5}
                    onChange={(e) => set("points", Number(e.target.value) || 5)}
                  />
                </Field>
                <Field label="왼쪽 끝 라벨">
                  <TextInput value={q.lowLabel ?? ""} onChange={(e) => set("lowLabel", e.target.value || undefined)} />
                </Field>
                <Field label="오른쪽 끝 라벨">
                  <TextInput value={q.highLabel ?? ""} onChange={(e) => set("highLabel", e.target.value || undefined)} />
                </Field>
              </>
            )}

            {q.type === "multi" && (
              <Field label="최대 선택 개수" hint="0 또는 비우면 제한 없음">
                <NumberInput
                  min={0}
                  value={q.maxSelect ?? 0}
                  onChange={(e) => set("maxSelect", Number(e.target.value) || undefined)}
                />
              </Field>
            )}

            {q.type === "number" && (
              <Field label="최소값">
                <NumberInput value={q.min ?? 0} onChange={(e) => set("min", Number(e.target.value))} />
              </Field>
            )}

            <div className="flex flex-wrap items-center gap-5 md:col-span-2">
              <Toggle checked={!!q.required} onChange={(v) => set("required", v)} label="필수 응답" />
              <Toggle checked={!!q.conditional} onChange={(v) => set("conditional", v)} label="조건부 노출" />
              {hasOptions && (
                <Toggle
                  checked={!!q.allowCustom}
                  onChange={(v) => set("allowCustom", v || undefined)}
                  label="기타(직접입력) 허용"
                />
              )}
            </div>

            {q.type === "multi" && q.allowCustom && (
              <Field label="기타 입력 구분자" hint="여러 항목을 나눌 구분자예요. 비우면 쉼표(,)를 사용해요.">
                <TextInput
                  value={q.customSeparator ?? ""}
                  placeholder=","
                  className="max-w-24 font-mono"
                  onChange={(e) => set("customSeparator", e.target.value || undefined)}
                />
              </Field>
            )}

            {q.conditional && (
              <Field label="조건 안내 문구" className="md:col-span-2">
                <TextInput
                  value={q.conditionNote ?? ""}
                  onChange={(e) => set("conditionNote", e.target.value || undefined)}
                />
              </Field>
            )}
          </div>

          {/* Options editor */}
          {hasOptions && (
            <div className="mt-4">
              <p className="mb-2 text-xs font-medium text-muted-foreground">선택 항목</p>
              <div className="flex flex-col gap-2">
                {(q.options ?? []).map((opt) => (
                  <div key={opt.id} className="flex items-center gap-2">
                    <TextInput value={opt.label} onChange={(e) => updateOption(opt.id, e.target.value)} />
                    <IconBtn label="선택지 삭제" onClick={() => removeOption(opt.id)} danger>
                      <X className="size-4" />
                    </IconBtn>
                  </div>
                ))}
              </div>
              <Button variant="outline" size="sm" onClick={addOption} className="mt-2 gap-1.5 rounded-full bg-transparent">
                <Plus className="size-3.5" aria-hidden="true" />
                선택지 추가
              </Button>
            </div>
          )}

          {/* Scale labels editor (likert) */}
          {isLikert && (
            <div className="mt-4">
              <p className="mb-2 text-xs font-medium text-muted-foreground">척도 라벨 (각 점수)</p>
              <div className="grid gap-2 sm:grid-cols-5">
                {Array.from({ length: q.points ?? 5 }, (_, i) => (
                  <TextInput
                    key={i}
                    value={q.scaleLabels?.[i] ?? ""}
                    placeholder={`${i + 1}점`}
                    onChange={(e) => {
                      const next = [...(q.scaleLabels ?? Array.from({ length: q.points ?? 5 }, () => ""))]
                      next[i] = e.target.value
                      set("scaleLabels", next)
                    }}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Live preview */}
          <div className="mt-5 rounded-xl border border-dashed border-border bg-background/60 p-4">
            <p className="mb-3 text-xs font-medium text-muted-foreground">미리보기</p>
            <p className="mb-3 text-sm font-medium">{q.text}</p>
            <QuestionPreview question={q} />
          </div>
        </div>
      )}
    </div>
  )
}

function QuestionPreview({ question }: { question: Question }) {
  const [val, setVal] = useState<AnswerValue>(null)
  return <QuestionField question={question} value={val} onChange={setVal} />
}

function IconBtn({
  children,
  label,
  onClick,
  disabled,
  danger,
}: {
  children: React.ReactNode
  label: string
  onClick: () => void
  disabled?: boolean
  danger?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      className={cn(
        "flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted disabled:opacity-30",
        danger && "hover:bg-destructive/10 hover:text-destructive",
      )}
    >
      {children}
    </button>
  )
}
