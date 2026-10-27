import { useAuth } from '../auth'
import { ErrorBox, useFetch } from '../components/ui'

export default function Status() {
  const { me } = useAuth()
  const meta = useFetch<any>('/meta')
  const ready = useFetch<any>('/readyz')
  return (
    <>
      <h1>System status</h1>
      <div className="grid2">
        <section className="card">
          <h2>Backend</h2>
          {ready.data ? (
            <p>
              <span className={`badge ${ready.data.status === 'ready' ? 'b-ok' : 'b-danger'}`}>{ready.data.status === 'ready' ? '✓ Ready' : '✕ Not ready'}</span>{' '}
              database: {ready.data.checks.database}
            </p>
          ) : ready.error ? <ErrorBox error={ready.error} /> : <p>Checking…</p>}
          {meta.data && <p className="muted">Version {meta.data.version} · phase {meta.data.phase} · environment {meta.data.environment}</p>}
        </section>
        <section className="card">
          <h2>AI features</h2>
          <p><span className="badge b-neutral">Embeddings: not built</span> <span className="badge b-neutral">Language model: not built</span></p>
          <p className="muted">Overlaps use institution and category rules only. Matching different wording of the same issue is planned, not built.</p>
        </section>
        <section className="card"><h2>You</h2><p>{me?.name}<br /><span className="muted">{me?.email}</span></p></section>
        <section className="card">
          <h2>Data</h2>
          <p><span className="badge synthetic">⚗ SYNTHETIC DATA</span></p>
          <p className="muted">No real complaint or personal data is stored.</p>
        </section>
      </div>
    </>
  )
}
