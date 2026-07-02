import { NextResponse } from "next/server"
import { getSessionUser } from "@/lib/auth/session"

export async function GET() {
  const user = await getSessionUser()
  return NextResponse.json({
    user: user
      ? { name: user.name, username: user.username, email: user.email, isAdmin: user.isAdmin }
      : null,
  })
}
