import "server-only"
import { cookies } from "next/headers"
import { randomBytes } from "crypto"
import { prisma } from "@/lib/db"

const COOKIE_NAME = process.env.SESSION_COOKIE_NAME || "ta16_session"
const SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000 // 30일

export interface SessionUser {
  id: string
  name: string
  username: string
  email: string | null
  isAdmin: boolean
}

export async function createSession(userId: string) {
  const token = randomBytes(32).toString("hex")
  const expiresAt = new Date(Date.now() + SESSION_TTL_MS)
  await prisma.session.create({ data: { token, userId, expiresAt } })

  const cookieStore = await cookies()
  cookieStore.set(COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    expires: expiresAt,
  })
}

export async function destroySession() {
  const cookieStore = await cookies()
  const token = cookieStore.get(COOKIE_NAME)?.value
  if (token) {
    await prisma.session.delete({ where: { token } }).catch(() => {})
  }
  cookieStore.delete(COOKIE_NAME)
}

export async function getSessionUser(): Promise<SessionUser | null> {
  const cookieStore = await cookies()
  const token = cookieStore.get(COOKIE_NAME)?.value
  if (!token) return null

  const session = await prisma.session.findUnique({ where: { token }, include: { user: true } })
  if (!session) return null

  if (session.expiresAt < new Date()) {
    await prisma.session.delete({ where: { token } }).catch(() => {})
    return null
  }

  return {
    id: session.user.id,
    name: session.user.name,
    username: session.user.username,
    email: session.user.email,
    isAdmin: session.user.isAdmin,
  }
}

export async function getAdminUser(): Promise<SessionUser | null> {
  const user = await getSessionUser()
  return user?.isAdmin ? user : null
}
