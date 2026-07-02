import type { Survey, Answers, Axis, Question, Persona, ScoringConfig } from "./types"

// 계산 과정 기본값 — survey.scoring 이 없으면(구버전 데이터) 이 값을 사용
export const DEFAULT_SCORING: ScoringConfig = {
  axisThreshold: 0.5,
  neutralScore: 0.5,
  weightPivot: 0.5,
  weightClampMin: 0,
}

export function getScoring(survey: Survey): ScoringConfig {
  return { ...DEFAULT_SCORING, ...(survey.scoring ?? {}) }
}

// 특정 축의 고/저 분기 임계값 — 축별 오버라이드가 있으면 우선
function axisThresholdFor(axis: Axis, cfg: ScoringConfig): number {
  return typeof axis.threshold === "number" ? axis.threshold : cfg.axisThreshold
}

// 문항의 데이터 키(필드명). field 가 지정돼 있으면 그것을, 없으면 id 를 사용
export function answerKey(q: Question): string {
  const f = q.field?.trim()
  return f && f.length > 0 ? f : q.id
}

export interface AxisScore {
  axis: Axis
  score: number // 0~1 (평소)
  effective: number // 0~1 (Part C 오버라이드 반영)
  code: string // 이분화된 코드 문자
  overridden: boolean
  answeredCount: number
}

export interface WeightResult {
  id: string
  label: string
  value: number
  base: number
  contribution: number // k*(score-0.5)
  axisId: string
  overridden: boolean // 유형별 base 오버라이드 적용 여부
}

// 리커트 정규화: 정채점 (v-1)/4, 역채점 (5-v)/4 → 0~1
export function normalizeLikert(value: number, direction: "forward" | "reverse", points = 5): number {
  const max = points - 1
  if (direction === "reverse") return (points - value) / max
  return (value - 1) / max
}

// Part A 채점 → 4개 축 연속 점수
export function computeAxisScores(survey: Survey, answers: Answers): AxisScore[] {
  const cfg = getScoring(survey)
  return survey.axes.map((axis) => {
    const likertQs = survey.questions.filter(
      (q) => q.part === "A" && q.type === "likert" && q.axisId === axis.id,
    )
    const values: number[] = []
    for (const q of likertQs) {
      const v = answers[answerKey(q)]
      if (typeof v === "number") {
        values.push(normalizeLikert(v, q.direction ?? "forward", q.points ?? 5))
      }
    }
    const score = values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : cfg.neutralScore

    // Part C 슬라이더 오버라이드
    const overrideQ = survey.questions.find(
      (q) => q.type === "slider" && q.overrideAxisId === axis.id,
    )
    let effective = score
    let overridden = false
    if (overrideQ) {
      const ov = answers[answerKey(overrideQ)]
      if (typeof ov === "number") {
        effective = (ov - 1) / ((overrideQ.points ?? 5) - 1)
        overridden = true
      }
    }

    const threshold = axisThresholdFor(axis, cfg)
    const code = score >= threshold ? axis.highCode : axis.lowCode
    return { axis, score, effective, code, overridden, answeredCount: values.length }
  })
}

export function personaCode(scores: AxisScore[]): string {
  return scores.map((s) => s.code).join("")
}

// 오버라이드 반영 코드 (effective 기준)
export function effectivePersonaCode(scores: AxisScore[], survey?: Survey): string {
  const cfg = survey ? getScoring(survey) : DEFAULT_SCORING
  return scores
    .map((s) => {
      const threshold = typeof s.axis.threshold === "number" ? s.axis.threshold : cfg.axisThreshold
      return s.effective >= threshold ? s.axis.highCode : s.axis.lowCode
    })
    .join("")
}

// 가중치 계산: weight = base + k × (effective_score - pivot)
// persona 가 주어지면 해당 유형의 base 오버라이드를 우선 적용한다.
export function computeWeights(survey: Survey, scores: AxisScore[], persona?: Persona): WeightResult[] {
  const cfg = getScoring(survey)
  const byAxis = new Map(scores.map((s) => [s.axis.id, s.effective]))
  const overrides = persona?.weightOverrides ?? {}
  return survey.weightFeatures.map((f) => {
    const base = typeof overrides[f.id] === "number" ? overrides[f.id] : f.base
    const axisScore = f.axisId ? (byAxis.get(f.axisId) ?? cfg.neutralScore) : cfg.neutralScore
    const contribution = f.k * (axisScore - cfg.weightPivot)
    return {
      id: f.id,
      label: f.label,
      base,
      contribution,
      value: Math.max(cfg.weightClampMin, base + contribution),
      axisId: f.axisId ?? "",
      overridden: typeof overrides[f.id] === "number",
    }
  })
}

export function findPersona(survey: Survey, code: string) {
  return survey.personas.find((p) => p.code === code)
}

// 정반대 유형 코드 계산
export function oppositeCode(survey: Survey, scores: AxisScore[]): string {
  return scores
    .map((s) => (s.code === s.axis.highCode ? s.axis.lowCode : s.axis.highCode))
    .join("")
}

// Part A 응답 완료율
export function partACompletion(survey: Survey, answers: Answers): number {
  const qs = survey.questions.filter((q) => q.part === "A")
  const done = qs.filter((q) => typeof answers[answerKey(q)] === "number").length
  return qs.length === 0 ? 0 : done / qs.length
}
