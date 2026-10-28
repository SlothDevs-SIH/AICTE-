import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, ApiError } from '../api'
import { useAuth } from '../auth'
import { Count, Empty, ErrorBox, Loading, fmtDate, fmtDateTime, useDebounced, useFetch } from '../components/ui'
import { OrganicButton } from '@/components/ui/organic-button'

const TONE: Record<string, string> = { RECEIVED: 'b-neutral', ASSIGNED: 'b-info', UNDER_PROCESS: 'b-info', TRANSFERRED: 'b-violet', ESCALATED: 'b-orange', DISPOSED: 'b-ok', REOPENED: 'b-warn' }
const Status = ({ state, text }: { state: string; text: string }) => <span className={`badge ${TONE[state] ?? 'b-neutral'}`}>{text}</span>

/** Home for people who signed up as complainants. */
export function MyComplaints() {
  const nav = useNavigate()
  const { me } = useAuth()
  const l = useFetch<any>('/portal/my/complaints')
  const items = l.data?.items ?? []
  const open = items.filter((c: any) => c.state !== 'DISPOSED').length
  return (
    <>
      <h1>Hello, {(me?.name ?? '').split(' ')[0]}</h1>
      <p className="muted">Your complaints and where each one stands. Only you and the officers who handle a complaint can read it.</p>
      <div className="tiles" style={{ margin: '1rem 0' }}>
        <div className="tile"><span className="n"><Count to={items.length} /></span><span className="l">complaints filed</span></div>
        <div className="tile"><span className="n"><Count to={open} /></span><span className="l">still open</span></div>
        <div className="tile"><span className="n"><Count to={items.length - open} /></span><span className="l">closed</span></div>
      </div>
      <p><OrganicButton href="/app/file" label="File a complaint" onClick={(e) => { e.preventDefault(); nav("/app/file") }} /></p>
      {l.error && <ErrorBox error={l.error} retry={l.reload} />}
      {l.loading && !l.data && <Loading what="your complaints" />}
      {l.data && items.length === 0 && <Empty>You have not filed a complaint yet.</Empty>}
      {items.length > 0 && (
        <div className="tablewrap">
          <table>
            <thead><tr><th>Case ID</th><th>About</th><th>Category</th><th>Status</th><th>Filed</th><th>Expected by</th></tr></thead>
            <tbody>{items.map((c: any) => (
              <tr key={c.id}>
                <td><Link to={`/app/my/${c.id}`}>{c.case_id}</Link></td><td>{c.institution ?? '—'}<div className="muted">{c.title}</div></td>
                <td>{c.category}</td><td><Status state={c.state} text={c.status} /></td><td>{fmtDate(c.received_on)}</td><td>{fmtDate(c.expected_disposal_on)}</td>
              </tr>))}</tbody>
          </table>
        </div>
      )}
    </>
  )
}

export function MyComplaintDetail() {
  const { id } = useParams()
  const d = useFetch<any>(`/portal/my/complaints/${id}`)
  if (d.error) return <ErrorBox error={d.error} retry={d.reload} />
  if (!d.data) return <Loading what="your complaint" />
  const c = d.data
  return (
    <>
      <p><Link to="/app">← My complaints</Link></p>
      <h1>{c.case_id} <Status state={c.state} text={c.status} /></h1>
      <div className="grid2">
        <section className="card">
          <h2>{c.title}</h2>
          <p style={{ whiteSpace: 'pre-wrap' }}>{c.description}</p>
          <p className="muted">About: {c.institution ?? '—'} · {c.category} · filed {fmtDate(c.received_on)} · expected by {fmtDate(c.expected_disposal_on)}</p>
        </section>
        <section className="card">
          <h2>Progress</h2>
          <ol className="steps-list">
            {c.timeline.map((s: any, i: number) => <li key={i}><strong>{s.status}</strong><span className="muted">{fmtDateTime(s.at)}</span></li>)}
          </ol>
          <p className="muted" style={{ marginBottom: 0 }}>Officers' working notes are internal and are not shown here.</p>
        </section>
      </div>
    </>
  )
}

