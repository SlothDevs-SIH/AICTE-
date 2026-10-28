import { Link } from 'react-router-dom'
import { Empty, ErrorBox, Loading, useFetch } from '../components/ui'

export default function Management() {
  const risk = useFetch<any>('/risk/ranking?limit=12')
  const cl = useFetch<any>('/clusters')
  return (
    <>
      <h1>Management view</h1>
      <div className="notice" style={{ marginBottom: '1rem' }}>
        <strong>A ranking aid, not a judgement.</strong> The score is built only from complaint data (volume, age, how many units hold open cases, repeats, severity, open conflicts, trend). It does not use the size or reputation of a college, and every part is shown.
      </div>
      <section aria-labelledby="rk">
        <h2 id="rk">Colleges that may need attention</h2>
        {risk.error && <ErrorBox error={risk.error} retry={risk.reload} />}
        {risk.loading && !risk.data && <Loading what="ranking" />}
        {risk.data && risk.data.items.length === 0 && <Empty>No open cases to rank.</Empty>}
        <div style={{ display: 'grid', gap: '.8rem' }}>
          {risk.data?.items.map((r: any, i: number) => (
            <article key={r.institution_id} className="card">
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <strong>{i + 1}. <Link to={`/app/colleges/${r.institution_id}`}>{r.institution}</Link></strong>
                <span className="badge b-neutral" title="Ranking score out of 100">Score {r.score} / 100 · {r.open_cases} open</span>
              </div>
              <div className="bars" style={{ marginTop: '.6rem' }} role="img" aria-label={r.components.map((c: any) => `${c.name} ${c.points} points`).join(', ')}>
                {r.components.map((c: any) => (
                  <div className="bar" key={c.name} style={{ gridTemplateColumns: '120px 1fr 90px' }}>
                    <span>{c.name.replace('_', ' ')}</span><i style={{ width: `${c.value * 100}%`, background: 'var(--brand)' }} /><span className="muted">{c.points} of {Math.round(c.weight * 100)}</span>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
        {risk.data && <p className="muted">{risk.data.note}</p>}
      </section>
      <section style={{ marginTop: '2rem' }} aria-labelledby="cl">
        <h2 id="cl">Similar complaints piling up</h2>
        <p className="muted">Three or more open cases in the same category at one college within 90 days. Grouped by college and category only; wording is not compared.</p>
        {cl.data && cl.data.items.length === 0 && <Empty>No clusters at the moment.</Empty>}
        {cl.data && cl.data.items.length > 0 && (
          <div className="tablewrap"><table><thead><tr><th>College</th><th>Category</th><th>Pattern</th><th>Cases</th></tr></thead>
            <tbody>{cl.data.items.map((c: any) => (
              <tr key={c.institution_id + c.category}><td><Link to={`/app/colleges/${c.institution_id}`}>{c.institution}</Link></td><td>{c.category}</td>
                <td><span className="badge b-violet">☰ Systemic</span> {c.label}</td><td>{c.cases.join(', ')}</td></tr>))}</tbody></table></div>
        )}
      </section>
    </>
  )
}
