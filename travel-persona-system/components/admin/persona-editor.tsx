"use client"

import { useState } from "react"
import type { Persona, WeightFeature } from "@/lib/survey/types"
import { Field, TextInput, TextArea, NumberInput } from "./fields"
import { Button } from "@/components/ui/button"
import { ChevronDown, Trash2, Plus, X } from "lucide-react"
import { cn } from "@/lib/utils"

interface Props {
  persona: Persona
  weightFeatures: WeightFeature[]
  onChange: (patch: Partial<Persona>) => void
  onDelete: () => void
}

export function PersonaEditor({ persona: p, weightFeatures, onChange, onDelete }: Props) {
  const [open, setOpen] = useState(false)

  const overrides = p.weightOverrides ?? {}
  const overrideCount = Object.keys(overrides).length

  function setList(key: "strengths" | "tips", list: string[]) {
    onChange({ [key]: list })
  }
  function addListItem(key: "strengths" | "tips") {
    setList(key, [...(p[key] ?? []), ""])
  }
  function changeListItem(key: "strengths" | "tips", idx: number, value: string) {
    setList(
      key,
      (p[key] ?? []).map((v, i) => (i === idx ? value : v)),
    )
  }
  function removeListItem(key: "strengths" | "tips", idx: number) {
    setList(
      key,
      (p[key] ?? []).filter((_, i) => i !== idx),
    )
  }

  function setOverride(featureId: string, value: string) {
    const next = { ...overrides }
    if (value.trim() === "") {
      delete next[featureId]
    } else {
      next[featureId] = Number(value)
    }
    onChange({ weightOverrides: next })
  }

  return (
    <div className="rounded-2xl border border-border bg-card">
      {/* Header row */}
      <div className="flex items-center gap-2 p-3">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex flex-1 items-center gap-3 text-left"
          aria-expanded={open}
        >
          <ChevronDown
            className={cn("size-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")}
            aria-hidden="true"
          />
          <span className="shrink-0 rounded-md bg-foreground px-2 py-0.5 font-mono text-xs text-background">
            {p.code || "----"}
          </span>
          <span className="line-clamp-1 flex-1 text-sm font-medium">{p.name || "(이름 없음)"}</span>
          <span className="hidden max-w-[40%] shrink-0 truncate text-xs text-muted-foreground sm:inline">{p.tag}</span>
          {overrideCount > 0 && (
            <span className="hidden shrink-0 rounded-full bg-secondary px-2 py-0.5 font-mono text-[10px] text-secondary-foreground md:inline">
              가중치 {overrideCount}
            </span>
          )}
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
          aria-label="유형 삭제"
        >
          <Trash2 className="size-4" aria-hidden="true" />
        </button>
      </div>

      {open && (
        <div className="border-t border-border p-4">
          <div className="grid gap-3 md:grid-cols-3">
            <Field label="코드" hint="축 코드 조합">
              <TextInput
                value={p.code}
                className="font-mono uppercase"
                onChange={(e) => onChange({ code: e.target.value.toUpperCase() })}
              />
            </Field>
            <Field label="유형 이름" className="md:col-span-2">
              <TextInput value={p.name} onChange={(e) => onChange({ name: e.target.value })} />
            </Field>
          </div>

          <Field label="태그라인" className="mt-3">
            <TextInput value={p.tag} onChange={(e) => onChange({ tag: e.target.value })} />
          </Field>

          <Field label="해설 (설명 문단)" className="mt-3">
            <TextArea
              rows={4}
              value={p.description ?? ""}
              placeholder="이 유형이 여행을 즐기는 방식, 특징 등을 자유롭게 설명하세요."
              onChange={(e) => onChange({ description: e.target.value || undefined })}
            />
          </Field>

          {/* Strengths list */}
          <ListEditor
            title="강점 / 키워드"
            items={p.strengths ?? []}
            placeholder="예: 즉흥적인 분위기 메이커"
            onAdd={() => addListItem("strengths")}
            onChangeItem={(i, v) => changeListItem("strengths", i, v)}
            onRemoveItem={(i) => removeListItem("strengths", i)}
          />

          {/* Tips list */}
          <ListEditor
            title="여행 팁"
            items={p.tips ?? []}
            placeholder="예: 페스티벌·야시장 일정을 먼저 확인하세요."
            onAdd={() => addListItem("tips")}
            onChangeItem={(i, v) => changeListItem("tips", i, v)}
            onRemoveItem={(i) => removeListItem("tips", i)}
          />

          {/* Weight overrides */}
          <div className="mt-5 rounded-xl border border-border bg-secondary/30 p-3">
            <p className="text-sm font-medium">유형별 가중치 조정 (선택)</p>
            <p className="mt-1 text-xs text-muted-foreground">
              비워두면 기본 base 값을 사용해요. 값을 입력하면 이 유형에서만 해당 가중치의 base 가 대체됩니다.
            </p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {weightFeatures.map((f) => (
                <label key={f.id} className="flex items-center gap-2">
                  <span className="flex-1 truncate text-xs text-muted-foreground" title={f.label}>
                    {f.label}
                  </span>
                  <NumberInput
                    step="0.05"
                    className="w-24"
                    placeholder={`${f.base}`}
                    value={typeof overrides[f.id] === "number" ? overrides[f.id] : ""}
                    onChange={(e) => setOverride(f.id, e.target.value)}
                  />
                </label>
              ))}
              {weightFeatures.length === 0 && (
                <p className="text-xs text-muted-foreground">가중치 항목이 없어요. 가중치 탭에서 추가하세요.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ListEditor({
  title,
  items,
  placeholder,
  onAdd,
  onChangeItem,
  onRemoveItem,
}: {
  title: string
  items: string[]
  placeholder?: string
  onAdd: () => void
  onChangeItem: (idx: number, value: string) => void
  onRemoveItem: (idx: number) => void
}) {
  return (
    <div className="mt-4">
      <p className="mb-1.5 text-xs font-medium text-muted-foreground">{title}</p>
      <div className="flex flex-col gap-2">
        {items.map((item, i) => (
          <div key={i} className="flex items-center gap-2">
            <TextInput value={item} placeholder={placeholder} onChange={(e) => onChangeItem(i, e.target.value)} />
            <button
              type="button"
              onClick={() => onRemoveItem(i)}
              className="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
              aria-label="항목 삭제"
            >
              <X className="size-4" aria-hidden="true" />
            </button>
          </div>
        ))}
      </div>
      <Button variant="outline" size="sm" onClick={onAdd} className="mt-2 gap-1.5 rounded-full bg-transparent">
        <Plus className="size-3.5" aria-hidden="true" />
        {title} 추가
      </Button>
    </div>
  )
}
