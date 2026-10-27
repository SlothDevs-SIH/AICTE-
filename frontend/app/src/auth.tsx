import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, hasRefresh, restoreSession, setTokens } from './api'

export type Me = { id: string; email: string; name: string; role: string; unit_id: string | null; region_id: string | null }
type Ctx = { me: Me | null; ready: boolean; login: (e: string, p: string) => Promise<void>; logout: () => Promise<void> }
const C = createContext<Ctx>(null as any)
export const useAuth = () => useContext(C)

export const ROLE_LABEL: Record<string, string> = {
  unit_officer: 'Unit officer', unit_supervisor: 'Unit supervisor', regional_officer: 'Regional officer',
  management: 'Management', competent_authority: 'Competent Authority', admin: 'Admin', auditor: 'Auditor',
}
export const OFFICER_ROLES = ['unit_officer', 'unit_supervisor', 'regional_officer']

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)
  const [ready, setReady] = useState(false)
  useEffect(() => {
    ;(async () => {
      try { if (hasRefresh() && (await restoreSession())) setMe(await api<Me>('/me')) } catch { setTokens(null, null) }
      setReady(true)
    })()
  }, [])
  const login = async (email: string, password: string) => {
    const t = await api('/auth/login', { method: 'POST', body: { email, password } })
    setTokens(t.access_token, t.refresh_token)
    setMe(await api<Me>('/me'))
  }
  const logout = async () => {
    setTokens(null, null)
    setMe(null)
  }
  return <C.Provider value={{ me, ready, login, logout }}>{children}</C.Provider>
}
