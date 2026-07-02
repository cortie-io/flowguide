"use client"

import { cn } from "@/lib/utils"

const baseInput =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/30"

export function TextInput({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(baseInput, className)} {...props} />
}

export function TextArea({
  className,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(baseInput, "resize-y", className)} {...props} />
}

export function Select({
  className,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={cn(baseInput, "cursor-pointer", className)} {...props}>
      {children}
    </select>
  )
}

export function NumberInput({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input type="number" className={cn(baseInput, className)} {...props} />
}

export function Field({
  label,
  children,
  hint,
  className,
}: {
  label: string
  children: React.ReactNode
  hint?: string
  className?: string
}) {
  return (
    <label className={cn("flex flex-col gap-1.5", className)}>
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      {children}
      {hint && <span className="text-xs text-muted-foreground/80">{hint}</span>}
    </label>
  )
}

export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  label: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="flex items-center gap-2 text-sm"
    >
      <span
        className={cn(
          "relative h-5 w-9 rounded-full transition-colors",
          checked ? "bg-primary" : "bg-muted-foreground/30",
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 size-4 rounded-full bg-background transition-all",
            checked ? "left-4" : "left-0.5",
          )}
        />
      </span>
      <span className="text-muted-foreground">{label}</span>
    </button>
  )
}
