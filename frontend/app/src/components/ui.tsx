import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError, openStream } from '../api'

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
/** A number that counts up to its value (skipped when the user prefers reduced motion). */
export function Count({ to }: { to: number }) {
  const [v, setV] = useState(0)
  const from = useRef(0)
  useEffect(() => {
    const start = from.current
    from.current = to
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || Math.abs(to - start) < 2) { setV(to); return }
    let raf = 0
    const t0 = performance.now()
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / 900)
      setV(Math.round(start + (to - start) * (1 - Math.pow(1 - p, 3))))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [to])
  return <>{v.toLocaleString('en-IN')}</>
}

export function SyntheticBadge() {
  const o = useFetch<any>('/public/overview')
  const real = o.data?.colleges_real ?? 0
  return (
    <span className="badge synthetic" title="Complaints are simulated: AICTE does not publish complaint records. The college list is real AICTE data only where it has been imported.">
      Simulated complaints{real > 0 ? ` · ${real.toLocaleString('en-IN')} real AICTE colleges` : ''}
    </span>
  )
}


export function NoticeTicker() {
  const o = useFetch<any>('/public/overview')
  const d = o.data
  const items: ReactNode[] = [
    <>Cases on this site are <b>simulated</b>: AICTE does not publish complaint records.</>,
    d ? <><b>{d.colleges_real > 0 ? d.colleges_real.toLocaleString('en-IN') : 'No'}</b> real AICTE colleges in the registry{d.colleges_real > 0 ? '' : ' yet (load them from Admin)'}.</> : <>Loading registry figures…</>,
    d ? <><b>{d.complaints.toLocaleString('en-IN')}</b> simulated cases, <b>{d.open_overlaps.toLocaleString('en-IN')}</b> open overlaps across units.</> : <>Loading case figures…</>,
    <>Every flag is explained, and a person decides. The system only suggests.</>,
  ]
  const track = [...items, ...items]
  return (
    <div className="ticker" role="region" aria-label="Notices about the data on this site">
      <span className="ticker-tag"><span className="ticker-dot" aria-hidden="true" />Notice</span>
      <div className="ticker-view">
        <div className="ticker-track">
          {track.map((t, i) => <span className="ticker-item" key={i} aria-hidden={i >= items.length}>{t}</span>)}
        </div>
      </div>
    </div>
  )
}

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
        <li className="muted"><b>Wording match:</b>{' '}
          {L.L3_issue.concepts?.shared_concepts?.length
            ? <>same problem found in the text: {L.L3_issue.concepts.shared_concepts.map((s: any) => `${s.concept} ("${s.a_words[0]}" and "${s.b_words[0]}")`).join('; ')}. </>
            : 'no shared problem type found in the word list. '}
          {L.L3_issue.ai?.reason && <><AiLabel kind="AI-written" /> {L.L3_issue.ai.same_issue ? 'Reads as the same issue' : 'Does not read as the same issue'} ({Math.round(L.L3_issue.ai.confidence * 100)}% sure): {L.L3_issue.ai.reason}</>}
        </li>
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

export function AiLabel({ kind, reason }: { kind: string; reason?: string | null }) {
  const ai = kind === 'AI-written'
  return (
    <span className={`badge ${ai ? 'b-info' : 'b-neutral'}`} title={reason ?? ''}>
      {ai ? '✦ AI-written' : '▤ Template summary'}{reason ? ` — ${reason}` : ''}
    </span>
  )
}

/** Live updates over Server-Sent Events; if the stream fails the caller keeps polling. */
export function useStream(onChange: () => void) {
  const [lastAt, setLastAt] = useState<number | null>(null)
  const [ok, setOk] = useState(false)
  const cb = useRef(onChange)
  cb.current = onChange
  useEffect(() => {
    let stop = () => {}
    let retry: ReturnType<typeof setTimeout>
    const start = () => {
      setOk(true)
      stop = openStream(
        (kind) => { setLastAt(Date.now()); if (kind === 'counters_changed') cb.current() },
        () => { setOk(false); retry = setTimeout(start, 15000) },
      )
    }
    start()
    return () => { stop(); clearTimeout(retry) }
  }, [])
  return { lastAt, ok }
}

export function AskBar() {
  const [q, setQ] = useState('')
  const [res, setRes] = useState<any>(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const go = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr('')
    try { setRes(await api('/ask', { method: 'POST', body: { question: q } })) } catch (x) { setErr((x as ApiError).message) } finally { setBusy(false) }
  }
  const params = res && !res.needs_manual_filters ? new URLSearchParams(Object.entries(res.parsed_filters).map(([k, v]) => [k, String(v)])).toString() : ''
  return (
    <form onSubmit={go} className="card" style={{ marginBottom: '1rem' }} aria-label="Ask the dashboard">
      <div className="row">
        <label className="f" style={{ flex: 1, minWidth: 220 }}>Ask the dashboard
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. overdue PGRC cases older than 60 days" maxLength={300} />
        </label>
        <button className="btn primary" disabled={busy || q.trim().length < 3} style={{ alignSelf: 'end' }}>Find cases</button>
      </div>
      {err && <div className="notice err" role="alert" style={{ marginTop: '.6rem' }}>{err}</div>}
      {res && (
        <p style={{ margin: '.6rem 0 0' }} aria-live="polite">
          {res.needs_manual_filters ? res.explanation : (<>{res.explanation}. <Link to={`/app/complaints?${params}`}>Show these cases →</Link></>)}{' '}
          <span className="badge b-neutral">{res.used_ai ? '✦ AI-assisted' : 'Rule-based'} · filters only, nothing was run from the text</span>
        </p>
      )}
    </form>
  )
}
