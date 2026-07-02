"use client"

import { createContext, useCallback, useContext, useEffect, useState } from "react"

export interface User {
  name: string
  username: string
  email: string | null
  isAdmin: boolean
}

export interface SignupInput {
  name: string
  username: string
  email: string
  birthDate: string
  password: string
}

interface AuthResult {
  ok: boolean
  error?: string
}

interface AuthContextValue {
  user: User | null
  hydrated: boolean
  login: (identifier: string, password: string) => Promise<AuthResult>
  signup: (input: SignupInput) => Promise<AuthResult>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

async function parseResponse(res: Response): Promise<{ user?: User; error?: string }> {
  try {
    return await res.json()
  } catch {
    return {}
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetch("/api/auth/me")
      .then((res) => parseResponse(res))
      .then((data) => {
        if (!cancelled) setUser(data.user ?? null)
      })
      .catch(() => {
        // ignore
      })
      .finally(() => {
        if (!cancelled) setHydrated(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (identifier: string, password: string): Promise<AuthResult> => {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier, password }),
    })
    const data = await parseResponse(res)
    if (!res.ok || !data.user) {
      return { ok: false, error: data.error ?? "문제가 발생했어요." }
    }
    setUser(data.user)
    return { ok: true }
  }, [])

  const signup = useCallback(async (input: SignupInput): Promise<AuthResult> => {
    const res = await fetch("/api/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    })
    const data = await parseResponse(res)
    if (!res.ok || !data.user) {
      return { ok: false, error: data.error ?? "문제가 발생했어요." }
    }
    setUser(data.user)
    return { ok: true }
  }, [])

  const logout = useCallback(async () => {
    setUser(null)
    try {
      await fetch("/api/auth/logout", { method: "POST" })
    } catch {
      // ignore
    }
  }, [])

  return (
    <AuthContext.Provider value={{ user, hydrated, login, signup, logout }}>{children}</AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
