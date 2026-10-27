import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { api, ApiError } from '../api'

export function Logo({ size = 32 }: { size?: number }) {
  return (
    <span className="logo" style={{ width: size, height: size }} aria-hidden="true">
      <svg viewBox="0 0 32 32" width={size * 0.8} height={size * 0.8}><path d="M9 21c0-6 5-9 9-9h5M23 12l-3-3m3 3-3 3M9 21h8" stroke="#d6f36b" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
    </span>
  )
}

export function useFetch<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(true)
  const [stamp, setStamp] = useState<number | null>(null)
  const alive = useRef(true)
  const load = useCallback(async () => {
    if (!path) return
    try {
      const d = await api<T>(path)
      if (alive.current) { setData(d); setError(null); setStamp(Date.now()) }
    } catch (e) {
      if (alive.current) setError(e as ApiError)
    } finally {
      if (alive.current) setLoading(false)
    }
  }, [path])
  useEffect(() => {
    alive.current = true
    setLoading(true)
    load()
    return () => { alive.current = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load, ...deps])
  return { data, error, loading, reload: load, stamp }
}

export function Loading({ what = 'data' }: { what?: string }) {
  return <p className="muted" role="status">Loading {what}…</p>
}
export function ErrorBox({ error, retry }: { error: ApiError | Error; retry?: () => void }) {
  return (
    <div className="notice err" role="alert">
      <strong>Could not load.</strong> {error.message}{' '}
      {retry && <button className="btn sm" onClick={retry}>Try again</button>}
    </div>
  )
}
export function Empty({ children }: { children: ReactNode }) {
  return <div className="card muted" role="status">{children}</div>
}

const STATE_STYLE: Record<string, [string, string]> = {
  RECEIVED: ['b-neutral', 'Received'], ASSIGNED: ['b-info', 'Assigned'], UNDER_PROCESS: ['b-info', 'Under process'],
  TRANSFERRED: ['b-violet', 'Transferred'], ESCALATED: ['b-orange', 'Escalated'], DISPOSED: ['b-ok', 'Disposed'],
  REOPENED: ['b-warn', 'Reopened'],
}
export function StatePill({ state, level }: { state: string; level?: number }) {
  const [cls, label] = STATE_STYLE[state] ?? ['b-neutral', state]
  return <span className={`badge ${cls}`}>{state === 'ESCALATED' && level ? `${label} (Level ${level})` : label}</span>
}
export function Severity({ s }: { s: string | null | undefined }) {
  if (!s) return null
  const m: Record<string, [string, string, string]> = {
    CONFLICT: ['b-danger', '⛨', 'Conflict'], RELATED: ['b-warn', '△', 'Related'],
    SYSTEMIC: ['b-violet', '☰', 'Systemic'], CLEAR: ['b-ok', '✓', 'Clear'],
  }
  const [c, i, t] = m[s] ?? ['b-neutral', '', s]
  return <span className={`badge ${c}`}><span aria-hidden="true">{i}</span> {t}</span>
}
export const SyntheticBadge = () => <span className="badge synthetic" title="All data in this prototype is generated">⚗ SYNTHETIC DATA</span>

export const fmtDate = (d?: string | null) => (d ? new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—')
export const fmtDateTime = (d?: string | null) => (d ? new Date(d).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—')

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null
    ref.current?.querySelector<HTMLElement>('input,textarea,select,button')?.focus()
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', k)
    return () => { document.removeEventListener('keydown', k); prev?.focus() }
  }, [onClose])
  return (
    <div className="scrim" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title} ref={ref}>
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  )
}

export function MatchReceipt({ receipt }: { receipt?: any }) {
  if (!receipt) return <div className="notice err" role="alert">Defect: this overlap has no Match Receipt, so it cannot be shown.</div>
  const L = receipt.layers
  return (
    <div className="receipt">
      <strong>Match Receipt — why this was suggested</strong>
      <ol>
        <li><b>Institution:</b> {L.L1_institution.how}.</li>
        <li><b>Typed names:</b> {(L.L2_fuzzy_name.inputs || []).filter(Boolean).join('  |  ') || 'taken from the registry'} — {L.L2_fuzzy_name.how}.</li>
        <li><b>Rules ({L.L4_rules.type}):</b> {L.L4_rules.reasons.join('; ')}.</li>
        <li className="muted"><b>Wording match:</b> {L.L3_issue.used ? 'used' : L.L3_issue.formula}</li>
      </ol>
      <p className="muted" style={{ margin: '.5rem 0 0' }}>{receipt.note}</p>
    </div>
  )
}

export function useLive(intervalMs: number, reload: () => void, stamp: number | null) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const a = setInterval(reload, intervalMs)
    const b = setInterval(() => setNow(Date.now()), 1000)
    return () => { clearInterval(a); clearInterval(b) }
  }, [intervalMs, reload])
  const age = stamp ? Math.round((now - stamp) / 1000) : null
  return { age, stale: age !== null && age > 45 }
}

export function LiveIndicator({ age, stale }: { age: number | null; stale: boolean }) {
  if (age === null) return null
  return stale
    ? <span className="badge b-warn" role="status">⚠ Stale — last update {age} s ago</span>
    : <span className="badge b-ok" role="status">● Live · updated {age} s ago</span>
}
