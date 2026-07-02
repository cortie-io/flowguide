import fs from "node:fs"
import path from "node:path"

const SRC = "/home/ubuntu/personal/docs/docs"
const ROOT = "/home/ubuntu/personal/travel-persona-system"
const OUT_GUIDE = path.join(ROOT, "content/docs/guide")
const OUT_TYPES = path.join(ROOT, "content/docs/types")

const GUIDE_FILES = [
  { src: "travel-mbti/00-overview.md", slug: "overview", order: 0 },
  { src: "travel-mbti/01-questionnaire-a-personality.md", slug: "questionnaire-a", order: 1 },
  { src: "travel-mbti/02-questionnaire-b-profile.md", slug: "questionnaire-b", order: 2 },
  { src: "travel-mbti/03-questionnaire-c-trip.md", slug: "questionnaire-c", order: 3 },
  { src: "travel-mbti/04-reference.md", slug: "reference", order: 4 },
  { src: "restaurant-recommendation-design.md", slug: "restaurant-recommendation-design", order: 5 },
]

const TYPE_FILES = [
  ["SAEF", "SAEF-수달.md"],
  ["SAEJ", "SAEJ-플라밍고.md"],
  ["SAVF", "SAVF-원숭이.md"],
  ["SAVJ", "SAVJ-꿀벌.md"],
  ["SCEF", "SCEF-사자.md"],
  ["SCEJ", "SCEJ-백조.md"],
  ["SCVF", "SCVF-참새.md"],
  ["SCVJ", "SCVJ-펭귄.md"],
  ["PAEF", "PAEF-여우.md"],
  ["PAEJ", "PAEJ-매.md"],
  ["PAVF", "PAVF-낙타.md"],
  ["PAVJ", "PAVJ-다람쥐.md"],
  ["PCEF", "PCEF-판다.md"],
  ["PCEJ", "PCEJ-거북이.md"],
  ["PCVF", "PCVF-코알라.md"],
  ["PCVJ", "PCVJ-비버.md"],
]

const linkRewrites = [
  ["(00-overview.md)", "(/docs/overview)"],
  ["(01-questionnaire-a-personality.md)", "(/docs/questionnaire-a)"],
  ["(02-questionnaire-b-profile.md)", "(/docs/questionnaire-b)"],
  ["(03-questionnaire-c-trip.md)", "(/docs/questionnaire-c)"],
  ["(04-reference.md)", "(/docs/reference)"],
  ["(../restaurant-recommendation-design.md)", "(/docs/restaurant-recommendation-design)"],
  ["(travel-mbti/00-overview.md)", "(/docs/overview)"],
  ["(travel-mbti/04-reference.md)", "(/docs/reference)"],
  ["(../04-reference.md)", "(/docs/reference)"],
  ["(../../restaurant-recommendation-design.md)", "(/docs/restaurant-recommendation-design)"],
  ["[types/](types)", "[types/](/docs)"],
]
for (const [code, file] of TYPE_FILES) {
  linkRewrites.push([`(types/${file})`, `(/docs/type-${code.toLowerCase()})`])
}

function rewriteLinks(content) {
  let out = content
  for (const [from, to] of linkRewrites) out = out.split(from).join(to)
  return out
}

function readSrc(rel) {
  return fs.readFileSync(path.join(SRC, rel), "utf8")
}

function titleFromContent(content) {
  const m = content.match(/^# (.+)$/m)
  return m ? m[1].trim() : "제목 없음"
}

fs.mkdirSync(OUT_GUIDE, { recursive: true })
fs.mkdirSync(OUT_TYPES, { recursive: true })

const manifest = []

for (const g of GUIDE_FILES) {
  let content = readSrc(g.src)
  content = rewriteLinks(content).trimEnd() + "\n"
  const title = titleFromContent(content)
  fs.writeFileSync(path.join(OUT_GUIDE, `${g.slug}.md`), content, "utf8")
  manifest.push({ slug: g.slug, title, category: "guide", order: g.order, content })
}

// ---- section parsing helpers for type docs ----
function splitSections(content) {
  // Splits on top-level (## ) headings. Returns map heading-title -> body text.
  const parts = content.split(/\n(?=## )/g)
  const map = {}
  for (const part of parts) {
    const m = part.match(/^## (.+?)\n([\s\S]*)$/)
    if (!m) continue
    map[m[1].trim()] = m[2].trim()
  }
  return map
}

function bulletLines(body) {
  return body
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.startsWith("- "))
    .map((l) => l.slice(2).trim())
}

function parseLabeledBullets(body) {
  return bulletLines(body)
    .map((line) => {
      const m = line.match(/^\*\*(.+?)\*\*:\s*(.+)$/)
      if (!m) return null
      return { label: m[1].trim(), text: m[2].trim() }
    })
    .filter(Boolean)
}

function parseCatchphrases(body) {
  return bulletLines(body).map((l) => l.replace(/^"(.*)"$/, "$1"))
}

function parseMotto(body) {
  const m = body.match(/^>\s*"?(.+?)"?\s*$/m)
  return m ? m[1].trim() : body.trim()
}

const personaDetails = {}

for (const [code, file] of TYPE_FILES) {
  let raw = readSrc(`travel-mbti/types/${file}`)
  // fix a heading-level typo present in the source (### instead of ##)
  raw = raw.replace(/^### 4\. 음식 스타일$/m, "## 4. 음식 스타일")

  const rewritten = rewriteLinks(raw).trimEnd() + "\n"
  const slug = `type-${code.toLowerCase()}`
  const title = titleFromContent(rewritten)
  fs.writeFileSync(path.join(OUT_TYPES, `${slug}.md`), rewritten, "utf8")
  manifest.push({
    slug,
    title,
    category: "type",
    order: TYPE_FILES.findIndex(([c]) => c === code),
    content: rewritten,
  })

  const sections = splitSections(rewritten)
  const introBody = sections["1. 이 유형은 이런 사람이에요"] ?? ""
  const description = introBody
    .split("\n\n")
    .map((p) => p.trim())
    .filter(Boolean)
    .join("\n\n")
  const strengths = bulletLines(sections["7. 여행 중 강점"] ?? "")
  const tips = parseLabeledBullets(sections["8. 여행 중 주의할 점 & 성장 팁"] ?? "").map(
    (t) => `${t.label}: ${t.text}`,
  )
  const companions = parseLabeledBullets(sections["6. 동행자에 따라 달라지는 모습"] ?? "")
  const catchphrases = parseCatchphrases(sections["11. 이 유형이 자주 하는 말"] ?? "")
  const motto = parseMotto(sections["한 줄 모토"] ?? "")

  personaDetails[code] = { description, strengths, tips, companions, catchphrases, motto, docSlug: slug }
}

fs.writeFileSync(path.join(ROOT, "prisma/seed-docs.json"), JSON.stringify(manifest, null, 2), "utf8")

const tsOut = `// 자동 생성 파일 — scripts/build-docs.mjs 로 재생성한다. 직접 수정하지 말 것.
import type { Persona } from "./types"

export const PERSONA_DETAILS: Record<
  string,
  Pick<Persona, "description" | "strengths" | "tips" | "companions" | "catchphrases" | "motto" | "docSlug">
> = ${JSON.stringify(personaDetails, null, 2)}
`
fs.writeFileSync(path.join(ROOT, "lib/survey/persona-details.generated.ts"), tsOut, "utf8")

console.log(`guide docs: ${GUIDE_FILES.length}, type docs: ${TYPE_FILES.length}`)
console.log("wrote prisma/seed-docs.json and lib/survey/persona-details.generated.ts")
