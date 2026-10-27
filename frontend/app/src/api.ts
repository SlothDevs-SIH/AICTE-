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

export async function upload<T = any>(path: string, form: FormData): Promise<T> {
  const go = () => fetch('/api/v1' + path, { method: 'POST', headers: access ? { Authorization: `Bearer ${access}` } : {}, body: form })
  let r = await go()
  if (r.status === 401) {
    refreshing ??= refresh().finally(() => { refreshing = null })
    if (await refreshing) r = await go()
  }
  const j = await r.json().catch(() => ({}))
  if (!r.ok) {
    const e = j.error ?? {}
    throw new ApiError(r.status, e.code ?? 'error', e.message ?? 'Upload failed', e.details ?? {})
  }
  return j as T
}

export async function download(path: string, filename: string) {
  const res: Response = await api(path, { raw: true })
  if (!res.ok) throw new ApiError(res.status, 'download_failed', 'Could not download the file.')
  const blob = await res.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}

export function openStream(onEvent: (kind: string, data: any) => void, onFail: () => void): () => void {
  const ctl = new AbortController()
  ;(async () => {
    try {
      const r = await fetch('/api/v1/stream', { headers: access ? { Authorization: `Bearer ${access}` } : {}, signal: ctl.signal })
      if (!r.ok || !r.body) return onFail()
      const reader = r.body.getReader()
      const dec = new TextDecoder()
      let buf = ''
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        let i
        while ((i = buf.indexOf("\n\n")) >= 0) {
          const block = buf.slice(0, i)
          buf = buf.slice(i + 2)
          const kind = /event: (.*)/.exec(block)?.[1] ?? 'message'
          const data = /data: (.*)/.exec(block)?.[1]
          try { onEvent(kind, data ? JSON.parse(data) : null) } catch {}
        }
      }
      onFail()
    } catch {
      if (!ctl.signal.aborted) onFail()
    }
  })()
  return () => ctl.abort()
}

export const qs = (o: Record<string, string | number | boolean | undefined | null>) => {
  const p = new URLSearchParams()
  Object.entries(o).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') p.set(k, String(v)) })
  const s = p.toString()
  return s ? '?' + s : ''
}
