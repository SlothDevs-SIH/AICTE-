import { Expand } from '../components/Expand'
import { useState } from 'react'
import { api, ApiError, upload } from '../api'
import { useAuth } from '../auth'
import { useFetch } from '../components/ui'

export default function Imports() {
  const { me } = useAuth()
  const ref = useFetch<any>('/reference')
  const [file, setFile] = useState<File | null>(null)
  const [unit, setUnit] = useState('')
  const [job, setJob] = useState<any>(null)
  const [map, setMap] = useState<Record<string, string>>({})
  const [err, setErr] = useState<ApiError | null>(null)
  const [busy, setBusy] = useState(false)
  const isAdmin = me?.role === 'admin'
  const run = async (fn: () => Promise<any>) => {
    setBusy(true); setErr(null)
    try { await fn() } catch (e) { setErr(e as ApiError) } finally { setBusy(false) }
  }
  const doUpload = () => run(async () => {
    const f = new FormData()
    f.append('file', file!)
    if (unit) f.append('unit_id', unit)
    const j = await upload('/imports', f)
    setJob(j); setMap(Object.fromEntries(Object.entries(j.mapping).map(([k, v]) => [k, (v as string) ?? ''])))
  })
  const doDry = () => run(async () => {
    await api(`/imports/${job.id}/map`, { method: 'POST', body: { mapping: Object.fromEntries(Object.entries(map).map(([k, v]) => [k, v || null])) } })
    setJob(await api(`/imports/${job.id}/dry-run`, { method: 'POST' }))
  })
  const doCommit = () => run(async () => setJob(await api(`/imports/${job.id}/commit`, { method: 'POST' })))
  const rep = job?.report
  return (
    <>
      <h1>Import cases</h1>
      <p className="muted">Upload a CSV file, match its columns to the case fields, check it with a dry run, then commit. A bad row is reported by row number and never stops the file.</p>
      {!job && (
        <section className="card grid2">
          <label className="f">CSV file (UTF-8, up to 10 MB)<input type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></label>
          {isAdmin && <label className="f">Unit these cases belong to<select value={unit} onChange={(e) => setUnit(e.target.value)}><option value="">Choose…</option>{ref.data?.units.map((u: any) => <option key={u.id} value={u.id}>{u.code}</option>)}</select></label>}
          <div><button className="btn primary" disabled={!file || busy || (isAdmin && !unit)} onClick={doUpload}>Upload</button></div>
        </section>
      )}
      {err && <div className="notice err" role="alert" style={{ marginTop: '1rem' }}>{err.message}</div>}
      {job && (
        <>
          <section className="card" style={{ marginTop: '1rem' }}>
            <h2>1. Match columns <span className="muted" style={{ fontWeight: 400 }}>({job.filename}, {job.rows_total} rows)</span></h2>
            <div className="grid2">
              {job.fields.map((f: string) => (
                <label className="f" key={f}>{f.replace(/_/g, ' ')} {job.required.includes(f) && <small>required</small>}
                  <select value={map[f] ?? ''} disabled={job.status === 'COMMITTED'} onChange={(e) => setMap({ ...map, [f]: e.target.value })}>
                    <option value="">— none —</option>{job.columns.map((c: string) => <option key={c}>{c}</option>)}
                  </select></label>
              ))}
            </div>
            {job.sample && <Expand title="First rows of the file">
              <div className="tablewrap"><table><thead><tr>{job.columns.map((c: string) => <th key={c}>{c}</th>)}</tr></thead>
                <tbody>{job.sample.map((r: any, i: number) => <tr key={i}>{job.columns.map((c: string) => <td key={c}>{r[c]}</td>)}</tr>)}</tbody></table></div></Expand>}
            {job.status !== 'COMMITTED' && <p><button className="btn primary" disabled={busy} onClick={doDry}>Check with a dry run</button></p>}
          </section>
          {rep && (
            <section className="card" style={{ marginTop: '1rem' }} aria-live="polite">
              <h2>2. Dry run result</h2>
              {rep.duplicate_file && <div className="notice warn">This exact file was already imported before.</div>}
              <p><span className="badge b-ok">{rep.rows_ok} rows ready</span> <span className={`badge ${rep.rows_error ? 'b-danger' : 'b-neutral'}`}>{rep.rows_error} rows with errors</span></p>
              <p>College names: {rep.institution_matches.linked} linked automatically, {rep.institution_matches.needs_review} need review, {rep.institution_matches.unmatched} not found. {rep.rows_that_would_raise_overlap_alerts} row(s) would raise an overlap alert.</p>
              {rep.errors.length > 0 && (
                <div className="tablewrap"><table><thead><tr><th>Row</th><th>Problem</th></tr></thead>
                  <tbody>{rep.errors.map((e: any) => <tr key={e.row}><td>{e.row}</td><td>{e.errors.join('; ')}</td></tr>)}</tbody></table></div>
              )}
              {job.status === 'DRY_RUN' && (isAdmin
                ? <p><button className="btn primary" disabled={busy || rep.rows_ok === 0} onClick={doCommit}>Create {rep.rows_ok} cases</button></p>
                : <p className="notice">Only an administrator can commit an import. Ask your admin to commit job <code>{job.id.slice(0, 8)}</code>.</p>)}
              {job.status === 'COMMITTED' && <div className="notice ok">Done. {rep.created} case(s) created, {rep.skipped} skipped.</div>}
            </section>
          )}
          <p><button className="btn" onClick={() => { setJob(null); setFile(null) }}>Start another import</button></p>
        </>
      )}
    </>
  )
}
