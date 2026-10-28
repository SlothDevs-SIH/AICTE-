import { Link } from 'react-router-dom'
import { useAuth } from '../auth'
import { AskBar, Count, Empty, ErrorBox, LiveIndicator, Loading, Severity, useFetch, useLive, useStream } from '../components/ui'

const TILES: [string, string, string, string?][] = [
  ['total_received', 'Total received', ''], ['pending', 'Pending', '?state=RECEIVED'], ['under_process', 'Under process', '?state=UNDER_PROCESS'],
  ['disposed', 'Disposed', '?state=DISPOSED'], ['transferred', 'Transferred', '?state=TRANSFERRED'],
  ['escalated', 'Escalated', '?escalated=true', 'warm'], ['beyond_timeline', 'Beyond timeline', '?overdue=true', 'hot'],
  ['due_soon', 'Due in 7 days', '?due_soon=true'],
]

export default function Dashboard() {
  const { me } = useAuth()
  const sum = useFetch<any>('/dashboard/summary')
  const age = useFetch<any>('/dashboard/ageing')
  const inst = useFetch<any>('/dashboard/by-institution')
  const conf = useFetch<any>('/overlaps?severity=CONFLICT&status=SUGGESTED')
  const work = useFetch<any>(me && me.role !== 'auditor' ? '/dashboard/workload' : null)
  const reloadAll = () => { sum.reload(); age.reload(); inst.reload(); conf.reload(); work.reload() }
  const stream = useStream(reloadAll)
  // the stream gives instant updates; polling every 20 s is the fallback if it fails
  const live = useLive(stream.ok ? 60000 : 20000, reloadAll, stream.lastAt && sum.stamp ? Math.max(stream.lastAt, sum.stamp) : sum.stamp)

  return (
    <>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h1 style={{ margin: 0 }}>Dashboard</h1>
        <LiveIndicator {...live} />
      </div>
      {sum.data && <p className="muted">{sum.data.caption}</p>}
      <AskBar />
      {sum.error && <ErrorBox error={sum.error} retry={sum.reload} />}
      {sum.loading && !sum.data && <Loading what="counters" />}
      {sum.data && (
        <div className={`tiles ${live.stale ? 'dim' : ''}`}>
          {TILES.map(([k, label, q, cls]) => (
            <Link key={k} to={`/app/complaints${q}`} className={`tile ${cls ?? ''}`}>
              <div className="n"><Count to={sum.data.counters[k]} /></div><div className="l">{label}</div>
            </Link>
          ))}
        </div>
      )}

      <section aria-labelledby="conf" style={{ marginTop: '1.5rem' }}>
        <h2 id="conf">Conflicts needing attention</h2>
        {conf.data && conf.data.items.length === 0 && <Empty>No open conflicts. Nothing is waiting for coordination.</Empty>}
        {conf.data && conf.data.items.length > 0 && (
          <div className="grid2">
            {conf.data.items.slice(0, 6).map((o: any) => (
              <Link key={o.id} to="/app/overlaps" className="overlap CONFLICT" style={{ textDecoration: 'none', color: 'inherit' }}>
                <Severity s="CONFLICT" /> <strong>{o.institution}</strong>
                <div className="muted">{o.a.unit} · {o.a.case_id} ⇄ {o.b.unit} · {o.b.case_id}</div>
              </Link>
            ))}
          </div>
        )}
        {conf.data && conf.data.items.length > 6 && <p><Link to="/app/overlaps?severity=CONFLICT">See all {conf.data.items.length} conflicts →</Link></p>}
      </section>

      <div className="grid2" style={{ marginTop: '1.5rem' }}>
        <section className="card" aria-labelledby="ag">
          <h2 id="ag">Ageing of open cases</h2>
          {age.data && <Bars rows={age.data.items.map((r: any) => [r.bucket, r.count])} />}
        </section>
        <section className="card" aria-labelledby="wl">
          <h2 id="wl">Open cases by unit</h2>
          {work.data && <Bars rows={work.data.by_unit.map((r: any) => [r.unit, r.open])} />}
          {!work.data && sum.data && <Bars rows={sum.data.by_unit.map((r: any) => [r.unit, r.open])} />}
        </section>
      </div>

      <section style={{ marginTop: '1.5rem' }} aria-labelledby="ii">
        <h2 id="ii">Institution-wise case status</h2>
        {inst.loading && !inst.data && <Loading what="institutions" />}
        {inst.data && (
          <div className="tablewrap">
            <table>
              <caption className="sr">Cases per institution by status</caption>
              <thead><tr><th>Institution</th><th>State</th><th className="num">Cases</th><th>By status</th><th>Units with open cases</th></tr></thead>
              <tbody>
                {inst.data.items.slice(0, 25).map((r: any) => (
                  <tr key={r.institution_id}>
                    <td><Link to={`/app/colleges/${r.institution_id}`}>{r.name}</Link></td>
                    <td>{r.state}</td><td className="num">{r.total}</td>
                    <td>{Object.entries(r.by_status).map(([s, n]) => `${s.replace('_', ' ').toLowerCase()} ${n}`).join(' · ')}</td>
                    <td>{r.units.join(', ') || '—'} {r.units.length > 1 && <span className="badge b-warn">△ multiple units</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {inst.data && inst.data.items.length > 25 && <p className="muted">Showing 25 of {inst.data.items.length}. Use <Link to="/app/colleges">Colleges</Link> to search.</p>}
      </section>
    </>
  )
}

function Bars({ rows }: { rows: [string, number][] }) {
  const max = Math.max(1, ...rows.map((r) => r[1]))
  return (
    <>
      <div className="bars" role="img" aria-label={rows.map((r) => `${r[0]}: ${r[1]}`).join(', ')}>
        {rows.map(([l, n]) => (
          <div className="bar" key={l}><span>{l}</span><i style={{ width: `${(n / max) * 100}%` }} /><span>{n}</span></div>
        ))}
      </div>
      <details style={{ marginTop: '.6rem' }}><summary>View as table</summary>
        <table><tbody>{rows.map(([l, n]) => <tr key={l}><td>{l}</td><td className="num">{n}</td></tr>)}</tbody></table>
      </details>
    </>
  )
}
