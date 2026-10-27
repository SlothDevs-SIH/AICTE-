import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { qs } from '../api'
import { Empty, ErrorBox, Loading, Severity, StatePill, fmtDate, useFetch } from '../components/ui'

export default function Colleges() {
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
