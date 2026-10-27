import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, ApiError } from '../api'
import { OFFICER_ROLES, useAuth } from '../auth'
import { Empty, ErrorBox, Loading, fmtDateTime, useFetch } from '../components/ui'

const OUTCOMES: [string, string][] = [
  ['PROCEED_TOGETHER', 'Proceed together'], ['DEFER_TO_A', 'First unit leads, the other defers'],
  ['DEFER_TO_B', 'Second unit leads, the first defers'], ['NOT_RELATED', 'The cases are not related'],
]

export function CoordinationList() {
  const l = useFetch<any>('/coordination')
  return (
    <>
      <h1>Coordination</h1>
      <p className="muted">When two units hold cases on one college, an officer can ask the other unit to talk before either acts. The cases stay on hold until someone records an outcome or the deadline passes.</p>
      {l.error && <ErrorBox error={l.error} retry={l.reload} />}
      {l.loading && !l.data && <Loading what="threads" />}
      {l.data && l.data.items.length === 0 && <Empty>No coordination threads yet. Start one from an overlap.</Empty>}
      <div style={{ display: 'grid', gap: '.8rem' }}>
        {l.data?.items.map((t: any) => (
          <Link key={t.id} to={`/app/coordination/${t.id}`} className="overlap RELATED" style={{ textDecoration: 'none', color: 'inherit' }}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <strong>{t.institution}</strong>
              <span className={`badge ${t.status === 'OPEN' ? 'b-warn' : t.status === 'RESOLVED' ? 'b-ok' : 'b-danger'}`}>{t.status.toLowerCase()}</span>
            </div>
            <div className="muted">Units: {t.units.join(', ')} · opened by {t.opened_by} · due {fmtDateTime(t.due_at)}</div>
            {t.outcome && <div>Outcome: {t.outcome.replace(/_/g, ' ').toLowerCase()}</div>}
          </Link>
        ))}
      </div>
    </>
  )
}

export function CoordinationThread() {
  const { id } = useParams()
  const { me } = useAuth()
  const t = useFetch<any>(`/coordination/${id}`)
  const [body, setBody] = useState('')
  const [outcome, setOutcome] = useState('PROCEED_TOGETHER')
  const [note, setNote] = useState('')
  const [err, setErr] = useState<ApiError | null>(null)
  if (t.error) return <ErrorBox error={t.error} retry={t.reload} />
  if (!t.data) return <Loading what="thread" />
  const d = t.data
  const canAct = me && OFFICER_ROLES.includes(me.role) && d.status === 'OPEN'
  const send = async () => {
    setErr(null)
    try { await api(`/coordination/${id}/messages`, { method: 'POST', body: { body } }); setBody(''); t.reload() } catch (e) { setErr(e as ApiError) }
  }
  const resolve = async () => {
    setErr(null)
    try { await api(`/coordination/${id}/resolve`, { method: 'POST', body: { outcome, note } }); t.reload() } catch (e) { setErr(e as ApiError) }
  }
  return (
    <>
      <p><Link to="/app/coordination">← Coordination</Link></p>
      <h1>{d.institution}</h1>
      <p><span className={`badge ${d.status === 'OPEN' ? 'b-warn' : d.status === 'RESOLVED' ? 'b-ok' : 'b-danger'}`}>{d.status.toLowerCase()}</span> Due {fmtDateTime(d.due_at)} · units {d.units.join(', ')}</p>
      {d.status === 'EXPIRED' && <div className="notice err">This request passed its deadline with no outcome. A supervisor has been told.</div>}
      {d.outcome && <div className="notice ok"><strong>Outcome:</strong> {d.outcome.replace(/_/g, ' ').toLowerCase()}. {d.resolution_note}</div>}
      <section className="card" style={{ margin: '1rem 0' }}>
        <h2>Cases on hold</h2>
        {d.cases.map((c: any) => <p key={c.id} style={{ margin: '.2rem 0' }}><span className="badge b-info">{c.unit}</span> <Link to={`/app/complaints/${c.id}`}>{c.case_id}</Link> {c.title}</p>)}
      </section>
      <section className="card">
        <h2>Discussion</h2>
        <ul className="timeline">
          {d.messages.map((m: any) => (
            <li key={m.id}><strong>{m.author}</strong> <span className="muted">{m.unit} · {fmtDateTime(m.posted_at)}</span><div>{m.body}</div></li>
          ))}
        </ul>
        {canAct && (
          <>
            <label className="f">Add a note<textarea value={body} onChange={(e) => setBody(e.target.value)} /></label>
            <p><button className="btn primary" disabled={!body.trim()} onClick={send}>Post note</button></p>
            <hr style={{ border: 0, borderTop: '1px solid var(--border)' }} />
            <h3>Record the outcome</h3>
            <label className="f">Outcome<select value={outcome} onChange={(e) => setOutcome(e.target.value)}>{OUTCOMES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
            <label className="f">Note (required)<textarea value={note} onChange={(e) => setNote(e.target.value)} /></label>
            <p><button className="btn" disabled={note.trim().length < 3} onClick={resolve}>Resolve and release the cases</button></p>
          </>
        )}
        {err && <div className="notice err" role="alert">{err.message}</div>}
      </section>
    </>
  )
}
