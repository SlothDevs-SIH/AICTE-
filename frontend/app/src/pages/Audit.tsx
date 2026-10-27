import { ErrorBox, Loading, fmtDateTime, useFetch } from '../components/ui'

export default function Audit() {
  const v = useFetch<any>('/audit/verify')
  const a = useFetch<any>('/audit?limit=100')
  return (
    <>
      <h1>Audit &amp; Verify</h1>
      <section className="card" aria-live="polite">
        <h2>Chain check</h2>
        {v.loading && !v.data && <Loading what="verification" />}
        {v.error && <ErrorBox error={v.error} retry={v.reload} />}
        {v.data && (v.data.intact ? (
          <div className="notice ok">
            <strong>✓ Chain intact.</strong> {v.data.entries_checked} entries re-computed. Head hash <code>{v.data.head_hash.slice(0, 16)}…</code>
          </div>
        ) : (
          <div className="notice err" role="alert">
            <strong>✕ Broken at entry #{v.data.first_broken_seq}.</strong> The record was changed, removed or reordered after it was written.
          </div>
        ))}
        <p className="muted">
          Each entry carries a hash of the one before it. This reveals edits, deletions and reordering. It does not stop someone with full
          database access from rewriting the whole chain.
        </p>
        <button className="btn sm" onClick={() => { v.reload(); a.reload() }}>Verify again</button>
      </section>
      <section style={{ marginTop: '1.5rem' }}>
        <h2>Latest entries</h2>
        {a.data && (
          <div className="tablewrap">
            <table>
              <thead><tr><th className="num">#</th><th>When</th><th>Who</th><th>Action</th><th>Record</th><th>Hash</th></tr></thead>
              <tbody>
                {a.data.items.map((e: any) => (
                  <tr key={e.seq}>
                    <td className="num">{e.seq}</td><td>{fmtDateTime(e.at)}</td><td>{e.actor}</td>
                    <td>{e.action}</td><td>{e.entity_type}</td><td><code>{e.entry_hash.slice(0, 10)}</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  )
}
