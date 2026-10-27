import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, ApiError } from '../api'
import { OFFICER_ROLES, useAuth } from '../auth'
import { ErrorBox, Loading, Modal, Severity, StatePill, fmtDate, fmtDateTime, useFetch } from '../components/ui'

type Dlg = null | 'transition' | 'remark' | 'next' | 'escalate' | 'transfer' | 'reveal'

export default function CaseDetail() {
  const { id } = useParams()
  const { me } = useAuth()
  const c = useFetch<any>(`/complaints/${id}`)
  const ev = useFetch<any>(c.data?.detail_visible ? `/complaints/${id}/events` : null, [c.data?.detail_visible])
  const ref = useFetch<any>('/reference')
  const ovs = useFetch<any>(`/overlaps${''}`)
  const [dlg, setDlg] = useState<Dlg>(null)
  const [revealed, setRevealed] = useState<any>(null)
  if (c.error) return <ErrorBox error={c.error} retry={c.reload} />
  if (!c.data) return <Loading what="case" />
  const d = c.data
  const mine = me && (d.unit_id === me.unit_id || me.role === 'admin' || me.role === 'regional_officer') && [...OFFICER_ROLES, 'admin'].includes(me.role)
  const caseOverlaps = (ovs.data?.items ?? []).filter((o: any) => o.a.case_id === d.case_id || o.b.case_id === d.case_id)
  const done = () => { setDlg(null); c.reload(); ev.reload() }
  return (
    <>
      <p><Link to="/app/complaints">← Complaints</Link></p>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h1 style={{ margin: 0 }}>{d.case_id} <span className="muted" style={{ fontWeight: 400 }}>· {d.reference_no}</span></h1>
        <span><StatePill state={d.state} level={d.escalation_level} /> {d.overdue && <span className="badge b-danger">Overdue</span>}</span>
      </div>
      <h2 style={{ marginTop: '.5rem' }}>{d.title}</h2>
      {!d.detail_visible && <div className="notice warn">{d.note}</div>}

      {!d.institution_id && mine && <LinkCollege d={d} onDone={c.reload} />}

      {caseOverlaps.length > 0 && (
        <div className="notice warn" role="alert" style={{ margin: '1rem 0' }}>
          <strong>Potential Overlapping Cases – Coordination Required.</strong> {caseOverlaps.length} suggested overlap(s) involve this case. <Link to="/app/overlaps">Review</Link> {caseOverlaps.map((o: any) => <Severity key={o.id} s={o.severity} />)}
        </div>
      )}

      <div className="grid2" style={{ marginTop: '1rem' }}>
        <section className="card">
          <h2>Tracking</h2>
          <dl style={{ margin: 0, display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '.35rem 1rem' }}>
            <dt className="muted">College</dt><dd>{d.institution_id ? <Link to={`/app/colleges/${d.institution_id}`}>{d.institution}</Link> : d.institution}</dd>
            <dt className="muted">Category</dt><dd>{d.category}</dd>
            <dt className="muted">Handled by</dt><dd>{d.unit}</dd>
            <dt className="muted">Officer</dt><dd>{d.owner ?? 'Not assigned'}</dd>
            <dt className="muted">Received</dt><dd>{fmtDate(d.received_on)}</dd>
            <dt className="muted">SLA due</dt><dd>{fmtDate(d.due_on)}</dd>
            <dt className="muted">Expected disposal</dt><dd>{fmtDate(d.expected_disposal_on)}</dd>
            <dt className="muted">Last action</dt><dd>{d.last_action_text ?? '—'} <span className="muted">{d.last_action_at ? `(${fmtDateTime(d.last_action_at)})` : ''}</span></dd>
            <dt className="muted">Next action</dt><dd>{d.next_action_text ?? <span className="badge b-warn">Not set</span>} {d.next_action_due_on && <span className="muted">by {fmtDate(d.next_action_due_on)}</span>}</dd>
          </dl>
        </section>
        {d.detail_visible && (
          <section className="card">
            <h2>Complaint</h2>
            <p>{d.description || <span className="muted">No description.</span>}</p>
            <h3 style={{ fontSize: '1rem' }}>Complainant <span className="badge b-neutral">masked by default</span></h3>
            {revealed ? (
              <p>{revealed.name} · {revealed.phone} · {revealed.email} <button className="btn sm" onClick={() => setRevealed(null)}>Hide</button></p>
            ) : (
              <p>{d.complainant.name ?? '—'} · {d.complainant.phone ?? '—'} · {d.complainant.email ?? '—'}{' '}
                {d.complainant.can_reveal && <button className="btn sm" onClick={() => setDlg('reveal')}>Reveal…</button>}</p>
            )}
          </section>
        )}
      </div>

      {d.detail_visible && mine && d.state !== 'DISPOSED' && (
        <div className="row" style={{ margin: '1rem 0' }}>
          <button className="btn" onClick={() => setDlg('transition')}>Change status</button>
          <button className="btn" onClick={() => setDlg('remark')}>Add remark</button>
          <button className="btn" onClick={() => setDlg('next')}>Set next action</button>
          <button className="btn" onClick={() => setDlg('transfer')}>Transfer</button>
          <button className="btn" onClick={() => setDlg('escalate')}>Escalate</button>
          <Link className="btn" to={`/app/gate?complaint_id=${d.id}`}>Run Action Gate</Link>
        </div>
      )}
      {d.state === 'DISPOSED' && mine && me?.role === 'unit_supervisor' && <p><button className="btn" onClick={() => setDlg('transition')}>Reopen…</button></p>}

      {d.detail_visible && (
        <section className="card" style={{ marginTop: '1rem' }}>
          <h2>Workflow history</h2>
          {ev.loading && !ev.data && <Loading what="history" />}
          {ev.data && (
            <ul className="timeline">
              {ev.data.items.map((e: any) => (
                <li key={e.id}>
                  <strong>{e.kind.replace(/_/g, ' ').toLowerCase()}</strong>{e.to_state && <> → {e.to_state.replace('_', ' ').toLowerCase()}</>}
                  <div className="muted">{fmtDateTime(e.occurred_at)} · {e.actor}{e.actor_unit ? ` (${e.actor_unit})` : ''}</div>
                  {e.remark && <div>{e.remark}</div>}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {dlg === 'reveal' && <Reveal id={d.id} onClose={() => setDlg(null)} onDone={(v) => { setRevealed(v); setDlg(null) }} />}
      {dlg === 'transition' && <Transition d={d} onClose={() => setDlg(null)} onDone={done} role={me!.role} />}
      {dlg === 'remark' && <Simple title="Add remark" label="Remark" path={`/complaints/${d.id}/remarks`} field="text" onClose={() => setDlg(null)} onDone={done} />}
      {dlg === 'next' && <NextAction id={d.id} onClose={() => setDlg(null)} onDone={done} />}
      {dlg === 'escalate' && <Escalate id={d.id} onClose={() => setDlg(null)} onDone={done} />}
      {dlg === 'transfer' && <Transfer id={d.id} units={ref.data?.units.filter((u: any) => u.code !== d.unit) ?? []} onClose={() => setDlg(null)} onDone={done} />}
    </>
  )
}

function LinkCollege({ d, onDone }: { d: any; onDone: () => void }) {
  const [q, setQ] = useState(d.institution_text_raw ?? '')
  const [save, setSave] = useState(true)
  const sugg = useFetch<any>(q.trim().length > 2 ? `/institutions/suggest?text=${encodeURIComponent(q)}` : null, [q])
  const found = useFetch<any>(q.trim().length > 2 ? `/institutions?q=${encodeURIComponent(q)}&limit=6` : null, [q])
  const { err, busy, run } = useSubmit(onDone)
  const options: { id: string; name: string; note: string }[] = [
    ...(sugg.data?.items ?? []).map((s: any) => ({ id: s.institution_id, name: s.name, note: `match score ${s.match_score.toFixed(2)}` })),
    ...(found.data?.items ?? []).map((i: any) => ({ id: i.id, name: i.name, note: 'registry search' })),
  ].filter((o, i, a) => a.findIndex((x) => x.id === o.id) === i)
  return (
    <section className="notice warn" style={{ margin: '1rem 0' }}>
      <strong>This case is not linked to a college yet,</strong> so no overlap check has run. Typed name: “{d.institution_text_raw}”.
      <label className="f" style={{ marginTop: '.6rem' }}>Search the registry
        <input value={q} onChange={(e) => setQ(e.target.value)} />
      </label>
      {options.map((o) => (
        <div className="row" key={o.id} style={{ margin: '.3rem 0' }}>
          <button className="btn sm" disabled={busy} onClick={() => run(`/complaints/${d.id}/institution`, { institution_id: o.id, save_alias: save })}>Link</button>
          <span><strong>{o.name}</strong> <span className="muted">{o.note}</span></span>
        </div>
      ))}
      <label style={{ display: 'flex', gap: '.5rem', alignItems: 'center' }}>
        <input type="checkbox" style={{ width: 'auto', minHeight: 0 }} checked={save} onChange={(e) => setSave(e.target.checked)} />
        Remember this spelling so the next case with it links automatically
      </label>
      <Err e={err} />
    </section>
  )
}

function useSubmit(onDone: () => void) {
  const [err, setErr] = useState<ApiError | null>(null)
  const [busy, setBusy] = useState(false)
  const run = async (path: string, body: any) => {
    setBusy(true); setErr(null)
    try { await api(path, { method: 'POST', body }); onDone() } catch (e) { setErr(e as ApiError) } finally { setBusy(false) }
  }
  return { err, busy, run }
}
const Err = ({ e }: { e: ApiError | null }) => e && (
  <div className="notice err" role="alert">{e.message}
    {e.code === 'gate_required' && <> <Link to="/app/gate">Open the Action Gate</Link></>}
  </div>
)

function Reveal({ id, onClose, onDone }: { id: string; onClose: () => void; onDone: (v: any) => void }) {
  const [reason, setReason] = useState('')
  const [err, setErr] = useState<ApiError | null>(null)
  return (
    <Modal title="Reveal personal details" onClose={onClose}>
      <p className="muted">Revealing is recorded in the audit log with your reason. Details are shown only on this page and are hidden again when you leave.</p>
      <label className="f">Reason (at least 10 characters)<textarea value={reason} onChange={(e) => setReason(e.target.value)} /></label>
      <Err e={err} />
      <p className="row"><button className="btn primary" disabled={reason.trim().length < 10} onClick={async () => { try { onDone(await api(`/complaints/${id}/reveal-pii`, { method: 'POST', body: { reason } })) } catch (e) { setErr(e as ApiError) } }}>Reveal</button><button className="btn" onClick={onClose}>Cancel</button></p>
    </Modal>
  )
}
function Simple({ title, label, path, field, onClose, onDone }: any) {
  const [v, setV] = useState('')
  const { err, busy, run } = useSubmit(onDone)
  return (
    <Modal title={title} onClose={onClose}>
      <label className="f">{label}<textarea value={v} onChange={(e) => setV(e.target.value)} /></label>
      <Err e={err} />
      <p className="row"><button className="btn primary" disabled={busy || !v.trim()} onClick={() => run(path, { [field]: v })}>Save</button><button className="btn" onClick={onClose}>Cancel</button></p>
    </Modal>
  )
}
function NextAction({ id, onClose, onDone }: any) {
  const [t, setT] = useState(''); const [due, setDue] = useState('')
  const { err, busy, run } = useSubmit(onDone)
  return (
    <Modal title="Set next action" onClose={onClose}>
      <label className="f">What must happen next<textarea value={t} onChange={(e) => setT(e.target.value)} /></label>
      <label className="f">By<input type="date" value={due} onChange={(e) => setDue(e.target.value)} /></label>
      <Err e={err} />
      <p className="row"><button className="btn primary" disabled={busy || t.trim().length < 3} onClick={() => run(`/complaints/${id}/next-action`, { text: t, due_on: due || null })}>Save</button><button className="btn" onClick={onClose}>Cancel</button></p>
    </Modal>
  )
}
function Escalate({ id, onClose, onDone }: any) {
  const [lvl, setLvl] = useState('2'); const [r, setR] = useState('')
  const { err, busy, run } = useSubmit(onDone)
  return (
    <Modal title="Escalate case" onClose={onClose}>
      <label className="f">Level<select value={lvl} onChange={(e) => setLvl(e.target.value)}><option value="2">Level 2 — unit supervisor</option><option value="3">Level 3 — Competent Authority</option></select></label>
      <label className="f">Reason (required)<textarea value={r} onChange={(e) => setR(e.target.value)} /></label>
      <Err e={err} />
      <p className="row"><button className="btn primary" disabled={busy || !r.trim()} onClick={() => run(`/complaints/${id}/escalate`, { level: Number(lvl), reason: r })}>Escalate</button><button className="btn" onClick={onClose}>Cancel</button></p>
    </Modal>
  )
}
function Transfer({ id, units, onClose, onDone }: any) {
  const [u, setU] = useState(''); const [r, setR] = useState('')
  const { err, busy, run } = useSubmit(onDone)
  return (
    <Modal title="Transfer to another Bureau/Cell" onClose={onClose}>
      <label className="f">Transfer to<select value={u} onChange={(e) => setU(e.target.value)}><option value="">Choose…</option>{units.map((x: any) => <option key={x.id} value={x.id}>{x.code} — {x.name}</option>)}</select></label>
      <label className="f">Remark (required)<textarea value={r} onChange={(e) => setR(e.target.value)} /></label>
      <Err e={err} />
      <p className="row"><button className="btn primary" disabled={busy || !u || !r.trim()} onClick={() => run(`/complaints/${id}/transfer`, { target_unit_id: u, remark: r })}>Transfer</button><button className="btn" onClick={onClose}>Cancel</button></p>
    </Modal>
  )
}
function Transition({ d, onClose, onDone, role }: any) {
  const opts: Record<string, string[]> = {
    RECEIVED: ['ASSIGNED'], ASSIGNED: ['UNDER_PROCESS'], UNDER_PROCESS: ['DISPOSED'], TRANSFERRED: ['ASSIGNED'],
    ESCALATED: ['UNDER_PROCESS', 'DISPOSED'], DISPOSED: ['REOPENED'], REOPENED: ['UNDER_PROCESS'],
  }
  const choices = opts[d.state] ?? []
  const [to, setTo] = useState(choices[0] ?? ''); const [r, setR] = useState('')
  const { err, busy, run } = useSubmit(onDone)
  void role
  return (
    <Modal title="Change status" onClose={onClose}>
      <p>Now: <StatePill state={d.state} /></p>
      <label className="f">Move to<select value={to} onChange={(e) => setTo(e.target.value)}>{choices.map((c) => <option key={c} value={c}>{c.replace('_', ' ').toLowerCase()}</option>)}</select></label>
      <label className="f">Remark {['DISPOSED', 'REOPENED'].includes(to) ? '(required)' : '(optional)'}<textarea value={r} onChange={(e) => setR(e.target.value)} /></label>
      {to === 'DISPOSED' && <p className="muted">Closing a case is a regulatory action. If another unit has a conflicting action on this college, the Action Gate must be decided first.</p>}
      <Err e={err} />
      <p className="row"><button className="btn primary" disabled={busy || !to} onClick={() => run(`/complaints/${d.id}/transition`, { to_state: to, remark: r || null })}>Apply</button><button className="btn" onClick={onClose}>Cancel</button></p>
    </Modal>
  )
}
