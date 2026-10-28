import { useAuth } from '../auth'
import { ErrorBox, SyntheticBadge, useFetch } from '../components/ui'

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
          <p><span className="badge b-ok">Concept matching: built</span> <span className="badge b-neutral">Neural embeddings: not built</span> <span className="badge b-neutral">AI reading of wording: off until a key is set and the Admin switch is on</span></p>
          <p className="muted">Different wording of the same issue is matched through a hand-written list of problem concepts in English, Hinglish and Devanagari. Without the AI switch a problem described in a way the list does not know is missed; with it, Claude is asked about those pairs and its answer is shown as AI-written. A neural embedding model could not be downloaded on the machine this was built on.</p>
        </section>
        <section className="card"><h2>You</h2><p>{me?.name}<br /><span className="muted">{me?.email}</span></p></section>
        <section className="card">
          <h2>Data</h2>
          <p><SyntheticBadge /></p>
          <p className="muted">No real complaint or personal data is stored. AICTE does not publish complaint records, so cases are simulated. Real AICTE colleges can be loaded with <code>python -m app.cli import-aicte</code>.</p>
        </section>
      </div>
    </>
  )
}

