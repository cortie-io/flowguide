// 성향 테스트 스키마 타입 정의
// 모든 문항, 응답 방식, 선택지, 가중치, 축, 유형이 이 스키마로 표현되며
// 관리자 에디터에서 전부 수정 가능하다.

export type PartId = "A" | "B" | "C"

export type QuestionType =
  | "likert" // 5점 리커트 (채점됨 - Part A)
  | "scale" // 1~5 척도 (원값 저장 - Part B/C)
  | "single" // 단일 선택
  | "multi" // 다중 선택
  | "text" // 자유 입력
  | "number" // 숫자 입력
  | "date" // 날짜 입력
  | "slider" // 축 오버라이드 슬라이더 (1~5, 미조작 시 null)

export interface Axis {
  id: string
  name: string // 사교성
  field: string // social_score
  lowLabel: string // Private(프라이빗)
  highLabel: string // Social(소셜)
  lowCode: string // P
  highCode: string // S
  colorVar: string // css 변수 토큰 (예: --chart-1)
  threshold?: number // 이 축의 고/저 분기 임계값(0~1). 없으면 전역 axisThreshold 사용
}

// 유형 산출 계산 과정 설정 — 관리자에서 전부 수정 가능
export interface ScoringConfig {
  axisThreshold: number // 축 점수가 이 값 이상이면 highCode (기본 0.5)
  neutralScore: number // 응답이 없을 때 사용할 기본 점수 (기본 0.5)
  weightPivot: number // 가중치 공식의 기준점: base + k×(축점수 − pivot) (기본 0.5)
  weightClampMin: number // 가중치 하한값 (기본 0)
}

export interface QuestionOption {
  id: string
  label: string
}

export interface Question {
  id: string
  field?: string // 데이터에 저장될 필드명(키). 비우면 id 사용
  part: PartId
  sectionId: string
  text: string
  type: QuestionType
  required?: boolean
  helpText?: string

  // 채점 (likert 전용)
  axisId?: string
  direction?: "forward" | "reverse"

  // 척도/리커트 라벨
  points?: number // 기본 5
  scaleLabels?: string[] // likert 5개 라벨
  lowLabel?: string // scale/slider 좌측 끝 라벨
  highLabel?: string // scale/slider 우측 끝 라벨

  // 선택지 (single/multi)
  options?: QuestionOption[]
  maxSelect?: number
  allowCustom?: boolean
  customSeparator?: string // multi 기타 입력에서 여러 항목을 나누는 구분자 (기본 ",")

  // number
  min?: number

  // 조건부 노출 안내 (UI에는 표시만)
  conditional?: boolean
  conditionNote?: string

  // slider 가 연동되는 축
  overrideAxisId?: string
}

export interface Section {
  id: string
  part: PartId
  title: string
  description?: string
}

// weight = base + k × (axis_score - 0.5)
export interface WeightFeature {
  id: string
  label: string
  base: number
  k: number
  axisId?: string // 연동 축 (없으면 빈 문자열)
}

export interface PersonaCompanionNote {
  label: string // 예: 연인과 함께
  text: string
}

export interface Persona {
  code: string // SAEF
  name: string // 페스티벌 수달
  tag: string // 흥 따라, 사람 따라, 순간 따라
  description?: string // 유형 해설(설명 문단)
  strengths?: string[] // 강점/키워드
  tips?: string[] // 여행 팁/추천
  companions?: PersonaCompanionNote[] // 동행자에 따라 달라지는 모습
  catchphrases?: string[] // 이 유형이 자주 하는 말
  motto?: string // 한 줄 모토
  docSlug?: string // /docs/{docSlug} 상세 문서 링크
  // 유형별 가중치 오버라이드: weightFeature.id → 대체할 base 값
  // 지정되지 않은 항목은 기본 base 를 사용한다.
  weightOverrides?: Record<string, number>
}

export interface Survey {
  version: string
  title: string
  subtitle: string
  axes: Axis[]
  sections: Section[]
  questions: Question[]
  personas: Persona[]
  weightFeatures: WeightFeature[]
  scoring?: ScoringConfig // 계산 과정 설정 (없으면 기본값 사용)
}

// 응답 값
export type AnswerValue = number | string | string[] | null
export type Answers = Record<string, AnswerValue>
