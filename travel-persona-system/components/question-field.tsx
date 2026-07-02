"use client"

import type { Question, AnswerValue } from "@/lib/survey/types"
import { cn } from "@/lib/utils"

// "기타(직접입력)" 값은 이 접두사로 인코딩해서 저장한다. (예: "custom:글램핑")
const CUSTOM_PREFIX = "custom:"
const CUSTOM_ID = "__custom__"

function isCustom(v: string) {
  return v.startsWith(CUSTOM_PREFIX)
}
function customText(v: string) {
  return v.slice(CUSTOM_PREFIX.length)
}

interface Props {
  question: Question
  value: AnswerValue
  onChange: (value: AnswerValue) => void
}

interface SubProps {
  q: Question
  value: AnswerValue
  onChange: (value: AnswerValue) => void
}

export function QuestionField({ question: q, value, onChange }: Props) {
  switch (q.type) {
    case "likert":
      return <ScaleChoice q={q} value={value} onChange={onChange} likert />
    case "scale":
    case "slider":
      return <ScaleChoice q={q} value={value} onChange={onChange} />
    case "single":
      return <SingleChoice q={q} value={value} onChange={onChange} />
    case "multi":
      return <MultiChoice q={q} value={value} onChange={onChange} />
    case "number":
      return (
        <input
          type="number"
          inputMode="numeric"
          min={q.min}
          value={typeof value === "number" ? value : ""}
          onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
          className="w-full max-w-xs rounded-xl border border-input bg-background px-4 py-3 text-base outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
          placeholder="숫자를 입력하세요"
        />
      )
    case "date":
      return (
        <input
          type="date"
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.target.value || null)}
          className="w-full max-w-xs rounded-xl border border-input bg-background px-4 py-3 text-base outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
        />
      )
    case "text":
    default:
      return (
        <textarea
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.target.value || null)}
          rows={3}
          className="w-full rounded-xl border border-input bg-background px-4 py-3 text-base outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
          placeholder="자유롭게 입력하세요"
        />
      )
  }
}

function ScaleChoice({ q, value, onChange, likert }: SubProps & { likert?: boolean }) {
  const points = q.points ?? 5
  const items = Array.from({ length: points }, (_, i) => i + 1)
  const labels = q.scaleLabels && q.scaleLabels.length === points ? q.scaleLabels : null

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-stretch gap-2">
        {items.map((n) => {
          const active = value === n
          return (
            <button
              key={n}
              type="button"
              onClick={() => onChange(n)}
              className={cn(
                "flex flex-1 flex-col items-center gap-2 rounded-xl border px-2 py-3 text-center transition-colors",
                active
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-background hover:border-primary/50 hover:bg-primary/5",
              )}
              aria-pressed={active}
            >
              <span className="font-serif text-lg font-bold">{n}</span>
              {labels && <span className="text-xs leading-tight opacity-90">{labels[n - 1]}</span>}
            </button>
          )
        })}
      </div>
      {!labels && (
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>{q.lowLabel ?? (likert ? "전혀 아니다" : "낮음")}</span>
          <span>{q.highLabel ?? (likert ? "매우 그렇다" : "높음")}</span>
        </div>
      )}
    </div>
  )
}

function SingleChoice({ q, value, onChange }: SubProps) {
  const strVal = typeof value === "string" ? value : ""
  const customActive = isCustom(strVal)

  return (
    <div className="flex flex-col gap-2">
      {(q.options ?? []).map((opt) => {
        const active = value === opt.id
        return (
          <button
            key={opt.id}
            type="button"
            onClick={() => onChange(opt.id)}
            className={cn(
              "flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-colors",
              active
                ? "border-primary bg-primary/10"
                : "border-border bg-background hover:border-primary/50 hover:bg-primary/5",
            )}
            aria-pressed={active}
          >
            <span
              className={cn(
                "flex size-5 shrink-0 items-center justify-center rounded-full border-2",
                active ? "border-primary" : "border-muted-foreground/40",
              )}
            >
              {active && <span className="size-2.5 rounded-full bg-primary" />}
            </span>
            <span className="text-base">{opt.label}</span>
          </button>
        )
      })}

      {q.allowCustom && (
        <CustomOptionRow
          type="radio"
          active={customActive}
          text={customActive ? customText(strVal) : ""}
          onSelect={() => onChange(CUSTOM_PREFIX)}
          onText={(t) => onChange(CUSTOM_PREFIX + t)}
        />
      )}
    </div>
  )
}

