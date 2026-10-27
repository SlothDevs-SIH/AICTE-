import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, ApiError, qs } from '../api'
import { useAuth } from '../auth'
import { Empty, ErrorBox, Loading, Severity, StatePill, fmtDate, useFetch } from '../components/ui'

export default function Colleges() {
  const { me } = useAuth()
  const [adding, setAdding] = useState(false)
  const blank = { canonical_name: '', aicte_id: '', state: '', district: '', region_code: '' }
  const [nf, setNf] = useState<Record<string, string>>(blank)
  const [addErr, setAddErr] = useState('')
  const [q, setQ] = useState('')
  const [state, setState] = useState('')
  const list = useFetch<any>(`/institutions${qs({ q, state, limit: 60 })}`, [q, state])
  return (
    <>
      <h1>Colleges</h1>
      <div className="row" style={{ marginBottom: '1rem' }}>
        <label className="f">Name or AICTE ID
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Spelling variants are matched" />
        </label>
        <label className="f">State
          <input value={state} onChange={(e) => setState(e.target.value)} placeholder="e.g. Maharashtra" />
        </label>
      </div>
      {me?.role === 'admin' && <p><button className="btn sm" onClick={() => setAdding(!adding)}>{adding ? 'Close' : 'Add a college'}</button></p>}
      {adding && (
        <form className="card grid2" style={{ marginBottom: '1rem' }} onSubmit={async (e) => {
          e.preventDefault()
          setAddErr('')
          const body: Record<string, string> = {}
          Object.entries(nf).forEach(([k, v]) => { if (v) body[k] = v })
          try { await api('/institutions', { method: 'POST', body }); setAdding(false); setNf(blank); list.reload() } catch (x) { setAddErr((x as ApiError).message) }
        }}>
          <label className="f">College name<input required value={nf.canonical_name} onChange={(e) => setNf({ ...nf, canonical_name: e.target.value })} /></label>
          <label className="f">AICTE permanent ID<input value={nf.aicte_id} onChange={(e) => setNf({ ...nf, aicte_id: e.target.value })} /></label>
          <label className="f">State<input value={nf.state} onChange={(e) => setNf({ ...nf, state: e.target.value })} /></label>
          <label className="f">District<input value={nf.district} onChange={(e) => setNf({ ...nf, district: e.target.value })} /></label>
          <label className="f">Region code (NR, WR, SR, ER, CR)<input value={nf.region_code} onChange={(e) => setNf({ ...nf, region_code: e.target.value })} /></label>
          {addErr && <div className="notice err" role="alert">{addErr}</div>}
          <div><button className="btn primary">Save college</button></div>
        </form>
      )}
      {list.error && <ErrorBox error={list.error} retry={list.reload} />}
      {list.loading && !list.data && <Loading what="colleges" />}
      {list.data && list.data.items.length === 0 && <Empty>No college matches.</Empty>}
      {list.data && list.data.items.length > 0 && (
        <div className="tablewrap">
          <table>
            <thead><tr><th>College</th><th>AICTE ID</th><th>District</th><th>State</th><th>Region</th></tr></thead>
            <tbody>
              {list.data.items.map((i: any) => (
                <tr key={i.id}>
                  <td><Link to={`/app/colleges/${i.id}`}>{i.name}</Link></td>
                  <td>{i.aicte_id}</td><td>{i.district}</td><td>{i.state}</td><td>{i.region}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {list.data && <p className="muted">{list.data.total} found{list.data.total > 60 ? ', showing 60' : ''}.</p>}
    </>
  )
}

export function College360() {
  const { id } = useParams()
  const d = useFetch<any>(`/institutions/${id}/360`)
  const inst = useFetch<any>(`/institutions/${id}`)
  const { me: who } = useAuth()
  const risk = useFetch<any>(who && ['management', 'competent_authority', 'admin', 'auditor'].includes(who.role) ? `/institutions/${id}/risk` : null)
  if (d.error) return <ErrorBox error={d.error} retry={d.reload} />
  if (!d.data) return <Loading what="college" />
  const i = d.data.institution
  return (
    <>
      <p><Link to="/app/colleges">← Colleges</Link></p>
      <h1>{i.name}</h1>
      <p className="muted">AICTE ID {i.aicte_id} · {i.district}, {i.state} · Region {i.region} · {i.address}</p>
      {d.data.open_units.length > 1 && (
        <div className="notice warn" role="alert">
          <strong>Potential Overlapping Cases – Coordination Required.</strong> Open cases are held by: {d.data.open_units.join(', ')}.
        </div>
      )}
      <div className="tiles" style={{ margin: '1rem 0' }}>
        <div className="tile"><div className="n">{d.data.summary.total}</div><div className="l">Total cases</div></div>
        <div className="tile"><div className="n">{d.data.summary.open}</div><div className="l">Open</div></div>
        <div className="tile"><div className="n">{d.data.summary.disposed}</div><div className="l">Disposed</div></div>
        <div className="tile"><div className="n">{d.data.overlaps.length}</div><div className="l">Overlaps</div></div>
      </div>
      {risk.data && (
        <section className="card" style={{ marginBottom: '1rem' }}>
          <h2>Attention score: {risk.data.score} / 100</h2>
          <p className="muted" style={{ margin: 0 }}>
            {risk.data.components.map((c: any) => `${c.name.replace('_', ' ')} ${c.points}`).join(' · ')}. {risk.data.note}
          </p>
        </section>
      )}
      {d.data.overlaps.length > 0 && (
        <section>
          <h2>Overlaps</h2>
          {d.data.overlaps.map((o: any) => (
            <p key={o.id}>
              <Severity s={o.severity} /> {o.a.unit} {o.a.case_id} ⇄ {o.b.unit} {o.b.case_id} · {o.status.toLowerCase()} · <Link to="/app/overlaps">review</Link>
            </p>
          ))}
        </section>
      )}
      <section>
        <h2>Consolidated case history</h2>
        <div className="tablewrap">
          <table>
            <thead><tr><th>Case</th><th>Unit</th><th>Category</th><th>Status</th><th>Last action</th><th>Received</th></tr></thead>
            <tbody>
              {d.data.cases.map((c: any) => (
                <tr key={c.id}>
                  <td><Link to={`/app/complaints/${c.id}`}>{c.case_id}</Link></td>
                  <td>{c.unit}</td><td>{c.category}</td>
                  <td><StatePill state={c.state} level={c.escalation_level} /></td>
                  <td>{c.last_action_text ?? '—'}</td><td>{fmtDate(c.received_on)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {inst.data && inst.data.aliases.length > 0 && (
        <section>
          <h2>Known name variants</h2>
          <p>{inst.data.aliases.map((a: any) => a.alias).join(' · ')}</p>
        </section>
      )}
    </>
  )
}
