import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, ApiError } from '../api'
import { OFFICER_ROLES, useAuth } from '../auth'
import { Empty, ErrorBox, Loading, MatchReceipt, Modal, Severity, useFetch } from '../components/ui'

export default function Overlaps() {
  const { me } = useAuth()
  const [sp, setSp] = useSearchParams()
  const severity = sp.get('severity') ?? ''
  const status = sp.get('status') ?? 'SUGGESTED'
  const list = useFetch<any>(`/overlaps?status=${status}${severity ? `&severity=${severity}` : ''}`)
  const [open, setOpen] = useState<string | null>(null)
  const canDecide = me && [...OFFICER_ROLES, 'competent_authority', 'admin'].includes(me.role)
  const setP = (k: string, v: string) => {
    const n = new URLSearchParams(sp)
    if (v) n.set(k, v)
    else n.delete(k)
    setSp(n, { replace: true })
  }
  return (
    <>
      <h1>Overlaps</h1>
      <p className="muted">Suggested overlaps are for officer review. Nothing is linked, merged or closed automatically.</p>
      <div className="row" style={{ marginBottom: '1rem' }}>
        <label className="f">Status
          <select value={status} onChange={(e) => setP('status', e.target.value)}>
            {['SUGGESTED', 'CONFIRMED', 'LINKED', 'DISMISSED', 'UNLINKED'].map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
        <label className="f">Severity
          <select value={severity} onChange={(e) => setP('severity', e.target.value)}>
            <option value="">Any</option><option>CONFLICT</option><option>RELATED</option>
          </select>
        </label>
      </div>
      {list.error && <ErrorBox error={list.error} retry={list.reload} />}
      {list.loading && !list.data && <Loading what="overlaps" />}
      {list.data && list.data.items.length === 0 && <Empty>No overlaps with this status.</Empty>}
      <div style={{ display: 'grid', gap: '1rem' }}>
        {list.data?.items.map((o: any) => (
          <article key={o.id} className={`overlap ${o.severity}`} aria-label={`Overlap at ${o.institution}`}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <strong>{o.label}</strong>
              <span>
                <Severity s={o.severity} /> <span className="badge b-neutral">{o.type}</span>{' '}
                <span className="badge b-neutral">match score {o.match_score.toFixed(2)}</span>
              </span>
            </div>
            <p style={{ margin: '.3rem 0' }}><Link to={`/app/colleges/${o.institution_id}`}>{o.institution}</Link></p>
            <div className="sides">
              {[o.a, o.b].map((s: any) => (
                <div className="side-case" key={s.id}>
                  <span className="badge b-info">{s.unit}</span> <Link to={`/app/complaints/${s.id}`}>{s.case_id}</Link>
                  <div><strong>{s.title}</strong></div>
                  <div className="muted">{s.category} · {s.state.replace('_', ' ').toLowerCase()}</div>
                  <div>Last action: {s.last_action_text ?? '—'}</div>
                </div>
              ))}
            </div>
            <p><button className="btn sm" onClick={() => setOpen(o.id)}>Review with evidence</button></p>
          </article>
        ))}
      </div>
      {open && <Review id={open} canDecide={!!canDecide} onClose={() => setOpen(null)} onDone={() => { setOpen(null); list.reload() }} />}
    </>
  )
}

function Review({ id, canDecide, onClose, onDone }: { id: string; canDecide: boolean; onClose: () => void; onDone: () => void }) {
  const o = useFetch<any>(`/overlaps/${id}`)
  const [reason, setReason] = useState('')
  const [err, setErr] = useState<ApiError | null>(null)
  const decide = async (decision: string) => {
    try {
      await api(`/overlaps/${id}/decision`, { method: 'POST', body: { decision, reason } })
      onDone()
    } catch (e) {
      setErr(e as ApiError)
    }
  }
  const ok = reason.trim().length >= 3
  return (
    <Modal title="Suggested overlap — review" onClose={onClose}>
      {!o.data && <Loading what="receipt" />}
      {o.data && (
        <>
          <p><strong>{o.data.institution}</strong> <Severity s={o.data.severity} /></p>
          <MatchReceipt receipt={o.data.receipt} />
          {canDecide && o.data.status === 'SUGGESTED' && (
            <>
              <label className="f" style={{ marginTop: '1rem' }}>Reason for your decision
                <textarea value={reason} onChange={(e) => setReason(e.target.value)} />
              </label>
              {err && <div className="notice err" role="alert">{err.message}</div>}
              <p className="row">
                <button className="btn primary" disabled={!ok} onClick={() => decide('CONFIRM')}>Confirm overlap</button>
                <button className="btn" disabled={!ok} onClick={() => decide('LINK')}>Link cases</button>
                <button className="btn" disabled={!ok} onClick={() => decide('DISMISS')}>Dismiss</button>
              </p>
            </>
          )}
          {canDecide && ['CONFIRMED', 'LINKED'].includes(o.data.status) && (
            <>
              <label className="f" style={{ marginTop: '1rem' }}>Reason to unlink
                <textarea value={reason} onChange={(e) => setReason(e.target.value)} />
              </label>
              <p><button className="btn danger" disabled={!ok} onClick={() => decide('UNLINK')}>Unlink</button></p>
            </>
          )}
          {o.data.decision_reason && <p className="muted">Decision recorded: {o.data.decision_reason}</p>}
        </>
      )}
    </Modal>
  )
}