function MultiChoice({ q, value, onChange }: SubProps) {
  const selected = Array.isArray(value) ? value : []
  const max = q.maxSelect ?? Infinity
  const customVal = selected.find((s) => isCustom(s))
  const customActive = customVal !== undefined
  const countsTowardMax = selected.length

  function toggle(id: string) {
    if (selected.includes(id)) {
      onChange(selected.filter((s) => s !== id))
    } else {
      if (countsTowardMax >= max) return
      onChange([...selected, id])
    }
  }

  function toggleCustom() {
    if (customActive) {
      onChange(selected.filter((s) => !isCustom(s)))
    } else {
      if (countsTowardMax >= max) return
      onChange([...selected, CUSTOM_PREFIX])
    }
  }

  function setCustomText(t: string) {
    onChange([...selected.filter((s) => !isCustom(s)), CUSTOM_PREFIX + t])
  }

  return (
    <div className="flex flex-col gap-2">
      {q.maxSelect && (
        <p className="text-xs text-muted-foreground">
          최대 {q.maxSelect}개 선택 · {countsTowardMax}/{q.maxSelect}
        </p>
      )}
      {(q.options ?? []).map((opt) => {
        const active = selected.includes(opt.id)
        const disabled = !active && countsTowardMax >= max
        return (
          <button
            key={opt.id}
            type="button"
            onClick={() => toggle(opt.id)}
            disabled={disabled}
            className={cn(
              "flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-colors",
              active
                ? "border-primary bg-primary/10"
                : "border-border bg-background hover:border-primary/50 hover:bg-primary/5",
              disabled && "cursor-not-allowed opacity-40",
            )}
            aria-pressed={active}
          >
            <span
              className={cn(
                "flex size-5 shrink-0 items-center justify-center rounded-md border-2",
                active ? "border-primary bg-primary text-primary-foreground" : "border-muted-foreground/40",
              )}
            >
              {active && (
                <svg viewBox="0 0 16 16" className="size-3.5" fill="none" aria-hidden="true">
                  <path d="M3 8.5l3 3 7-7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </span>
            <span className="text-base">{opt.label}</span>
          </button>
        )
      })}

      {q.allowCustom && (
        <CustomOptionRow
          type="checkbox"
          active={customActive}
          disabled={!customActive && countsTowardMax >= max}
          text={customActive ? customText(customVal!) : ""}
          separator={q.customSeparator ?? ","}
          onSelect={toggleCustom}
          onText={setCustomText}
        />
      )}
    </div>
  )
}

// "기타(직접입력)" 공통 UI — 라디오/체크박스 스타일 선택 + 인라인 텍스트 입력
function CustomOptionRow({
  type,
  active,
  disabled,
  text,
  separator,
  onSelect,
  onText,
}: {
  type: "radio" | "checkbox"
  active: boolean
  disabled?: boolean
  text: string
  separator?: string
  onSelect: () => void
  onText: (t: string) => void
}) {
  // 구분자가 지정된 경우(다중 입력) 입력값을 나눠 미리보기 항목으로 보여준다.
  const items =
    separator && text.trim()
      ? text
          .split(separator)
          .map((s) => s.trim())
          .filter(Boolean)
      : []
  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-xl border px-4 py-3 transition-colors",
        active ? "border-primary bg-primary/10" : "border-border bg-background",
        disabled && "cursor-not-allowed opacity-40",
      )}
    >
      <button
        type="button"
        onClick={onSelect}
        disabled={disabled}
        className="flex items-center gap-3 text-left"
        aria-pressed={active}
      >
        <span
          className={cn(
            "flex size-5 shrink-0 items-center justify-center border-2",
            type === "radio" ? "rounded-full" : "rounded-md",
            active
              ? type === "radio"
                ? "border-primary"
                : "border-primary bg-primary text-primary-foreground"
              : "border-muted-foreground/40",
          )}
        >
          {active &&
            (type === "radio" ? (
              <span className="size-2.5 rounded-full bg-primary" />
            ) : (
              <svg viewBox="0 0 16 16" className="size-3.5" fill="none" aria-hidden="true">
                <path d="M3 8.5l3 3 7-7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ))}
        </span>
        <span className="text-base">기타 (직접입력)</span>
      </button>
      {active && (
        <>
          <input
            type="text"
            autoFocus
            value={text}
            onChange={(e) => onText(e.target.value)}
            placeholder={separator ? `직접 입력 (여러 개는 '${separator}' 로 구분)` : "직접 입력하세요"}
            className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
          />
          {separator && items.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {items.map((it, i) => (
                <span
                  key={i}
                  className="rounded-full border border-primary/40 bg-background px-2.5 py-0.5 text-xs text-foreground"
                >
                  {it}
                </span>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
