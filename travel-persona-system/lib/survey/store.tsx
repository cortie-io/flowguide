"use client"

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react"
import type { Survey, Answers } from "./types"
import { DEFAULT_SURVEY } from "./default-data"

const ANSWERS_KEY = "ta16.answers.v1"
const SAVE_DEBOUNCE_MS = 600

interface SurveyContextValue {
  survey: Survey
  setSurvey: (s: Survey) => void
  resetSurvey: () => void
  answers: Answers
  setAnswer: (id: string, value: Answers[string]) => void
  setAnswers: (a: Answers) => void
  clearAnswers: () => void
  hydrated: boolean
  saving: boolean
  saveError: string | null
}

const SurveyContext = createContext<SurveyContextValue | null>(null)

export function SurveyProvider({ children }: { children: React.ReactNode }) {
  const [survey, setSurveyState] = useState<Survey>(DEFAULT_SURVEY)
  const [answers, setAnswersState] = useState<Answers>({})
  const [hydrated, setHydrated] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 설문 데이터는 서버(DB)에서 불러오고, 진행 중인 응답은 브라우저에만 임시 저장한다
  useEffect(() => {
    let cancelled = false
    fetch("/api/survey")
      .then((res) => res.json())
      .then((data) => {
        if (!cancelled && data?.survey) setSurveyState(data.survey)
      })
      .catch(() => {
        // 서버 연결 실패 시 기본 설문으로 대체
      })
      .finally(() => {
        if (!cancelled) setHydrated(true)
      })

    try {
      const rawAnswers = localStorage.getItem(ANSWERS_KEY)
      if (rawAnswers) setAnswersState(JSON.parse(rawAnswers))
    } catch {
      // ignore
    }

    return () => {
      cancelled = true
    }
  }, [])

  // 편집기에서 매 입력마다 호출되므로, 서버 저장은 디바운스해서 과도한 요청을 막는다
  const persistSurvey = useCallback((s: Survey) => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(async () => {
      setSaving(true)
      setSaveError(null)
      try {
        const res = await fetch("/api/survey", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(s),
        })
        if (!res.ok) {
          const data = await res.json().catch(() => null)
          setSaveError(data?.error ?? "저장에 실패했어요.")
        }
      } catch {
        setSaveError("저장에 실패했어요.")
      } finally {
        setSaving(false)
      }
    }, SAVE_DEBOUNCE_MS)
  }, [])

  const setSurvey = useCallback(
    (s: Survey) => {
      setSurveyState(s)
      persistSurvey(s)
    },
    [persistSurvey],
  )

  const resetSurvey = useCallback(() => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    setSurveyState(DEFAULT_SURVEY)
    setSaving(true)
    setSaveError(null)
    fetch("/api/survey/reset", { method: "POST" })
      .then((res) => res.json())
      .then((data) => {
        if (data?.survey) setSurveyState(data.survey)
      })
      .catch(() => setSaveError("초기화에 실패했어요."))
      .finally(() => setSaving(false))
  }, [])

  const persistAnswers = useCallback((a: Answers) => {
    try {
      localStorage.setItem(ANSWERS_KEY, JSON.stringify(a))
    } catch {
      // ignore
    }
  }, [])

  const setAnswer = useCallback(
    (id: string, value: Answers[string]) => {
      setAnswersState((prev) => {
        const next = { ...prev, [id]: value }
        persistAnswers(next)
        return next
      })
    },
    [persistAnswers],
  )

  const setAnswers = useCallback(
    (a: Answers) => {
      setAnswersState(a)
      persistAnswers(a)
    },
    [persistAnswers],
  )

  const clearAnswers = useCallback(() => {
    setAnswersState({})
    try {
      localStorage.removeItem(ANSWERS_KEY)
    } catch {
      // ignore
    }
  }, [])

  return (
    <SurveyContext.Provider
      value={{
        survey,
        setSurvey,
        resetSurvey,
        answers,
        setAnswer,
        setAnswers,
        clearAnswers,
        hydrated,
        saving,
        saveError,
      }}
    >
      {children}
    </SurveyContext.Provider>
  )
}

export function useSurvey() {
  const ctx = useContext(SurveyContext)
  if (!ctx) throw new Error("useSurvey must be used within SurveyProvider")
  return ctx
}
