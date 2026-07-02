import "server-only"
import { prisma } from "@/lib/db"
import { DEFAULT_SURVEY } from "./default-data"
import type { Survey } from "./types"

const SURVEY_ID = "default"

export async function getSurvey(): Promise<Survey> {
  const row = await prisma.surveyConfig.findUnique({ where: { id: SURVEY_ID } })
  if (!row) {
    await prisma.surveyConfig.create({ data: { id: SURVEY_ID, data: JSON.stringify(DEFAULT_SURVEY) } })
    return DEFAULT_SURVEY
  }
  try {
    return JSON.parse(row.data) as Survey
  } catch {
    return DEFAULT_SURVEY
  }
}

export async function saveSurvey(survey: Survey): Promise<void> {
  await prisma.surveyConfig.upsert({
    where: { id: SURVEY_ID },
    update: { data: JSON.stringify(survey) },
    create: { id: SURVEY_ID, data: JSON.stringify(survey) },
  })
}

export async function resetSurvey(): Promise<Survey> {
  await saveSurvey(DEFAULT_SURVEY)
  return DEFAULT_SURVEY
}

export function isValidSurvey(value: unknown): value is Survey {
  if (!value || typeof value !== "object") return false
  const v = value as Record<string, unknown>
  return (
    Array.isArray(v.questions) &&
    Array.isArray(v.axes) &&
    Array.isArray(v.personas) &&
    Array.isArray(v.sections) &&
    Array.isArray(v.weightFeatures)
  )
}
