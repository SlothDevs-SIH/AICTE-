// Thin API client. Access token lives in memory; the refresh token in sessionStorage so a reload keeps the demo session.
export class ApiError extends Error {
  status: number
  code: string
  details: Record<string, any>
  constructor(status: number, code: string, message: string, details: Record<string, any> = {}) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
  }
}

let access: string | null = null
let refreshing: Promise<boolean> | null = null
const RT = 'samanvay_rt'

export const setTokens = (a: string | null, r: string | null) => {
  access = a
  try {
    if (r) sessionStorage.setItem(RT, r)
    else sessionStorage.removeItem(RT)
  } catch {}
}
export const hasRefresh = () => {
  try { return !!sessionStorage.getItem(RT) } catch { return false }
}

async function refresh(): Promise<boolean> {
  let rt: string | null = null
  try { rt = sessionStorage.getItem(RT) } catch {}
  if (!rt) return false
  const r = await fetch('/api/v1/auth/refresh', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: rt }) })
  if (!r.ok) { setTokens(null, null); return false }
  const j = await r.json()
  setTokens(j.access_token, j.refresh_token)
  return true
}

export const restoreSession = refresh

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown; raw?: boolean } = {}): Promise<T> {
  const go = () => fetch('/api/v1' + path, {
    method: opts.method ?? 'GET',
    headers: { ...(opts.body ? { 'Content-Type': 'application/json' } : {}), ...(access ? { Authorization: `Bearer ${access}` } : {}) },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  })
  let r = await go()
  if (r.status === 401 && !path.startsWith('/auth/')) {
    refreshing ??= refresh().finally(() => { refreshing = null })
    if (await refreshing) r = await go()
  }
  if (opts.raw) return r as unknown as T
  if (r.status === 204) return undefined as T
  const j = await r.json().catch(() => ({}))
  if (!r.ok) {
    const e = j.error ?? {}
    throw new ApiError(r.status, e.code ?? 'error', e.message ?? 'Request failed', e.details ?? {})
  }
  return j as T
}

export const qs = (o: Record<string, string | number | boolean | undefined | null>) => {
  const p = new URLSearchParams()
  Object.entries(o).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') p.set(k, String(v)) })
  const s = p.toString()
  return s ? '?' + s : ''
}
