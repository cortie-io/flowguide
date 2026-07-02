import "dotenv/config"
import fs from "node:fs"
import path from "node:path"
import bcrypt from "bcryptjs"
import { PrismaClient } from "../generated/prisma/client"
import { PrismaBetterSqlite3 } from "@prisma/adapter-better-sqlite3"

const adapter = new PrismaBetterSqlite3({ url: process.env.DATABASE_URL ?? "file:./prisma/dev.db" })
const prisma = new PrismaClient({ adapter })

// 요청받은 초기 관리자 계정 3개. 이미 있으면 비밀번호는 건드리지 않고 관리자 권한만 보장한다.
const ADMINS = [
  { username: "whgur06", password: "Whgur2006!" },
  { username: "cortie", password: "kkh^^4289c3" },
  { username: "shkevin1234", password: "song-an1" },
]

interface DocSeed {
  slug: string
  title: string
  category: string
  order: number
  content: string
}

async function seedDocs() {
  const manifestPath = path.join(__dirname, "seed-docs.json")
  const docs: DocSeed[] = JSON.parse(fs.readFileSync(manifestPath, "utf8"))
  for (const doc of docs) {
    const existing = await prisma.doc.findUnique({ where: { slug: doc.slug } })
    if (existing) {
      console.log(`이미 존재하는 문서 - 건너뜀: ${doc.slug}`)
      continue
    }
    await prisma.doc.create({
      data: { slug: doc.slug, title: doc.title, category: doc.category, order: doc.order, content: doc.content },
    })
    console.log(`문서 생성: ${doc.slug}`)
  }
}

async function main() {
  for (const admin of ADMINS) {
    const existing = await prisma.user.findUnique({ where: { username: admin.username } })
    if (existing) {
      await prisma.user.update({ where: { username: admin.username }, data: { isAdmin: true } })
      console.log(`이미 존재하는 계정 - 관리자 권한만 갱신: ${admin.username}`)
      continue
    }
    const passwordHash = await bcrypt.hash(admin.password, 10)
    await prisma.user.create({
      data: {
        name: admin.username,
        username: admin.username,
        passwordHash,
        isAdmin: true,
      },
    })
    console.log(`관리자 계정 생성: ${admin.username}`)
  }

  await seedDocs()
}

main()
  .catch((e) => {
    console.error(e)
    process.exitCode = 1
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