export function FileComplaint() {
  const nav = useNavigate()
  const ref = useFetch<any>('/reference')
  const [title, setTitle] = useState('')
  const [desc, setDesc] = useState('')
  const [cat, setCat] = useState('')
  const [q, setQ] = useState('')
  const [inst, setInst] = useState<any>(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const dq = useDebounced(q.trim(), 300)
  const res = useFetch<any>(!inst && dq.length >= 2 ? `/institutions?q=${encodeURIComponent(dq)}&limit=6` : null, [dq, inst])
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true); setErr('')
    try {
      const r = await api('/portal/complaints', { method: 'POST', body: { title, description: desc, category_id: cat, institution_id: inst?.id ?? null, institution_text: inst ? null : q } })
      nav(`/app/my/${r.id}`, { replace: true })
    } catch (x) { setErr((x as ApiError).message) } finally { setBusy(false) }
  }
  return (
    <>
      <h1>File a complaint</h1>
      <p className="muted">Describe what happened in your own words. Do not include passwords or bank details. You will get a case ID to follow it.</p>
      <form className="card" onSubmit={submit} style={{ display: 'grid', gap: '1rem', maxWidth: '46rem' }}>
        <label className="f">Which institution is this about?
          {inst ? (
            <span className="pick-chosen"><span><strong>{inst.name}</strong><br /><span className="muted">{[inst.district, inst.state].filter(Boolean).join(', ')}</span></span> <button type="button" className="btn sm" onClick={() => { setInst(null); setQ('') }}>Change</button></span>
          ) : <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Start typing the college name" required />}
          {!inst && res.data && dq.length >= 2 && (
            <ul className="pick-list">
              {res.data.items.map((i: any) => <li key={i.id}><button type="button" onClick={() => setInst(i)}><strong>{i.name}</strong><span>{[i.district, i.state].filter(Boolean).join(', ')}</span></button></li>)}
              {res.data.items.length === 0 && <li className="muted">Not in our list. We will use the name you typed.</li>}
            </ul>
          )}
        </label>
        <label className="f">What is it about?
          <select value={cat} onChange={(e) => setCat(e.target.value)} required><option value="">Choose a category…</option>{ref.data?.categories.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
        </label>
        <label className="f">Short title
          <input value={title} onChange={(e) => setTitle(e.target.value)} minLength={5} maxLength={300} required placeholder="For example: Hostel deposit not returned" />
        </label>
        <label className="f">What happened?
          <textarea value={desc} onChange={(e) => setDesc(e.target.value)} minLength={10} maxLength={4000} required rows={6} placeholder="Dates, amounts, who you spoke to, what you were told." />
        </label>
        {err && <div className="notice err" role="alert">{err}</div>}
        <div><button className="btn primary" disabled={busy}>{busy ? 'Sending…' : 'Submit complaint'}</button></div>
      </form>
    </>
  )
}

export function InstitutionHome() {
  const l = useFetch<any>('/portal/institution/complaints')
  if (l.error) return <ErrorBox error={l.error} retry={l.reload} />
  if (!l.data) return <Loading what="your institution" />
  return (
    <>
      <h1>{l.data.institution}</h1>
      <p className="muted">Complaints about your institution and their stage. Titles, descriptions and the complainants' details are not shown.</p>
      <div className="tiles" style={{ margin: '1rem 0' }}>
        <div className="tile warm"><span className="n"><Count to={l.data.open} /></span><span className="l">open</span></div>
        <div className="tile"><span className="n"><Count to={l.data.closed} /></span><span className="l">closed</span></div>
      </div>
      {l.data.items.length === 0 ? <Empty>No complaints are recorded about your institution.</Empty> : (
        <div className="tablewrap">
          <table>
            <thead><tr><th>Case ID</th><th>Category</th><th>Status</th><th>Received</th><th>Expected by</th></tr></thead>
            <tbody>{l.data.items.map((c: any) => <tr key={c.case_id}><td>{c.case_id}</td><td>{c.category}</td><td><Status state={c.state} text={c.status} /></td><td>{fmtDate(c.received_on)}</td><td>{fmtDate(c.expected_disposal_on)}</td></tr>)}</tbody>
          </table>
        </div>
      )}
    </>
  )
}
